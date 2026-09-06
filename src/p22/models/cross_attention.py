"""Small latent-token fusion models; attention is not a mechanism explanation.

Each existing ViewEncoder projects a feature vector to T * D values, reshaped
into T latent tokens. These are learned summaries, not named genes or peaks.
The matched control uses identical encoders and a classification head; only the
cross-attention model adds the attention parameters. No cell attends to another.
"""

from collections.abc import Sequence

import torch
from torch import nn

from p22.models.encoders import ViewEncoder
from p22.models.fusion import VIEW_A, VIEW_B, FusionOutput, _encode_branches


class TokenConcatFusionModel(nn.Module):
    """Mean-pool each modality's latent tokens and concatenate the two vectors."""

    has_gate = False

    def __init__(
        self,
        n_features_a: int,
        n_features_b: int,
        n_classes: int,
        n_tokens: int = 4,
        embed_dim: int = 16,
        hidden_dim: int = 32,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        for name, value, minimum in (
            ("n_features_a", n_features_a, 1),
            ("n_features_b", n_features_b, 1),
            ("n_classes", n_classes, 2),
            ("n_tokens", n_tokens, 2),
            ("embed_dim", embed_dim, 1),
            ("hidden_dim", hidden_dim, 1),
        ):
            if type(value) is not int or value < minimum:
                raise ValueError(f"{name} must be an integer >= {minimum}")
        self.n_tokens, self.embed_dim, self.n_classes = n_tokens, embed_dim, n_classes
        self.encoder_a = ViewEncoder(n_features_a, n_tokens * embed_dim, hidden_dim, dropout)
        self.encoder_b = ViewEncoder(n_features_b, n_tokens * embed_dim, hidden_dim, dropout)
        self.head = nn.Linear(2 * embed_dim, n_classes)

    def _fuse(self, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        return torch.cat((a.mean(dim=1), b.mean(dim=1)), dim=1)

    def forward(
        self,
        view_a: torch.Tensor,
        view_b: torch.Tensor,
        ablate_views: Sequence[str] = (),
    ) -> FusionOutput:
        branches = _encode_branches(self.encoder_a, self.encoder_b, view_a, view_b, ablate_views)
        tokens = {
            name: value.reshape(-1, self.n_tokens, self.embed_dim)
            for name, value in branches.items()
        }
        fused = self._fuse(tokens[VIEW_A], tokens[VIEW_B])
        return FusionOutput(
            logits=self.head(fused),
            routing_weights=fused.new_full((len(view_a), 2), 0.5),
            branch_embeddings={name: value.mean(dim=1) for name, value in tokens.items()},
            fused_embedding=fused,
        )


class CrossAttentionModel(TokenConcatFusionModel):
    """RNA (view A) queries ATAC (view B) keys/values, within each cell.

    Concatenate mean RNA with mean ATAC plus mean attention output. Uniform routing
    weights are a reporting placeholder inherited from the no-gate model contract,
    not attention weights. The matched control has the same pooling and head sizes.
    """

    def __init__(
        self,
        n_features_a: int,
        n_features_b: int,
        n_classes: int,
        n_tokens: int = 4,
        embed_dim: int = 16,
        hidden_dim: int = 32,
        dropout: float = 0.1,
        n_heads: int = 2,
    ) -> None:
        super().__init__(
            n_features_a, n_features_b, n_classes, n_tokens, embed_dim, hidden_dim, dropout
        )
        if type(n_heads) is not int or n_heads < 1 or embed_dim % n_heads:
            raise ValueError("n_heads must be positive and divide embed_dim")
        # PyTorch 2.8: batch_first keeps the cell axis separate from token axes.
        # https://docs.pytorch.org/docs/2.8/generated/torch.nn.MultiheadAttention.html
        self.attention = nn.MultiheadAttention(
            embed_dim, n_heads, dropout=dropout, batch_first=True
        )

    def _fuse(self, a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        context, _ = self.attention(a, b, b, need_weights=False)
        return torch.cat((a.mean(dim=1), b.mean(dim=1) + context.mean(dim=1)), dim=1)
