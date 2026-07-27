"""Tests for modality-agnostic model components.

No training happens here. These tests check shapes, routing contracts, neutral
naming, and determinism of a forward pass.
"""

from __future__ import annotations

import dataclasses

import pytest
import torch

from p22.models import (
    VIEW_A,
    VIEW_B,
    VIEW_NAMES,
    BaselineMLP,
    ConcatFusionModel,
    FusionOutput,
    GatedFusionModel,
    RoutingGate,
    ViewEncoder,
    validate_route_override,
)
from p22.testing import make_synthetic_multimodal

N_CLASSES = 3
BIOLOGICAL_WORDS = ("gene", "rna", "atac", "morph", "expression", "protein", "cell_type")


@pytest.fixture(scope="module")
def views():
    dataset = make_synthetic_multimodal(n_donors=4, cells_per_donor=5, seed=5)
    return (
        torch.from_numpy(dataset.view_a),
        torch.from_numpy(dataset.view_b),
        dataset,
    )


@pytest.fixture
def gated(views):
    view_a, view_b, _ = views
    torch.manual_seed(0)
    return GatedFusionModel(view_a.shape[1], view_b.shape[1], N_CLASSES).eval()


@pytest.fixture
def concat(views):
    view_a, view_b, _ = views
    torch.manual_seed(0)
    return ConcatFusionModel(view_a.shape[1], view_b.shape[1], N_CLASSES).eval()


def test_view_encoder_shapes(views):
    view_a, _, _ = views
    encoder = ViewEncoder(view_a.shape[1], embed_dim=8)
    output = encoder(view_a)
    assert output.shape == (view_a.shape[0], 8)


def test_view_encoder_rejects_wrong_shape(views):
    view_a, view_b, _ = views
    encoder = ViewEncoder(view_a.shape[1])
    with pytest.raises(ValueError, match="features, encoder expects"):
        encoder(view_b)
    with pytest.raises(ValueError, match="two-dimensional"):
        encoder(view_a[0])


@pytest.mark.parametrize(
    "kwargs",
    [{"n_features": 0}, {"n_features": 4, "embed_dim": 0}, {"n_features": 4, "dropout": 1.0}],
)
def test_view_encoder_rejects_bad_sizes(kwargs):
    with pytest.raises(ValueError):
        ViewEncoder(**kwargs)


def test_baseline_mlp_shapes(views):
    view_a, _, _ = views
    model = BaselineMLP(view_a.shape[1], N_CLASSES, embed_dim=8).eval()
    with torch.no_grad():
        logits = model(view_a)
        embedding = model.embed(view_a)
    assert logits.shape == (view_a.shape[0], N_CLASSES)
    assert embedding.shape == (view_a.shape[0], 8)


def test_baseline_mlp_requires_two_classes(views):
    view_a, _, _ = views
    with pytest.raises(ValueError, match="n_classes must be >= 2"):
        BaselineMLP(view_a.shape[1], 1)


def test_fusion_output_fields_are_exactly_the_contract():
    assert [field.name for field in dataclasses.fields(FusionOutput)] == [
        "logits",
        "routing_weights",
        "branch_embeddings",
        "fused_embedding",
    ]


def test_gated_forward_contract(views, gated):
    view_a, view_b, _ = views
    with torch.no_grad():
        output = gated(view_a, view_b)
    n_cells = view_a.shape[0]
    assert output.logits.shape == (n_cells, N_CLASSES)
    assert output.routing_weights.shape == (n_cells, 2)
    assert set(output.branch_embeddings) == set(VIEW_NAMES)
    assert output.fused_embedding.shape == (n_cells, gated.embed_dim)
    torch.testing.assert_close(
        output.routing_weights.sum(dim=1), torch.ones(n_cells), rtol=1e-5, atol=1e-6
    )
    assert bool((output.routing_weights >= 0).all())


def test_concat_forward_reports_uniform_routing(views, concat):
    view_a, view_b, _ = views
    with torch.no_grad():
        output = concat(view_a, view_b)
    assert concat.has_gate is False
    assert output.routing_weights.shape == (view_a.shape[0], 2)
    torch.testing.assert_close(
        output.routing_weights, torch.full((view_a.shape[0], 2), 0.5), rtol=0, atol=0
    )
    assert output.fused_embedding.shape == (view_a.shape[0], concat.embed_dim * 2)


def test_view_a_only_override(views, gated):
    view_a, view_b, _ = views
    with torch.no_grad():
        output = gated(view_a, view_b, route_override=[1, 0])
    torch.testing.assert_close(
        output.routing_weights,
        torch.tensor([[1.0, 0.0]]).expand(view_a.shape[0], 2),
        rtol=0,
        atol=0,
    )
    torch.testing.assert_close(output.fused_embedding, output.branch_embeddings[VIEW_A])


def test_view_b_only_override(views, gated):
    view_a, view_b, _ = views
    with torch.no_grad():
        output = gated(view_a, view_b, route_override=[0, 1])
    torch.testing.assert_close(output.fused_embedding, output.branch_embeddings[VIEW_B])


def test_uniform_override(views, gated):
    view_a, view_b, _ = views
    with torch.no_grad():
        output = gated(view_a, view_b, route_override=[0.5, 0.5])
        expected = 0.5 * output.branch_embeddings[VIEW_A] + 0.5 * output.branch_embeddings[VIEW_B]
    torch.testing.assert_close(output.fused_embedding, expected)


@pytest.mark.parametrize(
    "override",
    [[1, 0, 0], [0.6, 0.6], [-0.5, 1.5], [float("nan"), 1.0], [0.2, 0.2]],
)
def test_invalid_overrides_are_rejected(views, gated, override):
    view_a, view_b, _ = views
    with pytest.raises(ValueError):
        gated(view_a, view_b, route_override=override)


def test_validate_route_override_accepts_plan_cases():
    for override in ([1, 0], [0, 1], [0.5, 0.5]):
        weights = validate_route_override(override)
        assert weights.shape == (2,)
        assert abs(float(weights.sum()) - 1.0) < 1e-6


def test_ablation_zeros_a_branch(views, gated):
    view_a, view_b, _ = views
    with torch.no_grad():
        output = gated(view_a, view_b, ablate_views=[VIEW_A])
    assert bool((output.branch_embeddings[VIEW_A] == 0).all())
    assert not bool((output.branch_embeddings[VIEW_B] == 0).all())


def test_ablation_changes_routing_and_logits(views, gated):
    view_a, view_b, _ = views
    with torch.no_grad():
        baseline = gated(view_a, view_b)
        ablated = gated(view_a, view_b, ablate_views=[VIEW_B])
    assert not torch.allclose(baseline.routing_weights, ablated.routing_weights)
    assert not torch.allclose(baseline.logits, ablated.logits)


def test_concat_supports_ablation(views, concat):
    view_a, view_b, _ = views
    with torch.no_grad():
        output = concat(view_a, view_b, ablate_views=[VIEW_B])
    assert bool((output.branch_embeddings[VIEW_B] == 0).all())


def test_unknown_ablation_name_is_rejected(views, gated):
    view_a, view_b, _ = views
    with pytest.raises(ValueError, match="unknown view name"):
        gated(view_a, view_b, ablate_views=["view_c"])


def test_mismatched_cell_counts_are_rejected(views, gated):
    view_a, view_b, _ = views
    with pytest.raises(ValueError, match="same number of cells"):
        gated(view_a, view_b[:-1])


def test_routing_gate_rejects_wrong_embedding_count():
    gate = RoutingGate(embed_dim=4)
    with pytest.raises(ValueError, match="expected 2 embeddings"):
        gate([torch.zeros(3, 4)])
    with pytest.raises(ValueError, match="n_views must be >= 2"):
        RoutingGate(embed_dim=4, n_views=1)


def test_forward_is_deterministic_for_a_fixed_seed(views):
    view_a, view_b, _ = views
    outputs = []
    for _ in range(2):
        torch.manual_seed(11)
        model = GatedFusionModel(view_a.shape[1], view_b.shape[1], N_CLASSES).eval()
        with torch.no_grad():
            outputs.append(model(view_a, view_b))
    torch.testing.assert_close(outputs[0].logits, outputs[1].logits, rtol=0, atol=0)
    torch.testing.assert_close(
        outputs[0].routing_weights, outputs[1].routing_weights, rtol=0, atol=0
    )


def test_models_expose_no_training_entry_point(gated, concat, views):
    view_a, _, _ = views
    for model in (gated, concat, BaselineMLP(view_a.shape[1], N_CLASSES)):
        assert not hasattr(model, "fit")
        assert not hasattr(model, "train_epochs")


def test_models_stay_on_cpu_by_default(gated):
    assert all(parameter.device.type == "cpu" for parameter in gated.parameters())


def test_names_carry_no_biological_meaning(gated, concat):
    text = " ".join(
        [
            type(gated).__name__,
            type(concat).__name__,
            *VIEW_NAMES,
            *(name for name, _ in gated.named_parameters()),
        ]
    ).lower()
    for word in BIOLOGICAL_WORDS:
        assert word not in text, word
    assert VIEW_A == "view_a" and VIEW_B == "view_b"
