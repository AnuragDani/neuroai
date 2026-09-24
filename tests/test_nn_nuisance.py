"""Offline tests for the N6 conditional gradient-reversal nuisance adversary.

Only synthetic tensors are used; no real data is read.
"""

import math

import numpy as np
import pytest
import torch
from sklearn.linear_model import LogisticRegression
from torch.nn import functional as F

from p22.models.encoders import ViewEncoder
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


_PLANTED_EPOCHS = 1500
_PLANTED_SEEDS = (0, 1)


def _planted_batch_embeddings(seed: int, lambda_adv: float, epochs: int = _PLANTED_EPOCHS):
    """Train a tiny encoder+head on synthetic cells with a planted batch direction.

    Feature 0 carries the disease label and feature 1 the sequencing batch, so a
    batch probe can recover the nuisance from embeddings unless the adversary
    strips it.
    """
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)
    n_cells = 400
    labels = np.array([i % 2 for i in range(n_cells)])
    batch = np.array([(i // 2) % 2 for i in range(n_cells)])
    features = rng.normal(0.0, 0.4, (n_cells, 6)).astype(np.float32)
    features[:, 0] += np.where(labels == 1, 2.0, -2.0)  # disease signal
    features[:, 1] += np.where(batch == 1, 3.0, -3.0)  # nuisance signal
    x = torch.tensor(features)
    y = torch.tensor(labels, dtype=torch.long)
    b = torch.tensor(batch, dtype=torch.long)

    encoder = ViewEncoder(6, embed_dim=4, hidden_dim=16, dropout=0.0)
    head = torch.nn.Linear(4, 2)
    adversary = ConditionalNuisanceAdversary(dim=4, n_library=2, n_batch=2, n_qc=5, hidden=32)
    params = list(encoder.parameters()) + list(head.parameters())
    if lambda_adv > 0.0:
        params += list(adversary.parameters())
    optimiser = torch.optim.Adam(params, lr=3e-3)

    for epoch in range(epochs):
        embeddings = encoder(x)
        loss = F.cross_entropy(head(embeddings), y)
        if lambda_adv > 0.0:
            losses = adversary_losses(
                adversary,
                embeddings,
                y,
                y,  # library is perfectly correlated with the label in this toy setup
                b,
                torch.zeros(n_cells, 5),
                gamma_schedule(epoch / (epochs - 1)),
            )
            loss = loss + lambda_adv * losses["total"]
        optimiser.zero_grad()
        loss.backward()
        optimiser.step()

    encoder.eval()
    with torch.no_grad():
        return encoder(x).numpy(), labels, batch


def _within_label_batch_probe(embeddings, labels, batch) -> float:
    """Mean linear batch-probe accuracy computed within each label class."""
    scores = []
    for value in (0, 1):
        mask = labels == value
        probe = LogisticRegression(max_iter=1000).fit(embeddings[mask], batch[mask])
        scores.append(probe.score(embeddings[mask], batch[mask]))
    return float(np.mean(scores))


def test_adversary_strips_planted_batch_signal():
    """GRL adversary removes a planted batch direction without erasing the label.

    Plan N6 acceptance: post-training within-label batch-probe accuracy drops by
    >= 10 points versus lambda_adv=0, while the label stays recoverable.
    """
    control, regularised, label_scores = [], [], []
    for seed in _PLANTED_SEEDS:
        c_emb, labels, batch = _planted_batch_embeddings(seed, 0.0)
        a_emb, _, _ = _planted_batch_embeddings(seed, 3.0)
        control.append(_within_label_batch_probe(c_emb, labels, batch))
        regularised.append(_within_label_batch_probe(a_emb, labels, batch))
        label_scores.append(
            LogisticRegression(max_iter=1000).fit(a_emb, labels).score(a_emb, labels)
        )

    mean_control = float(np.mean(control))
    mean_regularised = float(np.mean(regularised))
    assert mean_control >= 0.80, f"planted batch not learned at lambda=0: {mean_control:.3f}"
    assert mean_control - mean_regularised >= 0.10, (
        f"batch probe only dropped {mean_control - mean_regularised:.3f}: "
        f"control={mean_control:.3f} regularised={mean_regularised:.3f}"
    )
    assert min(label_scores) >= 0.90, f"label erased by adversary: {label_scores}"
