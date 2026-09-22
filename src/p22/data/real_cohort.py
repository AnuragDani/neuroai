"""Full-cohort schema audit, QC accounting, and donor census on the real H5AD.

Everything here reads a local public H5AD. Schema and QC work touches ``obs``
and ``var`` only, so it stays cheap. The donor pseudobulk pass streams raw
counts in row chunks, so the 248,998-cell matrix is never densified.

Thresholds are module constants: they are frozen before any filtering runs and
are reported alongside every retained and excluded count.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

DONOR_COLUMN = "donor_id"
CONDITION_COLUMN = "disease"
POSITIVE_CONDITION = "complete trisomy 21"
CONTROL_CONDITION = "normal"

# obs columns that carry author-computed QC. Values are checked against the raw
# count matrix before use, so the QC used for filtering stays deterministic.
QC_COLUMNS = {
    "n_genes": "nFeature_RNA",
    "total_counts": "nCount_RNA",
    "pct_mito": "percent.mt",
}
ATAC_QC_COLUMNS = ("nCount_ATAC", "nFeature_ATAC", "nucleosome_signal", "TSS.enrichment")
CATEGORICAL_COVARIATES = (
    "stage",
    "sex",
    "library",
    "batch_seq",
    "dataset_folder",
    "tissue_quality",
)
NUMERIC_COVARIATES = ("dev_PCW",)
CHROMOSOME_CANDIDATES = ("seqnames", "chromosome", "chrom", "seqname", "gene_chrom")
CHR21_LABELS = ("chr21", "21")
MITO_LABELS = ("chrm", "chrmt", "mt", "m")
MITO_SYMBOL_PREFIX = "MT-"
SYMBOL_COLUMN_CANDIDATES = ("feature_name", "gene_name")
ENSEMBL_ID_PATTERN = re.compile(r"^ENSG\d{11}")

# The 13 mitochondrially encoded protein-coding genes. A mask that finds far more
# than this is matching nuclear genes by prefix and must not be used.
MITO_GENE_RANGE = (10, 40)

# Plausible number of annotated chromosome-21 genes in a GENCODE human reference.
CHR21_GENE_RANGE = (200, 900)

MIN_DONORS_PER_CONDITION = 15
MIN_USABLE_CELLS_PER_DONOR = 64
MAX_DONOR_CLASS_RATIO = 1.5
MAX_CELL_CLASS_RATIO = 2.0


@dataclass(frozen=True)
class QcThresholds:
    """RNA QC cut-offs frozen before any cell is removed.

    The cohort is single-nucleus multiome. ATAC QC columns are recorded as
    observed covariates rather than filters, because the analysis layer that
    survives the ATAC branch decision is RNA-only.
    """

    min_genes: int = 200
    min_total_counts: int = 500
    max_pct_mito: float = 10.0
    min_usable_cells_per_donor: int = MIN_USABLE_CELLS_PER_DONOR
    min_donors_per_condition: int = MIN_DONORS_PER_CONDITION
    max_donor_class_ratio: float = MAX_DONOR_CLASS_RATIO
    max_cell_class_ratio: float = MAX_CELL_CLASS_RATIO
    rationale: str = (
        "nuclei with <200 detected genes or <500 counts are ambient-dominated; "
        "nuclear preparations should carry little mitochondrial signal, so 10% is "
        "a permissive upper bound rather than a tuned one"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "min_genes": self.min_genes,
            "min_total_counts": self.min_total_counts,
            "max_pct_mito": self.max_pct_mito,
            "min_usable_cells_per_donor": self.min_usable_cells_per_donor,
            "min_donors_per_condition": self.min_donors_per_condition,
            "max_donor_class_ratio": self.max_donor_class_ratio,
            "max_cell_class_ratio": self.max_cell_class_ratio,
            "frozen_before_filtering": True,
            "atac_qc_used_as_filter": False,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class Chr21Mapping:
    """Frozen gene-to-chromosome contract for the chr21 dosage baseline."""

    status: str
    source: str
    id_scheme: str
    chromosome_column: str | None
    n_genes_total: int
    n_chr21_genes: int
    mapping_sha256: str | None
    example_genes: tuple[str, ...] = ()
    reason: str | None = None

    @property
    def usable(self) -> bool:
        return self.status == "verified"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "id_scheme": self.id_scheme,
            "chromosome_column": self.chromosome_column,
            "n_genes_total": self.n_genes_total,
            "n_chr21_genes": self.n_chr21_genes,
            "mapping_sha256": self.mapping_sha256,
            "example_genes": list(self.example_genes),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class SchemaAudit:
    """What the file actually contains, including what it does not contain."""

    status: str
    n_cells: int
    n_vars: int
    fields: dict[str, str | None] = field(default_factory=dict)
    gene_identifiers: dict[str, Any] = field(default_factory=dict)
    genome_build: dict[str, Any] = field(default_factory=dict)
    count_semantics: dict[str, Any] = field(default_factory=dict)
    qc_fields: dict[str, Any] = field(default_factory=dict)
    covariates: dict[str, Any] = field(default_factory=dict)
    missingness: list[dict[str, Any]] = field(default_factory=list)
    atac: dict[str, Any] = field(default_factory=dict)
    chr21: Chr21Mapping | None = None
    blocking_problems: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "n_cells": self.n_cells,
            "n_vars": self.n_vars,
            "fields": dict(self.fields),
            "gene_identifiers": dict(self.gene_identifiers),
            "genome_build": dict(self.genome_build),
            "count_semantics": dict(self.count_semantics),
            "qc_fields": dict(self.qc_fields),
            "covariates": dict(self.covariates),
            "missingness": list(self.missingness),
            "atac": dict(self.atac),
            "chr21_mapping": None if self.chr21 is None else self.chr21.to_dict(),
            "blocking_problems": list(self.blocking_problems),
            "open_questions": list(self.open_questions),
        }


@dataclass(frozen=True)
class CohortQcReport:
    """Pre-QC and post-QC full-cohort accounting."""

    status: str
    thresholds: dict[str, Any]
    n_cells_pre_qc: int
    n_cells_post_qc: int
    n_donors_pre_qc: int
    n_donors_post_qc: int
    condition_cells_pre_qc: dict[str, int] = field(default_factory=dict)
    condition_cells_post_qc: dict[str, int] = field(default_factory=dict)
    condition_donors_post_qc: dict[str, int] = field(default_factory=dict)
    donor_table_pre_qc: list[dict[str, Any]] = field(default_factory=list)
    donor_table_post_qc: list[dict[str, Any]] = field(default_factory=list)
    exclusions: list[dict[str, Any]] = field(default_factory=list)
    missingness: list[dict[str, Any]] = field(default_factory=list)
    suffix_audit: dict[str, Any] = field(default_factory=dict)
    ratios: dict[str, float | None] = field(default_factory=dict)
    qc_sources: dict[str, str] = field(default_factory=dict)
    derived_qc: dict[str, Any] = field(default_factory=dict)
    stop_reasons: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    keep_mask: np.ndarray | None = None
    obs: pd.DataFrame | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "thresholds": dict(self.thresholds),
            "n_cells_pre_qc": self.n_cells_pre_qc,
            "n_cells_post_qc": self.n_cells_post_qc,
            "n_donors_pre_qc": self.n_donors_pre_qc,
            "n_donors_post_qc": self.n_donors_post_qc,
            "condition_cells_pre_qc": dict(self.condition_cells_pre_qc),
            "condition_cells_post_qc": dict(self.condition_cells_post_qc),
            "condition_donors_post_qc": dict(self.condition_donors_post_qc),
            "donor_table_pre_qc": list(self.donor_table_pre_qc),
            "donor_table_post_qc": list(self.donor_table_post_qc),
            "exclusions": list(self.exclusions),
            "missingness": list(self.missingness),
            "suffix_audit": dict(self.suffix_audit),
            "ratios": dict(self.ratios),
            "qc_sources": dict(self.qc_sources),
            "derived_qc": dict(self.derived_qc),
            "stop_reasons": list(self.stop_reasons),
            "open_questions": list(self.open_questions),
            "layer": "full_cohort",
            "not_a_model_cap": True,
        }


@dataclass(frozen=True)
class DonorPseudobulk:
    """Donor-level sums over every retained cell, plus derived dosage."""

    donor_ids: tuple[str, ...]
    conditions: tuple[str, ...]
    labels: np.ndarray
    n_cells: np.ndarray
    total_counts: np.ndarray
    gene_sums: np.ndarray
    chr21_fraction: np.ndarray | None
    gene_ids: tuple[str, ...]
    chr21_mapping: Chr21Mapping | None
    layer: str = "full_cohort_all_retained_cells"

    def log_cpm(self) -> np.ndarray:
        """Counts-per-million then ``log1p``, computed per donor independently."""
        totals = np.where(self.total_counts > 0, self.total_counts, 1.0)
        return np.log1p(self.gene_sums / totals[:, None] * 1e6)

    def summary(self) -> dict[str, Any]:
        return {
            "layer": self.layer,
            "n_donors": len(self.donor_ids),
            "n_genes": len(self.gene_ids),
            "n_cells_total": int(self.n_cells.sum()),
            "cells_per_donor_min": int(self.n_cells.min()) if self.n_cells.size else None,
            "cells_per_donor_max": int(self.n_cells.max()) if self.n_cells.size else None,
            "chr21_available": self.chr21_fraction is not None,
        }


def _read_frames(path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], int, int]:
    """Return ``(obs, var, uns, n_cells, n_vars)`` from a backed read."""
    import anndata as ad

    backed = ad.read_h5ad(Path(path), backed="r")
    try:
        obs = backed.obs.copy()
        var = backed.var.copy()
        uns = {key: backed.uns[key] for key in backed.uns}
        shape = (int(backed.n_obs), int(backed.n_vars))
        obsm_keys = tuple(backed.obsm.keys())
    finally:
        backed.file.close()
    uns["_obsm_keys"] = obsm_keys
    return obs, var, uns, shape[0], shape[1]


def read_var(path: str | Path) -> pd.DataFrame:
    """Return the ``var`` frame from a backed read."""
    import anndata as ad

    backed = ad.read_h5ad(Path(path), backed="r")
    try:
        return backed.var.copy()
    finally:
        backed.file.close()


def chr21_mapping_from_var(var: pd.DataFrame) -> Chr21Mapping:
    """Freeze a gene-to-chromosome mapping, or refuse it with a reason.

    The mapping ships inside the CELLxGENE-curated ``var`` block as Ensembl gene
    identifiers plus chromosome names. It is hashed so a later run can prove the
    same mapping was used.
    """
    gene_ids = tuple(str(value) for value in var.index)
    ensembl_share = (
        float(np.mean([bool(ENSEMBL_ID_PATTERN.match(value)) for value in gene_ids]))
        if gene_ids
        else 0.0
    )
    column = next((name for name in CHROMOSOME_CANDIDATES if name in var.columns), None)
    if column is None:
        return Chr21Mapping(
            status="not_applicable",
            source="h5ad var annotation",
            id_scheme="ensembl_gene_id" if ensembl_share > 0.9 else "unverified",
            chromosome_column=None,
            n_genes_total=len(gene_ids),
            n_chr21_genes=0,
            mapping_sha256=None,
            reason=f"no chromosome column among {CHROMOSOME_CANDIDATES}",
        )
    if ensembl_share <= 0.9:
        return Chr21Mapping(
            status="not_applicable",
            source="h5ad var annotation",
            id_scheme="unverified",
            chromosome_column=column,
            n_genes_total=len(gene_ids),
            n_chr21_genes=0,
            mapping_sha256=None,
            reason=(
                f"only {ensembl_share:.1%} of var index entries look like Ensembl gene IDs; "
                "chromosome mapping cannot be verified"
            ),
        )

    chromosomes = var[column].astype(str).str.lower()
    chr21_mask = chromosomes.isin([label.lower() for label in CHR21_LABELS]).to_numpy()
    n_chr21 = int(chr21_mask.sum())
    selected = sorted(str(gene) for gene in var.index[chr21_mask])
    digest = hashlib.sha256(
        "\n".join(f"{gene}\t21" for gene in selected).encode("utf-8")
    ).hexdigest()
    low, high = CHR21_GENE_RANGE
    if not low <= n_chr21 <= high:
        return Chr21Mapping(
            status="not_applicable",
            source="h5ad var annotation",
            id_scheme="ensembl_gene_id",
            chromosome_column=column,
            n_genes_total=len(gene_ids),
            n_chr21_genes=n_chr21,
            mapping_sha256=digest,
            reason=(
                f"{n_chr21} chr21 genes is outside the plausible range {CHR21_GENE_RANGE} "
                "for a human GENCODE reference"
            ),
        )
    return Chr21Mapping(
        status="verified",
        source="h5ad var annotation (CELLxGENE-curated Ensembl IDs + chromosome names)",
        id_scheme="ensembl_gene_id",
        chromosome_column=column,
        n_genes_total=len(gene_ids),
        n_chr21_genes=n_chr21,
        mapping_sha256=digest,
        example_genes=tuple(selected[:5]),
    )


def symbol_series(var: pd.DataFrame) -> pd.Series:
    """Gene symbols per var row, falling back to the index when absent."""
    for column in SYMBOL_COLUMN_CANDIDATES:
        if column in var.columns:
            return var[column].astype(str)
    return pd.Series([str(value) for value in var.index], index=var.index)


def mito_gene_mask(var: pd.DataFrame) -> tuple[np.ndarray, dict[str, Any]]:
    """Locate mitochondrial genes, preferring a chromosome column over symbols."""
    column = next((name for name in CHROMOSOME_CANDIDATES if name in var.columns), None)
    if column is not None:
        chromosomes = var[column].astype(str).str.lower().str.strip()
        mask = chromosomes.isin(MITO_LABELS).to_numpy()
        if mask.any():
            return mask, {
                "source": f"var.{column} in {list(MITO_LABELS)}",
                "n_genes": int(mask.sum()),
            }
    symbols = symbol_series(var).str.upper()
    mask = symbols.str.startswith(MITO_SYMBOL_PREFIX).to_numpy()
    detail = {
        "source": f"gene symbols starting with {MITO_SYMBOL_PREFIX!r}",
        "n_genes": int(mask.sum()),
        "chromosome_column_had_no_mito_contig": column is not None,
    }
    low, high = MITO_GENE_RANGE
    if not low <= int(mask.sum()) <= high:
        detail["rejected"] = (
            f"{int(mask.sum())} matches is outside the plausible mitochondrial range "
            f"{MITO_GENE_RANGE}"
        )
        return np.zeros(var.shape[0], dtype=bool), detail
    return mask, detail


@dataclass(frozen=True)
class DerivedCellQc:
    """Per-cell QC recomputed from the raw count matrix.

    Author-supplied ``obs`` QC was computed on the submitter's own feature space.
    This cohort was re-filtered during curation, so the two differ slightly. The
    filters use these derived values and report the disagreement rather than
    trusting a column whose provenance cannot be reproduced here.
    """

    n_genes: np.ndarray
    total_counts: np.ndarray
    pct_mito: np.ndarray | None
    source: str
    mito_detail: dict[str, Any] = field(default_factory=dict)
    agreement: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "n_cells": int(self.n_genes.size),
            "n_genes_median": float(np.median(self.n_genes)) if self.n_genes.size else None,
            "total_counts_median": (
                float(np.median(self.total_counts)) if self.total_counts.size else None
            ),
            "pct_mito_available": self.pct_mito is not None,
            "pct_mito_median": (
                float(np.median(self.pct_mito)) if self.pct_mito is not None else None
            ),
            "mito_mask": dict(self.mito_detail),
            "agreement_with_obs_columns": dict(self.agreement),
        }


def derive_cell_qc(
    path: str | Path,
    obs: pd.DataFrame | None = None,
    var: pd.DataFrame | None = None,
    chunk_rows: int = 20_000,
    matrix_key: str = "raw/X",
) -> DerivedCellQc:
    """Recompute detected genes, total counts, and mitochondrial fraction.

    The matrix is streamed in row chunks over the CSR arrays directly, so nothing
    dense is built and the pass costs one sequential read.
    """
    import h5py

    var = read_var(path) if var is None else var
    mask, mito_detail = mito_gene_mask(var)
    mito_columns = np.flatnonzero(mask)
    with h5py.File(Path(path), "r") as handle:
        group = handle[matrix_key]
        indptr = np.asarray(group["indptr"][:], dtype=np.int64)
        data = group["data"]
        indices = group["indices"]
        n_cells = int(indptr.size - 1)
        n_genes = np.diff(indptr).astype(np.int64)
        total_counts = np.zeros(n_cells, dtype=np.float64)
        mito_counts = np.zeros(n_cells, dtype=np.float64) if mito_columns.size else None
        mito_lookup = np.zeros(int(group.attrs["shape"][1]), dtype=bool)
        mito_lookup[mito_columns] = True
        for start in range(0, n_cells, chunk_rows):
            stop = min(start + chunk_rows, n_cells)
            low, high = int(indptr[start]), int(indptr[stop])
            if high == low:
                continue
            values = np.asarray(data[low:high], dtype=np.float64)
            offsets = indptr[start:stop] - low
            total_counts[start:stop] = np.add.reduceat(values, offsets)
            if mito_counts is not None:
                columns = np.asarray(indices[low:high])
                selected = np.where(mito_lookup[columns], values, 0.0)
                mito_counts[start:stop] = np.add.reduceat(selected, offsets)
        # ``reduceat`` repeats the previous value for empty rows; zero them out.
        empty = n_genes == 0
        total_counts[empty] = 0.0
        if mito_counts is not None:
            mito_counts[empty] = 0.0

    pct_mito = None
    if mito_counts is not None:
        safe = np.where(total_counts > 0, total_counts, 1.0)
        pct_mito = 100.0 * mito_counts / safe

    agreement: dict[str, Any] = {}
    if obs is not None:
        for alias, column in QC_COLUMNS.items():
            if column not in obs.columns:
                agreement[alias] = {"column": column, "present": False}
                continue
            author = obs[column].to_numpy(dtype=np.float64)
            derived = {
                "n_genes": n_genes.astype(np.float64),
                "total_counts": total_counts,
                "pct_mito": pct_mito,
            }[alias]
            if derived is None:
                agreement[alias] = {"column": column, "present": True, "derived": False}
                continue
            difference = derived - author
            agreement[alias] = {
                "column": column,
                "present": True,
                "derived": True,
                "identical": bool(np.array_equal(derived, author)),
                "correlation": (
                    float(np.corrcoef(derived, author)[0, 1])
                    if derived.std() > 0 and author.std() > 0
                    else None
                ),
                "median_difference": float(np.median(difference)),
                "max_abs_difference": float(np.max(np.abs(difference))),
            }

    return DerivedCellQc(
        n_genes=n_genes,
        total_counts=total_counts,
        pct_mito=pct_mito,
        source=f"recomputed from {matrix_key} over the curated feature space",
        mito_detail=mito_detail,
        agreement=agreement,
    )


def _missingness_rows(frame: pd.DataFrame, columns: tuple[str, ...]) -> list[dict[str, Any]]:
    rows = []
    total = int(frame.shape[0])
    for name in columns:
        if name not in frame.columns:
            rows.append({"column": name, "present": False, "n_missing": None, "pct_missing": None})
            continue
        values = frame[name]
        missing = int(values.isna().sum())
        if values.dtype == object or isinstance(values.dtype, pd.CategoricalDtype):
            as_text = values.astype(str).str.strip().str.lower()
            missing += int(as_text.isin({"nan", "", "na", "unknown", "none"}).sum())
        rows.append(
            {
                "column": name,
                "present": True,
                "n_missing": missing,
                "pct_missing": round(100.0 * missing / total, 4) if total else None,
            }
        )
    return rows


def verify_count_semantics(
    path: str | Path,
    obs: pd.DataFrame,
    n_rows: int = 2000,
) -> dict[str, Any]:
    """Check that ``raw/X`` holds integer counts matching the obs QC columns."""
    import h5py

    result: dict[str, Any] = {
        "raw_layer_present": False,
        "raw_is_integer": None,
        "x_layer_looks_log_normalized": None,
        "n_genes_matches_obs": None,
        "total_counts_matches_obs": None,
        "n_rows_checked": 0,
        "reason": None,
    }
    with h5py.File(Path(path), "r") as handle:
        if "raw/X" not in handle:
            result["reason"] = "no raw/X block; derived QC cannot be recomputed from counts"
            return result
        result["raw_layer_present"] = True
        group = handle["raw/X"]
        indptr = group["indptr"][: n_rows + 1]
        stop = int(indptr[-1])
        values = np.asarray(group["data"][:stop])
        indices = np.asarray(group["indices"][:stop])
        result["raw_is_integer"] = bool(np.all(values == np.round(values)))
        row_lengths = np.diff(indptr)
        row_sums = np.add.reduceat(values, indptr[:-1]) if stop else np.zeros(0)
        checked = int(row_lengths.size)
        result["n_rows_checked"] = checked
        if "X" in handle:
            x_values = np.asarray(handle["X"]["data"][: min(stop, 100_000)])
            result["x_layer_looks_log_normalized"] = bool(
                x_values.size and not np.all(x_values == np.round(x_values))
            )
        # Genes annotated to the mitochondrial contig are counted separately when
        # available; here only row-level agreement is asserted.
        del indices
    genes_column = QC_COLUMNS["n_genes"]
    counts_column = QC_COLUMNS["total_counts"]
    if genes_column in obs.columns:
        expected = obs[genes_column].to_numpy()[:checked]
        result["n_genes_matches_obs"] = bool(np.array_equal(expected, row_lengths))
    if counts_column in obs.columns:
        expected = obs[counts_column].to_numpy()[:checked].astype(np.float64)
        result["total_counts_matches_obs"] = bool(np.allclose(expected, row_sums))
    return result


def audit_schema(path: str | Path) -> SchemaAudit:
    """Inspect obs/var/uns and report what is present and what is absent."""
    obs, var, uns, n_cells, n_vars = _read_frames(path)
    counts = verify_count_semantics(path, obs)

    fields = {
        "donor": DONOR_COLUMN if DONOR_COLUMN in obs.columns else None,
        "condition": CONDITION_COLUMN if CONDITION_COLUMN in obs.columns else None,
        "stage": "stage" if "stage" in obs.columns else None,
        "development_stage": "development_stage" if "development_stage" in obs.columns else None,
        "sex": "sex" if "sex" in obs.columns else None,
        "batch": next(
            (name for name in ("library", "batch_seq", "sample") if name in obs.columns), None
        ),
        "cell_type": "cell_type" if "cell_type" in obs.columns else None,
    }

    gene_ids = [str(value) for value in var.index[:5]]
    ensembl_share = float(
        np.mean([bool(ENSEMBL_ID_PATTERN.match(str(value))) for value in var.index])
    )
    chromosome_column = next((name for name in CHROMOSOME_CANDIDATES if name in var.columns), None)
    chr21 = chr21_mapping_from_var(var)

    schema_version = str(uns.get("schema_version", "unknown"))
    coordinate_columns = [
        name for name in ("start", "end", "feature_length") if name in var.columns
    ]
    genome_build = {
        "declared_in_file": None,
        "coordinate_columns_present": coordinate_columns,
        "cellxgene_schema_version": schema_version,
        "gene_id_scheme": "ensembl_gene_id" if ensembl_share > 0.9 else "unverified",
        "chromosome_naming": (
            None if chromosome_column is None else f"var.{chromosome_column} (UCSC-style names)"
        ),
        "inferred": (
            "GRCh38 / GENCODE human, pinned by the CELLxGENE schema reference"
            if ensembl_share > 0.9
            else "unknown"
        ),
        "verified_by": "in-file var annotation only; coordinates were not re-derived externally",
    }

    mito_mask, mito_detail = mito_gene_mask(var)
    counts_derivable = bool(counts["raw_layer_present"] and counts.get("raw_is_integer"))
    qc_fields = {
        alias: {
            "column": column,
            "present": column in obs.columns,
            "derivable_from_counts": counts_derivable
            and (alias != "pct_mito" or bool(mito_mask.any())),
        }
        for alias, column in QC_COLUMNS.items()
    }
    qc_fields["mitochondrial_mask"] = mito_detail
    atac_qc_present = {name: name in obs.columns for name in ATAC_QC_COLUMNS}
    var_assay = (
        sorted({str(value) for value in var["assay"].unique()}) if "assay" in var.columns else []
    )
    peak_block_present = bool(
        any("peak" in value.lower() or "atac" in value.lower() for value in var_assay)
    )
    obsm_keys = list(uns.get("_obsm_keys", ()))
    peak_block_present = peak_block_present or any(
        "peak" in key.lower() or "atac" in key.lower() for key in obsm_keys
    )

    covariates = {
        "categorical_present": [name for name in CATEGORICAL_COVARIATES if name in obs.columns],
        "categorical_absent": [name for name in CATEGORICAL_COVARIATES if name not in obs.columns],
        "numeric_present": [name for name in NUMERIC_COVARIATES if name in obs.columns],
        "numeric_absent": [name for name in NUMERIC_COVARIATES if name not in obs.columns],
        "rna_qc_present": [column for column in QC_COLUMNS.values() if column in obs.columns],
        "atac_qc_present": [name for name, present in atac_qc_present.items() if present],
    }

    tracked = (
        DONOR_COLUMN,
        CONDITION_COLUMN,
        *QC_COLUMNS.values(),
        *ATAC_QC_COLUMNS,
        *CATEGORICAL_COVARIATES,
        *NUMERIC_COVARIATES,
    )
    missingness = _missingness_rows(obs, tracked)

    blocking: list[str] = []
    unknowns: list[str] = []
    if fields["donor"] is None:
        blocking.append("donor column absent")
    if fields["condition"] is None:
        blocking.append("disease/condition column absent")
    if not counts["raw_layer_present"]:
        unknowns.append("no raw count layer; QC columns cannot be checked against counts")
    elif counts.get("raw_is_integer") is False:
        unknowns.append("raw layer is not integer-valued; raw-count semantics unconfirmed")
    for alias, column in QC_COLUMNS.items():
        info = qc_fields[alias]
        if not info["present"]:
            unknowns.append(f"QC field {alias} ({column}) absent from obs")
        if not info["derivable_from_counts"]:
            unknowns.append(f"QC field {alias} cannot be recomputed from raw counts")
    if not peak_block_present:
        unknowns.append("no ATAC peak feature block in var or obsm; RNA-only feature space")
    if not chr21.usable:
        unknowns.append(f"chr21 mapping not usable: {chr21.reason}")

    status = "BLOCKED" if blocking else ("INCONCLUSIVE" if unknowns else "PASS")
    return SchemaAudit(
        status=status,
        n_cells=n_cells,
        n_vars=n_vars,
        fields=fields,
        gene_identifiers={
            "index_examples": gene_ids,
            "ensembl_share": round(ensembl_share, 6),
            "gene_symbol_column": "gene_name" if "gene_name" in var.columns else None,
            "var_assay_values": var_assay,
            "n_genes_flagged_filtered": (
                int(var["feature_is_filtered"].astype(bool).sum())
                if "feature_is_filtered" in var.columns
                else None
            ),
        },
        genome_build=genome_build,
        count_semantics=counts,
        qc_fields=qc_fields,
        covariates=covariates,
        missingness=missingness,
        atac={
            "peak_block_present": peak_block_present,
            "var_assay_values": var_assay,
            "obsm_keys": obsm_keys,
            "per_cell_atac_qc_present": atac_qc_present,
            "same_nucleus_evidence": (
                "per-cell ATAC QC columns exist on the same obs rows as RNA, so the assay is "
                "same-nucleus multiome; no ATAC feature matrix is present in this file"
                if any(atac_qc_present.values())
                else "absent"
            ),
        },
        chr21=chr21,
        blocking_problems=tuple(blocking),
        open_questions=tuple(unknowns),
    )


DERIVED_QC_COLUMNS = {
    "n_genes": "derived_n_genes",
    "total_counts": "derived_total_counts",
    "pct_mito": "derived_pct_mito",
}


def _donor_table(frame: pd.DataFrame, label: str) -> list[dict[str, Any]]:
    aggregations: dict[str, Any] = {"n_cells": (CONDITION_COLUMN, "size")}
    for alias, column in QC_COLUMNS.items():
        if column in frame.columns:
            aggregations[f"median_{alias}"] = (column, "median")
    for alias, column in DERIVED_QC_COLUMNS.items():
        if column in frame.columns:
            aggregations[f"median_derived_{alias}"] = (column, "median")
    grouped = frame.groupby([DONOR_COLUMN, CONDITION_COLUMN], observed=True).agg(**aggregations)
    grouped = grouped.reset_index()
    for name in ("stage", "sex", "batch_seq", "dev_PCW"):
        if name in frame.columns:
            first = frame.groupby(DONOR_COLUMN, observed=True)[name].agg(
                lambda values: str(values.iloc[0])
            )
            grouped[name] = grouped[DONOR_COLUMN].map(first)
    grouped["layer"] = label
    return grouped.to_dict(orient="records")


def audit_donor_suffix(donor_ids: pd.Series, conditions: pd.Series) -> dict[str, Any]:
    """Check the ``*_DS_*`` / ``*_CON_*`` donor suffix against the condition label."""
    pairs = pd.DataFrame({"donor_id": donor_ids.astype(str), "condition": conditions.astype(str)})
    pairs = pairs.drop_duplicates()
    problems: list[str] = []
    n_with_suffix = 0
    for donor, condition in pairs.itertuples(index=False):
        has_ds = "_DS_" in donor
        has_con = "_CON_" in donor
        if has_ds or has_con:
            n_with_suffix += 1
        if has_ds and has_con:
            problems.append(f"donor {donor} carries both _DS_ and _CON_")
        elif has_ds and condition != POSITIVE_CONDITION:
            problems.append(f"donor {donor} suffix says DS but condition is {condition!r}")
        elif has_con and condition != CONTROL_CONDITION:
            problems.append(f"donor {donor} suffix says control but condition is {condition!r}")
    return {
        "suffix_present": n_with_suffix > 0,
        "n_donors_with_suffix": n_with_suffix,
        "n_donors_checked": int(pairs.shape[0]),
        "agrees": not problems,
        "problems": problems,
        "role": "audit_only; condition label is authoritative",
    }


def _ratio(left: int, right: int) -> float:
    if left <= 0 or right <= 0:
        return float("inf")
    return max(left, right) / min(left, right)


def run_cohort_qc(
    path: str | Path,
    thresholds: QcThresholds | None = None,
    derived: DerivedCellQc | None = None,
) -> CohortQcReport:
    """Produce pre-QC and post-QC full-cohort accounting with frozen thresholds.

    When ``derived`` is supplied the filters run on QC recomputed from the raw
    counts. Otherwise they fall back to the author-supplied ``obs`` columns, and
    the report says which source was used.
    """
    thresholds = thresholds or QcThresholds()
    obs, _var, _uns, n_cells, _n_vars = _read_frames(path)

    tracked = (
        DONOR_COLUMN,
        CONDITION_COLUMN,
        *QC_COLUMNS.values(),
        *ATAC_QC_COLUMNS,
        *CATEGORICAL_COVARIATES,
        *NUMERIC_COVARIATES,
    )
    missingness = _missingness_rows(obs, tracked)

    if DONOR_COLUMN not in obs.columns or CONDITION_COLUMN not in obs.columns:
        return CohortQcReport(
            status="BLOCKED",
            thresholds=thresholds.to_dict(),
            n_cells_pre_qc=n_cells,
            n_cells_post_qc=0,
            n_donors_pre_qc=0,
            n_donors_post_qc=0,
            missingness=missingness,
            stop_reasons=("donor or condition column absent",),
        )

    obs[DONOR_COLUMN] = obs[DONOR_COLUMN].astype(str)
    obs[CONDITION_COLUMN] = obs[CONDITION_COLUMN].astype(str)
    if derived is not None:
        for alias, column in DERIVED_QC_COLUMNS.items():
            values = {
                "n_genes": derived.n_genes,
                "total_counts": derived.total_counts,
                "pct_mito": derived.pct_mito,
            }[alias]
            if values is not None:
                obs[column] = np.asarray(values, dtype=float)
    suffix_audit = audit_donor_suffix(obs[DONOR_COLUMN], obs[CONDITION_COLUMN])

    purity = obs.groupby(DONOR_COLUMN, observed=True)[CONDITION_COLUMN].nunique()
    impure = sorted(purity[purity > 1].index.tolist())

    keep = np.ones(n_cells, dtype=bool)
    exclusions: list[dict[str, Any]] = []

    def apply_rule(name: str, failing: np.ndarray, detail: str) -> None:
        nonlocal keep
        newly = failing & keep
        exclusions.append(
            {
                "rule": name,
                "detail": detail,
                "n_cells_failing": int(failing.sum()),
                "n_cells_removed_here": int(newly.sum()),
            }
        )
        keep = keep & ~failing

    genes_column = QC_COLUMNS["n_genes"]
    counts_column = QC_COLUMNS["total_counts"]
    mito_column = QC_COLUMNS["pct_mito"]
    unknowns: list[str] = []

    def qc_values(alias: str, column: str) -> tuple[np.ndarray | None, str]:
        if derived is not None:
            candidate = {
                "n_genes": derived.n_genes,
                "total_counts": derived.total_counts,
                "pct_mito": derived.pct_mito,
            }[alias]
            if candidate is not None:
                return np.asarray(candidate, dtype=float), f"derived:{alias}"
        if column in obs.columns:
            return obs[column].to_numpy(dtype=float), f"obs:{column}"
        return None, "absent"

    genes_values, genes_source = qc_values("n_genes", genes_column)
    if genes_values is not None:
        apply_rule(
            "min_genes",
            genes_values < thresholds.min_genes,
            f"{genes_source} < {thresholds.min_genes}",
        )
    else:
        unknowns.append(f"{genes_column} absent and not derivable; gene filter not applied")

    counts_values, counts_source = qc_values("total_counts", counts_column)
    if counts_values is not None:
        apply_rule(
            "min_total_counts",
            counts_values < thresholds.min_total_counts,
            f"{counts_source} < {thresholds.min_total_counts}",
        )
    else:
        unknowns.append(f"{counts_column} absent and not derivable; count filter not applied")

    mito_values, mito_source = qc_values("pct_mito", mito_column)
    if mito_values is not None:
        failing = np.isnan(mito_values) | (mito_values > thresholds.max_pct_mito)
        apply_rule(
            "max_pct_mito",
            failing,
            f"{mito_source} > {thresholds.max_pct_mito} or missing",
        )
    else:
        unknowns.append(f"{mito_column} absent and not derivable; mito filter not applied")

    qc_sources = {
        "n_genes": genes_source,
        "total_counts": counts_source,
        "pct_mito": mito_source,
    }

    unlabelled = ~obs[CONDITION_COLUMN].isin([POSITIVE_CONDITION, CONTROL_CONDITION]).to_numpy()
    apply_rule(
        "condition_label_recognized",
        unlabelled,
        f"condition not in {{{POSITIVE_CONDITION!r}, {CONTROL_CONDITION!r}}}",
    )
    if impure:
        apply_rule(
            "donor_label_purity",
            obs[DONOR_COLUMN].isin(impure).to_numpy(),
            f"donors with mixed condition labels: {impure[:5]}",
        )

    pre_frame = obs
    post_frame = obs.loc[keep]

    donor_post = post_frame.groupby(DONOR_COLUMN, observed=True).size()
    thin_donors = sorted(
        donor_post[donor_post < thresholds.min_usable_cells_per_donor].index.tolist()
    )

    condition_cells_pre = pre_frame[CONDITION_COLUMN].value_counts().astype(int).to_dict()
    condition_cells_post = post_frame[CONDITION_COLUMN].value_counts().astype(int).to_dict()
    donor_conditions = post_frame.groupby(DONOR_COLUMN, observed=True)[CONDITION_COLUMN].first()
    condition_donors_post = donor_conditions.value_counts().astype(int).to_dict()

    n_control_donors = int(condition_donors_post.get(CONTROL_CONDITION, 0))
    n_ds_donors = int(condition_donors_post.get(POSITIVE_CONDITION, 0))
    donor_ratio = _ratio(n_control_donors, n_ds_donors)
    cell_ratio = _ratio(
        int(condition_cells_post.get(CONTROL_CONDITION, 0)),
        int(condition_cells_post.get(POSITIVE_CONDITION, 0)),
    )

    stop_reasons: list[str] = []
    if impure:
        stop_reasons.append(f"{len(impure)} donors carry conflicting condition labels")
    if not suffix_audit["agrees"]:
        stop_reasons.append(
            f"donor suffix disagrees with condition for {len(suffix_audit['problems'])} donors"
        )
    if n_control_donors < thresholds.min_donors_per_condition:
        stop_reasons.append(
            f"control donors {n_control_donors} < {thresholds.min_donors_per_condition}"
        )
    if n_ds_donors < thresholds.min_donors_per_condition:
        stop_reasons.append(f"DS donors {n_ds_donors} < {thresholds.min_donors_per_condition}")
    if thin_donors:
        stop_reasons.append(
            f"{len(thin_donors)} donors have < {thresholds.min_usable_cells_per_donor} "
            f"usable cells: {thin_donors[:5]}"
        )
    if donor_ratio > thresholds.max_donor_class_ratio:
        stop_reasons.append(
            f"donor class ratio {donor_ratio:.3f} > {thresholds.max_donor_class_ratio}"
        )
    if cell_ratio > thresholds.max_cell_class_ratio:
        stop_reasons.append(
            f"cell class ratio {cell_ratio:.3f} > {thresholds.max_cell_class_ratio}"
        )

    status = "BLOCKED" if stop_reasons else ("INCONCLUSIVE" if unknowns else "PASS")
    return CohortQcReport(
        status=status,
        thresholds=thresholds.to_dict(),
        n_cells_pre_qc=int(n_cells),
        n_cells_post_qc=int(keep.sum()),
        n_donors_pre_qc=int(pre_frame[DONOR_COLUMN].nunique()),
        n_donors_post_qc=int(post_frame[DONOR_COLUMN].nunique()),
        condition_cells_pre_qc={str(k): int(v) for k, v in condition_cells_pre.items()},
        condition_cells_post_qc={str(k): int(v) for k, v in condition_cells_post.items()},
        condition_donors_post_qc={str(k): int(v) for k, v in condition_donors_post.items()},
        donor_table_pre_qc=_donor_table(pre_frame, "pre_qc"),
        donor_table_post_qc=_donor_table(post_frame, "post_qc"),
        exclusions=exclusions,
        missingness=missingness,
        suffix_audit=suffix_audit,
        ratios={
            "donor_class_ratio": donor_ratio,
            "cell_class_ratio": cell_ratio,
            "retained_fraction": float(keep.mean()),
        },
        qc_sources=qc_sources,
        derived_qc={} if derived is None else derived.to_dict(),
        stop_reasons=tuple(stop_reasons),
        open_questions=tuple(unknowns),
        keep_mask=keep,
        obs=obs,
    )


def _row_runs(rows: np.ndarray) -> list[tuple[int, int]]:
    """Merge sorted row indices into contiguous ``[start, stop)`` runs."""
    if rows.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(rows) != 1)
    starts = np.concatenate([[0], breaks + 1])
    stops = np.concatenate([breaks + 1, [rows.size]])
    return [
        (int(rows[start]), int(rows[stop - 1]) + 1)
        for start, stop in zip(starts, stops, strict=True)
    ]


def donor_pseudobulk(
    path: str | Path,
    obs: pd.DataFrame,
    keep_mask: np.ndarray,
    chr21_mapping: Chr21Mapping | None = None,
    chunk_rows: int = 20_000,
    matrix_key: str = "raw/X",
) -> DonorPseudobulk:
    """Stream raw counts and sum them per donor over every retained cell.

    The matrix is read in row chunks and reduced with a sparse donor indicator,
    so no dense cell-by-gene block is ever materialised.
    """
    import h5py
    from scipy import sparse

    donors = obs[DONOR_COLUMN].astype(str).to_numpy()
    conditions = obs[CONDITION_COLUMN].astype(str).to_numpy()
    donor_ids = tuple(sorted(set(donors[keep_mask])))
    donor_index = {donor: position for position, donor in enumerate(donor_ids)}
    donor_code = np.array([donor_index.get(value, -1) for value in donors], dtype=np.int64)

    with h5py.File(Path(path), "r") as handle:
        group = handle[matrix_key]
        n_genes = int(group.attrs["shape"][1])
        indptr = np.asarray(group["indptr"][:])
        data = group["data"]
        indices = group["indices"]
        gene_sums = np.zeros((len(donor_ids), n_genes), dtype=np.float64)
        n_cells = np.zeros(len(donor_ids), dtype=np.int64)
        total = indptr.size - 1
        for start in range(0, total, chunk_rows):
            stop = min(start + chunk_rows, total)
            local_keep = keep_mask[start:stop]
            if not local_keep.any():
                continue
            low, high = int(indptr[start]), int(indptr[stop])
            chunk = sparse.csr_matrix(
                (
                    np.asarray(data[low:high], dtype=np.float64),
                    np.asarray(indices[low:high]),
                    indptr[start : stop + 1] - low,
                ),
                shape=(stop - start, n_genes),
            )
            rows = np.flatnonzero(local_keep)
            codes = donor_code[start:stop][rows]
            indicator = sparse.csr_matrix(
                (np.ones(rows.size), (rows, codes)),
                shape=(stop - start, len(donor_ids)),
            )
            gene_sums += np.asarray((indicator.T @ chunk).todense())
            np.add.at(n_cells, codes, 1)

    var = read_var(path)
    gene_ids = tuple(str(value) for value in var.index)
    total_counts = gene_sums.sum(axis=1)
    chr21_fraction = None
    if chr21_mapping is not None and chr21_mapping.usable:
        column = chr21_mapping.chromosome_column
        chromosomes = var[column].astype(str).str.lower()
        chr21_mask = chromosomes.isin([label.lower() for label in CHR21_LABELS]).to_numpy()
        safe_totals = np.where(total_counts > 0, total_counts, 1.0)
        chr21_fraction = gene_sums[:, chr21_mask].sum(axis=1) / safe_totals

    donor_condition = {}
    for donor, condition in zip(donors[keep_mask], conditions[keep_mask], strict=True):
        donor_condition.setdefault(donor, condition)
    ordered_conditions = tuple(donor_condition[donor] for donor in donor_ids)
    labels = np.array(
        [1 if condition == POSITIVE_CONDITION else 0 for condition in ordered_conditions],
        dtype=int,
    )
    return DonorPseudobulk(
        donor_ids=donor_ids,
        conditions=ordered_conditions,
        labels=labels,
        n_cells=n_cells,
        total_counts=total_counts,
        gene_sums=gene_sums,
        chr21_fraction=chr21_fraction,
        gene_ids=gene_ids,
        chr21_mapping=chr21_mapping,
    )


def sample_capped_cells(
    obs: pd.DataFrame,
    keep_mask: np.ndarray,
    cap: int,
    seed: int = 0,
) -> np.ndarray:
    """Pick at most ``cap`` retained cells per donor, deterministically."""
    return sample_nested_capped_cells(obs, keep_mask, caps=(cap,), seed=seed)[cap]


def sample_nested_capped_cells(
    obs: pd.DataFrame,
    keep_mask: np.ndarray,
    caps: Sequence[int],
    seed: int = 0,
) -> dict[int, np.ndarray]:
    """Pick nested donor-level samples from one deterministic random ordering."""
    ordered_caps = tuple(sorted({int(cap) for cap in caps}))
    if not ordered_caps or ordered_caps[0] < 1:
        raise ValueError("caps must contain positive integers")
    donors = obs[DONOR_COLUMN].astype(str).to_numpy()
    positions = np.flatnonzero(keep_mask)
    rng = np.random.default_rng(seed)
    chosen: dict[int, list[np.ndarray]] = {cap: [] for cap in ordered_caps}
    for donor in sorted(set(donors[positions])):
        donor_positions = positions[donors[positions] == donor]
        donor_order = rng.permutation(donor_positions)
        for cap in ordered_caps:
            chosen[cap].append(np.sort(donor_order[:cap]))
    return {
        cap: (
            np.sort(np.concatenate(groups)).astype(np.int64)
            if groups
            else np.zeros(0, dtype=np.int64)
        )
        for cap, groups in chosen.items()
    }


# The RNA view consumes the raw count block. ``X`` is the author-processed
# (log-normalized) matrix and must never be presented as raw counts.
DEFAULT_RNA_MATRIX_KEY = "raw/X"
# A matrix block and the axis its columns follow. The raw block's columns follow
# ``raw/var``; attaching processed ``var`` labels to raw columns is a defect.
AXIS_KEY_FOR_MATRIX = {"raw/X": "raw/var", "X": "var"}


def _as_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _read_index_column(group, name: str = "_index") -> list[str] | None:
    """Read an AnnData index column, decoding a categorical or string dataset."""
    import h5py

    if name not in group:
        return None
    dataset = group[name]
    if isinstance(dataset, h5py.Group):
        categories = np.asarray(dataset["categories"][:])
        codes = np.asarray(dataset["codes"][:])
        return [_as_text(value) for value in categories[codes]]
    return [_as_text(value) for value in np.asarray(dataset[:])]


def read_matrix_axis(path: str | Path, matrix_key: str = DEFAULT_RNA_MATRIX_KEY) -> dict[str, Any]:
    """Return the ordered axis identifiers for a matrix block.

    ``raw/X`` columns follow ``raw/var`` and ``X`` columns follow ``var``. The
    returned ``axis_key`` names the block actually read so a caller cannot attach
    processed gene labels to raw columns.
    """
    import h5py

    axis_key = AXIS_KEY_FOR_MATRIX.get(matrix_key)
    with h5py.File(Path(path), "r") as handle:
        if matrix_key not in handle:
            raise KeyError(f"matrix block {matrix_key!r} is absent from {path}")
        group = handle[matrix_key]
        shape = tuple(int(value) for value in group.attrs["shape"])
        gene_ids: list[str] | None = None
        axis_source = "unresolved"
        if axis_key and axis_key in handle:
            gene_ids = _read_index_column(handle[axis_key])
            axis_source = axis_key
    return {
        "matrix_key": matrix_key,
        "axis_key": axis_source,
        "n_cells": shape[0],
        "n_genes": shape[1],
        "gene_ids": gene_ids,
    }


def _assert_raw_count_semantics(values: np.ndarray, matrix_key: str) -> None:
    """Refuse a consumed block that is not finite, nonnegative integer counts."""
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{matrix_key} contains non-finite values; not a raw count matrix")
    if np.any(values < 0):
        raise ValueError(f"{matrix_key} contains negative values; not a raw count matrix")
    if not np.all(values == np.floor(values)):
        raise ValueError(
            f"{matrix_key} contains non-integer values; the raw count representation "
            "is required (pass an explicit processed key with validate_counts=False "
            "to consume a normalized block)"
        )


def load_cell_matrix(
    path: str | Path,
    row_positions: np.ndarray,
    matrix_key: str = DEFAULT_RNA_MATRIX_KEY,
    *,
    validate_counts: bool = True,
):
    """Gather the given rows from a CSR block into an in-memory sparse matrix.

    Defaults to the raw count block ``raw/X``. When ``validate_counts`` is set,
    the values actually consumed must be finite, nonnegative integers, so a
    processed (e.g. log-normalized) block cannot be silently consumed as counts.
    """
    import h5py
    from scipy import sparse

    rows = np.sort(np.asarray(row_positions, dtype=np.int64))
    with h5py.File(Path(path), "r") as handle:
        if matrix_key not in handle:
            raise KeyError(f"matrix block {matrix_key!r} is absent from {path}")
        group = handle[matrix_key]
        n_genes = int(group.attrs["shape"][1])
        indptr = np.asarray(group["indptr"][:])
        data = group["data"]
        indices = group["indices"]
        blocks: list[Any] = []
        for start, stop in _row_runs(rows):
            low, high = int(indptr[start]), int(indptr[stop])
            values = np.asarray(data[low:high], dtype=np.float32)
            if validate_counts:
                _assert_raw_count_semantics(values, matrix_key)
            blocks.append(
                sparse.csr_matrix(
                    (
                        values,
                        np.asarray(indices[low:high]),
                        indptr[start : stop + 1] - low,
                    ),
                    shape=(stop - start, n_genes),
                )
            )
    return sparse.vstack(blocks, format="csr") if blocks else sparse.csr_matrix((0, 0))


def covariate_frame(obs: pd.DataFrame, row_positions: np.ndarray | None = None) -> pd.DataFrame:
    """Build a numeric covariate table from observed fields only.

    Categorical fields are one-hot encoded. No batch value is invented: a field
    that is absent from ``obs`` simply does not appear here.
    """
    frame = obs if row_positions is None else obs.iloc[np.asarray(row_positions)]
    parts: list[pd.DataFrame] = []
    numeric = (
        *QC_COLUMNS.values(),
        *DERIVED_QC_COLUMNS.values(),
        *ATAC_QC_COLUMNS,
        *NUMERIC_COVARIATES,
    )
    for column in numeric:
        if column in frame.columns:
            parts.append(pd.DataFrame({column: frame[column].to_numpy(dtype=float)}))
    for column in CATEGORICAL_COVARIATES:
        if column not in frame.columns:
            continue
        dummies = pd.get_dummies(frame[column].astype(str), prefix=column, dtype=float)
        parts.append(dummies.reset_index(drop=True))
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, axis=1)
