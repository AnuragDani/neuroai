"""Offline tests for the N5 gated-attention MIL head and bag construction.

Only synthetic tensors are used; no real data is read and no model is fit to
convergence here.
"""

import numpy as np
import pytest
import torch

from p22.models.baselines import BaselineMLP
from p22.models.cross_attention import TokenConcatFusionModel
from p22.models.mil import GatedAttentionPool, MILWrapper
from p22.training.bags import MIN_PARTIAL_BAG, make_bags


def test_attention_sums_to_one_and_has_right_shape():
    torch.manual_seed(0)
    pool = GatedAttentionPool(dim=8, attn_dim=4)
    h = torch.randn(13, 8)
    pooled, attention = pool(h)
    assert pooled.shape == (8,)
    assert attention.shape == (13,)
    assert attention.sum().item() == pytest.approx(1.0, abs=1e-6)
    assert torch.all(attention >= 0)


def test_pooled_output_is_permutation_invariant():
    torch.manual_seed(1)
    pool = GatedAttentionPool(dim=8, attn_dim=4).eval()
    h = torch.randn(11, 8)
    perm = torch.randperm(11)
    pooled, attention = pool(h)
    pooled_perm, attention_perm = pool(h[perm])
    assert torch.allclose(pooled, pooled_perm, atol=1e-6)
    assert torch.allclose(attention_perm, attention[perm], atol=1e-6)


def test_mil_wrapper_single_view_forward_bag():
    torch.manual_seed(2)
    model = BaselineMLP(n_features=8, n_classes=2, embed_dim=6)
    wrapper = MILWrapper(model, dim=6).eval()
    views = {"view_a": torch.randn(20, 8)}
    logit_bag, attention, cell_logits = wrapper.forward_bag(views)
    assert logit_bag.shape == (1,)
    assert attention.shape == (20,)
    assert cell_logits.shape == (20,)
    assert attention.sum().item() == pytest.approx(1.0, abs=1e-6)


def test_mil_wrapper_fusion_forward_bag():
    torch.manual_seed(3)
    model = TokenConcatFusionModel(n_features_a=5, n_features_b=7, n_classes=2,
                                   n_tokens=2, embed_dim=4, hidden_dim=8)
    wrapper = MILWrapper(model, dim=2 * 4).eval()
    views = {"view_a": torch.randn(9, 5), "view_b": torch.randn(9, 7)}
    logit_bag, attention, cell_logits = wrapper.forward_bag(views)
    assert logit_bag.shape == (1,)
    assert attention.sum().item() == pytest.approx(1.0, abs=1e-6)
    assert cell_logits.shape == (9,)


def test_pool_rejects_bad_shape_and_empty_bag():
    pool = GatedAttentionPool(dim=4)
    with pytest.raises(ValueError):
        pool(torch.randn(3, 5))
    with pytest.raises(ValueError):
        pool(torch.zeros(0, 4))


def test_make_bags_purity_partial_rule_and_determinism():
    donors = np.array(["d0"] * 70 + ["d1"] * 20 + ["d2"] * 10)
    bags = make_bags(donors, bag_size=64, seed=0, epoch=0)
    assert len(bags) == 2
    for bag in bags:
        assert len(set(donors[bag].tolist())) == 1
    sizes = sorted(len(bag) for bag in bags)
    assert sizes == [20, 64]
    assert MIN_PARTIAL_BAG == 16

    same = make_bags(donors, bag_size=64, seed=0, epoch=0)
    assert all(np.array_equal(a, b) for a, b in zip(bags, same, strict=True))
    other = make_bags(donors, bag_size=64, seed=0, epoch=1)
    assert not np.array_equal(bags[0], other[0])


def test_make_bags_rejects_bad_inputs():
    with pytest.raises(ValueError):
        make_bags(np.zeros((3, 2), dtype=int))
    with pytest.raises(ValueError):
        make_bags(np.array([1, 2]), bag_size=0)
    with pytest.raises(ValueError):
        make_bags(np.array([1, 2]), seed=-1)
