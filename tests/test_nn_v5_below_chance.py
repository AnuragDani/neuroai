"""Tests for V3 below-chance diagnosis decision tree."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _arm(mean: float, pooled: float) -> dict:
    return {
        "per_fold_auroc_mean": mean,
        "per_fold_auroc_sd": 0.1,
        "pooled_auroc": pooled,
    }


def test_pooling_artefact_when_means_near_half_and_no_fix():
    mod = _load("nn_v5_below_chance", "scripts/nn_v5_below_chance_diagnosis.py")
    summaries = [
        {"arm": "R3_ca", "mean_near_chance": True, "pooled_below_chance": True},
        {"arm": "R3_tc", "mean_near_chance": True, "pooled_below_chance": True},
        {"arm": "logreg_rna", "mean_near_chance": True, "pooled_below_chance": True},
    ]
    verdict, _ = mod.decide_verdict(summaries, v2_required_fix=False, positive_control_auroc=0.95)
    assert verdict == "POOLING_ARTEFACT"


def test_pipeline_bug_fixed_when_v2_required_fix():
    mod = _load("nn_v5_below_chance", "scripts/nn_v5_below_chance_diagnosis.py")
    summaries = [
        {"arm": "R3_ca", "mean_near_chance": False, "pooled_below_chance": True},
        {"arm": "R3_tc", "mean_near_chance": False, "pooled_below_chance": True},
        {"arm": "logreg_rna", "mean_near_chance": True, "pooled_below_chance": True},
    ]
    verdict, reason = mod.decide_verdict(
        summaries, v2_required_fix=True, positive_control_auroc=0.924
    )
    assert verdict == "PIPELINE_BUG_FIXED"
    assert "0.924" in reason


def test_real_anti_signal_when_means_low_and_v2_clean():
    mod = _load("nn_v5_below_chance", "scripts/nn_v5_below_chance_diagnosis.py")
    summaries = [
        {"arm": "R3_ca", "mean_near_chance": False, "pooled_below_chance": True},
        {"arm": "R3_tc", "mean_near_chance": False, "pooled_below_chance": True},
        {"arm": "logreg_rna", "mean_near_chance": False, "pooled_below_chance": True},
    ]
    verdict, _ = mod.decide_verdict(summaries, v2_required_fix=False, positive_control_auroc=0.95)
    assert verdict == "REAL_ANTI_SIGNAL_EXPLAINED"


def test_live_v1_v2_yield_pipeline_bug_fixed(tmp_path):
    mod = _load("nn_v5_below_chance", "scripts/nn_v5_below_chance_diagnosis.py")
    per_fold_path = ROOT / "docs/nn_v2/v5/per_fold_metrics.json"
    pc_path = ROOT / "docs/nn_v2/v5/positive_control.json"
    assert per_fold_path.is_file()
    assert pc_path.is_file()
    per_fold = json.loads(per_fold_path.read_text())
    pc = json.loads(pc_path.read_text())
    assert mod.shared_path_fix_present(pc)
    dx = mod.build_diagnosis(per_fold, pc)
    assert dx["verdict"] == "PIPELINE_BUG_FIXED"
    assert dx["positive_control_donor_auroc"] >= 0.9
    # Learned pooled below chance; neural per-fold means above chance.
    by = {s["arm"]: s for s in dx["learned_arms"]}
    assert by["R3_ca"]["pooled_auroc"] < 0.45
    assert by["R3_ca"]["per_fold_auroc_mean"] > 0.5
    md = mod.render_md(dx)
    assert md.count("\n") <= 60
    out = tmp_path / "v5"
    rc = mod.main(
        [
            "--out-dir",
            str(out),
            "--per-fold",
            str(per_fold_path),
            "--positive-control",
            str(pc_path),
        ]
    )
    assert rc == 0
    written = json.loads((out / "below_chance_diagnosis.json").read_text())
    assert written["verdict"] == "PIPELINE_BUG_FIXED"
    assert (out / "BELOW_CHANCE.md").is_file()
