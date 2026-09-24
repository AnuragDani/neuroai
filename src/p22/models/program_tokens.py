"""Program/module-token fusion with named NMF identities (professor D3).

Unlike :mod:`p22.models.cross_attention`, whose tokens are anonymous latent
summaries, the tokens here are gene programs and ATAC modules recovered by
non-negative matrix factorisation. Each token has an identity that can be
annotated (top genes / top regions), so attention weights are interpretable as
program-to-module couplings rather than opaque latent interactions.

The NMF is fitted on **training cells only**; holdout cells are projected with
``transform``. ``fit_programs`` returns the fitted estimator and never sees the
holdout matrix. The token models consume the resulting activity matrices as
their two views.

Attention is a reporting signal, not a causal explanation: an attention weight
says a program leaned on a module, not that the module caused the label.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import torch
from sklearn.decomposition import NMF
from torch import nn

from p22.models.fusion import VIEW_A, VIEW_B, FusionOutput

DEFAULT_N_COMPONENTS_RNA = 16
DEFAULT_N_COMPONENTS_ATAC = 8

__all__ = [
    "ProgramTokenConcat",
    "ProgramTokenCrossAttention",
    "annotate_programs",
    "fit_programs",
    "parameter_count",
    "program_activities",
    "top_program_features",
]


def _validate_nonneg(matrix: Any, name: str) -> np.ndarray:
    array = np.asarray(matrix, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError(f"{name} must be two-dimensional, got shape {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains a non-finite value")
    if (array < 0).any():
        raise ValueError(f"{name} must be non-negative; NMF inputs are log-normalised/TF-IDF")
    return array


def fit_programs(train_matrix_nonneg: Any, k: int, seed: int) -> NMF:
    """Fit an NMF program/module dictionary on training cells only.

    Args:
        train_matrix_nonneg: ``(n_train_cells, n_features)`` non-negative matrix.
            For RNA this is the log-normalised HVG matrix *before* scaling; for
            ATAC it is the TF-IDF matrix *before* scaling.
        k: number of programs (RNA) or modules (ATAC).
        seed: random seed for reproducible initialisation.

    Returns:
        The fitted :class:`sklearn.decomposition.NMF`. Project holdout cells with
        ``estimator.transform(holdout_matrix_nonneg)``.

    Raises:
        ValueError: if ``k``/``seed`` are not integers, ``k`` is not positive, or
            the matrix is not a finite non-negative 2-D array.
    """
    if type(k) is not int or k < 1:
        raise ValueError(f"k must be an integer >= 1, got {k!r}")
    if type(seed) is not int:
        raise ValueError(f"seed must be an integer, got {seed!r}")
    array = _validate_nonneg(train_matrix_nonneg, "train_matrix_nonneg")
    if k > array.shape[1]:
        raise ValueError(f"k={k} exceeds n_features={array.shape[1]}")
    model = NMF(n_components=k, init="nndsvda", max_iter=400, random_state=seed)
    model.fit(array)
    return model


def program_activities(nmf: NMF, matrix_nonneg: Any) -> torch.Tensor:
    """Project cells onto a fitted program dictionary.

    Args:
        nmf: a fitted estimator from :func:`fit_programs`.
        matrix_nonneg: ``(n_cells, n_features)`` non-negative matrix.

    Returns:
        ``(n_cells, k)`` float32 activity tensor.

    Raises:
        ValueError: if the matrix is invalid or its feature count does not match
            the fitted dictionary.
    """
    array = _validate_nonneg(matrix_nonneg, "matrix_nonneg")
    expected = int(nmf.components_.shape[1])
    if array.shape[1] != expected:
        raise ValueError(
            f"matrix has {array.shape[1]} features but the fitted NMF expects {expected}"
        )
    activities = nmf.transform(array)
    return torch.as_tensor(activities, dtype=torch.float32)


def top_program_features(
    components: Any,
    feature_names: Sequence[str],
    top_n: int = 10,
) -> list[dict[str, Any]]:
    """Annotate each program with its highest-weight features.

    Args:
        components: ``(k, n_features)`` NMF component matrix.
        feature_names: length-``n_features`` feature names (genes or regions).
        top_n: how many features to keep per program.

    Returns:
        One dict per program: ``{"program": i, "features": [...], "weights": [...]}``
        sorted by descending weight, suitable for JSON.

    Raises:
        ValueError: if shapes disagree or ``top_n`` is not a positive integer.
    """
    matrix = np.asarray(components, dtype=np.float64)
    if matrix.ndim != 2:
        raise ValueError(f"components must be two-dimensional, got shape {matrix.shape}")
    if type(top_n) is not int or top_n < 1:
        raise ValueError(f"top_n must be an integer >= 1, got {top_n!r}")
    names = list(feature_names)
    if len(names) != matrix.shape[1]:
        raise ValueError(
            f"feature_names has {len(names)} entries but components has {matrix.shape[1]} columns"
        )
    annotations: list[dict[str, Any]] = []
    for index, row in enumerate(matrix):
        order = np.argsort(row)[::-1][:top_n]
        annotations.append(
            {
                "program": int(index),
                "features": [names[int(j)] for j in order],
                "weights": [float(row[int(j)]) for j in order],
            }
        )
    return annotations


def annotate_programs(
    rna_nmf: NMF,
    atac_nmf: NMF,
    rna_features: Sequence[str],
    atac_features: Sequence[str],
    top_n: int = 10,
) -> dict[str, list[dict[str, Any]]]:
    """Build the per-fold RNA-program and ATAC-module annotation payload for N17."""
    return {
        "rna": top_program_features(rna_nmf.components_, rna_features, top_n=top_n),
        "atac": top_program_features(atac_nmf.components_, atac_features, top_n=top_n),
    }


def parameter_count(model: nn.Module) -> int:
    """Return the number of trainable scalar parameters in ``model``."""
    return int(sum(p.numel() for p in model.parameters() if p.requires_grad))


def _validate_positive_int(value: Any, name: str, minimum: int = 1) -> None:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}, got {value!r}")


class ProgramTokenConcat(nn.Module):
    """Mean-pool RNA-program and ATAC-module tokens, then concatenate.

    Tokens are ``token_k = activity_k * E_k + b_k`` with learned ``E`` and ``b``.
    This is the matched control for :class:`ProgramTokenCrossAttention`: identical
    token construction, pooling and head, but no attention parameters.

    Args:
        k_rna: number of RNA programs (view A token count).
        k_atac: number of ATAC modules (view B token count).
        dim: token width.
        n_classes: number of output classes.
        dropout: dropout applied to the token tensors.
    """

    has_gate = False

    def __init__(
        self,
        k_rna: int,
        k_atac: int,
        dim: int = 32,
        n_classes: int = 2,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        _validate_positive_int(k_rna, "k_rna")
        _validate_positive_int(k_atac, "k_atac")
        _validate_positive_int(dim, "dim")
        _validate_positive_int(n_classes, "n_classes", minimum=2)
        if not 0.0 <= dropout < 1.0:
            raise ValueError(f"dropout must be in [0, 1), got {dropout!r}")
        self.k_rna, self.k_atac, self.dim, self.n_classes = k_rna, k_atac, dim, n_classes
        self.rna_embedding = nn.Parameter(torch.empty(k_rna, dim))
        self.rna_bias = nn.Parameter(torch.zeros(k_rna))
        self.atac_embedding = nn.Parameter(torch.empty(k_atac, dim))
        self.atac_bias = nn.Parameter(torch.zeros(k_atac))
        self.token_dropout = nn.Dropout(dropout)
        self.head = nn.Linear(2 * dim, n_classes)
        self._reset_parameters()
        # Populated by ProgramTokenCrossAttention when need_weights=True.
        self.attention_weights: torch.Tensor | None = None

    def _reset_parameters(self) -> None:
        nn.init.normal_(self.rna_embedding, std=0.02)
        nn.init.normal_(self.atac_embedding, std=0.02)

    def _tokens(
        self, activities: torch.Tensor, embedding: torch.Tensor, bias: torch.Tensor
    ) -> torch.Tensor:
        # (n, k, 1) * (1, k, dim) + (1, k, 1) -> (n, k, dim)
        return activities.unsqueeze(-1) * embedding.unsqueeze(0) + bias.view(1, -1, 1)

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
        """Run one forward pass over program/module activities.

        Args:
            view_a: ``(n_cells, k_rna)`` RNA program activities.
            view_b: ``(n_cells, k_atac)`` ATAC module activities.
            need_weights: for the attention model, also store attention weights.
            ablate_views: view names whose activities are replaced by zeros.

        Returns:
            A :class:`FusionOutput` with uniform routing weights (no gate).

        Raises:
            ValueError: on shape mismatch or an unknown view name.
        """
        unknown = sorted(set(ablate_views) - {VIEW_A, VIEW_B})
        if unknown:
            raise ValueError(
                f"unknown view name(s) to ablate: {unknown}; expected (view_a, view_b)"
            )
        if view_a.ndim != 2 or view_a.shape[1] != self.k_rna:
            raise ValueError(f"view_a must be (n_cells, {self.k_rna}), got {tuple(view_a.shape)}")
        if view_b.ndim != 2 or view_b.shape[1] != self.k_atac:
            raise ValueError(f"view_b must be (n_cells, {self.k_atac}), got {tuple(view_b.shape)}")
        if view_a.shape[0] != view_b.shape[0]:
            raise ValueError(
                "views must have the same number of cells, "
                f"got {view_a.shape[0]} and {view_b.shape[0]}"
            )
        if VIEW_A in ablate_views:
            view_a = torch.zeros_like(view_a)
        if VIEW_B in ablate_views:
            view_b = torch.zeros_like(view_b)
        dtype = self.rna_embedding.dtype
        rna_tokens = self._tokens(view_a.to(dtype), self.rna_embedding, self.rna_bias)
        atac_tokens = self._tokens(view_b.to(dtype), self.atac_embedding, self.atac_bias)
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


class ProgramTokenCrossAttention(ProgramTokenConcat):
    """RNA program tokens query ATAC module tokens, within each cell.

    ``fused = cat(mean RNA tokens, mean ATAC tokens + mean attention context)``,
    matching :class:`~p22.models.cross_attention.CrossAttentionModel` but with
    named program/module tokens instead of latent tokens. No cell attends to
    another cell.

    Args:
        k_rna: number of RNA programs.
        k_atac: number of ATAC modules.
        dim: token width; must be divisible by ``heads``.
        heads: number of attention heads.
        n_classes: number of output classes.
        dropout: dropout on tokens and attention.
    """

    def __init__(
        self,
        k_rna: int,
        k_atac: int,
        dim: int = 32,
        heads: int = 4,
        n_classes: int = 2,
        dropout: float = 0.1,
    ) -> None:
        super().__init__(k_rna, k_atac, dim=dim, n_classes=n_classes, dropout=dropout)
        if type(heads) is not int or heads < 1 or dim % heads:
            raise ValueError(f"heads must be a positive integer dividing dim={dim}, got {heads!r}")
        self.heads = heads
        # PyTorch 2.8: batch_first keeps the cell axis separate from token axes.
        self.attention = nn.MultiheadAttention(dim, heads, dropout=dropout, batch_first=True)

    def _fuse(
        self, rna_tokens: torch.Tensor, atac_tokens: torch.Tensor, need_weights: bool
    ) -> torch.Tensor:
        context, weights = self.attention(
            rna_tokens, atac_tokens, atac_tokens, need_weights=need_weights
        )
        if need_weights:
            # (n_cells, k_rna, k_atac), averaged over heads.
            self.attention_weights = weights
        return torch.cat(
            (rna_tokens.mean(dim=1), atac_tokens.mean(dim=1) + context.mean(dim=1)), dim=1
        )
