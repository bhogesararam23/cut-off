"""Accuracy against hand-marked check points, scored once on a sealed test half.

Protocol:
  1. The check points (landslide / forest, marked by hand on Sentinel-2 photos) are split 50/50 per label
     with a fixed seed into a tune half and a test half.
  2. The detection threshold is chosen on the TUNE half only (best detection rate minus false-alarm rate).
  3. Detection is rerun with that threshold, then the TEST half is scored once. A landslide point counts as
     found if a landslide polygon lies within 20 m; a forest point is a false alarm if one does.
  4. A second scoring of the test half is refused unless --force is given, and every run is logged.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import shapely
from pyproj import Transformer
from scipy.stats import rankdata
from shapely.geometry import shape

from .detect import DetectParams, candidate_mask
from .export import mask_polygons
from .radar import Raster, read_raster

SEED = 2026
TOLERANCE_M = 20.0
THRESHOLDS = [-1.5 - 0.5 * i for i in range(10)]        # -1.5, -2.0, ... -6.0 dB
DEFAULT_THRESHOLD = -3.0
LABELS = ("landslide", "forest")
SIZES = ("small", "medium", "large")


class ValidationError(Exception):
    """A problem with the check points or the protocol (never a crash trace for the user)."""


@dataclass(frozen=True)
class CheckPoint:
    id: str
    lon: float
    lat: float
    label: str
    size: str


# ---- check points ----

def load_points(path: str | Path) -> list[CheckPoint]:
    """Read points.csv (id,lon,lat,label,size,notes) and refuse anything malformed."""
    path = Path(path)
    if not path.is_file():
        raise ValidationError(f"check points file not found: {path}")
    points: list[CheckPoint] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = {"id", "lon", "lat", "label", "size"} - set(reader.fieldnames or [])
        if missing:
            raise ValidationError(f"{path.name}: missing column(s) {sorted(missing)}")
        for n, row in enumerate(reader, start=2):
            pid = (row["id"] or "").strip()
            label = (row["label"] or "").strip()
            size = (row["size"] or "").strip()
            try:
                lon, lat = float(row["lon"]), float(row["lat"])
            except (TypeError, ValueError):
                raise ValidationError(f"{path.name} line {n}: lon and lat must be numbers") from None
            if not pid or pid in seen:
                raise ValidationError(f"{path.name} line {n}: id is empty or repeated")
            if label not in LABELS:
                raise ValidationError(f"{path.name} line {n}: label must be 'landslide' or 'forest', got {label!r}")
            if size and size not in SIZES:
                raise ValidationError(f"{path.name} line {n}: size must be small, medium, large or blank, got {size!r}")
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValidationError(f"{path.name} line {n}: coordinates out of range")
            seen.add(pid)
            points.append(CheckPoint(pid, lon, lat, label, size))
    return points


def split_points(points: list[CheckPoint], seed: int = SEED) -> tuple[list[CheckPoint], list[CheckPoint]]:
    """Stratified 50/50 split by label. Deterministic for a seed. Returns (tune, test)."""
    tune: list[CheckPoint] = []
    test: list[CheckPoint] = []
    rng = np.random.default_rng(seed)
    for label in LABELS:
        group = sorted((p for p in points if p.label == label), key=lambda p: p.id)
        order = rng.permutation(len(group))
        n_test = len(group) // 2
        test += [group[i] for i in order[:n_test]]
        tune += [group[i] for i in order[n_test:]]
    return sorted(tune, key=lambda p: p.id), sorted(test, key=lambda p: p.id)


def points_are_committed(root: Path, rel: str) -> tuple[bool, str]:
    """The check points must be committed (and unchanged) before anything is scored."""
    try:
        tracked = subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", "--", rel], capture_output=True, text=True)
        if tracked.returncode != 0:
            return False, f"{rel} is not committed yet"
        changed = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", rel], capture_output=True, text=True)
    except FileNotFoundError:
        return False, "git was not found, so it cannot be checked that the check points are committed"
    if changed.stdout.strip():
        return False, f"{rel} has changes that are not committed"
    return True, ""


# ---- scoring ----

def auc(scores: np.ndarray, positive: np.ndarray) -> float:
    """Rank-based area under the ROC curve (ties share their average rank). 0.5 = chance, 1.0 = perfect."""
    scores = np.asarray(scores, dtype=float)
    positive = np.asarray(positive, dtype=bool)
    n_pos, n_neg = int(positive.sum()), int((~positive).sum())
    if n_pos == 0 or n_neg == 0:
        raise ValidationError("the AUC needs at least one landslide point and one forest point with radar coverage")
    ranks = rankdata(scores)
    return float((ranks[positive].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def project_points(points: list[CheckPoint], crs) -> np.ndarray:
    t = Transformer.from_crs(4326, crs, always_xy=True)
    x, y = t.transform([p.lon for p in points], [p.lat for p in points])
    return np.column_stack([x, y]) if len(points) else np.empty((0, 2))


def found_within(xy: np.ndarray, polygons: list, tolerance_m: float = TOLERANCE_M) -> np.ndarray:
    """For each point: is a polygon within tolerance_m metres? (All False if there are no polygons.)"""
    out = np.zeros(len(xy), dtype=bool)
    if len(xy) == 0 or not polygons:
        return out
    tree = shapely.STRtree(polygons)
    hits = tree.query(shapely.points(xy), predicate="dwithin", distance=tolerance_m)
    out[np.unique(hits[0])] = True
    return out


def sample(raster: Raster, xy: np.ndarray) -> np.ndarray:
    """Raster value under each point; NaN outside the raster or where there is no data."""
    inv = ~raster.transform
    cols, rows = inv * (xy[:, 0], xy[:, 1])
    rows, cols = np.floor(rows).astype(int), np.floor(cols).astype(int)
    ok = (rows >= 0) & (rows < raster.shape[0]) & (cols >= 0) & (cols < raster.shape[1])
    out = np.full(len(xy), np.nan)
    out[ok] = raster.data[rows[ok], cols[ok]]
    return out


@dataclass
class TuneInputs:
    dhv: Raster
    before: Raster
    unknown: np.ndarray
    slope: np.ndarray


def load_tune_inputs(work: Path, pair_id: str) -> TuneInputs:
    names = [f"dhv_{pair_id}.tif", f"hvbefore_{pair_id}.tif", f"unknown_{pair_id}.tif", "slope.tif"]
    missing = [n for n in names if not (work / n).is_file()]
    if missing:
        raise ValidationError(f"missing work files {missing}: run the radar processing first (python -m cutoff run)")
    dhv, before, unknown, slope = (read_raster(work / n) for n in names)
    return TuneInputs(dhv, before, unknown.data > 0.5, slope.data)


def tune_threshold(inputs: TuneInputs, tune_land: np.ndarray, tune_forest: np.ndarray, base: DetectParams,
                   thresholds: list[float] = THRESHOLDS) -> tuple[float, list[dict]]:
    """Pick the threshold with the best Youden's J on the TUNE half only. Returns (best, table)."""
    if len(tune_land) == 0 or len(tune_forest) == 0:
        raise ValidationError("the tuning half needs at least one landslide point and one forest point")
    table = []
    for t in thresholds:
        params = DetectParams(t, base.min_slope_deg, base.min_forest_hv_db, base.min_pixels)
        mask = candidate_mask(inputs.dhv.data, inputs.before.data, inputs.slope, inputs.unknown, params)
        polys = mask_polygons(mask, inputs.dhv.transform)
        tpr = float(found_within(tune_land, polys).mean())
        fpr = float(found_within(tune_forest, polys).mean())
        table.append({"threshold_db": t, "detection_rate": round(tpr, 4), "false_alarm_rate": round(fpr, 4), "youden_j": round(tpr - fpr, 4)})
    # best J; ties go to the value closest to the default, then to the less negative one
    best = min(table, key=lambda r: (-r["youden_j"], abs(r["threshold_db"] - DEFAULT_THRESHOLD), -r["threshold_db"]))
    return best["threshold_db"], table


def landslide_polygons(path: Path, crs) -> list:
    """Landslide polygons from the output file, in the grid's metric coordinate system."""
    data = json.loads(path.read_text(encoding="utf-8"))
    t = Transformer.from_crs(4326, crs, always_xy=True)
    polys = []
    for f in data["features"]:
        g = shape(f["geometry"])
        polys.append(shapely.transform(g, lambda c: np.column_stack(t.transform(c[:, 0], c[:, 1]))))
    return polys


def score_test(test: list[CheckPoint], polygons: list, dhv: Raster, threshold_db: float) -> dict:
    """The sealed-test numbers: detection rate, false-alarm rate, AUC and detection by size."""
    xy = project_points(test, dhv.crs)
    is_land = np.array([p.label == "landslide" for p in test])
    found = found_within(xy, polygons)
    n_land, n_forest = int(is_land.sum()), int((~is_land).sum())
    if n_land == 0 or n_forest == 0:
        raise ValidationError("the test half needs at least one landslide point and one forest point")
    detection = float(found[is_land].mean())
    false_alarm = float(found[~is_land].mean())
    scores = -sample(dhv, xy)                                   # bigger drop = more landslide-like
    covered = np.isfinite(scores)
    value = auc(scores[covered], is_land[covered])
    by_size = []
    for size in SIZES:
        sel = np.array([p.label == "landslide" and p.size == size for p in test])
        if sel.any():
            by_size.append({"size": size, "n": int(sel.sum()), "detection_rate": round(float(found[sel].mean()), 4)})
    return {
        "split": "test", "n_test_landslide": n_land, "n_test_forest": n_forest,
        "detection_rate": round(detection, 4), "false_alarm_rate": round(false_alarm, 4), "auc": round(value, 4),
        "threshold_db": float(threshold_db), "by_size": by_size,
        "points_without_radar_coverage": int((~covered).sum()),
    }


# ---- the whole protocol ----

def _read_runs(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []


def _write(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _publish(out: Path, result: dict) -> None:
    """Put the validation block (without bookkeeping keys) into stats.json."""
    stats_path = out / "stats.json"
    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    if stats.get("mock"):
        raise ValidationError("stats.json is mock data: run the real processing first")
    stats["validation"] = {k: v for k, v in result.items() if k != "points_without_radar_coverage"}
    _write(stats_path, stats)


def run_validation(cfg: dict, root: Path, out: Path | None = None, work: Path | None = None, force: bool = False,
                   require_committed: bool = True, rerun: Callable[[], object] | None = None,
                   log: Callable[[str], None] = print) -> dict:
    """Tune on the tune half, rerun detection, score the test half once, write stats.json. Returns the result."""
    root = Path(root)
    out = Path(out) if out else (root / cfg["out"]).resolve()
    work = Path(work) if work else (root / cfg["work"]).resolve()
    points_rel = cfg["points"]
    runs_file, result_file = work / "validation_runs.json", work / "validation_result.json"

    runs = _read_runs(runs_file)
    if any(r.get("scored_test") for r in runs) and not force:
        raise ValidationError("the test half has already been scored once; scoring it again would defeat the "
                              "purpose. Use --restore to put the stored result back into stats.json, or --force "
                              "(it will be logged) if you really must.")
    if require_committed:
        ok, why = points_are_committed(root, points_rel)
        if not ok:
            raise ValidationError(f"{why}. Commit the check points before scoring anything (or pass --allow-uncommitted).")

    points_path = (root / points_rel).resolve()
    points = load_points(points_path)
    tune, test = split_points(points)
    log(f"{len(points)} check points: {len(tune)} for tuning, {len(test)} sealed for the test")

    pair_id = cfg["primary_pair"]
    inputs = load_tune_inputs(work, pair_id)
    base = DetectParams.from_config(cfg["detect"])
    tune_land = project_points([p for p in tune if p.label == "landslide"], inputs.dhv.crs)
    tune_forest = project_points([p for p in tune if p.label == "forest"], inputs.dhv.crs)
    best, table = tune_threshold(inputs, tune_land, tune_forest, base)
    log(f"tuned threshold: {best:g} dB (chosen on the tuning half only)")
    work.mkdir(parents=True, exist_ok=True)
    _write(work / "tuned.json", {
        "threshold_db": best, "seed": SEED, "n_tune_landslide": len(tune_land), "n_tune_forest": len(tune_forest),
        "points_sha256": hashlib.sha256(points_path.read_bytes()).hexdigest(), "table": table,
    })

    log("rerunning detection with the tuned threshold")
    if rerun is None:
        from .run import run
        rerun = lambda: run(cfg, root, out=out, work=work, log=log)  # noqa: E731
    rerun()

    polygons = landslide_polygons(out / "landslides.geojson", inputs.dhv.crs)
    runs.append({"time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "scored_test": True, "forced": bool(force),
                 "threshold_db": best, "points_sha256": hashlib.sha256(points_path.read_bytes()).hexdigest()})
    _write(runs_file, runs)                                       # logged before the numbers are looked at
    result = score_test(test, polygons, inputs.dhv, best)
    _write(result_file, result)
    _publish(out, result)
    log(f"test half scored once: found {100 * result['detection_rate']:.0f}%, false alarms {100 * result['false_alarm_rate']:.0f}%, AUC {result['auc']:.2f}")
    return result


def restore_validation(cfg: dict, root: Path, out: Path | None = None, work: Path | None = None) -> dict:
    """Put the stored (single) test result back into stats.json, for example after the processing was rerun."""
    root = Path(root)
    out = Path(out) if out else (root / cfg["out"]).resolve()
    work = Path(work) if work else (root / cfg["work"]).resolve()
    result_file = work / "validation_result.json"
    if not result_file.is_file():
        raise ValidationError("there is no stored test result: validation has not been run yet")
    result = json.loads(result_file.read_text(encoding="utf-8"))
    _publish(out, result)
    return result
