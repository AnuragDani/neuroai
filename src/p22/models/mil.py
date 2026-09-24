"""Gated-attention multiple-instance head over cell embeddings.

A bag is a set of cells from one donor. The head pools cell embeddings with a
gated-attention score (Ilse et al., 2018) and classifies the pooled vector. The
attention weights are reporting signals, not explanations: they say which cells
the head leaned on, not which genes or peaks caused the label.
"""

from __future__ import annotations

from collections.abc import Mapping

import torch
from torch import nn

from p22.models.fusion import VIEW_A, VIEW_B


class GatedAttentionPool(nn.Module):
    """Pool ``(n_cells, dim)`` embeddings into one vector with gated attention.

    Args:
        dim: embedding width.
        attn_dim: width of the gating bottleneck.

    Raises:
        ValueError: if ``dim`` or ``attn_dim`` is not a positive integer.
    """

    def __init__(self, dim: int, attn_dim: int = 64) -> None:
        super().__init__()
        for name, value in (("dim", dim), ("attn_dim", attn_dim)):
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be an integer >= 1, got {value!r}")
        self.dim, self.attn_dim = dim, attn_dim
        self.V = nn.Linear(dim, attn_dim)
        self.U = nn.Linear(dim, attn_dim)
        self.w = nn.Linear(attn_dim, 1)

    def forward(self, h: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Pool one bag.

        Args:
            h: ``(n_cells, dim)`` cell embeddings for a single bag.

        Returns:
            ``(pooled, attention)`` where ``pooled`` is ``(dim,)`` and
            ``attention`` is ``(n_cells,)`` summing to one.

        Raises:
            ValueError: if ``h`` is not two-dimensional with ``dim`` columns.
        """
        if h.ndim != 2 or h.shape[1] != self.dim:
            raise ValueError(f"h must be (n_cells, {self.dim}), got {tuple(h.shape)}")
        if h.shape[0] == 0:
            raise ValueError("cannot pool an empty bag")
        gates = self.w(torch.tanh(self.V(h)) * torch.sigmoid(self.U(h))).squeeze(-1)
        attention = torch.softmax(gates, dim=0)
        pooled = (attention.unsqueeze(-1) * h).sum(dim=0)
        return pooled, attention


class MILWrapper(nn.Module):
    """Attach a gated-attention bag head to a frozen-interface cell encoder.

    Args:
        encoder_model: a fusion model (exposing ``has_gate`` and returning
            :class:`~p22.models.fusion.FusionOutput`) or a single-view model
            exposing ``embed`` (e.g. :class:`~p22.models.baselines.BaselineMLP`).
        dim: embedding width produced by ``encoder_model``.
        attn_dim: width of the attention gating bottleneck.
    """

    def __init__(self, encoder_model: nn.Module, dim: int, attn_dim: int = 64) -> None:
        super().__init__()
        self.encoder = encoder_model
        self.dim = dim
        self.pool = GatedAttentionPool(dim, attn_dim)
        self.head = nn.Linear(dim, 1)

    def embed(self, views: Mapping[str, torch.Tensor]) -> torch.Tensor:
        """Return ``(n_cells, dim)`` embeddings for one bag's views."""
        if hasattr(self.encoder, "has_gate"):
            missing = [name for name in (VIEW_A, VIEW_B) if name not in views]
            if missing:
                raise ValueError(f"fusion encoder needs view(s) {missing}")
            output = self.encoder(views[VIEW_A], views[VIEW_B])
            return output.fused_embedding
        if len(views) != 1:
            raise ValueError(f"single-view encoder reads exactly one view, got {sorted(views)}")
        return self.encoder.embed(next(iter(views.values())))

    def forward_bag(
        self, views: Mapping[str, torch.Tensor]
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Classify one bag.

        Args:
            views: this bag's per-view ``(n_cells, n_features)`` tensors.

        Returns:
            ``(logit_bag, attention, cell_logits)`` with shapes ``(1,)``,
            ``(n_cells,)`` (summing to one), and ``(n_cells,)``.
        """
        embeddings = self.embed(views)
        pooled, attention = self.pool(embeddings)
        logit_bag = self.head(pooled)
        cell_logits = self.head(embeddings).squeeze(-1)
        return logit_bag, attention, cell_logits
