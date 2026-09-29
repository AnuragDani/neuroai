"""Focused checks for S7 fit ledger, budget, resume hashes and param match.

No H5AD loads and no model training beyond constructing uninitialized CA/TC
heads for the pre-fit parameter-count gate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.multiome_runner import paired_model
from p22.eval.s7_ledger import (
    S7_MAX_TOTAL_FITS,
    S7_MODELS,
    S7_RHO_GRID,
    S7_SCREEN_SEED,
    S7FitLedger,
    Provenance,
    check_param_match,
    count_parameters,
    enumerate_screen_jobs,
    make_fit_id,
    sha256_text,
)


def _prov(**overrides) -> Provenance:
    base = {
        "protocol_id": "S7_covariance_20260929",
        "spec_sha256": "a" * 64,
        "source_sha256": {"planted_signal.py": "b" * 64, "s7_ledger.py": "c" * 64},
        "input_sha256": {"h5ad": "d" * 64},
    }
    base.update(overrides)
    return Provenance(**base)


def test_enumerate_screen_is_105_predeclared() -> None:
    jobs = enumerate_screen_jobs()
    assert len(jobs) == len(S7_RHO_GRID) * 5 * len(S7_MODELS) == 105
    assert jobs[0]["fit_id"] == make_fit_id(
        "screen", 0.0, S7_SCREEN_SEED, 0, S7_MODELS[0]
    )
    ids = [j["fit_id"] for j in jobs]
    assert len(ids) == len(set(ids))


def test_immutable_fit_and_budget_accounting(tmp_path: Path) -> None:
    ledger = S7FitLedger(tmp_path, max_total_fits=3, smoke_fit_limit=2)
    ledger.freeze(_prov())
    fid = make_fit_id("smoke", 1.0, 1001, 0, "logreg_rna")
    ledger.record_fit(fid, {"stage": "smoke", "status": "ok", "donor_ba": 0.5})
    assert ledger.n_completed == 1
    assert ledger.remaining_budget() == 2
    assert ledger.smoke_remaining() == 1
    with pytest.raises(RuntimeError, match="immutable fit refusal"):
        ledger.record_fit(fid, {"stage": "smoke", "status": "ok"})
    ledger.record_fit(
        make_fit_id("smoke", 1.0, 1001, 1, "logreg_rna"),
        {"stage": "smoke", "status": "ok"},
    )
    assert ledger.smoke_remaining() == 0
    with pytest.raises(RuntimeError, match="smoke budget exhausted"):
        ledger.record_fit(
            make_fit_id("smoke", 1.0, 1001, 2, "logreg_rna"),
            {"stage": "smoke", "status": "ok"},
        )
    # Non-smoke still allowed within total budget.
    ledger.record_fit(
        make_fit_id("screen", 0.0, 1001, 0, "logreg_rna"),
        {"stage": "screen", "status": "ok"},
    )
    assert ledger.remaining_budget() == 0
    with pytest.raises(RuntimeError, match="budget exhausted"):
        ledger.record_fit(
            make_fit_id("screen", 0.0, 1001, 1, "logreg_rna"),
            {"stage": "screen", "status": "ok"},
        )
    assert S7_MAX_TOTAL_FITS == 480


def test_resume_hash_refusal_marks_invalid(tmp_path: Path) -> None:
    ledger = S7FitLedger(tmp_path)
    frozen = _prov()
    ledger.freeze(frozen)
    ledger.record_fit(
        make_fit_id("screen", 1.0, 1001, 0, "cross_attention"),
        {"stage": "screen", "status": "ok"},
    )
    # Exact match resumes cleanly.
    ledger.assert_resume_hashes(frozen)
    changed = _prov(source_sha256={"planted_signal.py": "e" * 64, "s7_ledger.py": "c" * 64})
    with pytest.raises(RuntimeError, match="resume hash refusal"):
        ledger.assert_resume_hashes(changed)
    assert ledger.is_invalid
    assert "resume hash refusal" in (ledger.invalid_reason or "")
    with pytest.raises(RuntimeError, match="ledger invalid"):
        ledger.record_fit(
            make_fit_id("screen", 1.0, 1001, 1, "cross_attention"),
            {"stage": "screen", "status": "ok"},
        )


def test_freeze_conflict_and_reload(tmp_path: Path) -> None:
    ledger = S7FitLedger(tmp_path)
    first = _prov()
    ledger.freeze(first)
    # Idempotent freeze with identical payload.
    ledger.freeze(first)
    other = _prov(spec_sha256="f" * 64)
    with pytest.raises(RuntimeError, match="resume hash refusal"):
        ledger.freeze(other)
    reloaded = S7FitLedger(tmp_path)
    reloaded.load()
    assert reloaded.is_invalid
    assert reloaded.n_completed == 0


def test_coverage_incomplete_until_all_cells(tmp_path: Path) -> None:
    ledger = S7FitLedger(tmp_path)
    ledger.freeze(_prov())
    for fold in range(5):
        for model in S7_MODELS:
            ledger.record_fit(
                make_fit_id("screen", 1.0, S7_SCREEN_SEED, fold, model),
                {"stage": "screen", "status": "ok"},
            )
    cov = ledger.coverage(stage="screen", rho=1.0)
    assert cov["complete"] is True
    assert cov["expected"] == 35
    full = ledger.coverage(stage="screen")
    assert full["complete"] is False
    assert len(full["missing"]) == 70


def test_param_match_gate_n4_widths() -> None:
    protocol = MultiomeProtocol(
        n_tokens=8,
        embed_dim=32,
        hidden_dim=128,
        n_heads=4,
        dropout=0.2,
        n_repeats=1,
        n_folds=5,
        split_seed=0,
        model_seed=1001,
        sampling_seed=22,
    )
    widths = [2000, 256]
    ca = paired_model("cross_attention", widths, protocol)
    tc = paired_model("token_concat", widths, protocol)
    record = check_param_match(count_parameters(ca), count_parameters(tc))
    assert record["matched"] is True
    assert record["relative_error"] <= 0.10
    with pytest.raises(ValueError, match="parameter mismatch"):
        check_param_match(1000, 2000)


def test_provenance_fingerprint_stable() -> None:
    a = _prov()
    b = _prov()
    assert a.fingerprint() == b.fingerprint()
    assert a.fingerprint() == sha256_text(
        json.dumps(a.to_dict(), sort_keys=True, separators=(",", ":"))
    )
