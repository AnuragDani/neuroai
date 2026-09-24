"""Cross-modal InfoNCE pairing loss and label-free retrieval metric (plan 4.3).

The pairing objective asks each cell's RNA branch embedding to identify its own
ATAC branch embedding among the other cells in the bag, and vice versa. It is
label-free: it never reads the donor label, only which rows came from the same
cell. ``z_R`` and ``z_A`` are the branch embeddings already produced by a fusion
encoder (:attr:`~p22.models.fusion.FusionOutput.branch_embeddings`), so no new
encoder is introduced.

Equations follow plan section 4.3 exactly:
``u_i = norm(P_R z_i^R)``, ``v_i = norm(P_A z_i^A)``,
``L_nce = 0.5 [CE(u V^T / tau, I) + CE(v U^T / tau, I)]`` with ``tau = 0.1``.

Precedent: Oord et al., 2018 (InfoNCE); the application to paired modalities is
an adapted combination, not claimed novel.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from p22.models.fusion import VIEW_A, VIEW_B

DEFAULT_TAU = 0.1
DEFAULT_CHUNK = 256


class PairingHead(nn.Module):
    """Project each modality's branch embedding to a shared normalised space.

    Args:
        dim: width of the branch embeddings ``z_R`` and ``z_A``.
        proj: width of the shared projection space.

    Raises:
        ValueError: if ``dim`` or ``proj`` is not a positive integer.
    """

    def __init__(self, dim: int, proj: int = 32) -> None:
        super().__init__()
        for name, value in (("dim", dim), ("proj", proj)):
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be an integer >= 1, got {value!r}")
        self.dim, self.proj = dim, proj
        self.proj_r = nn.Linear(dim, proj)
        self.proj_a = nn.Linear(dim, proj)

    def forward(self, z_r: torch.Tensor, z_a: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Return L2-normalised ``(u, v)`` for paired branch embeddings.

        Args:
            z_r: ``(n_cells, dim)`` RNA branch embeddings.
            z_a: ``(n_cells, dim)`` ATAC branch embeddings.

        Returns:
            ``(u, v)`` with shapes ``(n_cells, proj)``, each row unit-norm.

        Raises:
            ValueError: if inputs are not two-dimensional with ``dim`` columns
                or their row counts differ.
        """
        for name, z in (("z_r", z_r), ("z_a", z_a)):
            if z.ndim != 2 or z.shape[1] != self.dim:
                raise ValueError(f"{name} must be (n_cells, {self.dim}), got {tuple(z.shape)}")
        if z_r.shape[0] != z_a.shape[0]:
            raise ValueError("z_r and z_a must have the same number of rows")
        u = F.normalize(self.proj_r(z_r), dim=-1)
        v = F.normalize(self.proj_a(z_a), dim=-1)
        return u, v


def info_nce(u: torch.Tensor, v: torch.Tensor, tau: float = DEFAULT_TAU) -> torch.Tensor:
    """Symmetric InfoNCE over paired rows (plan section 4.3).

    Args:
        u: ``(n, proj)`` normalised embeddings for one modality.
        v: ``(n, proj)`` normalised embeddings for the other modality, row-aligned.
        tau: positive temperature.

    Returns:
        Scalar mean of the two cross-entropy directions.

    Raises:
        ValueError: if shapes disagree or ``tau`` is not positive and finite.
    """
    if u.ndim != 2 or v.ndim != 2 or u.shape != v.shape:
        raise ValueError(f"u and v must be equal-shape 2-D tensors, got {tuple(u.shape)} "
                         f"and {tuple(v.shape)}")
    tau = float(tau)
    if not math.isfinite(tau) or tau <= 0.0:
        raise ValueError(f"tau must be finite and > 0, got {tau!r}")
    logits = u @ v.transpose(0, 1) / tau
    labels = torch.arange(u.shape[0], device=u.device)
    return 0.5 * (
        F.cross_entropy(logits, labels) + F.cross_entropy(logits.transpose(0, 1), labels)
    )


def branch_embeddings(
    model: nn.Module, views: Mapping[str, torch.Tensor]
) -> dict[str, torch.Tensor]:
    """Extract ``z_R``/``z_A`` from a fusion model or a MIL-wrapped fusion model.

    Args:
        model: a fusion model (``has_gate`` and a ``FusionOutput`` forward) or a
            :class:`~p22.models.mil.MILWrapper` wrapping one.
        views: mapping with the two view matrices.

    Returns:
        The model's ``branch_embeddings`` dict.

    Raises:
        ValueError: if the model has no fusion encoder or a view is missing.
    """
    encoder = getattr(model, "encoder", model)
    if not hasattr(encoder, "has_gate"):
        raise ValueError("pairing requires a fusion encoder with two branches")
    missing = [name for name in (VIEW_A, VIEW_B) if name not in views]
    if missing:
        raise ValueError(f"pairing needs view(s) {missing}")
    output = encoder(views[VIEW_A], views[VIEW_B])
    return output.branch_embeddings


def pairing_aux_loss(
    head: PairingHead,
    lambda_nce: float = 1.0,
    view_a: str = VIEW_A,
    view_b: str = VIEW_B,
):
    """Build an InfoNCE auxiliary loss callable for :func:`~p22.training.mil_loop.train_mil`.

    ``head`` must be reachable from the optimiser. Attach it to the MIL model
    (``model.pairing_head = head``) or pass it as ``aux_losses=[...]``; the
    returned callable exposes the head as ``.head`` so :func:`train_mil` can add
    its parameters to the optimiser.

    Args:
        head: the :class:`PairingHead` projecting branch embeddings.
        lambda_nce: non-negative weight multiplying the InfoNCE term.
        view_a: view name for ``z_R`` (the query branch).
        view_b: view name for ``z_A`` (the key branch).

    Returns:
        A callable ``fn(batch_out, batch_meta) -> ("pairing", lambda_nce * loss)``
        reading ``batch_out["branch_embeddings"]``.

    Raises:
        ValueError: if ``lambda_nce`` is negative/non-finite or ``head`` is not a module.
    """
    if not isinstance(head, nn.Module):
        raise ValueError("head must be an nn.Module")
    lam = float(lambda_nce)
    if not math.isfinite(lam) or lam < 0.0:
        raise ValueError(f"lambda_nce must be finite and >= 0, got {lambda_nce!r}")

    def aux_loss(batch_out: dict, batch_meta: dict) -> tuple[str, torch.Tensor]:
        branches = batch_out.get("branch_embeddings")
        if not branches:
            raise ValueError("batch_out has no branch_embeddings for the pairing loss")
        u, v = head(branches[view_a], branches[view_b])
        return "pairing", lam * info_nce(u, v)

    aux_loss.head = head
    return aux_loss


def pairing_retrieval_top1(
    model: nn.Module,
    arrays: Mapping[str, np.ndarray],
    chunk_size: int = DEFAULT_CHUNK,
    device: str = "cpu",
    head: PairingHead | None = None,
) -> dict[str, object]:
    """Held-out top-1 pairing retrieval, computed within chunks of cells.

    Each cell's ``z_R`` is matched against the chunk's ``z_A`` rows; the metric is
    the fraction whose own row is the nearest. With random pairing this tends to
    ``1 / chunk_size`` (the chance level reported in the result).

    Args:
        model: fusion model or MIL-wrapped fusion model.
        arrays: held-out per-view matrices.
        chunk_size: number of cells per retrieval chunk (default 256).
        device: torch device string.
        head: optional trained :class:`PairingHead`; without it, raw branch
            embeddings are compared.

    Returns:
        A dict with ``top1``, ``chance``, ``n_cells`` and ``n_chunks``.

    Raises:
        ValueError: if ``chunk_size`` is not a positive integer or inputs are malformed.
    """
    if type(chunk_size) is not int or chunk_size < 1:
        raise ValueError(f"chunk_size must be a positive int, got {chunk_size!r}")
    if not arrays:
        raise ValueError("arrays must not be empty")
    lengths = {len(np.asarray(m)) for m in arrays.values()}
    if len(lengths) != 1:
        raise ValueError("all views must have the same number of cells")
    n_cells = lengths.pop()

    model = model.to(device)
    model.eval()
    correct = 0
    n_chunks = 0
    with torch.no_grad():
        for start in range(0, n_cells, chunk_size):
            stop = min(start + chunk_size, n_cells)
            chunk = {
                name: torch.as_tensor(np.asarray(m[start:stop]), dtype=torch.float32, device=device)
                for name, m in arrays.items()
            }
            z = branch_embeddings(model, chunk)
            if head is not None:
                u, v = head(z[VIEW_A], z[VIEW_B])
            else:
                u = F.normalize(z[VIEW_A], dim=-1)
                v = F.normalize(z[VIEW_B], dim=-1)
            predictions = (u @ v.transpose(0, 1)).argmax(dim=1)
            target = torch.arange(stop - start, device=device)
            correct += int((predictions == target).sum())
            n_chunks += 1
    return {
        "top1": correct / n_cells if n_cells else 0.0,
        "chance": 1.0 / chunk_size,
        "n_cells": n_cells,
        "n_chunks": n_chunks,
    }
