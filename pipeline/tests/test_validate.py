"""The validation protocol: sealed split, tuning on one half, one scoring of the other."""

import json
import subprocess

import numpy as np
import pytest
from shapely.geometry import box

import synth_validate
from cutoff.__main__ import main
from cutoff.contract import check_dir
from cutoff.run import run
from cutoff.validate import (CheckPoint, ValidationError, auc, found_within, load_points, points_are_committed,
                             restore_validation, run_validation, split_points)


# ---- pure pieces ----

def pts(n_land=10, n_forest=10):
    return ([CheckPoint(f"L{i:03d}", -80.0, 7.0 + i * 1e-4, "landslide", "small") for i in range(n_land)]
            + [CheckPoint(f"F{i:03d}", -80.1, 7.0 + i * 1e-4, "forest", "") for i in range(n_forest)])


def test_split_is_deterministic_and_half_per_label():
    points = pts(11, 8)
    tune, test = split_points(points)
    assert (tune, test) == split_points(points)
    assert sum(p.label == "landslide" for p in test) == 5 and sum(p.label == "landslide" for p in tune) == 6
    assert sum(p.label == "forest" for p in test) == 4 and sum(p.label == "forest" for p in tune) == 4
    assert not {p.id for p in tune} & {p.id for p in test}
    assert {p.id for p in tune} | {p.id for p in test} == {p.id for p in points}


def test_split_changes_with_the_seed_but_not_with_input_order():
    points = pts()
    assert split_points(points, seed=1)[1] != split_points(points, seed=2)[1]
    assert split_points(points[::-1])[1] == split_points(points)[1]


def test_auc_values():
    labels = np.array([1, 1, 1, 0, 0, 0], dtype=bool)
    assert auc(np.array([9, 8, 7, 3, 2, 1.0]), labels) == 1.0              # perfectly separated
    assert auc(np.array([1, 2, 3, 7, 8, 9.0]), labels) == 0.0
    assert auc(np.full(6, 5.0), labels) == 0.5                              # all tied = chance
    assert auc(np.array([9, 4, 7, 8, 2, 1.0]), labels) == pytest.approx(7 / 9)


def test_auc_needs_both_classes():
    with pytest.raises(ValidationError):
        auc(np.array([1.0, 2.0]), np.array([True, True]))


def test_found_within_uses_the_tolerance():
    poly = [box(0, 0, 20, 20)]
    xy = np.array([[10, 10], [35, 10], [45, 10], [10, 10.0]])
    assert found_within(xy, poly, 20).tolist() == [True, True, False, True]    # 15 m away counts, 25 m does not
    assert not found_within(xy, [], 20).any() and found_within(np.empty((0, 2)), poly).size == 0


def test_points_file_is_checked(tmp_path):
    p = tmp_path / "points.csv"

    def write(body):
        p.write_text("id,lon,lat,label,size,notes\n" + body, encoding="utf-8")

    write("P1,-80.1,7.5,landslide,medium,ok\nP2,-80.2,7.6,forest,,\n")
    assert [x.label for x in load_points(p)] == ["landslide", "forest"]
    for bad in ("P1,-80.1,7.5,tree,small,\n", "P1,-80.1,7.5,landslide,huge,\n", "P1,abc,7.5,landslide,small,\n",
                "P1,-80.1,7.5,landslide,small,\nP1,-80.2,7.5,forest,,\n", ",-80.1,7.5,landslide,small,\n",
                "P1,-80.1,97.5,landslide,small,\n"):
        write(bad)
        with pytest.raises(ValidationError):
            load_points(p)
    p.write_text("id,lon\nP1,1\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="missing column"):
        load_points(p)
    with pytest.raises(ValidationError):
        load_points(tmp_path / "nope.csv")


def test_points_must_be_committed_before_scoring(tmp_path):
    def git(*a):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-C", str(tmp_path), *a],
                              capture_output=True, text=True, check=True)

    git("init", "-q")
    (tmp_path / "points.csv").write_text("id,lon,lat,label,size\n", encoding="utf-8")
    assert points_are_committed(tmp_path, "points.csv")[0] is False                 # not tracked yet
    git("add", "points.csv")
    git("commit", "-q", "-m", "add points")
    assert points_are_committed(tmp_path, "points.csv") == (True, "")
    (tmp_path / "points.csv").write_text("id,lon,lat,label,size\nX,1,1,forest,\n", encoding="utf-8")
    ok, why = points_are_committed(tmp_path, "points.csv")
    assert ok is False and "not committed" in why


# ---- the protocol on a synthetic scene ----

@pytest.fixture
def scene(tmp_path):
    cfg, csv_text = synth_validate.build(tmp_path)
    (tmp_path / "data" / "validation").mkdir(parents=True)
    (tmp_path / "data" / "validation" / "points.csv").write_text(csv_text, encoding="utf-8")
    cfg["points"] = "data/validation/points.csv"
    run(cfg, tmp_path, log=lambda _: None)
    return tmp_path, cfg


def validate(root, cfg, **kw):
    return run_validation(cfg, root, require_committed=False, log=lambda _: None, **kw)


def test_run_saves_what_tuning_needs(scene):
    root, _ = scene
    for name in ("dhv_t141d.tif", "hvbefore_t141d.tif", "unknown_t141d.tif", "slope.tif"):
        assert (root / "work" / name).is_file()


def test_tuning_picks_the_threshold_that_separates_landslides_from_decoys(scene):
    root, cfg = scene
    result = validate(root, cfg)
    tuned = json.loads((root / "work" / "tuned.json").read_text(encoding="utf-8"))
    table = {r["threshold_db"]: r for r in tuned["table"]}
    assert tuned["seed"] == 2026 and sorted(table, reverse=True) == [-1.5 - 0.5 * i for i in range(10)]
    assert table[-1.5]["youden_j"] < 1.0 and table[-2.0]["youden_j"] < 1.0          # too sensitive: the decoys are flagged
    assert table[-6.0]["detection_rate"] < 1.0                                       # too strict: weaker landslides are missed
    assert all(table[t]["youden_j"] == 1.0 for t in (-2.5, -3.0, -3.5, -4.0, -4.5))   # a plateau of perfect separation
    assert tuned["threshold_db"] == -3.0                                              # ties go to the value nearest the default
    assert result["threshold_db"] == -3.0


def test_the_sealed_test_half_is_scored_into_stats(scene):
    root, cfg = scene
    result = validate(root, cfg)
    stats = json.loads((root / "out" / "stats.json").read_text(encoding="utf-8"))
    assert stats["mock"] is False and stats["params"]["threshold_db"] == -3.0          # detection reran with the tuned value
    v = stats["validation"]
    assert v["split"] == "test" and v["n_test_landslide"] == 10 and v["n_test_forest"] == 12
    assert v["detection_rate"] == 1.0 and v["false_alarm_rate"] == 0.0 and v["auc"] == 1.0
    assert sum(b["n"] for b in v["by_size"]) == 10 and {b["size"] for b in v["by_size"]} == {"small", "medium", "large"}
    assert "points_without_radar_coverage" not in v and set(v) == set(result) - {"points_without_radar_coverage"}
    assert check_dir(root / "out") == []                                              # still follows the data format


def test_the_test_half_is_scored_once(scene):
    root, cfg = scene
    validate(root, cfg)
    runs = json.loads((root / "work" / "validation_runs.json").read_text(encoding="utf-8"))
    assert len(runs) == 1 and runs[0]["scored_test"] is True and runs[0]["forced"] is False
    with pytest.raises(ValidationError, match="already been scored"):
        validate(root, cfg)
    validate(root, cfg, force=True)                                                  # allowed, and logged as forced
    runs = json.loads((root / "work" / "validation_runs.json").read_text(encoding="utf-8"))
    assert len(runs) == 2 and runs[1]["forced"] is True


def test_the_stored_result_survives_a_rerun_of_the_processing(scene):
    root, cfg = scene
    first = validate(root, cfg)
    run(cfg, root, log=lambda _: None)                                               # rewrites stats.json without validation
    assert json.loads((root / "out" / "stats.json").read_text(encoding="utf-8"))["validation"] is None
    restored = restore_validation(cfg, root)
    assert restored == first
    assert json.loads((root / "out" / "stats.json").read_text(encoding="utf-8"))["validation"]["auc"] == first["auc"]


def test_the_processing_uses_the_tuned_threshold_afterwards(scene):
    root, cfg = scene
    validate(root, cfg)
    logs: list[str] = []
    run(cfg, root, log=logs.append)
    assert any("tuned threshold -3 dB" in line for line in logs)
    assert json.loads((root / "out" / "stats.json").read_text(encoding="utf-8"))["params"]["threshold_db"] == -3.0
    run(cfg, root, use_tuned=False, log=lambda _: None)
    assert json.loads((root / "out" / "stats.json").read_text(encoding="utf-8"))["params"]["threshold_db"] == -1.5      # the starting value


def test_uncommitted_points_block_scoring(scene):
    root, cfg = scene
    with pytest.raises(ValidationError, match="Commit the check points"):
        run_validation(cfg, root, log=lambda _: None)                               # tmp folder is not a git repo
    assert not (root / "work" / "tuned.json").exists()


def test_validation_refuses_mock_or_missing_inputs(tmp_path):
    cfg, csv_text = synth_validate.build(tmp_path)
    (tmp_path / "data" / "validation").mkdir(parents=True)
    (tmp_path / "data" / "validation" / "points.csv").write_text(csv_text, encoding="utf-8")
    cfg["points"] = "data/validation/points.csv"
    with pytest.raises(ValidationError, match="run the radar processing first"):
        validate(tmp_path, cfg)


def test_cli_validate_reports_problems_plainly(scene, capsys):
    root, cfg = scene
    config = synth_validate.synth.write_config(root, cfg)
    assert main(["validate", "--config", str(config), "--allow-uncommitted"]) == 0
    assert "test half scored once" in capsys.readouterr().out
    assert main(["validate", "--config", str(config), "--allow-uncommitted"]) == 1
    assert "already been scored" in capsys.readouterr().err
    assert main(["validate", "--config", str(config), "--restore"]) == 0
    assert np.isclose(json.loads((root / "out" / "stats.json").read_text(encoding="utf-8"))["validation"]["auc"], 1.0)
