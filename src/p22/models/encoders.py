"""View encoders.

A view is any feature block. Nothing here names a measurement technology: the
encoder is the same code whether the block holds one modality or another.
"""

from __future__ import annotations

import torch
from torch import nn


class ViewEncoder(nn.Module):
    """Map one view's features to a shared embedding space.

    Args:
        n_features: input feature count for this view.
        embed_dim: output embedding size, shared across views so branches are comparable.
        hidden_dim: width of the single hidden layer.
        dropout: dropout probability applied after the hidden layer.

    Raises:
        ValueError: if any size is not positive or dropout is outside [0, 1).
    """

    def __init__(
        self,
        n_features: int,
        embed_dim: int = 32,
        hidden_dim: int = 64,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        for name, value in (
            ("n_features", n_features),
            ("embed_dim", embed_dim),
            ("hidden_dim", hidden_dim),
        ):
            if value < 1:
                raise ValueError(f"{name} must be >= 1, got {value}")
        if not 0.0 <= dropout < 1.0:
            raise ValueError(f"dropout must be in [0, 1), got {dropout}")

        self.n_features = int(n_features)
        self.embed_dim = int(embed_dim)
        self.net = nn.Sequential(
            nn.Linear(n_features, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, embed_dim),
        )

    def forward(self, view: torch.Tensor) -> torch.Tensor:
        """Encode one view.

        Args:
            view: ``(n_cells, n_features)`` tensor.

        Returns:
            ``(n_cells, embed_dim)`` embedding.

        Raises:
            ValueError: if the feature count does not match the encoder.
        """
        if view.ndim != 2:
            raise ValueError(f"view must be two-dimensional, got shape {tuple(view.shape)}")
        if view.shape[1] != self.n_features:
            raise ValueError(
                f"view has {view.shape[1]} features, encoder expects {self.n_features}"
            )
        return self.net(view)
