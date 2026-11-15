"""Check that a folder of output files follows the agreed data format.

The web app and the API read these files as they are, so keys and types must match exactly:
no missing keys, no extra keys, missing values are null. `check_dir` returns a list of problems
(empty list = all good).
"""

from __future__ import annotations

import json
import math
import re
import struct
from pathlib import Path
from typing import Any, Callable

PAIR_IDS = ("t141d", "t4a", "t40d", "t76a")
DIRECTIONS = ("ascending", "descending")
CONFIDENCES = ("high", "medium", "low")
ROAD_STATUSES = ("blocked", "at_risk", "clear", "unknown")
COMMUNITY_STATUSES = ("cut_off", "reachable", "unknown")
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
LANDSLIDE_ID = re.compile(r"^L\d{4,}$")
MAX_PNG_SIDE = 2048

Check = Callable[[Any], "str | None"]


# ---- small validators: each returns None when fine, else a short message ----

def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def is_str(v: Any) -> str | None:
    return None if isinstance(v, str) else f"expected string, got {type(v).__name__}"


def is_str_or_null(v: Any) -> str | None:
    return None if v is None or isinstance(v, str) else "expected string or null"


def is_num(v: Any) -> str | None:
    return None if _num(v) else "expected number"


def is_num_or_null(v: Any) -> str | None:
    return None if v is None or _num(v) else "expected number or null"


def is_int(v: Any) -> str | None:
    return None if isinstance(v, int) and not isinstance(v, bool) else "expected integer"


def is_int_or_null(v: Any) -> str | None:
    return None if v is None or (isinstance(v, int) and not isinstance(v, bool)) else "expected integer or null"


def is_bool(v: Any) -> str | None:
    return None if isinstance(v, bool) else "expected true or false"


def is_iso(v: Any) -> str | None:
    return None if isinstance(v, str) and ISO_UTC.match(v) else "expected ISO 8601 UTC time like 2026-10-09T17:56:00Z"


def one_of(*allowed: str) -> Check:
    return lambda v: None if v in allowed else f"expected one of {list(allowed)}"


def int_between(lo: int, hi: int) -> Check:
    return lambda v: None if isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi else f"expected integer {lo}-{hi}"


def is_lonlat(v: Any) -> str | None:
    if not (isinstance(v, list) and len(v) == 2 and all(_num(x) for x in v)):
        return "expected [lon, lat]"
    if not (-180 <= v[0] <= 180 and -90 <= v[1] <= 90):
        return "lon/lat out of range"
    return None


def list_of(item: Check) -> Check:
    def run(v: Any) -> str | None:
        if not isinstance(v, list):
            return "expected a list"
        for i, x in enumerate(v):
            m = item(x)
            if m:
                return f"item {i}: {m}"
        return None

    return run


def is_bbox(v: Any) -> str | None:
    if not (isinstance(v, list) and len(v) == 4 and all(_num(x) for x in v)):
        return "expected [west, south, east, north]"
    return None if v[0] < v[2] and v[1] < v[3] else "bbox must be west < east and south < north"


def is_bounds(v: Any) -> str | None:
    """Four corners in MapLibre image order: top-left, top-right, bottom-right, bottom-left."""
    if not (isinstance(v, list) and len(v) == 4 and all(is_lonlat(p) is None for p in v)):
        return "expected four [lon, lat] corners"
    tl, tr, br, bl = v
    ok = tl[0] == bl[0] and tr[0] == br[0] and tl[1] == tr[1] and bl[1] == br[1] and tl[0] < tr[0] and bl[1] < tl[1]
    return None if ok else "corners must be top-left, top-right, bottom-right, bottom-left"


def exact_keys(obj: Any, spec: dict[str, Check], where: str, errors: list[str]) -> bool:
    """Require exactly the keys in spec, each passing its validator. Returns True if the shape is fine."""
    if not isinstance(obj, dict):
        errors.append(f"{where}: expected an object")
        return False
    ok = True
    for key in spec:
        if key not in obj:
            errors.append(f"{where}: missing key '{key}'")
            ok = False
    for key in obj:
        if key not in spec:
            errors.append(f"{where}: unexpected key '{key}'")
            ok = False
    for key, check in spec.items():
        if key in obj:
            msg = check(obj[key])
            if msg:
                errors.append(f"{where}.{key}: {msg}")
                ok = False
    return ok


# ---- shapes of each file ----

EVENT = {
    "event_id": is_str, "name": is_str, "time_utc": is_iso, "epicentre": is_lonlat, "bbox": is_bbox,
    "maturity": is_str, "mock": is_bool, "optical": lambda v: None,
    "references": list_of(lambda r: None if isinstance(r, dict) and set(r) == {"label", "url"}
                          and all(isinstance(x, str) for x in r.values()) else "expected {label, url}"),
}
PAIR = {
    "id": one_of(*PAIR_IDS), "track": is_int, "direction": one_of(*DIRECTIONS), "before": is_iso, "after": is_iso,
    "before_png": is_str, "after_png": is_str, "change_png": is_str, "bounds": is_bounds,
    "granules": list_of(is_str), "flagged_pixels": is_int,
}
LANDSLIDE = {
    "id": is_str, "area_m2": is_num, "hv_before_db": is_num, "hv_after_db": is_num, "dhv_db": is_num,
    "slope_deg": is_num, "pairs_seen": int_between(0, 4), "pairs_visible": int_between(0, 4),
    "confidence": one_of(*CONFIDENCES),
}
ROAD = {
    "osm_id": is_str_or_null, "name": is_str_or_null, "highway": is_str_or_null,
    "status": one_of(*ROAD_STATUSES), "min_distance_m": is_num_or_null, "landslide_ids": is_str,
}
COMMUNITY = {
    "osm_id": is_str_or_null, "name": is_str, "place": is_str, "population": is_int_or_null,
    "status": one_of(*COMMUNITY_STATUSES), "nearest_hub": is_str_or_null, "reason": is_str,
}
OPTICAL = {"before_webp": is_str, "after_webp": is_str, "bounds": is_bounds, "before_caption": is_str,
           "after_caption": is_str, "attribution": is_str}
STATS_PARAMS = {"threshold_db": is_num, "min_slope_deg": is_num, "min_forest_hv_db": is_num, "min_pixels": is_int,
                "highpass_px": is_int}
STATS_BY_SIZE = {"size": one_of("small", "medium", "large"), "n": is_int, "detection_rate": is_num}
STATS_VALIDATION = {
    "split": one_of("test"), "n_test_landslide": is_int, "n_test_forest": is_int,
    "detection_rate": is_num, "false_alarm_rate": is_num, "auc": is_num, "threshold_db": is_num,
    "by_size": list_of(lambda x: None if isinstance(x, dict) and not _shape(x, STATS_BY_SIZE) else "bad by_size item"),
}
STATS = {
    "mock": is_bool, "landslides": is_int, "area_km2": is_num, "roads_blocked_km": is_num_or_null,
    "communities_cut_off": is_int_or_null, "validation": lambda v: None, "validation_original": lambda v: None,
    "baseline_no_change_flag_rate": is_num,
    "post_event_flag_rate": is_num, "params": lambda v: None, "pixel_m": is_num,
}
TIMESERIES = {"date": is_iso, "track": is_int, "direction": one_of(*DIRECTIONS),
              "hv_landslide_db": is_num, "hv_forest_db": is_num}
TIMELINE = {"time_utc": is_iso, "label": is_str, "source": is_str}


def _shape(obj: Any, spec: dict[str, Check]) -> list[str]:
    errs: list[str] = []
    exact_keys(obj, spec, "item", errs)
    return errs


# ---- geometry helpers ----

def _coords(geom: dict) -> list:
    out: list = []

    def walk(c: Any) -> None:
        if c and isinstance(c[0], (int, float)):
            out.append(c)
        else:
            for x in c:
                walk(x)

    walk(geom.get("coordinates", []))
    return out


def _check_geometry(geom: Any, kinds: tuple[str, ...], where: str, errors: list[str]) -> None:
    if not isinstance(geom, dict) or geom.get("type") not in kinds:
        errors.append(f"{where}: geometry must be one of {list(kinds)}")
        return
    pts = _coords(geom)
    if not pts:
        errors.append(f"{where}: geometry has no coordinates")
    for p in pts:
        if len(p) != 2 or not all(_num(x) for x in p) or is_lonlat(list(p)):
            errors.append(f"{where}: bad coordinate {p}")
            return
        if round(p[0], 6) != p[0] or round(p[1], 6) != p[1]:
            errors.append(f"{where}: coordinates must have at most 6 decimals ({p})")
            return
    if geom["type"] in ("Polygon", "MultiPolygon"):
        rings = geom["coordinates"] if geom["type"] == "Polygon" else [r for poly in geom["coordinates"] for r in poly]
        for r in rings:
            if len(r) < 4 or r[0] != r[-1]:
                errors.append(f"{where}: polygon ring must be closed with at least 4 points")
                return


def _feature_collection(data: Any, kinds: tuple[str, ...], props: dict[str, Check] | None,
                        name: str, errors: list[str]) -> list[dict]:
    if not (isinstance(data, dict) and data.get("type") == "FeatureCollection" and isinstance(data.get("features"), list)):
        errors.append(f"{name}: expected a GeoJSON FeatureCollection")
        return []
    feats = []
    for i, f in enumerate(data["features"]):
        where = f"{name} feature {i}"
        if not (isinstance(f, dict) and f.get("type") == "Feature" and "geometry" in f and "properties" in f):
            errors.append(f"{where}: expected a Feature with geometry and properties")
            continue
        _check_geometry(f["geometry"], kinds, where, errors)
        if props is not None:
            exact_keys(f["properties"], props, where + " properties", errors)
        elif not isinstance(f["properties"], dict):
            errors.append(f"{where}: properties must be an object")
        feats.append(f)
    return feats


def _png_size(path: Path) -> tuple[int, int] | None:
    try:
        with path.open("rb") as fh:
            head = fh.read(24)
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return struct.unpack(">II", head[16:24])
    except OSError:
        return None


# ---- per-file checks ----

def _load(folder: Path, name: str, errors: list[str]) -> Any:
    p = folder / name
    if not p.is_file():
        errors.append(f"{name}: file is missing")
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        errors.append(f"{name}: not valid JSON ({e})")
        return None


def _confidence_ok(seen: int, visible: int, conf: str) -> bool:
    if seen >= 2 and seen >= visible - 1:
        return conf == "high"
    if seen >= 2:
        return conf == "medium"
    return conf == "low"


def check_dir(folder: str | Path) -> list[str]:
    """Return a list of problems found in the output folder (empty list = follows the data format)."""
    folder = Path(folder)
    errors: list[str] = []
    if not folder.is_dir():
        return [f"{folder}: folder does not exist"]

    event = _load(folder, "event.json", errors)
    if event is not None:
        if exact_keys(event, EVENT, "event.json", errors) and event["optical"] is not None:
            if exact_keys(event["optical"], OPTICAL, "event.json.optical", errors):
                for key in ("before_webp", "after_webp"):
                    if not (folder / event["optical"][key]).is_file():
                        errors.append(f"event.json.optical.{key}: file '{event['optical'][key]}' is missing")

    pairs = _load(folder, "pairs.json", errors)
    if pairs is not None:
        if not isinstance(pairs, list):
            errors.append("pairs.json: expected an array")
        else:
            seen_ids: set[str] = set()
            for i, p in enumerate(pairs):
                where = f"pairs.json[{i}]"
                if not exact_keys(p, PAIR, where, errors):
                    continue
                if p["id"] in seen_ids:
                    errors.append(f"{where}: duplicate pair id {p['id']}")
                seen_ids.add(p["id"])
                want = {
                    "before_png": f"hv_{p['id']}_{p['before'][:10].replace('-', '')}.png",
                    "after_png": f"hv_{p['id']}_{p['after'][:10].replace('-', '')}.png",
                    "change_png": f"hv_change_{p['id']}.png",
                }
                for key, expected in want.items():
                    if p[key] != expected:
                        errors.append(f"{where}.{key}: expected file name {expected}")
                    size = _png_size(folder / p[key])
                    if size is None:
                        errors.append(f"{where}.{key}: PNG file '{p[key]}' is missing or not a PNG")
                    elif max(size) > MAX_PNG_SIDE:
                        errors.append(f"{where}.{key}: PNG longer side {max(size)} px exceeds {MAX_PNG_SIDE}")

    ids: set[str] = set()
    data = _load(folder, "landslides.geojson", errors)
    if data is not None:
        for f in _feature_collection(data, ("Polygon", "MultiPolygon"), LANDSLIDE, "landslides.geojson", errors):
            pr = f["properties"]
            if not isinstance(pr.get("id"), str) or not LANDSLIDE_ID.match(pr["id"]):
                errors.append(f"landslides.geojson: id {pr.get('id')!r} should look like L0001")
            elif pr["id"] in ids:
                errors.append(f"landslides.geojson: duplicate id {pr['id']}")
            else:
                ids.add(pr["id"])
            seen, vis, conf = pr.get("pairs_seen"), pr.get("pairs_visible"), pr.get("confidence")
            if all(isinstance(x, int) and not isinstance(x, bool) for x in (seen, vis)):
                if seen > vis:
                    errors.append(f"landslides.geojson {pr.get('id')}: pairs_seen is larger than pairs_visible")
                elif conf in CONFIDENCES and not _confidence_ok(seen, vis, conf):
                    errors.append(f"landslides.geojson {pr.get('id')}: confidence '{conf}' does not follow the rule "
                                  f"(seen {seen}, visible {vis})")

    data = _load(folder, "unknown.geojson", errors)
    if data is not None:
        _feature_collection(data, ("Polygon", "MultiPolygon"), None, "unknown.geojson", errors)

    data = _load(folder, "roads.geojson", errors)
    if data is not None:
        for f in _feature_collection(data, ("LineString", "MultiLineString"), ROAD, "roads.geojson", errors):
            pr = f["properties"]
            st, d = pr.get("status"), pr.get("min_distance_m")
            if _num(d):
                if st == "blocked" and d > 10:
                    errors.append(f"roads.geojson: a blocked road is {d} m from a landslide (limit 10 m)")
                if st == "at_risk" and not 10 < d <= 100:
                    errors.append(f"roads.geojson: an at_risk road is {d} m from a landslide (expected 10-100 m)")
                if st == "clear" and d <= 100:
                    errors.append(f"roads.geojson: a clear road is {d} m from a landslide (expected over 100 m)")
            elif st in ("blocked", "at_risk"):
                errors.append(f"roads.geojson: a {st} road needs min_distance_m")
            if isinstance(pr.get("landslide_ids"), str) and ids:
                for lid in filter(None, pr["landslide_ids"].split(",")):
                    if lid not in ids:
                        errors.append(f"roads.geojson: landslide_ids mentions unknown id {lid}")

    data = _load(folder, "communities.geojson", errors)
    if data is not None:
        _feature_collection(data, ("Point",), COMMUNITY, "communities.geojson", errors)

    stats = _load(folder, "stats.json", errors)
    if stats is not None and exact_keys(stats, STATS, "stats.json", errors):
        exact_keys(stats["params"], STATS_PARAMS, "stats.json.params", errors)
        for key in ("validation", "validation_original"):
            block = stats[key]
            if block is None:
                continue
            if exact_keys(block, {**STATS_VALIDATION, "by_size": lambda v: None}, f"stats.json.{key}", errors):
                if not isinstance(block["by_size"], list):
                    errors.append(f"stats.json.{key}.by_size: expected a list")
                else:
                    for i, item in enumerate(block["by_size"]):
                        exact_keys(item, STATS_BY_SIZE, f"stats.json.{key}.by_size[{i}]", errors)
        if event is not None and isinstance(event, dict) and event.get("mock") != stats["mock"]:
            errors.append("stats.json.mock and event.json.mock must be equal")

    for name, spec in (("timeseries.json", TIMESERIES), ("timeline.json", TIMELINE)):
        data = _load(folder, name, errors)
        if data is not None:
            if not isinstance(data, list):
                errors.append(f"{name}: expected an array")
            else:
                for i, item in enumerate(data):
                    exact_keys(item, spec, f"{name}[{i}]", errors)

    return errors
