"""Focused checks for S7 exit handoff labels and S7_RESULT.md writer.

No H5AD loads, no model fits — stage-label combinations only.
"""

from __future__ import annotations

from pathlib import Path

from p22.eval.s7_confirmation import (
    CONFIRM_INCOMPLETE,
    CONFIRM_NEGATIVE,
    CONFIRM_RELIABLE,
    CONFIRM_SKIPPED,
)
from p22.eval.s7_handoff import (
    BIOLOGICAL_POWER,
    FINISHED_PRIMARY,
    LABEL_CA_FAVOURED_CONTROL,
    LABEL_CONTROL_NEGATIVE,
    LABEL_INCOMPLETE,
    LABEL_INVALID,
    STUDY_STATUS,
    build_s7_result_payload,
    finalize_scientific_label,
    render_s7_result_md,
    write_s7_result,
)
from p22.eval.s7_pairing import PC_FAIL, PC_IDENTITY_FAIL, PC_INCOMPLETE, PC_PASS
from p22.eval.s7_screen import (
    SCREEN_CA_FAVOURED,
    SCREEN_INCOMPLETE,
    SCREEN_INVALID,
    SCREEN_NEGATIVE,
)


def test_favourable_control_requires_screen_pc_and_reliable_confirm() -> None:
    result = finalize_scientific_label(
        screen_label=SCREEN_CA_FAVOURED,
        pc_label=PC_PASS,
        confirm_label=CONFIRM_RELIABLE,
    )
    assert result["scientific_label"] == LABEL_CA_FAVOURED_CONTROL
    assert result["biological_power"] == BIOLOGICAL_POWER
    assert result["finished_primary"] == FINISHED_PRIMARY
    assert result["study"] == STUDY_STATUS
    assert result["confirmation_required"] is True
    assert result["eligible_for_confirmation"] is True


def test_screen_negative_is_complete_control_negative() -> None:
    result = finalize_scientific_label(
        screen_label=SCREEN_NEGATIVE,
        pc_label=PC_FAIL,
        confirm_label=CONFIRM_SKIPPED,
    )
    assert result["scientific_label"] == LABEL_CONTROL_NEGATIVE
    assert result["confirmation_required"] is False


def test_null_marginal_failure_is_invalid() -> None:
    result = finalize_scientific_label(
        screen_label=SCREEN_INVALID,
        pc_label=None,
        confirm_label=CONFIRM_SKIPPED,
    )
    assert result["scientific_label"] == LABEL_INVALID


def test_pc_pass_without_confirmation_is_incomplete() -> None:
    missing = finalize_scientific_label(
        screen_label=SCREEN_CA_FAVOURED,
        pc_label=PC_PASS,
        confirm_label=None,
    )
    assert missing["scientific_label"] == LABEL_INCOMPLETE

    skipped = finalize_scientific_label(
        screen_label=SCREEN_CA_FAVOURED,
        pc_label=PC_PASS,
        confirm_label=CONFIRM_SKIPPED,
    )
    assert skipped["scientific_label"] == LABEL_INCOMPLETE

    incomplete = finalize_scientific_label(
        screen_label=SCREEN_CA_FAVOURED,
        pc_label=PC_PASS,
        confirm_label=CONFIRM_INCOMPLETE,
    )
    assert incomplete["scientific_label"] == LABEL_INCOMPLETE


def test_pc_failure_after_favoured_screen_is_negative() -> None:
    for pc in (PC_FAIL, PC_IDENTITY_FAIL):
        result = finalize_scientific_label(
            screen_label=SCREEN_CA_FAVOURED,
            pc_label=pc,
            confirm_label=CONFIRM_SKIPPED,
        )
        assert result["scientific_label"] == LABEL_CONTROL_NEGATIVE


def test_confirm_negative_after_pc_pass_is_control_negative() -> None:
    result = finalize_scientific_label(
        screen_label=SCREEN_CA_FAVOURED,
        pc_label=PC_PASS,
        confirm_label=CONFIRM_NEGATIVE,
    )
    assert result["scientific_label"] == LABEL_CONTROL_NEGATIVE


def test_run_invalid_overrides_stages() -> None:
    result = finalize_scientific_label(
        screen_label=SCREEN_CA_FAVOURED,
        pc_label=PC_PASS,
        confirm_label=CONFIRM_RELIABLE,
        run_invalid=True,
        run_invalid_reason="resume hash refusal",
    )
    assert result["scientific_label"] == LABEL_INVALID
    assert "resume hash" in result["reason"]


def test_screen_incomplete_and_pc_incomplete_paths() -> None:
    screen = finalize_scientific_label(
        screen_label=SCREEN_INCOMPLETE,
        pc_label=None,
        confirm_label=None,
    )
    assert screen["scientific_label"] == LABEL_INCOMPLETE

    pc = finalize_scientific_label(
        screen_label=SCREEN_CA_FAVOURED,
        pc_label=PC_INCOMPLETE,
        confirm_label=None,
    )
    assert pc["scientific_label"] == LABEL_INCOMPLETE


def test_write_s7_result_markdown_and_json(tmp_path: Path) -> None:
    finalize = finalize_scientific_label(
        screen_label=SCREEN_NEGATIVE,
        pc_label=None,
        confirm_label=CONFIRM_SKIPPED,
    )
    payload = build_s7_result_payload(
        finalize=finalize,
        provenance={
            "spec_sha256": "abc",
            "fingerprint": "fp1",
            "source_sha256": {"s7_handoff.py": "deadbeef"},
            "input_sha256": {"config": "cafebabe"},
        },
        screen={"screen_label": SCREEN_NEGATIVE, "eligible_for_pairing_pc": False},
        pairing_pc={},
        confirmation={"confirm_label": CONFIRM_SKIPPED},
        resources={"completed_fits": 105, "max_total_fits": 480},
        ledger_path="/tmp/ledger/fit_ledger.jsonl",
        checkpoint_root="/tmp/ledger/checkpoints",
    )
    paths = write_s7_result(tmp_path / "docs" / "nn_v2" / "s7", payload)
    md = paths["markdown"].read_text(encoding="utf-8")
    assert "`CONTROL_NEGATIVE`" in md
    assert BIOLOGICAL_POWER in md
    assert FINISHED_PRIMARY in md
    assert STUDY_STATUS in md
    assert "/tmp/ledger/fit_ledger.jsonl" in md
    assert "Biological advantage claimed: no" in md
    assert paths["json"].exists()
    assert payload["scientific_label"] == LABEL_CONTROL_NEGATIVE
    assert payload["claims"]["biological_advantage"] is False


def test_render_includes_all_runbook_fields() -> None:
    finalize = finalize_scientific_label(
        screen_label=SCREEN_CA_FAVOURED,
        pc_label=PC_PASS,
        confirm_label=CONFIRM_RELIABLE,
    )
    payload = build_s7_result_payload(finalize=finalize)
    text = render_s7_result_md(payload)
    assert LABEL_CA_FAVOURED_CONTROL in text
    assert "Protocol and provenance" in text
    assert "Claims boundary" in text
