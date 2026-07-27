"""Tests for the plan guard and the plan records it reads."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = REPO_ROOT / "scripts" / "plan_guard.py"
SCIENTIFIC_IMPORTS = ("numpy", "pandas", "sklearn", "torch", "anndata", "scipy")
EXPECTED_SUBJECTS = [
    "chore: add guarded package and test scaffold",
    "docs: preserve legacy Tasic evidence boundary",
    "test: add deterministic synthetic multimodal fixtures",
    "feat: add donor-held-out split validation",
    "feat: add train-only preprocessing contracts",
    "feat: add metadata preflight schema and reporter",
    "feat: extract modality-agnostic model components",
    "feat: add benchmark metrics and donor bootstrap",
    "feat: add reproducible run registry and reports",
    "feat: add deterministic synthetic benchmark runner",
    "feat: add routing faithfulness interventions",
    "test: add end-to-end plan compliance workflow",
    "docs: finalize synthetic-only implementation handoff",
]


def load_guard():
    """Import the guard by path so it is exercised exactly as the Makefile runs it."""
    name = "plan_guard_under_test"
    spec = importlib.util.spec_from_file_location(name, GUARD_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def guard():
    return load_guard()


@pytest.fixture(scope="module")
def plan(guard):
    return guard.load_json(REPO_ROOT / "plan" / "implementation_plan.json")


@pytest.fixture(scope="module")
def state(guard):
    return guard.load_json(REPO_ROOT / "plan" / "state.json")


@pytest.fixture(scope="module")
def approvals(guard):
    return guard.load_json(REPO_ROOT / "plan" / "approvals.json")


def test_guard_source_has_no_scientific_imports():
    source = GUARD_PATH.read_text(encoding="utf-8")
    for name in SCIENTIFIC_IMPORTS:
        assert not re.search(rf"^\s*(import|from)\s+{name}\b", source, re.MULTILINE)


def test_plan_matches_handoff_subjects(plan):
    assert [step["subject"] for step in plan["steps"]] == EXPECTED_SUBJECTS
    assert [step["id"] for step in plan["steps"]] == [f"C{i:02d}" for i in range(1, 14)]


def test_every_step_declares_notebook_and_paths(plan):
    for step in plan["steps"]:
        assert step["notebook"].startswith("notebooks/implementation/")
        assert step["allowed_paths"], step["id"]
        if step["id"] != "C01":
            assert "plan/state.json" in step["allowed_paths"], step["id"]


def test_state_covers_every_step(plan, state):
    assert set(state["steps"]) == {step["id"] for step in plan["steps"]}
    assert state["branch"] == plan["branch"]
    assert re.fullmatch(r"[0-9a-f]{40}", state["base_commit"])


def test_approval_starts_blocked(approvals):
    assert approvals["approval_state"] == "blocked"
    assert "approved real data" in approvals["blocked_data_modes"]
    assert approvals["approver"]


def test_branch_check(guard):
    assert guard.check_branch("develop", "develop") == []
    assert guard.check_branch("main", "develop")


def test_step_order_rejects_skipped_step(guard, plan):
    state = {"steps": {sid: {"status": "pending"} for sid in guard.step_ids(plan)}}
    assert guard.check_step_order(plan, state, "C01", "worktree") == []
    problems = guard.check_step_order(plan, state, "C03", "worktree")
    assert any("C01" in message for message in problems)
    assert any("C02" in message for message in problems)


def test_step_order_requires_completion_before_staged_phase(guard, plan):
    state = {"steps": {sid: {"status": "pending"} for sid in guard.step_ids(plan)}}
    assert guard.check_step_order(plan, state, "C01", "staged")
    state["steps"]["C01"]["status"] = "complete"
    assert guard.check_step_order(plan, state, "C01", "staged") == []
    assert guard.check_step_order(plan, state, "C01", "worktree")


def test_path_allowlist(guard, plan):
    allowed = guard.find_step(plan, "C01")["allowed_paths"]
    assert guard.check_paths(["pyproject.toml", "Makefile"], allowed) == []
    problems = guard.check_paths(["experiments/run_tasic2018_pipeline.py"], allowed)
    assert len(problems) == 1


def test_real_data_paths_rejected(guard, approvals):
    patterns = approvals["real_data_path_patterns"]
    assert guard.check_real_data_paths(["src/p22/__init__.py"], patterns) == []
    assert guard.check_real_data_paths(["tests/fixtures/tiny.h5ad"], patterns)
    assert guard.check_real_data_paths(["data/matrix.csv"], patterns)
    assert guard.check_real_data_paths(["data/README.md"], patterns) == []


def test_network_calls_rejected(guard, approvals):
    patterns = approvals["network_call_patterns"]
    clean = {"src/p22/x.py": "import json\n"}
    dirty = {"src/p22/x.py": f"fetch = {patterns[0]}\n"}
    assert guard.check_network_calls(clean, patterns) == []
    assert guard.check_network_calls(dirty, patterns)


def test_condition_terms_rejected(guard, approvals):
    terms = approvals["condition_terms"]
    assert guard.check_condition_terms({"a.py": "view_a routing gate\n"}, terms) == []
    probe = f"cohort = load_cohort('{terms[0]}')\n"
    assert guard.check_condition_terms({"a.py": probe}, terms)


def test_data_mode_rejected_while_blocked(guard, approvals):
    allowed = approvals["allowed_data_modes"]
    assert guard.check_data_mode({"c.json": {"data_mode": "synthetic"}}, allowed) == []
    assert guard.check_data_mode({"c.json": {"data_mode": "approved real data"}}, allowed)
    assert guard.check_data_mode({"c.json": {"seed": 0}}, allowed) == []


def test_agent_trailers_rejected(guard):
    assert guard.check_agent_trailers("chore: add guarded package and test scaffold") == []
    assert guard.check_agent_trailers("feat: x\n\nCo-Authored-By: Someone <a@b.c>\n")
    assert guard.check_agent_trailers("feat: x\n\nGenerated with Claude\n")


def test_recorded_commits_must_be_in_history(guard):
    state = {
        "steps": {
            "C01": {"status": "complete", "commit": "a" * 40},
            "C02": {"status": "pending", "commit": None},
        }
    }
    assert guard.check_recorded_commits(state, lambda commit: True) == []
    problems = guard.check_recorded_commits(state, lambda commit: False)
    assert len(problems) == 1 and "C01" in problems[0]


def test_commit_subject_must_match_plan(guard, plan):
    subject = guard.find_step(plan, "C01")["subject"]
    assert guard.check_commit_subject(subject, subject) == []
    assert guard.check_commit_subject("wip", subject)


def test_status_porcelain_parsing(guard):
    porcelain = "?? plan/state.json\n M Makefile\nR  old.py -> src/p22/new.py\n"
    assert guard.parse_status_paths(porcelain) == [
        "Makefile",
        "plan/state.json",
        "src/p22/new.py",
    ]


def test_report_exit_code(guard):
    report = guard.Report()
    report.extend_failures([], "fine")
    assert report.exit_code == 0
    report.extend_failures(["broken"], "fine")
    assert report.exit_code == 1


def test_plan_json_files_are_formatted_consistently():
    for name in ("implementation_plan.json", "state.json", "approvals.json"):
        path = REPO_ROOT / "plan" / name
        text = path.read_text(encoding="utf-8")
        assert json.loads(text) is not None
        assert text.endswith("\n")
