"""Two-view fusion: concatenation and gated routing.

Routing weights are signals, not explanations. A weight of 0.9 on one view says
that the gate scaled that branch by 0.9 for that cell. Whether the prediction
actually depends on that branch is a separate question, answered by the held-out
interventions in :mod:`p22.eval.faithfulness`.

Nothing in this module trains. Fitting happens in :mod:`p22.training`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import torch
from torch import nn

from p22.models.encoders import ViewEncoder

VIEW_A = "view_a"
VIEW_B = "view_b"
VIEW_NAMES: tuple[str, str] = (VIEW_A, VIEW_B)
ROUTE_TOLERANCE = 1e-5


@dataclass(frozen=True)
class FusionOutput:
    """One forward pass of a fusion model.

    Attributes:
        logits: ``(n_cells, n_classes)`` class scores.
        routing_weights: ``(n_cells, 2)`` non-negative weights summing to one per
            cell, ordered as ``(view_a, view_b)``. A model without a gate reports
            uniform weights.
        branch_embeddings: per-view embeddings entering fusion.
        fused_embedding: the embedding the classification head consumed.
    """

    logits: torch.Tensor
    routing_weights: torch.Tensor
    branch_embeddings: dict[str, torch.Tensor]
    fused_embedding: torch.Tensor

    def routing_frame_columns(self) -> tuple[str, str]:
        return VIEW_NAMES


def validate_route_override(
    override: Sequence[float] | torch.Tensor, n_views: int = 2
) -> torch.Tensor:
    """Validate a fixed routing vector.

    Args:
        override: weights per view, for example ``[1, 0]``, ``[0, 1]``, or
            ``[0.5, 0.5]``.
        n_views: expected number of views.

    Returns:
        A validated float tensor of shape ``(n_views,)``.

    Raises:
        ValueError: if the length is wrong, a weight is negative or not finite, or
            the weights do not sum to one.
    """
    tensor = torch.as_tensor(override, dtype=torch.float32).flatten()
    if tensor.numel() != n_views:
        raise ValueError(f"route override must have {n_views} weights, got {tensor.numel()}")
    if not torch.isfinite(tensor).all():
        raise ValueError("route override contains a non-finite weight")
    if bool((tensor < 0).any()):
        raise ValueError(f"route override weights must be non-negative, got {tensor.tolist()}")
    total = float(tensor.sum())
    if abs(total - 1.0) > ROUTE_TOLERANCE:
        raise ValueError(f"route override weights must sum to one, got {total}")
    return tensor


class RoutingGate(nn.Module):
    """Per-cell soft weights over view embeddings.

    Args:
        embed_dim: embedding size of each branch.
        n_views: number of branches.
        hidden_dim: hidden width of the gate.
    """

    def __init__(self, embed_dim: int, n_views: int = 2, hidden_dim: int = 32) -> None:
        super().__init__()
        if n_views < 2:
            raise ValueError(f"n_views must be >= 2, got {n_views}")
        self.n_views = int(n_views)
        self.net = nn.Sequential(
            nn.Linear(embed_dim * n_views, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, n_views),
        )

    def forward(
        self,
        embeddings: Sequence[torch.Tensor],
        override: Sequence[float] | torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Return ``(n_cells, n_views)`` weights that sum to one per cell.

        Args:
            embeddings: one embedding tensor per view.
            override: optional fixed routing vector applied to every cell.

        Raises:
            ValueError: if the number of embeddings is wrong or the override is invalid.
        """
        if len(embeddings) != self.n_views:
            raise ValueError(f"expected {self.n_views} embeddings, got {len(embeddings)}")
        n_cells = embeddings[0].shape[0]
        if override is not None:
            fixed = validate_route_override(override, self.n_views).to(embeddings[0].device)
            return fixed.unsqueeze(0).expand(n_cells, self.n_views)
        scores = self.net(torch.cat(list(embeddings), dim=1))
        return torch.softmax(scores, dim=1)


class ConcatFusionModel(nn.Module):
    """Concatenate two view embeddings, then classify.

    This model has no gate. It reports uniform routing weights so that reporting
    code can treat every model family the same way.
    """

    has_gate = False

    def __init__(
        self,
        n_features_a: int,
        n_features_b: int,
        n_classes: int,
        embed_dim: int = 32,
        hidden_dim: int = 64,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if n_classes < 2:
            raise ValueError(f"n_classes must be >= 2, got {n_classes}")
        self.encoder_a = ViewEncoder(n_features_a, embed_dim, hidden_dim, dropout)
        self.encoder_b = ViewEncoder(n_features_b, embed_dim, hidden_dim, dropout)
        self.head = nn.Linear(embed_dim * 2, n_classes)
        self.embed_dim = int(embed_dim)
        self.n_classes = int(n_classes)

    def forward(
        self,
        view_a: torch.Tensor,
        view_b: torch.Tensor,
        ablate_views: Sequence[str] = (),
    ) -> FusionOutput:
        """Run one forward pass.

        Args:
            view_a: ``(n_cells, n_features_a)`` tensor.
            view_b: ``(n_cells, n_features_b)`` tensor.
            ablate_views: view names whose embedding is replaced by zeros.

        Returns:
            A :class:`FusionOutput` whose routing weights are uniform.
        """
        branches = _encode_branches(self.encoder_a, self.encoder_b, view_a, view_b, ablate_views)
        fused = torch.cat([branches[VIEW_A], branches[VIEW_B]], dim=1)
        weights = torch.full(
            (view_a.shape[0], 2), 0.5, dtype=branches[VIEW_A].dtype, device=view_a.device
        )
        return FusionOutput(
            logits=self.head(fused),
            routing_weights=weights,
            branch_embeddings=branches,
            fused_embedding=fused,
        )


class GatedFusionModel(nn.Module):
    """Combine two view embeddings with per-cell routing weights, then classify.

    This is gated multimodal fusion (routing MLP + weighted branch sum), not
    query/key/value cross-attention.
    """

    has_gate = True

    def __init__(
        self,
        n_features_a: int,
        n_features_b: int,
        n_classes: int,
        embed_dim: int = 32,
        hidden_dim: int = 64,
        dropout: float = 0.1,
        gate_hidden_dim: int = 32,
    ) -> None:
        super().__init__()
        if n_classes < 2:
            raise ValueError(f"n_classes must be >= 2, got {n_classes}")
        self.encoder_a = ViewEncoder(n_features_a, embed_dim, hidden_dim, dropout)
        self.encoder_b = ViewEncoder(n_features_b, embed_dim, hidden_dim, dropout)
        self.gate = RoutingGate(embed_dim=embed_dim, n_views=2, hidden_dim=gate_hidden_dim)
        self.head = nn.Linear(embed_dim, n_classes)
        self.embed_dim = int(embed_dim)
        self.n_classes = int(n_classes)

    def forward(
        self,
        view_a: torch.Tensor,
        view_b: torch.Tensor,
        route_override: Sequence[float] | torch.Tensor | None = None,
        ablate_views: Sequence[str] = (),
    ) -> FusionOutput:
        """Run one forward pass.

        Args:
            view_a: ``(n_cells, n_features_a)`` tensor.
            view_b: ``(n_cells, n_features_b)`` tensor.
            route_override: optional fixed routing vector, for example ``[1, 0]``,
                ``[0, 1]``, or ``[0.5, 0.5]``.
            ablate_views: view names whose embedding is replaced by zeros before
                the gate runs, so both the weights and the fused embedding change.

        Returns:
            A :class:`FusionOutput` whose routing weights sum to one per cell.
        """
        branches = _encode_branches(self.encoder_a, self.encoder_b, view_a, view_b, ablate_views)
        ordered = [branches[VIEW_A], branches[VIEW_B]]
        weights = self.gate(ordered, override=route_override)
        fused = weights[:, 0:1] * ordered[0] + weights[:, 1:2] * ordered[1]
        return FusionOutput(
            logits=self.head(fused),
            routing_weights=weights,
            branch_embeddings=branches,
            fused_embedding=fused,
        )


def _encode_branches(
    encoder_a: ViewEncoder,
    encoder_b: ViewEncoder,
    view_a: torch.Tensor,
    view_b: torch.Tensor,
    ablate_views: Sequence[str],
) -> dict[str, torch.Tensor]:
    unknown = sorted(set(ablate_views) - set(VIEW_NAMES))
    if unknown:
        raise ValueError(f"unknown view name(s) to ablate: {unknown}; expected {VIEW_NAMES}")
    if view_a.shape[0] != view_b.shape[0]:
        raise ValueError(
            f"views must have the same number of cells, got {view_a.shape[0]} and {view_b.shape[0]}"
        )
    branches = {VIEW_A: encoder_a(view_a), VIEW_B: encoder_b(view_b)}
    for name in ablate_views:
        branches[name] = torch.zeros_like(branches[name])
    return branches
