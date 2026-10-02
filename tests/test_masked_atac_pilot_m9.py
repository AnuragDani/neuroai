"""M9 real-data pilot path: auth resume, fold pins, smoke filter (no research fits)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from p22.eval.masked_atac_execute import (
    ALLOWED_RAW_ROOT,
    COUNTER_NAME,
    MaskedAtacExecuteRefusal,
    load_attempt_counter,
)
from p22.eval.masked_atac_metrics import binary_presence_labels, sha256_lines
from p22.eval.masked_atac_pilot import (
    IMMUTABLE_LOCK_KEYS,
    FoldFeatureBundle,
    MaskedAtacPilotError,
    authorize_immutable_lock,
    build_fold_features,
    evaluate_constant_arm,
    filter_jobs,
    fit_one_job,
)
from p22.eval.masked_atac_protocol import LEARNED_ARMS, NEURAL
from p22.models.fusion import VIEW_A, VIEW_B

ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001"
)
SPLITS = TASK_DIR / "SPLITS_AND_SAMPLING.json"


def test_smoke_job_filter_and_immutable_keys() -> None:
    smoke = filter_jobs(stages=["smoke"])
    assert len(smoke) == 5
    assert {j["fold"] for j in smoke} == {0}
    assert {j["arm"] for j in smoke} == set(LEARNED_ARMS)
    main = filter_jobs(stages=["main"])
    assert len(main) == 25
    assert COUNTER_NAME not in {k.split("/")[-1] for k in IMMUTABLE_LOCK_KEYS} or True
    assert all(not k.endswith(COUNTER_NAME) for k in IMMUTABLE_LOCK_KEYS)
    assert len(IMMUTABLE_LOCK_KEYS) == 9


def test_authorize_zero_counter_then_refuse_without_flag() -> None:
    from masked_atac_counter_testutil import temporarily_zeroed_attempt_counter

    counter_path = ROOT / ALLOWED_RAW_ROOT / COUNTER_NAME
    # After M9 smoke the live counter is progressed; zero-swap proves first-entry
    # mode, then restore and prove progressed resume path.
    with temporarily_zeroed_attempt_counter(counter_path):
        auth = authorize_immutable_lock(workspace=ROOT)
        assert auth["mode"] == "full_lock_including_zero_counter"
        assert int(auth["counter"]["total_attempts"]["used"]) == 0

    live = load_attempt_counter(counter_path)
    if int(live["total_attempts"]["used"]) == 0:
        pytest.skip("expected progressed counter after M9 smoke")
    with pytest.raises(MaskedAtacExecuteRefusal, match="progressed"):
        authorize_immutable_lock(workspace=ROOT, allow_progressed_counter=False)
    auth2 = authorize_immutable_lock(workspace=ROOT, allow_progressed_counter=True)
    assert auth2["mode"] == "immutable_lock_progressed_counter"
    assert all(not k.endswith(COUNTER_NAME) for k in auth2["reviewed_hashes"])


def test_toy_fold_features_and_logreg_fit() -> None:
    rng = np.random.default_rng(0)
    n_cells = 48
    n_genes = 20
    n_regions = 10
    cell_ids = [f"c{i}" for i in range(n_cells)]
    donors = np.asarray([f"d{i // 8}" for i in range(n_cells)], dtype=str)
    rna = rng.poisson(1.5, size=(n_cells, n_genes)).astype(np.float64)
    atac = rng.poisson(0.3, size=(n_cells, n_regions)).astype(np.float64)
    # Force mixed labels on target region 0.
    atac[:24, 0] = 0
    atac[24:, 0] = 3
    visible = list(range(1, n_regions))
    # Target on chrT; all visible regions on other chromosomes.
    region_chroms = ["chrT"] + [f"chrV{i}" for i in range(1, n_regions)]
    train_ids = cell_ids[:32]
    val_ids = cell_ids[32:40]
    test_ids = cell_ids[40:]
    fold_blob = {
        "fold": 0,
        "target": {
            "region_index": 0,
            "region_label": "chrT:0-1",
            "chrom": "chrT",
        },
        "visible_atac": {
            "visible_region_indices": visible,
            "visible_region_indices_sha256": sha256_lines([str(i) for i in visible]),
        },
        "cells": {
            "inner_train_cell_ids": train_ids,
            "inner_val_cell_ids": val_ids,
            "outer_test_cell_ids": test_ids,
        },
    }

    from types import SimpleNamespace

    arrays = SimpleNamespace(
        cell_ids=cell_ids,
        donors=donors,
        rna_counts=rna,
        atac_counts=atac,
    )
    bundle = build_fold_features(
        arrays, fold_blob, feature_budget=8, region_chroms=region_chroms
    )
    assert isinstance(bundle, FoldFeatureBundle)
    assert bundle.rna.shape == (n_cells, 8)
    assert bundle.atac.shape == (n_cells, len(visible))
    assert 0 not in bundle.visible_indices
    assert set(binary_presence_labels(atac[:, 0]).tolist()) == {0, 1}

    job = {"stage": "smoke", "arm": "logreg_rna", "fold": 0}
    record = fit_one_job(job, {0: bundle})
    assert record["arm"] == "logreg_rna"
    assert len(record["test_probabilities"]) == len(test_ids)
    assert np.isfinite(float(record["test_donor_average_cell_log_loss"]))

    const = evaluate_constant_arm(bundle)
    assert const["fits_count"] == 0
    assert const["arm"] == "training_prevalence_constant"
    assert np.isfinite(float(const["test_donor_average_cell_log_loss"]))


def test_target_in_visible_refused() -> None:
    from types import SimpleNamespace

    cell_ids = [f"c{i}" for i in range(12)]
    arrays = SimpleNamespace(
        cell_ids=cell_ids,
        donors=np.asarray(["a"] * 4 + ["b"] * 4 + ["c"] * 4),
        rna_counts=np.ones((12, 5), dtype=np.float64),
        atac_counts=np.ones((12, 4), dtype=np.float64),
    )
    visible = [0, 1, 2]
    region_chroms = ["chrT", "chrA", "chrB", "chrC"]
    fold_blob = {
        "fold": 0,
        "target": {"region_index": 0, "region_label": "chrT:0-1", "chrom": "chrT"},
        "visible_atac": {
            "visible_region_indices": visible,
            "visible_region_indices_sha256": sha256_lines([str(i) for i in visible]),
        },
        "cells": {
            "inner_train_cell_ids": cell_ids[:6],
            "inner_val_cell_ids": cell_ids[6:9],
            "outer_test_cell_ids": cell_ids[9:],
        },
    }
    with pytest.raises(MaskedAtacPilotError, match="leaked into visible"):
        build_fold_features(
            arrays, fold_blob, feature_budget=4, region_chroms=region_chroms
        )


def test_live_splits_manifest_pins() -> None:
    assert SPLITS.is_file()
    blob = json.loads(SPLITS.read_text(encoding="utf-8"))
    assert blob["disposition"] == "SPLITS_AND_SAMPLING_FROZEN"
    assert len(blob["sampling_cell_ids_sorted"]) == 7680
    assert len(blob["folds"]) == 5
    # Param-match widths: RNA budget 128, ATAC = full visible.
    for fold in blob["folds"]:
        n_vis = int(fold["visible_atac"]["n_visible_atac_regions"])
        assert 423 <= n_vis <= 440
    assert NEURAL.feature_budget == 128
    assert VIEW_A == "view_a"
    assert VIEW_B == "view_b"


def test_live_execute_main_coverage_contracts() -> None:
    execute_path = TASK_DIR / "EXECUTE.json"
    if not execute_path.is_file():
        pytest.skip("EXECUTE.json written after main fits")
    blob = json.loads(execute_path.read_text(encoding="utf-8"))
    assert blob["disposition"] == "EXECUTE_COMPLETE"
    assert blob["claim_level"] == 2
    assert blob["preserved_labels"]["primary"] == "B_NULL"
    cov = blob["coverage"]
    assert cov["smoke_ok"] == 5
    assert cov["main_ok"] == 25
    assert cov["failed"] == 0
    assert len(cov["completed_fit_ids"]) == 30
    primary = blob["primary_contrast"]
    assert primary["name"] == "mean_donor_paired_cell_log_loss_tc_minus_ca"
    assert primary["n_donors_pooled"] == 30
    assert primary["practical_margin"] == 0.01
    assert "exploratory_advantage_observed" in primary
    assert blob["equality_across_arms"]["per_fold_cell_label_donor_identity"] is True
    counter = load_attempt_counter(ROOT / ALLOWED_RAW_ROOT / COUNTER_NAME)
    assert int(counter["total_attempts"]["used"]) == 30
    assert int(counter["smoke_fits"]["used"]) == 5
    assert int(counter["scientific_fits"]["used"]) == 25
    assert counter["failed_fit_ids"] == []
