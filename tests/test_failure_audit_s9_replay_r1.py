"""R1 failure-audit S9 read-only replay: coverage, hashes, INVALID retained."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001"
)
AUDIT_JSON = OUT / "s9_audit.json"
AUDIT_MD = OUT / "S9_AUDIT.md"
SCRIPT = ROOT / "scripts" / "replay_failure_audit_s9.py"
S9_RAW = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/"
    "finish-engineering-20260928-gnhf-worktrees/"
    "read-tasks-nn-finish-ee2202-gnhf-worktrees/"
    "read-users-anuragdan-b61180-gnhf-worktrees/"
    "execute-the-p22-data-146414/reports/generated/nn_s9_analytic_pairing_20260930"
)
PRIOR_EXECUTE = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/next_stage_20260930"
    / "execute.json"
)


def _load_script():
    spec = importlib.util.spec_from_file_location("replay_failure_audit_s9", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def report() -> dict:
    assert AUDIT_JSON.is_file(), f"missing {AUDIT_JSON}; run R1 replay first"
    return json.loads(AUDIT_JSON.read_text())


def test_audit_files_and_disposition(report: dict) -> None:
    assert AUDIT_MD.is_file()
    text = AUDIT_MD.read_text()
    assert "protocol_failure" in text
    assert "INVALID" in text
    assert report["disposition"] == "REPLAY_PASS"
    assert report["scientific_label_retained"] == "INVALID"
    assert report["research_fits_this_replay"] == 0
    assert report["shared_raw_unchanged"] is True
    assert report["coverage"]["complete"] is True
    assert report["coverage"]["attempted"] == 49
    assert report["sidecar_hash_validation"]["all_ok"] is True


def test_marginal_pairing_match_prior(report: dict) -> None:
    prior = json.loads(PRIOR_EXECUTE.read_text())
    assert report["marginal_check"]["pass"] is False
    assert report["marginal_check"]["logreg_rna_ba"] == pytest.approx(
        prior["marginal_check"]["logreg_rna_ba"]
    )
    assert report["marginal_check"]["logreg_atac_ba"] == pytest.approx(
        prior["marginal_check"]["logreg_atac_ba"]
    )
    assert report["pairing_rho1"]["pairing_label"] == prior["pairing_rho1"]["pairing_label"]
    assert report["pairing_rho0"]["pairing_label"] == prior["pairing_rho0"]["pairing_label"]
    assert all(report["matches_prior_execute_json"].values())


def test_independent_ba_and_categories(report: dict) -> None:
    assert all(v["match"] for v in report["independent_ba_checks"].values())
    cats = report["failure_categories"]
    assert cats["protocol_failure"]["applies"] is True
    assert cats["implementation_deviation"]["applies"] is False
    assert cats["uncertain_optimization"]["applies"] is True
    assert cats["missing_provenance"]["applies"] is True
    assert report["optimization_provenance"]["any_epoch_history"] is False


def test_refuse_out_dir_equals_shared_raw() -> None:
    mod = _load_script()
    with pytest.raises(mod.S9ReplayRefusal):
        mod.main(["--out-dir", str(S9_RAW), "--s9-raw", str(S9_RAW)])


def test_shared_raw_fingerprint_stable_on_rerun(tmp_path: Path) -> None:
    if not S9_RAW.is_dir():
        pytest.skip("shared S9 raw unavailable")
    mod = _load_script()
    before = mod._fingerprint_tree(S9_RAW)
    out = tmp_path / "r1_out"
    summary = mod.write_outputs(
        out_dir=out,
        workspace=ROOT,
        s9_raw=S9_RAW,
        protocol_dir=PRIOR_EXECUTE.parent,
        audit_raw=tmp_path / "audit_raw",
    )
    after = mod._fingerprint_tree(S9_RAW)
    assert before["tree_sha256"] == after["tree_sha256"]
    assert summary["shared_raw_unchanged"] is True
    assert summary["scientific_label_retained"] == "INVALID"
