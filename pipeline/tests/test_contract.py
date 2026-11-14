"""The output-format checker: it accepts the mock files and rejects broken ones."""

import json
import shutil

import pytest

from cutoff.contract import check_dir


def test_mock_output_follows_the_format(mock_dir):
    assert check_dir(mock_dir) == []


def test_committed_web_data_follows_the_format():
    from conftest import REPO_ROOT

    folder = REPO_ROOT / "web" / "public" / "data" / "panama-2026"
    assert check_dir(folder) == []


def test_missing_folder_is_reported(tmp_path):
    assert check_dir(tmp_path / "nope")


@pytest.fixture
def broken(mock_dir, tmp_path):
    """A fresh copy of the mock output that a test may damage."""
    dst = tmp_path / "copy"
    shutil.copytree(mock_dir, dst)
    return dst


def _edit(path, fn):
    data = json.loads(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_missing_key_is_caught(broken):
    _edit(broken / "stats.json", lambda d: d.pop("pixel_m"))
    assert any("missing key 'pixel_m'" in e for e in check_dir(broken))


def test_extra_key_is_caught(broken):
    _edit(broken / "event.json", lambda d: d.update(extra=1))
    assert any("unexpected key 'extra'" in e for e in check_dir(broken))


def test_wrong_type_is_caught(broken):
    _edit(broken / "pairs.json", lambda d: d[0].update(track="141"))
    assert any("pairs.json[0].track" in e for e in check_dir(broken))


def test_bad_enum_is_caught(broken):
    _edit(broken / "roads.geojson", lambda d: d["features"][0]["properties"].update(status="closed"))
    assert any("status" in e for e in check_dir(broken))


def test_confidence_rule_is_enforced(broken):
    def flip(d):
        p = d["features"][0]["properties"]
        p["confidence"] = "high" if p["confidence"] != "high" else "low"

    _edit(broken / "landslides.geojson", flip)
    assert any("does not follow the rule" in e for e in check_dir(broken))


def test_road_status_must_match_distance(broken):
    _edit(broken / "roads.geojson", lambda d: d["features"][0]["properties"].update(status="clear"))
    assert any("clear road" in e for e in check_dir(broken))


def test_coordinate_precision_is_enforced(broken):
    _edit(broken / "communities.geojson", lambda d: d["features"][0]["geometry"].update(coordinates=[-80.1234567, 7.5]))
    assert any("6 decimals" in e for e in check_dir(broken))


def test_missing_png_is_caught(broken):
    (broken / "hv_change_t141d.png").unlink()
    assert any("hv_change_t141d.png" in e for e in check_dir(broken))


def test_mock_flags_must_agree(broken):
    _edit(broken / "event.json", lambda d: d.update(mock=False))
    assert any("mock" in e for e in check_dir(broken))


def test_validation_may_be_null(broken):
    _edit(broken / "stats.json", lambda d: d.update(validation=None))
    assert check_dir(broken) == []
