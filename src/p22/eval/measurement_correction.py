"""Shared reader for the corrected RNA/ATAC measurement record.

The canonical notebook must expose the corrected real workflow without rerunning
the bounded remote ATAC acquisition. This module reads the prospective ATAC
measurement contract, the acceptance requirements and the corrected internal
comparison record when they are present in the checkout, and always returns the
declared contract so a safe-mode or standalone run can still display what the
corrected workflow requires. It never trains, never reaches the network and never
promotes a claim: a missing corrected artifact is reported as absent rather than
silently replaced by the historical result.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CORRECTED_RECORD_RELATIVE = "docs/repeated_internal_comparison_corrected_2026-09-21.json"
HISTORICAL_RECORD_RELATIVE = "docs/repeated_internal_comparison_2026-09-21.json"
CONTRACT_RELATIVE = "configs/atac_measurement_contract_2026-09-21.json"
ACCEPTANCE_RELATIVE = "configs/real_paired_acceptance_2026-09-21.json"
MANIFEST_RELATIVE = "configs/real_paired_input_manifest_2026-09-21.json"

CORRECTED_RESULT_PRESENT = "CORRECTED_RESULT_PRESENT"
CORRECTED_ARTIFACT_ABSENT = "CORRECTED_ARTIFACT_ABSENT"

# Declared defaults; overridden by the contract record when it is present.
DECLARED_CONTRACT: dict[str, Any] = {
    "rna_matrix_key": "raw/X",
    "rna_axis_key": "raw/var",
    "atac_count_unit": "unique_fragment_overlap",
    "count_rule": "one count per unique qualifying fragment record; column five "
    "(supporting read pairs including duplicates) is not summed",
    "interval_rule": "a fragment record qualifies for region [beg, end) when "
    "fragment_start < end and fragment_end > beg; fragment_start >= fragment_end "
    "records are ignored",
    "reader": "scripts/query_fragment_regions.py (bounded HTTP range; BGZF members "
    "concatenated before line splitting; chunk-end virtual offsets enforced)",
    "independent_oracle": "pysam 0.24.1 / HTSlib",
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
    run = record.get("run")
    container = run if isinstance(run, dict) else record
    primary = container.get("primary_comparison")
    return primary if isinstance(primary, dict) else None


def _result_summary(primary: dict[str, Any] | None) -> dict[str, Any] | None:
    if primary is None:
        return None
    return {
        "model": primary.get("model"),
        "reference": primary.get("reference"),
        "metric": primary.get("metric"),
        "estimate": primary.get("estimate"),
        "interval": primary.get("interval"),
        "level": primary.get("level"),
        "practical_margin": primary.get("practical_margin"),
        "advantage_demonstrated": primary.get("advantage_demonstrated"),
        "n_donors": primary.get("n_donors"),
        "n_repeats": primary.get("n_repeats"),
    }


def summarize_measurement_correction(root: str | Path) -> dict[str, Any]:
    """Return the declared corrected contract plus any saved corrected result.

    ``root`` is the project root that may contain the configs and docs records.
    The function never raises for missing records: absence is reported through
    ``status`` and the ``*_path``/``*_present`` fields.
    """
    root = Path(root)
    contract = _read_json(root / CONTRACT_RELATIVE)
    acceptance = _read_json(root / ACCEPTANCE_RELATIVE)
    corrected = _read_json(root / CORRECTED_RECORD_RELATIVE)
    historical = _read_json(root / HISTORICAL_RECORD_RELATIVE)
    manifest = _read_json(root / MANIFEST_RELATIVE)

    declared = dict(DECLARED_CONTRACT)
    if contract:
        declared["atac_count_unit"] = contract.get("count_unit", declared["atac_count_unit"])
        declared["count_rule"] = contract.get("count_rule", declared["count_rule"])
        declared["interval_rule"] = contract.get("interval_rule", declared["interval_rule"])
    if acceptance:
        rna = acceptance.get("rna") or {}
        declared["rna_matrix_key"] = rna.get("matrix_key", declared["rna_matrix_key"])
        declared["rna_axis_key"] = rna.get("axis_key", declared["rna_axis_key"])
        atac = acceptance.get("atac") or {}
        declared["atac_count_unit"] = atac.get("count_unit", declared["atac_count_unit"])
        declared["atac_count_mode"] = atac.get("count_mode")
        declared["unknown_policy"] = atac.get("unknown_policy")

    corrected_primary = _primary(corrected)
    acceptance_decision = None
    if isinstance(corrected, dict):
        run = corrected.get("run") if isinstance(corrected.get("run"), dict) else corrected
        acceptance_decision = run.get("acceptance")

    status = (
        CORRECTED_RESULT_PRESENT
        if corrected_primary is not None
        else CORRECTED_ARTIFACT_ABSENT
    )
    return {
        "status": status,
        "declared_contract": declared,
        "corrected_result": _result_summary(corrected_primary),
        "historical_result": _result_summary(_primary(historical)),
        "acceptance": {
            "status": (acceptance_decision or {}).get("status"),
            "scientific_claim_allowed": (acceptance_decision or {}).get("scientific_claim_allowed"),
            "manifest_present": bool(manifest),
            "blocking_checks": (acceptance_decision or {}).get("blocking_checks"),
        },
        "paths": {
            "contract": CONTRACT_RELATIVE,
            "contract_present": contract is not None,
            "acceptance_requirements": ACCEPTANCE_RELATIVE,
            "acceptance_requirements_present": acceptance is not None,
            "corrected_record": CORRECTED_RECORD_RELATIVE,
            "corrected_record_present": corrected is not None,
            "historical_record": HISTORICAL_RECORD_RELATIVE,
            "historical_record_present": historical is not None,
            "measured_manifest": MANIFEST_RELATIVE,
            "measured_manifest_present": manifest is not None,
        },
        "note": (
            "The corrected internal comparison consumes integer raw/X RNA counts and the "
            "unique_fragment_overlap ATAC unit, and is bound to a measured-artifact manifest "
            "before the shared acceptance gate may set scientific_claim_allowed. Safe mode "
            "displays the declared contract and the saved corrected result only; the bounded "
            "remote ATAC regeneration is a separate authorized step."
        ),
    }
