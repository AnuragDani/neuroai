"""Offline tests for N8 program/module-token fusion.

Only synthetic matrices and tensors are used; no real data is read.
"""

import numpy as np
import pytest
import torch

from p22.models.fusion import VIEW_A, VIEW_B
from p22.models.mil import MILWrapper
from p22.models.program_tokens import (
    ProgramTokenConcat,
    ProgramTokenCrossAttention,
    annotate_programs,
    fit_programs,
    parameter_count,
    program_activities,
    top_program_features,
)


def _nonneg(rows, cols, seed):
    # Structured low-rank non-negative data so NMF converges within its iteration
    # budget (uniform noise needs many more iterations and emits ConvergenceWarning).
    rng = np.random.default_rng(seed)
    latent = min(rows, cols, 5)
    w = rng.random((rows, latent))
    h = rng.random((latent, cols))
    return (w @ h + 0.01 * rng.random((rows, cols))).astype(np.float64)


# --- NMF fitting / holdout isolation -------------------------------------------


def test_fit_programs_dictionary_ignores_holdout_perturbation():
    train = _nonneg(40, 12, 0)
    holdout = _nonneg(15, 12, 1)
    model = fit_programs(train, k=4, seed=7)
    # Re-fitting the same training matrix is reproducible.
    refit = fit_programs(train.copy(), k=4, seed=7)
    assert np.allclose(model.components_, refit.components_)
    # Perturbing holdout rows must not move the dictionary; only their activities move.
    before = program_activities(model, holdout)
    after = program_activities(model, holdout + 5.0)
    assert before.shape == (15, 4)
    assert not np.allclose(before.numpy(), after.numpy())
    assert np.allclose(model.components_, refit.components_)


def test_fit_programs_holdout_only_dictionary_differs():
    # Sanity: the two splits are genuinely different, so the isolation test is meaningful.
    train = _nonneg(40, 12, 0)
    holdout = _nonneg(40, 12, 1)
    a = fit_programs(train, k=4, seed=3)
    b = fit_programs(holdout, k=4, seed=3)
    assert not np.allclose(a.components_, b.components_)


def test_fit_programs_is_seed_deterministic():
    # nndsvda initialisation is deterministic, so the same seed reproduces the
    # dictionary exactly and the seed argument is accepted for all inits.
    train = _nonneg(30, 10, 2)
    a = fit_programs(train, k=3, seed=11)
    b = fit_programs(train, k=3, seed=11)
    assert np.allclose(a.components_, b.components_)
    assert a.components_.shape == (3, 10)
    assert a.reconstruction_err_ >= 0.0


def test_fit_programs_rejects_bad_inputs():
    train = _nonneg(10, 6, 0)
    with pytest.raises(ValueError):
        fit_programs(train - 1.0, k=3, seed=0)
    with pytest.raises(ValueError):
        fit_programs(np.full((10, 6), np.nan), k=3, seed=0)
    with pytest.raises(ValueError):
        fit_programs(train.ravel(), k=3, seed=0)
    with pytest.raises(ValueError):
        fit_programs(train, k=0, seed=0)
    with pytest.raises(ValueError):
        fit_programs(train, k=7, seed=0)
    with pytest.raises(ValueError):
        fit_programs(train, k=3, seed=0.5)


def test_program_activities_shape_and_feature_mismatch():
    train = _nonneg(20, 9, 4)
    model = fit_programs(train, k=5, seed=0)
    acts = program_activities(model, _nonneg(6, 9, 5))
    assert acts.shape == (6, 5)
    assert acts.dtype == torch.float32
    assert float(acts.min()) >= 0.0
    with pytest.raises(ValueError):
        program_activities(model, _nonneg(6, 8, 6))


# --- annotation helpers --------------------------------------------------------


def test_top_program_features_and_annotate():
    components = np.array([[0.1, 0.9, 0.2], [0.7, 0.05, 0.8]])
    names = ["g0", "g1", "g2"]
    ann = top_program_features(components, names, top_n=2)
    assert ann[0]["program"] == 0
    assert ann[0]["features"] == ["g1", "g2"]
    assert ann[0]["weights"][0] == pytest.approx(0.9)
    assert ann[1]["features"] == ["g2", "g0"]
    with pytest.raises(ValueError):
        top_program_features(components, names[:2], top_n=2)
    with pytest.raises(ValueError):
        top_program_features(components, names, top_n=0)

    rna = fit_programs(_nonneg(20, 3, 7), k=2, seed=0)
    atac = fit_programs(_nonneg(20, 4, 8), k=2, seed=0)
    payload = annotate_programs(rna, atac, ["a", "b", "c"], ["r0", "r1", "r2", "r3"], top_n=1)
    assert set(payload) == {"rna", "atac"}
    assert len(payload["rna"]) == 2 and len(payload["atac"]) == 2
    assert payload["atac"][0]["features"][0].startswith("r")


# --- token models --------------------------------------------------------------


def test_cross_attention_shapes_and_attention_rows_sum_to_one():
    torch.manual_seed(0)
    model = ProgramTokenCrossAttention(k_rna=16, k_atac=8, dim=32, heads=4, dropout=0.0)
    view_a = torch.rand(11, 16)
    view_b = torch.rand(11, 8)
    out = model(view_a, view_b, need_weights=True)
    assert out.logits.shape == (11, 2)
    assert out.fused_embedding.shape == (11, 64)
    assert out.branch_embeddings[VIEW_A].shape == (11, 32)
    assert out.branch_embeddings[VIEW_B].shape == (11, 32)
    assert out.routing_weights.shape == (11, 2)
    assert torch.allclose(out.routing_weights.sum(dim=1), torch.ones(11))
    weights = model.attention_weights.detach()
    assert weights is not None and weights.shape == (11, 16, 8)
    assert float(weights.min()) >= 0.0
    assert torch.allclose(weights.sum(dim=-1), torch.ones(11, 16), atol=1e-5)


def test_attention_weights_default_none_and_concat_has_none():
    torch.manual_seed(0)
    attn = ProgramTokenCrossAttention(k_rna=4, k_atac=3, dim=8, heads=2, dropout=0.0)
    attn(torch.rand(5, 4), torch.rand(5, 3))
    assert attn.attention_weights is None
    concat = ProgramTokenConcat(k_rna=4, k_atac=3, dim=8, dropout=0.0)
    concat(torch.rand(5, 4), torch.rand(5, 3), need_weights=True)
    assert concat.attention_weights is None


def test_concat_control_fewer_params_than_attention():
    concat = ProgramTokenConcat(k_rna=16, k_atac=8, dim=32, dropout=0.0)
    attn = ProgramTokenCrossAttention(k_rna=16, k_atac=8, dim=32, heads=4, dropout=0.0)
    n_concat, n_attn = parameter_count(concat), parameter_count(attn)
    assert n_concat == sum(p.numel() for p in concat.parameters())
    assert n_attn > n_concat
    # The attention model only adds the MultiheadAttention block on top of the control.
    assert n_attn - n_concat == sum(p.numel() for p in attn.attention.parameters())


def test_ablation_changes_fused_and_rejects_unknown():
    torch.manual_seed(0)
    model = ProgramTokenConcat(k_rna=5, k_atac=4, dim=8, dropout=0.0)
    view_a, view_b = torch.rand(6, 5), torch.rand(6, 4)
    full = model(view_a, view_b)
    ablated = model(view_a, view_b, ablate_views=(VIEW_A,))
    assert not torch.allclose(full.fused_embedding, ablated.fused_embedding)
    with pytest.raises(ValueError):
        model(view_a, view_b, ablate_views=("view_c",))


def test_forward_rejects_shape_mismatch():
    model = ProgramTokenConcat(k_rna=5, k_atac=4, dim=8, dropout=0.0)
    with pytest.raises(ValueError):
        model(torch.rand(6, 4), torch.rand(6, 4))
    with pytest.raises(ValueError):
        model(torch.rand(6, 5), torch.rand(6, 3))
    with pytest.raises(ValueError):
        model(torch.rand(6, 5), torch.rand(5, 4))


def test_constructor_validation():
    with pytest.raises(ValueError):
        ProgramTokenConcat(k_rna=0, k_atac=4)
    with pytest.raises(ValueError):
        ProgramTokenConcat(k_rna=4, k_atac=4, dim=0)
    with pytest.raises(ValueError):
        ProgramTokenConcat(k_rna=4, k_atac=4, n_classes=1)
    with pytest.raises(ValueError):
        ProgramTokenConcat(k_rna=4, k_atac=4, dropout=1.0)
    with pytest.raises(ValueError):
        ProgramTokenCrossAttention(k_rna=4, k_atac=4, dim=10, heads=3)
    with pytest.raises(ValueError):
        ProgramTokenCrossAttention(k_rna=4, k_atac=4, dim=8, heads=0)


@pytest.mark.parametrize("model_cls", [ProgramTokenConcat, ProgramTokenCrossAttention])
def test_models_work_inside_mil_wrapper(model_cls):
    torch.manual_seed(0)
    kwargs = {"heads": 2} if model_cls is ProgramTokenCrossAttention else {}
    model = model_cls(k_rna=6, k_atac=4, dim=8, dropout=0.0, **kwargs)
    wrapper = MILWrapper(model, dim=2 * model.dim).eval()
    views = {VIEW_A: torch.rand(7, 6), VIEW_B: torch.rand(7, 4)}
    logit_bag, attention, cell_logits = wrapper.forward_bag(views)
    assert logit_bag.shape == (1,)
    assert attention.shape == (7,)
    assert cell_logits.shape == (7,)
    assert torch.allclose(attention.sum(), torch.tensor(1.0), atol=1e-5)
    _, _, _, embeddings, branches = wrapper.forward_bag_full(views)
    assert embeddings.shape == (7, 2 * model.dim)
    assert branches is not None and set(branches) == {VIEW_A, VIEW_B}
