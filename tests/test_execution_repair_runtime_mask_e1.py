"""E1 runtime target-chromosome exclusion in actual feature construction."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from p22.eval.execution_repair_provenance import (
    EXPECTED_UNION_BED_SHA256,
    resolve_portable_path,
)
from p22.eval.execution_repair_runtime_mask import (
    enforce_runtime_feature_mask,
    load_union_bed_chroms,
)
from p22.eval.masked_atac_metrics import sha256_array, sha256_lines
from p22.eval.masked_atac_pilot import MaskedAtacPilotError, build_fold_features
from p22.eval.s7_ledger import sha256_file

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "tasks" / "runtime_mask_e1.json"
OUT_MD = ROOT / "tasks" / "RUNTIME_MASK_E1.md"
SPLITS = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001"
    / "SPLITS_AND_SAMPLING.json"
)


def _toy_arrays(
    *,
    n_cells: int = 24,
    n_genes: int = 8,
    n_regions: int = 6,
) -> tuple[SimpleNamespace, list[str], dict]:
    rng = np.random.default_rng(7)
    cell_ids = [f"c{i}" for i in range(n_cells)]
    donors = np.asarray([f"d{i // 6}" for i in range(n_cells)], dtype=str)
    rna = rng.poisson(1.2, size=(n_cells, n_genes)).astype(np.float64)
    atac = rng.poisson(0.4, size=(n_cells, n_regions)).astype(np.float64)
    atac[:12, 0] = 0
    atac[12:, 0] = 2
    # Target region 0 on chrT; visibles initially exclude chrT.
    region_chroms = ["chrT", "chrA", "chrB", "chrC", "chrD", "chrT"]
    visible = [1, 2, 3, 4]
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
            "inner_train_cell_ids": cell_ids[:16],
            "inner_val_cell_ids": cell_ids[16:20],
            "outer_test_cell_ids": cell_ids[20:],
        },
    }
    arrays = SimpleNamespace(
        cell_ids=cell_ids,
        donors=donors,
        rna_counts=rna,
        atac_counts=atac,
        region_chroms=region_chroms,
    )
    return arrays, region_chroms, fold_blob


def test_corrupt_visible_same_chrom_refused() -> None:
    arrays, region_chroms, fold_blob = _toy_arrays()
    # Corrupt manifest: inject same-chromosome partner (index 5) and rematch SHA.
    corrupt_visible = [1, 2, 3, 5]
    fold_blob["visible_atac"] = {
        "visible_region_indices": corrupt_visible,
        "visible_region_indices_sha256": sha256_lines(
            [str(i) for i in corrupt_visible]
        ),
    }
    with pytest.raises(MaskedAtacPilotError, match="chromosome-mask leak"):
        build_fold_features(
            arrays, fold_blob, feature_budget=4, region_chroms=region_chroms
        )


def test_target_count_perturbation_leaves_encoded_inputs() -> None:
    arrays, region_chroms, fold_blob = _toy_arrays()
    base = build_fold_features(
        arrays, fold_blob, feature_budget=4, region_chroms=region_chroms
    )
    mutated = SimpleNamespace(
        cell_ids=arrays.cell_ids,
        donors=arrays.donors,
        rna_counts=np.asarray(arrays.rna_counts, dtype=np.float64).copy(),
        atac_counts=np.asarray(arrays.atac_counts, dtype=np.float64).copy(),
        region_chroms=region_chroms,
    )
    mutated.atac_counts[:, 0] = (mutated.atac_counts[:, 0] + 9.0) * 4.0 + 1.0
    after = build_fold_features(
        mutated, fold_blob, feature_budget=4, region_chroms=region_chroms
    )
    assert base.rna_encoded_sha256 == after.rna_encoded_sha256
    assert base.atac_encoded_sha256 == after.atac_encoded_sha256
    assert np.array_equal(base.rna, after.rna)
    assert np.array_equal(base.atac, after.atac)
    assert base.labels_sha256 != after.labels_sha256
    assert sha256_array(base.labels.astype(np.float64)) != sha256_array(
        after.labels.astype(np.float64)
    )


def test_enforce_helper_and_missing_chroms_refuse() -> None:
    gate = enforce_runtime_feature_mask(
        region_chroms=["chrT", "chrA", "chrB"],
        visible_indices=[1, 2],
        target_index=0,
        target_chrom="chrT",
    )
    assert gate["runtime_mask_enforced"] is True
    assert gate["target_inclusive_depth_refused"] is True
    with pytest.raises(ValueError, match="chromosome-mask leak"):
        enforce_runtime_feature_mask(
            region_chroms=["chrT", "chrA", "chrT"],
            visible_indices=[1, 2],
            target_index=0,
            target_chrom="chrT",
        )
    arrays, _chroms, fold_blob = _toy_arrays()
    arrays_no_chrom = SimpleNamespace(
        cell_ids=arrays.cell_ids,
        donors=arrays.donors,
        rna_counts=arrays.rna_counts,
        atac_counts=arrays.atac_counts,
    )
    with pytest.raises(MaskedAtacPilotError, match="region_chroms required"):
        build_fold_features(arrays_no_chrom, fold_blob, feature_budget=4)


def test_live_union_bed_and_frozen_folds_exclusive() -> None:
    bed = resolve_portable_path(ROOT, "union_bed")
    assert bed.is_file()
    assert sha256_file(bed) == EXPECTED_UNION_BED_SHA256
    chroms = load_union_bed_chroms(bed)
    assert len(chroms) == 465
    blob = json.loads(SPLITS.read_text(encoding="utf-8"))
    assert blob["disposition"] == "SPLITS_AND_SAMPLING_FROZEN"
    for fold in blob["folds"]:
        gate = enforce_runtime_feature_mask(
            region_chroms=chroms,
            visible_indices=fold["visible_atac"]["visible_region_indices"],
            target_index=int(fold["target"]["region_index"]),
            target_chrom=str(fold["target"]["chrom"]),
        )
        assert gate["chromosome_mask_exclusivity_ok"] is True
    assert OUT_JSON.is_file(), "run scripts/report_execution_repair_runtime_mask_e1.py"
    assert OUT_MD.is_file()
    report = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    assert report["disposition"] == "RUNTIME_MASK_PASS"
    assert report["scientific_status_unchanged"]["masked_atac_m9"] == "NOT_AUTHORIZED"
    assert report["scientific_status_unchanged"]["primary"] == "B_NULL"
    assert "RUNTIME_MASK_PASS" in OUT_MD.read_text(encoding="utf-8")
