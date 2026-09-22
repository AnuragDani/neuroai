"""Evidence-bound acceptance gate for the real paired development entry points.

A real-data run may not promote itself to a scientific claim. Every real entry
point assembles one evidence bundle from the artifacts it actually consumed and
passes it through :func:`evaluate_input_acceptance` together with a prospective
requirements record and (once the corrected matrices exist) a measured artifact
manifest. Only an ``ACCEPTED`` decision may set ``scientific_claim_allowed`` or
``final_internal_estimate``.

This gate verifies that the declared representation, count unit, ordered cell and
region identities, per-fold donor provenance and protocol settings match the
executable configuration. It is a structural acceptance check, not scientific
approval, and it never replaces external validation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ACCEPTED = "ACCEPTED"
REFUSED = "REFUSED"
MISSING = "MISSING"
ALLOWED_STATUSES = (ACCEPTED, REFUSED, MISSING)

REQUIRED_RNA_MATRIX_KEY = "raw/X"
REQUIRED_RNA_AXIS_KEY = "raw/var"
REQUIRED_ATAC_COUNT_UNIT = "unique_fragment_overlap"
REQUIRED_GENOME_BUILD = "GRCh38"
REQUIRED_FAMILIES = (
    "rna_only",
    "atac_only",
    "rna_atac_concat",
    "gated_fusion",
    "token_concat",
    "cross_attention",
)
REQUIRED_AGGREGATION = "mean_predicted_probability"
REQUIRED_UNCERTAINTY_METHOD = "donor_cluster_percentile_bootstrap"


class AcceptanceError(ValueError):
    """Raised when an acceptance record is structurally invalid."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


def sha256_text(items) -> str:
    """Return the SHA-256 of newline-joined identifiers (the axis fingerprint)."""
    return hashlib.sha256("\n".join(str(item) for item in items).encode()).hexdigest()


def _load_json(path: str | Path, kind: str) -> dict[str, Any]:
    path = Path(path)
    _require(path.is_file(), f"{kind} record {path} is absent")
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise AcceptanceError(f"{kind} record {path} is not valid JSON: {error}") from error
    _require(isinstance(value, dict), f"{kind} record {path} must be a JSON object")
    return value


def load_requirements(path: str | Path) -> dict[str, Any]:
    """Load and structurally validate the prospective acceptance requirements."""
    value = _load_json(path, "requirements")
    _require(
        value.get("record_type") == "real_paired_acceptance_requirements",
        "wrong requirements record_type",
    )
    status = value.get("status")
    _require(
        isinstance(status, str) and status.startswith("PROSPECTIVE"),
        "requirements must be declared prospectively before the corrected run",
    )
    for section in ("rna", "atac", "regions", "population", "protocol"):
        _require(isinstance(value.get(section), dict), f"requirements section {section!r} missing")
    return value


def load_manifest(path: str | Path | None) -> dict[str, Any] | None:
    """Load the measured artifact manifest, or ``None`` when none is supplied."""
    if path is None:
        return None
    value = _load_json(path, "manifest")
    _require(
        value.get("record_type") == "real_paired_input_manifest",
        "wrong manifest record_type",
    )
    for section in ("rna", "atac", "region_sets"):
        _require(isinstance(value.get(section), dict), f"manifest section {section!r} missing")
    return value


def _result(name: str, ok: bool, detail: str) -> dict[str, str]:
    del name
    return {"status": "PASS" if ok else "FAIL", "detail": detail}


def evaluate_input_acceptance(
    requirements: dict[str, Any],
    manifest: dict[str, Any] | None,
    evidence: dict[str, Any],
    *,
    n_folds_run: int = 0,
    expected_n_folds: int | None = None,
) -> AcceptanceDecision:
    """Return one shared acceptance decision for a real-data run.

    Every check is evaluated; a single failure refuses the scientific claim while
    the passing/failing detail is preserved for the run record.
    """
    checks: dict[str, dict[str, str]] = {}
    rna_req = requirements["rna"]
    atac_req = requirements["atac"]
    regions_req = requirements["regions"]
    population_req = requirements["population"]
    protocol_req = requirements["protocol"]

    rna = evidence.get("rna", {})
    atac = evidence.get("atac", {})
    regions = evidence.get("region_sets", {})
    population = evidence.get("population", {})
    protocol = evidence.get("protocol", {})
    folds = evidence.get("folds", [])

    checks["rna_representation"] = _result(
        "rna_representation",
        rna.get("matrix_key") == rna_req["matrix_key"]
        and rna.get("axis_key") == rna_req["axis_key"]
        and bool(rna.get("integer_counts_validated")) == bool(rna_req["require_integer_counts"])
        and rna.get("genome_build", REQUIRED_GENOME_BUILD) == rna_req["genome_build"],
        f"matrix_key={rna.get('matrix_key')!r} axis_key={rna.get('axis_key')!r} "
        f"integer_counts_validated={rna.get('integer_counts_validated')!r}",
    )
    checks["atac_unit"] = _result(
        "atac_unit",
        atac.get("count_unit") == atac_req["count_unit"]
        and atac.get("count_mode") == atac_req["count_mode"]
        and atac.get("unknown_policy") == atac_req["unknown_policy"],
        f"count_unit={atac.get('count_unit')!r} count_mode={atac.get('count_mode')!r} "
        f"unknown_policy={atac.get('unknown_policy')!r}",
    )
    checks["region_identity"] = _result(
        "region_identity",
        regions.get("union_sha256") == regions_req["union_sha256"]
        and regions.get("n_union_regions") == regions_req["n_union_regions"]
        and bool(regions.get("selection_uses_labels")) == bool(regions_req["selection_uses_labels"])
        and bool(regions.get("union_decodes_from_regions_file")),
        f"union_sha256={str(regions.get('union_sha256'))[:12]}... "
        f"n_union_regions={regions.get('n_union_regions')!r}",
    )
    checks["population"] = _result(
        "population",
        population.get("n_donors") == population_req["n_donors"]
        and population.get("n_control") == population_req["n_control"]
        and population.get("n_positive") == population_req["n_positive"]
        and population.get("label_rule") == population_req["label_rule"],
        f"n_donors={population.get('n_donors')!r} "
        f"{population.get('n_control')!r}/{population.get('n_positive')!r}",
    )
    checks["protocol_match"] = _result(
        "protocol_match",
        tuple(protocol.get("families", ())) == tuple(protocol_req["families"])
        and protocol.get("donor_aggregation") == protocol_req["donor_aggregation"]
        and protocol.get("donor_threshold") == protocol_req["donor_threshold"]
        and protocol.get("practical_margin") == protocol_req["practical_margin"]
        and protocol.get("uncertainty_method") == protocol_req["uncertainty_method"]
        and protocol.get("uncertainty_seed") == protocol_req["uncertainty_seed"]
        and protocol.get("n_repeats") == protocol_req["n_repeats"]
        and protocol.get("n_folds") == protocol_req["n_folds"]
        and protocol.get("split_seed") == protocol_req["split_seed"],
        f"families={len(protocol.get('families', ()))} margin={protocol.get('practical_margin')!r} "
        f"seeds(repeat/fold/split)="
        f"{protocol.get('n_repeats')!r}/{protocol.get('n_folds')!r}/{protocol.get('split_seed')!r}",
    )
    checks["fold_provenance"] = _fold_provenance_check(
        folds, regions_req.get("top_n"), expected_n_folds
    )
    checks["inner_validation"] = _inner_validation_check(
        folds, protocol_req.get("inner_validation")
    )

    # Artifact checks require the measured manifest; without it there is nothing to
    # bind the consumed arrays to and the run stays exploratory.
    if manifest is None:
        checks["manifest_present"] = _result(
            "manifest_present", False, "no measured artifact manifest was supplied"
        )
        for name in ("rna_artifact", "cell_identity", "atac_artifact"):
            checks[name] = _result(name, False, "not evaluable without a manifest")
    else:
        checks["manifest_present"] = _result("manifest_present", True, "manifest supplied")
        man_rna = manifest["rna"]
        man_atac = manifest["atac"]
        checks["rna_artifact"] = _result(
            "rna_artifact",
            rna.get("h5ad_sha256") == man_rna.get("h5ad_sha256")
            and rna.get("n_cells") == man_rna.get("n_cells")
            and rna.get("n_genes") == man_rna.get("n_genes")
            and rna.get("gene_axis_sha256") == man_rna.get("gene_axis_sha256"),
            f"h5ad_sha256={str(rna.get('h5ad_sha256'))[:12]}... "
            f"n_cells={rna.get('n_cells')!r} n_genes={rna.get('n_genes')!r}",
        )
        checks["atac_artifact"] = _result(
            "atac_artifact",
            atac.get("matrix_sha256") == man_atac.get("matrix_sha256")
            and atac.get("n_regions") == man_atac.get("n_regions")
            and atac.get("n_cells") == man_atac.get("n_cells")
            and atac.get("regions_file_sha256") == man_atac.get("regions_file_sha256"),
            f"matrix_sha256={str(atac.get('matrix_sha256'))[:12]}... "
            f"n_regions={atac.get('n_regions')!r}",
        )
        checks["cell_identity"] = _result(
            "cell_identity",
            rna.get("ordered_cells_sha256")
            == atac.get("cells_sha256")
            == man_rna.get("cells_sha256")
            == man_atac.get("cells_sha256"),
            "ordered h5ad cells and ATAC matrix columns must agree",
        )

    blocking = tuple(
        name for name, value in checks.items() if value["status"] == "FAIL"
    )
    status = ACCEPTED if not blocking else REFUSED
    expected = expected_n_folds
    complete = n_folds_run > 0 and (expected is None or n_folds_run == expected)
    return AcceptanceDecision(
        status=status,
        scientific_claim_allowed=status == ACCEPTED,
        final_internal_estimate=status == ACCEPTED and complete,
        checks=checks,
        blocking=blocking,
        requirements_sha256=sha256_text(
            [json.dumps(requirements, sort_keys=True)]
        ),
        manifest_sha256=(
            sha256_text([json.dumps(manifest, sort_keys=True)]) if manifest is not None else None
        ),
    )


def _fold_provenance_check(
    folds: list[dict[str, Any]], top_n: Any, expected_n_folds: int | None
) -> dict[str, str]:
    problems = []
    if expected_n_folds is not None and len(folds) != expected_n_folds:
        problems.append(f"expected {expected_n_folds} folds, found {len(folds)}")
    for entry in folds:
        train = sorted(str(value) for value in entry.get("train_donors", ()))
        test = sorted(str(value) for value in entry.get("test_donors", ()))
        region_train = sorted(str(value) for value in entry.get("region_set_train_donors", ()))
        region_test = sorted(str(value) for value in entry.get("region_set_test_donors", ()))
        label = f"{entry.get('repeat')}.{entry.get('fold')}"
        if set(train) & set(test):
            problems.append(f"{label}: train/test donors overlap")
        if region_train != train or region_test != test:
            problems.append(f"{label}: region-set donors do not match the fold split")
        if top_n is not None and entry.get("n_regions") != top_n:
            problems.append(f"{label}: expected {top_n} regions, found {entry.get('n_regions')}")
    detail = (
        "all folds training-only and donor-matched"
        if not problems
        else "; ".join(problems[:4])
    )
    return _result("fold_provenance", not problems, detail)


def _inner_validation_check(
    folds: list[dict[str, Any]], requirement: Any
) -> dict[str, str]:
    """Assert nested-validation provenance for every outer fold.

    The outer check confirms the held-out test donors never entered feature
    discovery. This check additionally confirms that each fold's inner validation
    donors (used for early stopping / model selection) come only from that fold's
    training pool and are disjoint from the held-out test donors, so an outer-only
    check is not misdescribed as a complete nested-validation proof.
    """
    if not isinstance(requirement, dict):
        return _result(
            "inner_validation",
            False,
            "requirements do not declare inner-validation provenance",
        )
    want_split = requirement.get("selection_split")
    want_unit = requirement.get("selection_unit")
    problems = []
    for entry in folds:
        label = f"{entry.get('repeat')}.{entry.get('fold')}"
        train = {str(value) for value in entry.get("train_donors", ())}
        test = {str(value) for value in entry.get("test_donors", ())}
        val = [str(value) for value in entry.get("val_donors", ())]
        val_set = set(val)
        if entry.get("selection_split") != want_split:
            problems.append(
                f"{label}: selection_split={entry.get('selection_split')!r} "
                f"expected {want_split!r}"
            )
        if entry.get("selection_unit") != want_unit:
            problems.append(
                f"{label}: selection_unit={entry.get('selection_unit')!r} "
                f"expected {want_unit!r}"
            )
        if not val_set:
            problems.append(f"{label}: inner validation donors are absent")
        if val_set - train:
            problems.append(f"{label}: inner validation donors are not training donors")
        if val_set & test:
            problems.append(f"{label}: inner validation donors overlap held-out test donors")
    detail = (
        "all folds inner validation training-only and test-disjoint"
        if not problems
        else "; ".join(problems[:4])
    )
    return _result("inner_validation", not problems, detail)


@dataclass(frozen=True)
class AcceptanceDecision:
    """One shared acceptance outcome with per-check evidence."""

    status: str
    scientific_claim_allowed: bool
    final_internal_estimate: bool
    checks: dict[str, dict[str, str]]
    blocking: tuple[str, ...]
    requirements_sha256: str
    manifest_sha256: str | None

    def __post_init__(self) -> None:
        if self.status not in ALLOWED_STATUSES:
            raise AcceptanceError(f"unknown acceptance status {self.status!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "scientific_claim_allowed": self.scientific_claim_allowed,
            "final_internal_estimate": self.final_internal_estimate,
            "blocking_checks": list(self.blocking),
            "checks": dict(self.checks),
            "requirements_sha256": self.requirements_sha256,
            "manifest_sha256": self.manifest_sha256,
        }


def build_evidence(
    *,
    fingerprints: dict[str, Any],
    region_sets: dict[str, Any],
    folds: list[Any],
    protocol_evidence: dict[str, Any],
    population: dict[str, Any],
    atac_sidecar: dict[str, Any],
    regions_file: str | Path,
    inner_validation: dict[Any, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Assemble the evidence bundle consumed by :func:`evaluate_input_acceptance`.

    ``folds`` are the actual executable donor partitions; ``region_sets`` is the
    frozen per-fold region record whose entries carry their own train/test donor
    lists, so feature-discovery provenance is checked against the real split.
    ``protocol_evidence`` and ``population`` are built by the caller from the
    executable protocol and the consumed metadata. ``inner_validation`` maps a
    ``(repeat, fold)`` key to that fold's inner-validation donor record (the donors
    used for early stopping / model selection), so nested-validation provenance is
    bound to the same executable split.
    """
    rna = fingerprints["rna_representation"]
    atac_fp = fingerprints["atac_matrix"]
    inner_by_key = {
        (int(key[0]), int(key[1])): value for key, value in (inner_validation or {}).items()
    }
    region_by_key = {
        (int(entry["repeat"]), int(entry["fold"])): entry for entry in region_sets["per_fold"]
    }
    fold_evidence = []
    for fold in folds:
        entry = region_by_key.get((int(fold.repeat), int(fold.fold)), {})
        inner = inner_by_key.get((int(fold.repeat), int(fold.fold)), {})
        fold_evidence.append(
            {
                "repeat": int(fold.repeat),
                "fold": int(fold.fold),
                "train_donors": list(fold.train_donors),
                "test_donors": list(fold.test_donors),
                "region_set_train_donors": list(entry.get("train_donors", ())),
                "region_set_test_donors": list(entry.get("test_donors", ())),
                "n_regions": len(entry.get("regions", ())),
                "val_donors": list(inner.get("val_donors", ())),
                "selection_split": inner.get("selection_split"),
                "selection_unit": inner.get("selection_unit"),
            }
        )
    regions_file = Path(regions_file)
    regions_sha = hashlib.sha256(regions_file.read_bytes()).hexdigest()
    decoded = []
    for line in regions_file.read_text().splitlines():
        fields = line.split()
        if len(fields) >= 3:
            decoded.append(f"{fields[0]}:{fields[1]}-{fields[2]}")
    return {
        "rna": {
            "matrix_key": rna["matrix_key"],
            "axis_key": rna["axis_key"],
            "genome_build": fingerprints.get("genome_build", REQUIRED_GENOME_BUILD),
            "n_cells": rna["n_cells"],
            "n_genes": rna["n_genes"],
            "gene_axis_sha256": rna["gene_axis_sha256"],
            "integer_counts_validated": rna["integer_counts_validated"],
            "h5ad_sha256": fingerprints["h5ad"]["sha256"],
            "ordered_cells_sha256": fingerprints["ordered_cells_sha256"],
        },
        "atac": {
            "matrix_sha256": atac_fp["sha256"],
            "count_mode": atac_sidecar.get("count_mode"),
            "count_unit": atac_sidecar.get("count_unit"),
            "unknown_policy": atac_sidecar.get("unknown_policy"),
            "n_regions": atac_fp["n_regions"],
            "n_cells": atac_sidecar.get("n_cells"),
            "cells_sha256": atac_sidecar.get("cells_sha256"),
            "regions_file_sha256": regions_sha,
        },
        "region_sets": {
            "union_sha256": region_sets["union_sha256"],
            "n_union_regions": region_sets["n_union_regions"],
            "selection_uses_labels": bool(region_sets.get("selection_uses_labels", False)),
            "top_n": region_sets.get("top_n"),
            "union_decodes_from_regions_file": decoded == list(region_sets["union_regions"]),
        },
        "population": dict(population),
        "folds": fold_evidence,
        "protocol": dict(protocol_evidence),
    }
