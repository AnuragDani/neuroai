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
    DEFAULT_RNA_MATRIX_KEY,
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
    read_matrix_axis,
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


@pytest.fixture
def divergent_axis_h5ad(tmp_path: Path) -> dict[str, object]:
    """A fixture whose ``X`` and ``raw/X`` differ in values *and* gene order.

    Processed ``X`` is noninteger and follows ``var``. Raw counts are integers and
    follow a reordered ``raw/var`` with a different identifier scheme, so a loader
    that defaults to ``X`` or attaches processed labels to raw columns cannot pass
    unnoticed.
    """
    anndata = pytest.importorskip("anndata")
    from scipy import sparse

    rng = np.random.default_rng(7)
    n_cells, n_genes = 8, 6
    raw_counts = rng.poisson(4.0, size=(n_cells, n_genes)).astype(np.float32)
    processed = (rng.random((n_cells, n_genes)) + 0.25).astype(np.float32)
    var = _var_frame(n_genes, 0)
    raw_order = np.array([4, 1, 5, 0, 3, 2])
    raw_var = var.iloc[raw_order].copy()
    raw_var.index = [f"RAW{index:011d}" for index in range(n_genes)]
    obs = pd.DataFrame(
        {
            "donor_id": pd.Categorical(["d0"] * n_cells),
            "disease": pd.Categorical([CONTROL_CONDITION] * n_cells),
        },
        index=[f"cell{index}" for index in range(n_cells)],
    )
    adata = anndata.AnnData(X=sparse.csr_matrix(processed), obs=obs, var=var)
    adata.raw = anndata.AnnData(
        X=sparse.csr_matrix(raw_counts[:, raw_order]), obs=obs, var=raw_var
    )
    path = tmp_path / "divergent.h5ad"
    adata.write_h5ad(path)
    return {
        "path": path,
        "raw": raw_counts[:, raw_order],
        "processed": processed,
        "raw_var": list(raw_var.index),
        "var": list(var.index),
        "n_cells": n_cells,
    }


def test_default_rna_matrix_is_raw_counts(divergent_axis_h5ad: dict[str, object]):
    path = divergent_axis_h5ad["path"]
    matrix = load_cell_matrix(path, np.arange(divergent_axis_h5ad["n_cells"]))
    assert DEFAULT_RNA_MATRIX_KEY == "raw/X"
    assert np.all(matrix.data == np.floor(matrix.data))
    assert np.allclose(matrix.toarray(), divergent_axis_h5ad["raw"])


def test_wrong_default_processed_block_cannot_pass_as_raw(divergent_axis_h5ad: dict[str, object]):
    path = divergent_axis_h5ad["path"]
    rows = np.arange(divergent_axis_h5ad["n_cells"])
    with pytest.raises(ValueError, match="non-integer"):
        load_cell_matrix(path, rows, matrix_key="X")
    explicit = load_cell_matrix(path, rows, matrix_key="X", validate_counts=False)
    assert np.allclose(explicit.toarray(), divergent_axis_h5ad["processed"])


def test_raw_matrix_columns_follow_raw_axis_not_processed_axis(
    divergent_axis_h5ad: dict[str, object],
):
    path = divergent_axis_h5ad["path"]
    raw_axis = read_matrix_axis(path, DEFAULT_RNA_MATRIX_KEY)
    assert raw_axis["axis_key"] == "raw/var"
    assert raw_axis["n_genes"] == len(divergent_axis_h5ad["raw_var"])
    assert raw_axis["gene_ids"] == divergent_axis_h5ad["raw_var"]
    processed_axis = read_matrix_axis(path, "X")
    assert processed_axis["axis_key"] == "var"
    assert processed_axis["gene_ids"] == divergent_axis_h5ad["var"]


def test_load_cell_matrix_rejects_negative_raw_counts(tmp_path: Path):
    anndata = pytest.importorskip("anndata")
    from scipy import sparse

    counts = np.array([[1.0, -2.0], [3.0, 4.0]], dtype=np.float32)
    obs = pd.DataFrame(
        {
            "donor_id": pd.Categorical(["d0", "d0"]),
            "disease": pd.Categorical([CONTROL_CONDITION] * 2),
        },
        index=["c0", "c1"],
    )
    var = _var_frame(2, 0)
    adata = anndata.AnnData(X=sparse.csr_matrix(counts), obs=obs, var=var)
    adata.raw = anndata.AnnData(X=sparse.csr_matrix(counts), obs=obs, var=var)
    path = tmp_path / "negative.h5ad"
    adata.write_h5ad(path)
    with pytest.raises(ValueError, match="negative"):
        load_cell_matrix(path, np.arange(2))


def test_load_cell_matrix_refuses_missing_raw_block(tmp_path: Path):
    anndata = pytest.importorskip("anndata")
    from scipy import sparse

    counts = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    obs = pd.DataFrame(
        {
            "donor_id": pd.Categorical(["d0", "d0"]),
            "disease": pd.Categorical([CONTROL_CONDITION] * 2),
        },
        index=["c0", "c1"],
    )
    var = _var_frame(2, 0)
    adata = anndata.AnnData(X=sparse.csr_matrix(counts), obs=obs, var=var)
    path = tmp_path / "no_raw.h5ad"
    adata.write_h5ad(path)
    with pytest.raises(KeyError):
        load_cell_matrix(path, np.arange(2))


def _write_synthetic_h5ad(path: Path, gene_ids: list[str], *, n_cells: int = 2, n_genes=None):
    """Write a minimal CSR ``raw/X`` block plus a ``raw/var`` index dataset.

    ``n_genes`` lets a test declare a matrix wider than its identifier list so the
    mismatch path can be exercised without anndata rewriting the axis.
    """
    import h5py

    width = len(gene_ids) if n_genes is None else n_genes
    values = np.ones(n_cells, dtype=np.float32)
    indices = np.zeros(n_cells, dtype=np.int64)
    indptr = np.arange(n_cells + 1, dtype=np.int64)
    with h5py.File(path, "w") as handle:
        block = handle.create_group("raw/X")
        block.attrs["encoding-type"] = "csr_matrix"
        block.attrs["shape"] = np.array([n_cells, width], dtype=np.int64)
        block.create_dataset("data", data=values)
        block.create_dataset("indices", data=indices)
        block.create_dataset("indptr", data=indptr)
        var = handle.create_group("raw/var")
        var.attrs["_index"] = "_index"
        var.create_dataset("_index", data=gene_ids, dtype=h5py.string_dtype("utf-8"))
    return path


def test_read_matrix_axis_refuses_undeclared_matrix_key(tmp_path: Path):
    path = _write_synthetic_h5ad(tmp_path / "undeclared.h5ad", ["g0", "g1"])
    with pytest.raises(ValueError, match="no declared axis mapping"):
        read_matrix_axis(path, "layers/normalized")


def test_read_matrix_axis_refuses_absent_axis_block(tmp_path: Path):
    import h5py

    path = _write_synthetic_h5ad(tmp_path / "absent_axis.h5ad", ["g0", "g1"])
    with h5py.File(path, "a") as handle:
        del handle["raw/var"]
    with pytest.raises(KeyError, match="raw/var"):
        read_matrix_axis(path, "raw/X")


def test_read_matrix_axis_refuses_empty_identifiers(tmp_path: Path):
    path = _write_synthetic_h5ad(tmp_path / "empty_ids.h5ad", [], n_genes=2)
    with pytest.raises(ValueError, match="empty"):
        read_matrix_axis(path, "raw/X")


def test_read_matrix_axis_refuses_dimension_mismatch(tmp_path: Path):
    path = _write_synthetic_h5ad(tmp_path / "mismatch.h5ad", ["g0"], n_genes=2)
    with pytest.raises(ValueError, match="identifiers"):
        read_matrix_axis(path, "raw/X")


def test_read_matrix_axis_refuses_duplicate_identifiers(tmp_path: Path):
    path = _write_synthetic_h5ad(tmp_path / "dupes.h5ad", ["g0", "g0"])
    with pytest.raises(ValueError, match="duplicate"):
        read_matrix_axis(path, "raw/X")


def test_read_matrix_axis_refuses_missing_index_dataset(tmp_path: Path):
    import h5py

    path = _write_synthetic_h5ad(tmp_path / "no_index.h5ad", ["g0", "g1"])
    with h5py.File(path, "a") as handle:
        del handle["raw/var/_index"]
    with pytest.raises(KeyError, match="_index"):
        read_matrix_axis(path, "raw/X")
