"""A training loop that cannot see the test split.

Model selection reads the validation split and nothing else: the test arrays are not
parameters of this function, so there is no way to tune against them from here. Seeds are
set for Python, NumPy, and PyTorch together, and the device is CPU unless a caller asks
for something else on purpose.
"""

from __future__ import annotations

import copy
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
from torch import nn

from p22.data.group_splits import (
    _donor_labels_for_stratification,
    aggregate_donor_probabilities,
)
from p22.data.splits import _as_donor_array
from p22.eval.metrics import (
    accuracy,
    balanced_accuracy,
    macro_f1,
    weighted_f1,
)
from p22.models.fusion import VIEW_A, VIEW_B, FusionOutput

DEFAULT_DEVICE = "cpu"
SELECTION_METRICS = {
    "accuracy": accuracy,
    "balanced_accuracy": balanced_accuracy,
    "macro_f1": macro_f1,
    "weighted_f1": weighted_f1,
}


def set_all_seeds(seed: int) -> dict[str, int]:
    """Seed Python, NumPy, and PyTorch from one number.

    Args:
        seed: non-negative seed.

    Returns:
        A record of what was seeded, for storage in a run record.

    Raises:
        ValueError: if the seed is negative or not an integer.
    """
    if not isinstance(seed, (int, np.integer)) or isinstance(seed, bool):
        raise ValueError(f"seed must be an int, got {seed!r}")
    if int(seed) < 0:
        raise ValueError(f"seed must be non-negative, got {seed}")
    value = int(seed)
    random.seed(value)
    np.random.seed(value)
    torch.manual_seed(value)
    return {"python_random": value, "numpy": value, "torch": value}


@dataclass(frozen=True)
class EpochRecord:
    """One epoch of training, scored on the validation split."""

    epoch: int
    train_loss: float
    val_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "epoch": self.epoch,
            "train_loss": self.train_loss,
            "val_score": self.val_score,
        }


@dataclass
class TrainedModel:
    """A trained model together with how it was selected.

    Attributes:
        model: the model with the best validation weights restored.
        history: per-epoch training loss and validation score.
        best_epoch: epoch whose weights were kept.
        best_val_score: validation score at that epoch.
        selection_metric: metric used for selection.
        epochs_run: epochs actually executed.
        stopped_early: whether patience ended training before ``max_epochs``.
        seed: seed used.
        device: device used.
    """

    model: nn.Module
    history: tuple[EpochRecord, ...]
    best_epoch: int
    best_val_score: float
    selection_metric: str
    epochs_run: int
    stopped_early: bool
    seed: int
    device: str
    selection_unit: str = "cell"
    training_weighting: str = "uniform_cell"

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection_metric": self.selection_metric,
            "selection_split": "val",
            "selection_unit": self.selection_unit,
            "training_weighting": self.training_weighting,
            "best_epoch": self.best_epoch,
            "best_val_score": self.best_val_score,
            "epochs_run": self.epochs_run,
            "stopped_early": self.stopped_early,
            "seed": self.seed,
            "device": self.device,
            "history": [record.to_dict() for record in self.history],
        }


def forward_logits(
    model: nn.Module,
    views: Mapping[str, torch.Tensor],
    **forward_kwargs: Any,
) -> torch.Tensor:
    """Return logits from a single-view or two-view model.

    Args:
        model: a single-view baseline or a two-view fusion model.
        views: mapping of view name to feature tensor. A single-view model needs
            exactly one entry; a fusion model needs both.
        **forward_kwargs: passed through to a fusion model's forward pass.

    Returns:
        A ``(n_cells, n_classes)`` tensor of logits.

    Raises:
        ValueError: if the view mapping does not match what the model reads.
    """
    output = forward_views(model, views, **forward_kwargs)
    return output.logits if isinstance(output, FusionOutput) else output


def forward_views(
    model: nn.Module,
    views: Mapping[str, torch.Tensor],
    **forward_kwargs: Any,
) -> torch.Tensor | FusionOutput:
    """Run a forward pass, returning the model's native output type."""
    is_fusion = hasattr(model, "has_gate")
    if is_fusion:
        missing = [name for name in (VIEW_A, VIEW_B) if name not in views]
        if missing:
            raise ValueError(f"fusion model needs view(s) {missing}")
        return model(views[VIEW_A], views[VIEW_B], **forward_kwargs)
    if len(views) != 1:
        raise ValueError(f"single-view model reads exactly one view, got {sorted(views)}")
    if forward_kwargs:
        raise ValueError(f"single-view model does not accept {sorted(forward_kwargs)}")
    return model(next(iter(views.values())))


def train_model(
    model: nn.Module,
    train_views: Mapping[str, np.ndarray | torch.Tensor],
    train_labels: Sequence[int] | np.ndarray,
    val_views: Mapping[str, np.ndarray | torch.Tensor],
    val_labels: Sequence[int] | np.ndarray,
    max_epochs: int = 40,
    batch_size: int = 64,
    learning_rate: float = 1e-3,
    patience: int = 8,
    seed: int = 0,
    selection_metric: str = "balanced_accuracy",
    device: str = DEFAULT_DEVICE,
    train_donor_ids: Sequence[str] | None = None,
    val_donor_ids: Sequence[str] | None = None,
) -> TrainedModel:
    """Fit a model on the training split and select the epoch on validation.

    The test split is not an argument here, by design: selection cannot reach it.

    Args:
        model: model to fit in place.
        train_views: training features per view.
        train_labels: training labels.
        val_views: validation features per view, same view names as training.
        val_labels: validation labels.
        max_epochs: maximum epochs.
        batch_size: minibatch size.
        learning_rate: Adam learning rate.
        patience: epochs without improvement before stopping.
        seed: seed for shuffling and initialisation-time randomness.
        selection_metric: validation metric maximised during selection.
        device: torch device; CPU by default.
        train_donor_ids: optional donor IDs for equal-donor loss weighting.
        val_donor_ids: supply with train IDs for binary donor-mean probability
            selection at threshold 0.5. Donors must be disjoint between splits.

    Returns:
        A :class:`TrainedModel` with the best validation weights restored.

    Raises:
        ValueError: on empty or mismatched inputs, mismatched view names, invalid
            hyperparameters, an unknown selection metric, or a validation split that
            cannot support the selection metric.
    """
    if selection_metric not in SELECTION_METRICS:
        raise ValueError(
            f"unknown selection_metric {selection_metric!r}; expected one of "
            f"{sorted(SELECTION_METRICS)}"
        )
    for name, value in (
        ("max_epochs", max_epochs),
        ("batch_size", batch_size),
        ("patience", patience),
    ):
        if not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive int, got {value!r}")
    if not 0.0 < float(learning_rate) < 1.0:
        raise ValueError(f"learning_rate must lie in (0, 1), got {learning_rate}")

    donor_mode = train_donor_ids is not None or val_donor_ids is not None
    weights = None
    if donor_mode:
        if train_donor_ids is None or val_donor_ids is None:
            raise ValueError("supply both train_donor_ids and val_donor_ids")
        train_donors, _ = _binary_donors(train_donor_ids, train_labels)
        val_donors, donor_val_labels = _binary_donors(val_donor_ids, val_labels)
        if set(train_donors) & set(val_donors):
            raise ValueError("train and validation donor IDs overlap")
        _, inverse, counts = np.unique(train_donors, return_inverse=True, return_counts=True)
        weights = torch.as_tensor(
            len(train_donors) / (len(counts) * counts[inverse]),
            dtype=torch.float32,
            device=device,
        )

    train_tensors, train_target = _prepare(train_views, train_labels, "train", device)
    val_tensors, val_target = _prepare(val_views, val_labels, "val", device)
    if sorted(train_tensors) != sorted(val_tensors):
        raise ValueError(
            f"train views {sorted(train_tensors)} do not match val views {sorted(val_tensors)}"
        )
    for view_name in train_tensors:
        train_width = train_tensors[view_name].shape[1]
        val_width = val_tensors[view_name].shape[1]
        if train_width != val_width:
            raise ValueError(
                f"view {view_name!r} has {train_width} training features but {val_width} in val"
            )

    seeds = set_all_seeds(seed)
    model = model.to(device)
    generator = torch.Generator().manual_seed(int(seed))
    optimiser = torch.optim.Adam(model.parameters(), lr=float(learning_rate))
    # Unreduced loss permits per-cell weights, not class weights.
    # https://docs.pytorch.org/docs/2.8/generated/torch.nn.CrossEntropyLoss.html
    criterion = nn.CrossEntropyLoss(reduction="none" if donor_mode else "mean")
    metric_fn = SELECTION_METRICS[selection_metric]

    history: list[EpochRecord] = []
    best_score = -float("inf")
    best_epoch = 0
    best_state = copy.deepcopy(model.state_dict())
    epochs_without_improvement = 0
    stopped_early = False

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

        model.eval()
        with torch.no_grad():
            val_logits = forward_logits(model, val_tensors)
        if donor_mode:
            donor_predictions = aggregate_donor_probabilities(
                torch.softmax(val_logits, dim=1)[:, 1].cpu().numpy(), val_donors
            )
            scored = metric_fn(donor_val_labels, donor_predictions["prediction"].to_numpy())
        else:
            val_pred = val_logits.argmax(dim=1).cpu().numpy()
            scored = metric_fn(val_target.cpu().numpy(), val_pred)
        if not scored.applicable:
            raise ValueError(
                f"validation split cannot support {selection_metric!r}: {scored.not_applicable}"
            )
        history.append(
            EpochRecord(
                epoch=epoch,
                train_loss=epoch_loss,
                val_score=float(scored.value),
            )
        )

        if float(scored.value) > best_score:
            best_score = float(scored.value)
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
    return TrainedModel(
        model=model,
        history=tuple(history),
        best_epoch=best_epoch,
        best_val_score=best_score,
        selection_metric=selection_metric,
        epochs_run=len(history),
        stopped_early=stopped_early,
        seed=seeds["torch"],
        device=device,
        selection_unit="donor" if donor_mode else "cell",
        training_weighting="inverse_donor_cell_count" if donor_mode else "uniform_cell",
    )


def _train_epoch(model, tensors, target, weights, optimiser, criterion, generator, batch_size):
    """Shared update path for internal selection and fixed-epoch final refitting."""
    model.train()
    order = torch.randperm(len(target), generator=generator)
    epoch_loss = 0.0
    for start in range(0, len(target), batch_size):
        index = order[start : start + batch_size]
        batch = {name: tensor[index] for name, tensor in tensors.items()}
        optimiser.zero_grad()
        logits = forward_logits(model, batch)
        if weights is not None and logits.shape[1] != 2:
            raise ValueError("donor training requires two output classes")
        loss = criterion(logits, target[index])
        if weights is not None:
            # Global weights give each donor equal total influence, including short batches.
            loss = (loss * weights[index]).mean()
        if not bool(torch.isfinite(loss)):
            raise ValueError("non-finite training loss")
        loss.backward()
        optimiser.step()
        epoch_loss += float(loss.detach()) * index.numel()
    return epoch_loss / len(target)


def refit_model(
    model,
    views,
    labels,
    donor_ids,
    *,
    epochs,
    batch_size=64,
    learning_rate=1e-3,
    seed=0,
) -> dict:
    """Refit on all development donors for an internally frozen epoch count.

    No validation/test inputs or checkpoint selection. Mutates the supplied model.
    Uses the same Adam/loss/batching path as internal training, on CPU.
    """
    for name, value in (("epochs", epochs), ("batch_size", batch_size)):
        if type(value) is not int or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if isinstance(learning_rate, bool) or not 0 < learning_rate < 1:
        raise ValueError("learning_rate must be in (0, 1)")
    donors, _ = _binary_donors(donor_ids, labels)
    tensors, target = _prepare(views, labels, "development", "cpu")
    _, inverse, counts = np.unique(donors, return_inverse=True, return_counts=True)
    weights = torch.as_tensor(len(donors) / (len(counts) * counts[inverse]), dtype=torch.float32)
    set_all_seeds(seed)
    model.to("cpu")
    generator = torch.Generator().manual_seed(seed)
    optimiser = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.CrossEntropyLoss(reduction="none")
    losses = [
        _train_epoch(model, tensors, target, weights, optimiser, criterion, generator, batch_size)
        for _ in range(epochs)
    ]
    model.eval()
    return {
        "epochs_run": epochs,
        "train_loss": losses,
        "selection_split": None,
        "epoch_selection": "frozen before all-development refit",
        "training_weighting": "inverse_donor_cell_count",
        "seed": seed,
        "n_development_donors": len(counts),
    }


def _binary_donors(
    donor_ids: Sequence[str], labels: Sequence[int]
) -> tuple[np.ndarray, np.ndarray]:
    """Validate binary donor labels before any fitting or integer conversion."""
    donors = _as_donor_array(donor_ids).astype(str)
    target = np.asarray(labels)
    if target.ndim != 1 or len(target) != len(donors):
        raise ValueError("donor IDs and labels length mismatch")
    if not np.isin(target, [0, 1]).all() or set(target) != {0, 1}:
        raise ValueError("each split must contain both binary classes, 0 and 1")
    _, donor_labels = _donor_labels_for_stratification(donors, target)
    return donors, donor_labels


def predict(
    model: nn.Module,
    views: Mapping[str, np.ndarray | torch.Tensor],
    device: str = DEFAULT_DEVICE,
    **forward_kwargs: Any,
) -> tuple[np.ndarray, np.ndarray]:
    """Return predicted labels and class probabilities for one set of cells.

    Args:
        model: a trained model.
        views: features per view.
        device: torch device.
        **forward_kwargs: passed to a fusion model's forward pass.

    Returns:
        A tuple of predicted labels and a probability matrix whose rows sum to one.
    """
    tensors = {name: _as_tensor(matrix, name, device) for name, matrix in views.items()}
    model = model.to(device)
    model.eval()
    with torch.no_grad():
        logits = forward_logits(model, tensors, **forward_kwargs)
    probabilities = torch.softmax(logits, dim=1).cpu().numpy()
    return probabilities.argmax(axis=1), probabilities


def _prepare(
    views: Mapping[str, np.ndarray | torch.Tensor],
    labels: Sequence[int] | np.ndarray,
    split: str,
    device: str,
) -> tuple[dict[str, torch.Tensor], torch.Tensor]:
    if not views:
        raise ValueError(f"{split} views must not be empty")
    target = torch.as_tensor(np.asarray(labels), dtype=torch.long, device=device)
    if target.ndim != 1:
        raise ValueError(f"{split} labels must be one-dimensional, got shape {tuple(target.shape)}")
    if target.numel() == 0:
        raise ValueError(f"{split} split has no cells")
    tensors = {}
    for name, matrix in views.items():
        tensor = _as_tensor(matrix, name, device)
        if tensor.shape[0] != target.numel():
            raise ValueError(
                f"{split} view {name!r} has {tensor.shape[0]} cells but "
                f"{target.numel()} labels were given"
            )
        tensors[name] = tensor
    return tensors, target


def _as_tensor(matrix: np.ndarray | torch.Tensor, name: str, device: str) -> torch.Tensor:
    tensor = torch.as_tensor(np.asarray(matrix, dtype=np.float32), device=device)
    if tensor.ndim != 2:
        raise ValueError(f"view {name!r} must be two-dimensional, got shape {tuple(tensor.shape)}")
    if not bool(torch.isfinite(tensor).all()):
        raise ValueError(f"view {name!r} contains non-finite values")
    return tensor
