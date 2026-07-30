"""Real donor-held-out predictive comparison (C28 / G5–G6).

This module is the named entry point for the fixed baseline order under
identical donor resampling. The implementation lives in
:mod:`p22.eval.real_pipeline` so the notebook has one orchestrator.
"""

from __future__ import annotations

from p22.eval.real_pipeline import RealAnalysisState, run_real_model_comparison

__all__ = ["RealAnalysisState", "run_real_model_comparison"]
