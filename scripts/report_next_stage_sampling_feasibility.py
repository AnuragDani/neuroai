#!/usr/bin/env python3
"""Q4 sampling / age / class support feasibility and eligibility freeze.

Compares original global per-donor cap sampling with targeted per-type sampling,
reports donor/class/age/sex/library support, verifies seed-22 selected-cell
hashes against the immutable golden targeted JSON, freezes prospective
eligibility rules before any effect analysis, and records donor-count
uncertainty (not biological power). No fits, downloads, or package installs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import anndata as ad
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from p22.data.group_splits import build_repeated_group_split_report  # noqa: E402
from p22.data.nn_sampling import sample_donor_stratified_cells  # noqa: E402
from p22.eval.estimand import practical_margin, score_resolution  # noqa: E402

DEFAULT_H5AD = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/data/real/"
    "f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
)
DEFAULT_GLOBAL_SAMPLING = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/docs/nn_v2/sampling_cap1000_seed22.json"
)
DEFAULT_GOLDEN_TARGETED = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "next_stage_20260930"
    / "TARGETED_SAMPLING_FEASIBILITY.json"
)
DEFAULT_OUT_DIR = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "next_stage_20260930"
)
EXPECTED_H5AD_SHA256 = (
    "08d6eff265db6e6a2e1c4a259153588f3dba3c51f5f754736dc63c28795fcdbb"
)
EXPECTED_GLOBAL_SAMPLING_SHA256 = (
    "e515b2eee03804b3836256ba3e8b7604fa6a8043e50c06c36b24988250423b2f"
)
EXPECTED_GOLDEN_TARGETED_SHA256 = (
    "5c0fbd58d6c33db43c005e1c34fb6f82990efbe4d0fbe4c8ab2a0599a662b8d9"
)
CELL_TYPE_ORDER = (
    "AST",
    "IPC",
    "IPC_prol",
    "MIC",
    "NEU_CALB2",
    "NEU_CUX2",
    "NEU_RELN",
    "NEU_RORB",
    "NEU_SST",
    "NEU_TLE4",
    "NEU_low",
    "OPC",
    "RG",
    "RG_prol",
    "VASC",
)
SUPPORT_CUTOFF = 20
GLOBAL_CAP = 1000
TARGETED_CAP = 64
SAMPLING_SEED = 22
SPLIT_REPEATS = 5
SPLIT_FOLDS = 5
SPLIT_BASE_SEED = 0
OBS_COLUMNS = (
    "donor_id",
    "author_cell_type",
    "library",
    "dev_PCW",
    "sex",
    "disease",
)


class SamplingFeasibilityError(RuntimeError):
    """Nonzero-exit sampling feasibility failure."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(items: list[str]) -> str:
    return hashlib.sha256("\n".join(items).encode()).hexdigest()


def donor_class(donor_id: str) -> str:
    if "_CON_" in donor_id:
        return "CON"
    if "_DS_" in donor_id:
        return "DS"
    raise SamplingFeasibilityError(f"cannot parse class from donor_id={donor_id!r}")


def load_obs(h5ad_path: Path) -> pd.DataFrame:
    adata = ad.read_h5ad(h5ad_path, backed="r")
    try:
        missing = [c for c in OBS_COLUMNS if c not in adata.obs.columns]
        if missing:
            raise SamplingFeasibilityError(f"missing obs columns: {missing}")
        obs = adata.obs[list(OBS_COLUMNS)].copy()
    finally:
        adata.file.close()
    for column in OBS_COLUMNS:
        obs[column] = obs[column].astype(str)
    if not obs.index.is_unique:
        raise SamplingFeasibilityError("obs index is not unique")
    return obs


def empty_class_counts() -> dict[str, dict[str, int]]:
    return {
        "CON": {
            "available_donors": 0,
            "available_donors_ge20": 0,
            "selected_donors": 0,
            "selected_donors_ge20": 0,
            "available_cells": 0,
            "selected_cells": 0,
        },
        "DS": {
            "available_donors": 0,
            "available_donors_ge20": 0,
            "selected_donors": 0,
            "selected_donors_ge20": 0,
            "available_cells": 0,
            "selected_cells": 0,
        },
    }


def support_for_frame(
    available: pd.DataFrame,
    selected: pd.DataFrame,
    *,
    cutoff: int = SUPPORT_CUTOFF,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for cell_type in CELL_TYPE_ORDER:
        counts = empty_class_counts()
        avail_sub = available[available["author_cell_type"] == cell_type]
        sel_sub = selected[selected["author_cell_type"] == cell_type]
        for donor, group in avail_sub.groupby("donor_id", observed=True):
            cls = donor_class(str(donor))
            n = int(len(group))
            counts[cls]["available_donors"] += 1
            counts[cls]["available_cells"] += n
            if n >= cutoff:
                counts[cls]["available_donors_ge20"] += 1
        for donor, group in sel_sub.groupby("donor_id", observed=True):
            cls = donor_class(str(donor))
            n = int(len(group))
            counts[cls]["selected_donors"] += 1
            counts[cls]["selected_cells"] += n
            if n >= cutoff:
                counts[cls]["selected_donors_ge20"] += 1
        out[cell_type] = counts
    return out


def sample_global(obs: pd.DataFrame) -> pd.DataFrame:
    rows = sample_donor_stratified_cells(obs, cap=GLOBAL_CAP, seed=SAMPLING_SEED)
    return obs.iloc[rows]


def sample_targeted(
    obs: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, list[str]], dict[str, str]]:
    selected_ids: dict[str, list[str]] = {}
    hashes: dict[str, str] = {}
    frames: list[pd.DataFrame] = []
    for cell_type in CELL_TYPE_ORDER:
        sub = obs[obs["author_cell_type"] == cell_type]
        if sub.empty:
            raise SamplingFeasibilityError(f"no cells for cell_type={cell_type}")
        rows = sample_donor_stratified_cells(
            sub, cap=TARGETED_CAP, seed=SAMPLING_SEED
        )
        ids = [str(cell_id) for cell_id in sub.index.to_numpy()[rows]]
        selected_ids[cell_type] = ids
        hashes[cell_type] = sha256_text(ids)
        frames.append(sub.iloc[rows])
    return pd.concat(frames), selected_ids, hashes


def verify_label_free(obs: pd.DataFrame) -> dict[str, Any]:
    """Sampler must ignore disease labels: permuting disease cannot change IDs."""
    base_rows = sample_donor_stratified_cells(
        obs, cap=TARGETED_CAP, seed=SAMPLING_SEED
    )
    base_ids = [str(x) for x in obs.index.to_numpy()[base_rows]]
    shuffled = obs.copy()
    # Invert disease strings; sampler must not read this column.
    shuffled["disease"] = shuffled["disease"].map(
        lambda v: "normal" if "trisomy" in v else "complete trisomy 21"
    )
    alt_rows = sample_donor_stratified_cells(
        shuffled, cap=TARGETED_CAP, seed=SAMPLING_SEED
    )
    alt_ids = [str(x) for x in shuffled.index.to_numpy()[alt_rows]]
    return {
        "label_free": base_ids == alt_ids,
        "n_selected": len(base_ids),
        "selected_ids_sha256": sha256_text(base_ids),
    }


def age_sex_library_support(obs: pd.DataFrame) -> dict[str, Any]:
    donor_rows = []
    for donor, group in obs.groupby("donor_id", observed=True):
        ages = sorted(set(group["dev_PCW"].astype(str)))
        sexes = sorted(set(group["sex"].astype(str)))
        libs = sorted(set(group["library"].astype(str)))
        if len(ages) != 1:
            raise SamplingFeasibilityError(
                f"donor {donor} has multiple ages: {ages}"
            )
        if len(sexes) != 1:
            raise SamplingFeasibilityError(
                f"donor {donor} has multiple sexes: {sexes}"
            )
        donor_rows.append(
            {
                "donor_id": str(donor),
                "class": donor_class(str(donor)),
                "dev_PCW": ages[0],
                "sex": sexes[0],
                "n_libraries": len(libs),
                "libraries": libs,
                "n_cells": int(len(group)),
            }
        )
    age_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"CON": 0, "DS": 0})
    sex_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"CON": 0, "DS": 0})
    for row in donor_rows:
        age_counts[row["dev_PCW"]][row["class"]] += 1
        sex_counts[row["sex"]][row["class"]] += 1
    one_class_ages = {
        age: {k: v for k, v in counts.items() if v > 0}
        for age, counts in sorted(age_counts.items(), key=lambda x: float(x[0]))
        if sum(1 for v in counts.values() if v > 0) == 1
    }
    common_ages = sorted(
        age
        for age, counts in age_counts.items()
        if counts["CON"] > 0 and counts["DS"] > 0
    )
    return {
        "donors": donor_rows,
        "age_counts_by_class": {
            age: dict(counts)
            for age, counts in sorted(age_counts.items(), key=lambda x: float(x[0]))
        },
        "one_class_ages": one_class_ages,
        "common_ages_both_classes": common_ages,
        "sex_counts_by_class": {sex: dict(counts) for sex, counts in sex_counts.items()},
        "n_two_library_donors": sum(1 for row in donor_rows if row["n_libraries"] > 1),
    }


def fold_class_support(
    selected: pd.DataFrame,
    cell_type: str,
    *,
    cutoff: int = SUPPORT_CUTOFF,
    n_repeats: int = SPLIT_REPEATS,
    n_folds: int = SPLIT_FOLDS,
    base_seed: int = SPLIT_BASE_SEED,
) -> dict[str, Any]:
    sub = selected[selected["author_cell_type"] == cell_type]
    eligible = []
    for donor, group in sub.groupby("donor_id", observed=True):
        if len(group) < cutoff:
            continue
        eligible.append((str(donor), donor_class(str(donor)), int(len(group))))
    con = sum(1 for _, cls, _ in eligible if cls == "CON")
    ds = sum(1 for _, cls, _ in eligible if cls == "DS")
    result: dict[str, Any] = {
        "cell_type": cell_type,
        "eligible_donors_ge20": {"CON": con, "DS": ds},
        "n_repeats": n_repeats,
        "n_folds": n_folds,
        "split_base_seed": base_seed,
        "split_status": None,
        "donor_overlap_count": None,
        "n_folds_total": None,
        "n_folds_missing_both_classes_train_or_test": None,
        "both_classes_every_fold": None,
        "practical_margin_eligible_donors": None,
        "score_resolution_eligible_donors": None,
        "split_feasible_under_frozen_5x5": False,
    }
    if con < 2 or ds < 2:
        result["split_status"] = "INSUFFICIENT_CLASS_SUPPORT"
        return result
    # Expand to cell rows so train/test cell indices are meaningful; splits use donors.
    donors: list[str] = []
    labels: list[int] = []
    for donor, cls, n_cells in eligible:
        donors.extend([donor] * n_cells)
        labels.extend([1 if cls == "DS" else 0] * n_cells)
    report = build_repeated_group_split_report(
        donors,
        labels,
        n_repeats=n_repeats,
        n_folds=n_folds,
        base_seed=base_seed,
    )
    bad = 0
    for fold in report.folds:
        test_cls = {donor_class(d) for d in fold.test_donors}
        train_cls = {donor_class(d) for d in fold.train_donors}
        if test_cls != {"CON", "DS"} or train_cls != {"CON", "DS"}:
            bad += 1
    margin = practical_margin(con, ds)
    resolution = score_resolution(con, ds)
    result.update(
        {
            "split_status": report.status,
            "donor_overlap_count": report.donor_overlap_count,
            "n_folds_total": len(report.folds),
            "n_folds_missing_both_classes_train_or_test": bad,
            "both_classes_every_fold": bad == 0,
            "practical_margin_eligible_donors": margin,
            "score_resolution_eligible_donors": resolution,
            "split_feasible_under_frozen_5x5": report.status == "PASS" and bad == 0,
        }
    )
    return result


def repaired_types(
    global_support: dict[str, Any],
    targeted_support: dict[str, Any],
) -> list[dict[str, Any]]:
    repaired = []
    for cell_type in CELL_TYPE_ORDER:
        g = global_support[cell_type]
        t = targeted_support[cell_type]
        g_con = g["CON"]["selected_donors_ge20"]
        g_ds = g["DS"]["selected_donors_ge20"]
        t_con = t["CON"]["selected_donors_ge20"]
        t_ds = t["DS"]["selected_donors_ge20"]
        a_con = t["CON"]["available_donors_ge20"]
        a_ds = t["DS"]["available_donors_ge20"]
        lost_global = g_con < a_con or g_ds < a_ds
        restored = t_con == a_con and t_ds == a_ds and (t_con > g_con or t_ds > g_ds)
        if lost_global and restored:
            repaired.append(
                {
                    "cell_type": cell_type,
                    "global_selected_ge20": {"CON": g_con, "DS": g_ds},
                    "targeted_selected_ge20": {"CON": t_con, "DS": t_ds},
                    "available_ge20": {"CON": a_con, "DS": a_ds},
                }
            )
    return repaired


def freeze_eligibility(
    *,
    fold_reports: list[dict[str, Any]],
    repaired: list[dict[str, Any]],
    age_support: dict[str, Any],
) -> dict[str, Any]:
    split_ok = [
        r["cell_type"]
        for r in fold_reports
        if r.get("split_feasible_under_frozen_5x5") is True
    ]
    support_only = [
        r["cell_type"]
        for r in fold_reports
        if r["eligible_donors_ge20"]["CON"] >= 1
        and r["eligible_donors_ge20"]["DS"] >= 1
        and r["cell_type"] not in split_ok
    ]
    insufficient = [
        r["cell_type"]
        for r in fold_reports
        if r["eligible_donors_ge20"]["CON"] < 1 or r["eligible_donors_ge20"]["DS"] < 1
    ]
    return {
        "frozen_before_effect_analysis": True,
        "rules": {
            "sampler": "p22.data.nn_sampling.sample_donor_stratified_cells",
            "sampling_seed": SAMPLING_SEED,
            "global_cap_per_donor": GLOBAL_CAP,
            "targeted_cap_per_donor_per_type": TARGETED_CAP,
            "min_cells_per_donor_support_floor": SUPPORT_CUTOFF,
            "min_cells_note": (
                "Descriptive ≥20 screen is frozen as the type-restricted support "
                "floor for eligibility tables; it is not a biological power gate."
            ),
            "split_protocol": {
                "n_repeats": SPLIT_REPEATS,
                "n_folds": SPLIT_FOLDS,
                "base_seed": SPLIT_BASE_SEED,
                "method": "StratifiedGroupKFold donor-held-out",
                "require_both_classes_every_train_and_test_fold": True,
            },
            "age_covariate_rules": {
                "age_is_not_cell_state_endpoint": True,
                "one_class_ages_excluded_from_age_matched_claims": sorted(
                    age_support["one_class_ages"]
                ),
                "common_ages_both_classes": age_support["common_ages_both_classes"],
                "age_matched_analyses_require_common_age_donors_only": True,
            },
            "sex_covariate_rules": {
                "sex_is_covariate_not_endpoint": True,
                "no_performance_based_donor_deletion": True,
            },
            "author_cell_type_role": (
                "stratification / sampling factor only; not independent cell-state truth "
                "(Q2 ENDPOINT_UNRESOLVED)"
            ),
            "preserve_all_eligible_donors": True,
            "no_outcome_based_type_or_donor_selection": True,
        },
        "candidate_types_split_feasible_under_frozen_5x5": split_ok,
        "candidate_types_with_both_class_support_but_not_5x5_feasible": support_only,
        "types_insufficient_both_class_ge20_selected": insufficient,
        "types_with_measured_support_repair": [r["cell_type"] for r in repaired],
        "biological_cell_state_pilot_eligibility": {
            "status": "BLOCKED",
            "reason": "Q2 ENDPOINT_UNRESOLVED — no independent cell-state endpoint",
        },
        "power_status": "POWER_UNESTABLISHED",
        "uncertainty_note": (
            "practical_margin / score_resolution below are donor-count score-grid "
            "descriptions for a stated donor-balanced-accuracy contrast; they are "
            "not established biological power or CI-width proxies."
        ),
    }


def build_report(
    *,
    h5ad_path: Path,
    global_sampling_path: Path,
    golden_targeted_path: Path,
) -> dict[str, Any]:
    for path, expected in (
        (h5ad_path, EXPECTED_H5AD_SHA256),
        (global_sampling_path, EXPECTED_GLOBAL_SAMPLING_SHA256),
        (golden_targeted_path, EXPECTED_GOLDEN_TARGETED_SHA256),
    ):
        if not path.is_file():
            raise SamplingFeasibilityError(f"missing required input: {path}")
        got = sha256_file(path)
        if got != expected:
            raise SamplingFeasibilityError(
                f"sha256 mismatch for {path}: got {got}, expected {expected}"
            )

    obs = load_obs(h5ad_path)
    global_selected = sample_global(obs)
    targeted_selected, targeted_ids, targeted_hashes = sample_targeted(obs)
    golden = json.loads(golden_targeted_path.read_text())
    golden_ids = golden["selected_cell_ids_by_type"]
    id_mismatches = [
        ct for ct in CELL_TYPE_ORDER if targeted_ids[ct] != golden_ids[ct]
    ]
    if id_mismatches:
        raise SamplingFeasibilityError(
            f"targeted sample IDs differ from golden for: {id_mismatches}"
        )

    global_support = support_for_frame(obs, global_selected)
    targeted_support = support_for_frame(obs, targeted_selected)
    repaired = repaired_types(global_support, targeted_support)
    label_free = verify_label_free(obs)
    if not label_free["label_free"]:
        raise SamplingFeasibilityError("sampler is not label-free under disease permute")

    age_support = age_sex_library_support(obs)
    fold_reports = [
        fold_class_support(targeted_selected, cell_type) for cell_type in CELL_TYPE_ORDER
    ]
    eligibility = freeze_eligibility(
        fold_reports=fold_reports,
        repaired=repaired,
        age_support=age_support,
    )

    support_repair_pass = len(repaired) > 0 and all(
        r["targeted_selected_ge20"]["CON"] == r["available_ge20"]["CON"]
        and r["targeted_selected_ge20"]["DS"] == r["available_ge20"]["DS"]
        for r in repaired
    )
    disposition = "SUPPORT_REPAIR_PASS" if support_repair_pass else "SUPPORT_REPAIR_FAIL"

    return {
        "record_type": "next_stage_sampling_feasibility_q4",
        "date": "2026-09-30",
        "disposition": disposition,
        "eligibility_status": "ELIGIBILITY_FROZEN",
        "inputs": {
            "h5ad": str(h5ad_path),
            "h5ad_sha256": EXPECTED_H5AD_SHA256,
            "global_sampling_record": str(global_sampling_path),
            "global_sampling_sha256": EXPECTED_GLOBAL_SAMPLING_SHA256,
            "golden_targeted_json": str(golden_targeted_path),
            "golden_targeted_sha256": EXPECTED_GOLDEN_TARGETED_SHA256,
        },
        "sampling": {
            "global_cap_per_donor": GLOBAL_CAP,
            "targeted_cap_per_donor_per_type": TARGETED_CAP,
            "seed": SAMPLING_SEED,
            "sampler": "p22.data.nn_sampling.sample_donor_stratified_cells",
            "support_cutoff_cells_per_donor": SUPPORT_CUTOFF,
            "global_n_cells_selected": int(len(global_selected)),
            "targeted_n_cells_selected": int(len(targeted_selected)),
            "targeted_selected_ids_sha256_by_type": targeted_hashes,
            "targeted_all_types_ids_sha256": sha256_text(
                [cell_id for ct in CELL_TYPE_ORDER for cell_id in targeted_ids[ct]]
            ),
            "golden_targeted_ids_exact_match": True,
            "label_free_check": label_free,
        },
        "global_support_by_type": global_support,
        "targeted_support_by_type": targeted_support,
        "measured_support_repair": {
            "decision": (
                "targeted_sampling_repairs_measured_loss_of_support"
                if support_repair_pass
                else "targeted_sampling_does_not_fully_repair_support"
            ),
            "types": repaired,
            "do_not_rerun_full_ladder_merely_with_more_cells": True,
        },
        "age_sex_library_support": {
            "age_counts_by_class": age_support["age_counts_by_class"],
            "one_class_ages": age_support["one_class_ages"],
            "common_ages_both_classes": age_support["common_ages_both_classes"],
            "sex_counts_by_class": age_support["sex_counts_by_class"],
            "n_two_library_donors": age_support["n_two_library_donors"],
            "n_donors": len(age_support["donors"]),
        },
        "fold_class_support_targeted_ge20": fold_reports,
        "eligibility_freeze": eligibility,
        "cohort_uncertainty_full_15_plus_15": {
            "n_control_donors": 15,
            "n_ds_donors": 15,
            "score_resolution": score_resolution(15, 15),
            "practical_margin": practical_margin(15, 15),
            "inference_rule": (
                "donor_balanced_accuracy contrast with donor-bootstrap interval; "
                "advantage requires CI above practical_margin"
            ),
            "power_status": "POWER_UNESTABLISHED",
        },
        "limits": [
            "More cells do not add independent donors.",
            "Support repair does not authorize biological cell-state fits (Q2).",
            "practical_margin is not established biological power.",
            "No disease-effect calculation or model fit was performed.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    repaired = report["measured_support_repair"]["types"]
    elig = report["eligibility_freeze"]
    age = report["age_sex_library_support"]
    lines = [
        "# Q4 — Sampling and age/class support feasibility",
        "",
        f"**Disposition:** `{report['disposition']}`  ",
        f"**Eligibility:** `{report['eligibility_status']}`  ",
        "**Date:** 2026-09-30  ",
        "**Branch:** `gnhf/execute-the-p22-data-146414`  ",
        "**Dependency:** Q1 PASS; Q2 `ENDPOINT_UNRESOLVED` blocks biological cell-state "
        "pilot. No fits, downloads, package installs, or scientific-gate weakening.",
        "",
        "Machine-readable: [sampling_feasibility.json](sampling_feasibility.json).",
        "",
        "## Decision: does targeted sampling repair measured support loss?",
        "",
        f"**Yes — `{report['measured_support_repair']['decision']}`.** "
        "Global per-donor cap underrepresents rare types; targeted "
        f"`cap={TARGETED_CAP}` / `seed={SAMPLING_SEED}` restores selected ≥20-cell "
        "donor support to the available ≥20 counts for:",
        "",
    ]
    for row in repaired:
        lines.append(
            f"- **{row['cell_type']}**: global selected ge20 "
            f"{row['global_selected_ge20']['CON']}/{row['global_selected_ge20']['DS']} "
            f"→ targeted {row['targeted_selected_ge20']['CON']}/"
            f"{row['targeted_selected_ge20']['DS']} "
            f"(available {row['available_ge20']['CON']}/{row['available_ge20']['DS']})"
        )
    lines.extend(
        [
            "",
            "Do **not** rerun the full ladder merely with more cells. Donor count, "
            "not cell count, drives replication.",
            "",
            "## Global vs targeted support (selected donors with ≥20 cells)",
            "",
            "| Type | Global CON/DS | Targeted CON/DS | Available CON/DS |",
            "|---|---:|---:|---:|",
        ]
    )
    for cell_type in CELL_TYPE_ORDER:
        g = report["global_support_by_type"][cell_type]
        t = report["targeted_support_by_type"][cell_type]
        lines.append(
            f"| {cell_type} | "
            f"{g['CON']['selected_donors_ge20']}/{g['DS']['selected_donors_ge20']} | "
            f"{t['CON']['selected_donors_ge20']}/{t['DS']['selected_donors_ge20']} | "
            f"{t['CON']['available_donors_ge20']}/{t['DS']['available_donors_ge20']} |"
        )
    lines.extend(
        [
            "",
            f"Global selected cells: **{report['sampling']['global_n_cells_selected']}** "
            f"(cap {GLOBAL_CAP}/donor). Targeted selected cells: "
            f"**{report['sampling']['targeted_n_cells_selected']}** "
            f"(cap {TARGETED_CAP}/donor/type). Golden targeted IDs: "
            f"**exact match** (SHA-256 by type in JSON).",
            "",
            f"Label-free check (disease permute): "
            f"**{report['sampling']['label_free_check']['label_free']}**.",
            "",
            "## Age / sex / library support",
            "",
            f"- One-class ages (excluded from age-matched claims): "
            f"`{sorted(age['one_class_ages'])}` → "
            f"{age['one_class_ages']}",
            f"- Common ages (both classes): `{age['common_ages_both_classes']}`",
            f"- Sex counts by class: `{age['sex_counts_by_class']}`",
            f"- Two-library donors: **{age['n_two_library_donors']}** / "
            f"{age['n_donors']}",
            "",
            "Age is a **covariate**, not a cell-state endpoint (Q2).",
            "",
            "## Fold class support (targeted, ≥20 cells/donor, frozen 5×5)",
            "",
            "| Type | Eligible CON/DS | Both classes every fold | "
            "practical_margin | Split-feasible |",
            "|---|---:|:---:|---:|:---:|",
        ]
    )
    for row in report["fold_class_support_targeted_ge20"]:
        lines.append(
            f"| {row['cell_type']} | "
            f"{row['eligible_donors_ge20']['CON']}/{row['eligible_donors_ge20']['DS']} | "
            f"{row['both_classes_every_fold']} | "
            f"{row['practical_margin_eligible_donors']} | "
            f"{row['split_feasible_under_frozen_5x5']} |"
        )
    lines.extend(
        [
            "",
            "## Eligibility freeze (before effect analysis)",
            "",
            f"- Split-feasible types under frozen 5×5: "
            f"`{elig['candidate_types_split_feasible_under_frozen_5x5']}`",
            f"- Both-class ≥20 support but not 5×5 both-class every fold: "
            f"`{elig['candidate_types_with_both_class_support_but_not_5x5_feasible']}`",
            f"- Biological cell-state pilot: "
            f"**{elig['biological_cell_state_pilot_eligibility']['status']}** "
            f"({elig['biological_cell_state_pilot_eligibility']['reason']})",
            f"- Power: **`{elig['power_status']}`** — "
            f"{elig['uncertainty_note']}",
            "",
            "Full-cohort 15+15 score-resolution / practical_margin: "
            f"`{report['cohort_uncertainty_full_15_plus_15']['score_resolution']}` / "
            f"`{report['cohort_uncertainty_full_15_plus_15']['practical_margin']}` "
            "under donor-balanced-accuracy + donor-bootstrap inference "
            "(descriptive grid only).",
            "",
            "## What this does and does not authorize",
            "",
            "| Allowed next | Not authorized |",
            "|---|---|",
            "| Continue Q5 read-only external feasibility | Biological cell-state fit |",
            "| Use frozen eligibility in Q6 ranking | Full-ladder rerun for more cells only |",
            "| Synthetic controls that do not need a state endpoint | "
            "Calling CI width or planted amplitude established power |",
            "",
            "## Verification commands",
            "",
            "```bash",
            'export PYTHONPATH="$(pwd)/src"',
            "/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python "
            '-c "import p22; print(p22.__file__)"',
            "/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python "
            "scripts/report_next_stage_sampling_feasibility.py",
            "/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest "
            "tests/test_next_stage_sampling_feasibility_q4.py tests/test_nn_sampling.py -q",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5ad", type=Path, default=DEFAULT_H5AD)
    parser.add_argument(
        "--global-sampling", type=Path, default=DEFAULT_GLOBAL_SAMPLING
    )
    parser.add_argument(
        "--golden-targeted", type=Path, default=DEFAULT_GOLDEN_TARGETED
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)

    report = build_report(
        h5ad_path=args.h5ad,
        global_sampling_path=args.global_sampling,
        golden_targeted_path=args.golden_targeted,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "sampling_feasibility.json"
    md_path = args.out_dir / "SAMPLING_FEASIBILITY.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    md_path.write_text(render_markdown(report))
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(f"disposition={report['disposition']} eligibility={report['eligibility_status']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SamplingFeasibilityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
