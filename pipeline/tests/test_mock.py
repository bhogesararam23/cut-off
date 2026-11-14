"""The mock generator: deterministic, flagged as mock, and covers every status the app must show."""

import json
import math
from pathlib import Path

from cutoff.mock import write_mock


def _load(folder: Path, name: str):
    return json.loads((folder / name).read_text(encoding="utf-8"))


def test_every_output_file_is_written(mock_dir):
    names = {p.name for p in mock_dir.iterdir()}
    for required in ("event.json", "pairs.json", "landslides.geojson", "unknown.geojson", "roads.geojson",
                     "communities.geojson", "stats.json", "timeseries.json", "timeline.json"):
        assert required in names
    assert sum(n.endswith(".png") for n in names) == 12  # 4 pairs x (before, after, change)


def test_mock_is_flagged(mock_dir):
    assert _load(mock_dir, "event.json")["mock"] is True
    assert _load(mock_dir, "stats.json")["mock"] is True


def test_output_is_deterministic(cfg, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    write_mock(cfg, a)
    write_mock(cfg, b)
    for p in a.iterdir():
        assert p.read_bytes() == (b / p.name).read_bytes(), p.name


def test_landslides_cluster_near_the_expected_place(mock_dir):
    feats = _load(mock_dir, "landslides.geojson")["features"]
    assert 20 <= len(feats) <= 30
    lons = [f["geometry"]["coordinates"][0][0][0] for f in feats]
    lats = [f["geometry"]["coordinates"][0][0][1] for f in feats]
    assert abs(sum(lons) / len(lons) - (-80.87)) < 0.05
    assert abs(sum(lats) / len(lats) - 7.48) < 0.05
    assert {f["properties"]["confidence"] for f in feats} == {"high", "medium", "low"}


def test_roads_show_all_four_statuses(mock_dir):
    statuses = {f["properties"]["status"] for f in _load(mock_dir, "roads.geojson")["features"]}
    assert statuses == {"blocked", "at_risk", "clear", "unknown"}


def test_communities_show_all_three_statuses(mock_dir):
    statuses = {f["properties"]["status"] for f in _load(mock_dir, "communities.geojson")["features"]}
    assert statuses == {"cut_off", "reachable", "unknown"}


def test_stats_agree_with_the_files(mock_dir):
    stats = _load(mock_dir, "stats.json")
    feats = _load(mock_dir, "landslides.geojson")["features"]
    comms = _load(mock_dir, "communities.geojson")["features"]
    assert stats["landslides"] == len(feats)
    assert math.isclose(stats["area_km2"], sum(f["properties"]["area_m2"] for f in feats) / 1e6, abs_tol=0.001)
    assert stats["communities_cut_off"] == sum(f["properties"]["status"] == "cut_off" for f in comms)


def test_landslide_signal_drops_about_5_db_after_the_quake(mock_dir, cfg):
    series = _load(mock_dir, "timeseries.json")
    before = [s["hv_landslide_db"] for s in series if s["date"] < cfg["time_utc"]]
    after = [s["hv_landslide_db"] for s in series if s["date"] > cfg["time_utc"]]
    assert before and after
    drop = sum(before) / len(before) - sum(after) / len(after)
    assert 4.0 <= drop <= 6.0
    forest = [s["hv_forest_db"] for s in series]
    assert max(forest) - min(forest) < 1.5          # intact forest stays flat


def test_images_are_small_enough(mock_dir):
    from PIL import Image

    for p in mock_dir.glob("*.png"):
        with Image.open(p) as im:
            assert max(im.size) <= 2048
