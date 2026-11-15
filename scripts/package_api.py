"""Build the zip that is deployed to the hosting service for the API.

It holds only: the API code, its runtime requirements, and the data files from web/public/data (json, geojson
and png files with safe names). Tests, virtual environments, caches and anything else are left out.
It refuses to package mock data unless --allow-mock is given, so made-up results cannot go live by accident.

    python scripts/package_api.py                 # writes build/api-package.zip
    python scripts/package_api.py --allow-mock    # for a staging copy only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

API_FILES = ("main.py", "models.py", "store.py", "requirements.txt")
EVENT_RE = re.compile(r"^[a-z0-9-]{1,64}$")
FILE_RE = re.compile(r"^[a-z0-9_.-]{1,100}\.(png|webp|json|geojson)$")
FIXED_TIME = (2026, 1, 1, 0, 0, 0)          # a fixed timestamp makes the zip identical for identical input


class PackageError(Exception):
    pass


def data_files(data_dir: Path) -> list[Path]:
    """Every data file that may be served: <event>/<name> with an allowed name and extension."""
    found: list[Path] = []
    if not data_dir.is_dir():
        raise PackageError(f"data folder not found: {data_dir}")
    for event in sorted(data_dir.iterdir()):
        if event.is_symlink() or not event.is_dir() or not EVENT_RE.fullmatch(event.name):
            continue
        for f in sorted(event.iterdir()):
            if f.is_file() and not f.is_symlink() and not f.name.startswith(".") and FILE_RE.fullmatch(f.name):
                found.append(f)
    if not any(f.name == "event.json" for f in found):
        raise PackageError("no event.json found in the data folder")
    return found


def check_not_mock(files: list[Path]) -> None:
    for f in files:
        if f.name in ("event.json", "stats.json") and json.loads(f.read_text(encoding="utf-8")).get("mock") is True:
            raise PackageError(f"{f.parent.name}/{f.name} says mock: true. Process the real data first, "
                               "or pass --allow-mock for a staging copy.")


def build(repo_root: Path, out_zip: Path, allow_mock: bool = False) -> list[str]:
    """Write the zip. Returns the names of the files inside it."""
    repo_root = Path(repo_root)
    api = repo_root / "api"
    for name in API_FILES:
        if not (api / name).is_file():
            raise PackageError(f"missing {api / name}")
    files = data_files(repo_root / "web" / "public" / "data")
    if not allow_mock:
        check_not_mock(files)
    out_zip = Path(out_zip)
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        entries = [(api / n, n) for n in API_FILES] + [(f, f"data/{f.parent.name}/{f.name}") for f in files]
        for src, arc in entries:
            info = zipfile.ZipInfo(arc, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, src.read_bytes())
            names.append(arc)
    return names


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(root / "build" / "api-package.zip"))
    ap.add_argument("--allow-mock", action="store_true", help="package mock data too (staging only)")
    args = ap.parse_args(argv)
    try:
        names = build(root, Path(args.out), allow_mock=args.allow_mock)
    except PackageError as e:
        print(f"cannot package: {e}", file=sys.stderr)
        return 1
    print(f"wrote {args.out}: {len(names)} files ({sum(n.startswith('data/') for n in names)} data files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
