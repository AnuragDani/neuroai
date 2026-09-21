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
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import query_fragment_regions as qfr  # noqa: E402


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
) -> tuple[list[dict], list[dict], object]:
    """Query all regions, concurrently, returning (records, stats, matrix)."""
    if not regions:
        raise ValueError("at least one region is required")
    if type(workers) is not int or workers < 1:
        raise ValueError("workers must be a positive integer")

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
        )

    if workers == 1:
        stats_list = [run(region) for region in regions]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            stats_list = list(pool.map(run, regions))
    allowlist = set(cells)
    records = []
    for stats in stats_list:
        record = stats.to_dict()
        observed = set(stats.rows_by_barcode)
        record["allowlist_size"] = len(allowlist)
        record["n_in_allowlist"] = len(observed & allowlist)
        record["n_unknown"] = len(observed - allowlist)
        record["join_complete"] = bool(observed) and not (observed - allowlist)
        records.append(record)
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
    parser.add_argument("--count-unit", default="fragment_overlap_sum")
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
        "count_unit": args.count_unit,
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
        "n_regions": len(regions),
        "total_bytes_fetched": sidecar["total_bytes_fetched"],
        "n_join_complete": int(sum(record["join_complete"] for record in records)),
        "n_joining_any": int(sum(record["n_in_allowlist"] > 0 for record in records)),
        "regions": records,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"shape": sidecar["shape"], "nnz": sidecar["nnz"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
