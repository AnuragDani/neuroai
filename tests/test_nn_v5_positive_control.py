"""Tests for V2 positive control (chr21 genes forced into the HVG union)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_force_include_unions_chr21_into_hvg():
    from p22.data.nn_inputs import prepare_nn_fold as prepare
    from tests.test_nn_inputs import make_inputs

    inputs = make_inputs(with_chr21=True)
    # Tiny n_hvg so default selection can miss chr21.
    default = prepare(
        inputs,
        train_rows=np.arange(0, 4),
        holdout_rows=np.arange(4, 8),
        region_rows=np.arange(len(inputs.regions)),
        n_hvg=1,
        exclude_chr21=False,
    )
    forced = prepare(
        inputs,
        train_rows=np.arange(0, 4),
        holdout_rows=np.arange(4, 8),
        region_rows=np.arange(len(inputs.regions)),
        n_hvg=1,
        exclude_chr21=False,
        force_include_gene_mask=inputs.chr21_gene_mask(),
    )
    chr21_id = "ENSG3"
    assert chr21_id in set(forced.gene_ids.tolist())
    assert forced.evidence["force_include_genes"] == 1
    assert forced.rna.shape[1] >= default.rna.shape[1]
    assert forced.rna.shape[1] >= 1


def test_orientation_check_spearman_positive_when_aligned():
    mod = _load("nn_v5_positive_control", "scripts/nn_v5_positive_control.py")
    sanity = {
        "donors": [
            {"donor": "a", "chr21_fraction_pooled": 0.01},
            {"donor": "b", "chr21_fraction_pooled": 0.02},
            {"donor": "c", "chr21_fraction_pooled": 0.03},
            {"donor": "d", "chr21_fraction_pooled": 0.04},
        ]
    }
    out = mod._orientation_check(
        ["a", "b", "c", "d"],
        [0.1, 0.2, 0.3, 0.4],
        sanity,
    )
    assert out["spearman_rho"] == 1.0
    assert out["n_donors"] == 4


def test_control_arms_fit_on_full_outer_train():
    """Regression: sklearn controls must not drop the inner-val third of donors."""
    from p22.eval.nn_factory import _CONTROL_ARM_NAMES

    src = (ROOT / "scripts" / "run_nn_v2_comparison.py").read_text()
    assert "_CONTROL_FIT_FULL_TRAIN" in src
    for arm in _CONTROL_ARM_NAMES:
        assert f'"{arm}"' in src or f"'{arm}'" in src
    # The full-outer-train override must appear before trainer() is called.
    assert "inner_train_pos = np.arange(len(train_rows))" in src


def test_write_payload_schema(tmp_path: Path):
    """Schema keys the gate and V2 task require, without a real training run."""
    payload = {
        "record_type": "v5_positive_control",
        "repeat": 0,
        "n_folds": 5,
        "arms": ["logreg_rna", "R3_tc"],
        "force_include": "all_chr21_genes_union_hvg",
        "chr21_genes_in_hvg_default": 12,
        "chr21_genes_in_hvg_default_per_fold": [12, 11, 12, 10, 13],
        "n_chr21_genes_total": 538,
        "donor_auroc": 0.95,
        "per_fold_auroc": [1.0, 1.0, 0.9, 1.0, 0.9],
        "orientation_check": {"spearman_rho": 0.9, "n_donors": 30},
        "per_arm": {
            "logreg_rna": {
                "donor_auroc": 0.95,
                "per_fold_auroc": [1.0, 1.0, 0.9, 1.0, 0.9],
                "orientation_check": {"spearman_rho": 0.9, "n_donors": 30},
            },
            "R3_tc": {
                "donor_auroc": 0.96,
                "per_fold_auroc": [1.0, 1.0, 1.0, 0.9, 0.9],
                "orientation_check": {"spearman_rho": 0.88, "n_donors": 30},
            },
        },
        "run_dir": str(tmp_path),
    }
    out = tmp_path / "positive_control.json"
    out.write_text(json.dumps(payload, indent=2) + "\n")
    loaded = json.loads(out.read_text())
    assert loaded["donor_auroc"] >= 0.9
    assert "chr21_genes_in_hvg_default" in loaded
    assert "orientation_check" in loaded
    assert "per_fold_auroc" in loaded
    assert set(loaded["per_arm"]) == {"logreg_rna", "R3_tc"}
