"""Conditional gradient-reversal nuisance adversary.

Technical factors (library, sequencing batch, QC depth) are removed from the cell
embedding while the disease label is protected: the adversary input is
``cat(grl(h), onehot(y))``, so only ``h`` is reversed and the label onehot reaches
the heads unchanged. Batches E23/E27 contain DS donors only, so an unconditional
adversary would erase disease signal; the onehot is what makes the adversary
conditional (plan A10).

Precedent: Ganin & Lempitsky, ICML 2015; Ganin et al., JMLR 2016 [B2]. The
schedules and heads here are an adapted combination, not claimed novel.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


class _GradReverse(torch.autograd.Function):
    """Identity forward; backward multiplies the gradient by ``-gamma``."""

    @staticmethod
    def forward(ctx, x: torch.Tensor, gamma: torch.Tensor) -> torch.Tensor:
        ctx.gamma = float(gamma)
        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output: torch.Tensor):
        return -ctx.gamma * grad_output, None


def grl(x: torch.Tensor, gamma: float) -> torch.Tensor:
    """Gradient-reversal layer: forward identity, backward ``-gamma`` scaling.

    Args:
        x: any float tensor.
        gamma: non-negative reversal strength.

    Returns:
        ``x`` unchanged in the forward pass.

    Raises:
        ValueError: if ``x`` is not a float tensor or ``gamma`` is negative/non-finite.
    """
    if not torch.is_tensor(x):
        raise ValueError("x must be a torch.Tensor")
    if not torch.is_floating_point(x):
        raise ValueError("x must be a floating-point tensor")
    gamma = float(gamma)
    if not math.isfinite(gamma) or gamma < 0.0:
        raise ValueError(f"gamma must be finite and >= 0, got {gamma!r}")
    return _GradReverse.apply(x, gamma)


def gamma_schedule(progress: float) -> float:
    """Map training progress in ``[0, 1]`` to a reversal strength in ``[0, 1)``.

    ``gamma(p) = 2 / (1 + exp(-10 p)) - 1`` follows plan section 4.3: 0 at the
    start of training, approaching 1 as training finishes.

    Raises:
        ValueError: if ``progress`` is outside ``[0, 1]`` or non-finite.
    """
    p = float(progress)
    if not math.isfinite(p) or not 0.0 <= p <= 1.0:
        raise ValueError(f"progress must lie in [0, 1], got {progress!r}")
    return 2.0 / (1.0 + math.exp(-10.0 * p)) - 1.0


def _head(in_dim: int, out_dim: int, hidden: int) -> nn.Sequential:
    return nn.Sequential(nn.Linear(in_dim, hidden), nn.ReLU(), nn.Linear(hidden, out_dim))


class ConditionalNuisanceAdversary(nn.Module):
    """Three nuisance heads reading ``cat(grl(h), onehot(y))``.

    Args:
        dim: embedding width ``h`` produced by the encoder.
        n_library: number of library codes.
        n_batch: number of batch codes.
        n_qc: number of standardized QC columns predicted by the MSE head.
        hidden: width of each head's single hidden layer.

    Raises:
        ValueError: if any count or width is not a positive integer.
    """

    def __init__(
        self, dim: int, n_library: int, n_batch: int, n_qc: int = 5, hidden: int = 64
    ) -> None:
        super().__init__()
        for name, value in (
            ("dim", dim),
            ("n_library", n_library),
            ("n_batch", n_batch),
            ("n_qc", n_qc),
            ("hidden", hidden),
        ):
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be an integer >= 1, got {value!r}")
        self.dim = dim
        self.n_library = n_library
        self.n_batch = n_batch
        self.n_qc = n_qc
        self.hidden = hidden
        in_dim = dim + 2  # reversed embedding plus the binary-label onehot
        self.library_head = _head(in_dim, n_library, hidden)
        self.batch_head = _head(in_dim, n_batch, hidden)
        self.qc_head = _head(in_dim, n_qc, hidden)

    def forward(
        self, h: torch.Tensor, labels: torch.Tensor, gamma: float
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Score nuisance factors from reversed embeddings and an intact label.

        Args:
            h: ``(n_cells, dim)`` cell embeddings from the encoder.
            labels: ``(n_cells,)`` binary disease labels (0/1).
            gamma: reversal strength for :func:`grl`.

        Returns:
            ``(library_logits, batch_logits, qc_pred)`` with shapes
            ``(n_cells, n_library)``, ``(n_cells, n_batch)``, ``(n_cells, n_qc)``.

        Raises:
            ValueError: on malformed shapes.
        """
        if h.ndim != 2 or h.shape[1] != self.dim:
            raise ValueError(f"h must be (n_cells, {self.dim}), got {tuple(h.shape)}")
        if labels.ndim != 1 or labels.shape[0] != h.shape[0]:
            raise ValueError("labels must be (n_cells,) matching h")
        reversed_h = grl(h, gamma)
        onehot = F.one_hot(labels.long(), num_classes=2).to(reversed_h.dtype)
        x = torch.cat([reversed_h, onehot], dim=-1)
        return self.library_head(x), self.batch_head(x), self.qc_head(x)


def adversary_losses(
    adversary: ConditionalNuisanceAdversary,
    h: torch.Tensor,
    labels: torch.Tensor,
    library: torch.Tensor,
    batch: torch.Tensor,
    qc: torch.Tensor,
    gamma: float,
) -> dict[str, torch.Tensor]:
    """Per-factor adversary losses plus their sum (plan section 4.3).

    Args:
        adversary: the conditional adversary.
        h: ``(n_cells, dim)`` embeddings (gradients flow back through ``grl``).
        labels: ``(n_cells,)`` binary disease labels.
        library: ``(n_cells,)`` integer library codes.
        batch: ``(n_cells,)`` integer batch codes.
        qc: ``(n_cells, n_qc)`` standardized QC targets.
        gamma: reversal strength.

    Returns:
        A dict with ``library`` (CE), ``batch`` (CE), ``qc`` (MSE) and ``total``.
    """
    library_logits, batch_logits, qc_pred = adversary(h, labels, gamma)
    library_loss = F.cross_entropy(library_logits, library.long())
    batch_loss = F.cross_entropy(batch_logits, batch.long())
    qc_loss = F.mse_loss(qc_pred, qc.to(qc_pred.dtype))
    return {
        "library": library_loss,
        "batch": batch_loss,
        "qc": qc_loss,
        "total": library_loss + batch_loss + qc_loss,
    }


def adversary_aux_loss(
    adversary: ConditionalNuisanceAdversary,
    cell_meta: Mapping[str, object],
    lambda_adv: float = 1.0,
) -> Callable[[dict, dict], tuple[str, torch.Tensor]]:
    """Build an auxiliary loss callable for :func:`~p22.training.mil_loop.train_mil`.

    ``cell_meta`` holds full per-cell training arrays under the keys ``labels``,
    ``library``, ``batch`` and ``qc``. The returned callable reads a bag's row
    positions from ``batch_meta["index"]`` (set by the MIL loop), selects those
    cells, and returns ``("adversary", lambda_adv * total)``.

    Args:
        adversary: the conditional adversary.
        cell_meta: per-cell arrays for the training cells.
        lambda_adv: non-negative weight multiplying the summed adversary loss.

    Raises:
        ValueError: if a required array is missing or ``lambda_adv`` is negative.
    """
    lam = float(lambda_adv)
    if not math.isfinite(lam) or lam < 0.0:
        raise ValueError(f"lambda_adv must be finite and >= 0, got {lambda_adv!r}")
    required = ("labels", "library", "batch", "qc")
    missing = [key for key in required if key not in cell_meta]
    if missing:
        raise ValueError(f"cell_meta is missing {missing}")
    arrays = {key: np.asarray(cell_meta[key]) for key in required}
    n_cells = len(arrays["labels"])
    for key, array in arrays.items():
        if array.shape[0] != n_cells:
            raise ValueError(f"cell_meta[{key!r}] has {array.shape[0]} rows, expected {n_cells}")

    def aux_loss(batch_out: dict, batch_meta: dict) -> tuple[str, torch.Tensor]:
        index = np.asarray(batch_meta["index"])
        h = batch_out["embeddings"]
        gamma = gamma_schedule(float(batch_meta.get("progress", 0.0)))
        losses = adversary_losses(
            adversary,
            h,
            torch.as_tensor(arrays["labels"][index], dtype=torch.long),
            torch.as_tensor(arrays["library"][index], dtype=torch.long),
            torch.as_tensor(arrays["batch"][index], dtype=torch.long),
            torch.as_tensor(arrays["qc"][index], dtype=torch.float32),
            gamma,
        )
        return "adversary", lam * losses["total"]

    return aux_loss