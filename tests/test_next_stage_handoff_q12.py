"""Q12 handoff: dispositions, INVALID closeout, resource counters, stop condition."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/next_stage_20260930"
)
HANDOFF = OUT / "HANDOFF.md"
VERIFICATION = OUT / "VERIFICATION.json"
EXECUTE = OUT / "execute.json"
TODO = ROOT / "tasks" / "todo.md"


def test_handoff_and_verification_exist_with_required_fields() -> None:
    assert HANDOFF.is_file()
    assert VERIFICATION.is_file()
    text = HANDOFF.read_text()
    assert "INVALID" in text
    assert "ENDPOINT_UNRESOLVED" in text
    assert "One smallest next action" in text
    assert "gnhf/execute-the-p22-data-146414" in text
    assert "04282f0a803cc40c5d40aa0a9a7c535a213e1560" in text
    assert "nn_s9_analytic_pairing_20260930" in text

    ver = json.loads(VERIFICATION.read_text())
    assert ver["task"] == "Q12"
    assert ver["disposition"] == "DONE"
    assert ver["scientific_result"] == "INVALID"
    assert ver["stop"]["checkpoint_d"] is True
    assert ver["resources"]["attempted_fits"] == 49
    assert ver["resources"]["within_synthetic_cap"] is True
    assert ver["resources"]["real_pilot_fits"] == 0
    assert ver["reviewer"]["self_certification"] is False
    assert ver["reviewer"]["q9_verdict"] == "PASS"


def test_all_q_task_dispositions_recorded() -> None:
    ver = json.loads(VERIFICATION.read_text())
    d = ver["task_dispositions"]
    for key in [
        "Q0",
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "Q5",
        "Q6",
        "Q7",
        "Q8",
        "Q9",
        "Q10",
        "Q11a",
        "Q11b",
        "Q11c",
        "Q12",
        "Checkpoint_D",
    ]:
        assert key in d, key
    assert d["Q10"]["label"] == "INVALID"
    assert d["Q11a"]["status"] == "BLOCKED"
    assert d["Q11b"]["status"] == "BLOCKED"
    assert d["Q11c"]["status"] == "BLOCKED"
    assert d["Q12"]["status"] == "DONE"
    assert d["Q2"]["label"] == "ENDPOINT_UNRESOLVED"
    assert d["Checkpoint_D"]["stop_condition_met"] is True


def test_scientific_invariants_preserved() -> None:
    ver = json.loads(VERIFICATION.read_text())
    inv = ver["scientific_invariants"]
    assert inv["primary"] == "B_NULL"
    assert inv["s7_v1"] == "INVALID"
    assert inv["s7_v2"] == "INVALID"
    assert inv["prior_s8"] == "NO FIT"
    assert inv["s9_selected_experiment"] == "INVALID"
    assert inv["power"] == "POWER_UNESTABLISHED"
    assert inv["study"] == "STUDY_PARTIAL"
    exe = json.loads(EXECUTE.read_text())
    assert exe["disposition"] == "INVALID"
    assert exe["research_fits_executed"] == 49


def test_todo_marks_q12_and_checkpoint_d() -> None:
    text = TODO.read_text()
    assert "Q12:" in text
    # Q12 and Checkpoint D should be checked after closeout packaging.
    assert "- [x] Q12:" in text
    assert "- [x] Checkpoint D:" in text
    assert "`BLOCKED`" in text
    assert "HANDOFF.md" in text
    assert "VERIFICATION.json" in text


def test_fresh_verification_commands_recorded() -> None:
    ver = json.loads(VERIFICATION.read_text())
    cmds = {c["id"]: c for c in ver["commands"]}
    assert cmds["focused_pytest_q1_q10"]["exit_code"] == 0
    assert cmds["focused_pytest_q1_q10"]["passed"] == 55
    assert cmds["focused_pytest_q1_q12"]["exit_code"] == 0
    assert cmds["focused_pytest_q1_q12"]["passed"] == 60
    assert cmds["s9_replay_skip_fits"]["exit_code"] == 0
    assert cmds["git_diff_check"]["exit_code"] == 0
    assert cmds["ruff_owned_paths"]["exit_code"] == 0
    assert cmds["make_lint_worktree"]["inherited_failure"] is True
    assert "do not reuse prior iteration tallies" in cmds["focused_pytest_q1_q10"]["note"]
