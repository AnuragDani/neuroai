"""Frozen donor-level RNA direction replication against published summary effects.

The external p-values never enter the analysis. This module does not establish
predictive validation, raw external replication, or causal biological effects.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from p22.data.census import sha256_file
from p22.data.real_cohort import (
    CONTROL_CONDITION,
    POSITIVE_CONDITION,
    DonorPseudobulk,
    mito_gene_mask,
    symbol_series,
)

EXTERNAL_ACCESSION = "GSE280175"
EXTERNAL_URL = (
    "https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-025-63752-0/"
    "MediaObjects/41467_2025_63752_MOESM4_ESM.xlsx"
)
EXTERNAL_SHA256 = "ea0e5a0d96e122ce39ace8be29b65039c3f7775cc96699873a8acc4ee74ccf13"
EXTERNAL_SIZE_BYTES = 19_576_790
SHEETS = {"oRG": "oRG", "vRG": "vRG", "CP": "Cycling_progenitors", "IP": "IP"}
COMPARISONS = (
    ("RG", ("RG",), "oRG"),
    ("RG", ("RG",), "vRG"),
    ("cycling_progenitors", ("RG_prol", "IPC_prol"), "CP"),
    ("IPC", ("IPC",), "IP"),
)
MIN_CELLS_PER_DONOR = 50
MIN_SHARED_GENES = 500
MIN_CPM = 1.0
MIN_CLASS_EXPRESSION_FRACTION = 0.5
MIN_POSITIVE_CHR21_FRACTION = 0.8
MAX_FAILED_BOOTSTRAP_FRACTION = 0.05
N_BOOTSTRAP = 1_000
N_PERMUTATIONS = 1_000
TOP_N = 100
SEED = 22
NOMINAL_ALPHA = 0.025
EVIDENCE_SCOPE = (
    "published cell-level MAST summary effects (donor covariate); not raw external reanalysis"
)
REQUIRED_COLUMNS = {
    "gene",
    "avg_log2FC",
    "p_val",
    "p_val_adj",
    "pct.1",
    "pct.2",
    "celltype",
    "FDR",
    "sig",
}


def _symbols(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().str.upper().fillna("")


def gene_eligibility(gene_metadata: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return row-aligned symbols and the frozen autosomal non-chr21 mask."""
    if "seqnames" not in gene_metadata:
        raise ValueError("gene schema requires var.seqnames")
    symbols = _symbols(gene_metadata.get("gene_name", symbol_series(gene_metadata)))
    chromosomes = _symbols(gene_metadata["seqnames"]).str.removeprefix("CHR")
    duplicate = symbols.duplicated(keep=False) & symbols.ne("")
    mito, _ = mito_gene_mask(gene_metadata)
    canonical = chromosomes.isin([str(chromosome) for chromosome in range(1, 23)])
    excluded = ~canonical | chromosomes.eq("21") | mito | symbols.str.startswith("MT-")
    eligible = ~(excluded | duplicate | symbols.eq(""))
    return pd.DataFrame(
        {
            "gene": symbols.to_numpy(),
            "chromosome": chromosomes.to_numpy(),
            "eligible": eligible.to_numpy(),
            "duplicate": duplicate.to_numpy(),
        },
        index=gene_metadata.index,
    ), {
        "dropped_duplicate_primary": int(duplicate.sum()),
        "dropped_missing_primary_symbol": int(symbols.eq("").sum()),
        "excluded_chromosome_or_mito": int(excluded.sum()),
    }


def load_external_effects(
    path: str | Path,
    *,
    gene_metadata: pd.DataFrame,
    expected_sha256: str = EXTERNAL_SHA256,
    sheets: dict[str, str] = SHEETS,
) -> dict[str, pd.DataFrame]:
    """Hash, schema, and orientation guards run before returning any effects."""
    path = Path(path)
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise ValueError("external workbook hash mismatch")
    genes, _ = gene_eligibility(gene_metadata)
    chr21 = set(genes.loc[genes.chromosome.eq("21") & ~genes.duplicate, "gene"])
    result = {}
    # ExcelFile closes its openpyxl workbook on exit; only the four sheets parse.
    # https://pandas.pydata.org/pandas-docs/version/2.2/reference/api/pandas.read_excel.html
    with pd.ExcelFile(path, engine="openpyxl") as workbook:
        if not set(sheets).issubset(workbook.sheet_names):
            raise ValueError("external workbook schema: required sheet missing")
        for sheet, celltype in sheets.items():
            frame = pd.read_excel(workbook, sheet_name=sheet)
            if not REQUIRED_COLUMNS.issubset(frame.columns):
                raise ValueError(f"external workbook schema mismatch: {sheet}")
            if frame.empty or frame.celltype.isna().any() or set(frame.celltype) != {celltype}:
                raise ValueError(f"external workbook celltype mismatch: {sheet}")
            frame["gene"] = _symbols(frame.gene)
            frame["avg_log2FC"] = pd.to_numeric(frame.avg_log2FC, errors="raise")
            if not np.isfinite(frame.avg_log2FC.to_numpy(dtype=float)).all():
                raise ValueError(f"external workbook non-finite effect: {sheet}")
            duplicated = frame.gene.duplicated(keep=False) & frame.gene.ne("")
            missing = frame.gene.eq("")
            clean = frame.loc[~(duplicated | missing)].copy().reset_index(drop=True)
            dosage = clean.loc[clean.gene.isin(chr21), "avg_log2FC"].to_numpy(dtype=float)
            if (
                not dosage.size
                or np.median(dosage) <= 0
                or np.mean(dosage > 0) < MIN_POSITIVE_CHR21_FRACTION
            ):
                raise ValueError(f"external orientation check failed: {sheet}")
            clean.attrs.update(
                external_sha256=actual,
                dropped_duplicate_external=int(duplicated.sum()),
                dropped_missing_external_symbol=int(missing.sum()),
                orientation_n_chr21=int(dosage.size),
                orientation_median_chr21=float(np.median(dosage)),
                orientation_positive_fraction=float(np.mean(dosage > 0)),
            )
            result[sheet] = clean
    return result


def collapse_donor_metadata(
    obs: pd.DataFrame, donor_ids: Sequence[str] | None = None
) -> pd.DataFrame:
    """Assert invariance before collapsing; preserve requested pseudobulk order."""
    columns = ["donor_id", "disease", "dev_PCW", "sex"]
    if not set(columns).issubset(obs.columns) or obs[columns].isna().any().any():
        raise ValueError("donor metadata schema or missing values")
    frame = obs[columns].copy()
    frame["donor_id"] = frame.donor_id.astype(str)
    if frame.donor_id.str.strip().eq("").any():
        raise ValueError("missing donor ID")
    if (frame.groupby("donor_id", observed=True).nunique(dropna=False) != 1).any().any():
        raise ValueError("disease, PCW, and sex must be invariant within donor")
    frame = frame.drop_duplicates("donor_id").set_index("donor_id")
    if not set(frame.disease).issubset({CONTROL_CONDITION, POSITIVE_CONDITION}):
        raise ValueError("unknown donor condition")
    frame["label"] = frame.disease.eq(POSITIVE_CONDITION).astype(int)
    frame["sex"] = frame.sex.astype(str).str.strip().str.lower()
    if not set(frame.sex).issubset({"male", "female"}):
        raise ValueError("unknown donor sex")
    frame["dev_PCW"] = pd.to_numeric(frame.dev_PCW, errors="raise")
    if not np.isfinite(frame.dev_PCW).all():
        raise ValueError("non-finite donor PCW")
    order = sorted(frame.index) if donor_ids is None else list(donor_ids)
    if len(set(order)) != len(order) or not set(order).issubset(frame.index):
        raise ValueError("pseudobulk donor IDs must be unique and present in metadata")
    return frame.loc[order]


@dataclass
class DiscoveryEffects:
    """Observed eligible genes plus donor-aligned inputs for bootstrap refits."""

    effects: pd.DataFrame
    log_cpm: np.ndarray
    cpm: np.ndarray
    design: np.ndarray
    labels: np.ndarray
    audit: dict


def _expression_floor(cpm: np.ndarray, labels: np.ndarray) -> np.ndarray:
    return np.logical_and.reduce(
        [
            np.mean(cpm[labels == label] >= MIN_CPM, axis=0) >= MIN_CLASS_EXPRESSION_FRACTION
            for label in (0, 1)
        ]
    )


def _fit_ols(log_cpm: np.ndarray, design: np.ndarray) -> tuple[np.ndarray, ...]:
    if design.shape[0] <= design.shape[1] or np.linalg.matrix_rank(design) != design.shape[1]:
        raise ValueError(
            "covariate design matrix is rank-deficient or has no residual degrees of freedom"
        )
    # Multi-response OLS shares the same donor design across genes.
    # https://numpy.org/doc/1.26/reference/generated/numpy.linalg.lstsq.html
    beta = np.linalg.lstsq(design, log_cpm, rcond=None)[0]
    variance = np.sum((log_cpm - design @ beta) ** 2, axis=0) / (len(design) - design.shape[1])
    standard_error = np.sqrt(variance * np.linalg.inv(design.T @ design)[1, 1])
    coefficient = beta[1]
    constant = np.ptp(log_cpm, axis=0) == 0
    coefficient[constant] = 0.0
    standard_error[constant] = 0.0
    with np.errstate(divide="ignore", invalid="ignore"):
        statistic = np.divide(coefficient, standard_error)
    statistic[(coefficient == 0) & (standard_error == 0)] = 0.0
    if not np.isfinite(coefficient).all() or np.isnan(statistic).any():
        raise ValueError("non-finite OLS effects")
    return coefficient, standard_error, statistic


def fit_discovery_effects(
    counts: DonorPseudobulk | np.ndarray,
    donor_metadata: pd.DataFrame,
    gene_metadata: pd.DataFrame,
    *,
    n_cells: np.ndarray | None = None,
) -> DiscoveryEffects:
    """Fit log1p(CPM) ~ DS + exact PCW + female, never cell-level replicates.

    Metadata rows and gene rows must match the count matrix. Passing the existing
    DonorPseudobulk object additionally verifies both identifier orders.
    """
    metadata = collapse_donor_metadata(donor_metadata.reset_index(), donor_metadata.index)
    labels = metadata.label.to_numpy(dtype=int)
    if set(labels) != {0, 1}:
        raise ValueError("both disease classes must be present")
    bulk = counts if isinstance(counts, DonorPseudobulk) else None
    values = np.asarray(bulk.gene_sums if bulk is not None else counts, dtype=float)
    if (
        values.shape != (len(metadata), len(gene_metadata))
        or not np.isfinite(values).all()
        or (values < 0).any()
        or (values != np.floor(values)).any()
        or (values.sum(axis=1) <= 0).any()
    ):
        raise ValueError("invalid donor pseudobulk counts or row/gene alignment")
    if bulk is not None:
        if (
            tuple(metadata.index) != bulk.donor_ids
            or tuple(gene_metadata.index.astype(str)) != bulk.gene_ids
            or not np.array_equal(labels, bulk.labels)
            or not np.array_equal(values.sum(axis=1), bulk.total_counts)
        ):
            raise ValueError("pseudobulk identifiers, labels, or totals mismatch")
        n_cells = bulk.n_cells
    cells = np.asarray(n_cells)
    if (
        cells.shape != (len(metadata),)
        or cells.dtype.kind not in "iu"
        or (cells < MIN_CELLS_PER_DONOR).any()
    ):
        raise ValueError(
            f"each donor-population pair requires at least {MIN_CELLS_PER_DONOR} cells"
        )
    if bulk is None:
        bulk = DonorPseudobulk(
            donor_ids=tuple(metadata.index),
            conditions=tuple(metadata.disease),
            labels=labels,
            n_cells=cells,
            total_counts=values.sum(axis=1),
            gene_sums=values,
            chr21_fraction=None,
            gene_ids=tuple(gene_metadata.index.astype(str)),
            chr21_mapping=None,
        )
    log_cpm = bulk.log_cpm()
    cpm = values / bulk.total_counts[:, None] * 1e6
    genes, audit = gene_eligibility(gene_metadata)
    expression = _expression_floor(cpm, labels)
    keep = genes.eligible.to_numpy(dtype=bool) & expression
    if not keep.any():
        raise ValueError("no genes pass discovery expression and annotation filters")
    design = np.column_stack(
        [
            np.ones(len(metadata)),
            labels,
            metadata.dev_PCW.to_numpy(dtype=float),
            metadata.sex.eq("female").to_numpy(dtype=float),
        ]
    )
    selected = np.flatnonzero(keep)
    selected = selected[np.argsort(genes.gene.iloc[selected].to_numpy(), kind="stable")]
    log_cpm, cpm = log_cpm[:, selected], cpm[:, selected]
    coefficient, standard_error, statistic = _fit_ols(log_cpm, design)
    effects = pd.DataFrame(
        {
            "gene": genes.gene.iloc[selected].to_numpy(),
            "coefficient": coefficient,
            "standard_error": standard_error,
            "t_statistic": statistic,
        }
    )
    audit.update(
        n_expression_eligible=int(expression.sum()),
        n_primary_eligible=int(keep.sum()),
        n_ds_donors=int(labels.sum()),
        n_control_donors=int((labels == 0).sum()),
        min_cells_per_donor=int(cells.min()),
        design_rank=4,
        residual_df=len(metadata) - 4,
        batch_modelled=False,
        expression_floor_reapplied_in_bootstrap=True,
    )
    return DiscoveryEffects(effects, log_cpm, cpm, design, labels, audit)
