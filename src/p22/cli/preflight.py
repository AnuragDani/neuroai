"""Run a metadata preflight on a local table or a local ``.h5ad`` file.

Usage::

    python -m p22.cli.preflight --metadata-csv path.csv --out report.json
    python -m p22.cli.preflight --h5ad tiny.h5ad --out report.json

The command reads local paths only. It never downloads and never trains.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from p22.data.preflight import inspect_h5ad, inspect_metadata, write_preflight_report
from p22.data.schema import ACCESS_FACTS, STATUS_BLOCKED


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--metadata-csv", type=Path, help="local per-cell metadata table")
    source.add_argument("--h5ad", type=Path, help="local .h5ad file")
    parser.add_argument("--out", type=Path, help="where to write the JSON report")
    parser.add_argument(
        "--access-fact",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help=f"record one access fact; recognised names: {', '.join(ACCESS_FACTS)}",
    )
    parser.add_argument("--data-mode", default="synthetic")
    parser.add_argument(
        "--fail-on-blocked",
        action="store_true",
        help="exit non-zero when the report status is BLOCKED",
    )
    return parser


def _parse_access_facts(entries: list[str]) -> dict[str, str]:
    facts: dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            raise ValueError(f"expected NAME=VALUE, got {entry!r}")
        name, value = entry.split("=", 1)
        facts[name.strip()] = value.strip()
    return facts


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    access_facts = _parse_access_facts(args.access_fact)

    if args.metadata_csv is not None:
        frame = pd.read_csv(args.metadata_csv)
        report = inspect_metadata(
            frame,
            access_facts=access_facts,
            data_mode=args.data_mode,
            source=f"local file {Path(args.metadata_csv).name}",
        )
    else:
        report = inspect_h5ad(args.h5ad, access_facts=access_facts, data_mode=args.data_mode)

    for line in report.summary_lines():
        print(line)

    if args.out is not None:
        written = write_preflight_report(report, args.out)
        print(f"report written: {written}")
    else:
        print(json.dumps(report.to_dict(), indent=2, default=str))

    if args.fail_on_blocked and report.status == STATUS_BLOCKED:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
