"""Training-only masked-ATAC target ranking and eligibility (M2).

Selects one binary accessibility target (count > 0) per outer donor fold using
inner-training cells only. Outer-test target labels never enter ranking,
eligibility, or visible-feature construction. No model fitting.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import sparse

INNER_VAL_SALT = "p22-masked-atac-inner-val-v1"
TARGET_RANK_SALT = "p22-masked-atac-target-rank-v1"

# Frozen numerical eligibility (inner-train cells / donors only).
MIN_POS_CELLS = 100
MIN_NEG_CELLS = 100
MIN_POS_DONORS = 8
MIN_NEG_DONORS = 8
MIN_BOTH_CLASS_DONORS = 4
N_INNER_VAL_DONORS = 8
N_INNER_TRAIN_DONORS = 16


@dataclass(frozen=True)
class RegionRecord:
    """One exact-union interval."""

    index: int
    chrom: str
    start: int
    end: int
    label: str


@dataclass(frozen=True)
class TargetEligibilityCriteria:
    """Committed support thresholds for binary presence targets."""

    min_pos_cells: int = MIN_POS_CELLS
    min_neg_cells: int = MIN_NEG_CELLS
    min_pos_donors: int = MIN_POS_DONORS
    min_neg_donors: int = MIN_NEG_DONORS
    min_both_class_donors: int = MIN_BOTH_CLASS_DONORS


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def rank_donors_label_free(
    donors: Sequence[str], *, salt: str = INNER_VAL_SALT
) -> list[str]:
    """Deterministic donor order; no disease/target labels consulted."""
    unique = sorted({str(d) for d in donors})
    return sorted(unique, key=lambda d: (sha256_text(f"{salt}\n{d}"), d))


def provisional_inner_split(
    outer_train_donors: Sequence[str],
    *,
    n_val: int = N_INNER_VAL_DONORS,
    salt: str = INNER_VAL_SALT,
) -> dict[str, list[str]]:
    """Carve provisional inner-train / inner-val from outer-train donors.

    Label-free SHA256 ranking. M3 may pin the same rule; a different M3 carve
    requires re-running this frozen algorithm before fits (not performance-driven).
    """
    ranked = rank_donors_label_free(outer_train_donors, salt=salt)
    if len(ranked) != n_val + N_INNER_TRAIN_DONORS:
        raise ValueError(
            f"expected {n_val + N_INNER_TRAIN_DONORS} outer-train donors; "
            f"got {len(ranked)}"
        )
    val = sorted(ranked[:n_val])
    train = sorted(ranked[n_val:])
    if set(val) & set(train):
        raise ValueError("inner-train/val donor overlap")
    if set(val) | set(train) != set(ranked):
        raise ValueError("inner split does not partition outer-train")
    return {"inner_train_donors": train, "inner_val_donors": val}


def binary_labels_from_counts(counts: np.ndarray | sparse.spmatrix) -> np.ndarray:
    """Map measured counts to binary presence; zeros remain measured negatives."""
    if sparse.issparse(counts):
        arr = np.asarray(counts.toarray()).reshape(-1)
    else:
        arr = np.asarray(counts).reshape(-1)
    if np.any(arr < 0):
        raise ValueError("negative ATAC counts are refused")
    return (arr > 0).astype(np.int8)


def region_support_stats(
    region_counts: sparse.spmatrix,
    cell_donors: Sequence[str],
) -> dict[str, Any]:
    """Cell/donor positive-negative support for one region on a fixed cell set."""
    if region_counts.ndim != 2 or region_counts.shape[0] != 1:
        raise ValueError("region_counts must be shape (1, n_cells)")
    n_cells = int(region_counts.shape[1])
    if len(cell_donors) != n_cells:
        raise ValueError("cell_donors length must match region_counts columns")
    labels = binary_labels_from_counts(region_counts)
    n_pos = int(labels.sum())
    n_neg = n_cells - n_pos
    depth = float(region_counts.sum())
    by_donor: dict[str, list[int]] = defaultdict(list)
    for i, donor in enumerate(cell_donors):
        by_donor[str(donor)].append(i)
    n_pos_donors = 0
    n_neg_donors = 0
    n_both = 0
    for idxs in by_donor.values():
        vals = labels[idxs]
        pos = int(vals.sum())
        neg = len(vals) - pos
        if pos >= 1:
            n_pos_donors += 1
        if neg >= 1:
            n_neg_donors += 1
        if pos >= 1 and neg >= 1:
            n_both += 1
    prevalence = float(n_pos / n_cells) if n_cells else float("nan")
    return {
        "n_cells": n_cells,
        "n_pos_cells": n_pos,
        "n_neg_cells": n_neg,
        "prevalence": prevalence,
        "count_depth_sum": depth,
        "n_donors": len(by_donor),
        "n_pos_donors": n_pos_donors,
        "n_neg_donors": n_neg_donors,
        "n_both_class_donors": n_both,
    }


def is_eligible(stats: Mapping[str, Any], criteria: TargetEligibilityCriteria) -> bool:
    return (
        int(stats["n_pos_cells"]) >= criteria.min_pos_cells
        and int(stats["n_neg_cells"]) >= criteria.min_neg_cells
        and int(stats["n_pos_donors"]) >= criteria.min_pos_donors
        and int(stats["n_neg_donors"]) >= criteria.min_neg_donors
        and int(stats["n_both_class_donors"]) >= criteria.min_both_class_donors
    )


def target_rank_key(
    stats: Mapping[str, Any],
    region_label: str,
    *,
    salt: str = TARGET_RANK_SALT,
) -> tuple[float, float, str, str]:
    """Frozen ranking: closest to balanced, then deeper counts, then SHA, then label."""
    prev = float(stats["prevalence"])
    depth = float(stats["count_depth_sum"])
    return (abs(prev - 0.5), -depth, sha256_text(f"{salt}\n{region_label}"), region_label)


def visible_regions_chromosome_mask(
    regions: Sequence[RegionRecord], target_chrom: str
) -> list[RegionRecord]:
    return [r for r in regions if r.chrom != target_chrom]


def select_fold_target(
    regions: Sequence[RegionRecord],
    atac_regions_by_cells: sparse.spmatrix,
    cell_donors: Sequence[str],
    *,
    inner_train_donors: Sequence[str],
    criteria: TargetEligibilityCriteria | None = None,
    rank_salt: str = TARGET_RANK_SALT,
) -> dict[str, Any]:
    """Choose one eligible target from inner-train counts only.

    ``atac_regions_by_cells`` is the full union matrix (n_regions × n_cells).
    Only columns belonging to ``inner_train_donors`` are read. Outer-test cells
    are never indexed.
    """
    if criteria is None:
        criteria = TargetEligibilityCriteria()
    if atac_regions_by_cells.shape[0] != len(regions):
        raise ValueError("region count does not match matrix rows")
    donors = np.asarray(cell_donors, dtype=object).astype(str)
    train_set = {str(d) for d in inner_train_donors}
    train_idx = np.flatnonzero(np.isin(donors, list(train_set)))
    if train_idx.size == 0:
        raise ValueError("no inner-train cells")
    observed = set(donors[train_idx].tolist())
    if observed != train_set:
        missing = sorted(train_set - observed)
        raise ValueError(f"inner-train donors missing from cells: {missing[:5]}")
    sub = atac_regions_by_cells[:, train_idx]
    train_donors_per_cell = donors[train_idx].tolist()

    eligible_rows: list[dict[str, Any]] = []
    for region in regions:
        stats = region_support_stats(sub.getrow(region.index), train_donors_per_cell)
        if not is_eligible(stats, criteria):
            continue
        visible = visible_regions_chromosome_mask(regions, region.chrom)
        if not visible:
            continue
        if any(v.chrom == region.chrom for v in visible):
            raise RuntimeError("chromosome mask failed exclusivity")
        eligible_rows.append(
            {
                "region_index": region.index,
                "region_label": region.label,
                "chrom": region.chrom,
                "start": region.start,
                "end": region.end,
                "n_visible_atac_regions": len(visible),
                "rank_key": list(target_rank_key(stats, region.label, salt=rank_salt)),
                **stats,
            }
        )

    if not eligible_rows:
        return {
            "disposition": "NO_TARGET_SUPPORT",
            "selected": None,
            "n_eligible": 0,
            "n_candidates_scored": len(regions),
            "criteria": criteria.__dict__,
            "inner_train_donors": sorted(train_set),
            "n_inner_train_cells": int(train_idx.size),
        }

    eligible_rows.sort(key=lambda row: tuple(row["rank_key"]))
    selected = eligible_rows[0]
    return {
        "disposition": "TARGET_SELECTED",
        "selected": selected,
        "n_eligible": len(eligible_rows),
        "n_candidates_scored": len(regions),
        "runner_up": eligible_rows[1] if len(eligible_rows) > 1 else None,
        "criteria": criteria.__dict__,
        "inner_train_donors": sorted(train_set),
        "n_inner_train_cells": int(train_idx.size),
        "ranking_rule": (
            "minimize |inner_train_prevalence - 0.5|; then maximize count_depth_sum; "
            f"then sha256('{rank_salt}' + '\\n' + region_label); then region_label"
        ),
    }


def select_targets_for_repeat0_folds(
    regions: Sequence[RegionRecord],
    atac_regions_by_cells: sparse.spmatrix,
    cell_donors: Sequence[str],
    per_fold_entries: Sequence[Mapping[str, Any]],
    *,
    criteria: TargetEligibilityCriteria | None = None,
    inner_val_salt: str = INNER_VAL_SALT,
    rank_salt: str = TARGET_RANK_SALT,
) -> dict[str, Any]:
    """Run frozen selection on repeat-0 archival outer folds."""
    folds_out: list[dict[str, Any]] = []
    for entry in per_fold_entries:
        if int(entry["repeat"]) != 0:
            continue
        outer_train = list(entry["train_donors"])
        outer_test = list(entry["test_donors"])
        if set(outer_train) & set(outer_test):
            raise ValueError(f"fold {entry['fold']} train/test donor overlap")
        split = provisional_inner_split(outer_train, salt=inner_val_salt)
        if set(split["inner_train_donors"]) & set(outer_test):
            raise ValueError("inner-train overlaps outer-test")
        if set(split["inner_val_donors"]) & set(outer_test):
            raise ValueError("inner-val overlaps outer-test")
        result = select_fold_target(
            regions,
            atac_regions_by_cells,
            cell_donors,
            inner_train_donors=split["inner_train_donors"],
            criteria=criteria,
            rank_salt=rank_salt,
        )
        folds_out.append(
            {
                "repeat": 0,
                "fold": int(entry["fold"]),
                "split_seed": entry.get("split_seed"),
                "outer_train_donors": sorted(outer_train),
                "outer_test_donors": sorted(outer_test),
                "inner_val_donors": split["inner_val_donors"],
                "inner_train_donors": split["inner_train_donors"],
                "inner_val_salt": inner_val_salt,
                "selection": result,
            }
        )
    folds_out.sort(key=lambda f: f["fold"])
    selected_labels = [
        f["selection"]["selected"]["region_label"]
        for f in folds_out
        if f["selection"]["selected"] is not None
    ]
    if len(folds_out) != 5 or any(
        f["selection"]["disposition"] != "TARGET_SELECTED" for f in folds_out
    ):
        overall = "NO_TARGET_SUPPORT"
    else:
        overall = "TARGET_FEASIBILITY_PASS"
    return {
        "disposition": overall,
        "n_folds": len(folds_out),
        "n_folds_with_target": sum(
            1 for f in folds_out if f["selection"]["selected"] is not None
        ),
        "unique_selected_targets": sorted(set(selected_labels)),
        "n_unique_selected_targets": len(set(selected_labels)),
        "fold_to_fold_target_varies": len(set(selected_labels)) > 1,
        "folds": folds_out,
        "criteria": (criteria or TargetEligibilityCriteria()).__dict__,
        "inner_val_rule": (
            f"label-free sha256('{inner_val_salt}' + '\\n' + donor); "
            f"first {N_INNER_VAL_DONORS} -> inner_val; remaining "
            f"{N_INNER_TRAIN_DONORS} -> inner_train"
        ),
        "binary_target_definition": "1 if exact-region unique_fragment_overlap count > 0 else 0",
        "claim_limits": {
            "estimand": (
                "performance of the training-only target-selection algorithm "
                "under whole-chromosome ATAC masking; not single-locus performance"
            ),
            "not_claimed": [
                "regulatory function of the selected interval",
                "count-magnitude reconstruction",
                "biological cell state",
                "causal modality routing",
            ],
        },
    }
