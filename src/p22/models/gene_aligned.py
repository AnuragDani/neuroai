import torch
from torch import nn
from p22.models.fusion import VIEW_A, VIEW_B, FusionOutput
import numpy as np
from typing import Sequence

__all__ = [
    "GeneAlignedTokenConcat",
    "GeneAlignedCrossAttention",
    "build_genomic_attention_mask"
]

def build_genomic_attention_mask(chromosomes: Sequence[str], starts: Sequence[int], k: int = 5) -> torch.Tensor:
    """Build attention mask restricting attention to same gene +- k nearest on same chromosome.
    
    Returns a boolean mask of shape (num_genes, num_genes) where True means attention is BLOCKED,
    for use with PyTorch MultiheadAttention.
    """
    n = len(chromosomes)
    mask = torch.ones(n, n, dtype=torch.bool)
    
    # Group by chromosome
    for chrom in set(chromosomes):
        indices = [i for i, c in enumerate(chromosomes) if c == chrom]
        if not indices:
            continue
        
        # Sort indices by start position
        sorted_indices = sorted(indices, key=lambda i: starts[i])
        
        for i, idx1 in enumerate(sorted_indices):
            # Allow +- k nearest on the SAME chromosome
            start_i = max(0, i - k)
            end_i = min(len(sorted_indices), i + k + 1)
            for j in range(start_i, end_i):
                idx2 = sorted_indices[j]
                mask[idx1, idx2] = False
                
    return mask

class GeneAlignedTokenConcat(nn.Module):
    """Mean-pool RNA and ATAC gene-aligned tokens, then concatenate."""
    has_gate = False
    
    def __init__(
        self, 
        num_genes: int, 
        dim: int = 32, 
        n_classes: int = 2, 
        dropout: float = 0.1
    ) -> None:
        super().__init__()
        if type(num_genes) is not int or num_genes < 1:
            raise ValueError(f"num_genes must be a positive integer, got {num_genes!r}")
        self.num_genes = num_genes
        self.dim = dim
        self.n_classes = n_classes
        
        self.gene_embeddings = nn.Parameter(torch.empty(num_genes, dim))
        self.rna_modality = nn.Parameter(torch.empty(dim))
        self.atac_modality = nn.Parameter(torch.empty(dim))
        self.token_dropout = nn.Dropout(dropout)
        
        self.head = nn.Linear(2 * dim, n_classes)
        
        self.attention_weights: torch.Tensor | None = None
        self._reset_parameters()
        
    def _reset_parameters(self) -> None:
        nn.init.normal_(self.gene_embeddings, std=0.02)
        nn.init.normal_(self.rna_modality, std=0.02)
        nn.init.normal_(self.atac_modality, std=0.02)
        
    def _tokens(self, view: torch.Tensor, modality_emb: torch.Tensor) -> torch.Tensor:
        value = view.unsqueeze(-1)
        return value * modality_emb.unsqueeze(0).unsqueeze(0) + self.gene_embeddings.unsqueeze(0)
        
    def _fuse(self, rna_tokens: torch.Tensor, atac_tokens: torch.Tensor, need_weights: bool) -> torch.Tensor:
        return torch.cat((rna_tokens.mean(dim=1), atac_tokens.mean(dim=1)), dim=1)
        
    def forward(
        self,
        view_a: torch.Tensor,
        view_b: torch.Tensor,
        need_weights: bool = False,
        ablate_views: Sequence[str] = (),
    ) -> FusionOutput:
        unknown = sorted(set(ablate_views) - {VIEW_A, VIEW_B})
        if unknown:
            raise ValueError(f"unknown view name(s) to ablate: {unknown}")
            
        if view_a.shape[1] != self.num_genes or view_b.shape[1] != self.num_genes:
            raise ValueError("View feature count must match num_genes")
            
        if VIEW_A in ablate_views:
            view_a = torch.zeros_like(view_a)
        if VIEW_B in ablate_views:
            view_b = torch.zeros_like(view_b)
            
        rna_tokens = self._tokens(view_a, self.rna_modality)
        atac_tokens = self._tokens(view_b, self.atac_modality)
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
    """RNA gene tokens attend to ATAC gene tokens."""
    
    def __init__(
        self, 
        num_genes: int, 
        dim: int = 32, 
        heads: int = 4, 
        n_classes: int = 2, 
        dropout: float = 0.1, 
        attn_mask: torch.Tensor | None = None
    ) -> None:
        super().__init__(num_genes, dim, n_classes, dropout)
        self.heads = heads
        self.attention = nn.MultiheadAttention(dim, heads, dropout=dropout, batch_first=True)
        if attn_mask is not None:
            self.register_buffer("attn_mask", attn_mask)
        else:
            self.attn_mask = None
        
    def _fuse(self, rna_tokens: torch.Tensor, atac_tokens: torch.Tensor, need_weights: bool) -> torch.Tensor:
        context, weights = self.attention(
            rna_tokens, atac_tokens, atac_tokens, 
            need_weights=need_weights,
            attn_mask=self.attn_mask
        )
        if need_weights:
            self.attention_weights = weights
        return torch.cat(
            (rna_tokens.mean(dim=1), atac_tokens.mean(dim=1) + context.mean(dim=1)), dim=1
        )
