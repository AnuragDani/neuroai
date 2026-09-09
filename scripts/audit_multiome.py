#!/usr/bin/env python
"""Audit pinned public files locally. Never download, train, or modify approval state."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

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
    args = parser.parse_args(argv)
    if min(args.cell_cap, args.max_input_bytes, args.max_expanded_bytes, args.max_nnz) < 1:
        parser.error("caps and budgets must be positive")
    try:
        args.output_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("output directory already exists; choose a new directory")
    budget = ReadBudget(args.max_input_bytes, args.max_expanded_bytes)
    try:
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
