"""Tests for run configuration and run records.

Two claims under test: while approval is blocked a configuration cannot ask for anything
other than synthetic data, and a run record is refused unless it carries the provenance
needed to replay it plus at least one stated limitation.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import p22
from p22.runs.config import (
    KNOWN_METRICS,
    ModelSpec,
    RunConfig,
    load_run_config,
)
from p22.runs.registry import (
    RunRecord,
    RunRegistry,
    current_git_commit,
    data_fingerprint,
)

CONFIG_PATH = p22.REPO_ROOT / "configs" / "toy_pilot.json"
COMMIT = "a" * 40


def config_payload(**overrides) -> dict:
    payload = json.loads(CONFIG_PATH.read_text())
    payload.update(overrides)
    return payload


def make_config(**overrides) -> RunConfig:
    return RunConfig.from_dict(config_payload(**overrides))


def make_record(**overrides) -> RunRecord:
    config = overrides.pop("config", None) or make_config()
    rng = np.random.default_rng(0)
    labels = rng.integers(0, 3, size=30)
    donors = np.repeat([f"donor_{index}" for index in range(6)], 5)
    fingerprint = data_fingerprint(
        {"view_a": rng.normal(size=(30, 4)), "view_b": rng.normal(size=(30, 3))}, labels, donors
    )
    arguments = {
        "config": config,
        "model": "concat_fusion",
        "seeds": (0, 1, 2, 3, 4),
        "data_fingerprint": fingerprint,
        "donor_counts": {"train": 4, "val": 1, "test": 1},
        "cell_counts": {"train": 20, "val": 5, "test": 5},
        "transform_metadata": {
            "kind": "standard_scaler",
            "fit_scope": "train cells only",
            "parameter_fingerprint": "b" * 64,
        },
        "metrics": {
            "accuracy": {
                "value": 0.81,
                "not_applicable": None,
                "interval": [0.7, 0.9],
                "unit": "donor",
                "n_valid": 400,
                "n_failed": 0,
            }
        },
        "evidence_labels": ("experimental result", "verified"),
        "git_commit": COMMIT,
        "created_at": "2026-07-27T00:00:00+00:00",
    }
    arguments.update(overrides)
    return RunRecord.create(**arguments)


class TestShippedConfig:
    def test_repository_config_loads_and_declares_synthetic_data(self):
        config = load_run_config(CONFIG_PATH)
        assert config.name == "toy_pilot"
        assert config.data_mode == p22.SYNTHETIC
        assert len(config.seeds) == 5

    def test_repository_config_declares_the_six_planned_baselines(self):
        config = load_run_config(CONFIG_PATH)
        families = sorted({model.family for model in config.models})
        assert families == ["concat_fusion", "gated_fusion", "logistic_regression", "mlp"]
        assert len(config.models) == 6
        single_view = [model for model in config.models if len(model.views) == 1]
        assert sorted(model.name for model in single_view) == [
            "logistic_regression_view_a",
            "logistic_regression_view_b",
            "mlp_view_a",
            "mlp_view_b",
        ]

    def test_repository_config_runs_on_cpu_and_states_limitations(self):
        config = load_run_config(CONFIG_PATH)
        assert config.training["device"] == "cpu"
        assert len(config.limitations) >= 3
        assert any("synthetic" in item.lower() for item in config.limitations)

    def test_repository_config_metrics_are_known(self):
        config = load_run_config(CONFIG_PATH)
        assert set(config.metrics) <= set(KNOWN_METRICS)


class TestConfigValidation:
    def test_hash_is_stable_and_order_independent(self):
        first = make_config()
        payload = config_payload()
        reordered = {key: payload[key] for key in reversed(list(payload))}
        second = RunConfig.from_dict(reordered)
        assert first.config_hash == second.config_hash
        assert len(first.config_hash) == 64

    def test_hash_changes_when_any_field_changes(self):
        base = make_config().config_hash
        assert make_config(seeds=[0, 1, 2, 3, 5]).config_hash != base
        assert make_config(name="other_pilot").config_hash != base

    def test_blocked_approval_refuses_non_synthetic_data_mode(self):
        assert p22.approval_blocked()
        for mode in (p22.APPROVED_REAL_DATA, p22.LEGACY_READ_ONLY):
            with pytest.raises(ValueError):
                make_config(data_mode=mode)

    def test_unknown_data_mode_is_refused(self):
        with pytest.raises(ValueError, match="unknown data_mode"):
            make_config(data_mode="whatever_is_lying_around")

    def test_missing_and_unexpected_keys_are_refused(self):
        payload = config_payload()
        del payload["bootstrap"]
        with pytest.raises(ValueError, match="missing required key"):
            RunConfig.from_dict(payload)
        with pytest.raises(ValueError, match="unexpected key"):
            make_config(extra_setting=True)

    def test_empty_limitations_are_refused(self):
        with pytest.raises(ValueError, match="limitations"):
            make_config(limitations=[])
        with pytest.raises(ValueError, match="limitations"):
            make_config(limitations=["   "])

    def test_seeds_must_be_present_and_unique(self):
        with pytest.raises(ValueError, match="at least one seed"):
            make_config(seeds=[])
        with pytest.raises(ValueError, match="unique"):
            make_config(seeds=[1, 1, 2])
        with pytest.raises(ValueError, match="non-negative"):
            make_config(seeds=[-1])

    def test_split_fractions_must_leave_training_donors(self):
        with pytest.raises(ValueError, match="leave donors for training"):
            make_config(split={"val_fraction": 0.5, "test_fraction": 0.5})
        with pytest.raises(ValueError, match=r"\(0, 1\)"):
            make_config(split={"val_fraction": 0.0, "test_fraction": 0.2})

    def test_non_cpu_device_is_refused(self):
        training = dict(config_payload()["training"], device="cuda")
        with pytest.raises(ValueError, match="device"):
            make_config(training=training)

    def test_unknown_metric_is_refused(self):
        with pytest.raises(ValueError, match="unknown metric"):
            make_config(metrics=["accuracy", "vibes"])

    def test_transform_components_must_match_kind(self):
        with pytest.raises(ValueError, match="n_components must be null"):
            make_config(transform={"kind": "standard_scaler", "n_components": 8})
        with pytest.raises(ValueError, match="positive int for pca"):
            make_config(transform={"kind": "pca", "n_components": None})

    def test_model_family_and_views_must_agree(self):
        with pytest.raises(ValueError, match="unknown model family"):
            ModelSpec(name="m", family="transformer_of_everything", views=("view_a",))
        with pytest.raises(ValueError, match="exactly one view"):
            ModelSpec(name="m", family="mlp", views=("view_a", "view_b"))
        with pytest.raises(ValueError, match="both views"):
            ModelSpec(name="m", family="gated_fusion", views=("view_a",))
        with pytest.raises(ValueError, match="unknown view"):
            ModelSpec(name="m", family="mlp", views=("view_c",))

    def test_duplicate_model_names_are_refused(self):
        models = config_payload()["models"]
        with pytest.raises(ValueError, match="unique"):
            make_config(models=[models[0], dict(models[1], name=models[0]["name"])])

    def test_dataset_needs_at_least_two_classes(self):
        dataset = dict(config_payload()["dataset"], n_classes=1)
        with pytest.raises(ValueError, match="at least 2"):
            make_config(dataset=dataset)


class TestConfigLoading:
    def test_rejects_remote_paths(self):
        with pytest.raises(ValueError, match="remote"):
            load_run_config("https://example.invalid/toy_pilot.json")

    def test_rejects_non_json_suffix(self, tmp_path: Path):
        target = tmp_path / "config.yaml"
        target.write_text("name: toy")
        with pytest.raises(ValueError, match=r"\.json"):
            load_run_config(target)

    def test_reports_a_missing_file(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_run_config(tmp_path / "absent.json")

    def test_round_trips_through_disk(self, tmp_path: Path):
        target = tmp_path / "copy.json"
        target.write_text(json.dumps(make_config().to_dict()))
        assert load_run_config(target).config_hash == make_config().config_hash


class TestDataFingerprint:
    def test_same_arrays_give_the_same_fingerprint(self):
        rng = np.random.default_rng(1)
        view = rng.normal(size=(20, 5))
        labels = rng.integers(0, 2, size=20)
        donors = np.repeat(["d0", "d1", "d2", "d3"], 5)
        first = data_fingerprint({"view_a": view}, labels, donors)
        second = data_fingerprint({"view_a": view.copy()}, labels.copy(), donors.copy())
        assert first["sha256"] == second["sha256"]
        assert first["n_cells"] == 20
        assert first["n_donors"] == 4
        assert first["views"]["view_a"] == [20, 5]

    def test_changed_values_labels_or_donors_change_the_fingerprint(self):
        rng = np.random.default_rng(2)
        view = rng.normal(size=(20, 5))
        labels = rng.integers(0, 2, size=20)
        donors = np.repeat(["d0", "d1", "d2", "d3"], 5)
        base = data_fingerprint({"view_a": view}, labels, donors)["sha256"]

        nudged = view.copy()
        nudged[0, 0] += 1.0
        assert data_fingerprint({"view_a": nudged}, labels, donors)["sha256"] != base

        relabelled = labels.copy()
        relabelled[0] = 1 - relabelled[0]
        assert data_fingerprint({"view_a": view}, relabelled, donors)["sha256"] != base

        regrouped = donors.copy()
        regrouped[0] = "d9"
        assert data_fingerprint({"view_a": view}, labels, regrouped)["sha256"] != base

    def test_view_set_is_part_of_the_fingerprint(self):
        rng = np.random.default_rng(3)
        view_a = rng.normal(size=(12, 3))
        view_b = rng.normal(size=(12, 2))
        labels = rng.integers(0, 2, size=12)
        donors = np.repeat(["d0", "d1", "d2"], 4)
        one = data_fingerprint({"view_a": view_a}, labels, donors)["sha256"]
        two = data_fingerprint({"view_a": view_a, "view_b": view_b}, labels, donors)["sha256"]
        assert one != two

    def test_rejects_shape_disagreement_and_empty_input(self):
        labels = np.zeros(10, dtype=int)
        donors = np.repeat(["d0", "d1"], 5)
        with pytest.raises(ValueError, match="at least one view"):
            data_fingerprint({}, labels, donors)
        with pytest.raises(ValueError, match="rows"):
            data_fingerprint({"view_a": np.zeros((9, 3))}, labels, donors)
        with pytest.raises(ValueError, match="two-dimensional"):
            data_fingerprint({"view_a": np.zeros(10)}, labels, donors)


class TestRunRecord:
    def test_record_carries_every_required_field(self):
        record = make_record()
        payload = record.to_dict()
        for field_name in (
            "run_id",
            "created_at",
            "git_commit",
            "config_hash",
            "config",
            "data_fingerprint",
            "data_mode",
            "approval_state",
            "seeds",
            "donor_counts",
            "cell_counts",
            "transform_metadata",
            "model",
            "metrics",
            "evidence_labels",
            "limitations",
        ):
            assert field_name in payload, field_name
            assert payload[field_name] not in (None, "", [], {})

    def test_run_id_ties_the_record_to_config_and_commit(self):
        record = make_record()
        assert record.config_hash[:8] in record.run_id
        assert record.git_commit[:8] in record.run_id
        assert "concat_fusion" in record.run_id

    def test_approval_state_and_data_mode_come_from_the_environment(self):
        record = make_record()
        assert record.approval_state == "blocked"
        assert record.data_mode == p22.SYNTHETIC

    def test_limitations_default_to_the_configuration(self):
        config = make_config()
        assert make_record(config=config).limitations == config.limitations

    def test_empty_limitations_are_refused(self):
        with pytest.raises(ValueError, match="limitations"):
            make_record(limitations=[])

    def test_missing_provenance_is_refused(self):
        with pytest.raises(ValueError, match="git_commit"):
            make_record(git_commit="not-a-commit")
        with pytest.raises(ValueError, match="fit_scope"):
            make_record(transform_metadata={"kind": "standard_scaler"})
        with pytest.raises(ValueError, match="transform_metadata"):
            make_record(transform_metadata={})

    def test_split_counts_must_cover_train_val_and_test(self):
        with pytest.raises(ValueError, match="missing split"):
            make_record(donor_counts={"train": 4, "test": 1})
        with pytest.raises(ValueError, match="unexpected split"):
            make_record(cell_counts={"train": 20, "val": 5, "test": 5, "extra": 2})
        with pytest.raises(ValueError, match="positive int"):
            make_record(cell_counts={"train": 20, "val": 0, "test": 5})

    def test_non_finite_metric_values_are_refused(self):
        with pytest.raises(ValueError, match="not_applicable"):
            make_record(metrics={"accuracy": {"value": float("nan"), "not_applicable": None}})
        with pytest.raises(ValueError, match="missing key"):
            make_record(metrics={"accuracy": {"value": 0.8}})

    def test_metric_without_value_needs_a_reason(self):
        with pytest.raises(ValueError, match="no value and no reason"):
            make_record(metrics={"macro_ovr_auroc": {"value": None, "not_applicable": ""}})
        record = make_record(
            metrics={"macro_ovr_auroc": {"value": None, "not_applicable": "a class was absent"}}
        )
        assert record.metrics["macro_ovr_auroc"]["value"] is None

    def test_unknown_evidence_label_is_refused(self):
        with pytest.raises(ValueError, match="unknown evidence label"):
            make_record(evidence_labels=("vibes",))

    def test_record_data_mode_must_match_its_config(self):
        record = make_record()
        payload = record.to_dict()
        payload["data_mode"] = p22.LEGACY_READ_ONLY
        with pytest.raises(ValueError):
            RunRecord.from_dict(payload)

    def test_round_trips_through_json(self):
        record = make_record()
        rebuilt = RunRecord.from_dict(json.loads(json.dumps(record.to_dict())))
        assert rebuilt.to_dict() == record.to_dict()


class TestRunRegistry:
    def test_writes_loads_and_lists_records(self, tmp_path: Path):
        registry = RunRegistry(tmp_path / "runs")
        record = make_record()
        path = registry.write(record)
        assert path.is_file()
        assert registry.run_ids() == (record.run_id,)
        assert registry.load(record.run_id).to_dict() == record.to_dict()
        assert len(registry.load_all()) == 1

    def test_refuses_to_overwrite_an_existing_record(self, tmp_path: Path):
        registry = RunRegistry(tmp_path / "runs")
        record = make_record()
        registry.write(record)
        with pytest.raises(FileExistsError):
            registry.write(record)

    def test_reports_a_missing_record(self, tmp_path: Path):
        registry = RunRegistry(tmp_path / "runs")
        assert registry.run_ids() == ()
        with pytest.raises(FileNotFoundError):
            registry.load("absent_run")

    def test_default_location_is_inside_the_generated_tree(self):
        from p22.runs.registry import RUNS_ROOT

        assert "generated" in RUNS_ROOT.parts
        assert RUNS_ROOT.is_relative_to(p22.REPO_ROOT)


class TestGitCommit:
    def test_reads_a_forty_character_commit_from_the_repository(self):
        commit = current_git_commit()
        assert len(commit) == 40
        assert all(character in "0123456789abcdef" for character in commit)

    def test_raises_when_the_directory_is_not_a_repository(self, tmp_path: Path):
        with pytest.raises(RuntimeError, match="could not read the git commit"):
            current_git_commit(tmp_path)
