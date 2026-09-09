"""Real-path wiring on a small synthetic H5AD, never biological evidence."""

import anndata as ad
import numpy as np
import pandas as pd
import pytest

from p22.data.census import sha256_file
from p22.eval.external_validation import SHEETS
from p22.eval.real_pipeline import RealAnalysisState, run_external_rna_replication
from p22.reports.evidence_package import EvidencePackage
from p22.testing.cohort_fixture import write_synthetic_cohort_h5ad


@pytest.fixture(scope="module")
def inputs(tmp_path_factory):
    root = tmp_path_factory.mktemp("external_pipeline")
    path = root / "cohort.h5ad"
    write_synthetic_cohort_h5ad(
        path, n_donors_per_class=10, cells_per_donor=150, n_genes=600, n_chr21_genes=20
    )
    cohort = ad.read_h5ad(path)
    obs = cohort.obs
    donor_number = np.repeat(np.arange(20), 150)
    obs["dev_PCW"] = 13 + (donor_number // 2) % 6
    obs["sex"] = np.where((donor_number // 2) % 2, "female", "male")
    obs["author_cell_type"] = np.tile(
        ["RG"] * 50 + ["RG_prol"] * 25 + ["IPC_prol"] * 25 + ["IPC"] * 50, 20
    )
    cohort.write_h5ad(path)
    book = root / "effects.xlsx"
    rng = np.random.default_rng(7)
    with pd.ExcelWriter(book, engine="openpyxl") as writer:
        for sheet, celltype in SHEETS.items():
            effects = rng.normal(size=600)
            effects[:20] = 0.5
            pd.DataFrame(
                {
                    "gene": cohort.var.gene_name.to_numpy(),
                    "avg_log2FC": effects,
                    "p_val": 0.1,
                    "p_val_adj": 0.2,
                    "pct.1": 0.8,
                    "pct.2": 0.8,
                    "celltype": celltype,
                    "FDR": 0.2,
                    "sig": False,
                }
            ).to_excel(writer, sheet_name=sheet, index=False)
    return path, book, obs.copy()


def test_replication_extends_alias_and_preserves_g8(inputs, tmp_path):
    path, book, obs = inputs
    state = RealAnalysisState(
        obs=obs,
        keep_mask=np.ones(len(obs), dtype=bool),
        qc={"status": "PASS", "data_mode": "synthetic_wiring_fixture"},
        validation={"status": "INCONCLUSIVE"},
        validation_rows=[{"analysis": "existing"}],
    )
    alias = state.validation_rows
    result = run_external_rna_replication(
        path,
        book,
        state=state,
        approval_present=True,
        expected_sha256=sha256_file(book),
        n_bootstrap=40,
        n_permutations=40,
    )
    assert result["execution_status"] == "completed", result["rows"]
    assert alias is state.validation_rows and len(alias) == 5
    assert state.validation["status"] == "INCONCLUSIVE"
    assert state.validation["processed_rna_summary"]["execution_status"] == "completed"
    assert state.validation["processed_rna_summary"]["external_sha256"] == sha256_file(book)
    assert result["external_matrix_ingested"] is False
    assert len(result["gene_tables"]) == 4
    assert {row["n_ds_donors"] for row in result["rows"]} == {10}
    assert {row["n_control_donors"] for row in result["rows"]} == {10}
    assert {row["primary_cells"] for row in result["rows"]} == {1000}
    paths = EvidencePackage(run_dir=tmp_path, validation_rows=alias).write()
    written = pd.read_csv(paths["validation"])
    assert len(written) == 5
    assert written.external_sha256.dropna().eq(sha256_file(book)).all()


def test_approval_and_source_failures_are_not_scientific_outcomes(inputs):
    path, book, obs = inputs
    state = RealAnalysisState(obs=obs, keep_mask=np.ones(len(obs), dtype=bool))
    denied = run_external_rna_replication("absent.h5ad", "absent.xlsx", state=state)
    assert denied["execution_status"] == "failed"
    assert "approval" in denied["rows"][0]["reason"]
    bad_hash = run_external_rna_replication(path, book, state=state, approval_present=True)
    assert len(bad_hash["rows"]) == 4
    assert {row["scientific_outcome"] for row in bad_hash["rows"]} == {"not_evaluated"}
    assert "hash" in bad_hash["rows"][0]["reason"]
    no_qc = run_external_rna_replication(
        path, book, state=state, approval_present=True, expected_sha256=sha256_file(book)
    )
    assert no_qc["execution_status"] == "failed"
    assert "QC" in no_qc["rows"][0]["reason"]
