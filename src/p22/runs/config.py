"""Run configuration with a hash and a fail-closed data mode.

A configuration is the input half of a run record. It is validated on construction,
hashed so two runs can be compared without reading every field, and refused outright
when it asks for a data mode the current approval state does not allow.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import p22

VIEW_A = "view_a"
VIEW_B = "view_b"
VIEW_NAMES = (VIEW_A, VIEW_B)

SINGLE_VIEW_FAMILIES = ("logistic_regression", "mlp")
TWO_VIEW_FAMILIES = ("concat_fusion", "gated_fusion")
MODEL_FAMILIES = SINGLE_VIEW_FAMILIES + TWO_VIEW_FAMILIES

KNOWN_METRICS = (
    "accuracy",
    "balanced_accuracy",
    "macro_f1",
    "weighted_f1",
    "macro_ovr_auroc",
    "multiclass_ece",
)

ALLOWED_DEVICES = ("cpu",)

DATASET_KEYS = (
    "n_donors",
    "cells_per_donor",
    "n_features_a",
    "n_features_b",
    "n_classes",
    "class_signal",
    "donor_nuisance",
    "noise",
)
SPLIT_KEYS = ("val_fraction", "test_fraction")
TRANSFORM_KEYS = ("kind", "n_components")
TRAINING_KEYS = (
    "max_epochs",
    "batch_size",
    "learning_rate",
    "hidden_dim",
    "embedding_dim",
    "patience",
    "device",
)
BOOTSTRAP_KEYS = ("n_replicates", "level")

CONFIG_KEYS = (
    "name",
    "data_mode",
    "seeds",
    "dataset",
    "split",
    "transform",
    "models",
    "training",
    "metrics",
    "bootstrap",
    "limitations",
)


@dataclass(frozen=True)
class ModelSpec:
    """One model entry: a neutral name, a family, and the views it may read."""

    name: str
    family: str
    views: tuple[str, ...]

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise ValueError("model name must not be blank")
        if self.family not in MODEL_FAMILIES:
            raise ValueError(
                f"unknown model family {self.family!r}; expected one of {MODEL_FAMILIES}"
            )
        if not self.views:
            raise ValueError(f"model {self.name!r} declares no views")
        unknown = [view for view in self.views if view not in VIEW_NAMES]
        if unknown:
            raise ValueError(f"model {self.name!r} declares unknown view(s) {unknown}")
        if len(set(self.views)) != len(self.views):
            raise ValueError(f"model {self.name!r} repeats a view")
        if self.family in SINGLE_VIEW_FAMILIES and len(self.views) != 1:
            raise ValueError(
                f"family {self.family!r} reads exactly one view, got {list(self.views)}"
            )
        if self.family in TWO_VIEW_FAMILIES and set(self.views) != set(VIEW_NAMES):
            raise ValueError(f"family {self.family!r} reads both views, got {list(self.views)}")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "family": self.family, "views": list(self.views)}


@dataclass(frozen=True)
class RunConfig:
    """A validated, hashable description of one benchmark run."""

    name: str
    data_mode: str
    seeds: tuple[int, ...]
    dataset: dict[str, Any]
    split: dict[str, Any]
    transform: dict[str, Any]
    models: tuple[ModelSpec, ...]
    training: dict[str, Any]
    metrics: tuple[str, ...]
    bootstrap: dict[str, Any]
    limitations: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise ValueError("config name must not be blank")
        _require_allowed_mode(self.data_mode)
        _check_seeds(self.seeds)
        _check_section("dataset", self.dataset, DATASET_KEYS)
        _check_section("split", self.split, SPLIT_KEYS)
        _check_section("transform", self.transform, TRANSFORM_KEYS)
        _check_section("training", self.training, TRAINING_KEYS)
        _check_section("bootstrap", self.bootstrap, BOOTSTRAP_KEYS)
        _check_dataset(self.dataset)
        _check_split(self.split)
        _check_transform(self.transform)
        _check_training(self.training)
        _check_bootstrap(self.bootstrap)
        _check_models(self.models)
        _check_metrics(self.metrics)
        if not self.limitations or any(not str(item).strip() for item in self.limitations):
            raise ValueError(
                "limitations must list at least one non-empty statement; a run with no stated "
                "limitation cannot be reported"
            )

    @property
    def config_hash(self) -> str:
        """SHA-256 of the canonical configuration, independent of key order."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "data_mode": self.data_mode,
            "seeds": list(self.seeds),
            "dataset": dict(self.dataset),
            "split": dict(self.split),
            "transform": dict(self.transform),
            "models": [model.to_dict() for model in self.models],
            "training": dict(self.training),
            "metrics": list(self.metrics),
            "bootstrap": dict(self.bootstrap),
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RunConfig:
        """Build a config from a mapping, rejecting missing or unexpected keys."""
        if not isinstance(payload, Mapping):
            raise ValueError(f"config payload must be a mapping, got {type(payload).__name__}")
        missing = [key for key in CONFIG_KEYS if key not in payload]
        if missing:
            raise ValueError(f"config is missing required key(s) {missing}")
        unexpected = [key for key in payload if key not in CONFIG_KEYS]
        if unexpected:
            raise ValueError(f"config has unexpected key(s) {sorted(unexpected)}")
        models_payload = payload["models"]
        if not isinstance(models_payload, Sequence) or isinstance(models_payload, str):
            raise ValueError("models must be a list of model entries")
        models = []
        for entry in models_payload:
            if not isinstance(entry, Mapping):
                raise ValueError(f"model entry must be a mapping, got {type(entry).__name__}")
            unknown = [key for key in entry if key not in ("name", "family", "views")]
            if unknown:
                raise ValueError(f"model entry has unexpected key(s) {sorted(unknown)}")
            models.append(
                ModelSpec(
                    name=str(entry["name"]),
                    family=str(entry["family"]),
                    views=tuple(str(view) for view in entry["views"]),
                )
            )
        return cls(
            name=str(payload["name"]),
            data_mode=str(payload["data_mode"]),
            seeds=tuple(int(seed) for seed in payload["seeds"]),
            dataset=dict(payload["dataset"]),
            split=dict(payload["split"]),
            transform=dict(payload["transform"]),
            models=tuple(models),
            training=dict(payload["training"]),
            metrics=tuple(str(name) for name in payload["metrics"]),
            bootstrap=dict(payload["bootstrap"]),
            limitations=tuple(str(item) for item in payload["limitations"]),
        )


def load_run_config(path: str | Path) -> RunConfig:
    """Read a configuration from JSON on disk.

    Args:
        path: local path to a ``.json`` configuration.

    Returns:
        The validated :class:`RunConfig`.

    Raises:
        ValueError: if the path is remote, is not JSON, or the payload fails
            validation, including asking for a data mode approval does not allow.
        FileNotFoundError: if the file does not exist.
    """
    text_path = str(path)
    for prefix in ("http://", "https://", "s3://", "gs://", "ftp://"):
        if text_path.startswith(prefix):
            raise ValueError(f"config path must be local, got remote {text_path!r}")
    local = Path(text_path)
    if local.suffix != ".json":
        raise ValueError(f"config must be a .json file, got {local.suffix!r}")
    if not local.is_file():
        raise FileNotFoundError(f"config not found: {local}")
    return RunConfig.from_dict(json.loads(local.read_text()))


def _require_allowed_mode(data_mode: str) -> None:
    if data_mode not in p22.DATA_MODES:
        raise ValueError(f"unknown data_mode {data_mode!r}; expected one of {p22.DATA_MODES}")
    p22.require_allowed_data_mode(data_mode)
    if p22.approval_blocked() and data_mode != p22.SYNTHETIC:
        raise ValueError(
            f"approval is blocked, so data_mode must be {p22.SYNTHETIC!r}, got {data_mode!r}"
        )


def _check_seeds(seeds: Sequence[int]) -> None:
    if not seeds:
        raise ValueError("seeds must list at least one seed")
    if len(set(seeds)) != len(seeds):
        raise ValueError(f"seeds must be unique, got {list(seeds)}")
    for seed in seeds:
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError(f"each seed must be an int, got {seed!r}")
        if seed < 0:
            raise ValueError(f"seeds must be non-negative, got {seed}")


def _check_section(section: str, payload: Mapping[str, Any], keys: Sequence[str]) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError(f"{section} is missing key(s) {missing}")
    unexpected = [key for key in payload if key not in keys]
    if unexpected:
        raise ValueError(f"{section} has unexpected key(s) {sorted(unexpected)}")


def _check_dataset(dataset: Mapping[str, Any]) -> None:
    for key in ("n_donors", "cells_per_donor", "n_features_a", "n_features_b", "n_classes"):
        value = dataset[key]
        if not isinstance(value, int) or value < 1:
            raise ValueError(f"dataset.{key} must be a positive int, got {value!r}")
    if dataset["n_classes"] < 2:
        raise ValueError(f"dataset.n_classes must be at least 2, got {dataset['n_classes']}")
    for key in ("class_signal", "donor_nuisance", "noise"):
        value = dataset[key]
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"dataset.{key} must be a non-negative number, got {value!r}")


def _check_split(split: Mapping[str, Any]) -> None:
    for key in SPLIT_KEYS:
        value = split[key]
        if not isinstance(value, (int, float)) or not 0.0 < float(value) < 1.0:
            raise ValueError(f"split.{key} must lie in (0, 1), got {value!r}")
    if float(split["val_fraction"]) + float(split["test_fraction"]) >= 1.0:
        raise ValueError("split fractions must leave donors for training")


def _check_transform(transform: Mapping[str, Any]) -> None:
    kind = transform["kind"]
    if kind not in ("standard_scaler", "pca"):
        raise ValueError(f"transform.kind must be 'standard_scaler' or 'pca', got {kind!r}")
    components = transform["n_components"]
    if kind == "pca":
        if not isinstance(components, int) or components < 1:
            raise ValueError(
                f"transform.n_components must be a positive int for pca, got {components!r}"
            )
    elif components is not None:
        raise ValueError("transform.n_components must be null unless kind is 'pca'")


def _check_training(training: Mapping[str, Any]) -> None:
    for key in ("max_epochs", "batch_size", "hidden_dim", "embedding_dim", "patience"):
        value = training[key]
        if not isinstance(value, int) or value < 1:
            raise ValueError(f"training.{key} must be a positive int, got {value!r}")
    rate = training["learning_rate"]
    if not isinstance(rate, (int, float)) or not 0.0 < float(rate) < 1.0:
        raise ValueError(f"training.learning_rate must lie in (0, 1), got {rate!r}")
    device = training["device"]
    if device not in ALLOWED_DEVICES:
        raise ValueError(f"training.device must be one of {ALLOWED_DEVICES}, got {device!r}")


def _check_bootstrap(bootstrap: Mapping[str, Any]) -> None:
    replicates = bootstrap["n_replicates"]
    if not isinstance(replicates, int) or replicates < 1:
        raise ValueError(f"bootstrap.n_replicates must be a positive int, got {replicates!r}")
    level = bootstrap["level"]
    if not isinstance(level, (int, float)) or not 0.0 < float(level) < 1.0:
        raise ValueError(f"bootstrap.level must lie in (0, 1), got {level!r}")


def _check_models(models: Sequence[ModelSpec]) -> None:
    if not models:
        raise ValueError("models must list at least one model")
    names = [model.name for model in models]
    if len(set(names)) != len(names):
        raise ValueError(f"model names must be unique, got {names}")


def _check_metrics(metrics: Sequence[str]) -> None:
    if not metrics:
        raise ValueError("metrics must list at least one metric")
    unknown = [name for name in metrics if name not in KNOWN_METRICS]
    if unknown:
        raise ValueError(f"unknown metric(s) {unknown}; expected a subset of {KNOWN_METRICS}")
    if len(set(metrics)) != len(metrics):
        raise ValueError(f"metrics must be unique, got {list(metrics)}")
