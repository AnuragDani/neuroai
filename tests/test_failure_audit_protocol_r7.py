"""R7 failure-audit S10 protocol freeze and minimal implement tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from p22.eval.s9_analytic import generate_analytic_arrays
from p22.eval.s10_analytic import (
    ALLOWED_RAW_ROOT,
    ARMS,
    DECISION_GENERATOR_SEED,
    DECISION_SPLIT_SEED,
    NEURAL_ARMS,
    NULL_CANDIDATE_ID,
    PROTOCOL_ID,
    R7_EXCHANGEABILITY_SEEDS,
    SCIENTIFIC_ATTEMPT_CAP,
    TOTAL_FITS,
    WORKERS,
    S10Refusal,
    allocate_s10_folds,
    assert_donor_isolation,
    assign_donor_labels,
    check_finite_gradients,
    check_state_dict_reload_equality,
    enumerate_s10_jobs,
    fold_row_indices,
    generate_corrected_arrays,
    permute_atac_within_donor,
    refuse_if_not_allowed_raw_root,
    refuse_mismatched_protocol_hash,
    refuse_unreviewed_scientific_fits,
    s10_protocol_from_frozen,
    verify_exchangeability_panel,
    verify_oracle_invariants,
)
from p22.eval.s10_execute import (
    execution_defaults,
    preflight_no_fit,
    run_scientific_batch,
)
from p22.models.fusion import VIEW_A, VIEW_B

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001"
)
PROTOCOL_JSON = OUT / "S10_PROTOCOL.json"
PROTOCOL_MD = OUT / "S10_PROTOCOL.md"
SPLIT_JSON = OUT / "S10_SPLIT_MANIFEST.json"
SEED_JSON = OUT / "S10_SEED_SCHEDULE.json"
IMPLEMENT_JSON = OUT / "implement.json"
IMPLEMENT_MD = OUT / "IMPLEMENT.md"
COUNTER = ROOT / "reports/generated/nn_failure_audit_20261001/attempt_counter.json"


@pytest.fixture(scope="module")
def report() -> dict:
    assert IMPLEMENT_JSON.is_file(), f"missing {IMPLEMENT_JSON}; run R7 reporter"
    assert PROTOCOL_JSON.is_file()
    assert SPLIT_JSON.is_file()
    return json.loads(IMPLEMENT_JSON.read_text())


def test_protocol_frozen_and_zero_fits(report: dict) -> None:
    proto = json.loads(PROTOCOL_JSON.read_text())
    assert proto["disposition"] == "PROTOCOL_FROZEN"
    assert proto["protocol_id"] == PROTOCOL_ID
    assert proto["null_candidate_id"] == NULL_CANDIDATE_ID
    assert proto["claim_level"] == 1
    assert proto["fits"] == 0
    assert report["disposition"] == "IMPLEMENT_PASS"
    assert report["research_fits_executed"] == 0
    assert report["diagnostic_fits_executed"] == 0
    assert report["trainability_with_learning"] == "REFUSED_UNTIL_CHECKPOINT_C"
    text = PROTOCOL_MD.read_text()
    assert "PROTOCOL_FROZEN" in text
    assert "no exact" in text.lower() or "NO orthogonalize" in text or "orthogonal" in text.lower()
    assert IMPLEMENT_MD.is_file()
    labels = report["scientific_invariants"]
    assert labels["s9"] == "INVALID"
    assert labels["s9_immutable"] is True
    assert labels["primary"] == "B_NULL"


def test_corrected_generator_not_orthogonal_and_exchangeable() -> None:
    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    rna, atac, donor, _, _ = generate_corrected_arrays(
        labels, rho=0.0, generator_seed=DECISION_GENERATOR_SEED
    )
    products = []
    for name in sorted(set(donor.tolist()), key=str):
        idx = np.flatnonzero(donor == name)
        for ch in range(4):
            products.append(float(np.mean(rna[idx, ch] * atac[idx, ch])))
    assert float(np.max(np.abs(products))) > 1e-6
    # S9 orthogonal path remains machine-near-zero (contrast).
    rna_s9, atac_s9, donor_s9, _, _ = generate_analytic_arrays(
        labels, rho=0.0, generator_seed=DECISION_GENERATOR_SEED
    )
    s9_products = []
    for name in sorted(set(donor_s9.tolist()), key=str):
        idx = np.flatnonzero(donor_s9 == name)
        for ch in range(4):
            s9_products.append(float(np.mean(rna_s9[idx, ch] * atac_s9[idx, ch])))
    assert float(np.max(np.abs(s9_products))) < 1e-12
    oracle = verify_oracle_invariants(labels)
    assert oracle["oracle_gate"] == "PASS"
    assert oracle["rho0_not_exact_orthogonal"] is True
    panel = verify_exchangeability_panel(labels)
    assert panel["ratio_within_band"] is True
    assert 0.95 <= panel["mean_ratio"] <= 1.05
    assert len(R7_EXCHANGEABILITY_SEEDS) == 16


def test_job_coverage_serial_defaults_and_hashes(report: dict) -> None:
    assert report["job_coverage"]["total"] == TOTAL_FITS == 49
    assert report["job_coverage"]["smoke"] == 7
    assert report["job_coverage"]["screen"] == 42
    assert report["job_coverage"]["within_cap"] is True
    jobs = enumerate_s10_jobs()
    assert len(jobs) == 49
    assert len({j["fit_id"] for j in jobs}) == 49
    assert WORKERS == 1
    defaults = execution_defaults()
    assert defaults["workers"] == 1
    assert defaults["parallel_dispatch"] is False
    assert defaults["thread_pool_executor"] is False
    assert defaults["planned_fits"] <= SCIENTIFIC_ATTEMPT_CAP
    for key in (
        "S10_PROTOCOL.json",
        "S10_SPLIT_MANIFEST.json",
        "src/p22/eval/s10_analytic.py",
        "src/p22/eval/s10_execute.py",
    ):
        digest = report["hashes"][key]
        assert len(digest) == 64
    # Live file hashes match report.
    for rel, key in (
        (PROTOCOL_JSON, "S10_PROTOCOL.json"),
        (SPLIT_JSON, "S10_SPLIT_MANIFEST.json"),
        (ROOT / "src/p22/eval/s10_analytic.py", "src/p22/eval/s10_analytic.py"),
        (ROOT / "src/p22/eval/s10_execute.py", "src/p22/eval/s10_execute.py"),
    ):
        live = hashlib.sha256(rel.read_bytes()).hexdigest()
        assert live == report["hashes"][key]


def test_donor_isolation_margins_gradients_reload() -> None:
    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    split = allocate_s10_folds(labels)
    assert split["folds"]["0"]["test_donors"]
    rna, atac, donor, label_col, _ = generate_corrected_arrays(
        labels, rho=1.0, generator_seed=DECISION_GENERATOR_SEED
    )
    positions = fold_row_indices(donor, split["folds"]["0"])
    assert_donor_isolation(positions, donor)
    leak = {
        "train": positions["train"],
        "val": positions["val"],
        "test": np.concatenate([positions["test"], positions["train"][:2]]),
    }
    from p22.eval.s9_analytic import S9Refusal

    with pytest.raises(S9Refusal, match="leakage"):
        assert_donor_isolation(leak, donor)
    shuffled = permute_atac_within_donor(atac, donor, seed=4001)
    for name in sorted(set(donor.tolist()), key=str):
        idx = np.flatnonzero(donor == name)
        assert np.allclose(np.sort(atac[idx], axis=0), np.sort(shuffled[idx], axis=0))
    views = {VIEW_A: rna.astype(np.float32), VIEW_B: atac.astype(np.float32)}
    proto = s10_protocol_from_frozen()
    assert proto.split_seed == DECISION_SPLIT_SEED
    for arm in NEURAL_ARMS:
        assert check_finite_gradients(arm, views, label_col, proto)["finite"] is True
        assert check_state_dict_reload_equality(arm, views, proto)["passed"] is True


def test_refusals_and_executor_gate(report: dict) -> None:
    with pytest.raises(S10Refusal, match="hash mismatch"):
        refuse_mismatched_protocol_hash("a" * 64, "b" * 64)
    with pytest.raises(S10Refusal):
        refuse_if_not_allowed_raw_root(
            "reports/generated/nn_s9_analytic_pairing_20260930/"
        )
    with pytest.raises(S10Refusal):
        refuse_if_not_allowed_raw_root("reports/generated/nn_s7_covariance_20260929/")
    with pytest.raises(S10Refusal):
        refuse_if_not_allowed_raw_root("reports/generated/nn_s8_demo/")
    refuse_if_not_allowed_raw_root(ALLOWED_RAW_ROOT)
    with pytest.raises(S10Refusal, match="R8"):
        refuse_unreviewed_scientific_fits()
    # No-arg scientific batch still hard-refuses (self-certification path).
    with pytest.raises(S10Refusal, match="R8"):
        run_scientific_batch()
    # External lock may already exist after R8; completeness is not required False here.
    assert execution_defaults()["workers"] == 1
    pf = preflight_no_fit(
        workspace=ROOT,
        protocol_path=PROTOCOL_JSON,
        split_path=SPLIT_JSON,
        raw_root=ALLOWED_RAW_ROOT,
    )
    assert pf["oracle_gate"] == "PASS"
    assert pf["n_jobs"] == 49
    # After R8 lock write, preflight reports authorization availability; fits still
    # require review record + verify_reviewed_hashes at dispatch.
    assert isinstance(pf["scientific_fits_authorized"], bool)
    assert len(ARMS) == 7
    seed = json.loads(SEED_JSON.read_text())
    assert seed["decision_generator_seed"] == DECISION_GENERATOR_SEED
    assert seed["committed_before_simulation"] is True
    assert seed["disjoint_from"]["s9_decision_generator"] == 9001
    assert DECISION_GENERATOR_SEED != 9001
    counter = json.loads(COUNTER.read_text())
    # R7 spent 0 scientific fits; later R9 may consume scientific attempts within cap.
    assert counter["scientific_fit_attempts"] <= counter["scientific_fit_cap"]
    assert report["generator_draws_this_run"] == 16
    assert counter["generator_only_draws"] >= 81 + 16
