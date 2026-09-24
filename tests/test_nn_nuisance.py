"""Offline tests for the N6 conditional gradient-reversal nuisance adversary.

Only synthetic tensors are used; no real data is read.
"""

import math

import numpy as np
import pytest
import torch

from p22.models.nuisance import (
    ConditionalNuisanceAdversary,
    adversary_aux_loss,
    adversary_losses,
    gamma_schedule,
    grl,
)


def test_grl_forward_identity_and_gradient_is_neg_gamma():
    torch.manual_seed(0)
    gamma = 0.7
    x = torch.randn(6, 4, requires_grad=True)
    w = torch.randn(6, 4)
    y = grl(x, gamma)
    assert torch.allclose(y, x)  # forward identity
    (y * w).sum().backward()
    assert torch.allclose(x.grad, -gamma * w, atol=1e-6)


def test_grl_gamma_zero_stops_gradient():
    x = torch.randn(3, 2, requires_grad=True)
    y = grl(x, gamma_schedule(0.0))  # exactly 0
    y.sum().backward()
    assert torch.allclose(x.grad, torch.zeros_like(x))


def test_grl_rejects_bad_inputs():
    with pytest.raises(ValueError):
        grl(torch.zeros(2), -0.1)
    with pytest.raises(ValueError):
        grl(torch.zeros(2, dtype=torch.long), 0.5)


def test_gamma_schedule_endpoints_and_monotone():
    assert gamma_schedule(0.0) == pytest.approx(0.0)
    assert gamma_schedule(1.0) == pytest.approx(2 / (1 + math.exp(-10)) - 1, abs=1e-12)
    values = [gamma_schedule(p) for p in np.linspace(0, 1, 11)]
    assert all(b >= a for a, b in zip(values[:-1], values[1:], strict=True))
    assert all(0.0 <= v < 1.0 for v in values)
    with pytest.raises(ValueError):
        gamma_schedule(1.5)


def test_adversary_output_shapes():
    torch.manual_seed(1)
    adv = ConditionalNuisanceAdversary(dim=8, n_library=3, n_batch=4, n_qc=5, hidden=16)
    h = torch.randn(12, 8)
    labels = torch.tensor([0, 1] * 6)
    lib_logits, batch_logits, qc_pred = adv(h, labels, gamma=0.5)
    assert lib_logits.shape == (12, 3)
    assert batch_logits.shape == (12, 4)
    assert qc_pred.shape == (12, 5)


def test_adversary_conditions_on_label():
    torch.manual_seed(2)
    adv = ConditionalNuisanceAdversary(dim=4, n_library=2, n_batch=2, n_qc=2, hidden=8).eval()
    h = torch.randn(5, 4)
    labels_zero = torch.zeros(5, dtype=torch.long)
    labels_one = torch.ones(5, dtype=torch.long)
    lib_zero, _, _ = adv(h, labels_zero, gamma=0.5)
    lib_one, _, _ = adv(h, labels_one, gamma=0.5)
    assert not torch.allclose(lib_zero, lib_one)


def test_adversary_losses_finite_and_backprop():
    torch.manual_seed(3)
    adv = ConditionalNuisanceAdversary(dim=6, n_library=3, n_batch=3, n_qc=5, hidden=12)
    h = torch.randn(10, 6, requires_grad=True)
    losses = adversary_losses(
        adv,
        h,
        torch.tensor([0, 1] * 5),
        torch.tensor([0, 1, 2, 0, 1, 2, 0, 1, 2, 0]),
        torch.tensor([0, 1, 0, 1, 0, 1, 0, 1, 0, 1]),
        torch.randn(10, 5),
        gamma=0.8,
    )
    assert set(losses) == {"library", "batch", "qc", "total"}
    assert all(bool(torch.isfinite(v)) for v in losses.values())
    losses["total"].backward()
    assert h.grad is not None and float(h.grad.abs().sum()) > 0.0


def test_adversary_aux_loss_uses_bag_index_and_scales():
    torch.manual_seed(4)
    adv = ConditionalNuisanceAdversary(dim=4, n_library=2, n_batch=2, n_qc=5, hidden=8)
    cell_meta = {
        "labels": np.array([0, 1, 0, 1]),
        "library": np.array([0, 1, 0, 1]),
        "batch": np.array([1, 0, 1, 0]),
        "qc": np.zeros((4, 5), dtype=np.float32),
    }
    aux = adversary_aux_loss(adv, cell_meta, lambda_adv=2.0)
    batch_out = {"embeddings": torch.randn(2, 4, requires_grad=True)}
    batch_meta = {"index": np.array([0, 2]), "progress": 0.5}
    name, term = aux(batch_out, batch_meta)
    assert name == "adversary"
    assert term.ndim == 0 and bool(torch.isfinite(term))
    with pytest.raises(ValueError):
        adversary_aux_loss(adv, {"labels": np.zeros(2)}, lambda_adv=1.0)
    with pytest.raises(ValueError):
        adversary_aux_loss(adv, cell_meta, lambda_adv=-1.0)