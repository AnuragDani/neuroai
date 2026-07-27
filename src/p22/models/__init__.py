"""Modality-agnostic model components.

View names are neutral (``view_a``, ``view_b``). Routing weights are signals, not
explanations.
"""

from p22.models.baselines import BaselineMLP
from p22.models.encoders import ViewEncoder
from p22.models.fusion import (
    VIEW_A,
    VIEW_B,
    VIEW_NAMES,
    ConcatFusionModel,
    FusionOutput,
    GatedFusionModel,
    RoutingGate,
    validate_route_override,
)

__all__ = [
    "VIEW_A",
    "VIEW_B",
    "VIEW_NAMES",
    "BaselineMLP",
    "ConcatFusionModel",
    "FusionOutput",
    "GatedFusionModel",
    "RoutingGate",
    "ViewEncoder",
    "validate_route_override",
]
