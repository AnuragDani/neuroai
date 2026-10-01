#!/usr/bin/env python3
"""Q3 fold-specific ATAC regulatory/structural coverage report.

Reports all 25 training-only 256-region panels (5 outer folds × 5 repeats),
exact count semantics, genome/annotation provenance, donor×type coverage, and
keeps structural measured coverage distinct from biological regulatory adequacy.
No fits, downloads, package installs, or recount contracts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import anndata as ad
import numpy as np
import pandas as pd
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from p22.data.nn_inputs import _read_regions  # noqa: E402

DEFAULT_H5AD = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/data/real/"
    "f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
)
DEFAULT_ATAC = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22-gnhf-worktrees/"
    "p22-results-executio-debda8/reports/generated/"
    "atac_tiebreak_measured_20260921/counts/counts.npz"
)
DEFAULT_BED = ROOT / "configs" / "atac_tiebreak_union_2026-09-21.bed"
DEFAULT_REGION_SETS = ROOT / "configs" / "atac_tiebreak_region_sets_2026-09-21.json"
DEFAULT_CONTRACT = ROOT / "configs" / "atac_tiebreak_measurement_contract_2026-09-21.json"
DEFAULT_GENE_ACTIVITY_BED = ROOT / "configs" / "nn_gene_activity_2026-09-23.bed"
DEFAULT_OUT_DIR = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "next_stage_20260930"
)
EXPECTED_MATRIX_SHA256 = (
    "5f13c089c0b598c45323d0afc874f96bdf7d4074307c3c01dc40129862d9f969"
)
EXPECTED_BED_SHA256 = (
    "d20d437ac96401746c20ff3645c464bc668ac7ed942bfb709a5bc667ef26bc23"
)
EXPECTED_REGION_SETS_SHA256 = (
    "13f630a6777a059db4ac1b5f17b397976030e0b0e29193e2bc09eab24dc46407"
)
EXPECTED_ORDERED_CELLS_SHA256 = (
    "7a56c2a906f66b528dd673f944c067a006d4f09127eda70ced4155c281a09e53"
)
CELL_TYPE_ORDER = (
    "AST",
    "IPC",
    "IPC_prol",
    "MIC",
    "NEU_CALB2",
    "NEU_CUX2",
    "NEU_RELN",
    "NEU_RORB",
    "NEU_SST",
    "NEU_TLE4",
    "NEU_low",
    "OPC",
    "RG",
    "RG_prol",
    "VASC",
)
GENE_FLANK_BP = 2000


class CoverageError(RuntimeError):
    """Nonzero-exit coverage failure."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(items: list[str]) -> str:
    return hashlib.sha256("\n".join(items).encode()).hexdigest()


def parse_region(region: str) -> tuple[str, int, int]:
    chrom, span = region.split(":")
    start_s, end_s = span.split("-")
    return chrom, int(start_s), int(end_s)


def load_gene_intervals(h5ad_path: Path) -> list[tuple[str, int, int]]:
    adata = ad.read_h5ad(h5ad_path, backed="r")
    try:
        chrom = adata.var["seqnames"].astype(str).to_numpy()
        start = adata.var["start"].to_numpy(dtype=np.int64)
        end = adata.var["end"].to_numpy(dtype=np.int64)
    finally:
        adata.file.close()
    out: list[tuple[str, int, int]] = []
    for c, s, e in zip(chrom, start, end, strict=True):
        if str(c).startswith("chr") and int(e) > int(s):
            out.append((str(c), int(s), int(e)))
    return out


def load_bed_intervals(path: Path) -> list[tuple[str, int, int, str]]:
    rows: list[tuple[str, int, int, str]] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        name = fields[3] if len(fields) > 3 else ""
        rows.append((fields[0], int(fields[1]), int(fields[2]), name))
    return rows


def interval_overlap_count(
    regions: list[str],
    annotation: list[tuple[str, int, int]] | list[tuple[str, int, int, str]],
    *,
    flank: int = 0,
) -> int:
    by_chrom: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for item in annotation:
        chrom, start, end = item[0], int(item[1]), int(item[2])
        by_chrom[chrom].append((max(0, start - flank), end + flank))
    for chrom in by_chrom:
        by_chrom[chrom].sort()
    hits = 0
    for region in regions:
        chrom, start, end = parse_region(region)
        intervals = by_chrom.get(chrom, ())
        lo, hi = 0, len(intervals)
        while lo < hi:
            mid = (lo + hi) // 2
            if intervals[mid][1] <= start:
                lo = mid + 1
            else:
                hi = mid
        for i in range(lo, len(intervals)):
            g_start, g_end = intervals[i]
            if g_start >= end:
                break
            if g_start < end and g_end > start:
                hits += 1
                break
    return hits


def ordered_cell_ids(h5ad_path: Path) -> list[str]:
    adata = ad.read_h5ad(h5ad_path, backed="r")
    try:
        return [str(x) for x in adata.obs_names.tolist()]
    finally:
        adata.file.close()


def load_obs(h5ad_path: Path) -> pd.DataFrame:
    adata = ad.read_h5ad(h5ad_path, backed="r")
    try:
        obs = adata.obs[
            ["donor_id", "author_cell_type", "library", "nCount_ATAC", "nCount_RNA"]
        ].copy()
    finally:
        adata.file.close()
    obs.index = obs.index.astype(str)
    for col in ("donor_id", "author_cell_type", "library"):
        obs[col] = obs[col].astype(str)
    return obs


def panel_matrix_stats(
    matrix_csr: sparse.csr_matrix,
    row_indices: np.ndarray,
    obs: pd.DataFrame,
) -> dict[str, Any]:
    sub = matrix_csr[row_indices].tocsc()
    nnz_cell = np.diff(sub.indptr).astype(np.int64)
    depth = np.asarray(sub.sum(axis=0)).ravel().astype(np.float64)
    per_type: list[dict[str, Any]] = []
    donors = obs["donor_id"].to_numpy()
    types = obs["author_cell_type"].to_numpy()
    for cell_type in CELL_TYPE_ORDER:
        mask = types == cell_type
        idx = np.flatnonzero(mask)
        nnz = nnz_cell[idx]
        dep = depth[idx]
        donor_ids = sorted(set(donors[idx].tolist()))
        donors_gt_half_zero = 0
        for donor in donor_ids:
            dmask = donors[idx] == donor
            if int(dmask.sum()) and float((nnz[dmask] == 0).mean()) > 0.5:
                donors_gt_half_zero += 1
        per_type.append(
            {
                "cell_type": cell_type,
                "n_cells": int(mask.sum()),
                "zero_cell_fraction": float((nnz == 0).mean()) if idx.size else 0.0,
                "median_nonzero_regions": float(np.median(nnz)) if idx.size else 0.0,
                "median_fragment_overlaps": float(np.median(dep)) if idx.size else 0.0,
                "n_donors": int(len(donor_ids)),
                "donors_zero_fraction_gt_0.5": int(donors_gt_half_zero),
            }
        )
    return {
        "zero_cell_fraction": float((nnz_cell == 0).mean()),
        "median_nonzero_regions": float(np.median(nnz_cell)),
        "median_fragment_overlaps": float(np.median(depth)),
        "mean_fragment_overlaps": float(depth.mean()),
        "n_cells_all_zero": int((nnz_cell == 0).sum()),
        "per_type": per_type,
        "_nnz_cell": nnz_cell,
        "_depth": depth,
    }


def chr21_depth_fraction(
    matrix_csr: sparse.csr_matrix,
    row_indices: np.ndarray,
    region_chrom: np.ndarray,
) -> float:
    chroms = region_chrom[row_indices]
    chr21_rows = row_indices[chroms == "chr21"]
    if chr21_rows.size == 0:
        return 0.0
    total = float(matrix_csr[row_indices].sum())
    if total <= 0:
        return 0.0
    return float(matrix_csr[chr21_rows].sum()) / total


def build_coverage(
    *,
    h5ad_path: Path,
    atac_npz: Path,
    union_bed: Path,
    region_sets_path: Path,
    contract_path: Path,
    gene_activity_bed: Path,
    date: str = "2026-09-30",
) -> dict[str, Any]:
    for path, label in (
        (h5ad_path, "h5ad"),
        (atac_npz, "ATAC counts"),
        (union_bed, "union BED"),
        (region_sets_path, "region sets"),
        (contract_path, "measurement contract"),
        (gene_activity_bed, "gene-activity BED"),
    ):
        if not path.is_file():
            raise CoverageError(f"{label} not found: {path}")

    matrix_sha = sha256_file(atac_npz)
    bed_sha = sha256_file(union_bed)
    region_sets_sha = sha256_file(region_sets_path)
    cells = ordered_cell_ids(h5ad_path)
    ordered_sha = sha256_text(cells)
    if matrix_sha != EXPECTED_MATRIX_SHA256:
        raise CoverageError(f"matrix sha256 mismatch: {matrix_sha}")
    if bed_sha != EXPECTED_BED_SHA256:
        raise CoverageError(f"BED sha256 mismatch: {bed_sha}")
    if region_sets_sha != EXPECTED_REGION_SETS_SHA256:
        raise CoverageError(f"region sets sha256 mismatch: {region_sets_sha}")
    if ordered_sha != EXPECTED_ORDERED_CELLS_SHA256:
        raise CoverageError(f"ordered-cell sha256 mismatch: {ordered_sha}")

    regions, region_chrom = _read_regions(union_bed)
    region_index = {region: i for i, region in enumerate(regions)}
    if len(regions) != 465:
        raise CoverageError(f"expected 465 union regions, found {len(regions)}")

    region_sets = json.loads(region_sets_path.read_text())
    contract = json.loads(contract_path.read_text())
    if int(region_sets.get("n_folds", -1)) != 25:
        raise CoverageError("region sets n_folds must be 25 (5 folds × 5 repeats)")
    if len(region_sets.get("per_fold", [])) != 25:
        raise CoverageError("expected exactly 25 per_fold panel entries")

    obs = load_obs(h5ad_path)
    if len(obs) != len(cells):
        raise CoverageError("obs length does not match ordered cells")
    if list(obs.index) != cells:
        raise CoverageError("obs order does not match H5AD cell order")

    matrix = sparse.load_npz(atac_npz).tocsr()
    if matrix.shape != (465, len(cells)):
        raise CoverageError(f"unexpected matrix shape {matrix.shape}")
    if np.any(matrix.data < 0):
        raise CoverageError("negative counts present")

    gene_intervals = load_gene_intervals(h5ad_path)
    ga_intervals = load_bed_intervals(gene_activity_bed)

    panels: list[dict[str, Any]] = []
    for entry in region_sets["per_fold"]:
        panel_regions = list(entry["regions"])
        if len(panel_regions) != 256:
            raise CoverageError(
                f"fold={entry['fold']} repeat={entry['repeat']}: "
                f"expected 256 regions, found {len(panel_regions)}"
            )
        missing = [r for r in panel_regions if r not in region_index]
        if missing:
            raise CoverageError(
                f"panel regions missing from union BED/matrix: {missing[:5]}"
            )
        if entry.get("regions_sha256"):
            recomputed = sha256_text(panel_regions)
            if recomputed != entry["regions_sha256"]:
                raise CoverageError(
                    f"regions_sha256 mismatch fold={entry['fold']} "
                    f"repeat={entry['repeat']}"
                )
        rows = np.asarray([region_index[r] for r in panel_regions], dtype=np.int64)
        stats = panel_matrix_stats(matrix, rows, obs)
        nnz_cell = stats.pop("_nnz_cell")
        depth = stats.pop("_depth")
        n_chr21 = int(sum(1 for r in panel_regions if r.startswith("chr21:")))
        gene_body = interval_overlap_count(panel_regions, gene_intervals, flank=0)
        gene_flank = interval_overlap_count(
            panel_regions, gene_intervals, flank=GENE_FLANK_BP
        )
        ga_overlap = interval_overlap_count(panel_regions, ga_intervals, flank=0)
        panels.append(
            {
                "fold": int(entry["fold"]),
                "repeat": int(entry["repeat"]),
                "split_seed": entry.get("split_seed"),
                "n_train_donors": int(entry["n_train_donors"]),
                "n_test_donors": int(entry["n_test_donors"]),
                "train_donors": list(entry["train_donors"]),
                "test_donors": list(entry["test_donors"]),
                "n_regions": 256,
                "regions_sha256": entry["regions_sha256"],
                "n_chr21_regions": n_chr21,
                "chr21_region_fraction": n_chr21 / 256.0,
                "chr21_fragment_overlap_fraction": chr21_depth_fraction(
                    matrix, rows, region_chrom
                ),
                "zero_cell_fraction": stats["zero_cell_fraction"],
                "median_nonzero_regions": stats["median_nonzero_regions"],
                "median_fragment_overlaps": stats["median_fragment_overlaps"],
                "mean_fragment_overlaps": stats["mean_fragment_overlaps"],
                "n_cells_all_zero": stats["n_cells_all_zero"],
                "gene_body_overlap_regions": gene_body,
                "gene_body_overlap_fraction": gene_body / 256.0,
                "gene_flank2kb_overlap_regions": gene_flank,
                "gene_flank2kb_overlap_fraction": gene_flank / 256.0,
                "gene_activity_bed_overlap_regions": ga_overlap,
                "gene_activity_bed_overlap_fraction": ga_overlap / 256.0,
                "per_type": stats["per_type"],
            }
        )
        del nnz_cell, depth

    zero_fracs = [p["zero_cell_fraction"] for p in panels]
    gene_body_fracs = [p["gene_body_overlap_fraction"] for p in panels]
    chr21_fracs = [p["chr21_region_fraction"] for p in panels]

    structural = {
        "label": "STRUCTURAL_COVERAGE_PASS",
        "meaning": (
            "All 25 panels are training-library-selected 256-region subsets of the "
            "exact counted 465-region union; hashes, dimensions, nonnegative counts, "
            "and panel∈union membership hold. Measured zeros are retained."
        ),
        "checks": {
            "n_panels": 25,
            "panel_size": 256,
            "union_regions": 465,
            "matrix_sha256": matrix_sha,
            "bed_sha256": bed_sha,
            "region_sets_sha256": region_sets_sha,
            "ordered_cells_sha256": ordered_sha,
            "all_panel_regions_in_union": True,
            "negative_counts": False,
            "unmeasured_peaks_filled_as_biological_zero": False,
        },
    }
    biological = {
        "label": "REGULATORY_ADEQUACY_UNRESOLVED",
        "meaning": (
            "Prevalence/tie-break panels and gene-interval overlaps are descriptive. "
            "Overlap counts do not prove regulatory function; missing annotations "
            "remain unknown. Cannot authorize a biological regulatory-feature claim."
        ),
        "annotation_sources": {
            "genome_build": contract["source"]["genome_build"],
            "interval_convention": region_sets["interval_convention"],
            "count_unit": region_sets["count_unit"],
            "selection_rule": region_sets["selection_rule"],
            "tie_break_salt": region_sets["tie_break_salt"],
            "gene_intervals": (
                "H5AD raw/var seqnames/start/end (0-based half-open; A9); "
                f"n_intervals={len(gene_intervals)}"
            ),
            "gene_activity_bed": str(gene_activity_bed),
            "gene_activity_bed_sha256": sha256_file(gene_activity_bed),
            "regulatory_element_catalog": "ABSENT_IN_REPO",
        },
    }

    alternate = {
        "proposed": True,
        "representation": (
            "Existing gene-activity exact-count panel "
            "(configs/nn_gene_activity_2026-09-23.bed + measured counts), "
            "already quantified under a separate contract"
        ),
        "reason": (
            "Measured deficiency for regulatory questions: fold panels are "
            "prevalence-selected intervals without a regulatory-element annotation "
            "gate. Gene-linked exact counts reuse existing measurements; no new "
            "interval recount and no filling unmeasured peaks with biological zero."
        ),
        "does_not_authorize": (
            "Biological cell-state fit (Q2 ENDPOINT_UNRESOLVED) or regulatory "
            "adequacy PASS; remains a candidate representation comparison for Q6+"
        ),
    }

    return {
        "record_type": "next_stage_q3_regulatory_coverage",
        "date": date,
        "disposition": "REGULATORY_ADEQUACY_UNRESOLVED",
        "structural_adequacy": structural,
        "biological_regulatory_adequacy": biological,
        "count_semantics": {
            "count_unit": "unique_fragment_overlap",
            "genome_build": contract["source"]["genome_build"],
            "interval_convention": region_sets["interval_convention"],
            "matrix_orientation": "regions × cells",
            "source_contract": str(contract_path),
        },
        "inputs": {
            "h5ad": str(h5ad_path),
            "atac_counts": str(atac_npz),
            "union_bed": str(union_bed),
            "region_sets": str(region_sets_path),
            "matrix_sha256": matrix_sha,
            "bed_sha256": bed_sha,
            "region_sets_sha256": region_sets_sha,
            "ordered_cells_sha256": ordered_sha,
            "n_cells": len(cells),
            "n_donors": int(obs["donor_id"].nunique()),
        },
        "summary": {
            "n_panels": 25,
            "outer_folds": 5,
            "repeats": 5,
            "panel_size": 256,
            "union_regions": 465,
            "zero_cell_fraction_min": float(min(zero_fracs)),
            "zero_cell_fraction_max": float(max(zero_fracs)),
            "zero_cell_fraction_median": float(np.median(zero_fracs)),
            "gene_body_overlap_fraction_min": float(min(gene_body_fracs)),
            "gene_body_overlap_fraction_max": float(max(gene_body_fracs)),
            "gene_body_overlap_fraction_median": float(np.median(gene_body_fracs)),
            "chr21_region_fraction_min": float(min(chr21_fracs)),
            "chr21_region_fraction_max": float(max(chr21_fracs)),
            "chr21_region_fraction_median": float(np.median(chr21_fracs)),
        },
        "panels": panels,
        "alternate_representation": alternate,
        "limits": [
            "Structural PASS is not regulatory adequacy.",
            "Gene/TSS overlap counts are not functional regulatory proof.",
            "No unmeasured peaks filled with biological zero.",
            "Cell-level depth ≠ donor-level replication.",
            "Q2 ENDPOINT_UNRESOLVED still blocks biological cell-state fits.",
        ],
    }


def independent_panel_replay(
    *,
    coverage: dict[str, Any],
    atac_npz: Path,
    union_bed: Path,
    region_sets_path: Path,
    fold: int = 0,
    repeat: int = 0,
) -> dict[str, Any]:
    """Rebuild one panel's region indices from BED + region-sets and recheck stats."""
    regions, _ = _read_regions(union_bed)
    region_index = {region: i for i, region in enumerate(regions)}
    region_sets = json.loads(region_sets_path.read_text())
    entry = next(
        e
        for e in region_sets["per_fold"]
        if int(e["fold"]) == fold and int(e["repeat"]) == repeat
    )
    rows = np.asarray([region_index[r] for r in entry["regions"]], dtype=np.int64)
    matrix = sparse.load_npz(atac_npz).tocsr()
    sub = matrix[rows].tocsc()
    nnz_cell = np.diff(sub.indptr)
    depth = np.asarray(sub.sum(axis=0)).ravel()
    saved = next(
        p
        for p in coverage["panels"]
        if int(p["fold"]) == fold and int(p["repeat"]) == repeat
    )
    return {
        "fold": fold,
        "repeat": repeat,
        "regions_sha256_match": sha256_text(list(entry["regions"]))
        == saved["regions_sha256"],
        "zero_cell_fraction": float((nnz_cell == 0).mean()),
        "zero_cell_fraction_match": abs(
            float((nnz_cell == 0).mean()) - float(saved["zero_cell_fraction"])
        )
        < 1e-15,
        "median_nonzero_regions": float(np.median(nnz_cell)),
        "median_nonzero_regions_match": float(np.median(nnz_cell))
        == float(saved["median_nonzero_regions"]),
        "median_fragment_overlaps": float(np.median(depth)),
        "median_fragment_overlaps_match": float(np.median(depth))
        == float(saved["median_fragment_overlaps"]),
        "n_regions": int(len(entry["regions"])),
    }


def render_markdown(coverage: dict[str, Any], replay: dict[str, Any]) -> str:
    s = coverage["summary"]
    struct = coverage["structural_adequacy"]
    bio = coverage["biological_regulatory_adequacy"]
    alt = coverage["alternate_representation"]
    cs = coverage["count_semantics"]
    inp = coverage["inputs"]
    py = "/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python"
    lines = [
        "# Q3 — Fold-specific ATAC regulatory coverage",
        "",
        f"**Disposition:** `{coverage['disposition']}`  ",
        f"**Date:** {coverage['date']}  ",
        "**Branch:** `gnhf/execute-the-p22-data-146414`  ",
        "**Dependency:** Q1 PASS. No fits, downloads, package installs, or recounts.",
        "",
        "Machine-readable: [regulatory_coverage.json](regulatory_coverage.json).",
        "",
        "## Adequacy labels (distinct)",
        "",
        "| Axis | Label |",
        "|---|---|",
        f"| Structural / measured coverage | `{struct['label']}` |",
        f"| Biological / regulatory adequacy | `{bio['label']}` |",
        "",
        struct["meaning"],
        "",
        bio["meaning"],
        "",
        "## Provenance and count semantics",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Genome build | `{cs['genome_build']}` |",
        f"| Interval convention | {cs['interval_convention']} |",
        f"| Count unit | `{cs['count_unit']}` |",
        f"| Union BED sha256 | `{inp['bed_sha256']}` |",
        f"| Counts matrix sha256 | `{inp['matrix_sha256']}` |",
        f"| Region sets sha256 | `{inp['region_sets_sha256']}` |",
        f"| Ordered cells sha256 | `{inp['ordered_cells_sha256']}` |",
        "| Selection | training-library prevalence top-256; "
        "salt `p22-atac-tiebreak-v1` |",
        "",
        "## All 25 panels (5 outer folds × 5 repeats)",
        "",
        f"- Panel size: **{s['panel_size']}** regions; "
        f"union **{s['union_regions']}**.",
        f"- Zero-cell fraction across panels: "
        f"min `{s['zero_cell_fraction_min']:.6g}`, "
        f"median `{s['zero_cell_fraction_median']:.6g}`, "
        f"max `{s['zero_cell_fraction_max']:.6g}`.",
        f"- Gene-body overlap fraction: "
        f"min `{s['gene_body_overlap_fraction_min']:.4f}`, "
        f"median `{s['gene_body_overlap_fraction_median']:.4f}`, "
        f"max `{s['gene_body_overlap_fraction_max']:.4f}` "
        f"(descriptive only; not regulatory proof).",
        f"- chr21 region fraction: "
        f"min `{s['chr21_region_fraction_min']:.4f}`, "
        f"median `{s['chr21_region_fraction_median']:.4f}`, "
        f"max `{s['chr21_region_fraction_max']:.4f}`.",
        "",
        "Per-panel and per-type donor coverage tables are in the JSON "
        "(`panels[].per_type`). Donor count, not cell count, drives replication.",
        "",
        "## Independent panel replay (fold 0 / repeat 0)",
        "",
        "| Check | Result |",
        "|---|---|",
        f"| regions_sha256 | `{replay['regions_sha256_match']}` |",
        (
            f"| zero_cell_fraction | `{replay['zero_cell_fraction']}` "
            f"match=`{replay['zero_cell_fraction_match']}` |"
        ),
        (
            f"| median_nonzero_regions | `{replay['median_nonzero_regions']}` "
            f"match=`{replay['median_nonzero_regions_match']}` |"
        ),
        (
            f"| median_fragment_overlaps | `{replay['median_fragment_overlaps']}` "
            f"match=`{replay['median_fragment_overlaps_match']}` |"
        ),
        "",
        "## Alternate representation (at most one)",
        "",
        f"**Proposed:** {alt['representation']}",
        "",
        f"**Reason:** {alt['reason']}",
        "",
        f"**Does not authorize:** {alt['does_not_authorize']}",
        "",
        "## What this does and does not authorize",
        "",
        "| Allowed next | Not authorized |",
        "|---|---|",
        "| Continue Q4–Q5 read-only reports | "
        "Claiming regulatory-feature adequacy PASS |",
        "| Use measured exact counts / existing gene-activity panel "
        "in later design ranking | "
        "Filling unmeasured peaks with biological zero |",
        "| Checkpoint A: unresolved regulatory adequacy is an "
        "acceptable reported outcome | "
        "Biological cell-state fit (still blocked by Q2) |",
        "",
        "## Verification commands",
        "",
        "```bash",
        'export PYTHONPATH="$(pwd)/src"',
        f'{py} -c "import p22; print(p22.__file__)"',
        f"{py} scripts/report_next_stage_regulatory_coverage.py",
        f"{py} -m pytest tests/test_next_stage_regulatory_coverage_q3.py -q",
        "```",
        "",
    ]
    return "\n".join(lines)



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5ad", type=Path, default=DEFAULT_H5AD)
    parser.add_argument("--atac", type=Path, default=DEFAULT_ATAC)
    parser.add_argument("--union-bed", type=Path, default=DEFAULT_BED)
    parser.add_argument("--region-sets", type=Path, default=DEFAULT_REGION_SETS)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument(
        "--gene-activity-bed", type=Path, default=DEFAULT_GENE_ACTIVITY_BED
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--date", default="2026-09-30")
    args = parser.parse_args(argv)

    coverage = build_coverage(
        h5ad_path=args.h5ad,
        atac_npz=args.atac,
        union_bed=args.union_bed,
        region_sets_path=args.region_sets,
        contract_path=args.contract,
        gene_activity_bed=args.gene_activity_bed,
        date=args.date,
    )
    replay = independent_panel_replay(
        coverage=coverage,
        atac_npz=args.atac,
        union_bed=args.union_bed,
        region_sets_path=args.region_sets,
    )
    if not all(
        [
            replay["regions_sha256_match"],
            replay["zero_cell_fraction_match"],
            replay["median_nonzero_regions_match"],
            replay["median_fragment_overlaps_match"],
        ]
    ):
        raise CoverageError(f"independent panel replay failed: {replay}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "regulatory_coverage.json"
    md_path = args.out_dir / "REGULATORY_COVERAGE.md"
    payload = dict(coverage)
    payload["independent_panel_replay"] = replay
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
    md_path.write_text(render_markdown(coverage, replay))
    print(
        json.dumps(
            {
                "disposition": coverage["disposition"],
                "structural": coverage["structural_adequacy"]["label"],
                "n_panels": coverage["summary"]["n_panels"],
                "json": str(json_path),
                "md": str(md_path),
                "replay_ok": True,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CoverageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
