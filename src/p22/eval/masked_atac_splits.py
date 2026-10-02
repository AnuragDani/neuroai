"""Freeze donor splits and matched paired cell sampling for masked ATAC pilot (M3).

Pins archival repeat-0 outer folds, adopts the M2 label-free inner-val carve as
the frozen pilot partition (so M2 targets remain valid), and samples one shared
cap/seed cell set with ``sample_donor_stratified_cells``. No fits; disease labels
are disclosed split provenance only and are not model features.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from p22.data.nn_sampling import DEFAULT_STRATA, sample_donor_stratified_cells
from p22.eval.masked_atac_target import (
    INNER_VAL_SALT,
    RegionRecord,
    provisional_inner_split,
    visible_regions_chromosome_mask,
)

SAMPLING_CAP = 256
SAMPLING_SEED = 22
SAMPLING_STRATA = DEFAULT_STRATA  # author_cell_type × library
OUTER_REPEAT = 0
OUTER_SPLIT_SEED = 0
N_OUTER_FOLDS = 5
N_OUTER_TEST_PER_FOLD = 6
N_DONORS = 30


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def sha256_lines(items: Sequence[str]) -> str:
    return sha256_text("\n".join(str(x) for x in items))


def sha256_ints(values: Sequence[int]) -> str:
    return sha256_lines([str(int(v)) for v in values])


def archival_repeat0_folds(
    per_fold_entries: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Extract and validate archival repeat-0 outer donor folds."""
    folds: list[dict[str, Any]] = []
    for entry in per_fold_entries:
        if int(entry["repeat"]) != OUTER_REPEAT:
            continue
        train = sorted(str(d) for d in entry["train_donors"])
        test = sorted(str(d) for d in entry["test_donors"])
        if set(train) & set(test):
            raise ValueError(f"fold {entry['fold']} train/test donor overlap")
        if len(train) != N_DONORS - N_OUTER_TEST_PER_FOLD:
            raise ValueError(
                f"fold {entry['fold']} expected "
                f"{N_DONORS - N_OUTER_TEST_PER_FOLD} train donors; got {len(train)}"
            )
        if len(test) != N_OUTER_TEST_PER_FOLD:
            raise ValueError(
                f"fold {entry['fold']} expected {N_OUTER_TEST_PER_FOLD} "
                f"test donors; got {len(test)}"
            )
        if len(set(train) | set(test)) != N_DONORS:
            raise ValueError(
                f"fold {entry['fold']} train∪test has "
                f"{len(set(train) | set(test))} donors; expected {N_DONORS}"
            )
        split_seed = entry.get("split_seed")
        if split_seed is not None and int(split_seed) != OUTER_SPLIT_SEED:
            raise ValueError(
                f"fold {entry['fold']} unexpected split_seed={split_seed}"
            )
        folds.append(
            {
                "repeat": OUTER_REPEAT,
                "fold": int(entry["fold"]),
                "split_seed": OUTER_SPLIT_SEED,
                "outer_train_donors": train,
                "outer_test_donors": test,
            }
        )
    folds.sort(key=lambda f: f["fold"])
    if len(folds) != N_OUTER_FOLDS:
        raise ValueError(f"expected {N_OUTER_FOLDS} repeat-0 folds; got {len(folds)}")
    return folds


def assert_each_donor_once_as_outer_test(folds: Sequence[Mapping[str, Any]]) -> list[str]:
    """Every cohort donor appears exactly once as outer-test across folds."""
    counts: dict[str, int] = {}
    for fold in folds:
        for donor in fold["outer_test_donors"]:
            counts[str(donor)] = counts.get(str(donor), 0) + 1
    if len(counts) != N_DONORS:
        raise ValueError(f"expected {N_DONORS} unique test donors; got {len(counts)}")
    bad = {d: c for d, c in counts.items() if c != 1}
    if bad:
        raise ValueError(f"donors not held out exactly once: {sorted(bad)[:5]}")
    return sorted(counts)


def freeze_inner_splits(
    folds: Sequence[Mapping[str, Any]],
    *,
    salt: str = INNER_VAL_SALT,
) -> list[dict[str, Any]]:
    """Adopt M2 label-free inner-val carve as the frozen pilot partition."""
    out: list[dict[str, Any]] = []
    for fold in folds:
        split = provisional_inner_split(fold["outer_train_donors"], salt=salt)
        if set(split["inner_train_donors"]) & set(fold["outer_test_donors"]):
            raise ValueError(f"fold {fold['fold']}: inner-train overlaps outer-test")
        if set(split["inner_val_donors"]) & set(fold["outer_test_donors"]):
            raise ValueError(f"fold {fold['fold']}: inner-val overlaps outer-test")
        if set(split["inner_train_donors"]) & set(split["inner_val_donors"]):
            raise ValueError(f"fold {fold['fold']}: inner-train/val overlap")
        union = set(split["inner_train_donors"]) | set(split["inner_val_donors"])
        if union != set(fold["outer_train_donors"]):
            raise ValueError(f"fold {fold['fold']}: inner split does not partition outer-train")
        out.append(
            {
                **dict(fold),
                "inner_train_donors": split["inner_train_donors"],
                "inner_val_donors": split["inner_val_donors"],
                "inner_val_salt": salt,
                "inner_split_status": "FROZEN",
            }
        )
    return out


def sample_matched_paired_cells(
    obs: pd.DataFrame,
    *,
    cap: int = SAMPLING_CAP,
    seed: int = SAMPLING_SEED,
    strata: tuple[str, ...] = SAMPLING_STRATA,
) -> dict[str, Any]:
    """One label-free donor×type×library sample shared by all arms.

    Disease / group columns are never read. Returns sorted row positions, cell
    IDs, and per-donor support relative to the cap.
    """
    required = ("donor_id", *strata)
    missing = [c for c in required if c not in obs.columns]
    if missing:
        raise KeyError(f"obs missing columns required for sampling: {missing}")
    # Explicitly refuse to consult disease/group even if present.
    forbidden_consulted = ("disease", "group", "disease_ontology_term_id")
    _ = forbidden_consulted  # documented non-inputs; not read below

    rows = sample_donor_stratified_cells(obs, cap=cap, seed=seed, strata=strata)
    cell_ids = obs.index.astype(str).to_numpy()[rows]
    donors = obs["donor_id"].astype(str).to_numpy()[rows]
    available = (
        obs["donor_id"].astype(str).value_counts().to_dict()
        if "donor_id" in obs.columns
        else {}
    )
    per_donor: list[dict[str, Any]] = []
    for donor in sorted(set(donors.tolist())):
        n_selected = int((donors == donor).sum())
        n_available = int(available.get(donor, n_selected))
        per_donor.append(
            {
                "donor_id": donor,
                "n_available_cells": n_available,
                "n_selected_cells": n_selected,
                "below_cap": n_available < cap,
                "at_cap": n_selected == cap and n_available >= cap,
            }
        )
    ordered_cell_ids = sorted(cell_ids.tolist())
    if len(ordered_cell_ids) != len(set(ordered_cell_ids)):
        raise ValueError("sampled cell IDs are not unique")
    return {
        "cap": cap,
        "seed": seed,
        "strata": list(strata),
        "sampler": "p22.data.nn_sampling.sample_donor_stratified_cells",
        "label_free": True,
        "disease_consulted": False,
        "row_positions": rows.astype(np.int64),
        "cell_ids_sorted": ordered_cell_ids,
        "cell_ids_sha256": sha256_lines(ordered_cell_ids),
        "n_cells_selected": len(ordered_cell_ids),
        "n_donors_selected": len(per_donor),
        "per_donor": per_donor,
        "n_donors_below_cap": sum(1 for d in per_donor if d["below_cap"]),
    }


def cells_for_donors(
    cell_ids: Sequence[str],
    cell_donors: Sequence[str],
    donor_set: Sequence[str],
) -> list[str]:
    """Return sorted cell IDs belonging to the requested donors."""
    want = {str(d) for d in donor_set}
    out = [
        str(cid)
        for cid, donor in zip(cell_ids, cell_donors, strict=True)
        if str(donor) in want
    ]
    return sorted(out)


def visible_feature_mask(
    regions: Sequence[RegionRecord], target_chrom: str
) -> dict[str, Any]:
    """Pin chromosome-masked visible ATAC region indices and labels."""
    visible = visible_regions_chromosome_mask(regions, target_chrom)
    if any(v.chrom == target_chrom for v in visible):
        raise RuntimeError("chromosome mask exclusivity failed")
    indices = [int(v.index) for v in visible]
    labels = [v.label for v in visible]
    return {
        "target_chrom": target_chrom,
        "n_visible_atac_regions": len(visible),
        "visible_region_indices": indices,
        "visible_region_labels": labels,
        "visible_region_indices_sha256": sha256_ints(indices),
        "visible_region_labels_sha256": sha256_lines(labels),
    }


def attach_targets_and_cells(
    frozen_folds: Sequence[Mapping[str, Any]],
    *,
    m2_fold_details: Sequence[Mapping[str, Any]],
    regions: Sequence[RegionRecord],
    sampled_cell_ids: Sequence[str],
    sampled_cell_donors: Sequence[str],
) -> list[dict[str, Any]]:
    """Combine frozen donors, M2 targets, visible masks, and sampled cells."""
    by_fold = {int(f["fold"]): f for f in m2_fold_details}
    out: list[dict[str, Any]] = []
    for fold in frozen_folds:
        fold_i = int(fold["fold"])
        if fold_i not in by_fold:
            raise KeyError(f"M2 target detail missing for fold {fold_i}")
        m2 = by_fold[fold_i]
        # Donor partitions must match M2 so targets remain valid.
        for key in (
            "outer_train_donors",
            "outer_test_donors",
            "inner_train_donors",
            "inner_val_donors",
        ):
            if sorted(m2[key]) != sorted(fold[key]):
                raise ValueError(
                    f"fold {fold_i}: M3 {key} differs from M2; re-run target "
                    "selection before fits (no outcome-driven redesign)"
                )
        selected = m2["selection"]["selected"]
        if selected is None:
            raise ValueError(f"fold {fold_i}: M2 has no selected target")
        mask = visible_feature_mask(regions, selected["chrom"])
        if int(selected["n_visible_atac_regions"]) != mask["n_visible_atac_regions"]:
            raise ValueError(f"fold {fold_i}: visible count mismatch vs M2")

        train_cells = cells_for_donors(
            sampled_cell_ids, sampled_cell_donors, fold["inner_train_donors"]
        )
        val_cells = cells_for_donors(
            sampled_cell_ids, sampled_cell_donors, fold["inner_val_donors"]
        )
        test_cells = cells_for_donors(
            sampled_cell_ids, sampled_cell_donors, fold["outer_test_donors"]
        )
        all_fold_cells = cells_for_donors(
            sampled_cell_ids,
            sampled_cell_donors,
            list(fold["outer_train_donors"]) + list(fold["outer_test_donors"]),
        )
        # Partition check on cells
        if set(train_cells) & set(val_cells) or set(train_cells) & set(test_cells) or set(
            val_cells
        ) & set(test_cells):
            raise ValueError(f"fold {fold_i}: cell partition overlap")
        if set(train_cells) | set(val_cells) | set(test_cells) != set(all_fold_cells):
            raise ValueError(f"fold {fold_i}: cells do not partition fold donors")

        out.append(
            {
                "repeat": fold["repeat"],
                "fold": fold_i,
                "split_seed": fold["split_seed"],
                "outer_train_donors": list(fold["outer_train_donors"]),
                "outer_test_donors": list(fold["outer_test_donors"]),
                "inner_train_donors": list(fold["inner_train_donors"]),
                "inner_val_donors": list(fold["inner_val_donors"]),
                "inner_val_salt": fold["inner_val_salt"],
                "inner_split_status": fold["inner_split_status"],
                "target": {
                    "region_index": int(selected["region_index"]),
                    "region_label": selected["region_label"],
                    "chrom": selected["chrom"],
                    "start": int(selected["start"]),
                    "end": int(selected["end"]),
                    "binary_definition": (
                        "1 if exact-region unique_fragment_overlap count > 0 else 0"
                    ),
                },
                "visible_atac": {
                    "n_visible_atac_regions": mask["n_visible_atac_regions"],
                    "visible_region_indices_sha256": mask[
                        "visible_region_indices_sha256"
                    ],
                    "visible_region_labels_sha256": mask[
                        "visible_region_labels_sha256"
                    ],
                    "visible_region_indices": mask["visible_region_indices"],
                },
                "cells": {
                    "inner_train_cell_ids": train_cells,
                    "inner_val_cell_ids": val_cells,
                    "outer_test_cell_ids": test_cells,
                    "inner_train_cell_ids_sha256": sha256_lines(train_cells),
                    "inner_val_cell_ids_sha256": sha256_lines(val_cells),
                    "outer_test_cell_ids_sha256": sha256_lines(test_cells),
                    "n_inner_train_cells": len(train_cells),
                    "n_inner_val_cells": len(val_cells),
                    "n_outer_test_cells": len(test_cells),
                },
                "donor_hashes": {
                    "outer_train_donors_sha256": sha256_lines(fold["outer_train_donors"]),
                    "outer_test_donors_sha256": sha256_lines(fold["outer_test_donors"]),
                    "inner_train_donors_sha256": sha256_lines(fold["inner_train_donors"]),
                    "inner_val_donors_sha256": sha256_lines(fold["inner_val_donors"]),
                },
            }
        )
    return out


def build_splits_and_sampling_manifest(
    *,
    region_sets_per_fold: Sequence[Mapping[str, Any]],
    m2_fold_details: Sequence[Mapping[str, Any]],
    regions: Sequence[RegionRecord],
    obs: pd.DataFrame,
    cap: int = SAMPLING_CAP,
    seed: int = SAMPLING_SEED,
) -> dict[str, Any]:
    """Assemble the frozen M3 SPLITS_AND_SAMPLING contract (no fits)."""
    outer = archival_repeat0_folds(region_sets_per_fold)
    all_donors = assert_each_donor_once_as_outer_test(outer)
    frozen = freeze_inner_splits(outer, salt=INNER_VAL_SALT)
    sample = sample_matched_paired_cells(obs, cap=cap, seed=seed)
    # Map sampled cells to donors for partition filtering.
    donor_by_cell = {
        str(cid): str(don)
        for cid, don in zip(
            obs.index.astype(str).to_numpy()[sample["row_positions"]],
            obs["donor_id"].astype(str).to_numpy()[sample["row_positions"]],
            strict=True,
        )
    }
    sampled_ids = sample["cell_ids_sorted"]
    sampled_donors = [donor_by_cell[cid] for cid in sampled_ids]
    folds = attach_targets_and_cells(
        frozen,
        m2_fold_details=m2_fold_details,
        regions=regions,
        sampled_cell_ids=sampled_ids,
        sampled_cell_donors=sampled_donors,
    )
    # Cross-arm identity: one sample object; all arms must reuse these cell sets.
    return {
        "disposition": "SPLITS_AND_SAMPLING_FROZEN",
        "outer_repeat": OUTER_REPEAT,
        "outer_split_seed": OUTER_SPLIT_SEED,
        "n_outer_folds": N_OUTER_FOLDS,
        "n_donors": len(all_donors),
        "all_donors_sorted": all_donors,
        "all_donors_sha256": sha256_lines(all_donors),
        "each_donor_once_as_outer_test": True,
        "inner_val_salt": INNER_VAL_SALT,
        "inner_split_status": "FROZEN",
        "inner_split_rule": (
            f"label-free sha256('{INNER_VAL_SALT}' + '\\n' + donor); "
            "first 8 -> inner_val; remaining 16 -> inner_train"
        ),
        "inner_matches_m2": True,
        "sampling": {
            "cap": sample["cap"],
            "seed": sample["seed"],
            "strata": sample["strata"],
            "sampler": sample["sampler"],
            "label_free": sample["label_free"],
            "disease_consulted": sample["disease_consulted"],
            "n_cells_selected": sample["n_cells_selected"],
            "n_donors_selected": sample["n_donors_selected"],
            "n_donors_below_cap": sample["n_donors_below_cap"],
            "cell_ids_sha256": sample["cell_ids_sha256"],
            "cell_ids_sorted": sample["cell_ids_sorted"],
            "per_donor": sample["per_donor"],
            "matched_across_arms": True,
            "matched_across_arms_note": (
                "One global donor×type×library sample; every arm and fold "
                "reuses the same per-donor cell IDs"
            ),
        },
        "archival_split_provenance": {
            "source": "configs/atac_tiebreak_region_sets_2026-09-21.json per_fold",
            "disease_stratified_disclosed": True,
            "disease_as_model_feature": False,
            "note": (
                "Archival outer folds are disease-stratified donor splits; "
                "disease/group/author_cell_type are not model input features. "
                "author_cell_type and library are sampling strata only."
            ),
        },
        "class_dependent_metrics_policy": (
            "If a partition lacks both target classes, report secondary "
            "class-dependent metrics (AUROC/BA) as unavailable; do not drop "
            "donors or targets. Log-loss remains defined."
        ),
        "folds": folds,
    }
