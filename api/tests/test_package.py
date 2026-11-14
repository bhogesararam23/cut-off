"""The packaging script: only the right files go into the zip, and mock data is refused by default."""

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "package_api.py"
spec = importlib.util.spec_from_file_location("package_api", SCRIPT)
package_api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package_api)


@pytest.fixture
def repo(tmp_path):
    api = tmp_path / "api"
    (api / "tests").mkdir(parents=True)
    (api / ".venv").mkdir()
    for name in package_api.API_FILES:
        (api / name).write_text(f"# {name}\n", encoding="utf-8")
    (api / "tests" / "test_x.py").write_text("x", encoding="utf-8")
    (api / "requirements-dev.txt").write_text("pytest\n", encoding="utf-8")
    (api / ".venv" / "junk.py").write_text("x", encoding="utf-8")
    ev = tmp_path / "web" / "public" / "data" / "panama-2026"
    ev.mkdir(parents=True)
    (ev / "event.json").write_text(json.dumps({"mock": False}), encoding="utf-8")
    (ev / "stats.json").write_text(json.dumps({"mock": False}), encoding="utf-8")
    (ev / "roads.geojson").write_text("{}", encoding="utf-8")
    (ev / "a.png").write_bytes(b"png")
    # things that must never be packaged
    for junk in (".env", "notes.txt", "run.py", "UPPER.json", ".hidden.json", "x" * 120 + ".png", "a b.png"):
        (ev / junk).write_text("no", encoding="utf-8")
    (ev / "sub").mkdir()
    (ev / "sub" / "deep.json").write_text("{}", encoding="utf-8")
    (tmp_path / "web" / "public" / "data" / "Bad Event").mkdir()
    (tmp_path / "web" / "public" / "data" / "Bad Event" / "event.json").write_text("{}", encoding="utf-8")
    (tmp_path / "web" / "public" / "data" / "stray.json").write_text("{}", encoding="utf-8")
    return tmp_path


def names(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        return sorted(z.namelist())


def test_only_the_expected_files_are_packaged(repo, tmp_path):
    out = tmp_path / "out" / "pkg.zip"
    package_api.build(repo, out)
    assert names(out) == sorted(["main.py", "models.py", "store.py", "requirements.txt", "data/panama-2026/a.png",
                                 "data/panama-2026/event.json", "data/panama-2026/roads.geojson", "data/panama-2026/stats.json"])


def test_mock_data_is_refused_unless_allowed(repo, tmp_path):
    (repo / "web" / "public" / "data" / "panama-2026" / "stats.json").write_text(json.dumps({"mock": True}), encoding="utf-8")
    with pytest.raises(package_api.PackageError, match="mock"):
        package_api.build(repo, tmp_path / "a.zip")
    assert not (tmp_path / "a.zip").exists()
    package_api.build(repo, tmp_path / "b.zip", allow_mock=True)
    assert (tmp_path / "b.zip").is_file()


def test_the_zip_is_the_same_every_time(repo, tmp_path):
    package_api.build(repo, tmp_path / "1.zip")
    package_api.build(repo, tmp_path / "2.zip")
    assert (tmp_path / "1.zip").read_bytes() == (tmp_path / "2.zip").read_bytes()


def test_missing_pieces_are_reported(repo, tmp_path):
    (repo / "api" / "store.py").unlink()
    with pytest.raises(package_api.PackageError, match="store.py"):
        package_api.build(repo, tmp_path / "x.zip")


def test_empty_data_folder_is_reported(repo, tmp_path):
    (repo / "web" / "public" / "data" / "panama-2026" / "event.json").unlink()
    with pytest.raises(package_api.PackageError, match="event.json"):
        package_api.build(repo, tmp_path / "x.zip")


def test_the_real_repository_packages_with_the_staging_flag(tmp_path):
    out = tmp_path / "real.zip"
    package_api.build(Path(__file__).resolve().parents[2], out, allow_mock=True)
    inside = names(out)
    assert "main.py" in inside and "data/panama-2026/event.json" in inside
    assert not any(n.startswith(("tests/", ".venv/")) or n.endswith((".py",)) and n.startswith("data/") for n in inside)
