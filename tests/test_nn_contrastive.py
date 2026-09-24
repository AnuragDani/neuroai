"""Offline tests for the N7 cross-modal InfoNCE pairing loss and retrieval metric.

Only synthetic tensors are used; no real data is read.
"""

import copy

import numpy as np
import pytest
import torch

from p22.models.contrastive import (
    PairingHead,
    branch_embeddings,
    info_nce,
    pairing_aux_loss,
    pairing_retrieval_top1,
)
from p22.models.cross_attention import TokenConcatFusionModel
from p22.models.fusion import VIEW_A, VIEW_B, FusionOutput
from p22.models.mil import MILWrapper
from p22.training.mil_loop import train_mil


class _IdentityFusion(torch.nn.Module):
    """Stub fusion whose branch embeddings are the raw view rows."""

    has_gate = False

    def forward(self, view_a, view_b):
        n = view_a.shape[0]
        return FusionOutput(
            logits=torch.zeros(n, 2),
            routing_weights=torch.full((n, 2), 0.5),
            branch_embeddings={VIEW_A: view_a, VIEW_B: view_b},
            fused_embedding=torch.cat([view_a, view_b], dim=1),
        )


def test_pairing_head_returns_unit_rows():
    torch.manual_seed(0)
    head = PairingHead(dim=10, proj=4)
    z_r, z_a = torch.randn(7, 10), torch.randn(7, 10)
    u, v = head(z_r, z_a)
    assert u.shape == (7, 4) and v.shape == (7, 4)
    assert torch.allclose(u.norm(dim=1), torch.ones(7), atol=1e-5)
    assert torch.allclose(v.norm(dim=1), torch.ones(7), atol=1e-5)


def test_pairing_head_rejects_bad_shapes():
    head = PairingHead(dim=10, proj=4)
    with pytest.raises(ValueError):
        head(torch.randn(7, 9), torch.randn(7, 10))
    with pytest.raises(ValueError):
        head(torch.randn(7, 10), torch.randn(6, 10))
    with pytest.raises(ValueError):
        PairingHead(dim=0, proj=4)


def test_info_nce_paired_beats_shuffled():
    torch.manual_seed(1)
    base = torch.nn.functional.normalize(torch.randn(64, 32), dim=-1)
    u = base
    v = torch.nn.functional.normalize(base + 0.05 * torch.randn(64, 32), dim=-1)
    perm = torch.randperm(64)
    paired = info_nce(u, v)
    shuffled = info_nce(u, v[perm])
    assert paired < shuffled
    assert paired.ndim == 0


def test_info_nce_is_symmetric():
    torch.manual_seed(2)
    u = torch.nn.functional.normalize(torch.randn(16, 8), dim=-1)
    v = torch.nn.functional.normalize(torch.randn(16, 8), dim=-1)
    assert info_nce(u, v).item() == pytest.approx(info_nce(v, u).item(), abs=1e-6)


def test_info_nce_rejects_bad_tau_and_shapes():
    u = torch.eye(4)
    with pytest.raises(ValueError):
        info_nce(u, u, tau=0.0)
    with pytest.raises(ValueError):
        info_nce(u, torch.eye(3))


def test_pairing_aux_loss_reads_branches_and_scales():
    torch.manual_seed(3)
    head = PairingHead(dim=5, proj=3)
    aux = pairing_aux_loss(head, lambda_nce=2.5)
    assert aux.head is head
    batch_out = {"branch_embeddings": {VIEW_A: torch.randn(9, 5), VIEW_B: torch.randn(9, 5)}}
    name, term = aux(batch_out, {})
    assert name == "pairing"
    u, v = head(batch_out["branch_embeddings"][VIEW_A], batch_out["branch_embeddings"][VIEW_B])
    assert term.item() == pytest.approx(2.5 * info_nce(u, v).item(), abs=1e-6)
    with pytest.raises(ValueError):
        aux({"views": {}}, {})


def test_retrieval_top1_perfect_when_paired():
    torch.manual_seed(4)
    model = _IdentityFusion()
    n = 512
    view_a = torch.randn(n, 6).numpy()
    arrays = {VIEW_A: view_a, VIEW_B: view_a.copy()}
    result = pairing_retrieval_top1(model, arrays, chunk_size=256)
    assert result["top1"] == pytest.approx(1.0)
    assert result["chance"] == pytest.approx(1 / 256)
    assert result["n_cells"] == n and result["n_chunks"] == 2


def test_retrieval_top1_far_below_chance_gain_when_shuffled():
    torch.manual_seed(5)
    model = _IdentityFusion()
    n = 512
    view_a = torch.randn(n, 6).numpy()
    arrays = {VIEW_A: view_a, VIEW_B: np.roll(view_a, shift=1, axis=0)}
    result = pairing_retrieval_top1(model, arrays, chunk_size=256)
    assert result["top1"] < 0.02


def test_branch_embeddings_through_mil_wrapper():
    torch.manual_seed(6)
    fusion = TokenConcatFusionModel(n_features_a=5, n_features_b=7, n_classes=2,
                                    n_tokens=2, embed_dim=4, hidden_dim=8)
    wrapper = MILWrapper(fusion, dim=8).eval()
    views = {VIEW_A: torch.randn(9, 5), VIEW_B: torch.randn(9, 7)}
    branches = branch_embeddings(wrapper, views)
    assert set(branches) == {VIEW_A, VIEW_B}
    assert branches[VIEW_A].shape == (9, 4)
    with pytest.raises(ValueError):
        branch_embeddings(torch.nn.Linear(3, 3), views)


def test_train_mil_optimises_pairing_head():
    torch.manual_seed(7)
    n_donors, per_donor, dim = 6, 12, 5
    all_donors = np.repeat([f"d{i}" for i in range(n_donors)], per_donor)
    all_labels = np.repeat([0, 1, 0, 1, 0, 1], per_donor)
    rng = np.random.default_rng(0)
    features = {VIEW_A: rng.normal(size=(len(all_donors), dim)),
                VIEW_B: rng.normal(size=(len(all_donors), dim))}
    is_train = np.isin(all_donors, ["d0", "d1", "d2", "d3"])
    train_arrays = {name: m[is_train] for name, m in features.items()}
    val_arrays = {name: m[~is_train] for name, m in features.items()}
    fusion = TokenConcatFusionModel(n_features_a=dim, n_features_b=dim, n_classes=2,
                                    n_tokens=2, embed_dim=3, hidden_dim=6)
    wrapper = MILWrapper(fusion, dim=6)
    head = PairingHead(dim=3, proj=2)
    before = copy.deepcopy(head.proj_r.weight.detach().clone())
    aux = pairing_aux_loss(head, lambda_nce=1.0)
    train_mil(
        wrapper, train_arrays, all_donors[is_train], all_labels[is_train],
        val_arrays, all_donors[~is_train], all_labels[~is_train],
        cfg={"bag_size": 6, "max_epochs": 3, "patience": 3, "seed": 1}, aux_losses=[aux],
    )
    assert not torch.allclose(before, head.proj_r.weight.detach())
