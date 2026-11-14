"""Which roads are likely blocked, and which communities are possibly cut off.

Inputs are the detected landslides (output of the radar run), the areas the radar could not see, open road and
place data (OpenStreetMap) and a list of main towns ("hubs"). Everything is computed in a metric coordinate
system (EPSG:32617) and written back in lon/lat.

Road status (first rule that applies, per piece of road of at most `segment_m` metres):
  blocked  a landslide within `blocked_m` of the road (about one pixel: it touches)
  at_risk  a landslide within `at_risk_m`
  unknown  at least `unknown_share` of the piece lies where the radar could not see
  clear    otherwise
Community status: the road graph is cut at "blocked" pieces. A community is
  reachable  if it can still reach a hub,
  cut_off    if it could reach a hub on the full map but every such route crosses a blocked piece,
  unknown    if there is no mapped road within `far_m`, or its roads do not reach a hub even on the full map.
The wording in the app is always "likely blocked" and "possibly cut off": nobody saw the blockage.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import shapely
from pyproj import Transformer
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from shapely.geometry import LineString, MultiLineString, Point, shape
from shapely.ops import substring

from .export import write_json

METRIC_CRS = "EPSG:32617"
ROAD_CLASSES = {"trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "track"}
PLACE_CLASSES = {"city", "town", "village", "hamlet"}
REPORTED_PLACES = ["Arenas", "El Cacao", "Quebro"]       # places news reports said were cut off (for the sanity check)
NAME_MAX = 120


class AccessError(Exception):
    """A problem with the inputs (never a crash trace for the user)."""


@dataclass(frozen=True)
class AccessParams:
    blocked_m: float = 10.0
    at_risk_m: float = 100.0
    unknown_share: float = 0.5
    segment_m: float = 500.0
    snap_m: float = 1.0
    far_m: float = 2000.0
    hub_snap_m: float = 3000.0

    @classmethod
    def from_config(cls, cfg: dict) -> "AccessParams":
        return cls(**{k: float(v) for k, v in cfg.get("access", {}).items() if k in cls.__dataclass_fields__})


@dataclass
class Way:
    osm_id: str | None
    name: str | None
    highway: str | None
    line: LineString                      # metric coordinates


@dataclass
class Piece:
    way: int                              # index of the way it belongs to
    order: int                            # position along the way
    line: LineString
    status: str = "clear"
    min_distance_m: float | None = None
    landslide_ids: tuple[str, ...] = ()


# ---- reading inputs ----

def _clean_name(v) -> str | None:
    if not isinstance(v, str):
        return None
    v = " ".join(v.split())
    return v[:NAME_MAX] or None


def _osm_id(props: dict) -> str | None:
    for key in ("osm_id", "@id", "id"):
        v = props.get(key)
        if v not in (None, ""):
            return re.sub(r"^(way|node|relation)/", "", str(v))[:40]
    return None


def _projector(src: str, dst: str) -> Callable[[np.ndarray], np.ndarray]:
    t = Transformer.from_crs(src, dst, always_xy=True)

    def convert(coords: np.ndarray) -> np.ndarray:
        x, y = t.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])

    return convert


def read_ways(path: Path) -> list[Way]:
    """Road lines from a lon/lat GeoJSON file. Only drivable classes are kept; names are treated as plain text."""
    if not Path(path).is_file():
        raise AccessError(f"roads file not found: {path}")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    to_metric = _projector("EPSG:4326", METRIC_CRS)
    ways: list[Way] = []
    for f in data.get("features", []):
        props = f.get("properties") or {}
        highway = props.get("highway")
        geom = f.get("geometry")
        if highway not in ROAD_CLASSES or not geom or geom.get("type") not in ("LineString", "MultiLineString"):
            continue
        g = shape(geom)
        for part in (g.geoms if isinstance(g, MultiLineString) else [g]):
            if len(part.coords) >= 2:
                line = shapely.transform(part, to_metric)
                if line.length > 0:
                    ways.append(Way(_osm_id(props), _clean_name(props.get("name")), highway, line))
    if not ways:
        raise AccessError("no usable roads in the roads file (expected OpenStreetMap lines with a 'highway' tag)")
    return ways


def _parse_population(v) -> int | None:
    digits = re.sub(r"[^0-9]", "", str(v)) if v not in (None, "") else ""
    return int(digits) if digits and len(digits) <= 9 else None


@dataclass
class Place:
    osm_id: str | None
    name: str
    place: str
    population: int | None
    xy: tuple[float, float]


def read_places(path: Path) -> list[Place]:
    if not Path(path).is_file():
        raise AccessError(f"places file not found: {path}")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    to_metric = _projector("EPSG:4326", METRIC_CRS)
    places: list[Place] = []
    for f in data.get("features", []):
        props = f.get("properties") or {}
        name = _clean_name(props.get("name"))
        if props.get("place") not in PLACE_CLASSES or not name or not f.get("geometry"):
            continue
        p = shapely.transform(shape(f["geometry"]).representative_point(), to_metric)
        places.append(Place(_osm_id(props), name, props["place"], _parse_population(props.get("population")), (p.x, p.y)))
    return places


def read_polygons(path: Path, with_ids: bool = False):
    """Polygons from an output GeoJSON file, projected to metres. With ids: [(id, polygon)]."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    to_metric = _projector("EPSG:4326", METRIC_CRS)
    out = []
    for f in data["features"]:
        g = shapely.transform(shape(f["geometry"]), to_metric)
        out.append((str(f["properties"].get("id")), g) if with_ids else g)
    return out


# ---- road pieces and their status ----

def split_ways(ways: list[Way], segment_m: float) -> list[Piece]:
    """Cut every way into equal pieces no longer than segment_m."""
    pieces: list[Piece] = []
    for wi, w in enumerate(ways):
        length = w.line.length
        n = max(1, math.ceil(length / segment_m))
        step = length / n
        for k in range(n):
            line = w.line if n == 1 else substring(w.line, k * step, (k + 1) * step if k < n - 1 else length)
            if isinstance(line, LineString) and line.length > 0:
                pieces.append(Piece(wi, k, line))
    return pieces


def classify_pieces(pieces: list[Piece], landslides: list[tuple[str, object]], unknown: list, params: AccessParams) -> None:
    """Set status, min_distance_m and landslide_ids on every piece (in place)."""
    if not pieces:
        return
    lines = np.array([p.line for p in pieces], dtype=object)
    dmin = np.full(len(pieces), np.inf)
    ids: list[set[str]] = [set() for _ in pieces]
    if landslides:
        tree = shapely.STRtree([g for _, g in landslides])
        idx, dist = tree.query_nearest(lines, return_distance=True, all_matches=False)
        dmin[idx[0]] = dist
        near = tree.query(lines, predicate="dwithin", distance=params.at_risk_m)
        for pi, li in zip(near[0], near[1]):
            ids[pi].add(landslides[li][0])
    share = np.zeros(len(pieces))
    if unknown:
        utree = shapely.STRtree(unknown)
        pi, ui = utree.query(lines, predicate="intersects")
        if len(pi):
            inter = shapely.length(shapely.intersection(lines[pi], np.array(unknown, dtype=object)[ui]))
            np.add.at(share, pi, inter)
        share = share / np.maximum(shapely.length(lines), 1e-9)
    for i, p in enumerate(pieces):
        d = float(dmin[i])
        if d <= params.blocked_m:
            p.status = "blocked"
        elif d <= params.at_risk_m:
            p.status = "at_risk"
        elif share[i] >= params.unknown_share:
            p.status = "unknown"
        else:
            p.status = "clear"
        # round up, so a rounded distance can never cross a limit that decided the status
        p.min_distance_m = None if math.isinf(d) else math.ceil(d * 10) / 10
        p.landslide_ids = tuple(sorted(ids[i]))


def merge_runs(ways: list[Way], pieces: list[Piece]) -> list[dict]:
    """Join neighbouring pieces of one way that share a status into single lines. Returns lon/lat features."""
    to_lonlat = _projector(METRIC_CRS, "EPSG:4326")
    feats: list[dict] = []
    by_way: dict[int, list[Piece]] = {}
    for p in sorted(pieces, key=lambda p: (p.way, p.order)):
        by_way.setdefault(p.way, []).append(p)
    for wi, group in by_way.items():
        w = ways[wi]
        runs: list[list[Piece]] = []
        for p in group:
            if runs and runs[-1][-1].status == p.status:
                runs[-1].append(p)
            else:
                runs.append([p])
        for run in runs:
            coords = [c for p in run for c in (p.line.coords if p is run[0] else list(p.line.coords)[1:])]
            ll = to_lonlat(np.array(coords))
            dists = [p.min_distance_m for p in run if p.min_distance_m is not None]
            feats.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[round(float(x), 6), round(float(y), 6)] for x, y in ll]},
                "properties": {
                    "osm_id": w.osm_id, "name": w.name, "highway": w.highway, "status": run[0].status,
                    "min_distance_m": min(dists) if dists else None,
                    "landslide_ids": ",".join(sorted({i for p in run for i in p.landslide_ids})),
                },
            })
    return feats


# ---- road graph and community access ----

@dataclass
class Graph:
    keys: dict                            # snapped coordinates -> node number
    xy: np.ndarray                        # node coordinates (metres)
    full: np.ndarray                      # connected-component label of each node, all roads
    open: np.ndarray                      # the same with blocked pieces removed


def build_graph(ways: list[Way], pieces: list[Piece], params: AccessParams) -> Graph:
    """Nodes are road vertices snapped to snap_m; an edge joins neighbouring vertices of a way."""
    status = {(p.way, p.order): p.status for p in pieces}
    n_pieces = {}
    for p in pieces:
        n_pieces[p.way] = max(n_pieces.get(p.way, 0), p.order + 1)
    keys: dict = {}
    coords: list = []

    def node(x: float, y: float) -> int:
        k = (round(x / params.snap_m), round(y / params.snap_m))
        if k not in keys:
            keys[k] = len(coords)
            coords.append((k[0] * params.snap_m, k[1] * params.snap_m))
        return keys[k]

    u_all, v_all, u_open, v_open = [], [], [], []
    for wi, w in enumerate(ways):
        pts = list(w.line.coords)
        length, n = w.line.length, n_pieces.get(wi, 1)
        step = length / n
        run = 0.0
        for a, b in zip(pts, pts[1:]):
            seg = math.hypot(b[0] - a[0], b[1] - a[1])
            first = min(int(run / step), n - 1)
            last = min(int(max(run + seg - 1e-9, run) / step), n - 1)
            run += seg
            ua, vb = node(*a[:2]), node(*b[:2])
            if ua == vb:
                continue
            u_all.append(ua)
            v_all.append(vb)
            # an edge can span several pieces (sparse map vertices): it is blocked if it crosses any blocked piece
            if not any(status.get((wi, k)) == "blocked" for k in range(first, last + 1)):
                u_open.append(ua)
                v_open.append(vb)
    count = len(coords)

    def labels(u, v) -> np.ndarray:
        m = coo_matrix((np.ones(len(u)), (u, v)), shape=(count, count))
        return connected_components(m, directed=False)[1]

    return Graph(keys, np.array(coords, dtype=float).reshape(-1, 2), labels(u_all, v_all), labels(u_open, v_open))


@dataclass
class Hub:
    name: str
    xy: tuple[float, float]


@dataclass
class CommunityResult:
    place: Place
    status: str
    nearest_hub: str | None
    reason: str


def assess_communities(places: list[Place], hubs: list[Hub], graph: Graph, params: AccessParams) -> tuple[list[CommunityResult], list[str]]:
    """Status of every place. Returns (results, names of hubs that could not be placed on the road map)."""
    if len(graph.xy) == 0:
        raise AccessError("the road graph is empty")
    tree = cKDTree(graph.xy)
    usable: list[tuple[Hub, int]] = []
    skipped: list[str] = []
    for h in hubs:
        d, i = tree.query(h.xy)
        if d <= params.hub_snap_m:
            usable.append((h, int(i)))
        else:
            skipped.append(h.name)
    far_km = f"{params.far_m / 1000:g}"
    results: list[CommunityResult] = []
    for pl in places:
        d, i = tree.query(pl.xy)
        if d > params.far_m:
            results.append(CommunityResult(pl, "unknown", None, f"No mapped road within {far_km} km, so access is unknown."))
            continue
        i = int(i)

        def nearest(candidates: list[tuple[Hub, int]]) -> str:
            return min(candidates, key=lambda hn: math.hypot(hn[0].xy[0] - pl.xy[0], hn[0].xy[1] - pl.xy[1]))[0].name

        on_map = [(h, n) for h, n in usable if graph.full[n] == graph.full[i]]
        if not on_map:
            results.append(CommunityResult(pl, "unknown", None, "Its mapped roads do not reach a town, so access is unknown."))
            continue
        still = [(h, n) for h, n in usable if graph.open[n] == graph.open[i]]
        if still:
            hub = nearest(still)
            results.append(CommunityResult(pl, "reachable", hub, f"A mapped road to {hub} has no likely-blocked stretch."))
        else:
            hub = nearest(on_map)
            results.append(CommunityResult(pl, "cut_off", hub, f"Every mapped road to {hub} crosses a likely-blocked stretch."))
    return results, skipped


def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c)).strip()


def community_features(results: list[CommunityResult]) -> list[dict]:
    to_lonlat = _projector(METRIC_CRS, "EPSG:4326")
    feats = []
    for r in sorted(results, key=lambda r: (r.place.name, r.place.osm_id or "")):
        lon, lat = to_lonlat(np.array([r.place.xy]))[0]
        feats.append({
            "type": "Feature", "geometry": {"type": "Point", "coordinates": [round(float(lon), 6), round(float(lat), 6)]},
            "properties": {"osm_id": r.place.osm_id, "name": r.place.name, "place": r.place.place, "population": r.place.population,
                           "status": r.status, "nearest_hub": r.nearest_hub, "reason": r.reason},
        })
    return feats


# ---- the whole step ----

def run_access(cfg: dict, root: Path, out: Path | None = None, log: Callable[[str], None] = print) -> dict:
    """Read landslides and map data, write roads.geojson and communities.geojson, update stats.json."""
    root = Path(root)
    out = Path(out) if out else (root / cfg["out"]).resolve()
    params = AccessParams.from_config(cfg)
    stats_path = out / "stats.json"
    if not stats_path.is_file() or not (out / "landslides.geojson").is_file():
        raise AccessError("run the radar processing first: there are no landslides to join to the roads yet")
    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    if stats.get("mock"):
        raise AccessError("the output folder holds mock data: run the radar processing first")

    ways = read_ways((root / cfg["roads"]).resolve())
    places = read_places((root / cfg["places"]).resolve())
    landslides = read_polygons(out / "landslides.geojson", with_ids=True)
    unknown = read_polygons(out / "unknown.geojson") if (out / "unknown.geojson").is_file() else []
    log(f"{len(ways)} road lines, {len(places)} places, {len(landslides)} landslides")

    pieces = split_ways(ways, params.segment_m)
    classify_pieces(pieces, landslides, unknown, params)
    km = {s: 0.0 for s in ("blocked", "at_risk", "clear", "unknown")}
    for p in pieces:
        km[p.status] += p.line.length / 1000.0
    log("roads: " + ", ".join(f"{v:.1f} km {k}" for k, v in km.items()))

    graph = build_graph(ways, pieces, params)
    hubs = []
    for h in cfg["hubs"]:
        x, y = _projector("EPSG:4326", METRIC_CRS)(np.array([[h["lon"], h["lat"]]]))[0]
        hubs.append(Hub(h["name"], (float(x), float(y))))
    results, skipped = assess_communities(places, hubs, graph, params)
    counts = {s: sum(r.status == s for r in results) for s in ("cut_off", "reachable", "unknown")}
    log("communities: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    if skipped:
        log(f"warning: these towns are not on the road map (more than {params.hub_snap_m / 1000:g} km from any road): {', '.join(skipped)}")

    write_json(out / "roads.geojson", {"type": "FeatureCollection", "features": merge_runs(ways, pieces)}, compact=True)
    write_json(out / "communities.geojson", {"type": "FeatureCollection", "features": community_features(results)}, compact=True)
    stats["roads_blocked_km"] = round(km["blocked"], 2)
    stats["communities_cut_off"] = counts["cut_off"]
    write_json(stats_path, stats)

    by_name = {_fold(r.place.name): r for r in results}
    reported = []
    for name in cfg.get("reported_cut_off", REPORTED_PLACES):
        r = by_name.get(_fold(name))
        reported.append({"name": name, "found_in_map": r is not None, "status": r.status if r else None})
    return {"road_km": km, "communities": counts, "skipped_hubs": skipped, "reported_places": reported}
