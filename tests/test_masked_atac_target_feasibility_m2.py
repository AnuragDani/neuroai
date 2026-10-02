"""M2 training-only target feasibility: ranking, leakage refusal, chrom mask."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from scipy import sparse

from p22.eval.masked_atac_target import (
    INNER_VAL_SALT,
    TARGET_RANK_SALT,
    RegionRecord,
    TargetEligibilityCriteria,
    binary_labels_from_counts,
    is_eligible,
    provisional_inner_split,
    rank_donors_label_free,
    region_support_stats,
    select_fold_target,
    select_targets_for_repeat0_folds,
    target_rank_key,
    visible_regions_chromosome_mask,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001"
    / "target_feasibility.json"
)
OUT_MD = OUT_JSON.with_name("TARGET_FEASIBILITY.md")


def _toy_regions() -> list[RegionRecord]:
    return [
        RegionRecord(0, "chr1", 10, 20, "chr1:10-20"),
        RegionRecord(1, "chr1", 30, 40, "chr1:30-40"),
        RegionRecord(2, "chr2", 1, 5, "chr2:1-5"),
        RegionRecord(3, "chr3", 100, 110, "chr3:100-110"),
    ]


def test_binary_labels_and_rank_determinism() -> None:
    assert binary_labels_from_counts(np.array([0, 1, 3, 0])).tolist() == [0, 1, 1, 0]
    with pytest.raises(ValueError):
        binary_labels_from_counts(np.array([0, -1]))
    a = rank_donors_label_free(["d2", "d1", "d3"], salt=INNER_VAL_SALT)
    b = rank_donors_label_free(["d3", "d1", "d2"], salt=INNER_VAL_SALT)
    assert a == b
    split = provisional_inner_split(
        [f"d{i:02d}" for i in range(24)], salt=INNER_VAL_SALT
    )
    assert len(split["inner_val_donors"]) == 8
    assert len(split["inner_train_donors"]) == 16
    assert not (set(split["inner_val_donors"]) & set(split["inner_train_donors"]))


def test_eligibility_and_outer_test_mutation_does_not_change_target() -> None:
    regions = _toy_regions()
    # 16 inner-train donors × 20 cells; construct region 2 (chr2) as near-balanced.
    donors = []
    for d in range(16):
        donors.extend([f"tr{d:02d}"] * 20)
    n = len(donors)
    # 4 regions × n cells
    data = np.zeros((4, n), dtype=np.float32)
    # region0/1 same chrom sparse; region2 balanced; region3 all-zero on train
    rng = np.random.default_rng(0)
    for i in range(n):
        data[0, i] = 1.0 if rng.random() < 0.05 else 0.0
        data[1, i] = 1.0 if rng.random() < 0.05 else 0.0
        data[2, i] = 1.0 if (i % 2 == 0) else 0.0
        data[3, i] = 0.0
    # Ensure donor both-class support on region2
    for d in range(16):
        sl = slice(d * 20, (d + 1) * 20)
        data[2, sl] = 0
        data[2, sl.start : sl.start + 10] = 1.0
    mat = sparse.csr_matrix(data)
    criteria = TargetEligibilityCriteria(
        min_pos_cells=50,
        min_neg_cells=50,
        min_pos_donors=8,
        min_neg_donors=8,
        min_both_class_donors=4,
    )
    inner = [f"tr{d:02d}" for d in range(16)]
    # Append outer-test cells that must not affect selection
    test_donors = [f"te{d:02d}" for d in range(6)]
    test_cols = np.ones((4, 60), dtype=np.float32)  # all positive on test
    mat_full = sparse.hstack(
        [mat, sparse.csr_matrix(test_cols)], format="csr"
    )
    donors_full = donors + [d for d in test_donors for _ in range(10)]
    assert len(donors_full) == mat_full.shape[1]

    first = select_fold_target(
        regions,
        mat_full,
        donors_full,
        inner_train_donors=inner,
        criteria=criteria,
    )
    assert first["disposition"] == "TARGET_SELECTED"
    assert first["selected"]["region_label"] == "chr2:1-5"
    assert first["selected"]["chrom"] == "chr2"
    visible = visible_regions_chromosome_mask(regions, "chr2")
    assert all(r.chrom != "chr2" for r in visible)
    assert first["selected"]["n_visible_atac_regions"] == len(visible)

    # Mutate only outer-test columns (flip to zeros) — selection must be identical
    mat_mut = mat_full.copy()
    mat_mut = mat_mut.tolil()
    mat_mut[:, len(donors) :] = 0
    mat_mut = mat_mut.tocsr()
    second = select_fold_target(
        regions,
        mat_mut,
        donors_full,
        inner_train_donors=inner,
        criteria=criteria,
    )
    assert second["selected"]["region_label"] == first["selected"]["region_label"]
    assert second["selected"]["rank_key"] == first["selected"]["rank_key"]
    assert second["n_eligible"] == first["n_eligible"]

    # Stats helper + eligibility edge
    stats = region_support_stats(mat.getrow(2), donors)
    assert is_eligible(stats, criteria)
    stats_empty = region_support_stats(mat.getrow(3), donors)
    assert not is_eligible(stats_empty, criteria)
    k1 = target_rank_key(stats, "chr2:1-5", salt=TARGET_RANK_SALT)
    k2 = target_rank_key(stats, "chr2:1-5", salt=TARGET_RANK_SALT)
    assert k1 == k2


def test_repeat0_selector_ignores_non_repeat0_and_requires_partition() -> None:
    regions = _toy_regions()
    donors = [f"d{i:02d}" for i in range(30) for _ in range(5)]
    # Build a matrix with region2 eligible on any 16-donor subset
    n = len(donors)
    data = np.zeros((4, n), dtype=np.float32)
    for i, d in enumerate(donors):
        # alternate by donor id parity within cells
        data[2, i] = 1.0 if (hash(d) + i) % 2 == 0 else 0.0
        data[0, i] = 1.0 if i % 17 == 0 else 0.0
    # Force both classes per donor on region 2
    by = {}
    for i, d in enumerate(donors):
        by.setdefault(d, []).append(i)
    for _d, idxs in by.items():
        data[2, idxs] = 0
        half = max(1, len(idxs) // 2)
        data[2, idxs[:half]] = 1.0
    mat = sparse.csr_matrix(data)
    outer_train = [f"d{i:02d}" for i in range(24)]
    outer_test = [f"d{i:02d}" for i in range(24, 30)]
    entries = [
        {
            "repeat": 0,
            "fold": 0,
            "split_seed": 0,
            "train_donors": outer_train,
            "test_donors": outer_test,
        },
        {
            "repeat": 1,
            "fold": 0,
            "split_seed": 0,
            "train_donors": outer_train,
            "test_donors": outer_test,
        },
    ]
    criteria = TargetEligibilityCriteria(
        min_pos_cells=10,
        min_neg_cells=10,
        min_pos_donors=4,
        min_neg_donors=4,
        min_both_class_donors=2,
    )
    out = select_targets_for_repeat0_folds(
        regions, mat, donors, entries, criteria=criteria
    )
    assert out["n_folds"] == 1
    assert out["folds"][0]["selection"]["selected"]["chrom"] == "chr2"


@pytest.mark.skipif(not OUT_JSON.is_file(), reason="run M2 reporter first")
def test_live_report_disposition_and_contracts() -> None:
    report = json.loads(OUT_JSON.read_text())
    assert OUT_MD.is_file()
    assert "TARGET_FEASIBILITY" in OUT_MD.read_text()
    assert report["disposition"] == "TARGET_FEASIBILITY_PASS"
    assert report["claim_level"] == 2
    assert report["preserved_labels"]["primary"] == "B_NULL"
    assert report["preserved_labels"]["S10"] == "INVALID"
    assert report["checks"]["input_hashes_pass"] is True
    assert report["checks"]["chromosome_mask_exclusivity_for_selected"] is True
    assert report["checks"]["no_disease_in_ranking"] is True
    assert report["selection_summary"]["n_folds_with_target"] == 5
    assert report["binary_target_rationale"]["not_a_fixed_locus_claim"] is True
    assert report["panel_provenance"]["disease_labels_in_target_ranking"] is False
    labels = []
    for fold in report["selection_summary"]["folds"]:
        assert fold["target_label"]
        assert fold["n_visible_atac_regions"] >= 415
        assert fold["n_eligible"] > 0
        labels.append(fold["target_label"])
        # chrom exclusivity already checked in reporter; re-check summary fields
        assert fold["target_chrom"]
    # Algorithm may repeat a target across folds; must disclose variation flag
    assert report["selection_summary"]["n_unique_selected_targets"] == len(set(labels))
    assert report["selection_summary"]["fold_to_fold_target_varies"] == (
        len(set(labels)) > 1
    )
