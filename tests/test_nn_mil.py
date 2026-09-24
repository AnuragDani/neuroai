"""Offline tests for the N5 gated-attention MIL head and bag construction.

Only synthetic tensors are used; no real data is read and no model is fit to
convergence here.
"""

import inspect

import numpy as np
import pytest
import torch
from sklearn.metrics import roc_auc_score

from p22.models.baselines import BaselineMLP
from p22.models.cross_attention import TokenConcatFusionModel
from p22.models.mil import GatedAttentionPool, MILWrapper
from p22.training.bags import MIN_PARTIAL_BAG, make_bags
from p22.training.mil_loop import predict_mil, train_mil


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


def _partial_signal_donors(
    n_donors: int = 12,
    cells_per_donor: int = 40,
    n_features: int = 8,
    signal_fraction: float = 0.1,
    seed: int = 0,
    prefix: str = "d",
    shift: float = 4.0,
) -> tuple[dict[str, np.ndarray], np.ndarray, np.ndarray]:
    """Build donors where only ``signal_fraction`` of positive-donor cells carry signal."""
    rng = np.random.default_rng(seed)
    n_signal = max(1, int(round(cells_per_donor * signal_fraction)))
    matrices, donors, labels = [], [], []
    for index in range(n_donors):
        label = index % 2
        matrix = rng.standard_normal((cells_per_donor, n_features)).astype(np.float32)
        if label == 1:
            rows = rng.choice(cells_per_donor, size=n_signal, replace=False)
            matrix[rows, 0] += shift
            matrix[rows, 1] -= shift
        matrices.append(matrix)
        donors.extend([f"{prefix}{index:02d}"] * cells_per_donor)
        labels.extend([label] * cells_per_donor)
    return {"rna": np.concatenate(matrices)}, np.array(donors), np.array(labels)


def test_synthetic_partial_signal_reaches_donor_auroc():
    train = _partial_signal_donors(seed=0)
    val = _partial_signal_donors(seed=100, prefix="v")
    model = MILWrapper(BaselineMLP(n_features=8, n_classes=2, embed_dim=8), dim=8)
    record = train_mil(
        model, train[0], train[1], train[2], val[0], val[1], val[2],
        cfg={"seed": 0, "max_epochs": 30, "patience": 6},
    )
    assert record.epochs_run <= 30
    assert record.selection_metric == "negative_donor_log_loss"
    assert record.selection_unit == "donor"
    scored = predict_mil(record.model, val[0], val[1])
    positive = set(val[1][val[2] == 1].tolist())
    targets = np.array([int(donor in positive) for donor in scored["donor_ids"]])
    assert len(targets) == 12 and targets.sum() == 6
    assert roc_auc_score(targets, scored["donor_probabilities"]) >= 0.9


def test_predict_mil_shapes_and_per_donor_attention():
    train = _partial_signal_donors(seed=1)
    val = _partial_signal_donors(seed=101, prefix="v")
    model = MILWrapper(BaselineMLP(n_features=8, n_classes=2, embed_dim=8), dim=8)
    record = train_mil(
        model, train[0], train[1], train[2], val[0], val[1], val[2],
        cfg={"seed": 0, "max_epochs": 2},
    )
    scored = predict_mil(record.model, val[0], val[1])
    n_cells = len(val[1])
    assert len(scored["donor_ids"]) == 12
    assert scored["donor_probabilities"].shape == (12,)
    assert scored["donor_logits"].shape == (12,)
    assert scored["cell_logits"].shape == (n_cells,)
    assert scored["attention"].shape == (n_cells,)
    for donor in scored["donor_ids"]:
        rows = val[1] == donor
        assert scored["attention"][rows].sum() == pytest.approx(1.0, abs=1e-5)


def test_train_mil_signature_has_no_test_arrays():
    parameters = set(inspect.signature(train_mil).parameters)
    assert not any("test" in name.lower() for name in parameters)
    assert {"train_arrays", "val_arrays", "donors", "val_donors"} <= parameters
