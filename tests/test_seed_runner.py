"""Tests for the multi-seed benchmark runner.

Claims under test: donors are split before any transform is fitted, transforms see training
cells only, the test split is read exactly once per model, the same seed reproduces the same
numbers, and non-synthetic data fails closed.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import p22
from p22.runs.config import RunConfig
from p22.runs.registry import RunRegistry
from p22.training.seed_runner import (
    HoldoutAlreadyUsedError,
    SingleUseHoldout,
    build_record,
    require_synthetic,
    run_all_seeds,
    run_one_seed,
    summarize_across_seeds,
)

TINY = {
    "name": "tiny_pilot",
    "data_mode": "synthetic",
    "seeds": [0, 1],
    "dataset": {
        "n_donors": 12,
        "cells_per_donor": 12,
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
    "metrics": ["accuracy", "balanced_accuracy", "macro_f1", "macro_ovr_auroc", "multiclass_ece"],
    "bootstrap": {"n_replicates": 20, "level": 0.95},
    "limitations": [
        "Synthetic data with hand-set signal, so numbers carry no biological meaning.",
        "Two epochs and twelve donors: this configuration tests the runner, not any model.",
    ],
}


def tiny_config(**overrides) -> RunConfig:
    payload = json.loads(json.dumps(TINY))
    payload.update(overrides)
    return RunConfig.from_dict(payload)


@pytest.fixture(scope="module")
def config() -> RunConfig:
    return tiny_config()


@pytest.fixture(scope="module")
def run(config: RunConfig):
    return run_one_seed(config, seed=0)


class TestFailClosed:
    def test_runner_refuses_non_synthetic_modes(self):
        for mode in (p22.LEGACY_READ_ONLY, p22.APPROVED_REAL_DATA):
            with pytest.raises(ValueError):
                require_synthetic(mode)

    def test_runner_refuses_an_unknown_mode(self):
        with pytest.raises(ValueError, match="unknown data_mode"):
            require_synthetic("whatever_is_lying_around")

    def test_synthetic_mode_passes(self):
        require_synthetic(p22.SYNTHETIC)


class TestSplitBeforeTransforms:
    def test_every_configured_model_produced_an_outcome(self, config: RunConfig, run):
        assert sorted(run.outcomes) == sorted(model.name for model in config.models)
        assert len(run.outcomes) == 6

    def test_donors_do_not_cross_splits(self, run):
        summary = run.split_summary
        assert summary["split_unit"] == "donor"
        assert summary["validated"] is True
        assert summary["donor_overlap"] == 0
        assert summary["unassigned_cells"] == 0

    def test_counts_add_up_to_the_whole_dataset(self, config: RunConfig, run):
        expected = config.dataset["n_donors"] * config.dataset["cells_per_donor"]
        assert sum(run.cell_counts.values()) == expected
        assert sum(run.donor_counts.values()) == config.dataset["n_donors"]
        assert run.data_fingerprint["n_cells"] == expected

    def test_transforms_were_fitted_on_training_cells_only(self, run):
        assert run.transform_metadata["fit_scope"] == "train cells only"
        for view in ("view_a", "view_b"):
            metadata = run.transform_metadata[view]
            assert metadata["fit_scope"] == "train cells only"
            assert metadata["n_train_cells"] == run.cell_counts["train"]
            assert metadata["n_holdout_ids_declared"] == (
                run.cell_counts["val"] + run.cell_counts["test"]
            )
            assert len(metadata["parameter_fingerprint"]) == 64


class TestSingleUseHoldout:
    def test_first_read_returns_the_arrays(self):
        holdout = SingleUseHoldout(
            views={"view_a": np.zeros((4, 2))},
            labels=np.array([0, 1, 0, 1]),
            donor_ids=np.array(["d0", "d0", "d1", "d1"]),
        )
        views, labels, donors = holdout.take("model")
        assert views["view_a"].shape == (4, 2)
        assert labels.size == 4
        assert donors.size == 4
        assert holdout.used_by == ("model",)

    def test_second_read_is_refused(self):
        holdout = SingleUseHoldout(
            views={"view_a": np.zeros((2, 2))},
            labels=np.array([0, 1]),
            donor_ids=np.array(["d0", "d1"]),
        )
        holdout.take("first")
        with pytest.raises(HoldoutAlreadyUsedError, match="selection signal"):
            holdout.take("second")


class TestMetrics:
    def test_label_metrics_carry_donor_intervals_and_replicate_counts(self, run):
        for outcome in run.outcomes.values():
            entry = outcome.metrics["accuracy"]
            assert entry["unit"] == "donor"
            assert entry["n_valid"] + entry["n_failed"] == 20
            assert entry["interval"][0] <= entry["value"] <= entry["interval"][1]

    def test_probability_metrics_say_why_they_lack_an_interval(self, run):
        entry = run.outcomes["mlp_view_a"].metrics["macro_ovr_auroc"]
        assert "interval" not in entry
        assert "across-seed summary" in entry["not_applicable"]

    def test_every_configured_metric_is_present(self, config: RunConfig, run):
        for outcome in run.outcomes.values():
            assert sorted(outcome.metrics) == sorted(config.metrics)

    def test_no_metric_value_is_a_silent_nan(self, run):
        for outcome in run.outcomes.values():
            for entry in outcome.metrics.values():
                assert entry["value"] is None or np.isfinite(entry["value"])


class TestTrainingRecords:
    def test_selection_used_the_validation_split(self, run):
        for outcome in run.outcomes.values():
            assert outcome.training["selection_split"] == "val"
            assert outcome.training["device"] == "cpu"

    def test_logistic_regression_chose_its_regularisation_on_validation(self, run):
        record = run.outcomes["logistic_regression_view_a"].training
        assert record["chosen_inverse_regularisation"] in record["grid"]
        assert len(record["history"]) == len(record["grid"])

    def test_torch_models_report_their_epoch_history(self, run):
        record = run.outcomes["gated_fusion"].training
        assert record["epochs_run"] >= 1
        assert len(record["history"]) == record["epochs_run"]
        assert record["best_epoch"] >= 1


class TestRoutingSignals:
    def test_single_view_models_report_no_routing(self, run):
        for name in ("logistic_regression_view_a", "mlp_view_b"):
            assert run.outcomes[name].routing_signals == {}

    def test_gated_weights_sum_to_one_and_are_labelled_as_signals(self, run):
        signals = run.outcomes["gated_fusion"].routing_signals
        assert signals["has_gate"] is True
        assert signals["weights_sum_to_one"] is True
        assert signals["mean_weight_view_a"] + signals["mean_weight_view_b"] == pytest.approx(1.0)
        assert "not evidence of dependence" in signals["reading"]

    def test_concatenation_reports_uniform_weights_without_a_gate(self, run):
        signals = run.outcomes["concat_fusion"].routing_signals
        assert signals["has_gate"] is False
        assert signals["mean_weight_view_a"] == pytest.approx(0.5)

    def test_per_label_routing_summaries_are_present(self, run):
        signals = run.outcomes["gated_fusion"].routing_signals
        per_label = [key for key in signals if key.startswith("mean_weight_view_a_label_")]
        assert len(per_label) >= 2


class TestDeterminism:
    def test_same_seed_reproduces_every_metric(self, config: RunConfig, run):
        repeat = run_one_seed(config, seed=0)
        for name, outcome in run.outcomes.items():
            for metric, entry in outcome.metrics.items():
                assert repeat.outcomes[name].metrics[metric]["value"] == pytest.approx(
                    entry["value"], rel=1e-9, abs=1e-9
                ), f"{name}/{metric}"
        assert repeat.data_fingerprint["sha256"] == run.data_fingerprint["sha256"]

    def test_different_seed_changes_the_data_and_the_numbers(self, config: RunConfig, run):
        other = run_one_seed(config, seed=1)
        assert other.data_fingerprint["sha256"] != run.data_fingerprint["sha256"]
        differences = [
            other.metric_value(name, "accuracy") != run.metric_value(name, "accuracy")
            for name in run.outcomes
        ]
        assert any(differences)


class TestMultipleSeeds:
    def test_runs_each_seed_and_summarises_across_them(self, config: RunConfig):
        runs = run_all_seeds(config, seeds=[0, 1], n_replicates=10)
        assert [run.seed for run in runs] == [0, 1]
        summary = summarize_across_seeds(runs, metrics=["accuracy"])
        assert sorted(summary) == sorted(model.name for model in config.models)
        for entry in summary.values():
            assert entry["accuracy"]["n_seeds"] == 2
            assert entry["accuracy"]["mean"] is not None

    def test_rejects_empty_or_repeated_seeds(self, config: RunConfig):
        with pytest.raises(ValueError, match="at least one seed"):
            run_all_seeds(config, seeds=[])
        with pytest.raises(ValueError, match="unique"):
            run_all_seeds(config, seeds=[0, 0])

    def test_summary_refuses_runs_from_different_configurations(self, config: RunConfig, run):
        other = run_one_seed(tiny_config(name="other_pilot"), seed=0)
        with pytest.raises(ValueError, match="different configurations"):
            summarize_across_seeds([run, other])

    def test_summary_refuses_an_empty_run_list(self):
        with pytest.raises(ValueError, match="at least one run"):
            summarize_across_seeds([])

    def test_single_seed_summary_states_it_cannot_show_spread(self, config: RunConfig, run):
        summary = summarize_across_seeds([run], metrics=["accuracy"])
        entry = summary["gated_fusion"]["accuracy"]
        assert entry["n_seeds"] == 1
        assert "at least two usable seeds" in entry["not_applicable"]


class TestRecordsAndRegistry:
    def test_one_valid_record_per_model(self, config: RunConfig, run, tmp_path: Path):
        registry = RunRegistry(tmp_path / "runs")
        for outcome in run.outcomes.values():
            registry.write(build_record(config, run, outcome))
        assert len(registry.run_ids()) == 6
        for record in registry.load_all():
            assert record.data_mode == p22.SYNTHETIC
            assert record.approval_state == "blocked"
            assert record.limitations
            assert record.transform_metadata["fit_scope"] == "train cells only"
            assert any("evaluated once" in note for note in record.notes)

    def test_registry_integration_writes_during_the_run(self, config: RunConfig, tmp_path: Path):
        registry = RunRegistry(tmp_path / "runs")
        run_one_seed(config, seed=0, registry=registry, n_replicates=10)
        assert len(registry.run_ids()) == 6

    def test_record_notes_name_the_family_and_views(self, config: RunConfig, run):
        record = build_record(config, run, run.outcomes["concat_fusion"])
        assert any("concat_fusion" in note for note in record.notes)
        assert any("view_a" in note for note in record.notes)


@pytest.mark.slow
class TestScript:
    def test_toy_pilot_script_runs_and_writes_reports(self, tmp_path: Path):
        import importlib.util

        script = p22.REPO_ROOT / "scripts" / "run_toy_pilot.py"
        spec = importlib.util.spec_from_file_location("run_toy_pilot_under_test", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        config_path = tmp_path / "tiny.json"
        config_path.write_text(json.dumps(TINY))
        out = tmp_path / "generated"
        exit_code = module.main(
            [
                "--config",
                str(config_path),
                "--seeds",
                "0",
                "--replicates",
                "10",
                "--out",
                str(out),
            ]
        )
        assert exit_code == 0
        assert len(list((out / "runs").glob("*.json"))) == 6
        assert len(list((out / "reports").glob("*.md"))) == 6
        summary = json.loads((out / "reports" / "tiny_pilot_across_seeds.json").read_text())
        assert sorted(summary) == sorted(model["name"] for model in TINY["models"])
