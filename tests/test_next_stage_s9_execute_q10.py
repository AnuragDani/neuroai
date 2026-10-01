"""Q10 S9 execute: coverage, INVALID gates, replay, caps, hash lock."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from p22.eval.s7_ledger import sha256_file
from p22.eval.s9_analytic import PROTOCOL_ID, TOTAL_FITS, S9Refusal
from p22.eval.s9_execute import (
    REVIEWED_HASHES,
    interpret_batch,
    prepare_raw_root,
    read_ledger_records,
    refuse_if_not_allowed_raw_root,
    verify_checkpoint_c_hashes,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/next_stage_20260930"
)
EXECUTE_JSON = OUT / "execute.json"
EXECUTE_MD = OUT / "EXECUTE.md"
RAW_ROOT = ROOT / "reports/generated/nn_s9_analytic_pairing_20260930"
SCRIPT = ROOT / "scripts" / "report_next_stage_s9_execute.py"


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "report_next_stage_s9_execute", SCRIPT
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def report() -> dict:
    assert EXECUTE_JSON.is_file(), f"missing {EXECUTE_JSON}; run Q10 executor first"
    return json.loads(EXECUTE_JSON.read_text())


def test_disposition_invalid_and_coverage(report: dict) -> None:
    assert EXECUTE_MD.is_file()
    text = EXECUTE_MD.read_text()
    assert "INVALID" in text
    assert report["disposition"] == "INVALID"
    assert report["protocol_id"] == PROTOCOL_ID
    assert report["research_fits_executed"] == TOTAL_FITS == 49
    assert report["coverage"]["complete"] is True
    assert report["coverage"]["attempted"] == 49
    assert report["coverage"]["completed_ok"] == 49
    assert report["coverage"]["failed"] == 0
    assert report["scientific_invariants"]["primary"] == "B_NULL"
    assert report["scientific_invariants"]["prior_s8"] == "NO FIT"
    assert report["q11_authorization"]["biological_pilot"] == "BLOCKED"


def test_marginal_and_null_gates_from_saved(report: dict) -> None:
    marginal = report["marginal_check"]
    assert marginal["pass"] is False
    assert marginal["logreg_rna_ba"] == pytest.approx(0.75)
    assert marginal["logreg_atac_ba"] == pytest.approx(0.7083333333333334)
    assert report["pairing_rho0"]["pairing_label"] == "PAIRING_POSITIVE"
    assert report["pairing_rho1"]["pairing_label"] == "PAIRING_NEGATIVE"
    assert "unimodal marginal" in report["interpretation"]["reason"]
    secondary = report["interpretation"].get("secondary_findings") or []
    assert any("rho=0" in s for s in secondary)


def test_resources_within_caps(report: dict) -> None:
    res = report["resources"]
    assert res["attempted_fits"] == 49
    assert res["within_cap"] is True
    assert res["within_fitting_hours"] is True
    assert res["within_artifact_cap"] is True
    assert res["artifacts_gib"] <= 2.0
    assert res["workers"] == 2
    assert res["torch_threads"] == 2


def test_reviewed_hashes_unchanged_and_raw_ledger() -> None:
    live = verify_checkpoint_c_hashes(
        workspace=ROOT,
        protocol_path=OUT / "SYNTHETIC_PROTOCOL.json",
        split_path=OUT / "SPLIT_MANIFEST.json",
        ledger_path=OUT / "FIT_LEDGER.json",
    )
    assert live == REVIEWED_HASHES
    assert sha256_file(ROOT / "src/p22/eval/s9_analytic.py") == REVIEWED_HASHES[
        "src/p22/eval/s9_analytic.py"
    ]
    assert RAW_ROOT.is_dir()
    assert not RAW_ROOT.is_symlink()
    rows = read_ledger_records(RAW_ROOT)
    assert len(rows) == 49
    assert len({r["fit_id"] for r in rows}) == 49
    assert all(r.get("status") == "ok" for r in rows)
    ckpts = list((RAW_ROOT / "checkpoints").glob("*.pt"))
    assert len(ckpts) == 12  # CA+TC × 3 folds × 2 rho
    preds = list((RAW_ROOT / "donor_predictions").glob("*.donors.json"))
    assert len(preds) == 49


def test_replay_skip_fits_stable(report: dict) -> None:
    mod = _load_script()
    summary = mod.write_outputs(
        OUT, workers=2, torch_threads=2, skip_fits=True, raw_root=RAW_ROOT
    )
    assert summary["disposition"] == "INVALID"
    assert summary["research_fits_executed"] == 49
    assert summary["coverage_complete"] is True
    refreshed = json.loads(EXECUTE_JSON.read_text())
    assert refreshed["disposition"] == report["disposition"]
    assert refreshed["marginal_check"]["logreg_rna_ba"] == report["marginal_check"][
        "logreg_rna_ba"
    ]
    assert refreshed["pairing_rho1"]["pairing_label"] == "PAIRING_NEGATIVE"


def test_refuse_forbidden_roots_and_incomplete_rule() -> None:
    with pytest.raises(S9Refusal):
        refuse_if_not_allowed_raw_root("reports/generated/nn_s7_covariance_20260929/")
    with pytest.raises(S9Refusal):
        prepare_raw_root("reports/generated/nn_s8_fake/")
    out = interpret_batch(
        records=[],
        pairing_rho1={"pairing_label": "PAIRING_POSITIVE"},
        pairing_rho0={"pairing_label": "PAIRING_NEGATIVE"},
        marginal={"pass": True},
        coverage={"complete": False},
    )
    assert out["disposition"] == "INCOMPLETE"
