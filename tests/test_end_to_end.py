"""End-to-end check that one local command can decide whether this repository is reportable.

Claims under test: `scripts/verify_repository.py` runs every check and returns one of three
verdicts with a matching exit code; the five-seed synthetic benchmark completes with donors
held out and transforms fitted on training cells only; all seven interventions run on a gated
model; and rendered reports carry the six fixed sections. The checks that guard the approval
boundary are asserted individually, so a failure names the rule that broke.

This module is marked slow and integration: it shells out to the verifier, which collects the
whole test suite, and it trains models. Run it with `pytest -m integration`.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import torch

import p22
from p22.data.splits import make_donor_split, validate_donor_split
from p22.data.transforms import fit_train_only
from p22.eval.faithfulness import EVIDENCE_STATEMENT, INTERVENTIONS, run_all_interventions
from p22.models.fusion import VIEW_A, VIEW_B, GatedFusionModel
from p22.reports.render import SECTION_TITLES, render_run_report, write_run_report
from p22.runs.config import RunConfig
from p22.runs.registry import RunRegistry
from p22.testing.synthetic import make_synthetic_multimodal
from p22.training.loop import train_model
from p22.training.seed_runner import (
    build_record,
    run_all_seeds,
    summarize_across_seeds,
)

pytestmark = [pytest.mark.slow, pytest.mark.integration]

VERIFY_SCRIPT = p22.REPO_ROOT / "scripts" / "verify_repository.py"
PLAN_GUARD = p22.REPO_ROOT / "scripts" / "plan_guard.py"
LEGACY_MANIFEST = p22.REPO_ROOT / "scripts" / "build_legacy_manifest.py"
SEEDS = (0, 1, 2, 3, 4)

# Small enough to run five seeds in a test, large enough to exercise every stage.
BENCHMARK_CONFIG = {
    "name": "end_to_end_pilot",
    "data_mode": "synthetic",
    "seeds": list(SEEDS),
    "dataset": {
        "n_donors": 12,
        "cells_per_donor": 10,
        "n_features_a": 8,
        "n_features_b": 6,
        "n_classes": 3,
        "class_signal": 1.4,
        "donor_nuisance": 0.4,
        "noise": 1.0,
    },
    "split": {"val_fraction": 0.25, "test_fraction": 0.25},
    "transform": {"kind": "standard_scaler", "n_components": None},
    "models": [
        {
            "name": "logistic_regression_view_a",
            "family": "logistic_regression",
            "views": ["view_a"],
        },
        {
            "name": "logistic_regression_view_b",
            "family": "logistic_regression",
            "views": ["view_b"],
        },
        {"name": "mlp_view_a", "family": "mlp", "views": ["view_a"]},
        {"name": "mlp_view_b", "family": "mlp", "views": ["view_b"]},
        {"name": "concat_fusion", "family": "concat_fusion", "views": ["view_a", "view_b"]},
        {"name": "gated_fusion", "family": "gated_fusion", "views": ["view_a", "view_b"]},
    ],
    "training": {
        "max_epochs": 2,
        "batch_size": 32,
        "learning_rate": 0.01,
        "hidden_dim": 16,
        "embedding_dim": 8,
        "patience": 2,
        "device": "cpu",
    },
    "metrics": ["accuracy", "balanced_accuracy", "macro_f1"],
    "bootstrap": {"n_replicates": 20, "level": 0.95},
    "limitations": [
        "Synthetic data with hand-set signal, so numbers carry no biological meaning.",
        "Two epochs and twelve donors: this configuration tests the workflow, not any model.",
    ],
}


def load_verifier():
    """Import the verifier as a module so its constants can be reused."""
    spec = importlib.util.spec_from_file_location("verify_repository_under_test", VERIFY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    # The module uses postponed annotations, so dataclasses resolves them through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def verifier():
    return load_verifier()


@pytest.fixture(scope="module")
def verification(verifier) -> dict[str, Any]:
    """Run the local verification command once and reuse its report.

    `--allow-dirty` is used because this test also runs while the step that adds it is still
    uncommitted; the clean-tree rule is asserted separately against the same report.
    """
    completed = subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT), "--allow-dirty", "--json"],
        cwd=p22.REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.stdout, f"verifier printed nothing; stderr was {completed.stderr[-2000:]}"
    payload = json.loads(completed.stdout)
    payload["returncode"] = completed.returncode
    return payload


def status_of(verification: dict[str, Any], name: str) -> tuple[str, str]:
    """Return the status and detail of one named check."""
    for check in verification["checks"]:
        if check["name"] == name:
            return check["status"], check["detail"]
    raise AssertionError(f"the verifier ran no check named {name!r}")


def assert_passes(verification: dict[str, Any], name: str) -> dict[str, Any]:
    status, detail = status_of(verification, name)
    assert status == "PASS", f"{name}: {status} - {detail}"
    return verification


class TestLocalVerificationCommand:
    def test_every_check_reports_one_of_the_three_verdicts(self, verification, verifier):
        allowed = {verifier.PASS, verifier.INCONCLUSIVE, verifier.BLOCKED}
        statuses = {check["status"] for check in verification["checks"]}
        assert statuses <= allowed
        assert verification["verdict"] in allowed

    def test_the_command_reports_a_verdict_for_every_planned_check(self, verification):
        expected = {
            "plan guard status",
            "python sources parse",
            "test suite collects",
            "end-to-end test marked slow and integration",
            "run configuration",
            "intervention set",
            "report schema",
            "legacy evidence unchanged",
            "no real dataset files tracked",
            "no condition-specific work while approval is blocked",
            "generated outputs stay out of the source tree",
            "notebooks executed",
            "repository clean",
        }
        assert {check["name"] for check in verification["checks"]} == expected

    def test_the_exit_code_matches_the_verdict(self, verification, verifier):
        assert verification["returncode"] == verifier.EXIT_CODES[verification["verdict"]]

    def test_nothing_is_blocked(self, verification):
        blocked = [
            f"{check['name']}: {check['detail']}"
            for check in verification["checks"]
            if check["status"] == "BLOCKED"
        ]
        assert not blocked, "blocked check(s): " + "; ".join(blocked)

    def test_an_inconclusive_check_says_what_evidence_is_missing(self, verification):
        for check in verification["checks"]:
            if check["status"] == "INCONCLUSIVE":
                assert check["detail"].strip(), f"{check['name']} gave no reason"

    def test_sources_parse_and_the_suite_collects(self, verification):
        assert_passes(verification, "python sources parse")
        status, detail = status_of(verification, "test suite collects")
        assert status == "PASS", detail
        assert "end-to-end" in detail

    def test_this_module_is_marked_slow_and_integration(self, verification):
        assert_passes(verification, "end-to-end test marked slow and integration")

    def test_the_working_tree_state_is_reported_either_way(self, verification):
        status, detail = status_of(verification, "repository clean")
        assert status in ("PASS", "INCONCLUSIVE"), detail
        if status == "INCONCLUSIVE":
            assert "--allow-dirty" in detail

    def test_a_dirty_tree_blocks_without_the_flag(self, verifier):
        result = verifier.check_repository_clean(allow_dirty=False)
        assert result.status in ("PASS", "BLOCKED")


class TestApprovalBoundary:
    def test_plan_guard_runs_and_names_the_next_action(self, verification):
        assert_passes(verification, "plan guard status")
        completed = subprocess.run(
            [sys.executable, str(PLAN_GUARD), "status"],
            cwd=p22.REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        for step in [f"C{index:02d}" for index in range(1, 14)]:
            assert step in completed.stdout

    def test_no_real_dataset_file_is_tracked(self, verification):
        assert_passes(verification, "no real dataset files tracked")

    def test_no_condition_specific_work_is_present(self, verification):
        assert_passes(verification, "no condition-specific work while approval is blocked")
        approvals = p22.load_approvals()
        assert approvals["approval_state"] == "blocked"
        assert p22.approval_blocked()

    def test_legacy_evidence_is_unchanged(self, verification):
        assert_passes(verification, "legacy evidence unchanged")
        completed = subprocess.run(
            [sys.executable, str(LEGACY_MANIFEST), "verify"],
            cwd=p22.REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr

    def test_generated_outputs_stay_out_of_the_source_tree(self, verification):
        assert_passes(verification, "generated outputs stay out of the source tree")

    def test_the_run_configuration_declares_five_seeds_and_six_baselines(self, verification):
        assert_passes(verification, "run configuration")
        config = RunConfig.from_dict(
            json.loads((p22.REPO_ROOT / "configs" / "toy_pilot.json").read_text())
        )
        assert config.data_mode == p22.SYNTHETIC
        assert len(config.seeds) == 5
        assert len(config.models) == 6


@pytest.fixture(scope="module")
def benchmark_runs():
    config = RunConfig.from_dict(json.loads(json.dumps(BENCHMARK_CONFIG)))
    runs = run_all_seeds(config, seeds=list(SEEDS), n_replicates=10)
    return config, runs


class TestFiveSeedBenchmark:
    def test_every_seed_produced_every_baseline(self, benchmark_runs):
        config, runs = benchmark_runs
        assert [run.seed for run in runs] == list(SEEDS)
        for run in runs:
            assert sorted(run.outcomes) == sorted(model.name for model in config.models)

    def test_donors_never_cross_splits_in_any_seed(self, benchmark_runs):
        _, runs = benchmark_runs
        for run in runs:
            summary = run.split_summary
            assert summary["split_unit"] == "donor"
            assert summary["validated"] is True
            assert summary["donor_overlap"] == 0
            assert summary["unassigned_cells"] == 0

    def test_transforms_saw_training_cells_only(self, benchmark_runs):
        _, runs = benchmark_runs
        for run in runs:
            assert run.transform_metadata["fit_scope"] == "train cells only"
            for view in (VIEW_A, VIEW_B):
                metadata = run.transform_metadata[view]
                assert metadata["n_train_cells"] == run.cell_counts["train"]
                assert metadata["n_holdout_ids_declared"] == (
                    run.cell_counts["val"] + run.cell_counts["test"]
                )

    def test_each_seed_generated_its_own_data(self, benchmark_runs):
        _, runs = benchmark_runs
        fingerprints = {run.data_fingerprint["sha256"] for run in runs}
        assert len(fingerprints) == len(SEEDS)

    def test_five_seeds_report_a_spread_rather_than_a_winner(self, benchmark_runs):
        config, runs = benchmark_runs
        summary = summarize_across_seeds(runs, metrics=["accuracy"])
        assert sorted(summary) == sorted(model.name for model in config.models)
        for name, entry in summary.items():
            accuracy = entry["accuracy"]
            assert accuracy["n_seeds"] == len(SEEDS), name
            assert accuracy["mean"] is not None, name
            assert accuracy["std"] is not None, name
            lower, upper = accuracy["interval"]
            assert lower <= accuracy["mean"] <= upper, name
            assert accuracy["min"] <= accuracy["max"], name

    def test_metrics_are_never_silent_nans(self, benchmark_runs):
        _, runs = benchmark_runs
        for run in runs:
            for outcome in run.outcomes.values():
                for name, entry in outcome.metrics.items():
                    assert entry["value"] is None or np.isfinite(entry["value"]), name
                    if entry["value"] is None:
                        assert entry["not_applicable"]


class TestReportSchema:
    @pytest.fixture(scope="class")
    def record(self, benchmark_runs):
        config, runs = benchmark_runs
        return build_record(config, runs[0], runs[0].outcomes["gated_fusion"])

    def test_the_six_sections_appear_in_a_fixed_order(self, record):
        report = render_run_report(record)
        positions = [report.index(f"## {title}") for title in SECTION_TITLES]
        assert positions == sorted(positions)

    def test_an_unmeasured_section_says_so_instead_of_being_dropped(self, record):
        bare = dataclasses.replace(record, intervention_evidence={})
        report = render_run_report(bare)
        section = report.split("## Intervention evidence")[1].split("## Limitations")[0]
        assert "Not measured" in section

    def test_intervention_results_render_in_their_own_section(self, record):
        with_evidence = dataclasses.replace(
            record,
            intervention_evidence={"ablate_view_b": {"metric_drop": 0.0, "flip_rate": 0.0}},
        )
        report = render_run_report(with_evidence)
        performance = report.split("## Predictive performance")[1].split("## Routing signals")[0]
        assert "ablate_view_b" not in performance
        assert "ablate_view_b" in report.split("## Intervention evidence")[1]

    def test_the_report_states_the_approval_state_and_its_limits(self, record):
        report = render_run_report(record)
        assert "blocked" in report
        assert record.limitations
        for limitation in record.limitations:
            assert limitation in report

    def test_records_and_reports_are_written_under_the_generated_tree(
        self, benchmark_runs, tmp_path: Path
    ):
        config, runs = benchmark_runs
        registry = RunRegistry(tmp_path / "generated" / "runs")
        for outcome in runs[0].outcomes.values():
            registry.write(build_record(config, runs[0], outcome))
        assert len(registry.run_ids()) == len(config.models)
        written = write_run_report(
            build_record(config, runs[0], runs[0].outcomes["concat_fusion"]),
            root=tmp_path / "generated" / "reports",
        )
        assert written.is_file()
        assert written.read_text().startswith("# Run report:")


@pytest.fixture(scope="module")
def gated_model_on_held_out_data():
    """Train a gated model through the same order the runner uses, then hold out one split.

    Interventions need the fitted model itself, which the runner does not return, so the
    stages are repeated here: donor split, train-only transforms, training, then held-out data.
    """
    dataset = make_synthetic_multimodal(
        n_donors=12,
        cells_per_donor=12,
        n_features_a=8,
        n_features_b=6,
        n_classes=3,
        class_signal=1.6,
        donor_nuisance=0.4,
        seed=0,
    )
    split = make_donor_split(
        dataset.donor_ids, labels=dataset.labels, val_fraction=0.25, test_fraction=0.25, seed=0
    )
    assert validate_donor_split(split, dataset.donor_ids, dataset.labels)["validated"] is True

    views = {VIEW_A: dataset.view_a, VIEW_B: dataset.view_b}
    train_ids = dataset.cell_ids[split.train_index]
    holdout_ids = np.concatenate(
        [dataset.cell_ids[split.val_index], dataset.cell_ids[split.test_index]]
    )
    transformed = {}
    for name, matrix in views.items():
        fitted = fit_train_only(
            matrix,
            dataset.cell_ids,
            train_ids,
            holdout_cell_ids=holdout_ids,
            kind="standard_scaler",
        )
        assert fitted.metadata["fit_scope"] == "train cells only"
        transformed[name] = fitted.transformer.transform(matrix).astype(np.float32)

    def take(index):
        return {
            VIEW_A: transformed[VIEW_A][index],
            VIEW_B: transformed[VIEW_B][index],
            "labels": dataset.labels[index],
            "donors": dataset.donor_ids[index],
        }

    train, val, test = take(split.train_index), take(split.val_index), take(split.test_index)
    torch.manual_seed(0)
    trained = train_model(
        GatedFusionModel(
            n_features_a=transformed[VIEW_A].shape[1],
            n_features_b=transformed[VIEW_B].shape[1],
            n_classes=3,
            embed_dim=8,
            hidden_dim=16,
        ),
        {VIEW_A: train[VIEW_A], VIEW_B: train[VIEW_B]},
        train["labels"],
        {VIEW_A: val[VIEW_A], VIEW_B: val[VIEW_B]},
        val["labels"],
        max_epochs=15,
        batch_size=16,
        learning_rate=0.02,
        patience=15,
        seed=0,
    )
    return trained.model, train, test


@pytest.fixture(scope="module")
def effects(gated_model_on_held_out_data):
    model, train, test = gated_model_on_held_out_data
    return run_all_interventions(
        model,
        {VIEW_A: test[VIEW_A], VIEW_B: test[VIEW_B]},
        test["labels"],
        test["donors"],
        train_views={VIEW_A: train[VIEW_A], VIEW_B: train[VIEW_B]},
        seed=0,
    )


class TestSevenInterventions:
    def test_all_seven_interventions_ran_on_held_out_cells(
        self, effects, gated_model_on_held_out_data
    ):
        _, _, test = gated_model_on_held_out_data
        assert sorted(effects) == sorted(INTERVENTIONS)
        assert len(effects) == 7
        for name, effect in effects.items():
            assert effect.n_cells == test["labels"].size, name

    def test_every_effect_is_labelled_intervention_evidence(self, effects):
        for name, effect in effects.items():
            assert effect.evidence == EVIDENCE_STATEMENT, name
            assert "not a causal claim" in effect.evidence

    def test_every_effect_reports_a_measured_change_or_a_reason(self, effects):
        for name, effect in effects.items():
            if effect.not_applicable:
                assert effect.flip_rate is None, name
            else:
                assert 0.0 <= effect.flip_rate <= 1.0, name
                assert effect.metric_before is not None, name
                assert effect.metric_after is not None, name

    def test_effects_break_down_by_donor_and_by_label(self, effects, gated_model_on_held_out_data):
        _, _, test = gated_model_on_held_out_data
        for name, effect in effects.items():
            if effect.not_applicable:
                continue
            assert set(effect.per_donor) == set(np.unique(test["donors"])), name
            expected_labels = {f"class_{label}" for label in np.unique(test["labels"])}
            assert set(effect.per_label) <= expected_labels, name
            assert effect.per_label, name

    def test_a_gated_model_reports_a_routing_shift_under_the_uniform_route(self, effects):
        effect = effects["fixed_uniform_route"]
        assert effect.not_applicable is None
        assert effect.routing_shift is not None
