#!/usr/bin/env python3
"""E0 portable provenance report for execution repair (2026-10-02).

Verifies archive digests, measured ATAC/BED/region-set hashes, and the 30
pilot prediction sidecars under primary-checkout relative paths. No fits.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from p22.eval.execution_repair_provenance import build_provenance_report  # noqa: E402

DEFAULT_OUT_JSON = ROOT / "tasks" / "provenance_e0.json"
DEFAULT_OUT_MD = ROOT / "tasks" / "PROVENANCE_E0.md"


def render_markdown(report: dict) -> str:
    checks = report["checks"]
    archives = report["archives"]
    sidecars = report["pilot_sidecars"]
    measured = report["measured_inputs"]
    lines = [
        "# E0 portable provenance — 2026-10-02",
        "",
        f"**Disposition:** `{report['disposition']}`",
        "",
        "Canonical measured inputs and pilot sidecars resolve under the primary",
        "checkout. Former worktree absolute paths are provenance records only;",
        "hashed consolidation archives remain the immutable secondary source.",
        "",
        "## Checks",
        "",
        f"- Canonical paths without worktrees: `{checks['canonical_paths_resolve_without_worktrees']}`",
        f"- Archive hashes OK ({archives['n_archives_hash_ok']}/{archives['n_archives']}): "
        f"`{checks['archives_immutable_hashes_ok']}`",
        f"- Pilot sidecars retain exact hashes "
        f"({sidecars['n_sidecars_match']}/{sidecars['n_sidecars_expected']}): "
        f"`{checks['pilot_sidecars_retain_exact_hashes']}`",
        f"- Live worktrees absent: `{archives['all_live_worktrees_absent']}` "
        f"({archives['n_live_worktrees_missing']}/{archives['n_archives']})",
        f"- Research fits this stage: `0`",
        "",
        "## Measured digests",
        "",
        f"- ATAC matrix match: `{measured['matrix']['match']}` "
        f"(`{measured['matrix']['sha256']}`)",
        f"- Union BED match: `{measured['union_bed']['match']}`",
        f"- Region sets match: `{measured['region_sets']['match']}`",
        f"- Ordered cells (counts.json) match: "
        f"`{measured['ordered_cells_from_counts_json']['match']}`",
        f"- Former worktree ATAC resolves: `{measured['former_worktree_atac_resolves']}`",
        "",
        "## Scientific labels preserved",
        "",
    ]
    for key, value in report["scientific_status_unchanged"].items():
        lines.append(f"- `{key}`: **{value}**")
    lines.extend(
        [
            "",
            "## Missing older live dependencies",
            "",
        ]
    )
    for key, value in report["missing_older_dependencies"].items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(
        [
            "",
            "## Contract",
            "",
            f"- `{report['contract']}`",
            f"- Report JSON: `tasks/provenance_e0.json`",
            "",
            "No research fits. E1 next.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=ROOT)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    args = parser.parse_args()

    report = build_provenance_report(args.workspace)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.out_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"disposition": report["disposition"], "out_json": str(args.out_json)}))
    return 0 if report["disposition"] == "PORTABLE_PROVENANCE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
