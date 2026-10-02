"""M4 leakage/metric falsification: mixed-label metrics, target invariance."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from p22.eval.masked_atac_metrics import (
    assert_chromosome_mask_exclusivity,
    assert_existing_mil_refuses_mixed_labels,
    assert_no_forbidden_features,
    assert_prediction_reload_identity,
    assert_target_perturbation_leaves_inputs_unchanged,
    binary_presence_labels,
    build_toy_leakage_arrays,
    donor_average_cell_log_loss,
    feature_order_hash,
    hand_calculated_metric_example,
    oracle_and_constant_direction_check,
    refuse_donor_average_probability_as_primary,
    refuse_output_overwrite,
    run_falsification_suite,
    target_inclusive_panel_depth_leaks,
    visible_atac_tfidf_fit,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001"
    / "FALSIFICATION.json"
)
OUT_MD = OUT_JSON.with_name("FALSIFICATION.md")
M3_JSON = OUT_JSON.with_name("SPLITS_AND_SAMPLING.json")


def test_binary_labels_and_hand_calculated_donor_average() -> None:
    assert binary_presence_labels([0, 1, 3, 0]).tolist() == [0, 1, 1, 0]
    with pytest.raises(ValueError, match="non-negative"):
        binary_presence_labels([-1.0])
    ex = hand_calculated_metric_example()
    assert ex["cell_match"] is True
    assert ex["donor_average_match"] is True
    assert ex["n_cells_unequal"] is True
    assert ex["mixed_labels_in_donor_A"] is True
    wrong = refuse_donor_average_probability_as_primary(
        ex["donors"], ex["y"], ex["p"]
    )
    assert wrong["forbidden_as_primary"] is True
    assert wrong["values_differ"] is True
    direction = oracle_and_constant_direction_check()
    assert direction["oracle_better_than_constant"] is True
    assert direction["oracle_near_zero"] is True
    assert direction["constant_equals_ln2"] is True


def test_target_perturbation_invariant_and_inclusive_depth_leaks() -> None:
    toy = build_toy_leakage_arrays()
    inv = assert_target_perturbation_leaves_inputs_unchanged(
        rna=toy["rna"],
        atac_counts=toy["atac"],
        visible_indices=toy["visible_indices"],
        target_index=toy["target_index"],
        train_rows=toy["train_rows"],
    )
    assert inv["passed"] is True
    leak = target_inclusive_panel_depth_leaks(
        toy["atac"],
        toy["visible_indices"],
        toy["target_index"],
        toy["train_rows"],
    )
    assert leak["target_inclusive_depth_changes_visible_tf"] is True
    assert leak["correct_visible_only_invariant"] is True
    # Chromosome exclusivity
    assert_chromosome_mask_exclusivity(
        toy["region_chroms"], toy["visible_indices"], toy["target_chrom"]
    )
    with pytest.raises(ValueError, match="chromosome-mask leak"):
        assert_chromosome_mask_exclusivity(
            toy["region_chroms"], [0, 1, 2], toy["target_chrom"]
        )
    fit = visible_atac_tfidf_fit(
        toy["atac"], toy["visible_indices"], toy["train_rows"]
    )
    assert fit["n_visible"] == 3
    assert len(fit["idf_sha256"]) == 64


def test_mil_refusal_forbidden_features_guards() -> None:
    mil = assert_existing_mil_refuses_mixed_labels()
    assert mil["mixed_refused"] is True
    assert mil["uniform_accepted"] is True
    assert mil["adapter_required"] is True
    hits = assert_no_forbidden_features(
        ["rna_0", "disease", "nCount_ATAC", "visible_0", "donor_id"]
    )
    assert hits == ["disease", "donor_id", "nCount_ATAC"]
    assert assert_no_forbidden_features(["rna_0", "visible_0"]) == []
    fwd = feature_order_hash(["a", "b", "c"])
    rev = feature_order_hash(["c", "b", "a"])
    assert fwd != rev
    assert assert_prediction_reload_identity([0.2, 0.8], [0.2, 0.8])["passed"]
    assert not assert_prediction_reload_identity([0.2, 0.8], [0.2, 0.1])["passed"]
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        refuse_output_overwrite(Path(__file__))


def test_suite_and_live_report_contracts() -> None:
    suite = run_falsification_suite()
    assert suite["disposition"] == "FALSIFICATION_PASS"
    assert all(suite["checks"].values())
    # Unequal-cell donor-average sanity on fresh arrays
    donors = ["X", "X", "Y"]
    y = np.asarray([1, 0, 1])
    p = np.asarray([0.7, 0.4, 0.6])
    got = donor_average_cell_log_loss(donors, y, p)
    assert got["n_donors"] == 2
    assert got["per_donor_n_cells"] == {"X": 2, "Y": 1}

    assert OUT_JSON.is_file(), f"missing {OUT_JSON}; run M4 reporter first"
    assert OUT_MD.is_file()
    report = json.loads(OUT_JSON.read_text())
    assert report["disposition"] == "FALSIFICATION_PASS"
    assert "FALSIFICATION_PASS" in OUT_MD.read_text()
    assert report["preserved_labels"]["primary"] == "B_NULL"
    assert report["preserved_labels"]["S10"] == "INVALID"
    assert report["claim_level"] == 2
    assert report["no_fits"] is True
    assert report["checks"]["target_perturbation_invariant"] is True
    assert report["checks"]["mil_mixed_label_refused"] is True
    assert report["checks"]["m3_chromosome_mask_exclusivity"] is True
    assert report["adapter_requirements"]["fake_disease_class_forbidden"] is True
    m3 = json.loads(M3_JSON.read_text())
    assert m3["disposition"] == "SPLITS_AND_SAMPLING_FROZEN"
    assert report["inputs"]["m3_disposition"] == "SPLITS_AND_SAMPLING_FROZEN"
    assert report["m3_mask_verification"]["n_folds_checked"] == 5
