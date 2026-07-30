"""Tests for the cohort-shaped synthetic H5AD used by simulation mode."""

from __future__ import annotations

import numpy as np
import pytest

from p22.data.real_cohort import (
    audit_schema,
    chr21_mapping_from_var,
    derive_cell_qc,
    donor_pseudobulk,
    read_var,
    run_cohort_qc,
)
from p22.testing.cohort_fixture import SYNTHETIC_MARKER, write_synthetic_cohort_h5ad


@pytest.fixture(scope="module")
def fixture_path(tmp_path_factory: pytest.TempPathFactory):
    pytest.importorskip("anndata")
    target = tmp_path_factory.mktemp("cohort_fixture") / "synthetic.h5ad"
    record = write_synthetic_cohort_h5ad(target, cells_per_donor=70, n_genes=600, n_chr21_genes=250)
    return target, record


def test_record_declares_itself_synthetic(fixture_path):
    _target, record = fixture_path
    assert record["data_mode"] == SYNTHETIC_MARKER
    assert "never evidence" in record["claim_boundary"]
    assert record["n_donors"] == 30
    assert record["n_mito_genes"] == 13


def test_fixture_matches_the_real_schema_contract(fixture_path):
    target, _record = fixture_path
    audit = audit_schema(target)
    assert audit.fields["donor"] == "donor_id"
    assert audit.fields["condition"] == "disease"
    assert audit.count_semantics["raw_is_integer"] is True
    assert audit.count_semantics["n_genes_matches_obs"] is True
    assert audit.atac["peak_block_present"] is False
    assert audit.chr21 is not None and audit.chr21.usable
    assert audit.qc_fields["pct_mito"]["derivable_from_counts"] is True


def test_fixture_passes_cohort_qc_with_frozen_thresholds(fixture_path):
    target, record = fixture_path
    report = run_cohort_qc(target, derived=derive_cell_qc(target, chunk_rows=500))
    assert report.status == "PASS", report.stop_reasons
    assert report.n_cells_pre_qc == record["n_cells"]
    assert report.n_donors_post_qc == 30
    assert report.suffix_audit["agrees"] is True


def test_dosage_groups_overlap_so_a_perfect_score_means_a_leak(fixture_path):
    target, _record = fixture_path
    report = run_cohort_qc(target)
    mapping = chr21_mapping_from_var(read_var(target))
    pseudobulk = donor_pseudobulk(
        target, report.obs, report.keep_mask, chr21_mapping=mapping, chunk_rows=500
    )
    assert pseudobulk.chr21_fraction is not None
    ds = pseudobulk.chr21_fraction[pseudobulk.labels == 1]
    control = pseudobulk.chr21_fraction[pseudobulk.labels == 0]
    assert ds.mean() > control.mean()
    assert control.max() > ds.min(), "synthetic groups must overlap"
    assert np.isfinite(pseudobulk.log_cpm()).all()
