"""Five-seed synthetic benchmark, in a fixed and enforced order.

The order is the point: split donors, then fit transforms on training cells, then train,
then select on validation, then touch the test split exactly once. Each step is enforced
rather than documented. The test arrays are wrapped in :class:`SingleUseHoldout`, so a
second evaluation raises instead of quietly happening.

Non-synthetic data fails closed here as well as in the configuration, because this module
generates its own data and would otherwise be the easy way around the approval gate.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression

import p22
from p22.data.splits import make_donor_split, validate_donor_split
from p22.data.transforms import fit_train_only
from p22.eval.metrics import accuracy, balanced_accuracy, compute_metrics, macro_f1
from p22.eval.statistics import donor_bootstrap, summarize_seeds
from p22.models.baselines import BaselineMLP
from p22.models.fusion import VIEW_A, VIEW_B, ConcatFusionModel, GatedFusionModel
from p22.runs.config import RunConfig
from p22.runs.registry import RunRecord, RunRegistry, data_fingerprint
from p22.testing.synthetic import make_synthetic_multimodal
from p22.training.loop import forward_views, predict, set_all_seeds, train_model

INTERVAL_METRICS = {
    "accuracy": accuracy,
    "balanced_accuracy": balanced_accuracy,
    "macro_f1": macro_f1,
}
LOGISTIC_REGULARISATION_GRID = (0.01, 0.1, 1.0, 10.0)
VIEW_ORDER = (VIEW_A, VIEW_B)


class HoldoutAlreadyUsedError(RuntimeError):
    """Raised when the test split is evaluated more than once."""


@dataclass
class SingleUseHoldout:
    """Test arrays that can be read once.

    Repeated reads are the mechanism by which a test split turns into a tuning
    signal, so the second read is an error rather than a warning.
    """

    views: dict[str, np.ndarray]
    labels: np.ndarray
    donor_ids: np.ndarray
    label: str = "test"
    used_by: tuple[str, ...] = ()

    def take(self, reader: str) -> tuple[dict[str, np.ndarray], np.ndarray, np.ndarray]:
        """Return the arrays and record the reader.

        Args:
            reader: name of the model or step reading the split.

        Raises:
            HoldoutAlreadyUsedError: if this holdout was already read.
        """
        if self.used_by:
            raise HoldoutAlreadyUsedError(
                f"the {self.label} split was already evaluated by {list(self.used_by)}; "
                "a second evaluation would turn it into a selection signal"
            )
        self.used_by = (reader,)
        return self.views, self.labels, self.donor_ids


@dataclass(frozen=True)
class ModelOutcome:
    """One model, one seed: how it was selected and what it measured."""

    model_name: str
    family: str
    views: tuple[str, ...]
    seed: int
    metrics: dict[str, dict[str, Any]]
    training: dict[str, Any]
    routing_signals: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "family": self.family,
            "views": list(self.views),
            "seed": self.seed,
            "metrics": self.metrics,
            "training": self.training,
            "routing_signals": self.routing_signals,
        }


@dataclass(frozen=True)
class SeedRun:
    """Every model for one seed, with the shared data facts."""

    seed: int
    config_hash: str
    donor_counts: dict[str, int]
    cell_counts: dict[str, int]
    data_fingerprint: dict[str, Any]
    transform_metadata: dict[str, Any]
    split_summary: dict[str, Any]
    outcomes: dict[str, ModelOutcome]

    def metric_value(self, model_name: str, metric: str) -> float | None:
        return self.outcomes[model_name].metrics[metric]["value"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "config_hash": self.config_hash,
            "donor_counts": self.donor_counts,
            "cell_counts": self.cell_counts,
            "data_fingerprint": self.data_fingerprint,
            "transform_metadata": self.transform_metadata,
            "split_summary": self.split_summary,
            "outcomes": {name: outcome.to_dict() for name, outcome in self.outcomes.items()},
        }


def require_synthetic(data_mode: str) -> None:
    """Refuse anything but synthetic data while approval is blocked.

    Args:
        data_mode: the mode a caller asked for.

    Raises:
        ValueError: if the mode is unknown, disallowed by the approval file, or not
            synthetic while approval is blocked.
    """
    if data_mode not in p22.DATA_MODES:
        raise ValueError(f"unknown data_mode {data_mode!r}; expected one of {p22.DATA_MODES}")
    p22.require_allowed_data_mode(data_mode)
    if data_mode != p22.SYNTHETIC:
        raise ValueError(
            f"the benchmark runner generates synthetic data only, got data_mode {data_mode!r}"
        )


def build_model(
    spec: Any, n_features: Mapping[str, int], n_classes: int, training: Mapping[str, Any]
):
    """Construct an untrained model for one specification.

    Args:
        spec: a :class:`~p22.runs.config.ModelSpec`.
        n_features: feature count per view after transformation.
        n_classes: number of label classes.
        training: training section of the configuration.

    Returns:
        A torch module, or ``None`` for the logistic regression family, which is
        fitted by scikit-learn rather than the torch loop.
    """
    if spec.family == "logistic_regression":
        return None
    if spec.family == "mlp":
        return BaselineMLP(
            n_features=int(n_features[spec.views[0]]),
            n_classes=int(n_classes),
            embed_dim=int(training["embedding_dim"]),
            hidden_dim=int(training["hidden_dim"]),
        )
    common = {
        "n_features_a": int(n_features[VIEW_A]),
        "n_features_b": int(n_features[VIEW_B]),
        "n_classes": int(n_classes),
        "embed_dim": int(training["embedding_dim"]),
        "hidden_dim": int(training["hidden_dim"]),
    }
    if spec.family == "concat_fusion":
        return ConcatFusionModel(**common)
    if spec.family == "gated_fusion":
        return GatedFusionModel(**common)
    raise ValueError(f"unknown model family {spec.family!r}")


def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray,
    donor_ids: np.ndarray,
    metrics: Sequence[str],
    n_classes: int,
    n_replicates: int,
    level: float,
    seed: int,
) -> dict[str, dict[str, Any]]:
    """Score one held-out prediction set, with donor intervals where they apply.

    Label-only metrics get a donor-cluster bootstrap interval. Probability metrics are
    reported as point values here; their spread comes from the across-seed summary.
    """
    entries: dict[str, dict[str, Any]] = {}
    for name in metrics:
        metric_fn = INTERVAL_METRICS.get(name)
        if metric_fn is None:
            continue
        result = donor_bootstrap(
            metric_fn,
            y_true,
            y_pred,
            donor_ids,
            n_replicates=int(n_replicates),
            level=float(level),
            seed=int(seed),
        )
        entries[name] = {
            "value": result.estimate,
            "not_applicable": result.not_applicable,
            "interval": [result.lower, result.upper],
            "unit": result.unit,
            "n_valid": result.n_valid,
            "n_failed": result.n_failed,
        }
    computed = compute_metrics(y_true, y_pred, y_prob, n_classes=int(n_classes))
    for name in metrics:
        if name in entries:
            continue
        result = computed[name]
        entries[name] = {
            "value": result.value,
            "not_applicable": result.not_applicable
            or "donor interval not computed for this metric; see the across-seed summary",
        }
    return entries


def summarize_routing(
    model: Any, views: Mapping[str, np.ndarray], labels: np.ndarray
) -> dict[str, Any]:
    """Summarise routing weights on held-out cells.

    Routing weights report how the gate scaled each branch. They are a signal, not
    evidence that the prediction depended on a view; that question belongs to the
    interventions in :mod:`p22.eval.faithfulness`.
    """
    if not hasattr(model, "has_gate"):
        return {}
    import torch

    tensors = {
        name: torch.as_tensor(np.asarray(matrix, dtype=np.float32))
        for name, matrix in views.items()
    }
    model.eval()
    with torch.no_grad():
        output = forward_views(model, tensors)
    weights = output.routing_weights.cpu().numpy()
    summary: dict[str, Any] = {
        "has_gate": bool(getattr(model, "has_gate", False)),
        "mean_weight_view_a": float(weights[:, 0].mean()),
        "mean_weight_view_b": float(weights[:, 1].mean()),
        "std_weight_view_a": float(weights[:, 0].std()),
        "min_weight_view_a": float(weights[:, 0].min()),
        "max_weight_view_a": float(weights[:, 0].max()),
        "weights_sum_to_one": bool(np.allclose(weights.sum(axis=1), 1.0, atol=1e-5)),
        "reading": "routing weight is a contribution signal, not evidence of dependence",
    }
    for label in np.unique(labels):
        mask = labels == label
        summary[f"mean_weight_view_a_label_{label}"] = float(weights[mask, 0].mean())
    return summary


def run_one_seed(
    config: RunConfig,
    seed: int,
    registry: RunRegistry | None = None,
    n_replicates: int | None = None,
) -> SeedRun:
    """Run every configured model for one seed.

    Args:
        config: validated run configuration.
        seed: seed controlling data generation, splitting, and training.
        registry: optional registry; when given, one record per model is written.
        n_replicates: override the bootstrap replicate count, for fast tests.

    Returns:
        A :class:`SeedRun` holding one :class:`ModelOutcome` per configured model.

    Raises:
        ValueError: if the configuration is not synthetic, or if the split, transform,
            or training steps reject their inputs.
    """
    require_synthetic(config.data_mode)
    set_all_seeds(seed)

    dataset = make_synthetic_multimodal(**config.dataset, seed=int(seed))
    raw_views = {VIEW_A: dataset.view_a, VIEW_B: dataset.view_b}

    # 1. Donors are split before any transform sees a cell.
    split = make_donor_split(
        dataset.donor_ids,
        labels=dataset.labels,
        val_fraction=float(config.split["val_fraction"]),
        test_fraction=float(config.split["test_fraction"]),
        seed=int(seed),
    )
    split_summary = validate_donor_split(split, dataset.donor_ids, labels=dataset.labels)

    # 2. Transforms are fitted on training cells only, then frozen.
    train_ids = dataset.cell_ids[split.train_index]
    holdout_ids = np.concatenate(
        [dataset.cell_ids[split.val_index], dataset.cell_ids[split.test_index]]
    )
    transformed: dict[str, np.ndarray] = {}
    transform_metadata: dict[str, Any] = {}
    for view_name, matrix in raw_views.items():
        fitted = fit_train_only(
            matrix,
            dataset.cell_ids,
            train_ids,
            holdout_ids,
            kind=str(config.transform["kind"]),
            n_components=config.transform["n_components"],
            seed=int(seed),
        )
        transformed[view_name] = fitted.transform(matrix)
        transform_metadata[view_name] = fitted.metadata
    transform_metadata["fit_scope"] = "train cells only"
    transform_metadata["kind"] = str(config.transform["kind"])

    def subset(index: np.ndarray) -> dict[str, np.ndarray]:
        return {name: matrix[index] for name, matrix in transformed.items()}

    train_views, val_views = subset(split.train_index), subset(split.val_index)
    train_labels = dataset.labels[split.train_index]
    val_labels = dataset.labels[split.val_index]

    fingerprint = data_fingerprint(raw_views, dataset.labels, dataset.donor_ids)
    donor_counts = {
        key: int(value) for key, value in split.summary["realized_donor_counts"].items()
    }
    cell_counts = {key: int(value) for key, value in split.summary["realized_cell_counts"].items()}
    n_features = {name: int(matrix.shape[1]) for name, matrix in transformed.items()}
    replicates = int(n_replicates if n_replicates is not None else config.bootstrap["n_replicates"])

    outcomes: dict[str, ModelOutcome] = {}
    for spec in config.models:
        # 3. Each model gets its own single-use view of the test split.
        holdout = SingleUseHoldout(
            views={name: transformed[name][split.test_index] for name in spec.views},
            labels=dataset.labels[split.test_index],
            donor_ids=dataset.donor_ids[split.test_index],
        )
        model_train = {name: train_views[name] for name in spec.views}
        model_val = {name: val_views[name] for name in spec.views}

        if spec.family == "logistic_regression":
            model, training_record = _fit_logistic_regression(
                model_train, train_labels, model_val, val_labels, seed=int(seed)
            )
        else:
            module = build_model(spec, n_features, int(dataset.labels.max()) + 1, config.training)
            trained = train_model(
                module,
                model_train,
                train_labels,
                model_val,
                val_labels,
                max_epochs=int(config.training["max_epochs"]),
                batch_size=int(config.training["batch_size"]),
                learning_rate=float(config.training["learning_rate"]),
                patience=int(config.training["patience"]),
                seed=int(seed),
                device=str(config.training["device"]),
            )
            model = trained.model
            training_record = trained.to_dict()

        # 4. One test evaluation, once.
        test_views, test_labels, test_donors = holdout.take(spec.name)
        if spec.family == "logistic_regression":
            features = np.hstack([test_views[name] for name in spec.views])
            probabilities = model.predict_proba(features)
            predictions = probabilities.argmax(axis=1)
            routing: dict[str, Any] = {}
        else:
            predictions, probabilities = predict(
                model, test_views, device=str(config.training["device"])
            )
            routing = summarize_routing(model, test_views, test_labels)

        outcomes[spec.name] = ModelOutcome(
            model_name=spec.name,
            family=spec.family,
            views=tuple(spec.views),
            seed=int(seed),
            metrics=evaluate_predictions(
                test_labels,
                predictions,
                probabilities,
                test_donors,
                metrics=config.metrics,
                n_classes=int(dataset.labels.max()) + 1,
                n_replicates=replicates,
                level=float(config.bootstrap["level"]),
                seed=int(seed),
            ),
            training=training_record,
            routing_signals=routing,
        )

    run = SeedRun(
        seed=int(seed),
        config_hash=config.config_hash,
        donor_counts=donor_counts,
        cell_counts=cell_counts,
        data_fingerprint=fingerprint,
        transform_metadata=transform_metadata,
        split_summary=split_summary,
        outcomes=outcomes,
    )
    if registry is not None:
        for outcome in outcomes.values():
            registry.write(build_record(config, run, outcome))
    return run


def build_record(config: RunConfig, run: SeedRun, outcome: ModelOutcome) -> RunRecord:
    """Turn one model outcome into a storable run record."""
    return RunRecord.create(
        config=config,
        model=outcome.model_name,
        seeds=(run.seed,),
        data_fingerprint=run.data_fingerprint,
        donor_counts=run.donor_counts,
        cell_counts=run.cell_counts,
        transform_metadata=run.transform_metadata,
        metrics=outcome.metrics,
        evidence_labels=("experimental result", "verified"),
        routing_signals=outcome.routing_signals,
        notes=(
            f"Model family {outcome.family} reading {', '.join(outcome.views)}.",
            "Selection used the validation split only; the test split was evaluated once.",
        ),
    )


def run_all_seeds(
    config: RunConfig,
    seeds: Sequence[int] | None = None,
    registry: RunRegistry | None = None,
    n_replicates: int | None = None,
) -> tuple[SeedRun, ...]:
    """Run the full benchmark for every configured seed.

    Args:
        config: validated run configuration.
        seeds: seeds to run; defaults to the configuration's seeds.
        registry: optional registry for run records.
        n_replicates: override the bootstrap replicate count.

    Returns:
        One :class:`SeedRun` per seed, in the order given.

    Raises:
        ValueError: if the seed list is empty or contains repeats.
    """
    chosen = tuple(int(seed) for seed in (seeds if seeds is not None else config.seeds))
    if not chosen:
        raise ValueError("run_all_seeds needs at least one seed")
    if len(set(chosen)) != len(chosen):
        raise ValueError(f"seeds must be unique, got {list(chosen)}")
    return tuple(
        run_one_seed(config, seed, registry=registry, n_replicates=n_replicates) for seed in chosen
    )


def summarize_across_seeds(
    runs: Sequence[SeedRun],
    metrics: Sequence[str] | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Summarise each model and metric across seeds.

    Args:
        runs: seed runs to combine.
        metrics: metrics to summarise; defaults to every metric present.

    Returns:
        A mapping of model name to metric name to a seed summary dictionary.

    Raises:
        ValueError: if no runs are given or the runs used different configurations.
    """
    if not runs:
        raise ValueError("summarize_across_seeds needs at least one run")
    hashes = {run.config_hash for run in runs}
    if len(hashes) != 1:
        raise ValueError(f"runs come from {len(hashes)} different configurations: {sorted(hashes)}")

    model_names = sorted({name for run in runs for name in run.outcomes})
    chosen_metrics = tuple(
        metrics
        if metrics is not None
        else sorted(
            {
                metric
                for run in runs
                for outcome in run.outcomes.values()
                for metric in outcome.metrics
            }
        )
    )
    summary: dict[str, dict[str, dict[str, Any]]] = {}
    for model_name in model_names:
        summary[model_name] = {}
        for metric in chosen_metrics:
            values = [
                run.outcomes[model_name].metrics.get(metric, {}).get("value")
                for run in runs
                if model_name in run.outcomes
            ]
            summary[model_name][metric] = summarize_seeds(values, metric=metric).to_dict()
    return summary


def _fit_logistic_regression(
    train_views: Mapping[str, np.ndarray],
    train_labels: np.ndarray,
    val_views: Mapping[str, np.ndarray],
    val_labels: np.ndarray,
    seed: int,
) -> tuple[LogisticRegression, dict[str, Any]]:
    """Fit logistic regression on train, choosing regularisation on validation only."""
    train_features = np.hstack([train_views[name] for name in sorted(train_views)])
    val_features = np.hstack([val_views[name] for name in sorted(val_views)])
    history = []
    best_model: LogisticRegression | None = None
    best_score = -float("inf")
    best_strength = None
    for strength in LOGISTIC_REGULARISATION_GRID:
        candidate = LogisticRegression(
            C=float(strength), max_iter=2000, random_state=int(seed), n_jobs=1
        )
        candidate.fit(train_features, train_labels)
        scored = balanced_accuracy(val_labels, candidate.predict(val_features))
        if not scored.applicable:
            raise ValueError(
                f"validation split cannot support balanced_accuracy: {scored.not_applicable}"
            )
        history.append(
            {"inverse_regularisation": float(strength), "val_score": float(scored.value)}
        )
        if float(scored.value) > best_score:
            best_score = float(scored.value)
            best_model = candidate
            best_strength = float(strength)
    assert best_model is not None
    return best_model, {
        "selection_metric": "balanced_accuracy",
        "selection_split": "val",
        "best_val_score": best_score,
        "chosen_inverse_regularisation": best_strength,
        "grid": list(LOGISTIC_REGULARISATION_GRID),
        "history": history,
        "seed": int(seed),
        "device": "cpu",
        "solver": "lbfgs",
    }
