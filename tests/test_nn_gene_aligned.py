import pytest
import torch

from p22.models.gene_aligned import GeneAlignedTokenConcat, GeneAlignedCrossAttention

def test_band_mask():
    from p22.models.gene_aligned import _create_band_mask
    mask = _create_band_mask(6, k=1, device=torch.device("cpu"))
    # Expected: diagonal + 1 off-diagonal are False, rest True
    assert mask.shape == (6, 6)
    assert mask[0, 0] == False
    assert mask[0, 1] == False
    assert mask[0, 2] == True
    assert mask[5, 5] == False
    assert mask[5, 4] == False
    assert mask[5, 3] == True

def test_gene_aligned_token_concat():
    model = GeneAlignedTokenConcat(num_genes=100, dim=16, n_classes=2)
    view_a = torch.randn(16, 100)
    view_b = torch.randn(16, 100)
    
    out = model(view_a, view_b)
    assert out.logits.shape == (16, 2)
    assert out.fused_embedding.shape == (16, 32)
    assert out.branch_embeddings["view_a"].shape == (16, 16)
    assert out.branch_embeddings["view_b"].shape == (16, 16)

def test_gene_aligned_cross_attention():
    model = GeneAlignedCrossAttention(num_genes=100, dim=16, heads=4, n_classes=2, k_nearest=5)
    view_a = torch.randn(16, 100)
    view_b = torch.randn(16, 100)
    
    out = model(view_a, view_b, need_weights=True)
    assert out.logits.shape == (16, 2)
    assert out.fused_embedding.shape == (16, 32)
    assert out.branch_embeddings["view_a"].shape == (16, 16)
    assert out.branch_embeddings["view_b"].shape == (16, 16)
    assert model.attention_weights.shape == (16, 100, 100)
    
    # Check that attention mask is respected (attention weights should be 0 where mask is True)
    # The mask prevents attention outside the band.
    # We can check that weights are ~0 for distance > 5
    weights = model.attention_weights[0].detach() # (100, 100)
    
    # Due to softmax, masked positions might be exactly 0 (or very close)
    assert torch.allclose(weights[0, 10], torch.tensor(0.0), atol=1e-5)
