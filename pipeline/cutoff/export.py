"""Write PNG overlays, GeoJSON and JSON outputs.

Overlays are in EPSG:4326 (what the web map expects), at most 2048 px on the long side. GeoJSON uses
[lon, lat] with 6 decimals, exterior rings counter-clockwise, simplified in metres before reprojection.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import shapely
from affine import Affine
from PIL import Image
from pyproj import Transformer
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.features import shapes
from rasterio.transform import from_bounds
from rasterio.warp import reproject
from shapely.geometry import Polygon, shape
from shapely.geometry.polygon import orient

MAX_PNG_SIDE = 2048
METRES_PER_DEGREE = 111_320.0
HV_BLACK_DB, HV_WHITE_DB = -25.0, -5.0     # HV images: -25 dB black, -5 dB white
CHANGE_FULL_DB = 6.0                        # change images: full colour at +/- 6 dB


# ---- small helpers shared with the mock generator ----

def write_json(path: Path, data, compact: bool = False) -> None:
    text = (json.dumps(data, ensure_ascii=False, separators=(",", ":")) if compact
            else json.dumps(data, ensure_ascii=False, indent=2))
    Path(path).write_text(text + "\n", encoding="utf-8", newline="\n")


def feature_collection(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}


def bounds_from_bbox(bbox: list[float]) -> list[list[float]]:
    """Image corners in MapLibre order: top-left, top-right, bottom-right, bottom-left."""
    w, s, e, n = bbox
    return [[w, n], [e, n], [e, s], [w, s]]


def png_names(pair: dict) -> dict[str, str]:
    d_before, d_after = pair["before"][:10].replace("-", ""), pair["after"][:10].replace("-", "")
    return {"before_png": f"hv_{pair['id']}_{d_before}.png", "after_png": f"hv_{pair['id']}_{d_after}.png",
            "change_png": f"hv_change_{pair['id']}.png"}


def pair_entry(pair: dict, bbox: list[float], flagged_pixels: int) -> dict:
    return {"id": pair["id"], "track": pair["track"], "direction": pair["direction"],
            "before": pair["before"], "after": pair["after"], **png_names(pair),
            "bounds": bounds_from_bbox(bbox), "granules": list(pair.get("granules", [])),
            "flagged_pixels": int(flagged_pixels)}


def default_timeline(cfg: dict) -> list[dict]:
    """Timeline from the config, or the standard entries built from the primary pair."""
    if cfg.get("timeline"):
        return cfg["timeline"]
    primary = next(p for p in cfg["pairs"] if p["id"] == cfg["primary_pair"])
    return [
        {"time_utc": cfg["time_utc"], "label": "M7.7 earthquake", "source": "USGS"},
        {"time_utc": primary["after"], "label": f"First NISAR pass after the quake (track {primary['track']})", "source": "ASF"},
        {"time_utc": "2026-10-16T00:00:00Z", "label": "92% of roads with structural collapses reopened", "source": "Newsroom Panama"},
    ]


# ---- PNG overlays ----

def png_hv(db: np.ndarray, nodata: np.ndarray | None = None) -> Image.Image:
    """Greyscale HV image with an alpha channel: transparent where there is no data."""
    if nodata is None:
        nodata = ~np.isfinite(db)
    grey = np.clip((np.nan_to_num(db, nan=HV_BLACK_DB) - HV_BLACK_DB) / (HV_WHITE_DB - HV_BLACK_DB), 0, 1) * 255.0
    alpha = np.where(nodata, 0, 255)
    return Image.fromarray(np.dstack([grey.astype(np.uint8), alpha.astype(np.uint8)]), "LA")


def png_change(dhv: np.ndarray, nodata: np.ndarray | None = None) -> Image.Image:
    """Change image: red = drop, blue = rise, transparent near 0 dB and where there is no data."""
    if nodata is None:
        nodata = ~np.isfinite(dhv)
    d = np.nan_to_num(dhv, nan=0.0)
    rgba = np.zeros(d.shape + (4,), dtype=np.uint8)
    rgba[d < 0, :3] = (220, 38, 38)
    rgba[d > 0, :3] = (37, 99, 235)
    alpha = np.clip((np.abs(d) - 1.0) / (CHANGE_FULL_DB - 1.0), 0, 1) * 255.0
    rgba[..., 3] = np.where(nodata, 0, alpha).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def overlay_size(bbox: list[float], res_m: float, max_side: int = MAX_PNG_SIDE) -> tuple[int, int]:
    """(width, height) in pixels for an EPSG:4326 overlay of the box: native detail, capped at max_side."""
    w_deg, h_deg = bbox[2] - bbox[0], bbox[3] - bbox[1]
    px_per_deg = min(max_side / max(w_deg, h_deg), METRES_PER_DEGREE / res_m)
    return max(1, round(w_deg * px_per_deg)), max(1, round(h_deg * px_per_deg))


def to_wgs84(data: np.ndarray, transform: Affine, crs: CRS, bbox: list[float], res_m: float) -> np.ndarray:
    """Resample a grid image onto an EPSG:4326 grid covering the bbox. Uncovered pixels are NaN."""
    width, height = overlay_size(bbox, res_m)
    dst = np.full((height, width), np.nan, dtype="float32")
    reproject(source=data.astype("float32"), destination=dst, src_transform=transform, src_crs=crs, src_nodata=np.nan,
              dst_transform=from_bounds(*bbox, width, height), dst_crs=CRS.from_epsg(4326), dst_nodata=np.nan,
              resampling=Resampling.average)
    return dst


def save_png(path: Path, image: Image.Image) -> None:
    image.save(path, optimize=True)


# ---- GeoJSON ----

def _clean_ring(coords) -> list[list[float]]:
    ring = [[round(float(x), 6), round(float(y), 6)] for x, y in coords]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def _polygon_coordinates(poly: Polygon) -> list[list[list[float]]]:
    poly = orient(poly, 1.0)
    return [_clean_ring(poly.exterior.coords)] + [_clean_ring(r.coords) for r in poly.interiors]


def geometry_dict(geom) -> dict | None:
    """GeoJSON geometry for a Polygon/MultiPolygon: rounded to 6 decimals, valid, CCW. None if it vanished."""
    polys = [geom] if isinstance(geom, Polygon) else list(getattr(geom, "geoms", []))
    cleaned: list[Polygon] = []
    for p in polys:
        if p.is_empty:
            continue
        rounded = Polygon(_clean_ring(p.exterior.coords), [_clean_ring(r.coords) for r in p.interiors])
        if not rounded.is_valid:
            rounded = rounded.buffer(0)
        for q in ([rounded] if isinstance(rounded, Polygon) else list(getattr(rounded, "geoms", []))):
            if isinstance(q, Polygon) and not q.is_empty and q.area > 0:
                cleaned.append(q)
    if not cleaned:
        return None
    if len(cleaned) == 1:
        return {"type": "Polygon", "coordinates": _polygon_coordinates(cleaned[0])}
    return {"type": "MultiPolygon", "coordinates": [_polygon_coordinates(q) for q in cleaned]}


def to_lonlat(geom, crs: CRS):
    """Reproject a geometry from the grid CRS to lon/lat."""
    t = Transformer.from_crs(crs, 4326, always_xy=True)

    def convert(coords: np.ndarray) -> np.ndarray:
        x, y = t.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])

    return shapely.transform(geom, convert)


def landslide_features(slides, crs: CRS, pixel_m: float) -> list[dict]:
    """GeoJSON features for detected landslides, simplified to half a pixel."""
    feats = []
    for s in slides:
        geom = geometry_dict(to_lonlat(s.geometry.simplify(0.5 * pixel_m, preserve_topology=True), crs))
        if geom is not None:
            feats.append({"type": "Feature", "geometry": geom, "properties": dict(s.props)})
    return feats


def mask_polygons(mask: np.ndarray, transform: Affine, min_pixels: int = 1):
    """Polygons (grid CRS) around the true pixels of a mask, dropping patches under min_pixels pixels."""
    pieces = [shape(g) for g, v in shapes(mask.astype("uint8"), mask=mask, transform=transform, connectivity=8) if v == 1]
    return [p for p in pieces if p.area >= min_pixels * abs(transform.a * transform.e)]


def unknown_features(unknown: np.ndarray, transform: Affine, crs: CRS, pixel_m: float, min_pixels: int = 10) -> list[dict]:
    """GeoJSON features for ground no pair can see, simplified to two pixels."""
    feats = []
    for p in mask_polygons(unknown, transform, min_pixels):
        geom = geometry_dict(to_lonlat(p.simplify(2.0 * pixel_m, preserve_topology=True), crs))
        if geom is not None:
            feats.append({"type": "Feature", "geometry": geom, "properties": {}})
    return feats

