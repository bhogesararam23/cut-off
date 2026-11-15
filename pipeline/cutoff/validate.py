"""Accuracy against hand-marked check points, using a held-out half of the points.

The points are a random split within one study area, labelled from optical images and checked by eye. This is
not independent geographic validation and not field validation; nearby points may share conditions.

Protocol:
  1. The check points (landslide / forest, marked by hand on Sentinel-2 photos) are split 50/50 per label
     with a fixed seed into a tuning half and a held-out half.
  2. The method settings (size of the local-mean window, detection threshold) are chosen on the TUNING half only.
     Among the settings that flag less before the quake than after it (and flag no more than a capped share of the
     forested slope), the one with the best tuning AUC wins; ties go to the best Youden's J.
  3. Detection is rerun with those settings, then the HELD-OUT half is scored. A landslide point counts as
     found if a landslide polygon lies within 20 m; a forest point is a false alarm if one does.
  4. Scoring the held-out half again is refused unless --force is given, and every scoring is logged.
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

from .detect import (DetectParams, adjusted_change, candidate_mask, combine_votes, eligible_mask, flag_rate,
                     remove_small_patches)
from .export import mask_polygons
from .radar import Raster, read_raster

SEED = 2026
TOLERANCE_M = 20.0
THRESHOLDS = [-0.5, -0.75, -1.0, -1.25, -1.5, -2.0, -2.5, -3.0, -4.0, -5.0, -6.0]     # dB below the reference
DEFAULT_THRESHOLD = -3.0
DEFAULT_WINDOWS = [0]                                   # 0 = no local-mean correction
UNLIMITED = 1.0
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
class PassData:
    """One pair's saved work files: the raw change, HV before, and the pixels the pair cannot see."""
    id: str
    dhv: Raster
    before: np.ndarray
    unknown: np.ndarray


@dataclass
class TuneInputs:
    passes: list[PassData]            # the after-the-quake pairs
    baseline: PassData                # two passes from before the quake
    compare_id: str                   # the pair the baseline is compared with (same track)
    slope: np.ndarray

    @property
    def transform(self):
        return self.passes[0].dhv.transform

    @property
    def crs(self):
        return self.passes[0].dhv.crs


def _load_pass(work: Path, name: str, label: str) -> PassData:
    names = [f"dhv_{name}.tif", f"hvbefore_{name}.tif", f"unknown_{name}.tif"]
    missing = [n for n in names if not (work / n).is_file()]
    if missing:
        raise ValidationError(f"missing work files {missing}: run the radar processing first (python -m cutoff run)")
    dhv, before, unknown = (read_raster(work / n) for n in names)
    return PassData(label, dhv, before.data, unknown.data > 0.5)


def load_tune_inputs(work: Path, pair_ids: list[str], compare_id: str) -> TuneInputs:
    passes = [_load_pass(work, pid, pid) for pid in pair_ids]
    baseline = _load_pass(work, "baseline", "baseline")
    if not (work / "slope.tif").is_file():
        raise ValidationError("missing work file 'slope.tif': run the radar processing first (python -m cutoff run)")
    return TuneInputs(passes, baseline, compare_id, read_raster(work / "slope.tif").data)


def _adjusted(p: PassData, highpass_px: int) -> np.ndarray:
    vis = np.isfinite(p.dhv.data) & np.isfinite(p.before) & ~p.unknown
    return adjusted_change(p.dhv.data, vis, highpass_px)


def point_cells(xy: np.ndarray, transform) -> tuple[np.ndarray, np.ndarray]:
    cols, rows = (~transform) * (xy[:, 0], xy[:, 1])
    return np.floor(rows).astype(int), np.floor(cols).astype(int)


def neighbourhood_max(score: np.ndarray, rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    """Largest value in the 3 x 3 pixels around each point (one pixel is the 20 m match distance). NaN if none."""
    out = np.full(len(rows), np.nan)
    h, w = score.shape
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            r, c = rows + dr, cols + dc
            ok = (r >= 0) & (r < h) & (c >= 0) & (c < w)
            v = np.full(len(rows), np.nan)
            v[ok] = score[r[ok], c[ok]]
            out = np.fmax(out, v)
    return out


def point_scores(adjusted: list[np.ndarray], xy: np.ndarray, transform) -> np.ndarray:
    """Per point: the mean over passes of the biggest drop in the 3 x 3 pixels around it (bigger = more landslide-like)."""
    rows, cols = point_cells(xy, transform)
    per_pass = np.vstack([neighbourhood_max(-a, rows, cols) for a in adjusted])
    valid = np.isfinite(per_pass)
    total = np.where(valid, per_pass, 0.0).sum(axis=0)
    n = valid.sum(axis=0)
    return np.where(n > 0, total / np.maximum(n, 1), np.nan)


def _params(base: DetectParams, threshold_db: float) -> DetectParams:
    return DetectParams(threshold_db, base.min_slope_deg, base.min_forest_hv_db, base.min_pixels, base.highpass_px)


def detect_with(inputs: TuneInputs, adjusted: list[np.ndarray], threshold_db: float, base: DetectParams):
    """The combined (voted) candidate mask, and the flag rate of the compare pair."""
    params = _params(base, threshold_db)
    cands, visibles = [], []
    post_rate = None
    for p, adj in zip(inputs.passes, adjusted):
        vis = np.isfinite(adj)
        c = candidate_mask(adj, p.before, inputs.slope, p.unknown, params)
        cands.append(c)
        visibles.append(vis)
        if p.id == inputs.compare_id:
            post_rate = flag_rate(c, eligible_mask(p.before, inputs.slope, vis, params))
    keep, _, _ = combine_votes(cands, visibles)
    keep = remove_small_patches(keep, params.min_pixels)
    return keep, post_rate


def baseline_flag_rate(inputs: TuneInputs, adj: np.ndarray, threshold_db: float, base: DetectParams) -> float:
    b = inputs.baseline
    params = _params(base, threshold_db)
    cand = candidate_mask(adj, b.before, inputs.slope, b.unknown, params)
    return flag_rate(cand, eligible_mask(b.before, inputs.slope, np.isfinite(adj), params))


def choose_setting(table: list[dict], max_post_share: float) -> tuple[dict, str]:
    """The rule: a setting must flag less before the quake than after it, and not more than max_post_share of the
    forested slope after it. Among those, best tuning AUC; then best Youden's J; then nearest the default threshold."""
    feasible = [r for r in table if r["baseline_flag_rate"] < r["post_flag_rate"] <= max_post_share]
    rule = ("flag rate before the quake below the rate after it, and at most %.0f%% of forested slope flagged after it; "
            "then best tuning AUC, then best Youden's J" % (100 * max_post_share))
    if not feasible:
        feasible = table
        rule = "no setting met the before/after condition: best tuning AUC, then best Youden's J, among all settings"
    top = max(r["tune_auc"] for r in feasible)
    pool = [r for r in feasible if r["tune_auc"] == top]
    best = min(pool, key=lambda r: (-r["youden_j"], abs(r["threshold_db"] - DEFAULT_THRESHOLD), -r["threshold_db"]))
    return best, rule


def tune_method(inputs: TuneInputs, tune_points: list[CheckPoint], base: DetectParams,
                windows: list[int] = DEFAULT_WINDOWS, thresholds: list[float] = THRESHOLDS,
                max_post_share: float = UNLIMITED, log: Callable[[str], None] = lambda _: None) -> tuple[dict, list[dict], str]:
    """Try every (window, threshold) with the TUNING points only: the held-out half is never passed in.
    Returns (best row, table of every setting tried, the selection rule)."""
    land = project_points([p for p in tune_points if p.label == "landslide"], inputs.crs)
    forest = project_points([p for p in tune_points if p.label == "forest"], inputs.crs)
    if len(land) == 0 or len(forest) == 0:
        raise ValidationError("the tuning half needs at least one landslide point and one forest point")
    xy = np.vstack([land, forest])
    is_land = np.r_[np.ones(len(land), bool), np.zeros(len(forest), bool)]
    table: list[dict] = []
    for w in windows:
        adjusted = [_adjusted(p, w) for p in inputs.passes]
        base_adj = _adjusted(inputs.baseline, w)
        scores = point_scores(adjusted, xy, inputs.transform)
        ok = np.isfinite(scores)
        tune_auc = auc(scores[ok], is_land[ok])
        for t in thresholds:
            keep, post_rate = detect_with(inputs, adjusted, t, base)
            polys = mask_polygons(keep, inputs.transform)
            tpr = float(found_within(land, polys).mean())
            fpr = float(found_within(forest, polys).mean())
            row = {"highpass_px": int(w), "threshold_db": t, "tune_auc": round(tune_auc, 4),
                   "detection_rate": round(tpr, 4), "false_alarm_rate": round(fpr, 4), "youden_j": round(tpr - fpr, 4),
                   "baseline_flag_rate": round(baseline_flag_rate(inputs, base_adj, t, base), 5),
                   "post_flag_rate": round(float(post_rate or 0.0), 5), "objects": len(polys)}
            table.append(row)
            log(f"  window {w:>3} px, threshold {t:g} dB: AUC {row['tune_auc']:.3f}, found {100 * tpr:.0f}%, "
                f"false alarms {100 * fpr:.0f}%, flagged before {100 * row['baseline_flag_rate']:.2f}% / after {100 * row['post_flag_rate']:.2f}%")
    best, rule = choose_setting(table, max_post_share)
    return best, table, rule


def landslide_polygons(path: Path, crs) -> list:
    """Landslide polygons from the output file, in the grid's metric coordinate system."""
    data = json.loads(path.read_text(encoding="utf-8"))
    t = Transformer.from_crs(4326, crs, always_xy=True)
    polys = []
    for f in data["features"]:
        g = shape(f["geometry"])
        polys.append(shapely.transform(g, lambda c: np.column_stack(t.transform(c[:, 0], c[:, 1]))))
    return polys


def score_test(test: list[CheckPoint], polygons: list, inputs: TuneInputs, highpass_px: int, threshold_db: float) -> dict:
    """The held-out numbers: detection rate, false-alarm rate, AUC and detection by size."""
    xy = project_points(test, inputs.crs)
    is_land = np.array([p.label == "landslide" for p in test])
    found = found_within(xy, polygons)
    n_land, n_forest = int(is_land.sum()), int((~is_land).sum())
    if n_land == 0 or n_forest == 0:
        raise ValidationError("the held-out half needs at least one landslide point and one forest point")
    detection = float(found[is_land].mean())
    false_alarm = float(found[~is_land].mean())
    adjusted = [_adjusted(p, highpass_px) for p in inputs.passes]
    scores = point_scores(adjusted, xy, inputs.transform)
    covered = np.isfinite(scores)
    value = auc(scores[covered], is_land[covered])
    first = point_scores(adjusted[:1], xy, inputs.transform)                    # the primary pair alone, as a comparison
    ok1 = np.isfinite(first)
    single = auc(first[ok1], is_land[ok1])
    by_size = []
    for size in SIZES:
        sel = np.array([p.label == "landslide" and p.size == size for p in test])
        if sel.any():
            by_size.append({"size": size, "n": int(sel.sum()), "detection_rate": round(float(found[sel].mean()), 4)})
    return {
        "split": "test", "n_test_landslide": n_land, "n_test_forest": n_forest,
        "detection_rate": round(detection, 4), "false_alarm_rate": round(false_alarm, 4), "auc": round(value, 4),
        "threshold_db": float(threshold_db), "by_size": by_size,
        "points_without_radar_coverage": int((~covered).sum()), "auc_primary_pair_only": round(single, 4),
    }


# ---- the whole protocol ----

BOOKKEEPING = {"points_without_radar_coverage", "auc_primary_pair_only"}


def _read_runs(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []


def _write(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _publish(out: Path, result: dict, original: dict | None = None) -> None:
    """Put the validation block (without bookkeeping keys) into stats.json, with the first scoring beside it."""
    stats_path = out / "stats.json"
    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    if stats.get("mock"):
        raise ValidationError("stats.json is mock data: run the real processing first")
    stats["validation"] = {k: v for k, v in result.items() if k not in BOOKKEEPING}
    stats["validation_original"] = None if original is None else {k: v for k, v in original.items() if k not in BOOKKEEPING}
    _write(stats_path, stats)


def _original(root: Path, cfg: dict) -> dict | None:
    """The first scoring, kept in the repository, if the config names one."""
    rel = cfg.get("validation_original")
    path = (root / rel) if rel else None
    return json.loads(path.read_text(encoding="utf-8")) if path and path.is_file() else None


def run_tuning(cfg: dict, root: Path, work: Path | None = None, require_committed: bool = True,
               log: Callable[[str], None] = print) -> tuple[dict, list[dict], str, list[CheckPoint]]:
    """Choose the method settings with the tuning half only and save them (tuned.json). Never touches the held-out
    half's labels except to leave them out. Returns (best row, table, rule, held-out points)."""
    from .run import compare_pair_id

    root = Path(root)
    work = Path(work) if work else (root / cfg["work"]).resolve()
    points_rel = cfg["points"]
    if require_committed:
        ok, why = points_are_committed(root, points_rel)
        if not ok:
            raise ValidationError(f"{why}. Commit the check points before scoring anything (or pass --allow-uncommitted).")
    points_path = (root / points_rel).resolve()
    points = load_points(points_path)
    tune, test = split_points(points)
    log(f"{len(points)} check points: {len(tune)} for tuning, {len(test)} held out")

    inputs = load_tune_inputs(work, [p["id"] for p in cfg["pairs"]], compare_pair_id(cfg, cfg["pairs"]))
    base = DetectParams.from_config(cfg["detect"])
    tuning_cfg = cfg.get("tuning", {})
    windows = [int(w) for w in tuning_cfg.get("highpass_px", DEFAULT_WINDOWS)]
    max_share = float(tuning_cfg.get("max_post_flag_share", UNLIMITED))
    best, table, rule = tune_method(inputs, tune, base, windows, THRESHOLDS, max_share, log)
    log(f"chosen on the tuning half only: window {best['highpass_px']} px, threshold {best['threshold_db']:g} dB")
    work.mkdir(parents=True, exist_ok=True)
    _write(work / "tuned.json", {
        "threshold_db": best["threshold_db"], "highpass_px": best["highpass_px"], "seed": SEED,
        "n_tune_landslide": len([p for p in tune if p.label == "landslide"]),
        "n_tune_forest": len([p for p in tune if p.label == "forest"]),
        "points_sha256": hashlib.sha256(points_path.read_bytes()).hexdigest(), "rule": rule, "chosen": best, "table": table,
    })
    return best, table, rule, test


def run_validation(cfg: dict, root: Path, out: Path | None = None, work: Path | None = None, force: bool = False,
                   require_committed: bool = True, rerun: Callable[[], object] | None = None,
                   log: Callable[[str], None] = print) -> dict:
    """Tune on the tuning half, rerun detection, score the held-out half, write stats.json. Returns the result."""
    from .run import compare_pair_id

    root = Path(root)
    out = Path(out) if out else (root / cfg["out"]).resolve()
    work = Path(work) if work else (root / cfg["work"]).resolve()
    points_rel = cfg["points"]
    runs_file, result_file = work / "validation_runs.json", work / "validation_result.json"

    runs = _read_runs(runs_file)
    if any(r.get("scored_test") for r in runs) and not force:
        raise ValidationError("the held-out half has already been scored; scoring it again would defeat the "
                              "purpose. Use --restore to put the stored result back into stats.json, or --force "
                              "(it will be logged) if you really must.")
    best, _table, _rule, test = run_tuning(cfg, root, work, require_committed, log)
    points_path = (root / points_rel).resolve()
    inputs = load_tune_inputs(work, [p["id"] for p in cfg["pairs"]], compare_pair_id(cfg, cfg["pairs"]))

    log("rerunning detection with the chosen settings")
    if rerun is None:
        from .run import run
        rerun = lambda: run(cfg, root, out=out, work=work, log=log)  # noqa: E731
    rerun()

    polygons = landslide_polygons(out / "landslides.geojson", inputs.crs)
    runs.append({"time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "scored_test": True, "forced": bool(force),
                 "threshold_db": best["threshold_db"], "highpass_px": best["highpass_px"],
                 "points_sha256": hashlib.sha256(points_path.read_bytes()).hexdigest()})
    _write(runs_file, runs)                                       # logged before the numbers are looked at
    if result_file.is_file():
        (work / f"validation_result_{len(runs) - 1}.json").write_text(result_file.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    result = score_test(test, polygons, inputs, best["highpass_px"], best["threshold_db"])
    _write(result_file, result)
    _publish(out, result, _original(root, cfg))
    log(f"held-out half scored: found {100 * result['detection_rate']:.0f}%, false alarms {100 * result['false_alarm_rate']:.0f}%, AUC {result['auc']:.2f}")
    return result


def restore_validation(cfg: dict, root: Path, out: Path | None = None, work: Path | None = None) -> dict:
    """Put the stored held-out result back into stats.json, for example after the processing was rerun."""
    root = Path(root)
    out = Path(out) if out else (root / cfg["out"]).resolve()
    work = Path(work) if work else (root / cfg["work"]).resolve()
    result_file = work / "validation_result.json"
    if not result_file.is_file():
        raise ValidationError("there is no stored result: validation has not been run yet")
    result = json.loads(result_file.read_text(encoding="utf-8"))
    _publish(out, result, _original(root, cfg))
    return result
