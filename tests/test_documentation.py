"""Documentation contracts for the synthetic-only handoff.

These tests only read markdown files. They check that a reviewer can find the
donor-first order, train-only transforms, baselines, five-seed reporting,
interventions, Tasic boundary, approval blocker, limitations, commands, and
generated-output location without reconstructing meeting context.
"""

from __future__ import annotations

import json

import p22

ROOT = p22.REPO_ROOT

REQUIRED_FILES = (
    "README.md",
    "DATA_CARD.md",
    "MODEL_CARD.md",
    "HANDOFF.md",
    "docs/interim_methods_protocol.md",
    "docs/decision_log.md",
    "docs/scale_benchmark.md",
    "notebooks/implementation/10_handoff.ipynb",
    "notebooks/scale/11_scale_benchmark.ipynb",
)


def read(relative: str) -> str:
    path = ROOT / relative
    assert path.is_file(), f"missing {relative}"
    return path.read_text(encoding="utf-8")


def test_every_handoff_document_exists():
    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    assert not missing, missing


def test_readme_states_blocked_approval_and_local_commands():
    text = read("README.md").lower()
    assert "blocked" in text
    assert "professor fang" in text
    assert "make verify" in text
    assert "reports/generated" in text
    assert "synthetic" in text
    assert "awaiting_professor_approval" in text


def test_data_card_states_no_real_matrix_and_donor_split():
    text = read("DATA_CARD.md").lower()
    assert "none" in text
    assert "donor" in text
    assert "train" in text and "only" in text
    assert "legacy" in text
    assert "unknown" in text


def test_model_card_lists_six_baselines_and_intervention_language():
    text = read("MODEL_CARD.md").lower()
    for name in (
        "logistic regression",
        "mlp",
        "concatenation",
        "gated",
        "routing",
        "intervention",
    ):
        assert name in text, name
    assert "not causal" in text or "not explanations" in text


def test_methods_protocol_records_fixed_order_and_stop_rules():
    text = read("docs/interim_methods_protocol.md").lower()
    assert "donor" in text
    assert "train" in text
    assert "validation" in text
    assert "test" in text
    assert "five seed" in text or "five-seed" in text
    assert "stop" in text
    assert "professor fang" in text


def test_decision_log_has_open_approval_item():
    text = read("docs/decision_log.md").lower()
    assert "professor fang" in text
    assert "pending" in text
    assert "blocked" in text
    assert "tasic" in text


def test_handoff_names_next_action_and_confirms_no_condition_data():
    text = read("HANDOFF.md")
    lowered = text.lower()
    assert "awaiting_professor_approval" in lowered
    assert "professor fang" in lowered
    assert "none" in lowered
    assert "make verify" in lowered
    assert "reports/generated" in lowered
    assert p22.approval_blocked()


def test_scale_document_preserves_synthetic_boundary():
    text = read("docs/scale_benchmark.md").lower()
    assert "synthetic" in text
    assert "engineering evidence" in text
    assert "not evidence" in text
    assert "professor fang" in text
    assert "32,000" in text


def test_approvals_remain_blocked_after_documentation():
    approvals = p22.load_approvals()
    assert approvals["approval_state"] == "blocked"
    assert approvals["approver"] == "Professor Fang"
    plan_state = json.loads((ROOT / "plan" / "state.json").read_text())
    assert plan_state["approval_state"] == "blocked"
    assert plan_state["next_action"] in {"C13", "awaiting_professor_approval"}
