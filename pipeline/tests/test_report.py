import json

import pytest

from cutoff.__main__ import main
from cutoff.report import END, START, ReportError, results_block, update_readme

REAL = {
    "mock": False, "landslides": 1234, "area_km2": 12.3456, "roads_blocked_km": 18.04, "communities_cut_off": 7,
    "validation": {"split": "test", "n_test_landslide": 40, "n_test_forest": 45, "detection_rate": 0.725, "false_alarm_rate": 0.0889,
                   "auc": 0.8123, "threshold_db": -3.5,
                   "by_size": [{"size": "small", "n": 10, "detection_rate": 0.4}, {"size": "large", "n": 12, "detection_rate": 0.9167}]},
    "baseline_no_change_flag_rate": 0.0042, "post_event_flag_rate": 0.0311,
    "params": {"threshold_db": -3.5, "min_slope_deg": 10.0, "min_forest_hv_db": -16.0, "min_pixels": 3}, "pixel_m": 20.0,
}


def test_every_number_comes_from_the_stats():
    text = results_block(REAL)
    for expected in ("1,234", "12.35 km²", "18.0 km", "7**", "40 landslide points", "45 forest points", "**72%**", "**9%**",
                     "AUC **0.81**", "small 40% (n = 10)", "large 92% (n = 12)", "0.4%", "3.1%", "-3.5 dB", "20 m"):
        assert expected in text, expected
    assert "likely blocked" in text and "possibly cut off" in text


def test_missing_parts_are_stated_not_invented():
    stats = dict(REAL, validation=None, roads_blocked_km=None, communities_cut_off=None)
    text = results_block(stats)
    assert "not computed yet" in text and "Accuracy check: not run yet" in text
    assert "AUC" not in text and "km** of road" not in text


def test_mock_data_is_refused():
    with pytest.raises(ReportError, match="mock"):
        results_block(dict(REAL, mock=True))


def readme(tmp_path, body=f"# T\n\nintro\n\n{START}\nold text\n{END}\n\nafter\n"):
    p = tmp_path / "README.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_readme_block_is_replaced_and_the_rest_is_kept(tmp_path):
    stats = tmp_path / "stats.json"
    stats.write_text(json.dumps(REAL), encoding="utf-8")
    p = readme(tmp_path)
    update_readme(p, stats)
    out = p.read_text(encoding="utf-8")
    assert out.startswith("# T\n\nintro\n\n" + START) and out.endswith(END + "\n\nafter\n")
    assert "old text" not in out and "1,234" in out
    update_readme(p, stats)                                         # running twice changes nothing
    assert p.read_text(encoding="utf-8") == out


@pytest.mark.parametrize("body", ["no markers\n", f"{START}\n{START}\n{END}\n", f"{END}\n{START}\n", f"{START}\nonly start\n"])
def test_markers_must_be_exactly_one_pair(tmp_path, body):
    stats = tmp_path / "stats.json"
    stats.write_text(json.dumps(REAL), encoding="utf-8")
    with pytest.raises(ReportError):
        update_readme(readme(tmp_path, body), stats)


def test_cli_report(tmp_path, capsys):
    out = tmp_path / "out"
    out.mkdir()
    (out / "stats.json").write_text(json.dumps(REAL), encoding="utf-8")
    p = readme(tmp_path)
    cfg = tmp_path / "pipeline"
    cfg.mkdir()
    base = json.loads((__import__("pathlib").Path(__file__).resolve().parents[1] / "config.example.json").read_text(encoding="utf-8"))
    (cfg / "config.json").write_text(json.dumps(base), encoding="utf-8")
    assert main(["report", "--config", str(cfg / "config.json"), "--out", str(out), "--readme", str(p)]) == 0
    assert "1,234" in p.read_text(encoding="utf-8")
    (out / "stats.json").write_text(json.dumps(dict(REAL, mock=True)), encoding="utf-8")
    assert main(["report", "--config", str(cfg / "config.json"), "--out", str(out), "--readme", str(p)]) == 1
    assert "cannot write the results" in capsys.readouterr().err


def test_tiny_groups_get_a_count_not_a_rate_and_a_bad_baseline_is_said():
    stats = dict(REAL, baseline_no_change_flag_rate=0.01, post_event_flag_rate=0.005)
    stats["validation"] = dict(REAL["validation"], by_size=[{"size": "medium", "n": 20, "detection_rate": 0.5}, {"size": "large", "n": 1, "detection_rate": 1.0}])
    text = results_block(stats)
    assert "large: n = 1, too few to score" in text and "large 100%" not in text and "medium 50% (n = 20)" in text
    assert "Caution" in text and "Caution" not in results_block(REAL)
