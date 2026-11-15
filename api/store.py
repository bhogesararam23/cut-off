"""Reading the data folder safely.

Everything that touches the disk goes through here. Names that come from a request (event id, file name)
are checked against an allowlist first, then the fully resolved path must still lie inside the data folder.
Nothing is ever written.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

EVENT_ID_RE = re.compile(r"^[a-z0-9-]{1,64}$")
FILE_NAME_RE = re.compile(r"^[a-z0-9_.-]{1,100}\.(png|webp|json|geojson)$")
FEATURE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_JSON_BYTES = 25 * 1024 * 1024  # the output files are far smaller; this stops a runaway file


class DataStore:
    def __init__(self, base: Path):
        self.base = Path(base).resolve()
        self._cache: dict[Path, tuple[int, int, Any]] = {}

    def event_dir(self, event_id: str) -> Path | None:
        """The folder of one event, or None if the id is not allowed or the folder does not exist."""
        if not EVENT_ID_RE.fullmatch(event_id):
            return None
        d = (self.base / event_id).resolve()
        if d.parent != self.base or not d.is_dir():
            return None
        return d

    def file(self, event_id: str, name: str) -> Path | None:
        """A file inside an event folder, or None if anything about it is not allowed."""
        d = self.event_dir(event_id)
        if d is None or name.startswith(".") or not FILE_NAME_RE.fullmatch(name):
            return None
        p = (d / name).resolve()
        if p.parent != d or not p.is_file() or not p.is_relative_to(self.base):
            return None
        return p

    def event_ids(self) -> list[str]:
        if not self.base.is_dir():
            return []
        return sorted(p.name for p in self.base.iterdir() if p.is_dir() and self.event_dir(p.name) is not None
                      and (p / "event.json").is_file())

    def load_json(self, event_id: str, name: str) -> Any | None:
        """Parsed JSON of a file, or None if it does not exist. Cached until the file changes."""
        p = self.file(event_id, name)
        if p is None:
            return None
        st = p.stat()
        if st.st_size > MAX_JSON_BYTES:
            raise ValueError("file too large")
        cached = self._cache.get(p)
        if cached and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
            return cached[2]
        data = json.loads(p.read_text(encoding="utf-8"))
        self._cache[p] = (st.st_mtime_ns, st.st_size, data)
        return data
