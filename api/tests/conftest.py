import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import create_app

REPO = Path(__file__).resolve().parents[2]
MOCK_DATA = REPO / "web" / "public" / "data"          # the committed mock files
EVENT = "panama-2026"
ORIGIN = "https://cut-off.example.com"


@pytest.fixture(scope="session")
def mock_dir() -> Path:
    assert (MOCK_DATA / EVENT / "event.json").is_file()
    return MOCK_DATA


@pytest.fixture(scope="session")
def client(mock_dir) -> TestClient:
    app = create_app(data_dir=mock_dir, cors_origins=[ORIGIN, "http://localhost:5173"])
    return TestClient(app, raise_server_exceptions=False)


def read_file(mock_dir: Path, name: str):
    return json.loads((mock_dir / EVENT / name).read_text(encoding="utf-8"))


@pytest.fixture
def tree(tmp_path, mock_dir):
    """A private copy of the mock data (data/panama-2026) with secrets planted outside the event folder."""
    base = tmp_path / "data"
    shutil.copytree(mock_dir / EVENT, base / EVENT)
    (base / "root-secret.json").write_text('{"leak": "TOP-SECRET-ROOT"}', encoding="utf-8")
    (tmp_path / "secret.json").write_text('{"leak": "TOP-SECRET-PARENT"}', encoding="utf-8")
    (tmp_path / "passwd").write_text("TOP-SECRET-PASSWD", encoding="utf-8")
    return base


@pytest.fixture
def tree_client(tree) -> TestClient:
    return TestClient(create_app(data_dir=tree, cors_origins=[ORIGIN]), raise_server_exceptions=False)
