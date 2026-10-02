#!/usr/bin/env python3
"""E3 full-executor authorization report for execution repair (2026-10-02).

Rematches the complete real-data execution path, mutates each immutable entry
in a temporary fixture (require refusal), measures filesystem artifact bytes,
and verifies resume skip preserves counters. Bounded toy only; scientific
NOT_AUTHORIZED / B_NULL preserved. Zero research fits.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from p22.eval.execution_repair_authorization import (  # noqa: E402
    FULL_EXECUTOR_IMMUTABLE_KEYS,
    MUTABLE_COUNTER_KEY,
    AuthorizationBindingError,
    lock_path,
    measure_artifact_bytes,
    mutate_and_refuse,
    refuse_changed_source_learning,
    resume_skips_completed_jobs,
)
from p22.eval.masked_atac_execute import (  # noqa: E402
    execute_jobs_serial,
    job_fit_id,
    load_attempt_counter,
    save_attempt_counter,
)
from p22.eval.masked_atac_pilot import authorize_immutable_lock  # noqa: E402
from p22.eval.s7_ledger import sha256_file  # noqa: E402

DEFAULT_OUT_JSON = ROOT / "tasks" / "authorization_e3.json"
DEFAULT_OUT_MD = ROOT / "tasks" / "AUTHORIZATION_E3.md"


def build_authorization_report(workspace: Path) -> dict[str, Any]:
    workspace = Path(workspace)
    lock = lock_path(workspace)
    verified = refuse_changed_source_learning(workspace=workspace)
    auth = authorize_immutable_lock(
        workspace=workspace, allow_progressed_counter=True
    )
    artifacts = measure_artifact_bytes(
        workspace / "reports/generated/nn_masked_atac_pilot_20261001"
    )
    lock_blob = json.loads(lock.read_text(encoding="utf-8"))
    mutation_results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="e3_mut_") as tmp:
        tmp_root = Path(tmp)
        for key in FULL_EXECUTOR_IMMUTABLE_KEYS:
            mutation_results.append(
                mutate_and_refuse(
                    workspace=workspace,
                    key=key,
                    lock_blob=lock_blob,
                    tmp_root=tmp_root / key.replace("/", "__"),
                )
            )
    all_refused = all(bool(r["refused"]) for r in mutation_results)

    # Resume fixture.
    with tempfile.TemporaryDirectory(prefix="e3_resume_") as tmp:
        raw = Path(tmp) / "raw"
        raw.mkdir()
        (raw / "predictions").mkdir()
        counter_path = raw / "attempt_counter.json"
        jobs = [
            {"stage": "toy", "arm": "token_concat", "fold": 0},
            {"stage": "toy", "arm": "cross_attention", "fold": 0},
        ]
        fit_ids = [job_fit_id(j) for j in jobs]
        save_attempt_counter(
            counter_path,
            {
                "stage": "toy_e3_resume",
                "scientific_fits": {"used": 1, "cap": 40},
                "smoke_fits": {"used": 0, "cap": 5},
                "total_attempts": {"used": 1, "hard_cap": 40},
                "fitting_hours": {"used": 0.0, "cap": 6.0},
                "artifacts_gib": {"used": 0.0, "cap": 4.0},
                "network_bytes": 0,
                "workers": 1,
                "torch_threads": 2,
                "reserved_fit_ids": list(fit_ids),
                "completed_fit_ids": list(fit_ids),
                "failed_fit_ids": [],
            },
        )
        calls: list[str] = []

        def fit_fn(job: dict) -> dict:
            fid = job_fit_id(job)
            calls.append(fid)
            return {"fit_id": fid, "status": "ok"}

        resume = resume_skips_completed_jobs(
            jobs=jobs,
            raw_root=raw,
            counter_path=counter_path,
            fit_fn=fit_fn,
            execute_jobs_serial=execute_jobs_serial,
            job_fit_id=job_fit_id,
            load_attempt_counter=load_attempt_counter,
            save_attempt_counter=save_attempt_counter,
        )

    # Confirm mutable counter excluded from immutable set.
    mutable_excluded = MUTABLE_COUNTER_KEY not in lock_blob["immutable_reviewed_hashes"]
    # Changing scientific_fits_authorized to true in a temp lock must refuse.
    scientific_flip_refused = False
    with tempfile.TemporaryDirectory(prefix="e3_sci_") as tmp:
        bad = Path(tmp) / "lock.json"
        flipped = dict(lock_blob)
        flipped["scientific_fits_authorized"] = True
        bad.write_text(json.dumps(flipped) + "\n")
        try:
            refuse_changed_source_learning(workspace=workspace, lock_file=bad)
        except AuthorizationBindingError:
            scientific_flip_refused = True

    checks = {
        "lock_present": lock.is_file(),
        "lock_sha256": sha256_file(lock),
        "n_immutable_keys": int(verified["n_immutable_keys"]),
        "live_rematch_ok": bool(verified["ok"]),
        "authorize_includes_full_executor": "full_executor" in auth,
        "scientific_fits_authorized": bool(verified["scientific_fits_authorized"]),
        "mutable_counter_excluded": mutable_excluded,
        "mutable_counter_used": int(verified["mutable_counter"]["total_attempts_used"]),
        "mutable_counter_sha256": verified["mutable_counter"]["sha256"],
        "all_mutations_refused": all_refused,
        "n_mutation_cases": len(mutation_results),
        "resume_skips_completed": bool(resume["counter_preserved_for_skipped"]),
        "resume_n_skipped": int(resume["n_skipped_already_done"]),
        "resume_n_executed": int(resume["n_executed_this_call"]),
        "resume_used_preserved": int(resume["used_after"]) == int(resume["used_before"]),
        "artifact_du_kib": int(artifacts["du_kib"]),
        "artifact_du_gib": float(artifacts["du_gib"]),
        "artifact_n_files": int(artifacts["n_files"]),
        "artifact_within_cap": bool(artifacts["within_cap"]),
        "scientific_flip_refused": scientific_flip_refused,
        "m8_locked_execute_digest_unchanged": (
            verified["immutable_reviewed_hashes"][
                "src/p22/eval/masked_atac_execute.py"
            ]
            == "a9798c008689489ac913563a978726e2011a3e10cdb08f77d42df954a93987aa"
        ),
        "m8_locked_adapter_digest_unchanged": (
            verified["immutable_reviewed_hashes"][
                "src/p22/eval/masked_atac_adapter.py"
            ]
            == "cda024a4e0812c7ba76cb435b6e4cfd66de2879d408413f4a6a2d5f19068aae6"
        ),
    }
    required = (
        "lock_present",
        "live_rematch_ok",
        "authorize_includes_full_executor",
        "mutable_counter_excluded",
        "all_mutations_refused",
        "resume_skips_completed",
        "resume_used_preserved",
        "artifact_within_cap",
        "scientific_flip_refused",
        "m8_locked_execute_digest_unchanged",
        "m8_locked_adapter_digest_unchanged",
    )
    all_pass = (
        all(bool(checks[k]) for k in required)
        and checks["scientific_fits_authorized"] is False
        and checks["n_immutable_keys"] == len(FULL_EXECUTOR_IMMUTABLE_KEYS)
        and checks["n_mutation_cases"] == len(FULL_EXECUTOR_IMMUTABLE_KEYS)
        and checks["artifact_du_kib"] > 0
    )
    return {
        "disposition": (
            "FULL_EXECUTOR_AUTHORIZATION_PASS"
            if all_pass
            else "FULL_EXECUTOR_AUTHORIZATION_FAIL"
        ),
        "stage": "E3",
        "date": "2026-10-02",
        "research_fits": 0,
        "bounded_toy_only": True,
        "checks": checks,
        "required_checks_pass": all_pass,
        "mutation_results": [
            {"key": r["key"], "refused": r["refused"]} for r in mutation_results
        ],
        "scientific_status_unchanged": {
            "masked_atac_m9": "NOT_AUTHORIZED",
            "primary": "B_NULL",
            "prior_S10_S9_S7": "INVALID",
            "prior_S8": "NO FIT",
        },
        "artifacts": {
            "helper": "src/p22/eval/execution_repair_authorization.py",
            "lock": str(lock.relative_to(workspace)),
            "pilot_wiring": "src/p22/eval/masked_atac_pilot.py → authorize_immutable_lock",
            "focused_tests": "tests/test_execution_repair_authorization_e3.py",
        },
        "notes": [
            "M10 gap: runner + pilot were outside M8 REQUIRED_LOCK_KEYS; E3 binds them.",
            "Mutable attempt_counter remains separate from immutable source digests.",
            "Filesystem du measures artifact bytes; counter artifacts_gib.used stays 0.0.",
            "scientific_fits_authorized=false; E4 independent review still required.",
        ],
    }


def render_md(report: dict[str, Any]) -> str:
    checks = report["checks"]
    lines = [
        "# E3 full-executor authorization — 2026-10-02",
        "",
        f"**Disposition:** `{report['disposition']}`",
        "",
        "Review lock covers runner, preprocessing/fit module, repair helpers and",
        "transitive dependencies. Changed source refuses learning. Mutable counters",
        "remain separate from immutable source hashes. Artifact bytes measured from",
        "the filesystem. Bounded toy resume skips completed jobs. Scientific pilot",
        "status remains NOT_AUTHORIZED.",
        "",
        "## Checks",
        "",
        f"- Lock present: `{checks['lock_present']}`",
        f"- Lock SHA-256: `{checks['lock_sha256']}`",
        f"- Immutable keys rematched: `{checks['n_immutable_keys']}`",
        f"- Live rematch ok: `{checks['live_rematch_ok']}`",
        f"- Authorize includes full executor: `{checks['authorize_includes_full_executor']}`",
        f"- Scientific fits authorized: `{checks['scientific_fits_authorized']}`",
        f"- Mutable counter excluded: `{checks['mutable_counter_excluded']}`",
        f"- Mutable counter used: `{checks['mutable_counter_used']}`",
        f"- All mutations refused: `{checks['all_mutations_refused']}` "
        f"({checks['n_mutation_cases']} cases)",
        f"- Resume skips completed / used preserved: "
        f"`{checks['resume_skips_completed']}` / `{checks['resume_used_preserved']}`",
        f"- Artifact du KiB / GiB / files: `{checks['artifact_du_kib']}` / "
        f"`{checks['artifact_du_gib']:.6f}` / `{checks['artifact_n_files']}`",
        f"- Artifact within cap: `{checks['artifact_within_cap']}`",
        f"- Scientific flip refused: `{checks['scientific_flip_refused']}`",
        f"- M8 execute/adapter digests unchanged: "
        f"`{checks['m8_locked_execute_digest_unchanged']}` / "
        f"`{checks['m8_locked_adapter_digest_unchanged']}`",
        f"- Research fits this stage: `{report['research_fits']}`",
        "",
        "## Scientific labels preserved",
        "",
        f"- `masked_atac_m9`: **{report['scientific_status_unchanged']['masked_atac_m9']}**",
        f"- `primary`: **{report['scientific_status_unchanged']['primary']}**",
        f"- `prior_S10_S9_S7`: **{report['scientific_status_unchanged']['prior_S10_S9_S7']}**",
        f"- `prior_S8`: **{report['scientific_status_unchanged']['prior_S8']}**",
        "",
        "## Evidence",
        "",
        f"- `{report['artifacts']['helper']}`",
        f"- `{report['artifacts']['lock']}`",
        f"- `{report['artifacts']['pilot_wiring']}`",
        f"- Focused tests: `{report['artifacts']['focused_tests']}`",
        "",
        "No research fits. Next: Checkpoint B (focused + integration controls).",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=ROOT)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args(argv)
    report = build_authorization_report(args.workspace)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(report), encoding="utf-8")
    print(report["disposition"])
    return 0 if report["disposition"] == "FULL_EXECUTOR_AUTHORIZATION_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
