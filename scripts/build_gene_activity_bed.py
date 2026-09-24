"""Build the N19 gene-activity ATAC panel and its bounded transfer estimate.

Deterministic, label-free gene rule:

1. every chr21 gene whose RNA detection (column nnz of the H5AD ``raw/X`` CSR)
   is at least 1% of cells;
2. the 13 candidate genes RORB, FOXP1, TLE4, BCL11B, CUX2, NEUROD2, NEUROD6,
   SOX9, PAX6, EOMES, FEZF2, TCF7L2, RORA;
3. then genes in descending label-free normalized dispersion over all cells
   (the same math as ``p22.data.nn_fold._hvg_indices``, but over all cells)
   until the transfer estimate reaches the target or 1,500 genes.

Each gene becomes the zero-based half-open window ``[max(0, start - flank),
end + flank)`` on canonical contigs only. ``raw/var`` ``start``/``end`` are
0-based half-open, verified against SOX2 (``chr3:181711924-181711925`` while the
1-based TSS is 181,711,925), so no 1-based shift is applied.

Detection and dispersion come from a single streaming pass over the CSR matrix
(cell chunks; the matrix is never densified). The transfer estimate reuses
``scripts/estimate_fragment_transfer.py``, the estimator validated to the byte
against ``configs/atac_tiebreak_measurement_contract_2026-09-21.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import estimate_fragment_transfer as est  # noqa: E402
import query_fragment_regions as qfr  # noqa: E402

CANONICAL = tuple(f"chr{i}" for i in range(1, 23)) + ("chrX",)
CANDIDATES = (
    "RORB",
    "FOXP1",
    "TLE4",
    "BCL11B",
    "CUX2",
    "NEUROD2",
    "NEUROD6",
    "SOX9",
    "PAX6",
    "EOMES",
    "FEZF2",
    "TCF7L2",
    "RORA",
)
N_MEAN_BINS = 20  # mirrors p22.data.nn_inputs.N_MEAN_BINS
DEFAULT_TARGET_BYTES = 3_500_000_000
DEFAULT_RESERVE_FRACTION = 0.0
DEFAULT_MAX_GENES = 1500
DEFAULT_FLANK = 2000
DEFAULT_CHUNK_CELLS = 8192
DEFAULT_CHR21_DETECTION = 0.01
DEFAULT_FALLBACK_DETECTION = 0.05
TARGET_SUM = 1e4  # A7 scale factor
COORDINATE_BASE = (
    "BED region = [max(0, start - flank), end + flank); H5AD raw/var start/end are "
    "0-based half-open (verified against SOX2 chr3:181711924-181711925 vs 1-based TSS "
    "181711925), so no 1-based shift is applied"
)


@dataclass
class GeneTable:
    gene_ids: np.ndarray
    names: np.ndarray
    chrom: np.ndarray
    start: np.ndarray
    end: np.ndarray

    @property
    def n_genes(self) -> int:
        return int(self.names.shape[0])


def _decode(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _read_variable(group: h5py.Group, key: str) -> np.ndarray:
    """Read a var column, expanding H5AD categorical groups."""
    obj = group[key]
    if isinstance(obj, h5py.Group):
        cats = np.array([_decode(x) for x in obj["categories"][...]], dtype=object)
        codes = np.asarray(obj["codes"][...], dtype=np.int64)
        out = np.empty(codes.shape[0], dtype=object)
        valid = codes >= 0
        out[valid] = cats[codes[valid]]
        out[~valid] = ""
        return out
    data = obj[...]
    if data.dtype.kind in ("S", "O", "U"):
        return np.array([_decode(x) for x in data], dtype=object)
    return np.asarray(data)


def read_gene_table(h5ad_path: Path, var_key: str = "raw/var") -> GeneTable:
    with h5py.File(h5ad_path, "r") as handle:
        var = handle[var_key]
        return GeneTable(
            gene_ids=_read_variable(var, "_index"),
            names=_read_variable(var, "gene_name"),
            chrom=_read_variable(var, "seqnames"),
            start=np.asarray(var["start"][...], dtype=np.int64),
            end=np.asarray(var["end"][...], dtype=np.int64),
        )


def stream_gene_stats(
    h5ad_path: Path,
    matrix_key: str = "raw/X",
    chunk_cells: int = DEFAULT_CHUNK_CELLS,
    target_sum: float = TARGET_SUM,
) -> dict:
    """Column detection and per-gene log-normalized mean/variance, all cells."""
    with h5py.File(h5ad_path, "r") as handle:
        group = handle[matrix_key]
        n_cells, n_genes = (int(x) for x in group.attrs["shape"])
        indptr = group["indptr"]
        sum_ = np.zeros(n_genes, dtype=np.float64)
        sumsq = np.zeros(n_genes, dtype=np.float64)
        nnz = np.zeros(n_genes, dtype=np.int64)
        for lo in range(0, n_cells, chunk_cells):
            hi = min(n_cells, lo + chunk_cells)
            row_ptr = np.asarray(indptr[lo : hi + 1], dtype=np.int64)
            p0, p1 = int(row_ptr[0]), int(row_ptr[-1])
            data = np.asarray(group["data"][p0:p1], dtype=np.float64)
            indices = np.asarray(group["indices"][p0:p1], dtype=np.int64)
            rows = np.repeat(np.arange(hi - lo, dtype=np.int64), np.diff(row_ptr))
            totals = np.bincount(rows, weights=data, minlength=hi - lo)
            safe = np.where(totals > 0, totals, 1.0)
            vals = np.log1p(data * (target_sum / safe[rows]))
            sum_ += np.bincount(indices, weights=vals, minlength=n_genes)
            sumsq += np.bincount(indices, weights=vals * vals, minlength=n_genes)
            nnz += np.bincount(indices, minlength=n_genes)
    mean = sum_ / n_cells
    var = np.maximum(sumsq / n_cells - mean * mean, 0.0)
    dispersion = np.divide(var, mean, out=np.zeros_like(var), where=mean > 0)
    return {
        "n_cells": n_cells,
        "n_genes": n_genes,
        "nnz": nnz,
        "mean": mean,
        "dispersion": dispersion,
    }


def normalized_dispersion_z(mean: np.ndarray, dispersion: np.ndarray) -> np.ndarray:
    """Z-score dispersion within ``N_MEAN_BINS`` mean bins (same as N2 HVG)."""
    n_genes = mean.shape[0]
    order = np.argsort(mean, kind="stable")
    ranks = np.empty(n_genes, dtype=np.int64)
    ranks[order] = np.arange(n_genes)
    bins = np.minimum((ranks * N_MEAN_BINS) // max(n_genes, 1), N_MEAN_BINS - 1)
    z = np.zeros(n_genes, dtype=np.float64)
    for b in range(N_MEAN_BINS):
        mask = bins == b
        if int(mask.sum()) > 1:
            values = dispersion[mask]
            std = values.std()
            z[mask] = (values - values.mean()) / std if std > 0 else 0.0
    return z


def region_for_gene(
    chrom: str, start: int, end: int, flank: int = DEFAULT_FLANK
) -> tuple[str, int, int] | None:
    if chrom not in CANONICAL:
        return None
    beg = max(0, int(start) - flank)
    stop = int(end) + flank
    if stop <= beg:
        return None
    return chrom, beg, stop


def region_windows(
    index: qfr.TabixIndex, region: tuple[str, int, int], window: int
) -> int:
    chunks = index.query_chunks(region[0], region[1], region[2])
    return sum(est.windows_for_chunk(s, t, window) for s, t in chunks)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass
class Selection:
    indices: list[int] = field(default_factory=list)
    priority: dict[int, str] = field(default_factory=dict)
    estimated_bytes: int = 0


def _mandatory_order(
    table: GeneTable,
    detection: np.ndarray,
    chr21_detection: float,
) -> list[tuple[int, str]]:
    name_to_indices: dict[str, list[int]] = {}
    for i, name in enumerate(table.names):
        name_to_indices.setdefault(str(name), []).append(i)
    mandatory: list[tuple[int, str]] = []
    seen: set[int] = set()
    for i in range(table.n_genes):
        if table.chrom[i] == "chr21" and detection[i] >= chr21_detection:
            mandatory.append((i, "chr21_detection"))
            seen.add(i)
    for name in CANDIDATES:
        for i in name_to_indices.get(name, []):
            if i not in seen:
                mandatory.append((i, "candidate"))
                seen.add(i)
    return mandatory


def select_genes(
    table: GeneTable,
    stats: dict,
    index: qfr.TabixIndex,
    *,
    window: int = qfr.DEFAULT_WINDOW,
    flank: int = DEFAULT_FLANK,
    target_bytes: int = DEFAULT_TARGET_BYTES,
    reserve_fraction: float = DEFAULT_RESERVE_FRACTION,
    max_genes: int = DEFAULT_MAX_GENES,
    chr21_detection: float = DEFAULT_CHR21_DETECTION,
    fallback_detection: float = DEFAULT_FALLBACK_DETECTION,
) -> dict:
    """Apply the gene rule; return the selection plus a cost audit."""
    detection = stats["nnz"] / stats["n_cells"]
    disp_z = normalized_dispersion_z(stats["mean"], stats["dispersion"])
    planning_budget = int(target_bytes * (1.0 - reserve_fraction))

    def cost(i: int) -> int:
        region = region_for_gene(
            str(table.chrom[i]), table.start[i], table.end[i], flank
        )
        return region_windows(index, region, window) * window if region else 0

    mandatory = _mandatory_order(table, detection, chr21_detection)
    mandatory_est = sum(cost(i) for i, _ in mandatory)
    fallback_applied = False
    if mandatory_est > target_bytes:
        fallback_applied = True
        mandatory = _mandatory_order(table, detection, fallback_detection)
        mandatory_est = sum(cost(i) for i, _ in mandatory)
    blocked = mandatory_est > target_bytes

    selection = Selection(priority={i: p for i, p in mandatory})
    selection.indices = [i for i, _ in mandatory]
    selection.estimated_bytes = mandatory_est

    if not blocked:
        selected = set(selection.indices)
        eligible = [
            i
            for i in range(table.n_genes)
            if i not in selected
            and detection[i] > 0
            and stats["mean"][i] > 0
            and region_for_gene(
                str(table.chrom[i]), table.start[i], table.end[i], flank
            )
            is not None
        ]
        # Round before ordering: within-bin z-scores are mathematically +/-1, and
        # float noise otherwise makes an arbitrary high-index gene outrank a
        # genuinely high-dispersion gene. Rounding restores the index tie-break.
        eligible.sort(key=lambda i: (-round(float(disp_z[i]), 9), i))
        for i in eligible:
            if len(selection.indices) >= max_genes:
                break
            c = cost(i)
            if selection.estimated_bytes + c > planning_budget:
                break
            selection.indices.append(i)
            selection.priority[i] = "dispersion"
            selection.estimated_bytes += c

    return {
        "detection": detection,
        "disp_z": disp_z,
        "planning_budget": planning_budget,
        "target_bytes": target_bytes,
        "reserve_fraction": reserve_fraction,
        "max_genes": max_genes,
        "chr21_detection": chr21_detection,
        "fallback_detection": fallback_detection,
        "fallback_applied": fallback_applied,
        "blocked": blocked,
        "selection": selection,
        "mandatory_estimate": mandatory_est,
    }


def _priority_counts(selection: Selection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for i in selection.indices:
        key = selection.priority[i]
        counts[key] = counts.get(key, 0) + 1
    return counts


def build_report(args: argparse.Namespace) -> dict:
    table = read_gene_table(args.h5ad)
    stats = stream_gene_stats(
        args.h5ad, chunk_cells=args.chunk_cells, target_sum=TARGET_SUM
    )
    index = qfr.TabixIndex.from_path(args.index_path)
    chosen = select_genes(
        table,
        stats,
        index,
        window=args.window,
        flank=args.flank,
        target_bytes=args.target_bytes,
        reserve_fraction=args.reserve_fraction,
        max_genes=args.max_genes,
        chr21_detection=args.chr21_detection,
        fallback_detection=args.fallback_detection,
    )
    selection: Selection = chosen["selection"]

    regions = []
    genes = []
    for i in selection.indices:
        region = region_for_gene(
            str(table.chrom[i]), table.start[i], table.end[i], args.flank
        )
        regions.append(region)
        genes.append(
            {
                "gene_id": str(table.gene_ids[i]),
                "gene_name": str(table.names[i]),
                "chrom": str(table.chrom[i]),
                "start": int(table.start[i]),
                "end": int(table.end[i]),
                "window_start": region[1],
                "window_end": region[2],
                "region": f"{region[0]}:{region[1]}-{region[2]}",
                "detection": float(chosen["detection"][i]),
                "dispersion_z": float(chosen["disp_z"][i]),
                "priority": selection.priority[i],
            }
        )

    estimate = est.estimate_regions(index, regions, window=args.window)
    reconciliation_ok = estimate["estimated_bytes"] == selection.estimated_bytes

    validation = None
    if args.validation_bed and Path(args.validation_bed).exists():
        v_regions = qfr.read_regions_file(str(args.validation_bed))
        v_stats = est.estimate_regions(index, v_regions, window=args.window)
        expected = args.validation_expected_bytes
        relative = abs(v_stats["estimated_bytes"] - expected) / expected
        validation = {
            "regions_file": str(args.validation_bed),
            "expected_bytes": expected,
            "estimated_bytes": v_stats["estimated_bytes"],
            "relative_error": relative,
            "within_tolerance": relative <= args.validation_tolerance,
        }

    return {
        "method": (
            "chr21 genes with RNA detection >= 1% of cells, plus 13 candidate genes, "
            "then genes in descending normalized dispersion (all cells) until the "
            "transfer estimate reaches the target or max_genes"
        ),
        "generated_at": datetime.now(UTC).isoformat(),
        "coordinate_base": COORDINATE_BASE,
        "flank": args.flank,
        "canonical_contigs_only": True,
        "window_bytes": args.window,
        "h5ad": str(args.h5ad),
        "n_cells": stats["n_cells"],
        "n_genes_total": stats["n_genes"],
        "candidates": list(CANDIDATES),
        "target_bytes": chosen["target_bytes"],
        "reserve_fraction": chosen["reserve_fraction"],
        "planning_budget": chosen["planning_budget"],
        "max_genes": chosen["max_genes"],
        "chr21_detection": chosen["chr21_detection"],
        "fallback_detection": chosen["fallback_detection"],
        "fallback_applied": chosen["fallback_applied"],
        "blocked": chosen["blocked"],
        "n_selected": len(selection.indices),
        "priority_counts": _priority_counts(selection),
        "mandatory_estimate": chosen["mandatory_estimate"],
        "estimated_bytes": estimate["estimated_bytes"],
        "estimated_n_windows": estimate["n_windows"],
        "estimated_n_chunks": estimate["n_chunks"],
        "selection_cost_reconciles": reconciliation_ok,
        "estimator_method": est.METHOD,
        "index_path": str(args.index_path),
        "index_size": Path(args.index_path).stat().st_size,
        "index_sha256": _sha256(Path(args.index_path)),
        "estimator_validation": validation,
        "genes": genes,
    }


def write_bed(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{g['chrom']}\t{g['window_start']}\t{g['window_end']}\t{g['gene_name']}"
        for g in report["genes"]
    ]
    path.write_text("".join(line + "\n" for line in lines))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5ad", type=Path, required=True)
    parser.add_argument("--index-path", type=Path, required=True)
    parser.add_argument("--bed-out", type=Path, required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--flank", type=int, default=DEFAULT_FLANK)
    parser.add_argument("--window", type=int, default=qfr.DEFAULT_WINDOW)
    parser.add_argument("--target-bytes", type=int, default=DEFAULT_TARGET_BYTES)
    parser.add_argument(
        "--reserve-fraction", type=float, default=DEFAULT_RESERVE_FRACTION
    )
    parser.add_argument("--max-genes", type=int, default=DEFAULT_MAX_GENES)
    parser.add_argument("--chunk-cells", type=int, default=DEFAULT_CHUNK_CELLS)
    parser.add_argument(
        "--chr21-detection", type=float, default=DEFAULT_CHR21_DETECTION
    )
    parser.add_argument(
        "--fallback-detection", type=float, default=DEFAULT_FALLBACK_DETECTION
    )
    parser.add_argument(
        "--validation-bed",
        type=Path,
        default=ROOT / "configs" / "atac_tiebreak_union_2026-09-21.bed",
    )
    parser.add_argument(
        "--validation-expected-bytes", type=int, default=3_171_155_968
    )
    parser.add_argument("--validation-tolerance", type=float, default=0.01)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(args)
    report["bed_path"] = str(args.bed_out)
    write_bed(args.bed_out, report)
    report["bed_sha256"] = _sha256(args.bed_out)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2) + "\n")

    summary = {
        k: report[k]
        for k in (
            "n_selected",
            "priority_counts",
            "estimated_bytes",
            "target_bytes",
            "planning_budget",
            "fallback_applied",
            "blocked",
            "selection_cost_reconciles",
            "estimator_validation",
        )
    }
    print(json.dumps(summary, indent=2))
    if report["blocked"]:
        print("gene panel exceeds target budget", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())