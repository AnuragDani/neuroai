"""Tests for the NN v2 data module and fold preprocessing (N2).

The synthetic fixture builds an ``NNInputs`` directly, so the leakage contract
(HVG choice, scalers and ATAC IDF fit on training rows only) and the chr21
exclusion are proven without the real H5AD. The real smoke run is a separate
script; this file stays fast.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse

from p22.data.nn_inputs import (
    FoldArrays,
    NNInputs,
    prepare_nn_fold,
    region_indices,
)

GENES_CHR1 = ("ENSG0", "ENSG1", "ENSG2")
GENE_CHR21 = "ENSG3"
REGIONS_CHR1 = ("chr1:100-200", "chr2:100-200", "chr1:300-400")
REGION_CHR21 = "chr21:100-200"


def _metadata(n_cells: int, donors: list[str]) -> pd.DataFrame:
    diseases = ["complete trisomy 21" if d in ("d0", "d2") else "other" for d in donors]
    return pd.DataFrame(
        {
            "donor_id": donors,
            "disease": diseases,
            "author_cell_type": ["A", "B"] * (n_cells // 2),
            "cell_class": ["C"] * n_cells,
            "library": ["L1", "L2"] * (n_cells // 2),
            "batch_seq": ["b1"] * n_cells,
            "sex": ["M"] * n_cells,
            "dev_PCW": [10.0] * n_cells,
            "nCount_RNA": [100.0 + i for i in range(n_cells)],
            "nCount_ATAC": [50.0 + i for i in range(n_cells)],
            "TSS.enrichment": [1.5] * n_cells,
            "percent.mt": [0.1] * n_cells,
            "nucleosome_signal": [0.5] * n_cells,
        },
        index=[f"cell{i}" for i in range(n_cells)],
    )


def make_inputs(*, with_chr21: bool = False, holdout_boost: bool = False) -> NNInputs:
    n_cells = 8
    donors = ["d0", "d0", "d1", "d1", "d2", "d2", "d3", "d3"]
    metadata = _metadata(n_cells, donors)

    gene_ids = list(GENES_CHR1) + ([GENE_CHR21] if with_chr21 else [])
    n_genes = len(gene_ids)
    rng = np.random.default_rng(7)
    rna = sparse.csr_matrix(rng.integers(0, 4, size=(n_cells, n_genes)).astype(np.float32))
    if holdout_boost:
        rna = rna.tolil()
        rna[4:, 0] = 500  # holdout-only signal
        rna = rna.tocsr()
    rna_totals = np.asarray(rna.sum(axis=1)).ravel() + 5.0

    regions = list(REGIONS_CHR1) + ([REGION_CHR21] if with_chr21 else [])
    n_regions = len(regions)
    atac = sparse.csr_matrix(rng.integers(0, 3, size=(n_cells, n_regions)).astype(np.float32))
    if holdout_boost:
        atac = atac.tolil()
        atac[4:, 0] = 99
        atac = atac.tocsr()

    gene_chrom = np.asarray(
        ["chr1", "chr1", "chr1"] + (["chr21"] if with_chr21 else []), dtype=object
    )
    region_chrom = np.asarray(
        ["chr1", "chr2", "chr1"] + (["chr21"] if with_chr21 else []), dtype=object
    )
    return NNInputs(
        metadata=metadata,
        rna=rna,
        rna_totals=rna_totals,
        gene_ids=np.asarray(gene_ids, dtype=object),
        gene_names=np.asarray(gene_ids, dtype=object),
        gene_chrom=gene_chrom,
        gene_start=np.arange(n_genes, dtype=np.int64),
        gene_end=np.arange(n_genes, dtype=np.int64) + 100,
        atac=atac,
        regions=tuple(regions),
        region_index={region: i for i, region in enumerate(regions)},
        region_chrom=region_chrom,
    )


def _prepare(inputs: NNInputs, *, exclude_chr21: bool = False) -> FoldArrays:
    return prepare_nn_fold(
        inputs,
        train_rows=np.arange(0, 4),
        holdout_rows=np.arange(4, 8),
        region_rows=np.arange(len(inputs.regions)),
        n_hvg=10,
        exclude_chr21=exclude_chr21,
    )


def test_holdout_values_do_not_change_fit() -> None:
    baseline = _prepare(make_inputs())
    perturbed = _prepare(make_inputs(holdout_boost=True))
    assert np.array_equal(baseline.gene_ids, perturbed.gene_ids)
    assert baseline.evidence["idf_sha256"] == perturbed.evidence["idf_sha256"]
    np.testing.assert_allclose(
        baseline.rna[baseline.train_position], perturbed.rna[perturbed.train_position]
    )
    np.testing.assert_allclose(
        baseline.atac[baseline.train_position], perturbed.atac[perturbed.train_position]
    )
    assert not np.allclose(
        baseline.rna[~baseline.train_position], perturbed.rna[~perturbed.train_position]
    )


def test_exclude_chr21_drops_all_chr21_features() -> None:
    inputs = make_inputs(with_chr21=True)
    kept = _prepare(inputs, exclude_chr21=False)
    excluded = _prepare(inputs, exclude_chr21=True)
    assert any(region.startswith("chr21:") for region in kept.region_ids)
    assert not any(region.startswith("chr21:") for region in excluded.region_ids)
    for gene in excluded.gene_ids:
        assert inputs.gene_chrom[inputs.gene_ids == gene][0] != "chr21"
    assert excluded.evidence["n_regions"] == len(REGIONS_CHR1)
    assert excluded.evidence["exclude_chr21"] is True


def test_region_indices_maps_fold_ids() -> None:
    inputs = make_inputs(with_chr21=True)
    indices = region_indices(inputs, [REGION_CHR21, REGIONS_CHR1[0]])
    assert indices.tolist() == [inputs.region_index[REGION_CHR21], 0]


def test_train_holdout_donor_overlap_is_refused() -> None:
    inputs = make_inputs()
    try:
        prepare_nn_fold(
            inputs,
            train_rows=np.arange(0, 5),  # includes d2 which is also holdout
            holdout_rows=np.arange(4, 8),
            region_rows=np.arange(len(inputs.regions)),
            n_hvg=10,
        )
    except ValueError as error:
        assert "donor" in str(error)
    else:  # pragma: no cover - the guard must fire
        raise AssertionError("donor overlap was not refused")
