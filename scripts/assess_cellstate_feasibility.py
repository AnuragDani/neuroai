"""Cell-state feasibility assessment for the P22 paired study (Phase 4).

This is a read-only, model-free assessment. It does not fit any classifier and
does not alter the matched cell sample used by the frozen comparison. It:

* verifies which observation fields are donor-invariant instead of assuming it;
* builds donor-by-author-cell-type support tables for the full accepted cells and
  for the historical capped sample (seed 22, cap 256);
* measures per-cell and per-region ATAC support for the historical corrected
  (480-region) and sha256-tie-break (465-region) measured panels, keeping
  region-overlap counts distinct from author ATAC QC fields;
* prepares one deterministic, donor-aware, cell-type-stratified sampling proposal
  under the same total cap and measures the resulting ATAC support without fitting.

All outputs are descriptive. Author cell-type annotations are treated as context,
not independent truth, and no disease prediction is used to choose strata.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import sparse  # noqa: E402

from p22.data.real_cohort import sample_nested_capped_cells  # noqa: E402

OBS_COLUMNS = [
    "library",
    "donor_id",
    "cells_in_excitatory_lineage_subset",
    "disease",
    "dev_PCW",
    "batch_seq",
    "sex",
    "tissue_quality",
    "development_stage",
    "author_cell_type",
    "cell_class",
    "nCount_RNA",
    "nFeature_RNA",
    "nCount_ATAC",
    "nFeature_ATAC",
    "nucleosome_signal",
    "TSS.enrichment",
    "percent.mt",
]

DONOR_INVARIANT_CANDIDATES = [
    "disease",
    "dev_PCW",
    "batch_seq",
    "sex",
    "tissue_quality",
    "development_stage",
]

QC_COLUMNS = [
    "nCount_RNA",
    "nFeature_RNA",
    "nCount_ATAC",
    "nFeature_ATAC",
    "nucleosome_signal",
    "TSS.enrichment",
    "percent.mt",
]

PROPOSAL_NAME = "donor_aware_celltype_stratified_v1"

# Source-defined program for the future within-excitatory-lineage question. Gene
# identities and the RORB/FOXP1 and TLE4 subtype context come from the primary
# source (Lattke et al., Nat. Med. 2026, the development cohort itself), which is
# context for a hypothesis, not independent validation.
EXCITATORY_MATURATION_PROGRAM = {
    "name": "excitatory_subtype_maturation",
    "source": "Lattke et al. 2026 Nat Med, doi:10.1038/s41591-026-04211-1 (same cohort)",
    "subtype_markers": ["RORB", "FOXP1", "TLE4", "BCL11B", "CUX2", "NEUROD2", "NEUROD6"],
    "progenitor_markers": ["SOX9", "PAX6", "EOMES"],
    "predicted_regulators": ["FEZF2", "TCF7L2", "RORA"],
}


def _chrom(region: str) -> str:
    return region.split(":", 1)[0]


def load_obs(h5ad_path: Path) -> pd.DataFrame:
    import anndata as ad

    backed = ad.read_h5ad(h5ad_path, backed="r")
    try:
        obs = backed.obs[OBS_COLUMNS].copy()
    finally:
        backed.file.close()
    obs = obs.reset_index().rename(columns={"index": "cell_id"})
    if obs["cell_id"].duplicated().any():
        raise ValueError("H5AD cell identifiers are not unique")
    for column in ("disease", "dev_PCW", "batch_seq", "sex", "tissue_quality", "development_stage"):
        obs[column] = obs[column].astype(str)
    obs["author_cell_type"] = obs["author_cell_type"].astype(str)
    obs["cell_class"] = obs["cell_class"].astype(str)
    return obs


def donor_invariance(obs: pd.DataFrame) -> dict:
    report: dict[str, dict] = {}
    donors = sorted(obs["donor_id"].astype(str).unique())
    for column in DONOR_INVARIANT_CANDIDATES:
        varying = []
        max_unique = 0
        for donor in donors:
            values = obs.loc[obs["donor_id"].astype(str) == donor, column].unique()
            max_unique = max(max_unique, len(values))
            if len(values) > 1:
                varying.append({"donor_id": donor, "values": sorted(map(str, values))})
        report[column] = {
            "donor_invariant": not varying,
            "max_unique_per_donor": int(max_unique),
            "n_varying_donors": len(varying),
            "varying": varying,
        }
    libraries_per_donor = {}
    for donor in donors:
        libraries_per_donor[donor] = sorted(
            obs.loc[obs["donor_id"].astype(str) == donor, "library"].astype(str).unique()
        )
    report["library"] = {
        "donor_invariant": all(len(v) == 1 for v in libraries_per_donor.values()),
        "max_unique_per_donor": max(len(v) for v in libraries_per_donor.values()),
        "n_varying_donors": sum(1 for v in libraries_per_donor.values() if len(v) > 1),
        "per_donor": libraries_per_donor,
    }
    return report


def missingness(obs: pd.DataFrame) -> dict[str, int]:
    return {column: int(obs[column].isna().sum()) for column in OBS_COLUMNS}


def support_table(obs: pd.DataFrame, celltypes: list[str]) -> list[dict]:
    grouped = (
        obs.groupby(["donor_id", "author_cell_type"], observed=True)
        .size()
        .rename("n_cells")
        .reset_index()
    )
    donor_meta = (
        obs.groupby("donor_id", observed=True)
        .agg(
            disease=("disease", "first"),
            dev_PCW=("dev_PCW", "first"),
            batch_seq=("batch_seq", "first"),
            library=("library", lambda s: ",".join(sorted(set(map(str, s))))),
            n_cells_donor=("cell_id", "size"),
        )
        .reset_index()
    )
    table = grouped.merge(donor_meta, on="donor_id", how="left")
    table["fraction_of_donor"] = table["n_cells"] / table["n_cells_donor"]
    return table


def qc_summary(obs: pd.DataFrame, by: str) -> list[dict]:
    """Mean available QC fields per stratum; counts stay explicit."""
    grouped = obs.groupby(by, observed=True)[QC_COLUMNS].mean().reset_index()
    counts = obs.groupby(by, observed=True).size().rename("n_cells").reset_index()
    return grouped.merge(counts, on=by, how="left").to_dict(orient="records")


def celltype_totals(obs: pd.DataFrame) -> dict[str, int]:
    counts = obs["author_cell_type"].value_counts()
    return {str(k): int(v) for k, v in counts.items()}


def _panel_support(matrix: sparse.spmatrix, columns: np.ndarray) -> dict[str, np.ndarray]:
    sub = matrix[:, columns]
    return {
        "nonzero_regions": np.asarray(sub.getnnz(axis=0)).ravel().astype(np.int64),
        "overlap_sum": np.asarray(sub.sum(axis=0)).ravel().astype(np.float64),
    }


def _summarize(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return {"n": 0}
    return {
        "n": int(values.size),
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "q25": float(np.quantile(values, 0.25)),
        "q75": float(np.quantile(values, 0.75)),
        "min": float(values.min()),
        "max": float(values.max()),
    }


def panel_support_tables(
    obs: pd.DataFrame,
    matrix: sparse.spmatrix,
    regions: list[str],
    rows: np.ndarray,
) -> dict:
    """Per-cell and per-region ATAC support for one measured panel."""
    n_cells = obs.shape[0]
    if matrix.shape[1] != n_cells:
        raise ValueError("ATAC matrix cells do not match the observation axis")
    if matrix.shape[0] != len(regions):
        raise ValueError("ATAC matrix regions do not match the panel region list")
    capped_obs = obs.iloc[rows].reset_index(drop=True)
    support = _panel_support(matrix, rows)
    capped = capped_obs[["donor_id", "author_cell_type", "disease", "dev_PCW", "batch_seq"]].copy()
    capped["nonzero_regions"] = support["nonzero_regions"]
    capped["overlap_sum"] = support["overlap_sum"]
    by_celltype = (
        capped.groupby("author_cell_type", observed=True)
        .agg(
            n_cells=("nonzero_regions", "size"),
            nonzero_mean=("nonzero_regions", "mean"),
            nonzero_median=("nonzero_regions", "median"),
            overlap_mean=("overlap_sum", "mean"),
            overlap_median=("overlap_sum", "median"),
        )
        .reset_index()
    )
    by_donor = (
        capped.groupby("donor_id", observed=True)
        .agg(
            n_cells=("nonzero_regions", "size"),
            nonzero_mean=("nonzero_regions", "mean"),
            nonzero_median=("nonzero_regions", "median"),
            overlap_mean=("overlap_sum", "mean"),
        )
        .reset_index()
    )
    by_stratum = (
        capped.groupby(["donor_id", "author_cell_type"], observed=True)
        .agg(
            n_cells=("nonzero_regions", "size"),
            nonzero_mean=("nonzero_regions", "mean"),
            nonzero_median=("nonzero_regions", "median"),
            overlap_mean=("overlap_sum", "mean"),
        )
        .reset_index()
    )

    # Feature-level support over all accepted cells and by author cell type.
    region_nnz_all = np.asarray(matrix.getnnz(axis=1)).ravel().astype(np.int64)
    region_sum_all = np.asarray(matrix.sum(axis=1)).ravel().astype(np.float64)
    chrom = [region.split(":", 1)[0] for region in regions]
    per_region = []
    for index, region in enumerate(regions):
        per_region.append(
            {
                "region": region,
                "chrom": chrom[index],
                "nonzero_cells": int(region_nnz_all[index]),
                "nonzero_fraction": float(region_nnz_all[index] / n_cells),
                "overlap_sum": float(region_sum_all[index]),
            }
        )
    celltypes = sorted(obs["author_cell_type"].astype(str).unique())
    coverage_by_celltype = {}
    for celltype in celltypes:
        mask = (obs["author_cell_type"].astype(str) == celltype).to_numpy()
        sub = matrix[:, np.flatnonzero(mask)]
        coverage_by_celltype[celltype] = {
            "n_cells": int(mask.sum()),
            "regions_with_any_nonzero": int((sub.getnnz(axis=1) > 0).sum()),
            "nonzero_fraction_mean": float(sub.getnnz() / (sub.shape[0] * max(sub.shape[1], 1))),
        }
    zero_regions = [r["region"] for r in per_region if r["nonzero_cells"] == 0]
    return {
        "n_regions": len(regions),
        "n_cells": int(n_cells),
        "total_nnz": int(matrix.getnnz()),
        "panel_zero_regions": len(zero_regions),
        "panel_zero_region_examples": zero_regions[:10],
        "capped": {
            "n_cells": int(len(rows)),
            "nonzero_regions": _summarize(support["nonzero_regions"]),
            "overlap_sum": _summarize(support["overlap_sum"]),
            "zero_cells": int((support["nonzero_regions"] == 0).sum()),
            "zero_fraction": float((support["nonzero_regions"] == 0).mean()),
            "by_celltype": by_celltype.to_dict(orient="records"),
            "by_donor": by_donor.to_dict(orient="records"),
            "by_stratum": by_stratum.to_dict(orient="records"),
        },
        "per_region": per_region,
        "coverage_by_celltype": coverage_by_celltype,
        "chrom_region_counts": dict(sorted(pd.Series(chrom).value_counts().to_dict().items())),
    }


def allocate_within_donor(cap: int, available: dict[str, int]) -> dict[str, int]:
    """Deterministic largest-remainder allocation of ``cap`` across strata."""
    present = sorted(ct for ct, n in available.items() if n > 0)
    total = sum(available.values())
    if total <= cap:
        return {ct: int(available[ct]) for ct in present}
    if cap <= len(present):
        ranked = sorted(present, key=lambda ct: (-available[ct], ct))
        chosen = set(ranked[:cap])
        return {ct: (1 if ct in chosen else 0) for ct in present}
    alloc = {ct: 1 for ct in present}
    remaining = cap - len(present)
    while remaining > 0:
        eligible = [ct for ct in present if alloc[ct] < available[ct]]
        if not eligible:
            break
        denom = sum(available[ct] - alloc[ct] for ct in eligible)
        quotas = {ct: remaining * (available[ct] - alloc[ct]) / denom for ct in eligible}
        floors = {ct: int(math.floor(quotas[ct])) for ct in eligible}
        added = sum(floors.values())
        if added == 0:
            order = sorted(eligible, key=lambda ct: (-(quotas[ct] - math.floor(quotas[ct])), ct))
            alloc[order[0]] += 1
            remaining -= 1
        else:
            for ct in eligible:
                alloc[ct] += floors[ct]
            remaining -= added
    return alloc


def build_proposal(
    obs: pd.DataFrame,
    cap: int,
    matrix: sparse.spmatrix,
) -> dict:
    """Deterministic donor-aware cell-type-stratified proposal and its support."""
    donor_strata: dict[str, list[int]] = {}
    for donor, group in obs.groupby("donor_id", observed=True):
        donor_strata[str(donor)] = group.index.to_numpy()
    selected_positions: list[int] = []
    allocations: list[dict] = []
    for donor in sorted(donor_strata):
        positions = donor_strata[donor]
        celltypes = obs.loc[positions, "author_cell_type"].astype(str)
        available = {ct: int(n) for ct, n in celltypes.value_counts().items()}
        alloc = allocate_within_donor(cap, available)
        for celltype in sorted(alloc):
            n_alloc = alloc[celltype]
            if n_alloc <= 0:
                continue
            ct_positions = np.sort(positions[(celltypes == celltype).to_numpy()])
            chosen = ct_positions[:n_alloc]
            selected_positions.extend(chosen.tolist())
            allocations.append(
                {
                    "donor_id": donor,
                    "author_cell_type": celltype,
                    "available": int(available[celltype]),
                    "allocated": int(n_alloc),
                }
            )
    selected = np.sort(np.asarray(selected_positions, dtype=np.int64))
    support = _panel_support(matrix, selected)
    proposal_obs = obs.iloc[selected]
    by_celltype = (
        pd.DataFrame(
            {
                "author_cell_type": proposal_obs["author_cell_type"].astype(str).to_numpy(),
                "nonzero_regions": support["nonzero_regions"],
                "overlap_sum": support["overlap_sum"],
            }
        )
        .groupby("author_cell_type", observed=True)
        .agg(
            n_cells=("nonzero_regions", "size"),
            nonzero_mean=("nonzero_regions", "mean"),
            nonzero_median=("nonzero_regions", "median"),
            overlap_mean=("overlap_sum", "mean"),
        )
        .reset_index()
    )
    return {
        "name": PROPOSAL_NAME,
        "description": (
            "Within each donor allocate the cell cap across author cell types by "
            "deterministic largest remainder proportional to donor-level availability, "
            "reserving one cell per present stratum; take the lowest-index cells of "
            "each stratum. No random seed and no disease outcome is used."
        ),
        "cap_per_donor": int(cap),
        "n_cells": int(selected.size),
        "n_cells_expected": int(len(donor_strata) * cap),
        "zero_cells": int((support["nonzero_regions"] == 0).sum()),
        "zero_fraction": float((support["nonzero_regions"] == 0).mean()),
        "nonzero_regions": _summarize(support["nonzero_regions"]),
        "overlap_sum": _summarize(support["overlap_sum"]),
        "by_celltype": by_celltype.to_dict(orient="records"),
        "allocations": allocations,
    }


def gene_locus_table(h5ad_path: Path, gene_names: list[str]) -> dict:
    import anndata as ad

    backed = ad.read_h5ad(h5ad_path, backed="r")
    try:
        var = backed.var[["gene_name", "seqnames", "start", "end"]].copy()
    finally:
        backed.file.close()
    table: dict[str, dict] = {}
    for gene in gene_names:
        rows = var[var["gene_name"] == gene]
        if rows.empty:
            table[gene] = {"present_in_rna_axis": False, "loci": []}
            continue
        table[gene] = {
            "present_in_rna_axis": True,
            "loci": [
                {
                    "seqnames": str(row["seqnames"]),
                    "start": int(row["start"]),
                    "end": int(row["end"]),
                }
                for _, row in rows.iterrows()
            ],
        }
    return table


def program_feature_coverage(h5ad_path: Path, panels: dict[str, list[str]]) -> dict:
    """Audit RNA/ATAC feature coverage for the prespecified maturation program."""
    genes = (
        EXCITATORY_MATURATION_PROGRAM["subtype_markers"]
        + EXCITATORY_MATURATION_PROGRAM["progenitor_markers"]
        + EXCITATORY_MATURATION_PROGRAM["predicted_regulators"]
    )
    loci = gene_locus_table(h5ad_path, genes)
    parsed = {
        label: [
            (
                _chrom(region),
                int(region.split(":")[1].split("-")[0]),
                int(region.split(":")[1].split("-")[1]),
            )
            for region in regions
        ]
        for label, regions in panels.items()
    }
    result = {"program": EXCITATORY_MATURATION_PROGRAM, "panels": {}}
    for label, region_list in panels.items():
        per_gene = {}
        for gene, info in loci.items():
            if not info["present_in_rna_axis"]:
                per_gene[gene] = {
                    "rna_feature_present": False,
                    "atac_regions_overlapping_locus": 0,
                    "overlapping_regions": [],
                }
                continue
            overlapping = []
            for locus in info["loci"]:
                for region, (chrom, start, end) in zip(region_list, parsed[label], strict=True):
                    if chrom == locus["seqnames"] and start < locus["end"] and end > locus["start"]:
                        overlapping.append(region)
            per_gene[gene] = {
                "rna_feature_present": True,
                "atac_regions_overlapping_locus": len(overlapping),
                "overlapping_regions": overlapping[:5],
            }
        result["panels"][label] = {
            "n_regions": len(region_list),
            "genes_with_any_overlapping_region": sum(
                1 for value in per_gene.values() if value["atac_regions_overlapping_locus"] > 0
            ),
            "genes": per_gene,
        }
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5ad", required=True, type=Path)
    parser.add_argument("--historical-matrix", required=True, type=Path)
    parser.add_argument("--historical-region-sets", required=True, type=Path)
    parser.add_argument("--tiebreak-matrix", required=True, type=Path)
    parser.add_argument("--tiebreak-region-sets", required=True, type=Path)
    parser.add_argument("--sampling-seed", type=int, default=22)
    parser.add_argument("--cell-cap", type=int, default=256)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--csv-dir", default=None, type=Path)
    parser.add_argument(
        "--tracked-evidence",
        default=None,
        type=Path,
        help="compact machine-readable record with large per-region arrays stripped",
    )
    return parser


def _matrix_sidecar(matrix_path: Path) -> dict:
    sidecar = matrix_path.parent / "counts.json"
    if not sidecar.is_file():
        return {}
    data = json.loads(sidecar.read_text())
    return {
        "matrix_sha256": data.get("matrix_sha256"),
        "shape": data.get("shape"),
        "nnz": data.get("nnz"),
        "count_unit": data.get("count_unit"),
        "cells_sha256": data.get("cells_sha256"),
    }


def compact_record(record: dict, args: argparse.Namespace) -> dict:
    panels = {}
    for label, panel in record["atac_panels"].items():
        capped = panel["capped"]
        panels[label] = {
            "n_regions": panel["n_regions"],
            "total_nnz": panel["total_nnz"],
            "panel_zero_regions": panel["panel_zero_regions"],
            "chrom_region_counts": panel["chrom_region_counts"],
            "capped_zero_fraction": capped["zero_fraction"],
            "capped_nonzero_regions": capped["nonzero_regions"],
            "capped_overlap_sum": capped["overlap_sum"],
            "capped_by_celltype": capped["by_celltype"],
            "coverage_by_celltype": panel["coverage_by_celltype"],
        }
    proposals = {}
    for label, proposal in record["proposal"].items():
        proposals[label] = {key: value for key, value in proposal.items() if key != "allocations"}
    return {
        "record_type": "cellstate_feasibility_tracked_evidence",
        "generated_at": record["generated_at"],
        "outcome_used_for_selection": False,
        "model_fitted": False,
        "sampling_seed": record["sampling_seed"],
        "cell_cap": record["cell_cap"],
        "inputs": {
            **record["inputs"],
            "historical_matrix_sidecar": _matrix_sidecar(args.historical_matrix),
            "tiebreak_matrix_sidecar": _matrix_sidecar(args.tiebreak_matrix),
        },
        "n_accepted_cells": record["n_accepted_cells"],
        "n_capped_cells": record["n_capped_cells"],
        "n_donors": record["n_donors"],
        "missingness": record["missingness"],
        "donor_invariance": record["donor_invariance"],
        "celltype_counts_full": record["celltype_counts_full"],
        "celltype_counts_capped": record["celltype_counts_capped"],
        "excitatory_lineage_subset_counts_full": record["excitatory_lineage_subset_counts_full"],
        "excitatory_lineage_subset_counts_capped": record[
            "excitatory_lineage_subset_counts_capped"
        ],
        "cell_class_counts_full": record["cell_class_counts_full"],
        "qc_by_celltype_capped": record["qc_by_celltype_capped"],
        "atac_panels": panels,
        "proposal": proposals,
        "program_feature_coverage": record["program_feature_coverage"],
        "claim_boundaries": record["claim_boundaries"],
    }


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    obs = load_obs(args.h5ad)
    historical_regions = json.loads(args.historical_region_sets.read_text())["union_regions"]
    tiebreak_regions = json.loads(args.tiebreak_region_sets.read_text())["union_regions"]
    historical_matrix = sparse.load_npz(args.historical_matrix)
    tiebreak_matrix = sparse.load_npz(args.tiebreak_matrix)
    rows = sample_nested_capped_cells(
        obs[["donor_id"]],
        np.ones(obs.shape[0], dtype=bool),
        (args.cell_cap,),
        args.sampling_seed,
    )[args.cell_cap]

    historical_support = panel_support_tables(obs, historical_matrix, historical_regions, rows)
    tiebreak_support = panel_support_tables(obs, tiebreak_matrix, tiebreak_regions, rows)

    capped_obs = obs.iloc[rows].reset_index(drop=True)
    record = {
        "record_type": "cellstate_feasibility_assessment",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "outcome_used_for_selection": False,
        "model_fitted": False,
        "sampling_seed": args.sampling_seed,
        "cell_cap": args.cell_cap,
        "inputs": {
            "h5ad": str(args.h5ad),
            "historical_matrix": str(args.historical_matrix),
            "historical_region_sets": str(args.historical_region_sets),
            "tiebreak_matrix": str(args.tiebreak_matrix),
            "tiebreak_region_sets": str(args.tiebreak_region_sets),
        },
        "n_accepted_cells": int(obs.shape[0]),
        "n_capped_cells": int(len(rows)),
        "n_donors": int(obs["donor_id"].nunique()),
        "missingness": missingness(obs),
        "donor_invariance": donor_invariance(obs),
        "celltype_counts_full": celltype_totals(obs),
        "celltype_counts_capped": celltype_totals(capped_obs),
        "excitatory_lineage_subset_counts_full": {
            str(k): int(v)
            for k, v in obs["cells_in_excitatory_lineage_subset"].astype(str).value_counts().items()
        },
        "excitatory_lineage_subset_counts_capped": {
            str(k): int(v)
            for k, v in capped_obs["cells_in_excitatory_lineage_subset"]
            .astype(str)
            .value_counts()
            .items()
        },
        "cell_class_counts_full": {
            str(k): int(v) for k, v in obs["cell_class"].astype(str).value_counts().items()
        },
        "support_full": support_table(obs, sorted(obs["author_cell_type"].unique())),
        "support_capped": support_table(
            capped_obs, sorted(capped_obs["author_cell_type"].unique())
        ),
        "qc_by_celltype_full": qc_summary(obs, "author_cell_type"),
        "qc_by_celltype_capped": qc_summary(capped_obs, "author_cell_type"),
        "qc_by_donor_capped": qc_summary(capped_obs, "donor_id"),
        "atac_panels": {
            "historical_corrected": {
                "union_regions": len(historical_regions),
                **historical_support,
            },
            "sha256_tiebreak": {
                "union_regions": len(tiebreak_regions),
                **tiebreak_support,
            },
        },
        "proposal": {
            "historical_corrected": build_proposal(obs, args.cell_cap, historical_matrix),
            "sha256_tiebreak": build_proposal(obs, args.cell_cap, tiebreak_matrix),
        },
        "program_feature_coverage": program_feature_coverage(
            args.h5ad,
            {
                "historical_corrected": historical_regions,
                "sha256_tiebreak": tiebreak_regions,
            },
        ),
        "claim_boundaries": [
            "Descriptive only; author cell-type labels are context, not independent truth.",
            "Region-overlap sums are not total assay fragments or author ATAC QC.",
            "The stratified proposal is a separately named future sensitivity; it does "
            "not alter the frozen matched sample and no model was fitted on it.",
            "No biological mechanism or disease effect is claimed from these tables.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + "\n")

    if args.tracked_evidence is not None:
        compact = compact_record(record, args)
        args.tracked_evidence.parent.mkdir(parents=True, exist_ok=True)
        args.tracked_evidence.write_text(
            json.dumps(compact, indent=2, sort_keys=True, default=str) + "\n"
        )

    if args.csv_dir is not None:
        _write_csv(record["support_full"], args.csv_dir / "support_full.csv")
        _write_csv(record["support_capped"], args.csv_dir / "support_capped.csv")
        for label, support in record["atac_panels"].items():
            _write_csv(
                pd.DataFrame(support["per_region"]),
                args.csv_dir / f"per_region_{label}.csv",
            )
            _write_csv(
                pd.DataFrame(support["capped"]["by_stratum"]),
                args.csv_dir / f"by_stratum_{label}.csv",
            )
        for label, proposal in record["proposal"].items():
            _write_csv(
                pd.DataFrame(proposal["allocations"]),
                args.csv_dir / f"proposal_allocations_{label}.csv",
            )

    print(
        json.dumps(
            {
                "n_accepted_cells": record["n_accepted_cells"],
                "n_capped_cells": record["n_capped_cells"],
                "n_donors": record["n_donors"],
                "donor_invariant_fields": [
                    key
                    for key, value in record["donor_invariance"].items()
                    if value["donor_invariant"]
                ],
                "varying_fields": [
                    key
                    for key, value in record["donor_invariance"].items()
                    if not value["donor_invariant"]
                ],
                "historical_panel_zero_regions": historical_support["panel_zero_regions"],
                "tiebreak_panel_zero_regions": tiebreak_support["panel_zero_regions"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
