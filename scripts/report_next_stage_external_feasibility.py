#!/usr/bin/env python3
"""Q5 bounded external feasibility: NeMO QC/specimen/age/feature contracts.

Audits pinned local NeMO metadata and offline-replays the resolved ATAC Open bag
declaration. No count/fragment payload downloads, package installs, fits, author
contact, or predictive evaluation. Preserves NeMO as reserved external evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import pandas as pd  # noqa: E402

from scripts import resolve_nemo_source as source  # noqa: E402
from p22.data.multiome import (  # noqa: E402
    ReadBudget,
    metadata_report,
    nemo_metadata_diagnostics,
    normalize_metadata,
    read_asset,
)

DEFAULT_MANIFEST = ROOT / "configs" / "paired_multiome_audit.json"
DEFAULT_METADATA_TAR = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/data/multiome/"
    "VuongWeber_DSdevctx_metadata.tar"
)
DEFAULT_SOURCE_BAG = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/"
    "input_feasibility_20260912/source/source-bag.tgz"
)
DEFAULT_SOURCE_IDENTITY = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/"
    "input_feasibility_20260912/source/source_identity.json"
)
DEFAULT_H5AD = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/data/real/"
    "f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
)
DEFAULT_OUT_DIR = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "next_stage_20260930"
)
EXPECTED_METADATA_SHA256 = (
    "72cf7284663aeaee76ed3bab16ce0b414faf82847a883e946e7c2afab21b1526"
)
EXPECTED_BAG_SHA256 = (
    "4698c4b80d1e1bde7588b9b0979beb113df2ca24aebf54afbbac606eaf064d45"
)
EXPECTED_SOURCE_IDENTITY_SHA256 = (
    "45ed2cb478fa4b780f8f29f3e2499109f0a93a3e9610bcc298d1d7813f154735"
)
EXPECTED_H5AD_SHA256 = (
    "08d6eff265db6e6a2e1c4a259153588f3dba3c51f5f754736dc63c28795fcdbb"
)
PUBLISHED_CELLS = 113_801
PUBLISHED_DONORS = 26


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"REFUSAL: {message}")


def _h5ad_donor_ids(path: Path) -> set[str]:
    import h5py
    import numpy as np

    with h5py.File(path, "r") as handle:
        obs = handle["obs"]
        node = obs["donor_id"]
        if "categories" in node:
            categories = node["categories"].asstr()[:]
            codes = np.asarray(node["codes"][:], dtype=int)
            return {str(categories[i]) for i in codes}
        return {str(value) for value in node.asstr()[:]}


def _load_nemo_frame(manifest: dict[str, Any], metadata_tar: Path) -> tuple[pd.DataFrame, dict]:
    external = manifest["external"]
    _require(external["published_cells"] == PUBLISHED_CELLS, "published_cells drift")
    _require(external["published_donors"] == PUBLISHED_DONORS, "published_donors drift")
    spec = {
        "path": str(metadata_tar),
        "sha256": external["metadata"]["sha256"],
        "member": external["metadata"]["member"],
        "source_url": external["metadata"]["source_url"],
    }
    _require(spec["sha256"] == EXPECTED_METADATA_SHA256, "metadata SHA-256 drift")
    budget = ReadBudget(max_input_bytes=64 * 1024**2, max_expanded_bytes=256 * 1024**2)
    raw = read_asset(spec, budget)
    frame = pd.read_csv(io.BytesIO(raw)).rename(columns=external["columns"])
    return frame, {
        "input_bytes": budget.input_bytes,
        "expanded_bytes": budget.expanded_bytes,
        "records": budget.records,
    }


def build_report(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    metadata_tar: Path = DEFAULT_METADATA_TAR,
    source_bag: Path = DEFAULT_SOURCE_BAG,
    source_identity: Path = DEFAULT_SOURCE_IDENTITY,
    h5ad_path: Path = DEFAULT_H5AD,
) -> dict[str, Any]:
    _require(manifest_path.is_file(), f"missing manifest {manifest_path}")
    _require(metadata_tar.is_file(), f"missing metadata tar {metadata_tar}")
    _require(source_bag.is_file(), f"missing source bag {source_bag}")
    _require(source_identity.is_file(), f"missing source identity {source_identity}")
    _require(h5ad_path.is_file(), f"missing H5AD {h5ad_path}")

    manifest = json.loads(manifest_path.read_text())
    identity_bytes = source_identity.read_bytes()
    identity_sha = hashlib.sha256(identity_bytes).hexdigest()
    _require(
        identity_sha == EXPECTED_SOURCE_IDENTITY_SHA256,
        "source_identity.json SHA-256 drift",
    )
    prior_identity = json.loads(identity_bytes.decode())
    bag_raw = source_bag.read_bytes()
    bag_sha = hashlib.sha256(bag_raw).hexdigest()
    _require(bag_sha == EXPECTED_BAG_SHA256, "source-bag.tgz SHA-256 drift")
    _require(_sha256_file(h5ad_path) == EXPECTED_H5AD_SHA256, "H5AD SHA-256 drift")

    bag_report: dict[str, Any] = {"decoded_bytes": 0}
    resolved_payload = source.validate_bag(bag_raw, bag_report)
    _require(
        resolved_payload["bytes"] == source.TARGET["bytes"]
        and resolved_payload["md5"] == source.TARGET["md5"],
        "payload declaration mismatch on offline bag replay",
    )

    frame, budget_info = _load_nemo_frame(manifest, metadata_tar)
    external = manifest["external"]
    diagnostics = nemo_metadata_diagnostics(frame, published_cells=PUBLISHED_CELLS)
    metadata = normalize_metadata(
        frame,
        condition_map=external["condition_map"],
        age_unit=external["age_unit"],
        age_source=external["age_source"],
    )
    report = metadata_report(
        metadata,
        published_cells=PUBLISHED_CELLS,
        expected_donors=PUBLISHED_DONORS,
    )
    report["paired_matrices_checked"] = False
    report["annotation_diagnostics"] = diagnostics

    current_donors = _h5ad_donor_ids(h5ad_path)
    nemo_donors = set(metadata.donor_id.astype(str))
    donor_id_overlap = sorted(current_donors & nemo_donors)
    sources = diagnostics["all_rows"]["donors_per_source"]
    age_units = sorted(set(metadata.age_unit.astype(str)))
    age_conversions = sorted(set(metadata.age_conversion.astype(str)))

    # Per-contract dispositions (public link / distinct IDs alone cannot PASS QC/independence).
    contracts = {
        "source_declaration": {
            "status": "ACCEPTED",
            "evidence": (
                "Offline replay of pinned ATAC Open bag matches expected SHA-256 and "
                "resolves the same count-package URL/size/MD5 as prior source_identity.json; "
                "no payload downloaded."
            ),
            "resolved_payload": resolved_payload,
            "bag_sha256": bag_sha,
            "prior_request": {
                "created_utc": prior_identity.get("created_utc"),
                "body_bytes": prior_identity.get("body_bytes"),
                "requests": prior_identity.get("requests"),
                "stop_reason": prior_identity.get("stop_reason"),
            },
        },
        "qc_release_discrepancy": {
            "status": "UNRESOLVED",
            "evidence": (
                "Metadata has 117,532 rows vs published 113,801. Exact candidate "
                "reconciliation class!='Unk' yields 3,731 removed and 113,801 remaining "
                f"(status={diagnostics['status']}), but exclusion is not applied and "
                "upstream QC is not reproduced; candidate rows still include "
                f"{diagnostics['candidate']['qc_threshold_counters']} threshold hits."
            ),
            "annotation_status": diagnostics["status"],
            "class_unknown_cells": diagnostics["class_unknown_cells"],
            "candidate_count_matches_published": diagnostics[
                "candidate_count_matches_published"
            ],
            "exclusion_applied": diagnostics["exclusion_applied"],
            "qc_reproduced": diagnostics["qc_reproduced"],
            "candidate_qc_threshold_counters": diagnostics["candidate"][
                "qc_threshold_counters"
            ],
        },
        "specimen_provenance": {
            "status": "UNRESOLVED",
            "evidence": (
                "Provider-level separation documented (NeMO UCLA/NIH_NBB vs current "
                "HDBR multiome). Donor-ID overlap with current H5AD is empty. This is "
                "no_overlap_evidence, not independently certified specimen non-overlap."
            ),
            "nemo_donors_per_source": sources,
            "current_h5ad_donors": len(current_donors),
            "nemo_donors": len(nemo_donors),
            "donor_id_overlap": donor_id_overlap,
            "specimen_independence_certified": diagnostics[
                "specimen_independence_certified"
            ],
            "metadata_specimen_independence": report["specimen_independence"],
        },
        "age_conventions": {
            "status": "ACCEPTED",
            "evidence": (
                "Pinned obstetric_GW unit with documented age_source; conversion "
                "GW_minus_2_approximate yields age_pcw for all rows. Canonical PCW "
                "13–20 overlap is SUPPORTED at 8 control / 10 Ts21 donors "
                "(support_is_not_power)."
            ),
            "age_unit": age_units,
            "age_conversion": age_conversions,
            "age_source": external["age_source"],
            "age_overlap": report["age_overlap"],
            "donors_per_class_all_ages": report["donors_per_class"],
        },
        "feature_count_semantics": {
            "status": "UNRESOLVED",
            "evidence": (
                "ATAC count-package declaration resolved (bytes/MD5/URL) but payload "
                "not downloaded. Study-specific peak calling; no common measured-region "
                "or count-unit contract established versus current exact 465-region union. "
                "paired_matrices_checked=false."
            ),
            "paired_matrices_checked": False,
            "declared_payload_bytes": resolved_payload["bytes"],
            "declared_payload_md5": resolved_payload["md5"],
            "payload_downloaded": False,
        },
    }

    alternatives = [
        {
            "id": "GSE280175",
            "role": "RNA-only external replication candidate",
            "status": "EXPLORATORY_ONLY",
            "rationale": (
                "5+5 fetal cortex donors with snRNA-seq only; no same-nucleus ATAC. "
                "Cannot close multimodal external evaluation; retain as orthogonal RNA check."
            ),
            "sources": [
                "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE280175",
                "https://www.nature.com/articles/s41467-025-63752-0",
            ],
        },
        {
            "id": "GSE204684",
            "role": "general cortex multiome pretraining candidate",
            "status": "EXPLORATORY_ONLY",
            "rationale": (
                "Paired RNA+ATAC exists but lacks DS-versus-euploid disease design; "
                "cannot train or validate the target DS classifier."
            ),
            "sources": [
                "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE204684",
                "https://doi.org/10.1126/sciadv.adg3754",
            ],
        },
    ]

    comparison = {
        "current_cohort_gse305146": {
            "donors": 30,
            "cells": 248_998,
            "q4_support": "SUPPORT_REPAIR_PASS / ELIGIBILITY_FROZEN",
            "q2_endpoint": "ENDPOINT_UNRESOLVED",
            "q3_regulatory": "REGULATORY_ADEQUACY_UNRESOLVED (structural PASS)",
            "atac_representation": (
                "exact counted 465-region union / fold 256-region panels present locally"
            ),
            "addresses_independent_cohort": False,
            "note": (
                "Targeted sampling repaired rare-type cell support; donor count and "
                "independent cell-state endpoint remain binding. Null/primary B_NULL "
                "does not imply the dataset is defective."
            ),
        },
        "external_candidate_nemo": {
            "donors": PUBLISHED_DONORS,
            "published_cells": PUBLISHED_CELLS,
            "metadata_cells": report["metadata_cells"],
            "donors_per_class": report["donors_per_class"],
            "role_preserved": "reserved_external_evaluation",
            "addresses_independent_cohort": True,
            "confirmatory_ready": False,
            "blocking_contracts": [
                name
                for name, row in contracts.items()
                if row["status"] == "UNRESOLVED"
            ],
            "note": (
                "Different-study candidate with resolved payload declaration; QC, "
                "specimen certification, and common-region contracts remain UNRESOLVED. "
                "Not a demonstrated power remedy."
            ),
        },
        "nemo_switched_to_development": False,
        "nemo_evaluation_role_preserved": True,
    }

    overall_status = "UNRESOLVED"
    if any(row["status"] == "UNRESOLVED" for row in contracts.values()):
        overall_status = "UNRESOLVED"
    elif all(row["status"] == "ACCEPTED" for row in contracts.values()):
        overall_status = "ACCEPTED"
    else:
        overall_status = "EXPLORATORY_ONLY"

    return {
        "schema_version": 1,
        "record_kind": "next_stage_external_feasibility_q5",
        "created_utc": datetime.now(UTC).isoformat(),
        "disposition": "EXTERNAL_FEASIBILITY_BOUNDED",
        "overall_confirmatory_status": overall_status,
        "nemo_evaluation_role": "PRESERVED",
        "network": {
            "new_requests_this_run": 0,
            "aggregate_new_download_bytes": 0,
            "budget_ceiling_bytes": 64 * 1024**2,
            "budget_ceiling_requests": 10,
            "note": (
                "No new network in Q5; prior bag GET (1867 bytes, 2026-09-12) cited "
                "from pinned source_identity.json; metadata and bag read locally."
            ),
            "prior_cited_requests": prior_identity.get("requests", []),
        },
        "local_reads": {
            "metadata_tar_sha256": EXPECTED_METADATA_SHA256,
            "source_bag_sha256": bag_sha,
            "source_identity_sha256": identity_sha,
            "h5ad_sha256": EXPECTED_H5AD_SHA256,
            "budget": budget_info,
            "bag_decoded_bytes": bag_report["decoded_bytes"],
        },
        "contracts": contracts,
        "nemo_metadata_report": {
            "metadata_cells": report["metadata_cells"],
            "published_cells": report["published_cells"],
            "count_difference": report["count_difference"],
            "release_qc_status": report["release_qc_status"],
            "n_donors": report["n_donors"],
            "expected_donors": report["expected_donors"],
            "donor_count_matches": report["donor_count_matches"],
            "donors_per_class": report["donors_per_class"],
            "cells_per_class": report["cells_per_class"],
            "n_libraries": report["n_libraries"],
            "age_overlap": report["age_overlap"],
            "specimen_independence": report["specimen_independence"],
            "confirmatory_ready": report["confirmatory_ready"],
            "paired_matrices_checked": report["paired_matrices_checked"],
            "annotation_diagnostics": {
                "status": diagnostics["status"],
                "published_cells": diagnostics["published_cells"],
                "candidate_count_matches_published": diagnostics[
                    "candidate_count_matches_published"
                ],
                "candidate_rule": diagnostics["candidate_rule"],
                "class_unknown_cells": diagnostics["class_unknown_cells"],
                "cluster_unknown_cells": diagnostics["cluster_unknown_cells"],
                "unknown_masks_equal": diagnostics["unknown_masks_equal"],
                "exclusion_applied": diagnostics["exclusion_applied"],
                "qc_reproduced": diagnostics["qc_reproduced"],
                "specimen_independence_certified": diagnostics[
                    "specimen_independence_certified"
                ],
                "all_rows": diagnostics["all_rows"],
                "candidate": diagnostics["candidate"],
                "qc_counter_interpretation": diagnostics["qc_counter_interpretation"],
            },
        },
        "comparison_current_vs_external": comparison,
        "alternatives": alternatives,
        "costed_payload_note": (
            "Full NeMO ATAC count package is declared at "
            f"{resolved_payload['bytes']} bytes (~1.54 GiB) MD5 "
            f"{resolved_payload['md5']}. Acquisition exceeds this continuation's "
            "64 MiB / no-payload budget; deliver a separate costed proposal before "
            "any download/recount."
        ),
        "scientific_invariants": {
            "primary": "B_NULL",
            "s7_v1": "INVALID",
            "s7_v2": "INVALID",
            "prior_s8": "NO FIT",
            "power": "POWER_UNESTABLISHED",
            "study": "STUDY_PARTIAL",
            "no_dataset_defect_from_null_alone": True,
        },
        "predictions": None,
        "fits": 0,
    }


def render_markdown(report: dict[str, Any]) -> str:
    contracts = report["contracts"]
    rows = "\n".join(
        f"| `{name}` | `{row['status']}` | {row['evidence']} |"
        for name, row in contracts.items()
    )
    alts = "\n".join(
        f"- **{a['id']}** (`{a['status']}`): {a['rationale']}"
        for a in report["alternatives"]
    )
    cmp_ = report["comparison_current_vs_external"]
    meta = report["nemo_metadata_report"]
    diag = meta["annotation_diagnostics"]
    return f"""# Q5 — Bounded external feasibility (NeMO)

**Disposition:** `{report['disposition']}`  
**Overall confirmatory status:** `{report['overall_confirmatory_status']}`  
**NeMO evaluation role:** `{report['nemo_evaluation_role']}`  
**Date:** 2026-09-30  
**Branch:** `gnhf/execute-the-p22-data-146414`  
**Dependency:** Q1 PASS. No fits, payload downloads, package installs, author contact, or external predictions.

Machine-readable: [external_feasibility.json](external_feasibility.json).

## Per-contract statuses

| Contract | Status | Evidence summary |
|---|---|---|
{rows}

Public availability and distinct donor IDs alone **cannot** pass QC or specimen-independence gates.

## NeMO metadata audit (local pinned files)

| Check | Value |
|---|---|
| Metadata cells | {meta['metadata_cells']} |
| Published cells | {meta['published_cells']} |
| Count difference | {meta['count_difference']} |
| Annotation diagnostic | `{diag['status']}` |
| `class == Unk` cells | {diag['class_unknown_cells']} |
| Candidate cells (`class != Unk`) | {diag['candidate']['cells']} |
| Candidate matches published | {diag['candidate_count_matches_published']} |
| Exclusion applied | {diag['exclusion_applied']} |
| QC reproduced | {diag['qc_reproduced']} |
| Donors | {meta['n_donors']} (expected {meta['expected_donors']}; per class {meta['donors_per_class']}) |
| Age overlap PCW 13–20 | {meta['age_overlap']} |
| Donor-ID overlap vs current H5AD | {report['contracts']['specimen_provenance']['donor_id_overlap'] or '[]'} |
| NeMO donors per source | {report['contracts']['specimen_provenance']['nemo_donors_per_source']} |
| Paired matrices checked | {meta['paired_matrices_checked']} |

## Source declaration (offline bag replay)

- Prior GET cited: {report['network']['prior_cited_requests']}
- New requests this run: **{report['network']['new_requests_this_run']}** (0 bytes new download)
- Offline bag SHA-256: `{report['local_reads']['source_bag_sha256']}`
- Resolved payload URL/size/MD5: `{contracts['source_declaration']['resolved_payload']}`
- Costed note: {report['costed_payload_note']}

## Current cohort repair vs external candidate

- **Current GSE305146 / H5AD:** {cmp_['current_cohort_gse305146']['note']} Q4 `{cmp_['current_cohort_gse305146']['q4_support']}`; Q2 `{cmp_['current_cohort_gse305146']['q2_endpoint']}`; Q3 `{cmp_['current_cohort_gse305146']['q3_regulatory']}`.
- **NeMO candidate:** {cmp_['external_candidate_nemo']['note']} Blocking contracts: `{cmp_['external_candidate_nemo']['blocking_contracts']}`.
- NeMO switched to development: **{cmp_['nemo_switched_to_development']}**. Evaluation role preserved: **{cmp_['nemo_evaluation_role_preserved']}**.

## At most two primary-source alternatives

{alts}

## Scientific invariants (unchanged)

Primary `{report['scientific_invariants']['primary']}`; S7-v1/v2 `{report['scientific_invariants']['s7_v1']}`; prior S8 `{report['scientific_invariants']['prior_s8']}`; power `{report['scientific_invariants']['power']}`; study `{report['scientific_invariants']['study']}`. Dataset-defect inference from null alone is forbidden.

## Checkpoint B implication

Support tables (Q4) and candidate-source audit (Q5) are complete. Confirmatory external predictive evaluation remains **blocked** by unresolved QC/specimen/feature contracts. Q6 may rank bottlenecks with these unresolved flags retained.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--metadata-tar", type=Path, default=DEFAULT_METADATA_TAR)
    parser.add_argument("--source-bag", type=Path, default=DEFAULT_SOURCE_BAG)
    parser.add_argument("--source-identity", type=Path, default=DEFAULT_SOURCE_IDENTITY)
    parser.add_argument("--h5ad", type=Path, default=DEFAULT_H5AD)
    args = parser.parse_args()

    report = build_report(
        manifest_path=args.manifest,
        metadata_tar=args.metadata_tar,
        source_bag=args.source_bag,
        source_identity=args.source_identity,
        h5ad_path=args.h5ad,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "external_feasibility.json"
    md_path = args.out_dir / "EXTERNAL_FEASIBILITY.md"
    json_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    md_path.write_text(render_markdown(report))
    print(report["disposition"], report["overall_confirmatory_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
