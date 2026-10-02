"""M7 measured-target adapter / dry-run implement tests."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from p22.eval.masked_atac_adapter import (
    SELECTION_METRIC_NAME,
    assert_donors_allow_mixed_labels,
    build_toy_mixed_label_fold,
    check_finite_gradients_cell_target,
    check_state_dict_reload_equality_cell_target,
    fit_constant_prevalence,
    fit_logreg_cell_target,
    train_cell_target_model,
    verify_selection_prefers_cell_log_loss_over_donor_mean_prob,
)
from p22.eval.masked_atac_execute import (
    DISPOSITION,
    MaskedAtacExecuteRefusal,
    refuse_if_not_allowed_raw_root,
    refuse_unreviewed_learning,
)
from p22.eval.masked_atac_metrics import assert_existing_mil_refuses_mixed_labels
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.multiome_runner import paired_model
from p22.models.fusion import VIEW_A, VIEW_B
from p22.training.loop import train_model

ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001"
)
PROTOCOL_JSON = TASK_DIR / "PILOT_PROTOCOL.json"
M6_LOCK = TASK_DIR / "M6_REVIEWED_HASHES.json"
IMPLEMENT_JSON = TASK_DIR / "implement.json"
IMPLEMENT_MD = TASK_DIR / "IMPLEMENT.md"
COUNTER = ROOT / "reports/generated/nn_masked_atac_pilot_20261001/attempt_counter.json"


def test_mixed_label_adapter_trains_and_selects_by_cell_log_loss() -> None:
    toy = build_toy_mixed_label_fold()
    meta = assert_donors_allow_mixed_labels(
        toy["donors"][toy["train_idx"]], toy["labels"][toy["train_idx"]]
    )
    assert meta["mixed_label_donors"] == ["D0", "D1"]
    proto = MultiomeProtocol(
        max_epochs=3,
        patience=2,
        batch_size=4,
        n_repeats=1,
        feature_budget=8,
    )
    widths = [toy["views"][VIEW_A].shape[1], toy["views"][VIEW_B].shape[1]]
    model = paired_model("token_concat", widths, proto)
    result = train_cell_target_model(
        model,
        {
            VIEW_A: toy["views"][VIEW_A][toy["train_idx"]],
            VIEW_B: toy["views"][VIEW_B][toy["train_idx"]],
        },
        toy["labels"][toy["train_idx"]],
        toy["donors"][toy["train_idx"]],
        {
            VIEW_A: toy["views"][VIEW_A][toy["val_idx"]],
            VIEW_B: toy["views"][VIEW_B][toy["val_idx"]],
        },
        toy["labels"][toy["val_idx"]],
        toy["donors"][toy["val_idx"]],
        max_epochs=3,
        patience=2,
        batch_size=4,
        seed=0,
    )
    assert result.trained.selection_metric == SELECTION_METRIC_NAME
    assert result.trained.training_weighting == "inverse_donor_cell_count"
    assert result.trained.epochs_run >= 1
    assert len(result.initial_state_sha256) == 64
    assert len(result.checkpoint_sha256) == 64
    assert np.isfinite(result.val_donor_average_cell_log_loss)


def test_disease_trainers_still_refuse_mixed_labels() -> None:
    mil = assert_existing_mil_refuses_mixed_labels()
    assert mil["mixed_refused"] is True
    toy = build_toy_mixed_label_fold()
    proto = MultiomeProtocol(max_epochs=1, patience=1, batch_size=4, n_repeats=1)
    widths = [toy["views"][VIEW_A].shape[1], toy["views"][VIEW_B].shape[1]]
    model = paired_model("cross_attention", widths, proto)
    with pytest.raises(ValueError, match="mixed labels"):
        train_model(
            model,
            {
                VIEW_A: toy["views"][VIEW_A][toy["train_idx"]],
                VIEW_B: toy["views"][VIEW_B][toy["train_idx"]],
            },
            toy["labels"][toy["train_idx"]],
            {
                VIEW_A: toy["views"][VIEW_A][toy["val_idx"]],
                VIEW_B: toy["views"][VIEW_B][toy["val_idx"]],
            },
            toy["labels"][toy["val_idx"]],
            max_epochs=1,
            patience=1,
            batch_size=4,
            seed=0,
            train_donor_ids=toy["donors"][toy["train_idx"]],
            val_donor_ids=toy["donors"][toy["val_idx"]],
        )


def test_selection_metric_and_constant_logreg_paths() -> None:
    check = verify_selection_prefers_cell_log_loss_over_donor_mean_prob()
    assert check["cell_log_loss_prefers_good"] is True
    toy = build_toy_mixed_label_fold()
    const = fit_constant_prevalence(toy["labels"][toy["train_idx"]], n_predict=2)
    assert const["n_parameters"] == 0
    assert const["fits_count"] == 0
    logreg = fit_logreg_cell_target(
        toy["views"][VIEW_A],
        toy["labels"],
        toy["donors"],
        toy["train_idx"],
        toy["test_idx"],
    )
    assert logreg["probabilities"].shape == (2,)
    assert np.isfinite(logreg["probabilities"]).all()


def test_gradients_reload_and_m8_gate() -> None:
    toy = build_toy_mixed_label_fold()
    for arm in ("feature_concat_mlp", "token_concat", "cross_attention"):
        g = check_finite_gradients_cell_target(arm, toy["views"], toy["labels"])
        assert g["finite"] is True
        r = check_state_dict_reload_equality_cell_target(arm, toy["views"])
        assert r["passed"] is True
    # Missing lock still refuses; live M8 PASS lock authorizes when the
    # locked zero counter digest is present (swap/restore; never permanent reset).
    from masked_atac_counter_testutil import temporarily_zeroed_attempt_counter

    with pytest.raises(MaskedAtacExecuteRefusal, match="REFUSED_UNTIL_M8"):
        refuse_unreviewed_learning(m8_lock_path=None, workspace=ROOT)
    with temporarily_zeroed_attempt_counter(COUNTER):
        refuse_unreviewed_learning(
            m8_lock_path=TASK_DIR / "M8_REVIEWED_HASHES.json", workspace=ROOT
        )
    with pytest.raises(MaskedAtacExecuteRefusal):
        refuse_if_not_allowed_raw_root("reports/generated/nn_s9_analytic_pairing_20260930/")
    refuse_if_not_allowed_raw_root(ROOT / "reports/generated/nn_masked_atac_pilot_20261001/")


def test_live_implement_report_contracts() -> None:
    assert IMPLEMENT_JSON.is_file()
    assert IMPLEMENT_MD.is_file()
    report = json.loads(IMPLEMENT_JSON.read_text())
    assert report["disposition"] == DISPOSITION
    assert report["no_fits"] is True
    assert report["trainability_with_learning"] == "REFUSED_UNTIL_M8"
    assert report["checks"]["learning_refused_until_m8"] is True
    assert report["checks"]["adapter_mixed_label_train_ok"] is True
    assert report["counter_snapshot"]["ok"] is True
    assert report["preserved_labels"]["primary"] == "B_NULL"
    assert report["preserved_labels"]["S10"] == "INVALID"
    # Historical M7 snapshot remained zero; live counters may include M9 smoke.
    assert report["counter_snapshot"]["total_attempts_used"] == 0
    assert report["counter_snapshot"]["smoke_fits_used"] == 0
    counter = json.loads(COUNTER.read_text())
    assert int(counter["total_attempts"]["hard_cap"]) == 40
    assert int(counter["smoke_fits"]["cap"]) == 5
