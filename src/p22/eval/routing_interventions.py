"""Professor-facing names for held-out routing interventions (G7).

Reuses ``p22.eval.faithfulness`` so gate values stay routing signals, not
explanations or cross-attention claims.
"""

from __future__ import annotations

from p22.eval.faithfulness import (
    ABLATE_VIEW_A,
    ABLATE_VIEW_B,
    CLAMP_VIEW_A,
    CLAMP_VIEW_B,
    INTERVENTIONS,
    PERMUTE_VIEW_A,
    PERMUTE_VIEW_B,
    UNIFORM_ROUTE,
    intervention_table,
    run_all_interventions,
    run_intervention,
)

# Human-readable aliases used in the notebook and handoff.
RNA_ABLATION = ABLATE_VIEW_A
ATAC_ABLATION = ABLATE_VIEW_B
RNA_ROUTE_CLAMP = CLAMP_VIEW_A
ATAC_ROUTE_CLAMP = CLAMP_VIEW_B
UNIFORM_ROUTE_CLAMP = UNIFORM_ROUTE
DONOR_PRESERVING_MODALITY_PERMUTATION = (PERMUTE_VIEW_A, PERMUTE_VIEW_B)

PROFESSOR_INTERVENTIONS = (
    "rna_ablation",
    "atac_ablation",
    "rna_only_route_clamp",
    "atac_only_route_clamp",
    "uniform_route_clamp",
    "donor_preserving_modality_permutation",
)

__all__ = [
    "ATAC_ABLATION",
    "ATAC_ROUTE_CLAMP",
    "DONOR_PRESERVING_MODALITY_PERMUTATION",
    "INTERVENTIONS",
    "PROFESSOR_INTERVENTIONS",
    "RNA_ABLATION",
    "RNA_ROUTE_CLAMP",
    "UNIFORM_ROUTE_CLAMP",
    "intervention_table",
    "run_all_interventions",
    "run_intervention",
]
