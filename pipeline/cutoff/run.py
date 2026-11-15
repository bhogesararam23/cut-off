"""Orchestrate the radar processing: pairs, baseline, time series, and every output file.

Only one pair's full-size arrays are in memory at a time; what is kept between pairs is small
(yes/no masks and float16 dB images for the statistics).
Roads and communities are not made here: the files are written empty, so no mock content is left behind.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Callable

import numpy as np
from rasterio.enums import Resampling

from . import export
from .detect import (DetectParams, adjusted_change, candidate_mask, combine_votes, eligible_mask, flag_rate,
                     otsu_threshold, polygonise, remove_small_patches, visible_mask)
from .radar import align_to, median_speckle, power_to_db, read_raster, reference_grid, write_raster, Raster
from .terrain import look_azimuth, shadow_layover, slope_aspect


def _path(root: Path, rel: str) -> Path:
    return (root / rel).resolve()


def select_pairs(cfg: dict, pair_ids: list[str] | None) -> list[dict]:
    """Pairs to process, primary first. Unknown ids are an error."""
    pairs = cfg["pairs"]
    if pair_ids:
        unknown = set(pair_ids) - {p["id"] for p in pairs}
        if unknown:
            raise ValueError(f"unknown pair id(s): {sorted(unknown)}")
        pairs = [p for p in pairs if p["id"] in pair_ids]
    if not any(p["id"] == cfg["primary_pair"] for p in pairs):
        raise ValueError(f"the primary pair {cfg['primary_pair']} must be processed (it defines the grid)")
    return sorted(pairs, key=lambda p: p["id"] != cfg["primary_pair"])


def compare_pair_id(cfg: dict, pairs: list[dict]) -> str:
    """The after-the-quake pair the no-quake baseline is compared with: the one from the same track and direction
    (same viewing geometry), else the primary pair."""
    b = cfg["baseline"]
    for p in pairs:
        if p["track"] == b.get("track") and p["direction"] == b["direction"]:
            return p["id"]
    return pairs[0]["id"]


def required_inputs(cfg: dict, pairs: list[dict]) -> list[str]:
    files = [cfg["dem"]]
    for p in pairs:
        files += [p["before_hv"], p["after_hv"]]
    files += [cfg["baseline"]["before_hv"], cfg["baseline"]["after_hv"]]
    return files


def missing_inputs(cfg: dict, root: Path, pairs: list[dict]) -> list[str]:
    return [f for f in required_inputs(cfg, pairs) if not _path(root, f).is_file()]


def _series_entries(cfg: dict, pairs: list[dict]) -> list[dict]:
    """Every pass we have an image for: the configured series, each pair's two dates, and the baseline's."""
    entries: dict[str, dict] = {}
    for s in cfg.get("series", []):
        entries[s["date"]] = {"date": s["date"], "track": s["track"], "direction": s["direction"], "hv": s["hv"]}
    for p in pairs:
        for when, key in ((p["before"], "before_hv"), (p["after"], "after_hv")):
            entries.setdefault(when, {"date": when, "track": p["track"], "direction": p["direction"], "hv": p[key]})
    b = cfg["baseline"]
    if "before" in b and "after" in b:
        for when, key in ((b["before"], "before_hv"), (b["after"], "after_hv")):
            entries.setdefault(when, {"date": when, "track": b.get("track"), "direction": b["direction"], "hv": b[key]})
    return sorted((e for e in entries.values() if e["track"] is not None), key=lambda e: e["date"])


def run(cfg: dict, root: Path, out: Path | None = None, work: Path | None = None, pair_ids: list[str] | None = None,
        clean: bool = False, use_tuned: bool = True, log: Callable[[str], None] = print) -> dict:
    """Process the configured pairs and write every output file. Returns a short summary."""
    root = Path(root)
    out = Path(out) if out else _path(root, cfg["out"])
    work = Path(work) if work else _path(root, cfg["work"])
    pairs = select_pairs(cfg, pair_ids)
    missing = missing_inputs(cfg, root, pairs)
    if missing:
        raise FileNotFoundError("these input files are missing (download them first):\n  " + "\n  ".join(missing))

    params = DetectParams.from_config(cfg["detect"])
    tuned_file = work / "tuned.json"
    if use_tuned and tuned_file.is_file():
        # the threshold chosen on the tuning half of the check points replaces the starting value
        saved = json.loads(tuned_file.read_text(encoding="utf-8"))
        tuned = float(saved["threshold_db"])
        params = replace(params, threshold_db=tuned, highpass_px=int(saved.get("highpass_px", params.highpass_px)))
        log(f"using the tuned threshold {tuned:g} dB from the tuning step"
            + (f" and a local-mean window of {params.highpass_px} pixels" if params.highpass_px > 1 else ""))
    res = float(cfg["target_res_m"])
    fsize, incidence = int(cfg["filter_size"]), float(cfg["incidence_deg"])
    headings = cfg.get("headings", {})
    bbox = cfg["bbox"]
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    if clean:
        for old in out.glob("hv_*.png"):
            old.unlink()

    # reference grid from the primary pair's "before" image, then terrain on that grid
    primary = pairs[0]
    ref = read_raster(_path(root, primary["before_hv"]))
    shape, transform, crs = reference_grid(ref, res)
    del ref
    log(f"grid {shape[1]} x {shape[0]} pixels of {res:g} m ({crs.to_string()})")
    dem = align_to(read_raster(_path(root, cfg["dem"])), shape, transform, crs, Resampling.bilinear)
    slope, aspect = slope_aspect(dem.data, res, res)
    del dem
    write_raster(work / "slope.tif", Raster(slope, transform, crs))          # kept so the threshold can be tuned later

    unknown_by_dir: dict[str, np.ndarray] = {}

    def unknown_for(direction: str) -> np.ndarray:
        if direction not in unknown_by_dir:
            unknown_by_dir[direction] = shadow_layover(slope, aspect, look_azimuth(direction, headings.get(direction)), incidence)
        return unknown_by_dir[direction]

    def load_db(rel: str) -> np.ndarray:
        aligned = align_to(read_raster(_path(root, rel)), shape, transform, crs)      # average the power first
        return median_speckle(power_to_db(aligned.data), fsize)

    cands, visibles, before16, after16, entries = [], [], [], [], []
    db_cache: dict[str, np.ndarray] = {}
    otsu_first_guess = None
    post_rate = None
    compare_id = compare_pair_id(cfg, pairs)
    for p in pairs:
        before, after = load_db(p["before_hv"]), load_db(p["after_hv"])
        dhv = (after - before).astype("float32")
        unknown = unknown_for(p["direction"])
        vis = visible_mask(before, after, unknown)
        adj = adjusted_change(dhv, vis, params.highpass_px)                  # the change that detection looks at
        cand = candidate_mask(adj, before, slope, unknown, params)
        elig = eligible_mask(before, slope, vis, params)
        if p["id"] == compare_id or p is primary:                            # primary is the fallback if the compare pair is not run
            post_rate = flag_rate(cand, elig)
        if p is primary:
            otsu_first_guess = otsu_threshold(adj, elig)
        write_raster(work / f"dhv_{p['id']}.tif", Raster(dhv, transform, crs))             # inputs for tuning and scoring
        write_raster(work / f"hvbefore_{p['id']}.tif", Raster(before, transform, crs))
        write_raster(work / f"unknown_{p['id']}.tif", Raster(unknown.astype("float32"), transform, crs))
        names = export.png_names(p)
        export.save_png(out / names["before_png"], export.png_hv(export.to_wgs84(before, transform, crs, bbox, res)))
        export.save_png(out / names["after_png"], export.png_hv(export.to_wgs84(after, transform, crs, bbox, res)))
        export.save_png(out / names["change_png"], export.png_change(export.to_wgs84(dhv, transform, crs, bbox, res)))
        cands.append(cand)
        visibles.append(vis)
        before16.append(before.astype("float16"))
        after16.append(after.astype("float16"))
        db_cache[p["before_hv"]], db_cache[p["after_hv"]] = before16[-1], after16[-1]
        entries.append(export.pair_entry(p, bbox, int(cand.sum())))
        log(f"pair {p['id']}: {int(cand.sum())} candidate pixels, {100 * float(vis.mean()):.1f}% of the grid visible")
        del before, after, dhv

    # baseline: the same detection on two passes from before the quake
    b = cfg["baseline"]
    b_before, b_after = load_db(b["before_hv"]), load_db(b["after_hv"])
    b_unknown = unknown_for(b["direction"])
    b_vis = visible_mask(b_before, b_after, b_unknown)
    b_dhv = (b_after - b_before).astype("float32")
    b_cand = candidate_mask(adjusted_change(b_dhv, b_vis, params.highpass_px), b_before, slope, b_unknown, params)
    baseline_rate = flag_rate(b_cand, eligible_mask(b_before, slope, b_vis, params))
    write_raster(work / "dhv_baseline.tif", Raster(b_dhv, transform, crs))
    write_raster(work / "hvbefore_baseline.tif", Raster(b_before, transform, crs))
    write_raster(work / "unknown_baseline.tif", Raster(b_unknown.astype("float32"), transform, crs))
    del b_before, b_after, b_vis, b_cand, b_dhv

    # combine the pairs and make polygons
    keep, _, _ = combine_votes(cands, visibles)
    keep = remove_small_patches(keep, params.min_pixels)          # after voting, small leftovers are dropped too
    slides = polygonise(keep, cands, visibles, before16, after16, slope, transform)
    features = export.landslide_features(slides, crs, res)
    unknown_all = ~np.any(visibles, axis=0)
    unknown_feats = export.unknown_features(unknown_all, transform, crs, res)

    # time series: mean HV at landslides vs intact forest slopes, for every pass we have
    series = []
    forest_base = (slope >= params.min_slope_deg) & (before16[0] >= params.min_forest_hv_db) & ~keep
    if keep.any():
        for s in _series_entries(cfg, pairs):
            if not _path(root, s["hv"]).is_file():
                log(f"series: skipping {s['date']} (file missing)")
                continue
            db = db_cache.get(s["hv"])
            if db is None:
                db = load_db(s["hv"]).astype("float16")
            seen = np.isfinite(db) & ~unknown_for(s["direction"])
            land, forest = db[keep & seen].astype("float64"), db[forest_base & seen].astype("float64")
            if land.size and forest.size:
                series.append({"date": s["date"], "track": int(s["track"]), "direction": s["direction"],
                               "hv_landslide_db": round(float(land.mean()), 1), "hv_forest_db": round(float(forest.mean()), 1)})
    else:
        log("no landslides found: the time series is left empty")

    # write everything
    export.write_json(out / "event.json", {
        "event_id": cfg["event_id"], "name": cfg["name"], "time_utc": cfg["time_utc"], "epicentre": cfg["epicentre"],
        "bbox": bbox, "maturity": cfg["maturity"], "mock": False,
        "optical": export.optical_entry(cfg, out), "references": cfg["references"]})
    export.write_json(out / "pairs.json", entries)
    export.write_json(out / "landslides.geojson", export.feature_collection(features), compact=True)
    export.write_json(out / "unknown.geojson", export.feature_collection(unknown_feats), compact=True)
    export.write_json(out / "roads.geojson", export.feature_collection([]), compact=True)
    export.write_json(out / "communities.geojson", export.feature_collection([]), compact=True)
    area_km2 = round(sum(f["properties"]["area_m2"] for f in features) / 1e6, 3)
    export.write_json(out / "stats.json", {
        "mock": False, "landslides": len(features), "area_km2": area_km2, "roads_blocked_km": None,
        "communities_cut_off": None, "validation": None, "validation_original": None,
        "baseline_no_change_flag_rate": round(baseline_rate, 5), "post_event_flag_rate": round(post_rate, 5),
        "params": {"threshold_db": params.threshold_db, "min_slope_deg": params.min_slope_deg,
                   "min_forest_hv_db": params.min_forest_hv_db, "min_pixels": params.min_pixels,
                   "highpass_px": params.highpass_px},
        "pixel_m": res})
    export.write_json(out / "timeseries.json", series)
    export.write_json(out / "timeline.json", export.default_timeline(cfg))

    referenced = {e[k] for e in entries for k in ("before_png", "after_png", "change_png")}
    stale = sorted(f.name for f in out.glob("hv_*.png") if f.name not in referenced)
    if stale:
        log(f"warning: {len(stale)} image file(s) in the output folder are not used by this run "
            f"(old or mock files); rerun with --clean to remove them: {', '.join(stale[:3])}...")

    return {
        "pairs": {e["id"]: e["flagged_pixels"] for e in entries},
        "landslides": len(features), "area_km2": area_km2,
        "baseline_flag_rate": baseline_rate, "post_event_flag_rate": post_rate,
        "otsu_first_guess_db": otsu_first_guess, "threshold_db": params.threshold_db, "stale_files": stale,
    }
