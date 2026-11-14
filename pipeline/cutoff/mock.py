"""Write synthetic output files so the API and the web app can be built before real results exist.

Everything here is made up. Every file that can carry the flag has "mock": true, names are labelled
"Mock ...", and the images are random texture. The output is deterministic (fixed seed).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
from shapely.geometry import LineString, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

SEED = 2026
LON0, LAT0 = -80.87, 7.48            # centre of the mock landslide cluster
KLAT = 110_574.0                      # metres per degree of latitude (local approximation)
KLON = 111_320.0 * math.cos(math.radians(LAT0))
N_LANDSLIDES = 25
IMG = 768                             # side of each synthetic PNG, in pixels
QUAKE_UTC = "2026-10-09T17:56:00Z"


def r6(v: float) -> float:
    return round(float(v), 6)


def _metres(coords) -> list[tuple[float, float]]:
    return [((lon - LON0) * KLON, (lat - LAT0) * KLAT) for lon, lat in coords]


def _write_json(path: Path, data, compact: bool = False) -> None:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")) if compact else json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def confidence(seen: int, visible: int) -> str:
    if seen >= 2 and seen >= visible - 1:
        return "high"
    if seen >= 2:
        return "medium"
    return "low"


def _blob(rng: np.random.Generator, lon: float, lat: float, area_m2: float) -> list[list[float]]:
    """A closed, counter-clockwise, star-shaped ring around (lon, lat) with roughly the given area."""
    r = math.sqrt(area_m2 / math.pi)
    a = r * rng.uniform(1.1, 1.7)
    b = area_m2 / (math.pi * a)
    rot = rng.uniform(0, math.pi)
    n = 10
    ang = np.linspace(0, 2 * math.pi, n, endpoint=False) + rng.uniform(-0.15, 0.15, n)
    f = 1 + rng.uniform(-0.15, 0.15, n)
    x = a * f * np.cos(ang)
    y = b * f * np.sin(ang)
    xr = x * math.cos(rot) - y * math.sin(rot)
    yr = x * math.sin(rot) + y * math.cos(rot)
    ring = [[r6(lon + xr[i] / KLON), r6(lat + yr[i] / KLAT)] for i in range(n)]
    ring.append(ring[0])
    return ring


def _landslides(seed: int) -> list[dict]:
    rng = np.random.default_rng([seed, 1])
    feats = []
    for i in range(N_LANDSLIDES):
        lon = LON0 + rng.normal(0, 0.035)
        lat = LAT0 + rng.normal(0, 0.035)
        area = float(np.clip(math.exp(rng.normal(math.log(50_000), 0.6)), 8_000, 250_000))
        ring = _blob(rng, lon, lat, area)
        poly = orient(Polygon(_metres(ring)), 1.0)
        visible = int(rng.choice([2, 3, 4, 4, 3, 1]))
        if i == 0:
            visible = 1                       # guarantees a "low" example
        elif i == 1:
            visible = 4
        seen = 1 if visible == 1 else int(rng.integers(2, visible + 1))
        if i == 1:
            seen = 2                          # guarantees a "medium" example
        before = round(float(rng.normal(-12.5, 0.8)), 1)
        dhv = round(-float(rng.uniform(3.5, 8.0)), 1)
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {
                "id": f"L{i + 1:04d}",
                "area_m2": round(poly.area, 1),
                "hv_before_db": before,
                "hv_after_db": round(before + dhv, 1),
                "dhv_db": dhv,
                "slope_deg": round(float(rng.uniform(14, 38)), 1),
                "pairs_seen": seen,
                "pairs_visible": visible,
                "confidence": confidence(seen, visible),
            },
        })
    return feats


def _unknown_areas() -> list[dict]:
    boxes = [
        [(-80.935, 7.515), (-80.905, 7.515), (-80.905, 7.56), (-80.935, 7.56)],
        [(-80.805, 7.62), (-80.755, 7.62), (-80.755, 7.65), (-80.805, 7.65)],
        [(-80.62, 7.36), (-80.57, 7.36), (-80.57, 7.40), (-80.62, 7.40)],
    ]
    feats = []
    for b in boxes:
        ring = [[r6(x), r6(y)] for x, y in b] + [[r6(b[0][0]), r6(b[0][1])]]
        feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]}, "properties": {}})
    return feats


def _road_lines(landslides: list[dict]) -> list[tuple[str, str, list[tuple[float, float]]]]:
    """Hand-placed mock roads: one through a landslide, one close to another, one far away, one in an unseen area."""
    polys = [orient(Polygon(_metres(f["geometry"]["coordinates"][0])), 1.0) for f in landslides]
    c = polys[3].centroid
    c_lon, c_lat = LON0 + c.x / KLON, LAT0 + c.y / KLAT
    through = [(c_lon - 0.02, c_lat - 0.004), (c_lon, c_lat), (c_lon + 0.02, c_lat + 0.004)]

    big = max(range(len(polys)), key=lambda i: polys[i].area if i != 3 else 0)
    minx, miny, maxx, maxy = polys[big].bounds
    y_near = maxy + 55.0                  # 55 m north of the polygon's northern edge
    cx = (minx + maxx) / 2
    near = [(LON0 + (cx - 300) / KLON, LAT0 + y_near / KLAT), (LON0 + (cx + 300) / KLON, LAT0 + y_near / KLAT)]

    return [
        ("Mock Road 1", "primary", through),
        ("Mock Road 2", "secondary", near),
        ("Mock Road 3", "tertiary", [(-80.55, 7.40), (-80.50, 7.45), (-80.45, 7.50)]),
        ("Mock Road 4", "track", [(-80.795, 7.635), (-80.765, 7.635)]),
        ("Mock Road 5", "secondary", [(-80.95, 7.35), (-80.75, 7.55), (-80.50, 7.75)]),
        ("Mock Road 6", "tertiary", [(-80.65, 7.90), (-80.55, 7.80), (-80.42, 7.74)]),
        ("Mock Road 7", "track", [(-80.99, 7.62), (-80.93, 7.66), (-80.88, 7.72)]),
    ]


def _roads(landslides: list[dict], unknown: list[dict]) -> list[dict]:
    ls = [(f["properties"]["id"], orient(Polygon(_metres(f["geometry"]["coordinates"][0])), 1.0)) for f in landslides]
    unk = unary_union([Polygon(_metres(f["geometry"]["coordinates"][0])) for f in unknown])
    feats = []
    for name, highway, pts in _road_lines(landslides):
        coords = [[r6(x), r6(y)] for x, y in pts]
        line = LineString(_metres(coords))
        dists = [(lid, line.distance(p)) for lid, p in ls]
        dmin = min(d for _, d in dists)
        near_ids = ",".join(lid for lid, d in dists if d <= 100)
        unknown_share = line.intersection(unk).length / line.length if line.length else 0.0
        if dmin <= 10:
            status = "blocked"
        elif dmin <= 100:
            status = "at_risk"
        elif unknown_share >= 0.5:
            status = "unknown"
        else:
            status = "clear"
        feats.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "osm_id": None, "name": name, "highway": highway, "status": status,
                "min_distance_m": round(dmin, 1), "landslide_ids": near_ids,
            },
            "_length_m": line.length,         # removed before writing
        })
    return feats


def _communities(roads: list[dict]) -> list[dict]:
    by_name = {f["properties"]["name"]: f for f in roads}
    end1 = by_name["Mock Road 1"]["geometry"]["coordinates"][-1]
    rows = [
        ("Mock Village A", "village", 150, "cut_off", "Tonosí", [end1[0] + 0.004, end1[1] + 0.002]),
        ("Mock Village B", "village", None, "reachable", "Macaracas", [-80.50, 7.45]),
        ("Mock Town C", "town", 2400, "reachable", "Chitré", [-80.45, 7.74]),
        ("Mock Hamlet D", "hamlet", None, "unknown", None, [-80.78, 7.636]),
        ("Mock Village E", "village", 80, "cut_off", "Santiago", [-80.885, 7.72]),
        ("Mock Village F", "village", None, "unknown", None, [-80.60, 7.38]),
    ]
    reasons = {
        "cut_off": "Mock data: every mapped road to {hub} crosses a likely-blocked stretch.",
        "reachable": "Mock data: a mapped road to {hub} stays clear of detected landslides.",
        "unknown": "Mock data: no usable mapped road nearby, so access is unknown.",
    }
    feats = []
    for name, place, pop, status, hub, (lon, lat) in rows:
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r6(lon), r6(lat)]},
            "properties": {
                "osm_id": None, "name": name, "place": place, "population": pop, "status": status,
                "nearest_hub": hub, "reason": reasons[status].format(hub=hub),
            },
        })
    return feats


def _timeseries(cfg: dict, seed: int) -> list[dict]:
    rng = np.random.default_rng([seed, 2])
    passes = [
        ("2026-09-20T23:45:16Z", 40, "descending"), ("2026-09-27T23:53:35Z", 141, "descending"),
        ("2026-09-30T11:04:20Z", 4, "ascending"), ("2026-10-02T23:45:16Z", 40, "descending"),
        ("2026-10-05T10:56:04Z", 76, "ascending"), ("2026-10-09T23:53:35Z", 141, "descending"),
        ("2026-10-12T11:04:20Z", 4, "ascending"), ("2026-10-14T23:45:16Z", 40, "descending"),
        ("2026-10-17T10:56:04Z", 76, "ascending"),
    ]
    out = []
    for date, track, direction in passes:
        after = date > cfg["time_utc"]
        land = (-18.1 if after else -13.1) + float(rng.normal(0, 0.3))
        forest = -13.0 + float(rng.normal(0, 0.2))
        out.append({"date": date, "track": track, "direction": direction,
                    "hv_landslide_db": round(land, 1), "hv_forest_db": round(forest, 1)})
    return out


def _png_hv(db: np.ndarray, nodata: np.ndarray) -> Image.Image:
    grey = np.clip((db + 25.0) / 20.0, 0, 1) * 255.0          # -25 dB black, -5 dB white
    alpha = np.where(nodata, 0, 255)
    return Image.fromarray(np.dstack([grey.astype(np.uint8), alpha.astype(np.uint8)]), "LA")


def _png_change(dhv: np.ndarray, nodata: np.ndarray) -> Image.Image:
    rgba = np.zeros(dhv.shape + (4,), dtype=np.uint8)
    drop, rise = dhv < 0, dhv > 0
    rgba[drop, :3] = (220, 38, 38)                            # red = drop
    rgba[rise, :3] = (37, 99, 235)                            # blue = rise
    alpha = np.clip((np.abs(dhv) - 1.0) / 5.0, 0, 1) * 255.0  # transparent near 0, full at 6 dB
    rgba[..., 3] = np.where(nodata, 0, alpha).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def _images(out: Path, pairs: list[dict], landslides: list[dict], bbox: list[float], seed: int) -> list[str]:
    west, south, east, north = bbox
    mask_img = Image.new("L", (IMG, IMG), 0)
    draw = ImageDraw.Draw(mask_img)
    for f in landslides:
        pix = [((lon - west) / (east - west) * IMG, (north - lat) / (north - south) * IMG)
               for lon, lat in f["geometry"]["coordinates"][0]]
        draw.polygon(pix, fill=255)
    scar = gaussian_filter(np.asarray(mask_img, dtype=float) / 255.0, 1.0)
    scar = np.clip(scar * 1.6, 0, 1)

    base = gaussian_filter(np.random.default_rng([seed, 3]).normal(size=(IMG, IMG)), 14)
    base = base / base.std()
    yy, xx = np.mgrid[0:IMG, 0:IMG]
    nodata = ((xx + 0.3 * yy) > IMG - 20) | (yy < 6)

    written = []
    for k, p in enumerate(pairs):
        rng = np.random.default_rng([seed, 10 + k])
        gain = float(rng.normal(0, 0.4))
        before = -12.0 + 2.0 * base + gain + gaussian_filter(rng.normal(0, 1.2, (IMG, IMG)), 1.0)
        after = -12.0 + 2.0 * base + gain + gaussian_filter(rng.normal(0, 1.2, (IMG, IMG)), 1.0) - 5.5 * scar
        names = {
            p["before_png"]: _png_hv(before, nodata),
            p["after_png"]: _png_hv(after, nodata),
            p["change_png"]: _png_change(after - before, nodata),
        }
        for name, img in names.items():
            img.save(out / name, optimize=True)
            written.append(name)
    return written


def write_mock(cfg: dict, out: str | Path) -> list[str]:
    """Write every output file with mock data into `out`. Returns the file names written."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    seed = SEED
    written: list[str] = []

    event = {
        "event_id": cfg["event_id"], "name": cfg["name"], "time_utc": cfg["time_utc"],
        "epicentre": cfg["epicentre"], "bbox": cfg["bbox"], "maturity": cfg["maturity"],
        "mock": True, "references": cfg["references"],
    }
    _write_json(out / "event.json", event)

    pairs = []
    rng = np.random.default_rng([seed, 4])
    w, s, e, n = cfg["bbox"]
    for p in cfg["pairs"]:
        d_before, d_after = p["before"][:10].replace("-", ""), p["after"][:10].replace("-", "")
        pairs.append({
            "id": p["id"], "track": p["track"], "direction": p["direction"], "before": p["before"], "after": p["after"],
            "before_png": f"hv_{p['id']}_{d_before}.png", "after_png": f"hv_{p['id']}_{d_after}.png",
            "change_png": f"hv_change_{p['id']}.png",
            "bounds": [[w, n], [e, n], [e, s], [w, s]],
            "granules": list(p.get("granules", [])),
            "flagged_pixels": int(rng.integers(800, 3000)),
        })
    _write_json(out / "pairs.json", pairs)

    landslides = _landslides(seed)
    _write_json(out / "landslides.geojson", {"type": "FeatureCollection", "features": landslides}, compact=True)
    unknown = _unknown_areas()
    _write_json(out / "unknown.geojson", {"type": "FeatureCollection", "features": unknown}, compact=True)

    roads = _roads(landslides, unknown)
    blocked_km = sum(f["_length_m"] for f in roads if f["properties"]["status"] == "blocked") / 1000.0
    for f in roads:
        del f["_length_m"]
    _write_json(out / "roads.geojson", {"type": "FeatureCollection", "features": roads}, compact=True)

    communities = _communities(roads)
    _write_json(out / "communities.geojson", {"type": "FeatureCollection", "features": communities}, compact=True)

    stats = {
        "mock": True,
        "landslides": len(landslides),
        "area_km2": round(sum(f["properties"]["area_m2"] for f in landslides) / 1e6, 3),
        "roads_blocked_km": round(blocked_km, 2),
        "communities_cut_off": sum(1 for f in communities if f["properties"]["status"] == "cut_off"),
        "validation": {
            "split": "test", "n_test_landslide": 50, "n_test_forest": 50,
            "detection_rate": 0.78, "false_alarm_rate": 0.12, "auc": 0.86, "threshold_db": -3.5,
            "by_size": [{"size": "small", "n": 14, "detection_rate": 0.45},
                        {"size": "medium", "n": 24, "detection_rate": 0.8},
                        {"size": "large", "n": 12, "detection_rate": 0.95}],
        },
        "baseline_no_change_flag_rate": 0.004,
        "post_event_flag_rate": 0.031,
        "params": dict(cfg["detect"], threshold_db=float(cfg["detect"]["threshold_db"]),
                       min_slope_deg=float(cfg["detect"]["min_slope_deg"]),
                       min_forest_hv_db=float(cfg["detect"]["min_forest_hv_db"])),
        "pixel_m": float(cfg["target_res_m"]),
    }
    _write_json(out / "stats.json", stats)
    _write_json(out / "timeseries.json", _timeseries(cfg, seed))
    _write_json(out / "timeline.json", [
        {"time_utc": QUAKE_UTC, "label": "M7.7 earthquake", "source": "USGS"},
        {"time_utc": "2026-10-09T23:53:35Z", "label": "First NISAR pass after the quake (track 141)", "source": "ASF"},
        {"time_utc": "2026-10-16T00:00:00Z", "label": "92% of roads with structural collapses reopened", "source": "Newsroom Panama"},
    ])

    pngs = _images(out, pairs, landslides, cfg["bbox"], seed)
    written = ["event.json", "pairs.json", "landslides.geojson", "unknown.geojson", "roads.geojson",
               "communities.geojson", "stats.json", "timeseries.json", "timeline.json"] + pngs
    return written
