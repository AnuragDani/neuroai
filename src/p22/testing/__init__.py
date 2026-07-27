"""Deterministic synthetic test worlds.

Nothing here reads a dataset. These generators exist so that split, transform,
model, metric, and intervention code can be checked against a world whose ground
truth is known.
"""

from p22.testing.synthetic import (
    LATENT_DIM,
    SyntheticMultimodal,
    make_synthetic_multimodal,
)

__all__ = ["LATENT_DIM", "SyntheticMultimodal", "make_synthetic_multimodal"]
