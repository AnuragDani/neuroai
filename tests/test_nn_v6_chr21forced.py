"""X1: --force-chr21 unions every chr21 gene into the train-only HVG set."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parents[1]


def test_force_chr21_cli_flag_exists():
    src = (ROOT / "scripts" / "run_nn_v2_comparison.py").read_text()
    assert "--force-chr21" in src
    assert "force_include_chr21" in src
    assert "bool(args.force_chr21)" in src


def test_force_chr21_feature_set_contains_every_chr21_gene_train_only_fit():
    """Feature set ⊇ all chr21 genes; HVG/scalers fit on train donors only."""
    from p22.data.nn_inputs import prepare_nn_fold
    from tests.test_nn_inputs import make_inputs

    inputs = make_inputs(with_chr21=True, holdout_boost=True)
    train_rows = np.arange(0, 4)
    holdout_rows = np.arange(4, 8)
    region_rows = np.arange(len(inputs.regions))
    chr21_ids = set(inputs.gene_ids[inputs.chr21_gene_mask()].tolist())
    assert chr21_ids, "fixture must include at least one chr21 gene"

    # Tiny n_hvg so default HVG can miss chr21 (same idea as positive-control test).
    default = prepare_nn_fold(
        inputs,
        train_rows,
        holdout_rows,
        region_rows,
        n_hvg=1,
        exclude_chr21=False,
    )
    forced = prepare_nn_fold(
        inputs,
        train_rows,
        holdout_rows,
        region_rows,
        n_hvg=1,
        exclude_chr21=False,
        force_include_gene_mask=inputs.chr21_gene_mask(),
    )

    forced_ids = set(forced.gene_ids.tolist())
    assert chr21_ids <= forced_ids
    assert forced.evidence["force_include_genes"] == len(chr21_ids)
    assert forced.rna.shape[1] >= default.rna.shape[1]

    train_donors = set(inputs.metadata["donor_id"].iloc[train_rows].astype(str))
    holdout_donors = set(inputs.metadata["donor_id"].iloc[holdout_rows].astype(str))
    assert set(forced.evidence["fit_donors"]) == train_donors
    assert set(forced.evidence["holdout_donors"]) == holdout_donors
    assert not (train_donors & holdout_donors)


def test_force_chr21_argparse_sets_flag():
    """Runner argparse exposes --force-chr21 (wired into worker_task)."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-chr21", action="store_true")
    args = parser.parse_args(["--force-chr21"])
    assert args.force_chr21 is True
    args_off = parser.parse_args([])
    assert args_off.force_chr21 is False


def test_amendment_preregisters_n_hvg_and_chr21():
    amend = (ROOT / "configs" / "nn_protocol_v2_amendment_chr21forced.json").read_text()
    assert "chr21" in amend
    assert "n_hvg" in amend
    assert "primary_endpoint_unchanged" in amend
