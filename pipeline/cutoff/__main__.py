"""Command line: python -m cutoff mock|check|list|run|validate|access --config config.json"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import load_config

NOT_READY = ("validate", "access")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cutoff", description=__doc__)
    parser.add_argument("command", choices=("mock", "check", "list", "run") + NOT_READY)
    parser.add_argument("--config", help="config file (default: config.json, else config.example.json)")
    parser.add_argument("--root", help="repository root (default: parent of the config file's folder)")
    parser.add_argument("--out", help="output folder (default: 'out' from the config, under the root)")
    parser.add_argument("--work", help="work folder for intermediate files (default: 'work' from the config)")
    parser.add_argument("--pairs", help="run: only these pair ids, comma separated (the primary pair is required)")
    parser.add_argument("--clean", action="store_true", help="run: delete old hv_*.png files in the output folder first")
    parser.add_argument("--start", default="2026-09-01", help="list: first date to search (UTC)")
    parser.add_argument("--end", default="2026-10-31", help="list: last date to search (UTC)")
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

    if args.command == "list":
        from .fetch import format_table, list_granules

        print(format_table(list_granules(cfg["bbox"], args.start, args.end)))
        return 0

    if args.command == "run":
        from .run import run

        try:
            summary = run(cfg, root, out=out, work=Path(args.work) if args.work else None,
                          pair_ids=args.pairs.split(",") if args.pairs else None, clean=args.clean)
        except (FileNotFoundError, ValueError) as e:
            print(f"cannot run: {e}", file=sys.stderr)
            return 1
        print("\nsummary")
        for pid, n in summary["pairs"].items():
            print(f"  pair {pid}: {n} pixels flagged")
        print(f"  landslides: {summary['landslides']} covering {summary['area_km2']} km2")
        print(f"  share of forested slope flagged: baseline (no quake) {100 * summary['baseline_flag_rate']:.2f}%, "
              f"after the quake {100 * summary['post_event_flag_rate']:.2f}%")
        print(f"  threshold used {summary['threshold_db']} dB (Otsu first guess {summary['otsu_first_guess_db']:.2f} dB)")
        if summary["baseline_flag_rate"] >= summary["post_event_flag_rate"]:
            print("  WARNING: the baseline flag rate is not lower than after the quake: the signal is weak or the method is wrong here.")
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
