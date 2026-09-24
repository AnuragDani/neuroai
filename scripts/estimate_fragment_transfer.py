"""Estimate fragment transfer bytes from a local tabix index.

The estimator mirrors the reader in ``scripts/query_fragment_regions.py``:

* ``TabixIndex.query_chunks`` returns merged BGZF *virtual* spans ``(start, stop)``
  for a region;
* the reader always fetches at least one ``DEFAULT_WINDOW``-sized block per chunk,
  and a chunk that spans more than one window costs one window per window-sized step.

Therefore the estimated bytes are::

    sum over regions, sum over merged chunks
        max(1, ceil((stop_coffset - start_coffset) / window)) * window

This reproduces, to the byte, the historical estimates recorded in the tie-break
measurement contract (480 regions -> 3,284,402,176; 465-region union -> 3,171,155,968).

Usage::

    python scripts/estimate_fragment_transfer.py \
        --regions-bed configs/atac_tiebreak_union_2026-09-21.bed \
        --index-path SRC_WT/reports/generated/development_region_set_20260921/fragment.tbi \
        --expect-bytes 3171155968
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import query_fragment_regions as qfr  # noqa: E402

METHOD = (
    "sum over regions of merged tabix chunk byte spans, each costing at least one "
    "262144-byte window, rounded up to whole windows"
)


def windows_for_chunk(start_voffset: int, stop_voffset: int, window: int) -> int:
    """Number of reader windows fetched for one merged BGZF chunk."""
    if window <= 0:
        raise ValueError("window must be positive")
    span = (stop_voffset >> 16) - (start_voffset >> 16)
    if span < 0:
        raise ValueError("chunk stop offset precedes start offset")
    return max(1, -(-span // window))


def estimate_regions(
    index: qfr.TabixIndex,
    regions: list[tuple[str, int, int]],
    window: int = qfr.DEFAULT_WINDOW,
) -> dict:
    """Estimate bytes for ``regions`` using ``index``; no network access."""
    n_chunks = 0
    n_windows = 0
    per_region = []
    for name, beg, end in regions:
        chunks = index.query_chunks(name, beg, end)
        region_windows = sum(
            windows_for_chunk(start, stop, window) for start, stop in chunks
        )
        n_chunks += len(chunks)
        n_windows += region_windows
        per_region.append(
            {
                "region": f"{name}:{beg}-{end}",
                "chunks": len(chunks),
                "windows": region_windows,
                "bytes": region_windows * window,
            }
        )
    return {
        "n_regions": len(regions),
        "n_chunks": n_chunks,
        "n_windows": n_windows,
        "window_bytes": window,
        "estimated_bytes": n_windows * window,
        "per_region": per_region,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regions-bed", required=True, type=Path)
    parser.add_argument("--index-path", required=True, type=Path)
    parser.add_argument("--window", type=int, default=qfr.DEFAULT_WINDOW)
    parser.add_argument(
        "--expect-bytes",
        type=int,
        default=None,
        help="fail if the estimate differs by more than --tolerance",
    )
    parser.add_argument("--tolerance", type=float, default=0.01)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument(
        "--include-per-region",
        action="store_true",
        help="keep the per-region breakdown in stdout/json (omitted by default)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    regions = qfr.read_regions_file(str(args.regions_bed))
    index = qfr.TabixIndex.from_path(args.index_path)
    stats = estimate_regions(index, regions, window=args.window)

    if not args.include_per_region:
        stats.pop("per_region", None)

    report = {
        "method": METHOD,
        "generated_at": datetime.now(UTC).isoformat(),
        "regions_file": str(args.regions_bed),
        "regions_file_sha256": _sha256(args.regions_bed),
        "index_path": str(args.index_path),
        "index_size": args.index_path.stat().st_size,
        "index_sha256": _sha256(args.index_path),
        **stats,
    }

    exit_code = 0
    if args.expect_bytes is not None:
        expected = args.expect_bytes
        error = abs(report["estimated_bytes"] - expected) / expected
        report["expected_bytes"] = expected
        report["relative_error"] = error
        report["within_tolerance"] = error <= args.tolerance
        if error > args.tolerance:
            print(
                f"estimate {report['estimated_bytes']} differs from expected "
                f"{expected} by {error:.4%} > {args.tolerance:.2%}",
                file=sys.stderr,
            )
            exit_code = 2

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2) + "\n")

    print(json.dumps(report, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())