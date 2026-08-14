"""Tests for the real-cohort schema audit, QC accounting, and donor census.

A small synthetic H5AD stands in for the public file so the contract is testable
without a 1.57 GB download. The synthetic matrix proves wiring only.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from p22.data.real_cohort import (
    CHR21_LABELS,
    CONTROL_CONDITION,
    POSITIVE_CONDITION,
    QcThresholds,
    audit_donor_suffix,
    audit_schema,
    chr21_mapping_from_var,
    covariate_frame,
    derive_cell_qc,
    donor_pseudobulk,
    load_cell_matrix,
    mito_gene_mask,
    run_cohort_qc,
    sample_capped_cells,
    sample_nested_capped_cells,
)

N_DONORS_PER_CLASS = 15
CELLS_PER_DONOR = 70
N_GENES = 1200
N_CHR21_GENES = 300
N_MITO_GENES = 13


def _var_frame(n_genes: int, n_chr21: int, n_mito: int = 0) -> pd.DataFrame:
    ids = [f"ENSG{index:011d}" for index in range(n_genes)]
    chromosomes = ["chr21"] * min(n_chr21, n_genes) + ["chr1"] * max(n_genes - n_chr21, 0)
    symbols = [f"GENE{index}" for index in range(n_genes)]
    for offset in range(min(n_mito, n_genes - n_chr21)):
        symbols[n_genes - 1 - offset] = f"MT-ND{offset + 1}"
    return pd.DataFrame(
        {
            "gene_name": symbols,
            "assay": pd.Categorical(["Gene Expression"] * n_genes),
            "seqnames": pd.Categorical(chromosomes[:n_genes]),
            "feature_is_filtered": np.zeros(n_genes, dtype=bool),
        },
        index=ids,
    )


@pytest.fixture(scope="module")
def fixture_h5ad(tmp_path_factory: pytest.TempPathFactory) -> Path:
    anndata = pytest.importorskip("anndata")
    from scipy import sparse

    rng = np.random.default_rng(0)
    donors: list[str] = []
    conditions: list[str] = []
    for index in range(N_DONORS_PER_CLASS):
        donors.extend([f"PCW12_CON_{index:05d}"] * CELLS_PER_DONOR)
        conditions.extend([CONTROL_CONDITION] * CELLS_PER_DONOR)
    for index in range(N_DONORS_PER_CLASS):
        donors.extend([f"PCW12_DS_{index:05d}"] * CELLS_PER_DONOR)
        conditions.extend([POSITIVE_CONDITION] * CELLS_PER_DONOR)

    n_cells = len(donors)
    labels = np.array([1 if value == POSITIVE_CONDITION else 0 for value in conditions])
    counts = rng.poisson(3.0, size=(n_cells, N_GENES)).astype(np.float32)
    # Give chr21 genes a dosage lift so the positive control has something to find.
    counts[:, :N_CHR21_GENES] += (labels[:, None] * 2).astype(np.float32)
    raw = sparse.csr_matrix(counts)
    normalized = sparse.csr_matrix(np.log1p(counts / counts.sum(axis=1, keepdims=True) * 1e4))

    obs = pd.DataFrame(
        {
            "donor_id": pd.Categorical(donors),
            "disease": pd.Categorical(conditions),
            "nFeature_RNA": np.asarray((counts > 0).sum(axis=1), dtype=np.int64),
            "nCount_RNA": np.asarray(counts.sum(axis=1), dtype=np.int64),
            "percent.mt": rng.uniform(0.0, 1.0, size=n_cells),
            "nCount_ATAC": rng.integers(500, 5000, size=n_cells),
            "nFeature_ATAC": rng.integers(300, 3000, size=n_cells),
            "nucleosome_signal": rng.uniform(0.5, 1.5, size=n_cells),
            "TSS.enrichment": rng.uniform(2.0, 5.0, size=n_cells),
            "stage": pd.Categorical(["PCW11_12"] * n_cells),
            "sex": pd.Categorical(rng.choice(["male", "female"], size=n_cells)),
            "library": pd.Categorical(rng.choice(["L1", "L2"], size=n_cells)),
            "batch_seq": pd.Categorical(rng.choice(["E16", "E18"], size=n_cells)),
            "dev_PCW": np.full(n_cells, 12, dtype=np.int64),
        },
        index=[f"cell{index}" for index in range(n_cells)],
    )
    var = _var_frame(N_GENES, N_CHR21_GENES, N_MITO_GENES)
    adata = anndata.AnnData(X=normalized, obs=obs, var=var)
    adata.raw = anndata.AnnData(X=raw, obs=obs, var=var)
    adata.uns["schema_version"] = "7.1.0"
    path = tmp_path_factory.mktemp("real_cohort") / "fixture.h5ad"
    adata.write_h5ad(path)
    return path


def test_chr21_mapping_verified_and_hashed():
    var = _var_frame(1000, 500)
    mapping = chr21_mapping_from_var(var)
    assert mapping.usable
    assert mapping.n_chr21_genes == 500
    assert mapping.chromosome_column == "seqnames"
    assert mapping.mapping_sha256 and len(mapping.mapping_sha256) == 64
    assert "chr21" in CHR21_LABELS


def test_chr21_mapping_not_applicable_without_chromosome_column():
    var = pd.DataFrame({"gene_name": ["A", "B"]}, index=["ENSG00000000001", "ENSG00000000002"])
    mapping = chr21_mapping_from_var(var)
    assert mapping.status == "not_applicable"
    assert mapping.reason and "chromosome column" in mapping.reason


def test_chr21_mapping_not_applicable_for_non_ensembl_ids():
    var = pd.DataFrame({"seqnames": ["chr21", "chr1"]}, index=["SYMBOL_A", "SYMBOL_B"])
    mapping = chr21_mapping_from_var(var)
    assert mapping.status == "not_applicable"
    assert mapping.id_scheme == "unverified"


def test_chr21_mapping_rejects_implausible_gene_count():
    var = _var_frame(50, 5)
    mapping = chr21_mapping_from_var(var)
    assert mapping.status == "not_applicable"
    assert mapping.reason and "plausible range" in mapping.reason


def test_donor_suffix_audit_flags_disagreement():
    agree = audit_donor_suffix(
        pd.Series(["A_DS_1", "B_CON_2"]),
        pd.Series([POSITIVE_CONDITION, CONTROL_CONDITION]),
    )
    assert agree["agrees"] is True
    assert agree["n_donors_with_suffix"] == 2

    disagree = audit_donor_suffix(
        pd.Series(["A_DS_1"]),
        pd.Series([CONTROL_CONDITION]),
    )
    assert disagree["agrees"] is False
    assert "suffix says DS" in disagree["problems"][0]


def test_schema_audit_reports_absent_peak_block(fixture_h5ad: Path):
    audit = audit_schema(fixture_h5ad)
    assert audit.status in {"PASS", "INCONCLUSIVE"}
    assert audit.fields["donor"] == "donor_id"
    assert audit.fields["condition"] == "disease"
    assert audit.atac["peak_block_present"] is False
    assert audit.chr21 is not None and audit.chr21.usable
    assert audit.count_semantics["raw_layer_present"] is True
    assert audit.count_semantics["raw_is_integer"] is True
    assert audit.count_semantics["n_genes_matches_obs"] is True
    assert audit.count_semantics["total_counts_matches_obs"] is True
    assert audit.genome_build["gene_id_scheme"] == "ensembl_gene_id"
    assert any(row["column"] == "percent.mt" for row in audit.missingness)


def test_cohort_qc_produces_pre_and_post_tables(fixture_h5ad: Path):
    report = run_cohort_qc(fixture_h5ad)
    assert report.status == "PASS", report.stop_reasons
    assert report.n_cells_pre_qc == 2 * N_DONORS_PER_CLASS * CELLS_PER_DONOR
    assert report.n_donors_post_qc == 2 * N_DONORS_PER_CLASS
    assert report.condition_donors_post_qc[POSITIVE_CONDITION] == N_DONORS_PER_CLASS
    assert report.condition_donors_post_qc[CONTROL_CONDITION] == N_DONORS_PER_CLASS
    assert len(report.donor_table_pre_qc) == 2 * N_DONORS_PER_CLASS
    assert len(report.donor_table_post_qc) == 2 * N_DONORS_PER_CLASS
    assert {row["rule"] for row in report.exclusions} >= {"min_genes", "max_pct_mito"}
    assert report.thresholds["frozen_before_filtering"] is True
    assert report.suffix_audit["agrees"] is True


def test_mito_mask_uses_symbols_when_no_mito_contig_exists():
    mask, detail = mito_gene_mask(_var_frame(N_GENES, N_CHR21_GENES, N_MITO_GENES))
    assert int(mask.sum()) == N_MITO_GENES
    assert "MT-" in detail["source"]


def test_mito_mask_refuses_an_implausible_symbol_match():
    var = _var_frame(200, 20)
    var["gene_name"] = [f"MT-{index}" for index in range(200)]
    mask, detail = mito_gene_mask(var)
    assert not mask.any()
    assert "outside the plausible mitochondrial range" in detail["rejected"]


def test_derived_qc_matches_the_count_matrix(fixture_h5ad: Path):
    derived = derive_cell_qc(fixture_h5ad, chunk_rows=137)
    assert derived.n_genes.size == 2 * N_DONORS_PER_CLASS * CELLS_PER_DONOR
    assert derived.total_counts.min() > 0
    assert derived.pct_mito is not None
    assert derived.mito_detail["n_genes"] == N_MITO_GENES
    assert 0.0 < float(np.median(derived.pct_mito)) < 10.0


def test_derived_qc_reports_agreement_with_author_columns(fixture_h5ad: Path):
    report = run_cohort_qc(fixture_h5ad)
    derived = derive_cell_qc(fixture_h5ad, obs=report.obs, chunk_rows=500)
    assert derived.agreement["n_genes"]["identical"] is True
    assert derived.agreement["total_counts"]["identical"] is True
    # percent.mt in the fixture is arbitrary, so the derived value must disagree.
    assert derived.agreement["pct_mito"]["identical"] is False


def test_cohort_qc_filters_on_derived_values_when_supplied(fixture_h5ad: Path):
    derived = derive_cell_qc(fixture_h5ad, chunk_rows=1000)
    report = run_cohort_qc(fixture_h5ad, derived=derived)
    assert report.status == "PASS", report.stop_reasons
    assert report.qc_sources["n_genes"] == "derived:n_genes"
    assert report.qc_sources["pct_mito"] == "derived:pct_mito"
    assert report.derived_qc["pct_mito_available"] is True
    assert any("median_derived_pct_mito" in row for row in report.donor_table_post_qc)


def test_cohort_qc_stops_when_threshold_makes_donors_too_thin(fixture_h5ad: Path):
    strict = QcThresholds(min_total_counts=10**9)
    report = run_cohort_qc(fixture_h5ad, strict)
    assert report.status == "BLOCKED"
    assert report.n_cells_post_qc == 0
    assert report.stop_reasons


def test_donor_pseudobulk_uses_all_retained_cells(fixture_h5ad: Path):
    report = run_cohort_qc(fixture_h5ad)
    mapping = chr21_mapping_from_var(_var_frame(N_GENES, N_CHR21_GENES))
    pseudobulk = donor_pseudobulk(
        fixture_h5ad,
        report.obs,
        report.keep_mask,
        chr21_mapping=mapping,
        chunk_rows=137,
    )
    assert len(pseudobulk.donor_ids) == 2 * N_DONORS_PER_CLASS
    assert int(pseudobulk.n_cells.sum()) == report.n_cells_post_qc
    assert pseudobulk.labels.sum() == N_DONORS_PER_CLASS
    assert pseudobulk.log_cpm().shape == (2 * N_DONORS_PER_CLASS, N_GENES)
    assert pseudobulk.chr21_fraction is not None
    ds = pseudobulk.chr21_fraction[pseudobulk.labels == 1].mean()
    control = pseudobulk.chr21_fraction[pseudobulk.labels == 0].mean()
    assert ds > control


def test_capped_sampling_is_deterministic_and_per_donor(fixture_h5ad: Path):
    report = run_cohort_qc(fixture_h5ad)
    first = sample_capped_cells(report.obs, report.keep_mask, cap=5, seed=0)
    second = sample_capped_cells(report.obs, report.keep_mask, cap=5, seed=0)
    assert np.array_equal(first, second)
    assert first.size == 2 * N_DONORS_PER_CLASS * 5
    donors = report.obs["donor_id"].astype(str).to_numpy()[first]
    assert set(pd.Series(donors).value_counts().unique()) == {5}


def test_nested_capped_sampling_reuses_one_donor_ordering(fixture_h5ad: Path):
    report = run_cohort_qc(fixture_h5ad)
    caps = (5, 11, 23)

    first = sample_nested_capped_cells(report.obs, report.keep_mask, caps=caps, seed=7)
    second = sample_nested_capped_cells(report.obs, report.keep_mask, caps=caps, seed=7)

    assert set(first) == set(caps)
    for cap in caps:
        assert np.array_equal(first[cap], second[cap])
        donors = report.obs["donor_id"].astype(str).to_numpy()[first[cap]]
        assert set(pd.Series(donors).value_counts().unique()) == {cap}
    assert set(first[5]).issubset(first[11])
    assert set(first[11]).issubset(first[23])


def test_load_cell_matrix_returns_requested_rows(fixture_h5ad: Path):
    report = run_cohort_qc(fixture_h5ad)
    rows = sample_capped_cells(report.obs, report.keep_mask, cap=3, seed=1)
    matrix = load_cell_matrix(fixture_h5ad, rows)
    assert matrix.shape == (rows.size, N_GENES)
    assert matrix.min() >= 0.0


def test_covariate_frame_only_uses_observed_columns(fixture_h5ad: Path):
    report = run_cohort_qc(fixture_h5ad)
    frame = covariate_frame(report.obs)
    assert "nCount_RNA" in frame.columns
    assert "percent.mt" in frame.columns
    assert any(name.startswith("batch_seq_") for name in frame.columns)
    assert not any(name.startswith("dataset_folder") for name in frame.columns)
