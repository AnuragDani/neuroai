"""M5 protocol freeze: estimand, bootstrap, attempt arithmetic, artifacts."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from p22.eval.masked_atac_metrics import cell_log_loss
from p22.eval.masked_atac_protocol import (
    BOOTSTRAP_SEED,
    DISPOSITION,
    HARD_ATTEMPT_CAP,
    LEARNED_ARMS,
    PARAM_MATCH_TOLERANCE,
    PLANNED_MAIN_FITS,
    PLANNED_SMOKE_FITS,
    PRACTICAL_MARGIN_LOGLOSS,
    PRIMARY_CONTRAST_NAME,
    attempt_arithmetic,
    build_budget_ledger,
    build_protocol_report,
    ca_tc_param_match_for_widths,
    enumerate_planned_jobs,
    paired_donor_bootstrap_contrast,
    paired_donor_contrast_tc_minus_ca,
)

ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001"
)
OUT_JSON = TASK_DIR / "PILOT_PROTOCOL.json"
OUT_MD = TASK_DIR / "PILOT_PROTOCOL.md"
BUDGET_JSON = TASK_DIR / "budget_ledger.json"
BUDGET_MD = TASK_DIR / "BUDGET_LEDGER.md"
M3_JSON = TASK_DIR / "SPLITS_AND_SAMPLING.json"
M4_JSON = TASK_DIR / "FALSIFICATION.json"
COUNTER = ROOT / "reports/generated/nn_masked_atac_pilot_20261001/attempt_counter.json"


def test_attempt_arithmetic_exact() -> None:
    arith = attempt_arithmetic()
    assert arith.planned_main_fits == 25 == PLANNED_MAIN_FITS
    assert arith.planned_smoke_fits == 5 == PLANNED_SMOKE_FITS
    assert arith.planned_total_intended == 30
    assert arith.hard_attempt_cap == HARD_ATTEMPT_CAP == 40
    assert arith.headroom == 10
    assert arith.constant_arm_fits == 0
    assert arith.within_caps is True
    jobs = enumerate_planned_jobs()
    assert len(jobs) == 30
    assert sum(1 for j in jobs if j["stage"] == "smoke") == 5
    assert sum(1 for j in jobs if j["stage"] == "main") == 25
    assert {j["arm"] for j in jobs if j["stage"] == "smoke"} == set(LEARNED_ARMS)


def test_paired_contrast_hand_and_bootstrap_keeps_single_class() -> None:
    donors = ["A", "A", "B", "B", "C"]
    y = np.asarray([1, 0, 1, 1, 0], dtype=np.float64)
    p_tc = np.asarray([0.6, 0.4, 0.7, 0.55, 0.3], dtype=np.float64)
    p_ca = np.asarray([0.8, 0.3, 0.85, 0.7, 0.25], dtype=np.float64)
    # C is single-class (y=0 only) — must still contribute to log-loss contrast.
    got = paired_donor_contrast_tc_minus_ca(donors, y, p_tc, p_ca)
    hand = float(
        np.mean(
            [
                np.mean(cell_log_loss([1, 0], [0.6, 0.4]))
                - np.mean(cell_log_loss([1, 0], [0.8, 0.3])),
                np.mean(cell_log_loss([1, 1], [0.7, 0.55]))
                - np.mean(cell_log_loss([1, 1], [0.85, 0.7])),
                float(cell_log_loss([0], [0.3])[0] - cell_log_loss([0], [0.25])[0]),
            ]
        )
    )
    assert got["name"] == PRIMARY_CONTRAST_NAME
    assert math.isclose(got["estimate"], hand, rel_tol=0.0, abs_tol=1e-12)
    assert got["n_donors"] == 3
    boot = paired_donor_bootstrap_contrast(
        donors, y, p_tc, p_ca, n_replicates=100, seed=BOOTSTRAP_SEED
    )
    assert boot["n_valid"] == 100
    assert boot["n_failed"] == 0
    assert boot["single_class_draws_dropped"] is False
    assert boot["interval"][0] is not None
    assert boot["practical_margin"] == PRACTICAL_MARGIN_LOGLOSS
    # Determinism
    boot2 = paired_donor_bootstrap_contrast(
        donors, y, p_tc, p_ca, n_replicates=100, seed=BOOTSTRAP_SEED
    )
    assert boot2["interval"] == boot["interval"]


def test_ca_tc_param_match_and_protocol_suite() -> None:
    for width in (423, 430, 440):
        rec = ca_tc_param_match_for_widths(128, width)
        assert rec["matched"] is True
        assert rec["relative_error"] <= PARAM_MATCH_TOLERANCE
    report = build_protocol_report(m3_path=M3_JSON, m4_path=M4_JSON)
    assert report["disposition"] == DISPOSITION
    assert all(report["checks"].values())
    assert report["no_fits"] is True
    assert report["primary_contrast"]["practical_margin"] == PRACTICAL_MARGIN_LOGLOSS
    assert "disease BA" in report["primary_contrast"]["practical_margin_justification"] or (
        "Disease BA" in report["primary_contrast"]["practical_margin_justification"]
    )
    # Live production counter may already reflect M9 smoke/main; evaluate
    # M5 ledger arithmetic against the locked zero snapshot only.
    from masked_atac_counter_testutil import (
        LOCKED_ZERO_COUNTER,
        temporarily_zeroed_attempt_counter,
    )

    with temporarily_zeroed_attempt_counter(COUNTER):
        ledger = build_budget_ledger(counter_path=COUNTER, protocol=report)
        assert ledger["fit_feasibility"] == "PASS"
        assert ledger["checks"]["counters_still_zero"] is True
    # Confirm restore preserved any progressed production state schema.
    live = json.loads(COUNTER.read_text())
    assert "total_attempts" in live
    assert live["total_attempts"]["hard_cap"] == HARD_ATTEMPT_CAP
    _ = LOCKED_ZERO_COUNTER


def test_live_protocol_artifacts() -> None:
    assert OUT_JSON.is_file(), f"missing {OUT_JSON}; run M5 writer first"
    assert OUT_MD.is_file()
    assert BUDGET_JSON.is_file()
    assert BUDGET_MD.is_file()
    report = json.loads(OUT_JSON.read_text())
    assert report["disposition"] == DISPOSITION
    assert "PROTOCOL_FROZEN" in OUT_MD.read_text()
    assert report["attempt_arithmetic"]["planned_main_fits"] == 25
    assert report["attempt_arithmetic"]["planned_total_intended"] == 30
    assert report["bootstrap"]["n_replicates"] == 1000
    assert report["bootstrap"]["seed"] == BOOTSTRAP_SEED
    assert report["preserved_labels"]["primary"] == "B_NULL"
    assert report["preserved_labels"]["S10"] == "INVALID"
    assert report["claim_level"] == 2
    assert report["inputs"]["m3_disposition"] == "SPLITS_AND_SAMPLING_FROZEN"
    assert report["inputs"]["m4_disposition"] == "FALSIFICATION_PASS"
    ledger = json.loads(BUDGET_JSON.read_text())
    assert ledger["fit_feasibility"] == "PASS"
    assert ledger["planned"]["planned_total_intended"] == 30
    assert "Fit feasibility" in BUDGET_MD.read_text()
