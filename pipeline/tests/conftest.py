import json
from pathlib import Path

import pytest

PIPELINE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PIPELINE_DIR.parent


@pytest.fixture(scope="session")
def cfg() -> dict:
    return json.loads((PIPELINE_DIR / "config.example.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def mock_dir(tmp_path_factory, cfg) -> Path:
    from cutoff.mock import write_mock

    out = tmp_path_factory.mktemp("mock")
    write_mock(cfg, out)
    return out
