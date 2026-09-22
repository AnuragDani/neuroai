"""Shared reader for the P22 ATAC representation sensitivity and cell-state feasibility.

The canonical notebook must expose the prespecified ATAC tie-break sensitivity,
the missing simple linear controls and the model-free cell-state feasibility
assessment without rerunning any acquisition or model fit. This module reads the
tracked evidence records when they are present in the checkout and always returns
the declared sensitivity contract, so a safe-mode or standalone run can still
display what the sensitivity requires. It never trains, never reaches the network
and never promotes a claim: a missing record is reported as absent rather than
silently replaced by another result.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TIEBREAK_RECORD_RELATIVE = "docs/atac_tiebreak_measured_and_comparison_2026-09-21.json"
SENSITIVITY_RECORD_RELATIVE = "docs/atac_tiebreak_sensitivity_2026-09-21.json"
CELLSTATE_RECORD_RELATIVE = "docs/cellstate_feasibility_2026-09-21.json"
CELLSTATE_NEXT_STUDY_RELATIVE = "docs/cellstate_next_study_2026-09-21.json"
PROTOCOL_AMENDMENT_RELATIVE = "configs/atac_tiebreak_sensitivity_2026-09-21.json"

TIEBREAK_RESULT_PRESENT = "TIEBREAK_RESULT_PRESENT"
TIEBREAK_ARTIFACT_ABSENT = "TIEBREAK_ARTIFACT_ABSENT"

# Declared defaults; overridden by the amendment record when it is present.
DECLARED_SENSITIVITY: dict[str, Any] = {
    "question": (
        "does the corrected internal null persist when the arbitrary chromosome-name "
        "lexicographic tie-break inside training-library prevalence ties is removed, and "
        "does the available paired information support a cell-state-focused next study?"
    ),
    "salt": "p22-atac-tiebreak-v1",
    "ranking": (
        "top-256 exact intervals by training-library prevalence; ties broken by "
        "sha256(salt + '\\n' + region), then region"
    ),
    "historical_ranking": (
        "top-256 exact intervals by training-library prevalence; ties broken by "
        "(chromosome, start, end)"
    ),
    "region_budget": 256,
    "primary_contrast": "cross_attention minus token_concat donor balanced accuracy",
    "practical_margin": 0.07,
    "sampling_seed": 22,
    "cell_cap": 256,
    "feature_budget": 128,
    "n_repeats": 5,
    "n_folds": 5,
}


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _primary(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    container = record.get("run") if isinstance(record.get("run"), dict) else record
    primary = container.get("primary_comparison")
    if isinstance(primary, dict):
        return primary
    comparison = record.get("tiebreak_comparison")
    if isinstance(comparison, dict):
        return comparison.get("primary")
    return None


def _result_summary(primary: dict[str, Any] | None) -> dict[str, Any] | None:
    if primary is None:
        return None
    return {
        "estimate": primary.get("estimate"),
        "interval": primary.get("interval"),
        "practical_margin": primary.get("practical_margin"),
        "advantage_demonstrated": primary.get("advantage_demonstrated"),
        "n_donors": primary.get("n_donors"),
        "n_repeats": len(primary.get("per_repeat_delta") or {}) or None,
    }


def _chrom1_range(per_fold: Any) -> dict[str, int] | None:
    if not isinstance(per_fold, list) or not per_fold:
        return None
    historical = [
        (fold.get("chrom_historical") or {}).get("chr1", 0)
        for fold in per_fold
        if isinstance(fold, dict)
    ]
    sha256 = [
        (fold.get("chrom_sha256") or {}).get("chr1", 0)
        for fold in per_fold
        if isinstance(fold, dict)
    ]
    if not historical or not sha256:
        return None
    return {
        "historical_min": min(historical),
        "historical_max": max(historical),
        "sha256_min": min(sha256),
        "sha256_max": max(sha256),
    }


def _representation(record: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(record, dict):
        return {}
    historical = record.get("historical_representation") or {}
    sha256 = record.get("sha256_representation") or {}
    return {
        "historical": {
            "n_union_regions": historical.get("n_union_regions"),
            "union_semantic_sha256": historical.get("union_semantic_sha256"),
            "union_bed_sha256": historical.get("union_bed_sha256"),
            "selection_rule": historical.get("selection_rule"),
        },
        "sha256": {
            "n_union_regions": sha256.get("n_union_regions"),
            "count_unit": sha256.get("count_unit"),
            "union_semantic_sha256": sha256.get("union_semantic_sha256"),
            "union_bed_sha256": sha256.get("union_bed_sha256"),
        },
        "per_fold_chrom1": _chrom1_range((record.get("diagnostics") or {}).get("per_fold")),
    }


def _five_seed(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    block = record.get("tiebreak_five_seed_sensitivity") or {}
    per_seed = ((block.get("primary_estimand") or {}).get("per_seed")) or {}
    if not per_seed:
        return None
    estimates = {
        str(seed): {
            "estimate": value.get("estimate"),
            "interval": value.get("interval"),
            "advantage_demonstrated": value.get("advantage_demonstrated"),
        }
        for seed, value in sorted(per_seed.items(), key=lambda item: int(item[0]))
        if isinstance(value, dict)
    }
    values = [item["estimate"] for item in estimates.values() if item["estimate"] is not None]
    return {
        "seeds": block.get("seeds"),
        "estimates": estimates,
        "spread": (max(values) - min(values)) if values else None,
        "any_advantage_demonstrated": any(
            item["advantage_demonstrated"] for item in estimates.values()
        ),
    }


def _linear_controls(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    block = record.get("linear_controls") or {}
    if not block:
        return None
    out: dict[str, Any] = {}
    for condition, payload in block.items():
        if not isinstance(payload, dict):
            continue
        out[condition] = {
            "acceptance_status": payload.get("acceptance_status"),
            "model_means": payload.get("model_means"),
            "secondary_contrasts_vs_token_concat": payload.get(
                "secondary_contrasts_vs_token_concat"
            ),
            "all_converged": payload.get("all_converged"),
            "n_extension_used": payload.get("n_extension_used"),
            "frozen_regularisation": payload.get("frozen_regularisation"),
        }
    return out or None


def _cellstate(
    feasibility: dict[str, Any] | None, next_study: dict[str, Any] | None
) -> dict[str, Any] | None:
    if not isinstance(feasibility, dict):
        return None
    invariance = feasibility.get("donor_invariance") or {}
    panels = feasibility.get("atac_panels") or {}
    program = feasibility.get("program_feature_coverage") or {}
    panel_summary = {}
    for name, payload in panels.items():
        if not isinstance(payload, dict):
            continue
        panel_summary[name] = {
            "n_regions": payload.get("n_regions"),
            "panel_zero_regions": payload.get("panel_zero_regions"),
            "total_nnz": payload.get("total_nnz"),
            "capped_nonzero_regions": payload.get("capped_nonzero_regions"),
            "capped_overlap_sum": payload.get("capped_overlap_sum"),
            "capped_zero_fraction": payload.get("capped_zero_fraction"),
            "chrom_region_counts": payload.get("chrom_region_counts"),
        }
    program_summary = {}
    for name, payload in (program.get("panels") or {}).items():
        if not isinstance(payload, dict):
            continue
        program_summary[name] = {
            "n_regions": payload.get("n_regions"),
            "n_program_genes": len(payload.get("genes") or {}),
            "genes_with_any_overlapping_region": payload.get("genes_with_any_overlapping_region"),
        }
    proposal = feasibility.get("proposal") or {}
    proposal_condition = next(iter(proposal.values()), {}) if proposal else {}
    result: dict[str, Any] = {
        "n_accepted_cells": feasibility.get("n_accepted_cells"),
        "n_capped_cells": feasibility.get("n_capped_cells"),
        "n_donors": feasibility.get("n_donors"),
        "model_fitted": feasibility.get("model_fitted"),
        "outcome_used_for_selection": feasibility.get("outcome_used_for_selection"),
        "donor_invariance": {
            field: {
                "donor_invariant": (payload or {}).get("donor_invariant"),
                "n_varying_donors": (payload or {}).get("n_varying_donors"),
            }
            for field, payload in invariance.items()
            if isinstance(payload, dict)
        },
        "panels": panel_summary,
        "program_coverage": program_summary,
        "proposal_name": (
            proposal_condition.get("name") if isinstance(proposal_condition, dict) else None
        ),
        "claim_boundaries": feasibility.get("claim_boundaries"),
    }
    if isinstance(next_study, dict):
        result["next_study"] = {
            "status": next_study.get("status"),
            "sampling_proposal_name": next_study.get("sampling_proposal_name"),
            "biological_objective": next_study.get("biological_objective"),
            "future_estimand": next_study.get("future_estimand"),
            "support_audit": next_study.get("support_audit"),
            "validation_resources": next_study.get("validation_resources"),
        }
    return result


def summarize_atac_tiebreak_sensitivity(root: str | Path) -> dict[str, Any]:
    """Return the declared sensitivity plus any saved tie-break/cell-state evidence.

    ``root`` is the project root that may contain the configs and docs records. The
    function never raises for missing records: absence is reported through ``status``
    and the ``*_present`` fields.
    """
    root = Path(root)
    amendment = _read_json(root / PROTOCOL_AMENDMENT_RELATIVE)
    sensitivity = _read_json(root / SENSITIVITY_RECORD_RELATIVE)
    tiebreak = _read_json(root / TIEBREAK_RECORD_RELATIVE)
    feasibility = _read_json(root / CELLSTATE_RECORD_RELATIVE)
    next_study = _read_json(root / CELLSTATE_NEXT_STUDY_RELATIVE)

    declared = dict(DECLARED_SENSITIVITY)
    if isinstance(amendment, dict):
        declared["salt"] = amendment.get("salt", declared["salt"])
        declared["ranking"] = amendment.get("ranking", declared["ranking"])
        declared["question"] = amendment.get("question", declared["question"])
        declared["region_budget"] = amendment.get("region_budget", declared["region_budget"])
        declared["primary_contrast"] = amendment.get(
            "primary_contrast", declared["primary_contrast"]
        )

    tiebreak_primary = (tiebreak or {}).get("tiebreak_comparison") or {}
    historical_primary = (tiebreak or {}).get("historical_corrected_reference") or {}
    status = (
        TIEBREAK_RESULT_PRESENT
        if tiebreak is not None
        else TIEBREAK_ARTIFACT_ABSENT
    )
    return {
        "status": status,
        "declared_sensitivity": declared,
        "representation": _representation(sensitivity),
        "comparison": {
            "historical_corrected": {
                "n_union_regions": historical_primary.get("n_union_regions"),
                "union_sha256": historical_primary.get("union_sha256"),
                "acceptance_status": historical_primary.get("acceptance_status"),
                "primary": _result_summary(historical_primary.get("primary")),
            },
            "tiebreak": {
                "acceptance_status": tiebreak_primary.get("acceptance_status"),
                "primary": _result_summary(tiebreak_primary.get("primary")),
                "model_summaries": tiebreak_primary.get("model_summaries"),
            },
        },
        "five_seed": _five_seed(tiebreak),
        "linear_controls": _linear_controls(tiebreak),
        "measurement": (tiebreak or {}).get("measurement"),
        "cellstate": _cellstate(feasibility, next_study),
        "claim_boundaries": (tiebreak or {}).get("claim_boundaries"),
        "paths": {
            "protocol_amendment": PROTOCOL_AMENDMENT_RELATIVE,
            "protocol_amendment_present": amendment is not None,
            "sensitivity_record": SENSITIVITY_RECORD_RELATIVE,
            "sensitivity_record_present": sensitivity is not None,
            "tiebreak_record": TIEBREAK_RECORD_RELATIVE,
            "tiebreak_record_present": tiebreak is not None,
            "cellstate_record": CELLSTATE_RECORD_RELATIVE,
            "cellstate_record_present": feasibility is not None,
            "cellstate_next_study": CELLSTATE_NEXT_STUDY_RELATIVE,
            "cellstate_next_study_present": next_study is not None,
        },
        "note": (
            "The tie-break sensitivity removes only the lexicographic preference inside "
            "training-library prevalence ties; it is an ordering control, not a validated "
            "regulatory panel. The cell-state tables are model-free and descriptive: author "
            "cell-type labels are context, not independent truth. Safe mode displays the "
            "declared sensitivity and the saved records only; no acquisition or model fit "
            "runs here."
        ),
    }
