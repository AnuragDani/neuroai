from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import torch
from torch import nn

from p22.models.fusion import VIEW_A, VIEW_B, FusionOutput

__all__ = ["GeneAlignedTokenConcat", "GeneAlignedCrossAttention"]

def _create_band_mask(num_genes: int, k: int, device: torch.device) -> torch.Tensor:
    """Create a boolean attention mask for a band of width 2k+1 around the diagonal."""
    row_idx = torch.arange(num_genes, device=device).unsqueeze(1)
    col_idx = torch.arange(num_genes, device=device).unsqueeze(0)
    dist = torch.abs(row_idx - col_idx)
    return dist > k  # True where distance > k (not allowed)

class GeneAlignedTokenConcat(nn.Module):
    has_gate = False

    def __init__(
        self,
        num_genes: int,
        dim: int = 32,
        n_classes: int = 2,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.num_genes = num_genes
        self.dim = dim
        self.n_classes = n_classes
        
        # Identity embedding shared across modalities
        self.gene_embedding = nn.Embedding(num_genes, dim)
        
        # Modality specific value multipliers
        self.rna_e_mod = nn.Parameter(torch.empty(dim))
        self.atac_e_mod = nn.Parameter(torch.empty(dim))
        
        self.token_dropout = nn.Dropout(dropout)
        self.head = nn.Linear(2 * dim, n_classes)
        self._reset_parameters()

    def _reset_parameters(self) -> None:
        nn.init.normal_(self.gene_embedding.weight, std=0.02)
        nn.init.normal_(self.rna_e_mod, std=0.02)
        nn.init.normal_(self.atac_e_mod, std=0.02)

    def _tokens(
        self, values: torch.Tensor, e_mod: torch.Tensor
    ) -> torch.Tensor:
        # values: (n_cells, num_genes)
        # return: (n_cells, num_genes, dim)
        # value * E_mod + gene_identity_embedding
        
        # gene_identity: (num_genes, dim)
        gene_id = self.gene_embedding.weight.unsqueeze(0) # (1, num_genes, dim)
        
        # values.unsqueeze(-1) * e_mod.view(1, 1, dim) -> (n_cells, num_genes, dim)
        return values.unsqueeze(-1) * e_mod.view(1, 1, -1) + gene_id

    def _fuse(
        self, rna_tokens: torch.Tensor, atac_tokens: torch.Tensor, need_weights: bool
    ) -> torch.Tensor:
        return torch.cat((rna_tokens.mean(dim=1), atac_tokens.mean(dim=1)), dim=1)

    def forward(
        self,
        view_a: torch.Tensor,
        view_b: torch.Tensor,
        need_weights: bool = False,
        ablate_views: Sequence[str] = (),
    ) -> FusionOutput:
        if VIEW_A in ablate_views:
            view_a = torch.zeros_like(view_a)
        if VIEW_B in ablate_views:
            view_b = torch.zeros_like(view_b)
            
        dtype = self.gene_embedding.weight.dtype
        rna_tokens = self._tokens(view_a.to(dtype), self.rna_e_mod)
        atac_tokens = self._tokens(view_b.to(dtype), self.atac_e_mod)
        
        rna_tokens = self.token_dropout(rna_tokens)
        atac_tokens = self.token_dropout(atac_tokens)
        
        self.attention_weights = None
        fused = self._fuse(rna_tokens, atac_tokens, need_weights)
        weights = torch.full((view_a.shape[0], 2), 0.5, dtype=fused.dtype, device=fused.device)
        
        return FusionOutput(
            logits=self.head(fused),
            routing_weights=weights,
            branch_embeddings={
                VIEW_A: rna_tokens.mean(dim=1),
                VIEW_B: atac_tokens.mean(dim=1),
            },
            fused_embedding=fused,
        )

class GeneAlignedCrossAttention(GeneAlignedTokenConcat):
    def __init__(
        self,
        num_genes: int,
        dim: int = 32,
        heads: int = 4,
        n_classes: int = 2,
        dropout: float = 0.1,
        k_nearest: int = 5,
    ) -> None:
        super().__init__(num_genes=num_genes, dim=dim, n_classes=n_classes, dropout=dropout)
        self.heads = heads
        self.k_nearest = k_nearest
        self.attention = nn.MultiheadAttention(dim, heads, dropout=dropout, batch_first=True)

    def _fuse(
        self, rna_tokens: torch.Tensor, atac_tokens: torch.Tensor, need_weights: bool
    ) -> torch.Tensor:
        mask = _create_band_mask(self.num_genes, self.k_nearest, device=rna_tokens.device)
        
        context, weights = self.attention(
            rna_tokens, atac_tokens, atac_tokens, 
            need_weights=need_weights,
            attn_mask=mask
        )
        if need_weights:
            self.attention_weights = weights
        return torch.cat(
            (rna_tokens.mean(dim=1), atac_tokens.mean(dim=1) + context.mean(dim=1)), dim=1
        )
