"""Bag-level training loop for the gated-attention MIL head.

A bag is one donor's cells; the donor label is the bag label. Every donor gets the
same total influence per epoch (its bags' losses are averaged, then donors are
averaged), so a donor with many cells does not dominate one with few. The test
split is never an argument: selection reads one bag per validation donor only.

Auxiliary losses (N6 adversary, N7 InfoNCE) are injected as callables
``fn(batch_out, batch_meta) -> (name, tensor)``. The returned tensor is already
scaled by its own weight and is added to that bag's loss.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
import torch
from torch import nn

from p22.training.bags import make_bags
from p22.training.loop import EpochRecord, TrainedModel, set_all_seeds

DEFAULT_CFG: dict[str, Any] = {
    "bag_size": 64,
    "learning_rate": 1e-3,
    "max_epochs": 30,
    "patience": 6,
    "seed": 0,
    "device": "cpu",
}

AuxLoss = Callable[[dict[str, Any], dict[str, Any]], tuple[str, torch.Tensor]]


def _view_tensors(arrays: Mapping[str, np.ndarray], device: str, n_cells: int) -> dict:
    """Cast per-view matrices to ``(n_cells, n_features)`` float32 tensors."""
    if not arrays:
        raise ValueError("views must not be empty")
    tensors = {}
    for name, matrix in arrays.items():
        tensor = torch.as_tensor(np.asarray(matrix, dtype=np.float32), device=device)
        if tensor.ndim != 2 or tensor.shape[0] != n_cells:
            raise ValueError(
                f"view {name!r} must be (n_cells={n_cells}, n_features), "
                f"got {tuple(tensor.shape)}"
            )
        if not bool(torch.isfinite(tensor).all()):
            raise ValueError(f"view {name!r} contains non-finite values")
        tensors[name] = tensor
    return tensors


def _donor_label_map(donors: np.ndarray, labels: np.ndarray) -> dict[str, int]:
    """Return one binary label per donor, rejecting a donor with mixed labels."""
    donors = np.asarray(donors).astype(str)
    labels = np.asarray(labels)
    if donors.ndim != 1 or labels.ndim != 1 or len(donors) != len(labels):
        raise ValueError("donors and labels must be one-dimensional and equal length")
    if not np.isin(labels, [0, 1]).all():
        raise ValueError("labels must be binary 0/1")
    mapping: dict[str, int] = {}
    for donor, label in zip(donors.tolist(), labels.tolist(), strict=True):
        if donor in mapping and mapping[donor] != int(label):
            raise ValueError(f"donor {donor!r} carries both labels")
        mapping[donor] = int(label)
    return mapping


def _bag_batch(
    model: nn.Module,
    tensors: Mapping[str, torch.Tensor],
    bag: np.ndarray,
    meta: dict[str, Any],
    device: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Forward one bag, returning the model outputs and a metadata dict."""
    index = torch.as_tensor(bag, dtype=torch.long, device=device)
    views = {name: tensor[index] for name, tensor in tensors.items()}
    logit_bag, attention, cell_logits = model.forward_bag(views)
    batch_out = {
        "views": views,
        "logit_bag": logit_bag,
        "attention": attention,
        "cell_logits": cell_logits,
        "embeddings": model.embed(views),
    }
    return batch_out, meta


def _train_mil_epoch(
    model: nn.Module,
    tensors: Mapping[str, torch.Tensor],
    donors: np.ndarray,
    bags: Sequence[np.ndarray],
    donor_to_label: Mapping[str, int],
    optimiser: torch.optim.Optimizer,
    criterion: nn.Module,
    aux_losses: Sequence[AuxLoss],
    epoch: int,
    max_epochs: int,
    device: str,
) -> float:
    """One epoch: average each donor's bag losses, then average donors."""
    model.train()
    by_donor: dict[str, list[np.ndarray]] = {}
    for bag in bags:
        by_donor.setdefault(str(donors[bag[0]]), []).append(bag)

    epoch_total = 0.0
    for donor, donor_bags in by_donor.items():
        label = torch.tensor(float(donor_to_label[donor]), device=device)
        optimiser.zero_grad()
        donor_loss = torch.zeros((), device=device)
        for bag in donor_bags:
            meta = {
                "donor": donor,
                "label": donor_to_label[donor],
                "epoch": epoch,
                "progress": epoch / max_epochs,
            }
            batch_out, meta = _bag_batch(model, tensors, bag, meta, device)
            loss = criterion(batch_out["logit_bag"].squeeze(0), label)
            donor_loss = donor_loss + loss.squeeze()
            for aux in aux_losses:
                _name, term = aux(batch_out, meta)
                donor_loss = donor_loss + term
        donor_loss = donor_loss / len(donor_bags)
        if not bool(torch.isfinite(donor_loss)):
            raise ValueError("non-finite MIL training loss")
        donor_loss.backward()
        optimiser.step()
        epoch_total += float(donor_loss.detach())
    return epoch_total / len(by_donor)


def _validation_log_loss(
    model: nn.Module,
    tensors: Mapping[str, torch.Tensor],
    donors: np.ndarray,
    donor_to_label: Mapping[str, int],
    device: str,
) -> float:
    """Donor log-loss with one bag (all cells) per validation donor."""
    model.eval()
    criterion = nn.BCEWithLogitsLoss()
    total = 0.0
    with torch.no_grad():
        for donor, label in donor_to_label.items():
            index = torch.as_tensor(np.flatnonzero(donors == donor), device=device)
            views = {name: tensor[index] for name, tensor in tensors.items()}
            logit_bag, _attention, _cell_logits = model.forward_bag(views)
            target = torch.tensor(float(label), device=device)
            total += float(criterion(logit_bag.squeeze(0), target))
    return total / len(donor_to_label)


def train_mil(
    model: nn.Module,
    train_arrays: Mapping[str, np.ndarray],
    donors: Sequence[str] | np.ndarray,
    labels: Sequence[int] | np.ndarray,
    val_arrays: Mapping[str, np.ndarray],
    val_donors: Sequence[str] | np.ndarray,
    val_labels: Sequence[int] | np.ndarray,
    cfg: Mapping[str, Any] | None = None,
    aux_losses: Sequence[AuxLoss] = (),
) -> TrainedModel:
    """Fit a MIL model on donor bags, selecting on validation donor log-loss.

    Args:
        model: a :class:`~p22.models.mil.MILWrapper`.
        train_arrays: training features per view.
        donors: per-cell donor ID for each training cell.
        labels: per-cell binary label (inherited from the donor).
        val_arrays: validation features per view, same view names.
        val_donors: per-cell donor ID for each validation cell.
        val_labels: per-cell binary label for validation cells.
        cfg: overrides for :data:`DEFAULT_CFG`.
        aux_losses: auxiliary loss callables (see module docstring).

    Returns:
        A :class:`~p22.training.loop.TrainedModel` with the best-validation
        weights restored. ``best_val_score`` is the negative donor log-loss, so
        higher is better; ``selection_metric`` names that convention.

    Raises:
        ValueError: on malformed inputs or overlapping train/validation donors.
    """
    options = {**DEFAULT_CFG, **(dict(cfg) if cfg else {})}
    for name in ("bag_size", "max_epochs", "patience"):
        if type(options[name]) is not int or options[name] < 1:
            raise ValueError(f"{name} must be a positive int, got {options[name]!r}")
    if not 0.0 < float(options["learning_rate"]) < 1.0:
        raise ValueError("learning_rate must lie in (0, 1)")

    device = str(options["device"])
    donors = np.asarray(donors).astype(str)
    val_donors = np.asarray(val_donors).astype(str)
    train_tensors = _view_tensors(train_arrays, device, len(donors))
    val_tensors = _view_tensors(val_arrays, device, len(val_donors))
    if sorted(train_tensors) != sorted(val_tensors):
        raise ValueError(
            f"train views {sorted(train_tensors)} do not match val views {sorted(val_tensors)}"
        )
    donor_to_label = _donor_label_map(donors, np.asarray(labels))
    val_donor_label = _donor_label_map(val_donors, np.asarray(val_labels))
    if set(donor_to_label) & set(val_donor_label):
        raise ValueError("train and validation donor IDs overlap")

    seeds = set_all_seeds(int(options["seed"]))
    model = model.to(device)
    optimiser = torch.optim.Adam(model.parameters(), lr=float(options["learning_rate"]))
    criterion = nn.BCEWithLogitsLoss(reduction="none")

    history: list[EpochRecord] = []
    best_score = -float("inf")
    best_epoch = 0
    best_state = copy.deepcopy(model.state_dict())
    epochs_without_improvement = 0
    stopped_early = False

    for epoch in range(1, int(options["max_epochs"]) + 1):
        bags = make_bags(donors, int(options["bag_size"]), int(options["seed"]), epoch)
        if not bags:
            raise ValueError("no donor produced a bag at this bag_size")
        train_loss = _train_mil_epoch(
            model, train_tensors, donors, bags, donor_to_label, optimiser,
            criterion, aux_losses, epoch, int(options["max_epochs"]), device,
        )
        val_log_loss = _validation_log_loss(
            model, val_tensors, val_donors, val_donor_label, device
        )
        val_score = -val_log_loss
        history.append(EpochRecord(epoch=epoch, train_loss=train_loss, val_score=val_score))
        if val_score > best_score:
            best_score = val_score
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= int(options["patience"]):
                stopped_early = epoch < int(options["max_epochs"])
                break

    model.load_state_dict(best_state)
    model.eval()
    return TrainedModel(
        model=model,
        history=tuple(history),
        best_epoch=best_epoch,
        best_val_score=best_score,
        selection_metric="negative_donor_log_loss",
        epochs_run=len(history),
        stopped_early=stopped_early,
        seed=seeds["torch"],
        device=device,
        selection_unit="donor",
        training_weighting="equal_donor_bags",
    )


def predict_mil(
    model: nn.Module,
    arrays: Mapping[str, np.ndarray],
    donors: Sequence[str] | np.ndarray,
    device: str = "cpu",
) -> dict[str, Any]:
    """Score held-out cells and their donors with one bag per donor.

    Returns:
        A dict with ``donor_ids`` (sorted), ``donor_probabilities``,
        ``donor_logits``, ``cell_logits`` (``(n_cells,)``) and ``attention``
        (``(n_cells,)``, summing to one within each donor).
    """
    donors = np.asarray(donors).astype(str)
    tensors = _view_tensors(arrays, device, len(donors))
    model = model.to(device)
    model.eval()
    cell_logits = np.zeros(len(donors), dtype=np.float64)
    attention = np.zeros(len(donors), dtype=np.float64)
    donor_ids: list[str] = []
    donor_logits: list[float] = []
    donor_probs: list[float] = []
    with torch.no_grad():
        for donor in sorted(set(donors.tolist())):
            index = np.flatnonzero(donors == donor)
            rows = torch.as_tensor(index, dtype=torch.long, device=device)
            views = {name: tensor[rows] for name, tensor in tensors.items()}
            logit_bag, att, cell = model.forward_bag(views)
            cell_logits[index] = cell.cpu().numpy()
            attention[index] = att.cpu().numpy()
            donor_ids.append(donor)
            donor_logits.append(float(logit_bag.squeeze()))
            donor_probs.append(float(torch.sigmoid(logit_bag).squeeze()))
    return {
        "donor_ids": donor_ids,
        "donor_probabilities": np.asarray(donor_probs),
        "donor_logits": np.asarray(donor_logits),
        "cell_logits": cell_logits,
        "attention": attention,
    }
