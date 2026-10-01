#!/usr/bin/env python3
"""R9 reporter: replay S10 corrected-null batch from saved sidecars.

Default is --skip-fits (no new scientific fits). Writes execute.json /
EXECUTE.md under failure_audit_20261001/. Attempt counters must not increase
on skip-fits replay.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from p22.eval.s7_ledger import sha256_file  # noqa: E402
from p22.eval.s9_execute import _pool_donor_ba_from_predictions  # noqa: E402
from p22.eval.s10_analytic import (  # noqa: E402
    ALLOWED_RAW_ROOT,
    DECISION_GENERATOR_SEED,
    PROTOCOL_ID,
    SCIENTIFIC_ATTEMPT_CAP,
    SYNTHETIC_ARTIFACT_GIB_CAP,
    SYNTHETIC_FITTING_HOURS_CAP,
    TORCH_THREADS,
    TOTAL_FITS,
    WORKERS,
    assign_donor_labels,
    verify_oracle_invariants,
)
from p22.eval.s10_execute import (  # noqa: E402
    load_attempt_counter,
    read_ledger_records,
    run_scientific_batch,
)

DEFAULT_OUT_DIR = (
    ROOT
    / "tasks"
    / "nn"
    / "professor_direction_investigation_20260929"
    / "failure_audit_20261001"
)
STAGE_COUNTER = (
    ROOT / "reports/generated/nn_failure_audit_20261001/attempt_counter.json"
)
BRANCH = "gnhf/execute-p22-s-failur-d8f02c"


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def _dir_size_bytes(path: Path) -> int:
    total = 0
    for p in Path(path).rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


def build_report(batch: Mapping[str, Any], *, skip_fits: bool) -> dict[str, Any]:
    root = Path(batch["raw_root"])
    counter = load_attempt_counter(root)
    records = read_ledger_records(root)
    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    oracle = verify_oracle_invariants(labels)
    cov = batch["coverage"]
    marginal = batch["marginal"]
    interp = batch["interpretation"]
    pairing_rho1 = batch["pairing_rho1"]
    pairing_rho0 = batch["pairing_rho0"]

    ca_ba = _pool_donor_ba_from_predictions(
        records, stage="screen", rho=1.0, model="cross_attention"
    )
    tc_ba = _pool_donor_ba_from_predictions(
        records, stage="screen", rho=1.0, model="token_concat"
    )
    advantage = {
        "label": "SEPARATE_NON_PRIMARY",
        "ca_ba": ca_ba.get("ba"),
        "token_concat_ba": tc_ba.get("ba"),
        "ca_minus_token_concat": (
            None
            if ca_ba.get("ba") is None or tc_ba.get("ba") is None
            else float(ca_ba["ba"]) - float(tc_ba["ba"])
        ),
        "complete": bool(ca_ba.get("complete") and tc_ba.get("complete")),
    }

    artifacts_gib = _dir_size_bytes(root) / (1024**3)
    fitting_hours = float(counter.get("fitting_seconds", 0.0)) / 3600.0
    rna_ba = marginal.get("logreg_rna", {}).get("ba")
    atac_ba = marginal.get("logreg_atac", {}).get("ba")
    resource = {
        "attempted_fits": int(counter.get("attempted_fits", 0)),
        "completed_ok": int(counter.get("completed_ok", 0)),
        "failed": int(counter.get("failed", 0)),
        "cap": SCIENTIFIC_ATTEMPT_CAP,
        "within_cap": int(counter.get("attempted_fits", 0)) <= SCIENTIFIC_ATTEMPT_CAP,
        "fitting_seconds": float(counter.get("fitting_seconds", 0.0)),
        "fitting_hours": fitting_hours,
        "fitting_hours_cap": SYNTHETIC_FITTING_HOURS_CAP,
        "within_fitting_hours": fitting_hours <= SYNTHETIC_FITTING_HOURS_CAP,
        "artifacts_gib": round(artifacts_gib, 6),
        "artifact_gib_cap": SYNTHETIC_ARTIFACT_GIB_CAP,
        "within_artifact_cap": artifacts_gib <= SYNTHETIC_ARTIFACT_GIB_CAP,
        "workers": int(batch.get("workers", WORKERS)),
        "torch_threads": TORCH_THREADS,
        "planned_fits": TOTAL_FITS,
    }

    stage = {}
    if STAGE_COUNTER.is_file():
        stage = json.loads(STAGE_COUNTER.read_text(encoding="utf-8"))

    return {
        "task": "R9",
        "disposition": interp["disposition"],
        "claim_disposition": interp["disposition"],
        "protocol_id": PROTOCOL_ID,
        "date": time.strftime("%Y-%m-%d"),
        "timestamp_utc": _utc_now(),
        "branch": BRANCH,
        "fits": int(counter.get("attempted_fits", 0)),
        "research_fits_executed": int(counter.get("attempted_fits", 0)),
        "network_bytes": 0,
        "depends_on": ["R8", "Checkpoint C"],
        "raw_root": str(root),
        "reviewed_hashes": batch["reviewed_hashes"],
        "coverage": cov,
        "execution": {
            "n_executed_this_call": batch["exec_summary"].get("n_executed_this_call"),
            "n_skipped_already_done": batch["exec_summary"].get(
                "n_skipped_already_done"
            ),
            "wall_seconds": batch["exec_summary"].get("wall_seconds"),
            "skipped": bool(skip_fits or batch["exec_summary"].get("skipped")),
            "skip_fits": bool(skip_fits),
            "mode": "replay_saved_sidecars" if skip_fits else "fit_then_score",
        },
        "oracle": oracle,
        "marginal_check": {
            "logreg_rna_ba": rna_ba,
            "logreg_atac_ba": atac_ba,
            "threshold": 0.6,
            "pass": bool(marginal.get("pass")),
            "logreg_rna": marginal.get("logreg_rna"),
            "logreg_atac": marginal.get("logreg_atac"),
        },
        "pairing_rho1": _jsonable(pairing_rho1),
        "pairing_rho0": _jsonable(pairing_rho0),
        "advantage_contrast": advantage,
        "interpretation": _jsonable(interp),
        "resources": resource,
        "stage_attempt_counter": {
            "scientific_fit_attempts": stage.get("scientific_fit_attempts"),
            "scientific_fit_cap": stage.get("scientific_fit_cap"),
            "diagnostic_fit_attempts": stage.get("diagnostic_fit_attempts"),
            "diagnostic_fit_cap": stage.get("diagnostic_fit_cap"),
            "generator_only_draws": stage.get("generator_only_draws"),
            "fitting_hours": stage.get("fitting_hours"),
            "r9_scientific_fits": stage.get("r9_scientific_fits"),
            "r9_fitting_hours_this_run": stage.get("r9_fitting_hours_this_run"),
        },
        "scientific_invariants": {
            "primary": "B_NULL",
            "s7_v1": "INVALID",
            "s7_v2": "INVALID",
            "prior_s8": "NO FIT",
            "s9": "INVALID",
            "power": "POWER_UNESTABLISHED",
            "study": "STUDY_PARTIAL",
            "q2_endpoint": "ENDPOINT_UNRESOLVED",
        },
        "ruled_in": [
            "Under corrected independent-Gaussian null, ρ=0 pairing gate is "
            f"{pairing_rho0.get('pairing_label')} (supports that S9 ρ=0 "
            "PAIRING_POSITIVE is explained by broken orthogonal-null "
            "exchangeability rather than requiring a leak claim from that alone)."
        ],
        "ruled_out_or_not_established": [
            "Method claim / biology upgrade from this software control",
            "Unimodal marginal PASS at ρ=1 under frozen joint gate",
            "CA ρ=1 PAIRING_POSITIVE under corrected null (observed "
            f"{pairing_rho1.get('pairing_label')})",
        ],
    }


def render_execute_markdown(report: Mapping[str, Any]) -> str:
    cov = report["coverage"]
    res = report["resources"]
    interp = report["interpretation"]
    p1 = report.get("pairing_rho1") or {}
    p0 = report.get("pairing_rho0") or {}
    lines = [
        "# R9 — Bounded S10 corrected-null pairing-use batch",
        "",
        f"**Disposition:** `{report['disposition']}`  ",
        f"**Protocol ID:** `{report['protocol_id']}`  ",
        f"**Date:** {report['date']}  ",
        f"**Branch:** `{report['branch']}`  ",
        f"**Research fits:** {report['research_fits_executed']}  ",
        f"**Raw root:** `{report['raw_root']}`  ",
        f"**Mode:** `{report['execution'].get('mode')}` "
        f"(skip_fits=`{report['execution'].get('skip_fits')}`)",
        "",
        "Machine-readable: [execute.json](execute.json).",
        "",
        "## Coverage",
        "",
        f"- Planned: {cov['planned']}; attempted: {cov['attempted']}; "
        f"ok: {cov['completed_ok']}; failed: {cov['failed']}",
        f"- Complete: `{cov['complete']}`",
        "",
        "## Primary pairing (CA)",
        "",
        f"- ρ=1 label: `{p1.get('pairing_label')}`",
        f"- ρ=0 null label: `{p0.get('pairing_label')}`",
        f"- Interpretation: {interp.get('reason')}",
        "",
    ]
    secondary = interp.get("secondary_findings") or []
    if secondary:
        lines.append("- Secondary findings:")
        for item in secondary:
            lines.append(f"  - {item}")
        lines.append("")
    lines.extend(
        [
            "## Advantage contrast (SEPARATE_NON_PRIMARY)",
            "",
            f"- CA BA: {report['advantage_contrast'].get('ca_ba')}",
            f"- token_concat BA: {report['advantage_contrast'].get('token_concat_ba')}",
            f"- CA−TC: {report['advantage_contrast'].get('ca_minus_token_concat')}",
            "",
            "## Marginal check (ρ=1)",
            "",
            f"- logreg_rna BA: {report['marginal_check'].get('logreg_rna_ba')}",
            f"- logreg_atac BA: {report['marginal_check'].get('logreg_atac_ba')}",
            f"- pass (≤{report['marginal_check'].get('threshold')}): "
            f"`{report['marginal_check'].get('pass')}`",
            "",
            "## Resources",
            "",
            f"- Fits: {res['attempted_fits']} ≤ {res['cap']} (`{res['within_cap']}`)",
            f"- Fitting hours: {res['fitting_hours']:.6f} ≤ {res['fitting_hours_cap']}",
            f"- Artifacts GiB: {res['artifacts_gib']} ≤ {res['artifact_gib_cap']}",
            f"- Workers×threads: {res['workers']}×{res['torch_threads']}",
            "",
            "## Ruled in / not established",
            "",
        ]
    )
    for item in report.get("ruled_in") or []:
        lines.append(f"- Ruled in: {item}")
    for item in report.get("ruled_out_or_not_established") or []:
        lines.append(f"- Not established / ruled out as claim: {item}")
    lines.extend(
        [
            "",
            "## Scientific invariants (unchanged)",
            "",
            "Primary `B_NULL`; S9 `INVALID` immutable; S7-v1/v2 `INVALID`; "
            "prior S8 `NO FIT`; Q2 `ENDPOINT_UNRESOLVED`; "
            "power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`.",
            "",
            "## Next",
            "",
            "R10 verified handoff (no further fits; no positive-result search).",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    out_dir: Path,
    *,
    skip_fits: bool,
    raw_root: Path | None,
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    before_stage = (
        STAGE_COUNTER.read_bytes() if STAGE_COUNTER.is_file() else b""
    )
    root = Path(raw_root or (ROOT / ALLOWED_RAW_ROOT))
    before_s10 = (root / "attempt_counter.json").read_bytes()

    batch = run_scientific_batch(
        workspace=ROOT,
        protocol_path=out_dir / "S10_PROTOCOL.json",
        split_path=out_dir / "S10_SPLIT_MANIFEST.json",
        review_path=out_dir / "NO_FIT_REVIEW_R8.json",
        raw_root=root,
        skip_fits=skip_fits,
    )
    report = build_report(batch, skip_fits=skip_fits)

    after_stage = (
        STAGE_COUNTER.read_bytes() if STAGE_COUNTER.is_file() else b""
    )
    after_s10 = (root / "attempt_counter.json").read_bytes()
    if skip_fits:
        if before_stage != after_stage:
            raise RuntimeError("stage attempt_counter changed during skip-fits replay")
        if before_s10 != after_s10:
            raise RuntimeError("S10 attempt_counter changed during skip-fits replay")

    json_path = out_dir / "execute.json"
    md_path = out_dir / "EXECUTE.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    md_path.write_text(render_execute_markdown(report))
    return {
        "disposition": report["disposition"],
        "protocol_id": report["protocol_id"],
        "research_fits_executed": report["research_fits_executed"],
        "coverage_complete": report["coverage"]["complete"],
        "skip_fits": skip_fits,
        "raw_root": report["raw_root"],
        "resources": report["resources"],
        "execute_json_sha256": sha256_file(json_path),
        "execute_md_sha256": sha256_file(md_path),
        "paths": {"execute_json": str(json_path), "execute_md": str(md_path)},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--raw-root", type=Path, default=None)
    parser.add_argument(
        "--skip-fits",
        action="store_true",
        default=True,
        help="Replay/summarize only from existing ledger (default; no new fits).",
    )
    parser.add_argument(
        "--allow-fits",
        action="store_true",
        help="Dangerous: permit fitting. Forbidden under current stop condition.",
    )
    args = parser.parse_args(argv)
    skip_fits = not args.allow_fits
    if not skip_fits:
        raise SystemExit("refusing --allow-fits under R9 closeout stop condition")
    summary = write_outputs(
        args.out_dir,
        skip_fits=skip_fits,
        raw_root=args.raw_root,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
