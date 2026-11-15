"""Find candidate landslides from the HV drop on forested slopes.

A pixel is a candidate in one before/after pair when its HV dropped by at least the threshold, it lies on a
steep slope, it was forest before (bright enough in HV), and the radar could see it. Candidates from several
pairs are combined by voting, then turned into polygons with statistics.
All arrays share one grid; dB images are float32 with NaN for no data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from affine import Affine
from rasterio.features import shapes
from scipy.ndimage import find_objects, label, uniform_filter
from shapely.geometry import MultiPolygon, Polygon, shape
from shapely.ops import unary_union
from skimage.filters import threshold_otsu

EIGHT = np.ones((3, 3), dtype=int)   # 8-connected neighbourhood


@dataclass(frozen=True)
class DetectParams:
    threshold_db: float = -3.0         # a drop of at least this much (more negative = bigger drop)
    min_slope_deg: float = 10.0
    min_forest_hv_db: float = -16.0    # HV before the event must be at least this bright to count as forest
    min_pixels: int = 3                # smaller patches are removed
    highpass_px: int = 0               # 0 = off. Otherwise each pair's change is measured against its own local mean (window in pixels)

    @classmethod
    def from_config(cls, detect: dict) -> "DetectParams":
        return cls(float(detect["threshold_db"]), float(detect["min_slope_deg"]),
                   float(detect["min_forest_hv_db"]), int(detect["min_pixels"]), int(detect.get("highpass_px", 0)))


def local_mean(x: np.ndarray, size: int) -> np.ndarray:
    """size x size box mean that ignores NaN. Pixels with too little valid data around them stay NaN."""
    ok = np.isfinite(x)
    total = uniform_filter(np.where(ok, x, 0.0).astype("float32"), size, mode="nearest")
    count = uniform_filter(ok.astype("float32"), size, mode="nearest")
    out = np.where(count > 0.3, total / np.maximum(count, 1e-6), np.nan).astype("float32")
    out[~ok] = np.nan
    return out


def adjusted_change(dhv_db: np.ndarray, visible: np.ndarray, highpass_px: int) -> np.ndarray:
    """The change used for detection. With highpass_px > 1 the pair's own local mean change is subtracted, so a slow,
    region-wide shift (wetter soil, calibration drift, viewing geometry) is not mistaken for a landslide.
    Pixels the pair cannot see become NaN."""
    seen = np.where(visible & np.isfinite(dhv_db), dhv_db, np.nan).astype("float32")
    if highpass_px > 1:
        seen = (seen - local_mean(seen, highpass_px)).astype("float32")
    return seen


def visible_mask(before_db: np.ndarray, after_db: np.ndarray, unknown: np.ndarray) -> np.ndarray:
    """Pixels this pair can actually see: valid in both images and not shadow/layover/no DEM."""
    return np.isfinite(before_db) & np.isfinite(after_db) & ~unknown


def eligible_mask(before_db: np.ndarray, slope_deg: np.ndarray, visible: np.ndarray, params: DetectParams) -> np.ndarray:
    """Forested slopes the pair can see: the places a landslide could be flagged."""
    with np.errstate(invalid="ignore"):
        return visible & (slope_deg >= params.min_slope_deg) & (before_db >= params.min_forest_hv_db)


def remove_small_patches(mask: np.ndarray, min_pixels: int) -> np.ndarray:
    """Drop 8-connected patches smaller than min_pixels."""
    labels, n = label(mask, structure=EIGHT)
    if n == 0:
        return mask.copy()
    sizes = np.bincount(labels.ravel())
    keep = sizes >= min_pixels
    keep[0] = False
    return keep[labels]


def otsu_threshold(dhv_db: np.ndarray, eligible: np.ndarray, lo: float = -6.0, hi: float = -1.5,
                   default: float = -3.0) -> float:
    """First guess for the threshold: Otsu on the change over forested slopes, clamped to [lo, hi]."""
    values = dhv_db[eligible & np.isfinite(dhv_db)]
    if values.size < 10 or np.ptp(values) == 0:
        return default
    return float(np.clip(threshold_otsu(values), lo, hi))


def candidate_mask(dhv_db: np.ndarray, before_db: np.ndarray, slope_deg: np.ndarray, unknown: np.ndarray,
                   params: DetectParams) -> np.ndarray:
    """Candidate landslide pixels for one pair."""
    visible = np.isfinite(dhv_db) & np.isfinite(before_db) & ~unknown
    eligible = eligible_mask(before_db, slope_deg, visible, params)
    with np.errstate(invalid="ignore"):
        raw = eligible & (dhv_db <= params.threshold_db)
    return remove_small_patches(raw, params.min_pixels)


def flag_rate(candidates: np.ndarray, eligible: np.ndarray) -> float:
    """Share (0-1) of forested, visible slope pixels that were flagged."""
    n = int(eligible.sum())
    return float((candidates & eligible).sum()) / n if n else 0.0


def combine_votes(candidates: list[np.ndarray], visibles: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Keep pixels with votes >= min(2, max(visible, 1)). Returns (keep, votes, visible_count)."""
    votes = np.sum(candidates, axis=0, dtype=np.int16)
    visible = np.sum(visibles, axis=0, dtype=np.int16)
    need = np.minimum(2, np.maximum(visible, 1))
    return (votes >= 1) & (votes >= need), votes, visible


def confidence(seen: int, visible: int) -> str:
    """high: seen >= 2 and in all but at most one visible pair; medium: seen >= 2; low: otherwise."""
    if seen >= 2 and seen >= visible - 1:
        return "high"
    if seen >= 2:
        return "medium"
    return "low"


@dataclass
class Landslide:
    geometry: Polygon | MultiPolygon      # in the grid's metric CRS
    props: dict


def _mean(values: np.ndarray) -> float | None:
    values = values[np.isfinite(values)]
    return float(values.astype("float64").mean()) if values.size else None


def polygonise(keep: np.ndarray, candidates: list[np.ndarray], visibles: list[np.ndarray],
               before_dbs: list[np.ndarray], after_dbs: list[np.ndarray], slope_deg: np.ndarray,
               transform: Affine) -> list[Landslide]:
    """One landslide per 8-connected patch of `keep`, with the properties of the output format.

    A pair "flagged" a patch if it has at least one candidate pixel in it. A pair "could see" a patch if it
    flagged it or at least half of the patch is visible to it. HV statistics come from the first pair
    (the primary one); if it has no valid pixels there, the next pair that has some is used.
    """
    labels, n = label(keep, structure=EIGHT)
    out: list[Landslide] = []
    for i, sl in enumerate(find_objects(labels), start=1):
        if sl is None:
            continue
        sub = labels[sl] == i
        window = transform @ Affine.translation(sl[1].start, sl[0].start)
        parts = [shape(g) for g, v in shapes(sub.astype("uint8"), mask=sub, transform=window, connectivity=8) if v == 1]
        geom = unary_union(parts)
        if geom.is_empty:
            continue
        flagged = [bool(c[sl][sub].any()) for c in candidates]
        could = [f or float(v[sl][sub].mean()) >= 0.5 for f, v in zip(flagged, visibles)]
        seen, vis = int(sum(flagged)), int(sum(could))
        before = after = None
        for b, a in zip(before_dbs, after_dbs):
            before, after = _mean(b[sl][sub]), _mean(a[sl][sub])
            if before is not None and after is not None:
                break
        if before is None or after is None:
            before = after = float("nan")
        slope = _mean(slope_deg[sl][sub])
        out.append(Landslide(geom, {
            "id": f"L{len(out) + 1:04d}",
            "area_m2": round(float(geom.area), 1),
            "hv_before_db": round(before, 1),
            "hv_after_db": round(after, 1),
            "dhv_db": round(after - before, 1),
            "slope_deg": round(slope if slope is not None else float("nan"), 1),
            "pairs_seen": seen,
            "pairs_visible": vis,
            "confidence": confidence(seen, vis),
        }))
    return out
