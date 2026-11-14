"""End-to-end run on a small synthetic scene (no real data, no network)."""

import json

import numpy as np
import pytest
import rasterio

import synth
from cutoff.__main__ import main
from cutoff.contract import check_dir
from cutoff.run import missing_inputs, run, select_pairs


@pytest.fixture(scope="module")
def scene(tmp_path_factory):
    root = tmp_path_factory.mktemp("scene")
    cfg = synth.build(root)
    logs: list[str] = []
    summary = run(cfg, root, log=logs.append)
    return root, cfg, summary, logs


def load(root, name):
    return json.loads((root / "out" / name).read_text(encoding="utf-8"))


def test_output_follows_the_data_format(scene):
    root, *_ = scene
    assert check_dir(root / "out") == []


def test_files_are_real_not_mock(scene):
    root, *_ = scene
    assert load(root, "event.json")["mock"] is False and load(root, "stats.json")["mock"] is False
    # roads and communities belong to a later step: empty, never mock leftovers
    assert load(root, "roads.geojson")["features"] == [] and load(root, "communities.geojson")["features"] == []
    stats = load(root, "stats.json")
    assert stats["roads_blocked_km"] is None and stats["communities_cut_off"] is None and stats["validation"] is None


def test_the_real_patch_is_found_and_the_single_pair_decoy_is_dropped(scene):
    root, *_ = scene
    feats = load(root, "landslides.geojson")["features"]
    assert len(feats) == 1
    p = feats[0]["properties"]
    assert p["pairs_seen"] == 2 and p["pairs_visible"] == 2 and p["confidence"] == "high"
    assert -6.8 < p["dhv_db"] < -5.2 and p["slope_deg"] > 12
    assert 20_000 < p["area_m2"] < 40_000                                    # 160 m x 160 m patch = 25,600 m2
    ring = np.array(feats[0]["geometry"]["coordinates"][0])
    expected_lon = synth.LON0 + 108 * 10 / 110_300                           # patch A centre, about 1.08 km east
    expected_lat = synth.LAT0 - 108 * 10 / 110_574                           # and 1.08 km south
    assert ring[:, 0].mean() == pytest.approx(expected_lon, abs=0.0008)
    assert ring[:, 1].mean() == pytest.approx(expected_lat, abs=0.0008)


def test_each_pair_is_reported_with_images(scene):
    root, _, summary, _ = scene
    pairs = load(root, "pairs.json")
    assert [p["id"] for p in pairs] == ["t141d", "t4a"]
    assert all(p["flagged_pixels"] > 0 for p in pairs)
    assert pairs[0]["flagged_pixels"] > pairs[1]["flagged_pixels"]            # the first pair also has the decoy
    assert summary["pairs"] == {p["id"]: p["flagged_pixels"] for p in pairs}


def test_baseline_rate_is_lower_than_after_the_quake(scene):
    root, _, summary, _ = scene
    stats = load(root, "stats.json")
    assert stats["baseline_no_change_flag_rate"] < stats["post_event_flag_rate"]
    # the patch (and the decoy) are a small share of this 4 km scene: about 0.26% of forested slope
    assert stats["baseline_no_change_flag_rate"] < 0.0005 and stats["post_event_flag_rate"] > 0.002
    assert stats["pixel_m"] == 20.0 and stats["params"]["threshold_db"] == -3.0


def test_time_series_drops_after_the_quake_and_forest_stays_flat(scene):
    root, *_ = scene
    series = load(root, "timeseries.json")
    dates = [s["date"] for s in series]
    assert dates == sorted(dates) and len(series) == 6                        # 2 pairs x 2 passes + 2 baseline passes
    before = [s["hv_landslide_db"] for s in series if s["date"] < synth.QUAKE]
    after = [s["hv_landslide_db"] for s in series if s["date"] > synth.QUAKE]
    assert np.mean(before) - np.mean(after) == pytest.approx(6.0, abs=1.0)
    forest = [s["hv_forest_db"] for s in series]
    assert max(forest) - min(forest) < 1.0


def test_change_images_and_work_files_exist(scene):
    root, *_ = scene
    for name in ("hv_change_t141d.png", "hv_t141d_20260927.png", "hv_t141d_20261009.png"):
        assert (root / "out" / name).is_file()
    with rasterio.open(root / "work" / "dhv_t141d.tif") as src:                # used later for validation
        data = src.read(1)
        assert src.crs.to_epsg() == 32617 and np.nanmin(data) < -4


def test_timeline_is_built_from_the_primary_pair(scene):
    root, *_ = scene
    tl = load(root, "timeline.json")
    assert tl[0]["time_utc"] == synth.QUAKE and tl[1]["time_utc"] == "2026-10-09T23:53:35Z"


def test_missing_inputs_are_listed_not_guessed(tmp_path):
    cfg = synth.build(tmp_path)
    (tmp_path / "data" / "raw" / "t4_after.tif").unlink()
    pairs = select_pairs(cfg, None)
    assert missing_inputs(cfg, tmp_path, pairs) == ["data/raw/t4_after.tif"]
    with pytest.raises(FileNotFoundError, match="t4_after.tif"):
        run(cfg, tmp_path, log=lambda _: None)


def test_pair_selection_rules():
    cfg = {"primary_pair": "a", "pairs": [{"id": "b"}, {"id": "a"}, {"id": "c"}]}
    assert [p["id"] for p in select_pairs(cfg, None)] == ["a", "b", "c"]          # primary first
    assert [p["id"] for p in select_pairs(cfg, ["c", "a"])] == ["a", "c"]
    with pytest.raises(ValueError):
        select_pairs(cfg, ["b"])                                                   # primary is required
    with pytest.raises(ValueError):
        select_pairs(cfg, ["a", "zzz"])


def test_clean_removes_old_images_and_stale_files_are_reported(tmp_path):
    cfg = synth.build(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "hv_t999x_20200101.png").write_bytes(b"old")
    logs: list[str] = []
    summary = run(cfg, tmp_path, pair_ids=["t141d"], log=logs.append)
    assert summary["stale_files"] == ["hv_t999x_20200101.png"] and any("--clean" in line for line in logs)
    summary = run(cfg, tmp_path, pair_ids=["t141d"], clean=True, log=lambda _: None)
    assert summary["stale_files"] == [] and not (out / "hv_t999x_20200101.png").exists()


def test_cli_run_prints_a_summary(tmp_path, capsys):
    cfg = synth.build(tmp_path)
    config = synth.write_config(tmp_path, cfg)
    assert main(["run", "--config", str(config), "--pairs", "t141d,t4a"]) == 0
    text = capsys.readouterr().out
    assert "landslides: 1" in text and "baseline (no quake)" in text and "WARNING" not in text


def test_cli_run_reports_missing_files_without_a_traceback(tmp_path, capsys):
    cfg = synth.build(tmp_path)
    (tmp_path / "data" / "raw" / "dem.tif").unlink()
    config = synth.write_config(tmp_path, cfg)
    assert main(["run", "--config", str(config)]) == 1
    assert "dem.tif" in capsys.readouterr().err
