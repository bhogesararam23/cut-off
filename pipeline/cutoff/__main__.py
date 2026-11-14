"""Command line: python -m cutoff mock|check|list|run|validate|access --config config.json"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import load_config

NOT_READY = ("list", "run", "validate", "access")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cutoff", description=__doc__)
    parser.add_argument("command", choices=("mock", "check") + NOT_READY)
    parser.add_argument("--config", help="config file (default: config.json, else config.example.json)")
    parser.add_argument("--root", help="repository root (default: parent of the config file's folder)")
    parser.add_argument("--out", help="output folder (default: 'out' from the config, under the root)")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)

    if args.command in NOT_READY:
        print(f"'{args.command}' is not implemented yet.", file=sys.stderr)
        return 2

    cfg, root = load_config(args.config)
    if args.root:
        root = Path(args.root).resolve()
    out = Path(args.out) if args.out else root / cfg["out"]

    if args.command == "mock":
        from .mock import write_mock

        files = write_mock(cfg, out)
        print(f"wrote {len(files)} mock files to {out}")
        return 0

    from .contract import check_dir

    errors = check_dir(out)
    if errors:
        print(f"{len(errors)} problem(s) in {out}:")
        for e in errors:
            print(" -", e)
        return 1
    print(f"all output files in {out} follow the data format")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
