"""Fail-closed peak-space diagnostics; no approximate interval projection."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence


def audit_peak_spaces(
    peak_sets: dict[str, Sequence[str]],
    *,
    genome_builds: dict[str, str],
    count_units: dict[str, str],
    reference: dict | None = None,
) -> dict:
    """Compare full peak spaces; a common-subset design is a separate frozen choice.

    Overlap is not exact recounting. A missing region is not a biological zero.
    Source: https://stuartlab.org/signac/articles/merging
    """
    if (
        len(peak_sets) < 2
        or set(peak_sets) != set(genome_builds)
        or set(peak_sets) != set(count_units)
    ):
        raise ValueError("at least two peak sets need explicit build and count-unit records")
    canonical = {}
    for name, regions in peak_sets.items():
        parsed = []
        for region in regions:
            match = re.fullmatch(r"([^:\s]+):(\d+)-(\d+)", region)
            if match is None:
                raise ValueError(f"invalid peak interval: {region}")
            chromosome, start, end = match.groups()
            if int(end) <= int(start):
                raise ValueError(f"invalid peak interval: {region}")
            parsed.append((chromosome, int(start), int(end)))
        if not parsed or len(set(parsed)) != len(parsed):
            raise ValueError("empty peak space or duplicate intervals")
        canonical[name] = parsed
    sets = [set(values) for values in canonical.values()]
    union, common = set.union(*sets), set.intersection(*sets)
    identical = all(values == sets[0] for values in sets)
    known_build = all(
        value not in ("", "unknown", "unverified") for value in genome_builds.values()
    )
    same_build = known_build and len(set(genome_builds.values())) == 1
    same_units = len(set(count_units.values())) == 1 and set(count_units.values()) <= {
        "fragments",
        "tn5_insertions",
    }
    reference = reference or {}
    documented_reference = reference.get("kind") in ("fixed_reference", "training_fold") and str(
        reference.get("source", "")
    ).startswith("https://")
    reasons = []
    if not identical:
        reasons.append("full peak union has unmeasured regions; never zero-fill")
    if not same_build:
        reasons.append("genome build is unknown or differs")
    if not same_units:
        reasons.append("count semantics are unknown or differ")
    if not documented_reference:
        reasons.append("fixed-reference/training-fold feature provenance is not established")
    # No values are projected. Even PASS is only feature compatibility, not approval to train.
    status = "PASS" if not reasons else ("NEEDS_RECOUNT" if not identical else "INCONCLUSIVE")
    first = next(iter(canonical.values()))
    return {
        "status": status,
        "scope": "full_peak_union",
        "reasons": reasons,
        "n_regions": {key: len(values) for key, values in canonical.items()},
        "n_exact_common_regions": len(common),
        "unmeasured_regions": {key: len(union - set(values)) for key, values in canonical.items()},
        "row_order_identical": all(values == first for values in canonical.values()),
        "common_regions_sha256": hashlib.sha256(json.dumps(sorted(common)).encode()).hexdigest(),
        "zero_fill_allowed": False,
        "exact_projection_possible": identical and same_build and same_units,
        "alternative": "Assess a frozen, measured common subset before budgeting recount",
        "genome_builds": genome_builds,
        "count_units": count_units,
        "reference": reference,
        "training_approval": "NOT_ASSESSED",
    }
