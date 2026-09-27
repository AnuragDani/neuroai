import numpy as np
import pytest
import torch
from torch import nn

from p22.models.fusion import VIEW_A, VIEW_B, FusionOutput
from p22.models.mil import MILWrapper
from p22.eval.metrics import balanced_accuracy

from run_nn_v2_faithfulness import run_intervention

class DummyEncoder(nn.Module):
    def __init__(self, use_input=True):
        super().__init__()
        self.use_input = use_input
    def forward(self, x):
        if self.use_input:
            return x.mean(dim=1, keepdim=True)
        return torch.zeros((x.shape[0], 1))

class DummyFusion(nn.Module):
    has_gate = False
    def __init__(self, use_a=True, use_b=True):
        super().__init__()
        self.encoder_a = DummyEncoder(use_a)
        self.encoder_b = DummyEncoder(use_b)
        self.head = nn.Linear(2, 1)
        nn.init.constant_(self.head.weight, 1.0)
        nn.init.constant_(self.head.bias, 0.0)

    def forward(self, view_a, view_b, **kwargs):
        za = self.encoder_a(view_a)
        zb = self.encoder_b(view_b)
        fused = torch.cat([za, zb], dim=1)
        logits = self.head(fused)
        weights = torch.full((view_a.shape[0], 2), 0.5)
        return FusionOutput(
            logits=torch.cat([-logits, logits], dim=1),
            routing_weights=weights,
            branch_embeddings={VIEW_A: za, VIEW_B: zb},
            fused_embedding=fused
        )

def test_synthetic_faithfulness():
    # synthetic model where ATAC is unused -> I1 Δ ≈ 0; I2 large
    # Let's create dummy train and test views
    train_views = {
        VIEW_A: np.random.randn(100, 10).astype(np.float32),
        VIEW_B: np.random.randn(100, 10).astype(np.float32),
    }
    test_views = {
        VIEW_A: np.random.randn(100, 10).astype(np.float32) + 1.0, # Shift to make a difference
        VIEW_B: np.random.randn(100, 10).astype(np.float32) + 1.0,
    }
    test_labels = np.random.randint(0, 2, 100)
    test_donors = np.repeat(np.arange(10), 10)
    test_cell_types = np.repeat(np.arange(2), 50)
    donor_truth = np.array([test_labels[test_donors == d][0] for d in np.unique(test_donors)])

    fusion = DummyFusion(use_a=True, use_b=False) # ATAC is unused
    model = MILWrapper(fusion, dim=2)
    
    from p22.training.mil_loop import predict_mil
    pred = predict_mil(model, test_views, test_donors)
    prob = pred["donor_probabilities"]
    logits = pred["cell_logits"]
    attn = pred["attention"]
    baseline_donor_pred = (prob >= 0.5).astype(int)
    baseline_cell_pred = (logits >= 0).astype(int)

    # I1: ablate ATAC (replace with train mean)
    res_i1 = run_intervention(
        "I1", model, test_views, test_labels, test_donors, test_cell_types,
        train_views, 0, baseline_donor_pred, baseline_cell_pred, donor_truth
    )
    assert res_i1["flip_rate"] == 0.0 # because ATAC is unused
    assert res_i1["ba_drop"] == 0.0

    # I2: ablate RNA (replace with train mean)
    res_i2 = run_intervention(
        "I2", model, test_views, test_labels, test_donors, test_cell_types,
        train_views, 0, baseline_donor_pred, baseline_cell_pred, donor_truth
    )
    assert res_i2["flip_rate"] > 0.0 # because RNA is used and shifted

    # NC: identity permutation
    res_nc = run_intervention(
        "NC", model, test_views, test_labels, test_donors, test_cell_types,
        train_views, 0, baseline_donor_pred, baseline_cell_pred, donor_truth
    )
    assert res_nc["flip_rate"] == 0.0
    assert res_nc["ba_drop"] == 0.0
