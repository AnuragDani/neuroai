"""Public paired-file diagnostics. No training, QC invention, or approval changes."""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd


def parse_geo_libraries(soft_text: str) -> pd.DataFrame:
    """Read GSE305146's explicit sample characteristics, never infer donors from titles."""
    samples = []
    current = None
    for line in soft_text.splitlines():
        if line.startswith("^"):
            current = None
            if line.startswith("^SAMPLE = "):
                current = {"accession": line.split(" = ", 1)[1]}
                samples.append(current)
        elif current is not None and line.startswith("!Sample_title = "):
            current["title"] = line.split(" = ", 1)[1]
        elif current is not None and line.startswith("!Sample_characteristics_ch1 = "):
            key, value = line.split(" = ", 1)[1].split(": ", 1)
            if key in current and current[key] != value:
                raise ValueError(f"conflicting GEO characteristic: {key}")
            current[key] = value
    libraries = {}
    for sample in samples:
        match = re.search(r"Library ([^ ,]+)_(atac|gex)(?:,|$)", sample.get("title", ""))
        if match is None:
            raise ValueError("unrecognized GEO library title")
        library, assay = match.groups()
        required = ("name", "group", "dev stage_pcw", "in final_analysis")
        if any(not sample.get(key, "").strip() for key in required):
            raise ValueError("missing GEO donor or retention characteristic")
        if sample["in final_analysis"] not in ("TRUE", "FALSE"):
            raise ValueError("unknown GEO final-analysis flag")
        row = {
            "library_id": library,
            "donor_id": sample["name"],
            "condition": sample["group"],
            "age_raw": float(sample["dev stage_pcw"]),
            "in_final_analysis": sample["in final_analysis"] == "TRUE",
        }
        old = libraries.setdefault(library, row.copy())
        if any(old[key] != value for key, value in row.items()):
            raise ValueError(f"GEO assays disagree for library {library}")
        key = f"{assay}_accession"
        if key in old:
            raise ValueError(f"duplicate GEO assay for library {library}")
        old[key] = sample["accession"]
    if not libraries or any(
        not {"gex_accession", "atac_accession"}.issubset(row) for row in libraries.values()
    ):
        raise ValueError("each GEO library needs both RNA and ATAC sample records")
    result = pd.DataFrame(libraries.values()).sort_values("library_id").reset_index(drop=True)
    if result.groupby("donor_id").condition.nunique().gt(1).any():
        raise ValueError("GEO donor labels disagree across libraries")
    return result


def normalize_metadata(
    frame: pd.DataFrame,
    *,
    condition_map: dict[str, int],
    age_unit: str = "unknown",
    age_source: str = "",
) -> pd.DataFrame:
    """Validate library-qualified identities and preserve documented age provenance."""
    result = frame.copy().reset_index(drop=True)
    if result.empty:
        raise ValueError("metadata is empty")
    for column in ("donor_id", "library_id", "barcode", "condition"):
        if column not in result or result[column].isna().any():
            raise ValueError(f"missing metadata identity: {column}")
        result[column] = result[column].astype(str)
        if result[column].str.strip().eq("").any():
            raise ValueError(f"empty metadata identity: {column}")
    if result.duplicated(["library_id", "barcode"]).any():
        raise ValueError("duplicate library/barcode keys")
    if not condition_map or any(value not in (0, 1) for value in condition_map.values()):
        raise ValueError("condition_map must explicitly map source labels to 0 or 1")
    result["label"] = result.condition.map(condition_map)
    if result.label.isna().any():
        raise ValueError("unknown condition label")
    result["label"] = result.label.astype(int)
    if result.groupby("donor_id").label.nunique().gt(1).any():
        raise ValueError("conflicting condition labels for a donor")
    result["cell_id"] = [
        json.dumps([library, barcode], separators=(",", ":"))
        for library, barcode in zip(result.library_id, result.barcode, strict=True)
    ]
    if "age_raw" not in result:
        result["age_raw"] = np.nan
    age = pd.to_numeric(result.age_raw, errors="coerce")
    valid = np.isfinite(age) & age.gt(0)
    documented = bool(age_source.strip())
    result["age_unit"] = age_unit
    result["age_source"] = age_source
    result["age_conversion"] = "unresolved"
    result["age_pcw"] = np.nan
    if documented and age_unit in ("PCW", "obstetric_GW"):
        converted = age - (2 if age_unit == "obstetric_GW" else 0)
        valid &= converted.gt(0)
        result.loc[valid, "age_pcw"] = converted[valid]
        result.loc[valid, "age_conversion"] = (
            "GW_minus_2_approximate" if age_unit == "obstetric_GW" else "identity_PCW"
        )
    if result.groupby("donor_id").age_pcw.nunique().gt(1).any():
        raise ValueError("conflicting developmental ages for a donor")
    return result


def age_overlap_summary(frame: pd.DataFrame, low: float = 13, high: float = 20) -> dict:
    """Count donors with documented ages inside inclusive canonical-PCW bounds."""
    if not np.isfinite([low, high]).all() or low > high:
        raise ValueError("invalid age range")
    donors = frame.groupby("donor_id").agg(label=("label", "first"), age=("age_pcw", "first"))
    kept = donors.loc[donors.age.between(low, high)]
    counts = {str(label): int(kept.label.eq(label).sum()) for label in (0, 1)}
    return {
        "status": "SUPPORTED" if all(counts.values()) else "NOT_APPLICABLE",
        "age_pcw_range": [low, high],
        "donors_per_class": counts,
        "unknown_age_donors": int(donors.age.isna().sum()),
        "excluded_donors": int(len(donors) - len(kept)),
        "support_is_not_power": True,
    }


def metadata_report(frame: pd.DataFrame, *, published_cells: int, expected_donors: int) -> dict:
    """Separate observed metadata counts from published and unverified retained counts."""
    if published_cells < 1 or expected_donors < 1:
        raise ValueError("published counts must be positive")
    donors = frame.drop_duplicates("donor_id")
    difference = len(frame) - published_cells
    return {
        "metadata_cells": len(frame),
        "published_cells": published_cells,
        "count_difference": difference,
        "retained_cells": None,
        "release_qc_status": "UNRESOLVED" if difference else "COUNT_MATCH_ONLY",
        "n_donors": len(donors),
        "expected_donors": expected_donors,
        "donor_count_matches": len(donors) == expected_donors,
        "donors_per_class": {str(v): int(donors.label.eq(v).sum()) for v in (0, 1)},
        "cells_per_class": {str(v): int(frame.label.eq(v).sum()) for v in (0, 1)},
        "n_libraries": int(frame.library_id.nunique()),
        "age_overlap": age_overlap_summary(frame),
        "specimen_independence": "UNRESOLVED",
        "confirmatory_ready": False,
    }
