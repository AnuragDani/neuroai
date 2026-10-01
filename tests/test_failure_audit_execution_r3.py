"""R3 failure-audit execution determinism: inventory, hashes, diagnostics, ledger."""

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
AUDIT_JSON = OUT / "execution_audit.json"
AUDIT_MD = OUT / "EXECUTION_AUDIT.md"
SPEC = OUT / "R3_DIAGNOSTIC_FIT_SPEC.json"
RESULTS = OUT / "r3_diagnostic_results.json"
REVIEW = OUT / "INDEPENDENT_REVIEW_R3_DIAGNOSTIC_SPEC.json"
SCRIPT = ROOT / "scripts" / "audit_failure_audit_execution_r3.py"
COUNTER = ROOT / "reports/generated/nn_failure_audit_20261001/attempt_counter.json"
S9_RAW = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/"
    "finish-engineering-20260928-gnhf-worktrees/"
    "read-tasks-nn-finish-ee2202-gnhf-worktrees/"
    "read-users-anuragdan-b61180-gnhf-worktrees/"
    "execute-the-p22-data-146414/reports/generated/nn_s9_analytic_pairing_20260930"
)


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "audit_failure_audit_execution_r3", SCRIPT
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def report() -> dict:
    assert AUDIT_JSON.is_file(), f"missing {AUDIT_JSON}; run R3 audit first"
    return json.loads(AUDIT_JSON.read_text())


@pytest.fixture(scope="module")
def diag() -> dict:
    assert RESULTS.is_file(), f"missing {RESULTS}; run authorized diagnostic fits"
    return json.loads(RESULTS.read_text())


def test_audit_files_disposition_and_budget(report: dict, diag: dict) -> None:
    assert AUDIT_MD.is_file()
    assert SPEC.is_file()
    assert REVIEW.is_file()
    text = AUDIT_MD.read_text()
    assert "INVALID" in text
    assert report["disposition"] == "EXECUTION_AUDIT_PASS"
    assert report["review_status"] == "PASS"
    assert report["scientific_label_retained"] == "INVALID"
    assert report["research_fits"] == 0
    assert report["shared_raw_unchanged"] is True
    assert diag["attempts"] == 12
    assert diag["attempt_cap"] == 12
    assert report["diagnostic_fits_cumulative"] == 12
    counter = json.loads(COUNTER.read_text())
    assert counter["diagnostic_fit_attempts"] == 12
    # R3 spent 0 scientific fits; later R9 may consume scientific attempts within cap.
    assert counter["scientific_fit_attempts"] <= counter["scientific_fit_cap"]
    assert counter["diagnostic_fit_attempts"] <= counter["diagnostic_fit_cap"]


def test_executor_hashes_match_live_files(report: dict) -> None:
    mod = _load_script()
    live = mod.hash_executor_path(ROOT)
    assert live["chain_sha256"] == report["executor_hashes"]["chain_sha256"]
    assert live["files"] == report["executor_hashes"]["files"]
    assert "src/p22/eval/s9_execute.py" in live["files"]
    assert "src/p22/training/loop.py" in live["files"]


def test_inventory_finds_s9_thread_and_set_all_seeds(report: dict) -> None:
    inv = report["seed_caller_inventory"]
    risk = inv["concurrent_risk"]
    assert risk["s9_default_workers"] == 2
    assert risk["uses_thread_pool_executor"] is True
    assert risk["interference_code_path_exists"] is True
    assert risk["interference_inferred_from_threading_alone"] is False
    files = inv["files"]
    assert "src/p22/eval/s9_execute.py" in files
    assert "src/p22/training/loop.py" in files
    assert "src/p22/eval/multiome_runner.py" in files
    loop_defs = files["src/p22/training/loop.py"]["definitions"]
    assert "defines_set_all_seeds" in loop_defs
    assert "defines_train_model" in loop_defs


def test_ledger_findings_review_and_frozen_spec(report: dict) -> None:
    ledger = report["ledger_resume_resources"]
    assert ledger["pre_dispatch_total_cap_check"] is True
    assert ledger["per_job_reserve_before_thread_submit"] is False
    assert ledger["hours_hard_stop_mid_batch"] is False
    assert ledger["failed_attempts_counted"] is True
    assert ledger["resume_skips_done_fit_ids"] is True
    assert ledger["checkpoint_history_epochs_persisted"] is False

    spec = json.loads(SPEC.read_text())
    review = json.loads(REVIEW.read_text())
    assert spec["committed_before_any_diagnostic_fit"] is True
    assert spec["attempt_cap"] == 12
    assert review["verdict"] == "PASS"
    assert review["authorizes_diagnostic_fits"] is True
    assert review["reviewer"]["self_certification"] is False
    from p22.eval.s7_ledger import sha256_file

    assert sha256_file(SPEC) == report["diagnostic_fit_spec"]["sha256"]
    assert sha256_file(SPEC) == review["spec_sha256_recomputed"]


def test_diagnostic_comparisons_and_finding(diag: dict, report: dict) -> None:
    comps = diag["comparisons"]
    assert comps["serial_J1_A1_vs_A2"]["state_sha_equal"] is True
    assert comps["serial_J2_A3_vs_A4"]["state_sha_equal"] is True
    assert diag["rng_interference_finding"] in {
        "NO_DIVERGENCE_OBSERVED_UNDER_SPEC",
        "CONFIRMED_CROSS_JOB_DIVERGENCE",
        "CONCURRENT_UNSTABLE_NONDETERMINISM",
        "SERIAL_NONDETERMINISM_OR_FIT_FAILURE",
    }
    assert report["rng_interference_finding"] == diag["rng_interference_finding"]
    assert str(diag["deliberate_fail_status"]).startswith("error")
    assert "skipped_already_done" in str(diag["resume_skip_status"])
    # Match does not authorize claiming races are impossible.
    assert "does_not_prove" in json.dumps(json.loads(SPEC.read_text())["success_criteria"])


def test_shared_s9_raw_untouched(report: dict, diag: dict) -> None:
    mod = _load_script()
    fp = mod._fingerprint_tree(S9_RAW)
    assert fp["tree_sha256"] == report["shared_s9_tree_sha256"]
    assert fp["tree_sha256"] == diag["shared_s9_tree_sha256"]
    assert diag["shared_raw_unchanged"] is True


def test_diagnostic_fits_refuse_without_review() -> None:
    mod = _load_script()
    with pytest.raises(SystemExit):
        mod.main(["--run-diagnostic-fits"])
