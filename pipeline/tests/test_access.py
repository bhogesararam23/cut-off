"""Road status and community access, on small made-up maps (metric coordinates, no downloads)."""

import json
import math

import numpy as np
import pytest
from pyproj import Transformer
from shapely.geometry import LineString, box

from cutoff.__main__ import main
from cutoff.access import (AccessError, AccessParams, Hub, Place, Way, assess_communities, build_graph, classify_pieces,
                           merge_runs, read_places, read_ways, run_access, split_ways)
from cutoff.contract import check_dir

P = AccessParams()
SLIDE = [("L0001", box(0, 0, 20, 20))]


def way(coords, name="r", highway="tertiary", osm_id="1"):
    return Way(osm_id, name, highway, LineString(coords))


def status_of(line_coords, landslides=SLIDE, unknown=()):
    pieces = split_ways([way(line_coords)], 10_000)
    classify_pieces(pieces, landslides, list(unknown), P)
    return pieces[0]


# ---- road status ----

def test_a_line_touching_a_landslide_is_blocked_50_m_away_at_risk_500_m_clear():
    assert status_of([(-50, 10), (70, 10)]).status == "blocked"           # crosses it
    assert status_of([(20, 10), (200, 10)]).status == "blocked"           # touches its edge
    assert status_of([(-50, 70), (70, 70)]).status == "at_risk"           # 50 m north of the polygon's edge
    assert status_of([(-50, 520), (70, 520)]).status == "clear"           # 500 m away


def test_status_limits():
    assert status_of([(-50, 29), (70, 29)]).status == "blocked"           # 9 m away: inside the 10 m limit
    assert status_of([(-50, 31), (70, 31)]).status == "at_risk"           # 11 m
    assert status_of([(-50, 119), (70, 119)]).status == "at_risk"         # 99 m
    assert status_of([(-50, 121), (70, 121)]).status == "clear"           # 101 m


def test_distance_and_ids_are_reported_and_never_round_across_a_limit():
    p = status_of([(-50, 70), (70, 70)])
    assert p.min_distance_m == 50.0 and p.landslide_ids == ("L0001",)
    just_over = status_of([(-50, 30.0004), (70, 30.0004)])                # 10.0004 m: at_risk, and 10.1 after rounding up
    assert just_over.status == "at_risk" and just_over.min_distance_m > 10
    assert status_of([(-50, 700), (70, 700)]).landslide_ids == ()
    assert status_of([(-50, 700), (70, 700)], landslides=[]).min_distance_m is None


def test_unknown_when_half_or_more_is_unseen_but_landslides_win():
    unseen = [box(-1000, 495, 1000, 505)]
    assert status_of([(-50, 500), (50, 500)], unknown=unseen).status == "unknown"            # all inside
    half = [box(0, 480, 50, 520)]                                                             # covers 50 m of a 100 m line
    assert status_of([(-50, 500), (50, 500)], unknown=half).status == "unknown"
    less = [box(0, 480, 40, 520)]
    assert status_of([(-50, 500), (50, 500)], unknown=less).status == "clear"
    assert status_of([(-50, 10), (50, 10)], unknown=[box(-100, -100, 100, 100)]).status == "blocked"


def test_long_roads_are_cut_so_one_landslide_does_not_block_a_whole_road():
    long_road = way([(0, 5000), (10_000, 5000)])
    pieces = split_ways([long_road], 500)
    assert len(pieces) == 20 and all(abs(p.line.length - 500) < 1e-6 for p in pieces)
    classify_pieces(pieces, [("L1", box(4900, 4990, 5100, 5010))], [], P)
    statuses = [p.status for p in pieces]
    assert statuses.count("blocked") == 2 and statuses[0] == "clear" and statuses[-1] == "clear"


def test_neighbouring_pieces_with_one_status_are_joined(monkeypatch):
    # a road in lon/lat-free metric space cannot be merged to lon/lat without a real location, so build one near 7.5 N
    to_metric = Transformer.from_crs(4326, "EPSG:32617", always_xy=True)
    x0, y0 = to_metric.transform(-80.9, 7.5)
    w = way([(x0, y0), (x0 + 4000, y0)])
    pieces = split_ways([w], 500)
    classify_pieces(pieces, [("L1", box(x0 + 1990, y0 - 5, x0 + 2010, y0 + 5))], [], P)
    feats = merge_runs([w], pieces)
    assert [f["properties"]["status"] for f in feats] == ["clear", "blocked", "clear"]
    blocked = feats[1]
    assert blocked["properties"]["landslide_ids"] == "L1" and blocked["properties"]["min_distance_m"] <= 10
    assert blocked["geometry"]["coordinates"][0][0] == pytest.approx(-80.9 + 1500 / 110_300, abs=2e-4)
    assert all(round(c, 6) == c for f in feats for xy in f["geometry"]["coordinates"] for c in xy)


# ---- community access ----

def network(blocked_at=None, second_road=False):
    """A village V at (0, 0) joined to a town H at (3000, 0) by a road; optionally blocked, optionally with a bypass."""
    ways = [way([(0, 0), (1500, 0), (3000, 0)], osm_id="main")]
    if second_road:
        ways.append(way([(0, 0), (0, 800), (3000, 800), (3000, 0)], osm_id="bypass"))
    pieces = split_ways(ways, 500)
    landslides = [("L1", box(blocked_at - 10, -10, blocked_at + 10, 10))] if blocked_at is not None else []
    classify_pieces(pieces, landslides, [], P)
    return ways, pieces


def assess(ways, pieces, places=None, hubs=None, params=P):
    graph = build_graph(ways, pieces, params)
    places = places or [Place("1", "Village", "village", 120, (0.0, 0.0))]
    hubs = hubs or [Hub("Town", (3000.0, 0.0))]
    return assess_communities(places, hubs, graph, params)


def test_a_village_whose_only_road_is_blocked_is_cut_off():
    results, _ = assess(*network(blocked_at=1500))
    r = results[0]
    assert r.status == "cut_off" and r.nearest_hub == "Town" and "likely-blocked" in r.reason


def test_with_a_second_open_road_it_is_reachable():
    results, _ = assess(*network(blocked_at=1500, second_road=True))
    assert results[0].status == "reachable" and results[0].nearest_hub == "Town"


def test_no_landslide_means_reachable():
    assert assess(*network())[0][0].status == "reachable"


def test_an_unseen_road_does_not_cut_a_community_off():
    ways, pieces = network()
    classify_pieces(pieces, [], [box(-10, -10, 3010, 10)], P)
    assert {p.status for p in pieces} == {"unknown"}
    assert assess(ways, pieces)[0][0].status == "reachable"


def test_a_village_far_from_any_road_is_unknown():
    ways, pieces = network(blocked_at=1500)
    results, _ = assess(ways, pieces, places=[Place(None, "Remote", "hamlet", None, (0.0, 5000.0))])
    assert results[0].status == "unknown" and results[0].nearest_hub is None and "2 km" in results[0].reason


def test_roads_that_do_not_reach_a_town_are_a_map_gap_not_a_blockage():
    ways = [way([(0, 0), (1000, 0)], osm_id="a"), way([(2500, 0), (3000, 0)], osm_id="b")]      # a gap in the map
    pieces = split_ways(ways, 500)
    classify_pieces(pieces, [], [], P)
    results, _ = assess(ways, pieces)
    assert results[0].status == "unknown" and "do not reach a town" in results[0].reason


def test_the_nearest_reachable_town_is_named_and_unusable_towns_are_reported():
    ways = [way([(0, 0), (2000, 0), (6000, 0)])]
    pieces = split_ways(ways, 500)
    classify_pieces(pieces, [("L", box(1990, -10, 2010, 10))], [], P)       # blocks the way to the near town only
    hubs = [Hub("Near", (3000.0, 0.0)), Hub("Far", (6000.0, 0.0)), Hub("Offmap", (0.0, 50_000.0))]
    results, skipped = assess(ways, pieces, hubs=hubs)
    assert results[0].status == "cut_off" and skipped == ["Offmap"]         # both towns lie beyond the blocked stretch
    results, _ = assess(ways, pieces, places=[Place("2", "East", "village", None, (5500.0, 0.0))], hubs=hubs)
    assert results[0].status == "reachable" and results[0].nearest_hub == "Far"


def test_snapping_joins_roads_that_meet_within_a_metre():
    ways = [way([(0, 0), (1000, 0)], osm_id="a"), way([(1000.4, 0.3), (3000, 0)], osm_id="b")]
    pieces = split_ways(ways, 500)
    classify_pieces(pieces, [], [], P)
    assert assess(ways, pieces)[0][0].status == "reachable"
    loose = AccessParams(snap_m=0.1)
    assert assess(ways, pieces, params=loose)[0][0].status == "unknown"


# ---- reading map files and the whole step ----

def lonlat_features(tmp_path):
    to_ll = Transformer.from_crs("EPSG:32617", 4326, always_xy=True)
    x0, y0 = Transformer.from_crs(4326, "EPSG:32617", always_xy=True).transform(-80.9, 7.5)

    def ll(x, y):
        lon, lat = to_ll.transform(x0 + x, y0 + y)
        return [round(lon, 6), round(lat, 6)]

    def line(props, *pts):
        return {"type": "Feature", "properties": props, "geometry": {"type": "LineString", "coordinates": [ll(*p) for p in pts]}}

    roads = {"type": "FeatureCollection", "features": [
        line({"highway": "tertiary", "name": "Main <b>road</b>", "@id": "way/10"}, (0, 0), (1500, 0), (3000, 0)),
        line({"highway": "footway", "name": "Path"}, (0, 100), (1000, 100)),                  # not drivable: ignored
        line({"highway": "track", "@id": "way/11"}, (0, 3000), (500, 3000)),
    ]}
    places = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"place": "village", "name": "Arenas", "population": "1,200", "@id": "node/5"},
         "geometry": {"type": "Point", "coordinates": ll(0, 0)}},
        {"type": "Feature", "properties": {"place": "hamlet", "name": "Quebro"}, "geometry": {"type": "Point", "coordinates": ll(0, 9000)}},
        {"type": "Feature", "properties": {"place": "locality", "name": "Skipped"}, "geometry": {"type": "Point", "coordinates": ll(0, 0)}},
        {"type": "Feature", "properties": {"place": "village"}, "geometry": {"type": "Point", "coordinates": ll(0, 0)}},      # no name
    ]}
    sq = lambda x, y, h: {"type": "Polygon", "coordinates": [[ll(x - h, y - h), ll(x + h, y - h), ll(x + h, y + h), ll(x - h, y + h), ll(x - h, y - h)]]}
    landslides = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": sq(1500, 0, 30), "properties": {"id": "L0001"}}]}
    hub = ll(3000, 0)
    return roads, places, landslides, {"name": "Town", "lon": hub[0], "lat": hub[1]}


def test_map_files_are_read_with_only_drivable_roads_and_named_places(tmp_path):
    roads, places, _, _ = lonlat_features(tmp_path)
    (tmp_path / "r.geojson").write_text(json.dumps(roads), encoding="utf-8")
    (tmp_path / "p.geojson").write_text(json.dumps(places), encoding="utf-8")
    ways = read_ways(tmp_path / "r.geojson")
    assert [w.highway for w in ways] == ["tertiary", "track"] and ways[0].osm_id == "10" and ways[1].name is None
    assert ways[0].name == "Main <b>road</b>"                          # kept as plain text: the app never renders it as HTML
    ps = read_places(tmp_path / "p.geojson")
    assert [(p.name, p.place, p.population, p.osm_id) for p in ps] == [("Arenas", "village", 1200, "5"), ("Quebro", "hamlet", None, None)]
    (tmp_path / "none.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    with pytest.raises(AccessError):
        read_ways(tmp_path / "none.geojson")
    with pytest.raises(AccessError):
        read_ways(tmp_path / "missing.geojson")


def scene(tmp_path):
    roads, places, landslides, hub = lonlat_features(tmp_path)
    raw, out = tmp_path / "data" / "raw", tmp_path / "out"
    raw.mkdir(parents=True)
    out.mkdir()
    (raw / "roads.geojson").write_text(json.dumps(roads), encoding="utf-8")
    (raw / "places.geojson").write_text(json.dumps(places), encoding="utf-8")
    (out / "landslides.geojson").write_text(json.dumps(landslides), encoding="utf-8")
    (out / "unknown.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8")
    stats = {"mock": False, "landslides": 1, "area_km2": 0.0, "roads_blocked_km": None, "communities_cut_off": None, "validation": None,
             "baseline_no_change_flag_rate": 0.0, "post_event_flag_rate": 0.0,
             "params": {"threshold_db": -3.0, "min_slope_deg": 10.0, "min_forest_hv_db": -16.0, "min_pixels": 3}, "pixel_m": 20.0}
    (out / "stats.json").write_text(json.dumps(stats), encoding="utf-8")
    return {"out": "out", "roads": "data/raw/roads.geojson", "places": "data/raw/places.geojson", "hubs": [hub]}


def test_the_whole_step_writes_files_that_follow_the_data_format(tmp_path):
    cfg = scene(tmp_path)
    summary = run_access(cfg, tmp_path, log=lambda _: None)
    roads = json.loads((tmp_path / "out" / "roads.geojson").read_text(encoding="utf-8"))["features"]
    assert {f["properties"]["status"] for f in roads} == {"blocked", "clear"}
    blocked_km = sum(1 for f in roads if f["properties"]["status"] == "blocked")
    assert blocked_km >= 1 and all(f["properties"]["highway"] in ("tertiary", "track") for f in roads)
    comms = {f["properties"]["name"]: f["properties"] for f in json.loads((tmp_path / "out" / "communities.geojson").read_text(encoding="utf-8"))["features"]}
    assert comms["Arenas"]["status"] == "cut_off" and comms["Arenas"]["nearest_hub"] == "Town" and comms["Arenas"]["population"] == 1200
    assert comms["Quebro"]["status"] == "unknown" and comms["Quebro"]["nearest_hub"] is None
    stats = json.loads((tmp_path / "out" / "stats.json").read_text(encoding="utf-8"))
    assert stats["communities_cut_off"] == 1 and 0 < stats["roads_blocked_km"] < 1.5 and stats["landslides"] == 1
    assert summary["communities"] == {"cut_off": 1, "reachable": 0, "unknown": 1}
    assert {r["name"]: r["status"] for r in summary["reported_places"]} == {"Arenas": "cut_off", "El Cacao": None, "Quebro": "unknown"}
    assert [r["found_in_map"] for r in summary["reported_places"]] == [True, False, True]


def test_the_output_passes_the_format_checker_once_the_other_files_exist(tmp_path):
    cfg = scene(tmp_path)
    run_access(cfg, tmp_path, log=lambda _: None)
    problems = [p for p in check_dir(tmp_path / "out") if "roads.geojson" in p or "communities.geojson" in p or "stats.json" in p]
    assert problems == []


def test_access_refuses_mock_or_missing_landslides(tmp_path):
    cfg = scene(tmp_path)
    stats = json.loads((tmp_path / "out" / "stats.json").read_text(encoding="utf-8"))
    stats["mock"] = True
    (tmp_path / "out" / "stats.json").write_text(json.dumps(stats), encoding="utf-8")
    with pytest.raises(AccessError, match="mock"):
        run_access(cfg, tmp_path, log=lambda _: None)
    (tmp_path / "out" / "landslides.geojson").unlink()
    with pytest.raises(AccessError, match="radar processing first"):
        run_access(cfg, tmp_path, log=lambda _: None)


def test_cli_access(tmp_path, capsys):
    cfg = scene(tmp_path)
    (tmp_path / "pipeline").mkdir()
    full = dict(json.loads(open(__import__("pathlib").Path(__file__).resolve().parents[1] / "config.example.json", encoding="utf-8").read()), **cfg)
    (tmp_path / "pipeline" / "config.json").write_text(json.dumps(full), encoding="utf-8")
    assert main(["access", "--config", str(tmp_path / "pipeline" / "config.json")]) == 0
    text = capsys.readouterr().out
    assert "km likely blocked" in text and "possibly cut off" in text and "El Cacao" in text
    assert main(["access", "--config", str(tmp_path / "pipeline" / "config.json"), "--out", str(tmp_path / "nowhere")]) == 1
    assert "cannot run access" in capsys.readouterr().err


def test_reported_places_match_exact_names_then_whole_word_names():
    from cutoff.access import CommunityResult, reported_place_check

    def res(name, status):
        return CommunityResult(Place(None, name, "village", None, (0.0, 0.0)), status, None, "")

    results = [res("La Loma de Quebro", "unknown"), res("Quebrado", "reachable"), res("Arenas", "cut_off"), res("Las Arenas", "reachable")]
    q = reported_place_check("Quebro", results)
    assert q["found_in_map"] and q["matches"] == [{"name": "La Loma de Quebro", "status": "unknown"}]      # not "Quebrado"
    a = reported_place_check("Arenas", results)
    assert [m["name"] for m in a["matches"]] == ["Arenas", "Las Arenas"] and a["status"] == "cut_off"    # exact name first
    assert reported_place_check("El Cacao", results) == {"name": "El Cacao", "found_in_map": False, "status": None, "matches": []}
    assert reported_place_check("QUEBRO", results)["found_in_map"]
