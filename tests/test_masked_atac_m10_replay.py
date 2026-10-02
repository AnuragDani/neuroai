"""M10 saved-prediction replay contracts (no research fits)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from p22.eval.masked_atac_execute import ALLOWED_RAW_ROOT, COUNTER_NAME
from p22.eval.masked_atac_m10_replay import (
    MaskedAtacM10ReplayError,
    measure_artifact_bytes,
    replay_main_fold,
    replay_smoke,
    run_m10_replay,
    verify_pre_replay_pins,
)
from p22.eval.masked_atac_protocol import (
    BOOTSTRAP_SEED,
    PRACTICAL_MARGIN_LOGLOSS,
    paired_donor_contrast_tc_minus_ca,
)
from p22.eval.s7_ledger import sha256_file

ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001"
)
RAW = ROOT / ALLOWED_RAW_ROOT


def test_pre_replay_pins_rematch_live_raw() -> None:
    check = verify_pre_replay_pins(ROOT)
    assert check["all_match"] is True
    assert check["n_checked"] >= 33  # 3 ledger + 30 sidecars + path hashes


def test_toy_independent_loss_and_contrast() -> None:
    donors = ["a", "a", "b", "b"]
    y = np.asarray([0, 1, 0, 1], dtype=np.float64)
    p_tc = np.asarray([0.2, 0.8, 0.3, 0.7], dtype=np.float64)
    p_ca = np.asarray([0.1, 0.9, 0.2, 0.8], dtype=np.float64)
    got = paired_donor_contrast_tc_minus_ca(donors, y, p_tc, p_ca)
    # Hand: donor a mean loss TC vs CA, donor b same; equal mean of deltas.
    from p22.eval.masked_atac_metrics import cell_log_loss

    loss_tc = cell_log_loss(y, p_tc)
    loss_ca = cell_log_loss(y, p_ca)
    d_a = float(np.mean(loss_tc[:2] - loss_ca[:2]))
    d_b = float(np.mean(loss_tc[2:] - loss_ca[2:]))
    assert got["estimate"] == pytest.approx((d_a + d_b) / 2.0)
    assert got["n_donors"] == 2


def test_live_smoke_and_fold0_replay_without_fitting() -> None:
    if not (RAW / "predictions" / "main__token_concat__fold0.json").is_file():
        pytest.skip("main sidecars absent")
    counter_before = sha256_file(RAW / COUNTER_NAME)
    smoke = replay_smoke(ROOT)
    assert smoke["n_smoke_ok"] == 5
    assert smoke["stored_vs_recomputed_loss_match"] is True
    fold0 = replay_main_fold(ROOT, 0)
    assert fold0["arms_equal_cells_labels_donors_target"] is True
    assert fold0["stored_vs_recomputed_loss_match"] is True
    assert fold0["n_test_cells"] == 1536
    assert fold0["n_test_donors"] == 6
    assert sha256_file(RAW / COUNTER_NAME) == counter_before


def test_live_full_m10_replay_contracts() -> None:
    if not (TASK_DIR / "M10_PRE_REPLAY_PINS.json").is_file():
        pytest.skip("M10 pins absent")
    if not (TASK_DIR / "EXECUTE.json").is_file():
        pytest.skip("EXECUTE.json absent")
    counter_before = sha256_file(RAW / COUNTER_NAME)
    report = run_m10_replay(ROOT)
    assert report["fits_run"] == 0
    assert report["counters_modified"] is False
    assert report["diagnostic_replay_pass"] is True
    assert report["disposition"] == "REPLAY_PASS_DIAGNOSTIC_ONLY"
    assert report["prospective_executor_review_gate"] == "FAIL"
    assert report["scientific_acceptance_of_M9"] == "NOT_AUTHORIZED"
    primary = report["primary_contrast"]
    assert primary["n_donors_pooled"] == 30
    assert primary["practical_margin"] == PRACTICAL_MARGIN_LOGLOSS
    assert primary["bootstrap"]["seed"] == BOOTSTRAP_SEED
    assert primary["exploratory_advantage_observed"] is False
    assert report["execute_comparison"]["primary_match"] is True
    assert report["post_replay_counter"]["preserved"] is True
    assert report["post_replay_counter"]["total_attempts_used"] == 30
    assert sha256_file(RAW / COUNTER_NAME) == counter_before
    # Live du must be positive; counter field may remain 0.
    assert report["artifact_bytes"]["du_kib"] > 0
    assert measure_artifact_bytes(RAW)["du_kib"] == report["artifact_bytes"]["du_kib"]


def test_replay_refuses_missing_sidecar(tmp_path: Path) -> None:
    # Point workspace predictions at empty dir via monkeypatch of raw layout.
    # Minimal: call replay_main_fold against a fake workspace without sidecars.
    fake = tmp_path / "ws"
    pred = fake / ALLOWED_RAW_ROOT / "predictions"
    pred.mkdir(parents=True)
    with pytest.raises(MaskedAtacM10ReplayError, match="missing sidecar"):
        replay_main_fold(fake, 0)
