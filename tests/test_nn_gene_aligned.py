import importlib.util
import sys
from pathlib import Path

import pytest
import torch

from p22.models.fusion import VIEW_A
from p22.models.gene_aligned import (
    GeneAlignedCrossAttention,
    GeneAlignedTokenConcat,
    build_genomic_attention_mask,
)


def _load_gene_activity_runner():
    path = Path(__file__).resolve().parents[1] / "scripts" / "run_nn_v2_gene_activity.py"
    spec = importlib.util.spec_from_file_location("run_nn_v2_gene_activity", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_build_genomic_attention_mask():
    chromosomes = ["chr1", "chr1", "chr1", "chr2", "chr2"]
    starts = [100, 300, 200, 50, 10]
    
    mask = build_genomic_attention_mask(chromosomes, starts, k=1)
    
    # expected sort order for chr1: 0 (100), 2 (200), 1 (300)
    # indices:
    # chr1: 0, 2, 1
    # chr2: 4 (10), 3 (50)
    
    # Within chr1, sorted are [0, 2, 1]
    # For 0: nearest k=1 means index 0 and 2. So mask[0, 0]=F, mask[0, 2]=F
    # For 2: nearest k=1 means 0, 2, 1. mask[2, 0]=F, mask[2, 2]=F, mask[2, 1]=F
    # For 1: nearest k=1 means 2, 1. mask[1, 2]=F, mask[1, 1]=F
    
    # Within chr2, sorted are [4, 3]
    # For 4: nearest k=1 means 4, 3. mask[4, 4]=F, mask[4, 3]=F
    # For 3: nearest k=1 means 4, 3. mask[3, 4]=F, mask[3, 3]=F
    
    expected_false = [
        (0, 0), (0, 2),
        (2, 0), (2, 2), (2, 1),
        (1, 2), (1, 1),
        (4, 4), (4, 3),
        (3, 4), (3, 3)
    ]
    
    assert mask.shape == (5, 5)
    assert mask.dtype == torch.bool
    
    # Verify all expected Falses
    for i, j in expected_false:
        assert not mask[i, j], f"Expected False at ({i}, {j})"
        
    # Verify a few expected Trues
    assert mask[0, 1] # Too far on chr1
    assert mask[0, 3] # Different chromosome
    assert mask[3, 2]

def test_gene_aligned_token_concat():
    model = GeneAlignedTokenConcat(num_genes=10, dim=16, n_classes=2)
    view_a = torch.randn(4, 10)
    view_b = torch.randn(4, 10)
    
    out = model(view_a, view_b)
    assert out.logits.shape == (4, 2)
    assert out.fused_embedding.shape == (4, 32)
    
    # Ablation
    out_ablate = model(view_a, view_b, ablate_views=[VIEW_A])
    assert out_ablate.logits.shape == (4, 2)

def test_gene_aligned_cross_attention():
    mask = torch.ones(10, 10, dtype=torch.bool)
    # allow diagonal
    for i in range(10):
        mask[i, i] = False
        
    model = GeneAlignedCrossAttention(num_genes=10, dim=16, heads=4, n_classes=2, attn_mask=mask)
    view_a = torch.randn(4, 10)
    view_b = torch.randn(4, 10)
    
    out = model(view_a, view_b, need_weights=True)
    assert out.logits.shape == (4, 2)
    assert out.fused_embedding.shape == (4, 32)
    assert model.attention_weights is not None
    assert model.attention_weights.shape == (4, 10, 10)
    
    # Check mask was applied (weights should be exactly 0 where mask is True, 
    # except softmax may make it small; True mask -> -inf so weights should be 0)
    # Check off-diagonal
    assert torch.allclose(model.attention_weights[:, 0, 1], torch.tensor(0.0))


def test_select_ga_genes_matches_amendment_extremes():
    mod = _load_gene_activity_runner()
    cfg = Path(__file__).resolve().parents[1] / "configs" / "nn_gene_activity_2026-09-23.json"
    selection = mod.select_ga_genes(cfg, cap=500)
    assert selection["ga_n_genes"] == 500
    assert selection["panel_n_genes"] == 548
    assert selection["selection"] == "highest_label_free_dispersion_z"
    assert selection["dispersion_z_min"] == pytest.approx(-0.41207420616229146)
    assert selection["dispersion_z_max"] == pytest.approx(14.044904881960885)
    assert len(selection["names"]) == 500
    assert len(selection["chromosomes"]) == 500
    assert len(selection["starts"]) == 500
