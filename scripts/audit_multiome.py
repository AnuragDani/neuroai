#!/usr/bin/env python
"""Audit pinned public files locally. Never download, train, or modify approval state."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
from scripts import resolve_nemo_source as source  # noqa: E402

import p22  # noqa: E402
from p22.data.atac_features import audit_peak_spaces  # noqa: E402
from p22.data.multiome import (  # noqa: E402
    ReadBudget,
    load_mex,
    metadata_report,
    nemo_metadata_diagnostics,
    normalize_metadata,
    pair_and_cap,
    parse_geo_libraries,
    read_asset,
    read_features,
)
from p22.data.multiome_retention import (  # noqa: E402
    read_retained_release,
    reconcile_author_libraries,
    retained_mask,
)
from p22.data.resources import measure_stage  # noqa: E402

DEVELOPMENT_OBJECT = "GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz"
DEVELOPMENT_EVIDENCE_PATH = ROOT / "docs/PAIRED_MULTIOME_REMAINING_EVIDENCE_2026-09-08.md"
DEVELOPMENT_EVIDENCE_SHA256 = "66b1d8158f5b6c4260085cddb736db2d59de9df610e5dcac5ccfc2c4f63b18b9"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _unique_object(pairs):
    value = dict(pairs)
    _require(len(value) == len(pairs), "duplicate JSON field")
    return value


def _verified_json(path, expected):
    _require(
        isinstance(expected, str) and re.fullmatch("[a-f0-9]{64}", expected),
        "record needs a reviewed SHA256",
    )
    _require(not path.is_symlink() and path.is_file(), "record must be a regular file")
    _require(path.stat().st_size <= 1024**2, "record exceeds 1 MiB")
    raw = path.read_bytes()
    _require(source.digest(raw) == expected, "record checksum mismatch")
    value = json.loads(raw, object_pairs_hook=_unique_object)
    _require(
        isinstance(value, dict)
        and type(value.get("schema_version")) is int
        and value["schema_version"] == 1,
        "invalid record schema",
    )
    return value


def _number(value, *, positive=False):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and (value > 0 if positive else value >= 0)
    )


def load_feasibility_inputs(source_path, source_hash, development_path, development_hash):
    """Validate explicitly reviewed records. A matching checksum is not scientific acceptance."""
    identity = _verified_json(source_path, source_hash)
    development = _verified_json(development_path, development_hash)
    try:
        _require(identity["record_kind"] == "nemo_source_identity", "wrong source record kind")
        _require(identity["bag_url"] == source.BAG_URL, "source URL mismatch")
        _require(
            identity["expected_bag"] == {"bytes": source.BAG_BYTES, "sha256": source.BAG_SHA256},
            "source bag pin mismatch",
        )
        _require(identity["declared_payload"] == source.TARGET, "target declaration mismatch")
        _require(
            identity["code_sha256"] == source.digest(Path(source.__file__).read_bytes()),
            "source resolver code hash mismatch",
        )
        _require(
            identity["source_evidence"]["sha256"] == source.EVIDENCE_SHA256,
            "source evidence pin mismatch",
        )
        _require(
            source.digest(source.EVIDENCE_PATH.read_bytes()) == source.EVIDENCE_SHA256,
            "local source evidence hash mismatch",
        )
        _require(
            identity["limits"]
            == {
                "body_bytes": source.MAX_BODY,
                "decoded_bytes": source.MAX_DECODED,
                "network_seconds": source.NETWORK_SECONDS,
            },
            "source budget mismatch",
        )
        for name, cap in (("body_bytes", source.MAX_BODY), ("decoded_bytes", source.MAX_DECODED)):
            _require(
                type(identity[name]) is int and 0 <= identity[name] <= cap,
                "invalid observed byte ledger",
            )
        _require(_number(identity["elapsed_seconds"]), "invalid elapsed time")
        datetime.fromisoformat(identity["created_utc"])
        _require(isinstance(identity["command"], list) and identity["command"], "missing command")
        _require(type(identity["request_attempted"]) is bool, "invalid request flag")
        _require(set(identity["headers"]) == set(source.HEADER_NAMES), "missing response headers")
        if not identity["request_attempted"]:
            _require(
                identity["requests"] == []
                and identity["body_bytes"] == 0
                and identity["decoded_bytes"] == 0
                and identity["elapsed_seconds"] == 0
                and all(v is None for v in identity["headers"].values())
                and identity["body_sha256"] is None
                and identity["raw_bag_path"] is None,
                "no-request record has observations",
            )
        else:
            _require(len(identity["requests"]) == 1, "request count mismatch")
            request = identity["requests"][0]
            _require(
                request["method"] == "GET"
                and request["url"] == source.BAG_URL
                and request["body_bytes"] == identity["body_bytes"],
                "request ledger mismatch",
            )
        resolved = identity["stop_reason"] == "RESOLVED"
        if resolved:
            _require(
                identity["request_attempted"]
                and identity["requests"][0]["status"] == 200
                and identity["body_bytes"] == source.BAG_BYTES
                and identity["elapsed_seconds"] <= source.NETWORK_SECONDS,
                "invalid successful source request",
            )
            _require(
                identity["headers"]["Content-Encoding"] in (None, "identity")
                and identity["headers"]["Content-Length"] in (None, str(source.BAG_BYTES)),
                "successful source has invalid headers",
            )
        else:
            _require(
                identity["resolved_payload"] is None and identity["matched_members"] == [],
                "failed source record claims resolved payload",
            )
            _require(
                isinstance(identity["stop_reason"], str) and identity["stop_reason"],
                "missing source stop reason",
            )
        if identity["raw_bag_path"] is not None:
            _require(identity["raw_bag_path"] == "source-bag.tgz", "unexpected raw bag path")
            _require(
                identity["request_attempted"] and identity["body_bytes"] == source.BAG_BYTES,
                "saved bag disagrees with request byte ledger",
            )
            raw_path = source_path.parent / "source-bag.tgz"
            _require(
                not raw_path.is_symlink() and raw_path.stat().st_size == source.BAG_BYTES,
                "invalid saved bag size/type",
            )
            raw = raw_path.read_bytes()
            _require(
                source.digest(raw) == source.BAG_SHA256 == identity["body_sha256"],
                "saved bag hash mismatch",
            )
            replay = {"decoded_bytes": 0}
            try:
                payload = source.validate_bag(raw, replay)
            except (ValueError, tarfile.TarError, source.zlib.error):
                _require(not resolved, "saved bag cannot reproduce resolution")
            else:
                _require(
                    resolved
                    and payload == identity["resolved_payload"]
                    and replay["matched_members"] == identity["matched_members"]
                    and replay["decoded_bytes"] == identity["decoded_bytes"],
                    "saved bag/declaration replay mismatch",
                )
        else:
            _require(not resolved, "successful source missing saved bag")

        _require(
            development["record_kind"] == "development_object_feasibility"
            and development["selected_object"] == DEVELOPMENT_OBJECT,
            "wrong development object",
        )
        _require(
            development["source_evidence"]["sha256"] == DEVELOPMENT_EVIDENCE_SHA256
            and source.digest(DEVELOPMENT_EVIDENCE_PATH.read_bytes())
            == DEVELOPMENT_EVIDENCE_SHA256,
            "development evidence hash mismatch",
        )
        datetime.fromisoformat(development["created_utc"])
        checks = development["checks"]
        _require(
            checks["reader_support"] in ("ABSENT_IN_CHECKED_ENVIRONMENT", "UNTESTED")
            and checks["reader_proof"] is None,
            "reader readiness requires separately verified proof",
        )
        _require(
            type(checks["pyreadr"]) is bool and type(checks["rpy2"]) is bool,
            "invalid reader module checks",
        )
        for name in ("R", "Rscript"):
            _require(
                checks[name] is None or (isinstance(checks[name], str) and checks[name]),
                "invalid reader executable path",
            )
        if checks["reader_support"] == "ABSENT_IN_CHECKED_ENVIRONMENT":
            _require(
                not any(checks[k] for k in ("R", "Rscript", "pyreadr", "rpy2")),
                "absent reader contradicts observations",
            )
        _require(
            isinstance(checks["command"], str) and checks["command"], "missing inventory command"
        )
        resources = development["resources"]
        for name in (
            "disk_free_bytes",
            "host_memory_bytes",
            "available_memory_bytes",
            "compressed_bytes",
            "decoded_bytes",
            "peak_rss_bytes",
            "working_disk_bytes",
        ):
            _require(
                resources[name] is None or (type(resources[name]) is int and resources[name] > 0),
                "unknown resource must be null; known byte quantity must be positive",
            )
        _require(resources["unknown_reason"], "missing resource uncertainty explanation")
        _require(
            resources["listed_compressed_size"] == "7.6G", "publisher size declaration changed"
        )
        _require(
            isinstance(development["inspection_questions"], list)
            and len(development["inspection_questions"]) >= 5,
            "missing inspection questions",
        )
        _require(
            development["scientific_acceptance"] is False
            and development["model_training_performed"] is False,
            "feasibility cannot claim acceptance",
        )
        action = development["next_action"]
        _require(action["id"] == "ENABLE_R_READER_FIXTURE", "next action skips reader prerequisite")
        ceilings = {
            "network_bytes": 2 * 1024**3,
            "decoded_bytes": 4 * 1024**3,
            "working_disk_bytes": 6 * 1024**3,
            "peak_rss_bytes": 4 * 1024**3,
            "wall_seconds": 1800,
            "fixture_input_bytes": 1024**2,
        }
        for key, maximum in ceilings.items():
            _require(
                _number(action["limits"][key], positive=True) and action["limits"][key] <= maximum,
                "next action exceeds reviewed ceiling",
            )
        _require(
            _number(action["limits"]["minimum_free_disk_bytes"], positive=True)
            and action["limits"]["minimum_free_disk_bytes"] >= 10 * 1024**3,
            "next action lacks disk headroom",
        )
        for name in ("description", "runtime", "enforcement", "stop_rule", "authority"):
            _require(
                isinstance(action[name], str) and action[name].strip(), "incomplete next action"
            )
        _require(
            isinstance(action["outputs"], list) and action["outputs"], "missing next-action output"
        )
    except (KeyError, TypeError, IndexError, OSError) as error:
        raise ValueError(f"invalid feasibility evidence: {error}") from error
    return {
        "source": identity,
        "development": development,
        "records": [
            {"path": str(source_path.resolve()), "sha256": source_hash},
            {"path": str(development_path.resolve()), "sha256": development_hash},
        ],
    }


def build_input_decision(report, inputs):
    _require(report["preflight_status"] == "COMPLETED", "failed audit is not an input decision")
    requirements = {
        "release_retained_barcodes": "Full retained-cell barcode mapping for the intended cohort",
        "donor_pairing": "Measured RNA and ATAC paired to the same retained nuclei and donors",
        "qc_count_stage": "Release-specific author QC and count-stage semantics",
        "age_class_support": "Protocol-specific eligible donor/class support after accepted QC",
        "specimen_provenance": "Reviewed specimen provenance and overlap evidence",
        "genome_coordinates": "Accepted genome build and coordinate convention",
        "count_units": "Comparable measured count units",
        "exact_measured_regions": "Common measured ATAC counts without fabricated zeros",
        "feature_selection_provenance": "Fixed-reference or training-only peak selection evidence",
    }
    evidence = inputs["records"] + [{"path": "manifest.json", "sha256": report["manifest_sha256"]}]
    scopes = {
        "development": (
            "Existing one-library retained-cell pilot and two raw peak lists; "
            "processed objects uninspected"
        ),
        "external": "Existing metadata and one release declaration; count payload uninspected",
        "cross_cohort": "No accepted common measurement space across the two cohorts",
    }
    result = {
        group: {
            name: {
                "status": "UNRESOLVED",
                "scope": scope,
                "reason": "Available evidence does not establish this requirement",
                "missing_artifact": missing,
                "evidence": evidence,
            }
            for name, missing in requirements.items()
        }
        for group, scope in scopes.items()
    }
    compatibility = report["atac_compatibility"]
    if compatibility["status"] == "NEEDS_RECOUNT":
        result["development"]["exact_measured_regions"].update(
            status="FAIL",
            reason="Raw peak spaces differ; published processed objects remain uninspected",
        )
    units = set(compatibility["count_units"].values())
    if units <= {"fragments", "tn5_insertions"} and len(units) > 1:
        result["development"]["count_units"].update(
            status="FAIL", reason="Inspected count units differ"
        )
    result["external"]["source_identity"] = {
        "status": "PASS" if inputs["source"]["stop_reason"] == "RESOLVED" else "UNRESOLVED",
        "scope": "Pinned bag declaration only",
        "reason": inputs["source"]["stop_reason"],
        "missing_artifact": None
        if inputs["source"]["stop_reason"] == "RESOLVED"
        else "Validated payload declaration",
        "evidence": [inputs["records"][0]],
    }
    return result | {
        "schema_version": 1,
        "cycle": "F1-F3",
        "outcome": "INCONCLUSIVE",
        "training_allowed": False,
        "model_training_performed": False,
        "m4": compatibility,
        "resources": inputs["development"]["resources"],
        "next_action": inputs["development"]["next_action"],
        "next_action_executed": False,
        "evidence": evidence,
        "limitation": "Code/source feasibility completed; research question remains unresolved.",
    }


def render_input_decision(decision):
    lines = [
        "# Paired-input decision",
        "",
        "Outcome: INCONCLUSIVE. No models trained. Stop after this decision.",
        "",
        f"NeMO source declaration: {decision['external']['source_identity']['reason']}.",
        f"Existing raw-library M4 outcome: {decision['m4']['status']}; scope: full peak union.",
        "Two published development processed objects remain uninspected.",
        "URL recovery and reader inventory do not accept QC, counts or feature provenance.",
        "",
        "| Requirement | Development | External | Cross-cohort |",
        "|---|---|---|---|",
    ]
    for name in decision["development"]:
        lines.append(
            "| "
            + name
            + " | "
            + " | ".join(
                decision[group][name]["status"]
                for group in ("development", "external", "cross_cohort")
            )
            + " |"
        )
    action = decision["next_action"]
    lines += [
        "",
        "## One next action",
        "",
        action["description"],
        "",
        action["runtime"],
        "",
        "Proposed limits: " + json.dumps(action["limits"], sort_keys=True),
        "",
        action["enforcement"],
        "",
        action["stop_rule"],
        "",
        action["authority"],
        "",
        "Full-object memory/disk fit remains unknown. No dataset download follows automatically.",
    ]
    return "\n".join(lines) + "\n"


def audit(manifest: dict, base: Path, budget: ReadBudget, cap: int, max_nnz: int) -> dict:
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported manifest schema_version")

    def local(spec):
        return spec | {"path": str((base / spec["path"]).resolve())}

    geo, external = manifest["geo"], manifest["external"]
    libraries = parse_geo_libraries(read_asset(local(geo["soft"]), budget).decode())
    final = libraries.loc[libraries.in_final_analysis]
    geo_report = {
        "n_libraries": len(libraries),
        "n_donors": int(libraries.donor_id.nunique()),
        "final_flag_libraries": len(final),
        "final_flag_donors": int(final.donor_id.nunique()),
        "published_donors": geo["published_donors"],
        "published_cells": geo["published_cells"],
        "retained_cells": None,
        "library_manifest": libraries.to_dict(orient="records"),
        "retained_cell_barcode_mapping": "PENDING",
    }
    raw_metadata = pd.read_csv(io.BytesIO(read_asset(local(external["metadata"]), budget)))
    raw_metadata = raw_metadata.rename(columns=external["columns"])
    annotation_diagnostics = nemo_metadata_diagnostics(
        raw_metadata, published_cells=external["published_cells"]
    )
    metadata = normalize_metadata(
        raw_metadata,
        condition_map=external["condition_map"],
        age_unit=external["age_unit"],
        age_source=external["age_source"],
    )
    external_report = metadata_report(
        metadata,
        published_cells=external["published_cells"],
        expected_donors=external["published_donors"],
    )
    external_report["paired_matrices_checked"] = False
    external_report["annotation_diagnostics"] = annotation_diagnostics
    block = load_mex(
        {key: local(value) for key, value in geo["combined_mex"].items()}, budget, max_nnz=max_nnz
    )
    selected_library = libraries.loc[libraries.library_id.eq(geo["pilot_library"])]
    if len(selected_library) != 1:
        raise ValueError("pilot library must match exactly one GEO record")
    source_row = selected_library.iloc[0].to_dict()
    pilot_metadata = pd.DataFrame([source_row] * len(block["barcodes"]))
    pilot_metadata["barcode"] = block["barcodes"]
    pilot_metadata = normalize_metadata(
        pilot_metadata,
        condition_map={"CON": 0, "DS": 1},
        age_unit="PCW",
        age_source=geo["soft"]["source_url"] + "#dev-stage-pcw",
    )
    keep, retention = None, None
    if "retained_release" in geo:
        retained, release_report = read_retained_release(
            local(geo["retained_release"]), budget, libraries
        )
        keep, retention = retained_mask(pilot_metadata, retained)
        geo_report["retained_release"] = release_report
        geo_report["retained_cells"] = release_report["release_cells"]
        geo_report["retained_cell_barcode_mapping"] = "PILOT_EXACT_RELEASE_JOIN"
        if "author_filtered_libraries" in geo:
            author = pd.read_csv(
                io.BytesIO(read_asset(local(geo["author_filtered_libraries"]), budget))
            )
            geo_report["author_release_reconciliation"] = reconcile_author_libraries(
                author, release_report["library_manifest"]
            )
    paired = pair_and_cap(block, None, pilot_metadata, cap=cap, keep=keep)
    comparison = read_features(local(geo["comparison_features"]), budget)
    peak_sets = {
        geo["pilot_library"]: paired["atac_features"].feature_id.tolist(),
        geo["comparison_library"]: comparison.loc[
            comparison.modality.eq("Peaks"), "feature_id"
        ].tolist(),
    }
    compatibility = audit_peak_spaces(
        peak_sets,
        genome_builds={key: "unverified" for key in peak_sets},
        count_units={key: "unverified" for key in peak_sets},
    )
    blockers = [
        "GEO full-cohort raw barcode coverage and per-cell QC reproduction remain pending",
        "NeMO release/QC reconciliation, specimen provenance, and paired matrices remain pending",
        "ATAC shared-region/count contract and donor-level experiment protocol remain pending",
    ]
    if p22.approval_blocked():
        blockers.append("Professor approval record remains blocked; not modified by this audit")
    return {
        "preflight_status": "COMPLETED",
        "training_allowed": False,
        "model_training_performed": False,
        "scientific_outcome": "NOT_EVALUATED",
        "blocking_reasons": blockers,
        "geo": geo_report,
        "external": external_report,
        "atac_compatibility": compatibility,
        "pilot": {
            "library": geo["pilot_library"],
            "data_kind": "final_release_retained_cells"
            if retention
            else "raw_library_not_final_qc",
            "retention": retention,
            "source_cells": len(block["barcodes"]),
            "selected_cells": len(paired["metadata"]),
            "n_donors": int(paired["metadata"].donor_id.nunique()),
            "cell_cap": cap,
            "rna_features": paired["rna"].shape[1],
            "atac_features": paired["atac"].shape[1],
            "rna_nnz": paired["rna"].nnz,
            "atac_nnz": paired["atac"].nnz,
            "donors_below_cap": int(paired["metadata"].groupby("donor_id").size().lt(cap).sum()),
            "sample_seed": 22,
            "selected_cell_ids_sha256": hashlib.sha256(
                "\n".join(paired["metadata"].cell_id).encode()
            ).hexdigest(),
            "pairing": "shared columns in combined MEX",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cell-cap", type=int, default=256)
    parser.add_argument("--max-input-bytes", type=int, default=64 * 1024**2)
    parser.add_argument("--max-expanded-bytes", type=int, default=256 * 1024**2)
    parser.add_argument("--max-nnz", type=int, default=10_000_000)
    parser.add_argument("--source-identity", type=Path)
    parser.add_argument("--source-identity-sha256")
    parser.add_argument("--development-feasibility", type=Path)
    parser.add_argument("--development-feasibility-sha256")
    args = parser.parse_args(argv)
    evidence_args = (
        args.source_identity,
        args.source_identity_sha256,
        args.development_feasibility,
        args.development_feasibility_sha256,
    )
    if any(value is not None for value in evidence_args) and not all(evidence_args):
        parser.error("both feasibility records and their reviewed SHA256 values are required")
    if any(evidence_args) and (
        args.max_input_bytes,
        args.max_expanded_bytes,
        args.max_nnz,
        args.cell_cap,
    ) != (1_700_000_000, 268_435_456, 10_000_000, 256):
        parser.error("decision mode requires the four frozen F3 caps")
    if min(args.cell_cap, args.max_input_bytes, args.max_expanded_bytes, args.max_nnz) < 1:
        parser.error("caps and budgets must be positive")
    try:
        args.output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("output directory already exists; choose a new directory")
    budget = ReadBudget(args.max_input_bytes, args.max_expanded_bytes)
    decision = None
    try:
        inputs = load_feasibility_inputs(*evidence_args) if args.source_identity else None
        if args.manifest.stat().st_size > 1024**2:
            raise ValueError("manifest exceeds 1 MiB")
        raw = args.manifest.read_bytes()
        (args.output_dir / "manifest.json").write_bytes(raw)
        manifest = json.loads(raw)
        report, measurement = measure_stage(
            "paired_public_file_audit",
            lambda: audit(
                manifest, args.manifest.resolve().parent, budget, args.cell_cap, args.max_nnz
            ),
            cells_per_donor_cap=args.cell_cap,
            disk_path=args.output_dir,
            notes="Peak RSS includes imports and sparse parsing. Byte limits are not RAM limits.",
        )
        report["resources"] = measurement.to_dict() | {"input_bytes": budget.input_bytes}
        report["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
        if inputs is not None:
            decision = build_input_decision(report, inputs)
        exit_code = 0
    except (OSError, EOFError, ValueError, KeyError, TypeError, tarfile.TarError) as error:
        report = {
            "preflight_status": "FAILED",
            "training_allowed": False,
            "blocking_reasons": [str(error)],
            "model_training_performed": False,
        }
        exit_code = 2
    report.update(
        {
            "audit_utc": datetime.now(UTC).isoformat(),
            "files": budget.records,
            "expanded_bytes": budget.expanded_bytes,
            "command": sys.argv if argv is None else argv,
        }
    )
    (args.output_dir / "audit.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )
    if decision is not None:
        (args.output_dir / "input_decision.json").write_text(
            json.dumps(decision, indent=2, allow_nan=False) + "\n"
        )
        (args.output_dir / "INPUT_DECISION.md").write_text(render_input_decision(decision))
    lines = [
        "# Paired multiome public-file audit",
        "",
        f"File audit: {report['preflight_status']}.",
        "Training: BLOCKED. No models trained. No biological result produced.",
        "",
    ]
    if report["preflight_status"] == "COMPLETED":
        lines += [
            f"- GEO libraries: {report['geo']['n_libraries']}.",
            f"- GEO final-flag donors: {report['geo']['final_flag_donors']}; "
            f"published: {report['geo']['published_donors']}.",
            f"- NeMO metadata cells: {report['external']['metadata_cells']}; "
            f"published: {report['external']['published_cells']}.",
            "- NeMO annotation diagnostics: "
            f"{report['external']['annotation_diagnostics']['status']}; "
            "no exclusion applied, QC and specimen independence not certified.",
            f"- Pilot selected cells: {report['pilot']['selected_cells']} "
            f"({report['pilot']['data_kind']}).",
            f"- ATAC full-peak-union status: {report['atac_compatibility']['status']}.",
            f"- Exactly shared peaks: {report['atac_compatibility']['n_exact_common_regions']}.",
            "",
        ]
    lines += ["## Remaining gates", ""] + [f"- {reason}." for reason in report["blocking_reasons"]]
    (args.output_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    print(f"{report['preflight_status']}: {args.output_dir / 'SUMMARY.md'}; training not allowed")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
