"""The data store: names are allowlisted and resolved paths must stay inside the data folder."""

import json
import os
import subprocess
import sys

import pytest

from store import DataStore


@pytest.fixture
def tree(tmp_path):
    """data/ev-one/{event.json, a.png, notes.txt} and a secret next to data/."""
    base = tmp_path / "data"
    (base / "ev-one").mkdir(parents=True)
    (base / "ev-one" / "event.json").write_text(json.dumps({"x": 1}), encoding="utf-8")
    (base / "ev-one" / "a.png").write_bytes(b"png")
    (base / "ev-one" / "notes.txt").write_text("no", encoding="utf-8")
    (tmp_path / "secret.json").write_text('{"secret": true}', encoding="utf-8")
    (base / "stray.json").write_text("{}", encoding="utf-8")
    return base


def test_known_files_are_found(tree):
    s = DataStore(tree)
    assert s.event_ids() == ["ev-one"]
    assert s.file("ev-one", "event.json").name == "event.json"
    assert s.load_json("ev-one", "event.json") == {"x": 1}
    assert s.file("ev-one", "a.png") is not None


@pytest.mark.parametrize("event_id", [
    "..", ".", "../data", "ev-one/..", "ev-one/../ev-one", "EV-ONE", "ev_one", "ev-one ", "", "a" * 65, "ev-one\x00",
    "%2e%2e", "..%2f", "ev-one\\..", "/etc", "C:\\Windows", "missing",
])
def test_bad_event_ids_are_rejected(tree, event_id):
    s = DataStore(tree)
    assert s.event_dir(event_id) is None
    assert s.file(event_id, "event.json") is None
    assert s.load_json(event_id, "event.json") is None


@pytest.mark.parametrize("name", [
    "../secret.json", "..\\secret.json", "../../secret.json", "/etc/passwd", "ev-one/event.json", "sub/a.png",
    "notes.txt", "event.JSON", "A.png", ".hidden.json", "..json", "a.png\x00.txt", "a.png.exe", "", "a", "x" * 120 + ".png",
    "%2e%2e%2fsecret.json", "event.json ", "C:\\secret.json",
])
def test_bad_file_names_are_rejected(tree, name):
    s = DataStore(tree)
    assert s.file("ev-one", name) is None


def test_files_outside_an_event_folder_are_not_reachable(tree):
    s = DataStore(tree)
    assert s.file("ev-one", "stray.json") is None            # lives in data/, not in the event folder
    assert s.load_json("ev-one", "secret.json") is None


def test_a_link_that_leaves_the_data_folder_is_refused(tree, tmp_path):
    link = tree / "ev-one" / "leak.json"
    try:
        os.symlink(tmp_path / "secret.json", link)
    except (OSError, NotImplementedError):
        pytest.skip("cannot create symlinks here")
    assert DataStore(tree).file("ev-one", "leak.json") is None
    assert DataStore(tree).load_json("ev-one", "leak.json") is None


def _link_dir(link, target) -> bool:
    """Make `link` point at the folder `target`: a symlink, or a junction on Windows (needs no special rights)."""
    try:
        os.symlink(target, link, target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        pass
    if sys.platform == "win32":
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
        return r.returncode == 0
    return False


def test_an_event_folder_that_is_a_link_outside_is_refused(tree, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "event.json").write_text("{}", encoding="utf-8")
    if not _link_dir(tree / "evil", outside):
        pytest.skip("cannot create links here")
    s = DataStore(tree)
    assert s.event_dir("evil") is None and "evil" not in s.event_ids()
    assert s.file("evil", "event.json") is None


def test_a_link_inside_an_event_folder_to_the_outside_is_refused(tree, tmp_path):
    outside = tmp_path / "outside2"
    outside.mkdir()
    (outside / "x.json").write_text("{}", encoding="utf-8")
    if not _link_dir(tree / "ev-one" / "sub", outside):
        pytest.skip("cannot create links here")
    assert DataStore(tree).file("ev-one", "sub") is None


def test_cache_follows_file_changes(tree):
    s = DataStore(tree)
    assert s.load_json("ev-one", "event.json") == {"x": 1}
    (tree / "ev-one" / "event.json").write_text(json.dumps({"x": 2, "pad": "y" * 5}), encoding="utf-8")
    assert s.load_json("ev-one", "event.json")["x"] == 2


def test_missing_base_folder_is_fine(tmp_path):
    s = DataStore(tmp_path / "nope")
    assert s.event_ids() == [] and s.file("ev-one", "event.json") is None
