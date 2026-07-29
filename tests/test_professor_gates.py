"""Tests for adequacy, resources, estimand, group splits, baselines, validation, package."""

from pathlib import Path

import numpy as np

from p22.data.adequacy import (
    OFF_RAMPS,
    catalog_donor_frame,
    evaluate_donor_adequacy,
)
from p22.data.group_splits import (
    aggregate_donor_probabilities,
    build_repeated_group_split_report,
)
from p22.data.resources import build_resource_report, decide_atac_branch
from p22.eval.estimand import freeze_estimand, practical_margin, score_resolution
from p22.eval.validation import build_validation_report
from p22.models.named_baselines import (
    BASELINE_ORDER,
    baseline_table,
    majority_class_baseline,
    pseudobulk_rna_logistic,
)
from p22.reports.evidence_package import EvidencePackage, package_is_complete


def test_practical_margin_for_fifteen_donors_is_at_least_0_07():
    assert score_resolution(15, 15) == 1 / 30
    assert practical_margin(15, 15) == 0.07


def test_catalog_donor_adequacy_inconclusive_without_cells():
    donors = [f"A_CON_{i:02d}" for i in range(15)] + [f"A_DS_{i:02d}" for i in range(15)]
    frame = catalog_donor_frame(donors)
    report = evaluate_donor_adequacy(frame, pairing_known=False)
    assert report.status == "INCONCLUSIVE"
    assert report.checks["n_control_donors"] == 15
    assert report.checks["n_ds_donors"] == 15
    assert "O2" in OFF_RAMPS


def test_atac_branches():
    b1 = decide_atac_branch(True, True)
    assert b1.branch == "B1"
    assert b1.multimodal_claim_allowed
    b2b = decide_atac_branch(False, True, fragment_build_approved=False)
    assert b2b.branch == "B2b"
    assert not b2b.multimodal_claim_allowed
    unknown = decide_atac_branch(None, True)
    assert unknown.branch == "unknown"


def test_resource_report_blocked_without_approval():
    report = build_resource_report(
        atac_branch=decide_atac_branch(None, True),
        h5ad_available=False,
        approval_present=False,
    )
    assert report.status == "BLOCKED"


def test_freeze_estimand_margin_and_validation_plan():
    report = freeze_estimand(15, 15)
    assert report.status == "PASS"
    assert report.estimand.margin == 0.07
    assert report.estimand.validation_rna_accession == "GSE280175"
    assert report.estimand.to_dict()["validation_plan"]["rna_only_not_multimodal"] is True


def test_repeated_group_folds_have_zero_donor_overlap():
    donors = np.repeat([f"d{i:02d}" for i in range(20)], 4)
    labels = np.repeat([0, 1] * 10, 4)
    report = build_repeated_group_split_report(donors, labels, n_repeats=2, n_folds=5)
    assert report.status == "PASS"
    assert report.donor_overlap_count == 0
    assert len(report.folds) == 10


def test_aggregate_donor_probabilities_uses_mean_and_threshold():
    probs = np.array([0.2, 0.8, 0.9, 0.1])
    donors = np.array(["a", "a", "b", "b"])
    frame = aggregate_donor_probabilities(probs, donors, threshold=0.5)
    assert float(frame.loc[frame.donor_id == "a", "probability"].iloc[0]) == 0.5
    assert int(frame.loc[frame.donor_id == "a", "prediction"].iloc[0]) == 1


def test_named_baselines_and_table_order():
    rng = np.random.default_rng(0)
    donors = np.repeat([f"d{i:02d}" for i in range(12)], 5)
    labels = np.repeat([0, 1] * 6, 5)
    rna = rng.normal(size=(donors.size, 16))
    rna[:, 0] += labels * 1.5
    train = [f"d{i:02d}" for i in range(0, 8)]
    test = [f"d{i:02d}" for i in range(8, 12)]
    majority = majority_class_baseline(labels, donors)
    pseudo = pseudobulk_rna_logistic(rna, labels, donors, train, test, n_features=8)
    rows = baseline_table([majority, pseudo])
    assert [row["name"] for row in rows] == list(BASELINE_ORDER)
    assert majority.donor_balanced_accuracy is not None
    assert pseudo.status == "measured"


def test_validation_blocked_without_approval_and_marker_set():
    report = build_validation_report(
        marker_set=None,
        findings_available=False,
        approval_present=False,
    )
    assert report.status == "BLOCKED"
    assert report.resources[0].accession == "GSE280175"
    assert "not independent multimodal" in report.claim_boundary


def test_evidence_package_writes_required_files(tmp_path: Path):
    package = EvidencePackage(
        run_dir=tmp_path / "run",
        manifest={"gates": {"G0": "PASS"}},
        metrics_rows=[{"model": "majority_class", "status": "measured"}],
        intervention_rows=[{"intervention": "ablate_view_a", "status": "blocked"}],
        validation_rows=[{"accession": "GSE280175", "status": "BLOCKED"}],
    )
    paths = package.write()
    ok, missing = package_is_complete(paths["run_dir"])
    assert ok
    assert missing == []
    assert Path(paths["manifest"]).is_file()
