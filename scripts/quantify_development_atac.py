"""Quantify the frozen development region set into a real ATAC count matrix.

This is the development ingestion adapter the paired study was missing: it takes
a frozen training-fold region set and the open, indexed CELLxGENE ATAC fragment
and recovers a sparse ``regions x cells`` measured count matrix by bounded remote
tabix queries. It reuses the validated random-access reader
(``scripts/query_fragment_regions.py``) and adds concurrent region execution plus
count-matrix assembly and provenance.

It does not download the fragment, does not approve a feature contract and does
not train. The region set must already be frozen (see
``scripts/freeze_development_region_set.py``); this step only measures it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import query_fragment_regions as qfr  # noqa: E402


class IncompleteQueryError(ValueError):
    """Raised when a region query is truncated or leaves the retained population."""


class TransferBudgetExceeded(RuntimeError):
    """Raised when aggregate acquisition would exceed the declared byte budget."""


class _BudgetedTransport:
    """Thread-safe aggregate transfer cap shared across concurrent workers."""

    def __init__(self, inner, total_max_bytes: int):
        self._inner = inner
        self._total = total_max_bytes
        self._used = 0
        self._lock = threading.Lock()

    @property
    def used(self) -> int:
        with self._lock:
            return self._used

    def __call__(self, url: str, start: int, end: int) -> bytes:
        requested = end - start + 1
        with self._lock:
            if self._used + requested > self._total:
                raise TransferBudgetExceeded(
                    f"aggregate transfer budget {self._total} bytes would be exceeded"
                )
            self._used += requested
        return self._inner(url, start, end)


def quantify_regions(
    regions: list[tuple[str, int, int]],
    cells: list[str],
    index: qfr.TabixIndex,
    fragment_url: str,
    *,
    transport=qfr.http_range,
    window: int = qfr.DEFAULT_WINDOW,
    max_bytes: int = qfr.DEFAULT_MAX_BYTES_PER_REGION,
    workers: int = 8,
    count_mode: str = "fragment",
    unknown_policy: str = "error",
    total_max_bytes: int | None = None,
    allow_partial: bool = False,
) -> tuple[list[dict], list[dict], object]:
    """Query all regions, concurrently, returning (records, stats, matrix).

    A truncated or corrupt query is refused before a matrix is assembled unless
    ``allow_partial`` is set. Unknown barcodes are refused by default; pass
    ``unknown_policy="drop"`` to exclude them explicitly with the exclusions
    reported per region. A successful query with zero overlapping fragments is a
    valid empty region, not a failure.
    """
    if not regions:
        raise ValueError("at least one region is required")
    if type(workers) is not int or workers < 1:
        raise ValueError("workers must be a positive integer")
    if unknown_policy not in ("error", "drop"):
        raise ValueError("unknown_policy must be 'error' or 'drop'")

    budget = None
    if total_max_bytes is not None:
        budget = _BudgetedTransport(transport, int(total_max_bytes))
        transport = budget

    def run(region):
        name, beg, end = region
        return qfr.query_region(
            fragment_url,
            index,
            name,
            beg,
            end,
            transport=transport,
            window=window,
            max_bytes=max_bytes,
            count_mode=count_mode,
        )

    if workers == 1:
        stats_list = [run(region) for region in regions]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            stats_list = list(pool.map(run, regions))
    allowlist = set(cells)
    records = []
    excluded: dict[str, int] = {}
    for stats in stats_list:
        record = stats.to_dict()
        observed = set(stats.rows_by_barcode)
        unknown = observed - allowlist
        record["allowlist_size"] = len(allowlist)
        record["n_in_allowlist"] = len(observed & allowlist)
        record["n_unknown"] = len(unknown)
        record["unknown_barcodes"] = sorted(unknown)
        record["empty_region"] = stats.rows == 0
        record["join_complete"] = (not stats.truncated) and not unknown
        records.append(record)
        for barcode in unknown:
            excluded[barcode] = excluded.get(barcode, 0) + stats.rows_by_barcode[barcode]
    truncated = [record for record in records if record["truncated"]]
    if truncated and not allow_partial:
        raise IncompleteQueryError(
            f"refusing to assemble a matrix: {len(truncated)} region(s) returned "
            f"incomplete reads, e.g. {truncated[0]['region']}"
        )
    if excluded and unknown_policy == "error":
        raise IncompleteQueryError(
            f"refusing to assemble a matrix: {len(excluded)} barcode(s) outside the "
            f"retained population, e.g. {sorted(excluded)[0]}"
        )
    counts_records = [{"counts": stats.rows_by_barcode} for stats in stats_list]
    matrix = qfr.counts_matrix(regions, counts_records, cells)
    return records, [stats.to_dict() for stats in stats_list], matrix


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regions-file", required=True, type=Path)
    parser.add_argument("--index-path", required=True, type=Path)
    parser.add_argument("--fragment-url", default=qfr.DEFAULT_FRAGMENT_URL)
    parser.add_argument("--obs-h5ad", default=qfr.DEFAULT_OBS_H5AD)
    parser.add_argument("--allowlist-path", default=None)
    parser.add_argument("--window", type=int, default=qfr.DEFAULT_WINDOW)
    parser.add_argument(
        "--max-bytes-per-region", type=int, default=qfr.DEFAULT_MAX_BYTES_PER_REGION
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--count-mode", choices=qfr.COUNT_MODES, default="fragment")
    parser.add_argument("--unknown-policy", choices=("error", "drop"), default="error")
    parser.add_argument("--total-max-bytes", type=int, default=None)
    parser.add_argument("--counts-out", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.counts_out.exists() or args.out.exists():
        raise SystemExit("refusing to overwrite an existing result path")
    regions = qfr.read_regions_file(str(args.regions_file))
    index = qfr.TabixIndex.from_path(args.index_path)
    cells = qfr.load_ordered_cells(args.obs_h5ad, args.allowlist_path)
    records, _stats, matrix = quantify_regions(
        regions,
        cells,
        index,
        args.fragment_url,
        window=args.window,
        max_bytes=args.max_bytes_per_region,
        workers=args.workers,
        count_mode=args.count_mode,
        unknown_policy=args.unknown_policy,
        total_max_bytes=args.total_max_bytes,
    )
    args.counts_out.mkdir(parents=True, exist_ok=False)
    from scipy import sparse

    matrix_path = args.counts_out / "counts.npz"
    sparse.save_npz(matrix_path, matrix)
    sidecar = {
        "matrix": matrix_path.name,
        "matrix_sha256": hashlib.sha256(matrix_path.read_bytes()).hexdigest(),
        "shape": list(matrix.shape),
        "nnz": int(matrix.nnz),
        "n_cells": len(cells),
        "cells_sha256": hashlib.sha256("\n".join(cells).encode()).hexdigest(),
        "regions_file": str(args.regions_file),
        "regions_file_sha256": hashlib.sha256(args.regions_file.read_bytes()).hexdigest(),
        "count_mode": args.count_mode,
        "count_unit": qfr.COUNT_UNIT_LABELS[args.count_mode],
        "unknown_policy": args.unknown_policy,
        "total_bytes_fetched": int(sum(record["bytes_fetched"] for record in records)),
    }
    (args.counts_out / "counts.json").write_text(json.dumps(sidecar, indent=2) + "\n")
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "fragment_url": args.fragment_url,
        "index_sha256": hashlib.sha256(args.index_path.read_bytes()).hexdigest(),
        "index_header": index.header,
        "window_bytes": args.window,
        "workers": args.workers,
        "count_mode": args.count_mode,
        "count_unit": qfr.COUNT_UNIT_LABELS[args.count_mode],
        "n_regions": len(regions),
        "total_bytes_fetched": sidecar["total_bytes_fetched"],
        "n_join_complete": int(sum(record["join_complete"] for record in records)),
        "n_empty_regions": int(sum(record["empty_region"] for record in records)),
        "n_joining_any": int(sum(record["n_in_allowlist"] > 0 for record in records)),
        "regions": records,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"shape": sidecar["shape"], "nnz": sidecar["nnz"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
