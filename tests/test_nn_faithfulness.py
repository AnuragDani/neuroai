"""Synthetic checks for N13 faithfulness interventions."""

from __future__ import annotations

import numpy as np
import torch
from torch import nn

from p22.models.fusion import VIEW_A, VIEW_B, FusionOutput
from p22.models.mil import MILWrapper
from p22.training.mil_loop import predict_mil
from run_nn_v2_faithfulness import run_intervention


class _DummyEncoder(nn.Module):
    def __init__(self, use_input: bool = True) -> None:
        super().__init__()
        self.use_input = use_input

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.use_input:
            return x.mean(dim=1, keepdim=True)
        return torch.zeros((x.shape[0], 1), dtype=x.dtype, device=x.device)


class _DummyFusion(nn.Module):
    has_gate = False

    def __init__(self, use_a: bool = True, use_b: bool = True) -> None:
        super().__init__()
        self.encoder_a = _DummyEncoder(use_a)
        self.encoder_b = _DummyEncoder(use_b)
        self.head = nn.Linear(2, 1)
        nn.init.constant_(self.head.weight, 1.0)
        nn.init.constant_(self.head.bias, -5.0)

    def forward(self, view_a: torch.Tensor, view_b: torch.Tensor, **kwargs):
        za = self.encoder_a(view_a)
        zb = self.encoder_b(view_b)
        fused = torch.cat([za, zb], dim=1)
        logits = self.head(fused)
        weights = torch.full((view_a.shape[0], 2), 0.5)
        return FusionOutput(
            logits=torch.cat([-logits, logits], dim=1),
            routing_weights=weights,
            branch_embeddings={VIEW_A: za, VIEW_B: zb},
            fused_embedding=fused,
        )


def test_synthetic_atac_unused_i1_zero_i2_large():
    rng = np.random.default_rng(0)
    train_views = {
        VIEW_A: rng.normal(size=(100, 10)).astype(np.float32),
        VIEW_B: rng.normal(size=(100, 10)).astype(np.float32),
    }
    test_views = {
        VIEW_A: (rng.normal(size=(100, 10)) + 10.0).astype(np.float32),
        VIEW_B: (rng.normal(size=(100, 10)) + 10.0).astype(np.float32),
    }
    test_labels = rng.integers(0, 2, 100)
    test_donors = np.array([f"d{i}" for i in np.repeat(np.arange(10), 10)])
    test_cell_types = np.repeat(np.arange(2), 50)
    donor_ids = np.unique(test_donors)
    donor_truth = np.array([test_labels[test_donors == d][0] for d in donor_ids])

    fusion = _DummyFusion(use_a=True, use_b=False)  # ATAC unused
    model = MILWrapper(fusion, dim=2)
    pred = predict_mil(model, test_views, test_donors)
    order = {d: i for i, d in enumerate(pred["donor_ids"])}
    prob = np.array([pred["donor_probabilities"][order[d]] for d in donor_ids])
    baseline_cell_pred = (pred["cell_logits"] >= 0).astype(int)

    res_i1 = run_intervention(
        "I1",
        model,
        test_views,
        test_donors,
        test_cell_types,
        train_views,
        0,
        baseline_cell_pred,
        donor_truth,
        donor_ids,
        prob,
    )
    assert res_i1 is not None
    assert res_i1["flip_rate"] == 0.0
    assert res_i1["ba_drop"] == 0.0

    res_i2 = run_intervention(
        "I2",
        model,
        test_views,
        test_donors,
        test_cell_types,
        train_views,
        0,
        baseline_cell_pred,
        donor_truth,
        donor_ids,
        prob,
    )
    assert res_i2 is not None
    assert res_i2["flip_rate"] > 0.0

    res_nc = run_intervention(
        "NC",
        model,
        test_views,
        test_donors,
        test_cell_types,
        train_views,
        0,
        baseline_cell_pred,
        donor_truth,
        donor_ids,
        prob,
    )
    assert res_nc is not None
    assert res_nc["flip_rate"] == 0.0
    assert res_nc["ba_drop"] == 0.0
    assert np.allclose(res_nc["prob_donor"], prob)
