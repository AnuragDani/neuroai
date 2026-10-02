"""M7 measured-target training adapter for the masked ATAC pilot.

Reuses existing encoders/heads (``paired_model`` / ``predict``) and metric
helpers. Provides a **cell-target** training/selection path that allows mixed
accessibility labels within a donor — unlike ``mil_loop._donor_label_map`` and
``train_model`` donor-mode (which assume one class per donor).

Does **not** modify disease classification APIs. Neural smoke/main learning is
gated by M8 authorization in ``masked_atac_execute``; this module itself only
fits when a caller explicitly invokes the trainer (unit tests / authorized
executor).
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from torch import nn

from p22.eval.masked_atac_metrics import (
    ADAPTER_REQUIREMENTS,
    PROB_CLIP,
    donor_average_cell_log_loss,
)
from p22.eval.masked_atac_protocol import LOGREG_FROZEN, NEURAL, SELECTION_RULE
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.multiome_runner import model_inputs, paired_model
from p22.eval.s7_runner import donor_cell_weights
from p22.models.fusion import VIEW_A, VIEW_B
from p22.training.loop import (
    DEFAULT_DEVICE,
    EpochRecord,
    TrainedModel,
    _prepare,
    _train_epoch,
    forward_logits,
    predict,
    set_all_seeds,
)

SELECTION_METRIC_NAME = "donor_average_cell_log_loss"
ARM_TO_PAIRED_NAME: dict[str, str] = {
    "feature_concat_mlp": "rna_atac_concat",
    "token_concat": "token_concat",
    "cross_attention": "cross_attention",
}
NEURAL_ARMS: tuple[str, ...] = tuple(ARM_TO_PAIRED_NAME)
LOGREG_ARMS: tuple[str, ...] = ("logreg_rna", "logreg_visible_atac")


@dataclass(frozen=True)
class CellTargetTrainResult:
    """Adapter training outcome with cell-level predictions and hashes."""

    trained: TrainedModel
    initial_state_sha256: str
    checkpoint_sha256: str
    train_donor_average_cell_log_loss: float
    val_donor_average_cell_log_loss: float
    selection_rule: str
    adapter_requirements: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "training": self.trained.to_dict(),
            "initial_state_sha256": self.initial_state_sha256,
            "checkpoint_sha256": self.checkpoint_sha256,
            "train_donor_average_cell_log_loss": self.train_donor_average_cell_log_loss,
            "val_donor_average_cell_log_loss": self.val_donor_average_cell_log_loss,
            "selection_metric": SELECTION_METRIC_NAME,
            "selection_rule": self.selection_rule,
            "adapter_requirements": self.adapter_requirements,
        }


def state_dict_sha256(state: Mapping[str, Any]) -> str:
    hasher = hashlib.sha256()
    for key in sorted(state):
        hasher.update(key.encode("utf-8"))
        tensor = state[key]
        arr = (
            tensor.detach().cpu().numpy()
            if hasattr(tensor, "detach")
            else np.asarray(tensor)
        )
        hasher.update(np.ascontiguousarray(arr).tobytes())
    return hasher.hexdigest()


def assert_donors_allow_mixed_labels(
    donors: Sequence[str],
    labels: Sequence[int] | np.ndarray,
) -> dict[str, Any]:
    """Validate binary cell labels; mixed labels within a donor are allowed."""
    donor_arr = np.asarray(donors).astype(str).reshape(-1)
    y = np.asarray(labels)
    if y.ndim != 1 or y.shape[0] != donor_arr.shape[0]:
        raise ValueError("donors/labels length mismatch")
    if y.size == 0:
        raise ValueError("empty labels")
    if not np.isin(y, [0, 1]).all():
        raise ValueError("labels must be binary 0/1")
    unique = sorted(set(donor_arr.tolist()))
    mixed = []
    for donor in unique:
        vals = set(int(v) for v in y[donor_arr == donor].tolist())
        if vals == {0, 1}:
            mixed.append(donor)
    if set(int(v) for v in np.unique(y).tolist()) != {0, 1}:
        raise ValueError("each split must contain both binary classes, 0 and 1")
    return {
        "n_donors": len(unique),
        "n_cells": int(y.size),
        "mixed_label_donors": mixed,
        "mixed_labels_allowed": True,
    }


def _val_donor_average_cell_log_loss(
    model: nn.Module,
    val_tensors: Mapping[str, torch.Tensor],
    val_labels: np.ndarray,
    val_donors: np.ndarray,
    *,
    clip: float = PROB_CLIP,
) -> float:
    model.eval()
    with torch.no_grad():
        logits = forward_logits(model, val_tensors)
        probs = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()
    return float(
        donor_average_cell_log_loss(val_donors, val_labels, probs, clip=clip)["value"]
    )


def train_cell_target_model(
    model: nn.Module,
    train_views: Mapping[str, np.ndarray | torch.Tensor],
    train_labels: Sequence[int] | np.ndarray,
    train_donors: Sequence[str],
    val_views: Mapping[str, np.ndarray | torch.Tensor],
    val_labels: Sequence[int] | np.ndarray,
    val_donors: Sequence[str],
    *,
    max_epochs: int = 20,
    batch_size: int = 64,
    learning_rate: float = 1e-3,
    patience: int = 5,
    seed: int = 0,
    device: str = DEFAULT_DEVICE,
    clip: float = PROB_CLIP,
) -> CellTargetTrainResult:
    """Train with equal-donor cell weights; select by donor-average cell log-loss.

    Mixed cell labels within a donor are allowed. Minimises validation
    donor-average cell log-loss (does **not** use donor-mean probability or BA).
    """
    for name, value in (
        ("max_epochs", max_epochs),
        ("batch_size", batch_size),
        ("patience", patience),
    ):
        if not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive int, got {value!r}")
    if not 0.0 < float(learning_rate) < 1.0:
        raise ValueError(f"learning_rate must lie in (0, 1), got {learning_rate}")

    assert_donors_allow_mixed_labels(train_donors, train_labels)
    assert_donors_allow_mixed_labels(val_donors, val_labels)
    train_donor_arr = np.asarray(train_donors).astype(str).reshape(-1)
    val_donor_arr = np.asarray(val_donors).astype(str).reshape(-1)
    if set(train_donor_arr.tolist()) & set(val_donor_arr.tolist()):
        raise ValueError("train and validation donor IDs overlap")

    train_tensors, train_target = _prepare(train_views, train_labels, "train", device)
    val_tensors, _val_target = _prepare(val_views, val_labels, "val", device)
    if sorted(train_tensors) != sorted(val_tensors):
        raise ValueError(
            f"train views {sorted(train_tensors)} do not match val views "
            f"{sorted(val_tensors)}"
        )
    for view_name in train_tensors:
        if train_tensors[view_name].shape[1] != val_tensors[view_name].shape[1]:
            raise ValueError(f"view {view_name!r} width mismatch train vs val")

    weights_np = donor_cell_weights(train_donor_arr)
    weights = torch.as_tensor(weights_np, dtype=torch.float32, device=device)

    seeds = set_all_seeds(seed)
    model = model.to(device)
    initial_state = {
        key: value.detach().cpu().clone() for key, value in model.state_dict().items()
    }
    initial_sha = state_dict_sha256(initial_state)
    generator = torch.Generator().manual_seed(int(seed))
    optimiser = torch.optim.Adam(model.parameters(), lr=float(learning_rate))
    criterion = nn.CrossEntropyLoss(reduction="none")

    history: list[EpochRecord] = []
    best_loss = float("inf")
    best_epoch = 0
    best_state = copy.deepcopy(model.state_dict())
    epochs_without_improvement = 0
    stopped_early = False
    y_train = np.asarray(train_labels, dtype=np.int64)
    y_val = np.asarray(val_labels, dtype=np.int64)

    for epoch in range(1, int(max_epochs) + 1):
        epoch_loss = _train_epoch(
            model,
            train_tensors,
            train_target,
            weights,
            optimiser,
            criterion,
            generator,
            int(batch_size),
        )
        val_loss = _val_donor_average_cell_log_loss(
            model, val_tensors, y_val, val_donor_arr, clip=clip
        )
        # EpochRecord.val_score stores the selection metric; for this adapter
        # lower is better, so we store negative loss for monotonic "score" logs
        # while best_* uses the true loss for checkpointing.
        history.append(
            EpochRecord(
                epoch=epoch,
                train_loss=float(epoch_loss),
                val_score=float(-val_loss),
            )
        )
        if val_loss < best_loss - 0.0:
            best_loss = float(val_loss)
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= int(patience):
                stopped_early = epoch < int(max_epochs)
                break

    model.load_state_dict(best_state)
    model.eval()
    train_loss_final = _val_donor_average_cell_log_loss(
        model, train_tensors, y_train, train_donor_arr, clip=clip
    )
    val_loss_final = _val_donor_average_cell_log_loss(
        model, val_tensors, y_val, val_donor_arr, clip=clip
    )
    ckpt_sha = state_dict_sha256(model.state_dict())
    trained = TrainedModel(
        model=model,
        history=tuple(history),
        best_epoch=best_epoch,
        best_val_score=float(-best_loss),
        selection_metric=SELECTION_METRIC_NAME,
        epochs_run=len(history),
        stopped_early=stopped_early,
        seed=seeds["torch"],
        device=device,
        selection_unit="donor_mean_of_cell_log_loss",
        training_weighting="inverse_donor_cell_count",
    )
    return CellTargetTrainResult(
        trained=trained,
        initial_state_sha256=initial_sha,
        checkpoint_sha256=ckpt_sha,
        train_donor_average_cell_log_loss=float(train_loss_final),
        val_donor_average_cell_log_loss=float(val_loss_final),
        selection_rule=SELECTION_RULE,
        adapter_requirements=dict(ADAPTER_REQUIREMENTS),
    )


def fit_constant_prevalence(
    train_labels: Sequence[int] | np.ndarray,
    n_predict: int,
) -> dict[str, Any]:
    """Training-prevalence constant probability (zero learned parameters)."""
    y = np.asarray(train_labels, dtype=np.float64).reshape(-1)
    if y.size == 0:
        raise ValueError("empty train labels")
    if not np.isin(y, [0.0, 1.0]).all():
        raise ValueError("labels must be binary 0/1")
    prevalence = float(np.mean(y))
    p = np.full(int(n_predict), prevalence, dtype=np.float64)
    return {
        "arm": "training_prevalence_constant",
        "prevalence": prevalence,
        "probabilities": p,
        "n_parameters": 0,
        "fits_count": 0,
    }


def fit_logreg_cell_target(
    features: np.ndarray,
    labels: np.ndarray,
    donors: Sequence[str],
    train_idx: np.ndarray,
    predict_idx: np.ndarray,
    *,
    settings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Sklearn logistic regression with equal-donor cell sample weights."""
    cfg = dict(settings or LOGREG_FROZEN)
    x = np.asarray(features, dtype=np.float64)
    y = np.asarray(labels, dtype=np.int64)
    train = np.asarray(train_idx, dtype=np.int64)
    pred = np.asarray(predict_idx, dtype=np.int64)
    donor_arr = np.asarray(donors).astype(str)
    assert_donors_allow_mixed_labels(donor_arr[train], y[train])
    weights = donor_cell_weights(donor_arr[train])
    estimator = LogisticRegression(**cfg)
    estimator.fit(x[train], y[train], sample_weight=weights)
    probability = estimator.predict_proba(x[pred])[:, 1]
    return {
        "kind": "logreg",
        "probabilities": probability.astype(np.float64),
        "coef": estimator.coef_.tolist(),
        "intercept": estimator.intercept_.tolist(),
        "classes": estimator.classes_.tolist(),
        "settings": cfg,
    }


def fit_neural_cell_target(
    arm: str,
    views: Mapping[str, np.ndarray],
    labels: np.ndarray,
    donors: Sequence[str],
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    test_idx: np.ndarray,
    *,
    protocol: MultiomeProtocol | None = None,
) -> dict[str, Any]:
    """Build paired_model arm and train with the cell-target adapter."""
    if arm not in ARM_TO_PAIRED_NAME:
        raise ValueError(f"unknown neural arm {arm!r}; expected {NEURAL_ARMS}")
    proto = protocol or NEURAL
    paired_name = ARM_TO_PAIRED_NAME[arm]
    widths = [int(views[VIEW_A].shape[1]), int(views[VIEW_B].shape[1])]
    model = paired_model(paired_name, widths, proto)
    selected = model_inputs(paired_name, dict(views))
    train = np.asarray(train_idx, dtype=np.int64)
    val = np.asarray(val_idx, dtype=np.int64)
    test = np.asarray(test_idx, dtype=np.int64)
    donor_arr = np.asarray(donors).astype(str)
    result = train_cell_target_model(
        model,
        {key: value[train] for key, value in selected.items()},
        labels[train],
        donor_arr[train],
        {key: value[val] for key, value in selected.items()},
        labels[val],
        donor_arr[val],
        max_epochs=proto.max_epochs,
        batch_size=proto.batch_size,
        learning_rate=proto.learning_rate,
        patience=proto.patience,
        seed=proto.model_seed,
    )
    _, probs = predict(
        result.trained.model,
        {key: value[test] for key, value in selected.items()},
    )
    return {
        "arm": arm,
        "paired_name": paired_name,
        "widths": widths,
        "probabilities": probs[:, 1].astype(np.float64),
        "result": result.to_dict(),
        "model": result.trained.model,
    }


def check_finite_gradients_cell_target(
    arm: str,
    views: Mapping[str, np.ndarray],
    labels: np.ndarray,
    *,
    protocol: MultiomeProtocol | None = None,
    n_cells: int = 32,
) -> dict[str, Any]:
    """One forward+backward; no optimizer step (not a fit / smoke attempt)."""
    if arm not in ARM_TO_PAIRED_NAME:
        raise ValueError(f"neural arm required, got {arm!r}")
    proto = protocol or NEURAL
    paired_name = ARM_TO_PAIRED_NAME[arm]
    widths = [int(views[VIEW_A].shape[1]), int(views[VIEW_B].shape[1])]
    model = paired_model(paired_name, widths, proto)
    model.train()
    selected = model_inputs(paired_name, dict(views))
    take = min(int(n_cells), int(labels.shape[0]))
    tensors = {
        key: torch.as_tensor(value[:take], dtype=torch.float32)
        for key, value in selected.items()
    }
    y = torch.as_tensor(labels[:take], dtype=torch.long)
    logits = forward_logits(model, tensors)
    loss = nn.CrossEntropyLoss()(logits, y)
    model.zero_grad(set_to_none=True)
    loss.backward()
    grads: list[float] = []
    for param in model.parameters():
        if param.grad is None:
            continue
        g = param.grad.detach()
        if not torch.isfinite(g).all():
            return {
                "arm": arm,
                "finite": False,
                "loss": float(loss.detach()),
                "reason": "non-finite gradient tensor",
            }
        grads.append(float(g.abs().max()))
    if not grads:
        return {
            "arm": arm,
            "finite": False,
            "loss": float(loss.detach()),
            "reason": "no gradients produced",
        }
    return {
        "arm": arm,
        "finite": True,
        "loss": float(loss.detach()),
        "max_abs_grad": max(grads),
        "n_cells": take,
    }


def check_state_dict_reload_equality_cell_target(
    arm: str,
    views: Mapping[str, np.ndarray],
    *,
    protocol: MultiomeProtocol | None = None,
    n_cells: int = 32,
    atol: float = 1e-6,
) -> dict[str, Any]:
    """Build → predict → reload → predict; identity within atol (no fit)."""
    if arm not in ARM_TO_PAIRED_NAME:
        raise ValueError(f"neural arm required, got {arm!r}")
    proto = protocol or NEURAL
    paired_name = ARM_TO_PAIRED_NAME[arm]
    widths = [int(views[VIEW_A].shape[1]), int(views[VIEW_B].shape[1])]
    model = paired_model(paired_name, widths, proto)
    selected = model_inputs(paired_name, dict(views))
    take = min(int(n_cells), int(views[VIEW_A].shape[0]))
    subset = {key: value[:take] for key, value in selected.items()}
    _, probs_a = predict(model, subset)
    state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    model2 = paired_model(paired_name, widths, proto)
    model2.load_state_dict(state)
    _, probs_b = predict(model2, subset)
    max_diff = float(np.max(np.abs(probs_a - probs_b)))
    return {
        "arm": arm,
        "passed": bool(max_diff <= float(atol)),
        "max_abs_diff": max_diff,
        "atol": float(atol),
        "n_cells": take,
    }


def build_toy_mixed_label_fold(
    *,
    seed: int = 22,
    n_features: int = 8,
) -> dict[str, Any]:
    """Deterministic tiny fold with unequal cells and mixed labels per donor."""
    rng = np.random.default_rng(seed)
    # Donors: D0 (3 cells mixed), D1 (2 cells mixed), D2 (1 cell) train;
    # D3 (2 cells mixed) val; D4 (2 cells) test.
    donors = np.asarray(
        ["D0", "D0", "D0", "D1", "D1", "D2", "D3", "D3", "D4", "D4"],
        dtype=str,
    )
    labels = np.asarray([1, 0, 1, 0, 1, 0, 1, 0, 1, 0], dtype=np.int64)
    rna = rng.normal(size=(len(labels), n_features)).astype(np.float64)
    atac = rng.normal(size=(len(labels), n_features)).astype(np.float64)
    # Plant a weak RNA signal correlated with label for learnability checks.
    rna[:, 0] += labels.astype(np.float64) * 1.5
    train_idx = np.asarray([0, 1, 2, 3, 4, 5], dtype=np.int64)
    val_idx = np.asarray([6, 7], dtype=np.int64)
    test_idx = np.asarray([8, 9], dtype=np.int64)
    return {
        "donors": donors,
        "labels": labels,
        "views": {VIEW_A: rna, VIEW_B: atac},
        "train_idx": train_idx,
        "val_idx": val_idx,
        "test_idx": test_idx,
        "mixed_train_donors": ["D0", "D1"],
    }


def verify_selection_prefers_cell_log_loss_over_donor_mean_prob() -> dict[str, Any]:
    """Hand fixture: cell-log-loss ranking differs from donor-mean-prob collapse."""
    donors = ["A", "A", "A", "B", "B"]
    y = np.asarray([1, 0, 1, 0, 0], dtype=np.float64)
    # Candidate epoch predictions.
    p_good = np.asarray([0.9, 0.2, 0.85, 0.15, 0.25], dtype=np.float64)
    p_bad = np.asarray([0.55, 0.55, 0.55, 0.45, 0.45], dtype=np.float64)
    loss_good = donor_average_cell_log_loss(donors, y, p_good)["value"]
    loss_bad = donor_average_cell_log_loss(donors, y, p_bad)["value"]
    # Wrong statistic: donor-mean probability vs majority label.
    from p22.eval.masked_atac_metrics import refuse_donor_average_probability_as_primary

    wrong_good = refuse_donor_average_probability_as_primary(donors, y, p_good)
    wrong_bad = refuse_donor_average_probability_as_primary(donors, y, p_bad)
    return {
        "cell_log_loss_prefers_good": loss_good < loss_bad,
        "loss_good": loss_good,
        "loss_bad": loss_bad,
        "wrong_statistic_values_differ_from_correct": (
            wrong_good["values_differ"] and wrong_bad["values_differ"]
        ),
        "selection_metric": SELECTION_METRIC_NAME,
    }
