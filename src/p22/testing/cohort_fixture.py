"""Synthetic H5AD shaped like the public cohort, for wiring tests only.

The file written here has the same field names, count semantics, and chromosome
annotation as the public dataset, so the real-cohort code path can be exercised
end to end without a 1.57 GB download.

The signal is deliberately imperfect and donor-structured: per-donor dosage
multipliers overlap between the two groups, so a perfect score from this fixture
means a leak in the evaluation code, not a discovery. Nothing produced from this
file is evidence about any condition.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from p22.data.real_cohort import CONTROL_CONDITION, POSITIVE_CONDITION

SYNTHETIC_MARKER = "synthetic_wiring_fixture"
BATCHES = ("E16", "E18", "E20", "E22")
LIBRARIES = ("L01", "L02", "L03", "L04", "L05")
STAGES = ("PCW11_12", "PCW13_16", "PCW17_20")


def _var_frame(
    n_genes: int, n_chr21: int, n_mito: int, symbol_pool: tuple[str, ...]
) -> pd.DataFrame:
    """Build a var block with Ensembl IDs, chromosomes, and gene symbols."""
    gene_ids = [f"ENSG{index:011d}" for index in range(n_genes)]
    chromosomes = ["chr21"] * n_chr21 + ["chr1"] * (n_genes - n_chr21)
    symbols = [f"SYNGENE{index:05d}" for index in range(n_genes)]
    # Panel symbols are placed on chromosome 21 or elsewhere to match the panels
    # the validation stage tests, so the lookup exercises real code paths.
    for offset, symbol in enumerate(symbol_pool):
        position = offset if offset < n_chr21 else n_chr21 + (offset - n_chr21)
        if position < n_genes:
            symbols[position] = symbol
    for offset in range(n_mito):
        symbols[n_genes - 1 - offset] = f"MT-SYN{offset + 1}"
    return pd.DataFrame(
        {
            "feature_name": symbols,
            "gene_name": symbols,
            "assay": pd.Categorical(["Gene Expression"] * n_genes),
            "seqnames": pd.Categorical(chromosomes),
            "feature_type": pd.Categorical(["protein_coding"] * n_genes),
            "feature_is_filtered": np.zeros(n_genes, dtype=bool),
            "start": np.arange(n_genes, dtype=np.int64) * 1000,
            "end": np.arange(n_genes, dtype=np.int64) * 1000 + 800,
            "feature_length": np.full(n_genes, 800, dtype=np.int64),
        },
        index=gene_ids,
    )


def write_synthetic_cohort_h5ad(
    path: str | Path,
    n_donors_per_class: int = 15,
    cells_per_donor: int = 72,
    n_genes: int = 1000,
    n_chr21_genes: int = 300,
    n_mito_genes: int = 13,
    seed: int = 20260728,
    dosage_effect: float = 0.5,
    donor_dosage_noise: float = 0.22,
    panel_symbols: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Write a cohort-shaped synthetic H5AD and return its generation record.

    Args:
        path: destination ``.h5ad`` path.
        n_donors_per_class: donors per condition.
        cells_per_donor: cells generated for every donor.
        n_genes: total features.
        n_chr21_genes: features annotated to chromosome 21.
        n_mito_genes: features carrying an ``MT-`` symbol.
        seed: generator seed; the same seed writes the same file.
        dosage_effect: mean chromosome-21 lift applied to the positive group.
        donor_dosage_noise: per-donor spread of that lift, which is what makes the
            groups overlap.
        panel_symbols: marker symbols to plant so panel lookups find real columns.

    Returns:
        A record of the generation parameters and the resulting counts.
    """
    import anndata
    from scipy import sparse

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    donors: list[str] = []
    conditions: list[str] = []
    for index in range(n_donors_per_class):
        donors.append(f"PCW12_CON_{index:05d}")
        conditions.append(CONTROL_CONDITION)
        donors.append(f"PCW12_DS_{index:05d}")
        conditions.append(POSITIVE_CONDITION)
    donor_labels = np.array(
        [1 if value == POSITIVE_CONDITION else 0 for value in conditions], dtype=int
    )
    n_donors = len(donors)
    n_cells = n_donors * cells_per_donor

    donor_index = np.repeat(np.arange(n_donors), cells_per_donor)
    cell_donor = np.asarray(donors, dtype=object)[donor_index]
    cell_condition = np.asarray(conditions, dtype=object)[donor_index]
    cell_labels = donor_labels[donor_index]

    # Overlapping per-donor dosage multipliers keep the fixture honest.
    donor_multiplier = 1.0 + dosage_effect * donor_labels
    donor_multiplier += rng.normal(0.0, donor_dosage_noise, size=n_donors)
    donor_multiplier = np.clip(donor_multiplier, 0.5, None)
    donor_depth = rng.uniform(0.8, 1.6, size=n_donors)

    base_rate = rng.gamma(1.4, 1.0, size=n_genes) * 0.9
    rate = np.tile(base_rate, (n_cells, 1))
    rate[:, :n_chr21_genes] *= donor_multiplier[donor_index][:, None]
    # A handful of non-chr21 genes carry a weak condition effect so a learned
    # model has something beyond dosage, but far less than the dosage signal.
    weak = slice(n_chr21_genes, n_chr21_genes + 60)
    rate[:, weak] *= 1.0 + 0.15 * cell_labels[:, None]
    rate *= donor_depth[donor_index][:, None]
    rate *= rng.uniform(0.7, 1.3, size=(n_cells, 1))

    counts = rng.poisson(rate).astype(np.float32)
    raw = sparse.csr_matrix(counts)
    totals = np.maximum(counts.sum(axis=1, keepdims=True), 1.0)
    normalized = sparse.csr_matrix(np.log1p(counts / totals * 1e4).astype(np.float32))

    var = _var_frame(n_genes, n_chr21_genes, n_mito_genes, tuple(panel_symbols))
    mito_columns = np.flatnonzero(
        var["feature_name"].astype(str).str.upper().str.startswith("MT-").to_numpy()
    )

    # Donor covariates are drawn independently of the label. A covariate-only
    # baseline that scores well on this fixture is reporting a leak.
    def donor_attribute(values: tuple[str, ...]) -> np.ndarray:
        assigned = np.asarray(values, dtype=object)[rng.integers(0, len(values), size=n_donors)]
        return assigned[donor_index]

    obs = pd.DataFrame(
        {
            "donor_id": pd.Categorical(cell_donor.astype(str)),
            "disease": pd.Categorical(cell_condition.astype(str)),
            "group": pd.Categorical(np.where(cell_labels == 1, "DS", "CON")),
            "nFeature_RNA": np.asarray((counts > 0).sum(axis=1), dtype=np.int64),
            "nCount_RNA": np.asarray(counts.sum(axis=1), dtype=np.int64),
            "percent.mt": 100.0
            * np.asarray(counts[:, mito_columns].sum(axis=1), dtype=np.float64)
            / totals.ravel(),
            "nCount_ATAC": rng.integers(800, 40_000, size=n_cells),
            "nFeature_ATAC": rng.integers(500, 20_000, size=n_cells),
            "nucleosome_signal": rng.uniform(0.3, 1.6, size=n_cells),
            "TSS.enrichment": rng.uniform(1.5, 8.0, size=n_cells),
            "stage": pd.Categorical(donor_attribute(STAGES)),
            "sex": pd.Categorical(donor_attribute(("male", "female"))),
            "library": pd.Categorical(donor_attribute(LIBRARIES)),
            "batch_seq": pd.Categorical(donor_attribute(BATCHES)),
            "tissue_quality": pd.Categorical(["ok"] * n_cells),
            "dev_PCW": rng.integers(11, 21, size=n_donors)[donor_index].astype(np.int64),
            "cell_type": pd.Categorical(
                np.asarray(["state_a", "state_b", "state_c"], dtype=object)[np.arange(n_cells) % 3]
            ),
        },
        index=[f"syncell_{index:07d}" for index in range(n_cells)],
    )

    adata = anndata.AnnData(X=normalized, obs=obs, var=var)
    adata.raw = anndata.AnnData(X=raw, obs=obs, var=var)
    adata.uns["schema_version"] = "synthetic"
    adata.uns["title"] = "Synthetic cohort-shaped wiring fixture (not real data)"
    adata.uns["data_mode"] = SYNTHETIC_MARKER
    adata.write_h5ad(target)

    return {
        "generator": "p22.testing.cohort_fixture.write_synthetic_cohort_h5ad",
        "data_mode": SYNTHETIC_MARKER,
        "path": str(target),
        "seed": int(seed),
        "n_cells": int(n_cells),
        "n_donors": int(n_donors),
        "n_genes": int(n_genes),
        "n_chr21_genes": int(n_chr21_genes),
        "n_mito_genes": int(mito_columns.size),
        "cells_per_donor": int(cells_per_donor),
        "dosage_effect": float(dosage_effect),
        "donor_dosage_noise": float(donor_dosage_noise),
        "bytes": int(target.stat().st_size),
        "claim_boundary": "synthetic wiring only; never evidence about any condition",
    }
