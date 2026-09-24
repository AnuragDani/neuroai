"""Offline tests for the N9 ladder model factory.

Every arm is built on small synthetic widths and one forward pass is run for the
embedding-fusion arms, so the bag-head width (fused embedding width) regression
for concat/cross-attention arms is caught without touching real data.
"""

import numpy as np
import pytest
import torch

from p22.eval.nn_factory import (
    ARM_NAMES,
    ControlPlan,
    build_arm,
    parameter_counts,
)
from p22.models.fusion import VIEW_A, VIEW_B

WIDTHS = {
    "n_features_a": 12,
    "n_features_b": 8,
    "n_classes": 2,
    "n_library": 3,
    "n_batch": 2,
    "k_rna": 3,
    "k_atac": 2,
}

CONTROL_ARMS = (
    "logreg_rna",
    "logreg_concat",
    "pseudobulk_rna_logistic",
    "chr21_dosage",
    "majority",
)

CELL_META = {
    "labels": np.array([0, 1]),
    "library": np.array([0, 1]),
    "batch": np.array([0, 1]),
    "qc": np.zeros((2, 5)),
}
CFG = {"cell_meta": CELL_META}


@pytest.mark.parametrize("arm_name", ARM_NAMES)
def test_every_arm_builds(arm_name):
    model, aux, trainer = build_arm(arm_name, WIDTHS, CFG)
    assert callable(trainer)
    assert isinstance(aux, tuple)
    if arm_name in CONTROL_ARMS:
        assert isinstance(model, ControlPlan)
    else:
        assert isinstance(model, torch.nn.Module)


@pytest.mark.parametrize(
    "arm_name",
    ["R1_ca", "R1_tc", "R2_ca", "R2_tc", "R3_ca", "R3_tc", "R3_gated"],
)
def test_bag_head_forward_matches_fused_width(arm_name):
    torch.manual_seed(0)
    model, _aux, _trainer = build_arm(arm_name, WIDTHS, CFG)
    model.eval()
    views = {
        VIEW_A: torch.randn(5, WIDTHS["n_features_a"]),
        VIEW_B: torch.randn(5, WIDTHS["n_features_b"]),
    }
    with torch.no_grad():
        logit_bag, attention, cell_logits, embeddings, _branches = model.forward_bag_full(views)
    assert logit_bag.shape == (1,)
    assert attention.shape == (5,)
    assert cell_logits.shape == (5,)
    assert embeddings.shape == (5, model.dim)


def test_parammatched_within_tolerance():
    model, _aux, _trainer = build_arm("R3_tc_parammatched", WIDTHS, CFG)
    info = model.match_info
    assert info["relative_error"] <= 0.10
    assert info["within_5pct"] == (info["relative_error"] <= 0.05)
    assert info["target_params"] > 0


def test_parameter_counts_cover_all_arms():
    counts = parameter_counts(WIDTHS, CFG)
    assert set(counts) == set(ARM_NAMES)
    for name in CONTROL_ARMS:
        assert counts[name] is None
    for name, entry in counts.items():
        if name in CONTROL_ARMS:
            continue
        assert entry["n_params"] > 0
    assert counts["R3_tc_parammatched"]["match"]["relative_error"] <= 0.10


def test_unknown_arm_rejected():
    with pytest.raises(ValueError, match="unknown arm"):
        build_arm("R9_nope", WIDTHS)


def test_synthetic_majority_control_fits():
    _model, _aux, trainer = build_arm("majority", WIDTHS)
    train = _Arm((np.zeros((4, 12)), np.zeros((4, 8))))
    fitted = trainer(None, train, train)
    proba = fitted.predict_proba({VIEW_A: np.zeros((3, 12)), VIEW_B: np.zeros((3, 8))})
    assert proba.shape == (3, 2)
    assert np.allclose(proba.sum(axis=1), 1.0)


class _Arm:
    """Minimal stand-in for :class:`~p22.eval.nn_factory.ArmData`."""

    def __init__(self, views):
        self.views = {VIEW_A: views[0], VIEW_B: views[1]}
        self.labels = np.array([0, 1, 0, 1])
        self.donors = np.array(["d0", "d0", "d1", "d1"])
        self.cell_meta = None
