"""Tests for report rendering.

The claim under test: a report keeps predictive performance, routing signals, and
intervention evidence in separate sections, states when a section was not measured, and
never omits the limitations.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import p22
from p22.reports.render import (
    NOT_MEASURED,
    SECTION_TITLES,
    render_comparison_table,
    render_run_report,
    write_run_report,
)
from p22.runs.config import RunConfig
from p22.runs.registry import RunRecord, data_fingerprint

CONFIG_PATH = p22.REPO_ROOT / "configs" / "toy_pilot.json"
COMMIT = "c" * 40


def make_config() -> RunConfig:
    return RunConfig.from_dict(json.loads(CONFIG_PATH.read_text()))


def make_record(**overrides) -> RunRecord:
    rng = np.random.default_rng(0)
    labels = rng.integers(0, 3, size=30)
    donors = np.repeat([f"donor_{index}" for index in range(6)], 5)
    arguments = {
        "config": make_config(),
        "model": "gated_fusion",
        "seeds": (0, 1, 2, 3, 4),
        "data_fingerprint": data_fingerprint(
            {"view_a": rng.normal(size=(30, 4)), "view_b": rng.normal(size=(30, 3))},
            labels,
            donors,
        ),
        "donor_counts": {"train": 4, "val": 1, "test": 1},
        "cell_counts": {"train": 20, "val": 5, "test": 5},
        "transform_metadata": {
            "kind": "standard_scaler",
            "fit_scope": "train cells only",
            "parameter_fingerprint": "d" * 64,
        },
        "metrics": {
            "accuracy": {
                "value": 0.812,
                "not_applicable": None,
                "interval": [0.71, 0.9],
                "unit": "donor",
                "n_valid": 400,
                "n_failed": 0,
            },
            "macro_ovr_auroc": {
                "value": None,
                "not_applicable": "class 2 absent from the test split",
                "unit": "donor",
            },
        },
        "evidence_labels": ("experimental result",),
        "git_commit": COMMIT,
        "created_at": "2026-07-27T00:00:00+00:00",
    }
    arguments.update(overrides)
    return RunRecord.create(**arguments)


class TestSectionStructure:
    def test_all_sections_appear_in_a_fixed_order(self):
        text = render_run_report(make_record())
        positions = [text.index(f"## {title}") for title in SECTION_TITLES]
        assert positions == sorted(positions)
        assert len(positions) == 6

    def test_report_is_titled_with_the_run_id(self):
        record = make_record()
        assert render_run_report(record).startswith(f"# Run report: {record.run_id}")

    def test_unmeasured_sections_say_so_instead_of_vanishing(self):
        text = render_run_report(make_record())
        assert text.count(NOT_MEASURED) == 2
        routing = _section(text, "Routing signals")
        interventions = _section(text, "Intervention evidence")
        assert routing.strip() == NOT_MEASURED
        assert interventions.strip() == NOT_MEASURED

    def test_routing_and_intervention_evidence_stay_out_of_the_performance_table(self):
        record = make_record(
            routing_signals={"mean_weight_view_a": 0.62, "mean_weight_view_b": 0.38},
            intervention_evidence={"clamp_view_a": {"accuracy_change": -0.14}},
        )
        text = render_run_report(record)
        performance = _section(text, "Predictive performance")
        assert "mean_weight_view_a" not in performance
        assert "clamp_view_a" not in performance
        assert "mean_weight_view_a" in _section(text, "Routing signals")
        assert "clamp_view_a" in _section(text, "Intervention evidence")

    def test_routing_section_warns_against_reading_weights_as_dependence(self):
        record = make_record(routing_signals={"mean_weight_view_a": 0.62})
        routing = _section(render_run_report(record), "Routing signals")
        assert "do not by themselves show" in routing


class TestProvenanceSection:
    def test_reviewer_can_read_commit_config_and_data_facts(self):
        record = make_record()
        provenance = _section(render_run_report(record), "Provenance")
        for expected in (
            record.git_commit,
            record.config_hash,
            record.data_fingerprint["sha256"],
            record.data_mode,
            record.approval_state,
            record.model,
            "train cells only",
            "donor",
        ):
            assert expected in provenance

    def test_counts_and_seeds_are_visible(self):
        record = make_record()
        provenance = _section(render_run_report(record), "Provenance")
        assert "train 4" in provenance and "test 1" in provenance
        assert "train 20" in provenance
        assert "0, 1, 2, 3, 4" in provenance


class TestPerformanceSection:
    def test_estimates_appear_with_interval_unit_and_replicate_counts(self):
        performance = _section(render_run_report(make_record()), "Predictive performance")
        assert "0.8120" in performance
        assert "[0.7100, 0.9000]" in performance
        assert "donor" in performance
        assert "400 valid / 0 failed" in performance

    def test_inapplicable_metric_shows_its_reason_not_a_number(self):
        performance = _section(render_run_report(make_record()), "Predictive performance")
        assert "not applicable: class 2 absent from the test split" in performance
        assert "nan" not in performance.lower()


class TestLimitationsAndApproval:
    def test_every_configured_limitation_is_listed(self):
        record = make_record()
        limitations = _section(render_run_report(record), "Limitations")
        for item in record.limitations:
            assert item in limitations

    def test_blocked_approval_is_stated_with_its_consequence(self):
        approval = _section(render_run_report(make_record()), "Approval and next step")
        assert "blocked" in approval
        assert "approval is required" in approval.lower()

    def test_notes_reach_the_approval_section(self):
        record = make_record(notes=("Rerun after the professor reviews the split protocol.",))
        approval = _section(render_run_report(record), "Approval and next step")
        assert "Rerun after the professor" in approval

    def test_report_makes_no_causal_or_superiority_claim(self):
        text = render_run_report(
            make_record(routing_signals={"mean_weight_view_a": 0.6}),
        ).lower()
        for phrase in ("proves", "causes", "because the model", "outperforms", "state of the art"):
            assert phrase not in text


class TestComparisonTable:
    def test_lists_one_row_per_run_with_intervals(self):
        first = make_record(model="concat_fusion")
        second = make_record(model="gated_fusion")
        table = render_comparison_table([first, second])
        assert "concat_fusion" in table
        assert "gated_fusion" in table
        assert "[0.7100, 0.9000]" in table

    def test_states_that_overlapping_intervals_settle_nothing(self):
        table = render_comparison_table([make_record()])
        assert "Overlapping intervals" in table
        assert "no claim that any model is better" in table

    def test_missing_metric_is_shown_as_absent(self):
        table = render_comparison_table([make_record()], metric="multiclass_ece")
        assert "-" in table

    def test_refuses_an_empty_record_list(self):
        with pytest.raises(ValueError, match="at least one record"):
            render_comparison_table([])


class TestWriting:
    def test_writes_markdown_under_the_generated_tree(self, tmp_path: Path):
        record = make_record()
        target = write_run_report(record, tmp_path / "generated" / "reports")
        assert target.is_file()
        assert target.name == f"{record.run_id}.md"
        assert target.read_text() == render_run_report(record)

    def test_refuses_to_write_into_the_source_tree(self, tmp_path: Path):
        with pytest.raises(ValueError, match="generated"):
            write_run_report(make_record(), tmp_path / "docs")

    def test_default_location_is_ignored_by_git(self):
        from p22.reports.render import REPORTS_ROOT

        assert "generated" in REPORTS_ROOT.parts
        ignore = (p22.REPO_ROOT / ".gitignore").read_text()
        assert "/reports/generated/" in ignore


def _section(text: str, title: str) -> str:
    """Return the body of one section, exclusive of the next heading."""
    start = text.index(f"## {title}") + len(f"## {title}")
    remainder = text[start:]
    next_heading = remainder.find("\n## ")
    return remainder if next_heading == -1 else remainder[:next_heading]
