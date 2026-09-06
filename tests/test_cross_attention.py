"""Architecture checks on synthetic tensors, not biological evidence."""

import pytest
import torch

from p22.models.cross_attention import CrossAttentionModel, TokenConcatFusionModel
from p22.models.fusion import VIEW_A, VIEW_B
from p22.training.loop import forward_logits


@pytest.mark.parametrize("kind", [TokenConcatFusionModel, CrossAttentionModel])
def test_token_models_have_finite_gradients_and_valid_ablations(kind):
    torch.manual_seed(22)
    model = kind(6, 5, 2, n_tokens=4, embed_dim=8, hidden_dim=16, dropout=0).eval()
    a, b = torch.randn(3, 6, requires_grad=True), torch.randn(3, 5, requires_grad=True)
    logits = forward_logits(model, {VIEW_A: a, VIEW_B: b})
    assert logits.shape == (3, 2)
    logits.square().sum().backward()
    for gradient in (a.grad, b.grad):
        assert torch.isfinite(gradient).all() and gradient.abs().sum() > 0
    for parameter in model.parameters():
        assert parameter.grad is not None and torch.isfinite(parameter.grad).all()
    if kind is CrossAttentionModel:
        q, k, v = model.attention.in_proj_weight.grad.chunk(3)
        assert all(gradient.abs().sum() > 0 for gradient in (q, k, v))
    for name, altered_a, altered_b in (
        (VIEW_A, a + 50, b),
        (VIEW_B, a, b + 50),
    ):
        expected = model(a, b, ablate_views=[name]).logits
        actual = model(altered_a, altered_b, ablate_views=[name]).logits
        torch.testing.assert_close(actual, expected)
    # Tokens are within cells: other cells cannot influence this prediction.
    torch.testing.assert_close(model(a[:1], b[:1]).logits, logits[:1])
    with pytest.raises(ValueError, match="unknown view"):
        model(a, b, ablate_views=["bogus"])


def test_attention_control_has_identical_token_encoders_and_extra_attention_parameters():
    torch.manual_seed(22)
    concat = TokenConcatFusionModel(6, 5, 2, n_tokens=4, embed_dim=8)
    torch.manual_seed(22)
    attention = CrossAttentionModel(6, 5, 2, n_tokens=4, embed_dim=8)
    for name in ("encoder_a", "encoder_b", "head"):
        for a, b in zip(
            getattr(concat, name).parameters(), getattr(attention, name).parameters(), strict=True
        ):
            torch.testing.assert_close(a, b)
    assert attention.has_gate is False
    assert attention.attention.batch_first
    assert sum(p.numel() for p in attention.parameters()) > sum(
        p.numel() for p in concat.parameters()
    )


def test_attention_direction_and_token_axes_are_explicit():
    model = CrossAttentionModel(6, 5, 2, n_tokens=4, embed_dim=8, dropout=0).eval()
    a, b = torch.randn(3, 6), torch.randn(3, 5)
    inputs = []
    handle = model.attention.register_forward_pre_hook(lambda module, args: inputs.append(args))
    model(a, b)
    handle.remove()
    query, key, value = inputs[0]
    assert query.shape == key.shape == value.shape == (3, 4, 8)
    torch.testing.assert_close(query, model.encoder_a(a).reshape(3, 4, 8))
    torch.testing.assert_close(key, model.encoder_b(b).reshape(3, 4, 8))
    torch.testing.assert_close(value, key)


@pytest.mark.parametrize(
    "overrides",
    [
        {"n_tokens": 1},
        {"n_tokens": True},
        {"n_heads": 3},
        {"n_heads": 0},
        {"embed_dim": 0},
        {"n_classes": 1},
    ],
)
def test_attention_rejects_degenerate_token_or_head_contracts(overrides):
    with pytest.raises(ValueError):
        CrossAttentionModel(**(dict(n_features_a=6, n_features_b=5, n_classes=2) | overrides))
