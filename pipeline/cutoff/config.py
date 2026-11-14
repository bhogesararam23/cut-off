"""Load the pipeline configuration. Paths inside it are relative to the repository root."""

from __future__ import annotations

import json
from pathlib import Path


def find_config(path: str | None) -> Path:
    """Return the config file to use: the given one, else config.json, else config.example.json."""
    if path:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"config file not found: {p}")
        return p
    for name in ("config.json", "config.example.json"):
        p = Path(name)
        if p.is_file():
            return p
    raise FileNotFoundError("no config.json or config.example.json in the current folder")


def load_config(path: str | None) -> tuple[dict, Path]:
    """Return (config dict, repository root). The root is the parent of the config file's folder."""
    p = find_config(path).resolve()
    with p.open(encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg, p.parent.parent
