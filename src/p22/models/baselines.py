"""Single-view baselines.

A fusion model that cannot beat one view is not evidence of anything. These
baselines exist so that comparison starts from the simplest thing that works.
"""

from __future__ import annotations

import torch
from torch import nn

from p22.models.encoders import ViewEncoder


class BaselineMLP(nn.Module):
    """Classifier over exactly one view.

    Args:
        n_features: input feature count.
        n_classes: number of label classes.
        embed_dim: embedding size, matched to the fusion models for fairness.
        hidden_dim: hidden width of the encoder.
        dropout: dropout probability inside the encoder.

    Raises:
        ValueError: if a size is out of range.
    """

    def __init__(
        self,
        n_features: int,
        n_classes: int,
        embed_dim: int = 32,
        hidden_dim: int = 64,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if n_classes < 2:
            raise ValueError(f"n_classes must be >= 2, got {n_classes}")
        self.encoder = ViewEncoder(
            n_features=n_features,
            embed_dim=embed_dim,
            hidden_dim=hidden_dim,
            dropout=dropout,
        )
        self.head = nn.Linear(embed_dim, n_classes)
        self.n_features = self.encoder.n_features
        self.n_classes = int(n_classes)

    def forward(self, view: torch.Tensor) -> torch.Tensor:
        """Return ``(n_cells, n_classes)`` logits for one view."""
        return self.head(self.encoder(view))

    def embed(self, view: torch.Tensor) -> torch.Tensor:
        """Return the view embedding without the classification head."""
        return self.encoder(view)
