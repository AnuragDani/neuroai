"""M3 splits/sampling freeze: donor partitions, matched cells, M2 continuity."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from p22.data.nn_sampling import sample_donor_stratified_cells
from p22.eval.masked_atac_splits import (
    SAMPLING_CAP,
    SAMPLING_SEED,
    archival_repeat0_folds,
    assert_each_donor_once_as_outer_test,
    attach_targets_and_cells,
    build_splits_and_sampling_manifest,
    freeze_inner_splits,
    sample_matched_paired_cells,
    sha256_lines,
    visible_feature_mask,
)
from p22.eval.masked_atac_target import INNER_VAL_SALT, RegionRecord, provisional_inner_split

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001"
    / "SPLITS_AND_SAMPLING.json"
)
OUT_MD = OUT_JSON.with_name("SPLITS_AND_SAMPLING.md")
M2_JSON = OUT_JSON.with_name("target_feasibility.json")
REGION_SETS = ROOT / "configs" / "atac_tiebreak_region_sets_2026-09-21.json"


def _toy_obs(n_donors: int = 6, cells_per: int = 40) -> pd.DataFrame:
    rows = []
    for d in range(n_donors):
        donor = f"D{d:02d}"
        for i in range(cells_per):
            rows.append(
                {
                    "cell_id": f"{donor}|c{i}",
                    "donor_id": donor,
                    "author_cell_type": "A" if i % 2 == 0 else "B",
                    "library": "L1" if i < cells_per // 2 else "L2",
                    "disease": "DS" if d % 2 == 0 else "CON",
                    "group": "g0",
                }
            )
    return pd.DataFrame(rows).set_index("cell_id")


def _toy_regions() -> list[RegionRecord]:
    return [
        RegionRecord(0, "chr1", 10, 20, "chr1:10-20"),
        RegionRecord(1, "chr1", 30, 40, "chr1:30-40"),
        RegionRecord(2, "chr2", 1, 5, "chr2:1-5"),
        RegionRecord(3, "chr3", 100, 110, "chr3:100-110"),
    ]


def test_archival_repeat0_each_donor_once_and_inner_freeze() -> None:
    region_sets = json.loads(REGION_SETS.read_text())
    folds = archival_repeat0_folds(region_sets["per_fold"])
    assert len(folds) == 5
    donors = assert_each_donor_once_as_outer_test(folds)
    assert len(donors) == 30
    frozen = freeze_inner_splits(folds, salt=INNER_VAL_SALT)
    for fold in frozen:
        assert fold["inner_split_status"] == "FROZEN"
        assert len(fold["inner_val_donors"]) == 8
        assert len(fold["inner_train_donors"]) == 16
        assert not (
            set(fold["inner_train_donors"]) & set(fold["outer_test_donors"])
        )
        # Matches M2 provisional rule exactly
        expected = provisional_inner_split(
            fold["outer_train_donors"], salt=INNER_VAL_SALT
        )
        assert fold["inner_train_donors"] == expected["inner_train_donors"]
        assert fold["inner_val_donors"] == expected["inner_val_donors"]


def test_sampling_deterministic_label_free_and_disease_ignored() -> None:
    obs = _toy_obs()
    a = sample_matched_paired_cells(obs, cap=10, seed=22)
    b = sample_matched_paired_cells(obs, cap=10, seed=22)
    assert a["cell_ids_sorted"] == b["cell_ids_sorted"]
    assert a["cell_ids_sha256"] == b["cell_ids_sha256"]
    assert a["disease_consulted"] is False
    # Flipping disease must not change selection (sampler never reads it).
    flipped = obs.copy()
    flipped["disease"] = np.where(flipped["disease"] == "DS", "CON", "DS")
    c = sample_matched_paired_cells(flipped, cap=10, seed=22)
    assert c["cell_ids_sorted"] == a["cell_ids_sorted"]
    # Direct sampler replay equality
    rows = sample_donor_stratified_cells(obs, cap=10, seed=22)
    assert sorted(obs.index.astype(str).to_numpy()[rows].tolist()) == a[
        "cell_ids_sorted"
    ]


def test_visible_mask_and_m2_mismatch_refused() -> None:
    regions = _toy_regions()
    mask = visible_feature_mask(regions, "chr1")
    assert mask["n_visible_atac_regions"] == 2
    assert all(regions[i].chrom != "chr1" for i in mask["visible_region_indices"])

    folds = freeze_inner_splits(
        [
            {
                "repeat": 0,
                "fold": 0,
                "split_seed": 0,
                "outer_train_donors": [f"D{i:02d}" for i in range(24)],
                "outer_test_donors": [f"T{i:02d}" for i in range(6)],
            }
        ]
    )
    # Build a fake M2 detail with mismatched inner_train
    m2 = [
        {
            "fold": 0,
            "outer_train_donors": folds[0]["outer_train_donors"],
            "outer_test_donors": folds[0]["outer_test_donors"],
            "inner_train_donors": folds[0]["inner_train_donors"][1:]
            + folds[0]["inner_val_donors"][:1],
            "inner_val_donors": folds[0]["inner_val_donors"][1:]
            + folds[0]["inner_train_donors"][:1],
            "selection": {
                "selected": {
                    "region_index": 2,
                    "region_label": "chr2:1-5",
                    "chrom": "chr2",
                    "start": 1,
                    "end": 5,
                    "n_visible_atac_regions": 3,
                }
            },
        }
    ]
    # Simpler: just assert attach raises on mismatch without full sample
    with pytest.raises(ValueError, match="differs from M2"):
        attach_targets_and_cells(
            folds,
            m2_fold_details=m2,
            regions=regions,
            sampled_cell_ids=[],
            sampled_cell_donors=[],
        )


def test_live_report_contracts_when_present() -> None:
    if not OUT_JSON.is_file() or not OUT_MD.is_file() or not M2_JSON.is_file():
        pytest.skip("M3 report artifacts not generated yet")
    report = json.loads(OUT_JSON.read_text())
    m2 = json.loads(M2_JSON.read_text())
    assert report["disposition"] == "SPLITS_AND_SAMPLING_FROZEN"
    assert report["sampling"]["cap"] == SAMPLING_CAP
    assert report["sampling"]["seed"] == SAMPLING_SEED
    assert report["inner_splits"]["matches_m2"] is True
    assert report["checks"]["each_donor_once_as_outer_test"] is True
    assert report["checks"]["chromosome_mask_exclusivity"] is True
    assert report["sampling"]["n_cells_selected"] == len(
        report["sampling_cell_ids_sorted"]
    )
    assert report["sampling"]["cell_ids_sha256"] == sha256_lines(
        report["sampling_cell_ids_sorted"]
    )
    # M2 continuity: donor lists and targets
    m2_by_fold = {int(f["fold"]): f for f in m2["fold_details"]}
    for fold in report["folds"]:
        m2f = m2_by_fold[fold["fold"]]
        assert fold["inner_train_donors"] == m2f["inner_train_donors"]
        assert fold["inner_val_donors"] == m2f["inner_val_donors"]
        assert fold["outer_test_donors"] == m2f["outer_test_donors"]
        assert (
            fold["target"]["region_label"]
            == m2f["selection"]["selected"]["region_label"]
        )
        assert (
            fold["visible_atac"]["n_visible_atac_regions"]
            == m2f["selection"]["selected"]["n_visible_atac_regions"]
        )
        # Cell partitions disjoint
        train = set(fold["cells"]["inner_train_cell_ids"])
        val = set(fold["cells"]["inner_val_cell_ids"])
        test = set(fold["cells"]["outer_test_cell_ids"])
        assert not (train & val)
        assert not (train & test)
        assert not (val & test)
    md = OUT_MD.read_text()
    assert "SPLITS_AND_SAMPLING_FROZEN" in md
    assert "No fits were run" in md


def test_build_manifest_toy_end_to_end() -> None:
    """Small synthetic end-to-end without the live 248k-cell H5AD."""
    # 30 donors, 24 train / 6 test per fold; reuse archival structure shape
    all_donors = [f"D{i:02d}" for i in range(30)]
    per_fold = []
    for fold_i in range(5):
        test = all_donors[fold_i * 6 : (fold_i + 1) * 6]
        train = [d for d in all_donors if d not in test]
        per_fold.append(
            {
                "repeat": 0,
                "fold": fold_i,
                "split_seed": 0,
                "train_donors": train,
                "test_donors": test,
            }
        )
    # Also add a repeat=1 entry that must be ignored
    per_fold.append(
        {
            "repeat": 1,
            "fold": 0,
            "split_seed": 0,
            "train_donors": all_donors[:24],
            "test_donors": all_donors[24:],
        }
    )
    regions = _toy_regions()
    outer = archival_repeat0_folds(per_fold)
    frozen = freeze_inner_splits(outer)
    # Fabricate M2 details matching frozen donors and a chr2 target
    m2_details = []
    for fold in frozen:
        m2_details.append(
            {
                "fold": fold["fold"],
                "outer_train_donors": fold["outer_train_donors"],
                "outer_test_donors": fold["outer_test_donors"],
                "inner_train_donors": fold["inner_train_donors"],
                "inner_val_donors": fold["inner_val_donors"],
                "selection": {
                    "selected": {
                        "region_index": 2,
                        "region_label": "chr2:1-5",
                        "chrom": "chr2",
                        "start": 1,
                        "end": 5,
                        "n_visible_atac_regions": 3,
                    }
                },
            }
        )
    obs = _toy_obs(n_donors=30, cells_per=20)
    # Remap donor names D00.. already match
    manifest = build_splits_and_sampling_manifest(
        region_sets_per_fold=per_fold,
        m2_fold_details=m2_details,
        regions=regions,
        obs=obs,
        cap=8,
        seed=22,
    )
    assert manifest["disposition"] == "SPLITS_AND_SAMPLING_FROZEN"
    assert manifest["sampling"]["n_cells_selected"] == 30 * 8
    assert len(manifest["folds"]) == 5
    # Same global sample implies fold-0 train cells ⊂ global set
    global_cells = set(manifest["sampling"]["cell_ids_sorted"])
    for fold in manifest["folds"]:
        assert set(fold["cells"]["inner_train_cell_ids"]) <= global_cells
        assert fold["visible_atac"]["n_visible_atac_regions"] == 3
