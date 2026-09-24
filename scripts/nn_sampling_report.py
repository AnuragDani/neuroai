"""Report per-donor library and cell-type counts for the N1 stratified sampler.

Writes a compact JSON evidence file under ``docs/nn_v2/`` comparing the new
sampler at cap 1000 (the A6 primary cap) with cap 256 (the historical
reproduction cap). All counts are descriptive; no model is fit and no disease
label is read.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import pandas as pd  # noqa: E402

from p22.data.nn_sampling import sample_donor_stratified_cells  # noqa: E402

DEFAULT_H5AD = (
    ROOT / "data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
)
DEFAULT_OUT = ROOT / "docs/nn_v2/sampling_cap1000_seed22.json"
INPUTS = ROOT / "configs/nn_inputs_2026-09-23.json"
OBS_COLUMNS = ["donor_id", "library", "author_cell_type"]


def load_obs(h5ad_path: Path) -> pd.DataFrame:
    import anndata as ad

    backed = ad.read_h5ad(h5ad_path, backed="r")
    try:
        obs = backed.obs[OBS_COLUMNS].copy()
    finally:
        backed.file.close()
    for column in OBS_COLUMNS:
        obs[column] = obs[column].astype(str)
    return obs


def h5ad_sha256() -> str | None:
    if not INPUTS.exists():
        return None
    manifest = json.loads(INPUTS.read_text())
    entry = manifest.get("inputs", {}).get("h5ad", {})
    return entry.get("sha256")


def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:  # pragma: no cover - git should exist in this repo
        return "unknown"


def counts_by(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.value_counts().sort_index().items()}


def cap_report(obs: pd.DataFrame, cap: int, seed: int) -> dict:
    selected = obs.iloc[sample_donor_stratified_cells(obs, cap=cap, seed=seed)]
    donors: dict[str, dict] = {}
    for donor, group in obs.groupby("donor_id", observed=True):
        chosen = selected[selected["donor_id"] == donor]
        donors[str(donor)] = {
            "available": int(len(group)),
            "selected": int(len(chosen)),
            "library_available": counts_by(group["library"]),
            "library_selected": counts_by(chosen["library"]),
            "cell_type_available": counts_by(group["author_cell_type"]),
            "cell_type_selected": counts_by(chosen["author_cell_type"]),
        }
    return {
        "cap": cap,
        "seed": seed,
        "n_cells_available": int(len(obs)),
        "n_cells_selected": int(len(selected)),
        "n_donors": int(obs["donor_id"].nunique()),
        "donors": donors,
    }


def proportionality_audit(cap_data: dict) -> dict:
    cap = cap_data["cap"]
    violations: list[dict] = []
    two_library_donors = 0
    for donor, info in cap_data["donors"].items():
        available = info["library_available"]
        if len(available) < 2:
            continue
        two_library_donors += 1
        total = info["available"]
        for library, count in available.items():
            expected = count / total * cap
            got = info["library_selected"].get(library, 0)
            deviation = abs(got - expected)
            if deviation > 2:
                violations.append(
                    {
                        "donor": donor,
                        "library": library,
                        "expected": expected,
                        "got": got,
                        "deviation": deviation,
                    }
                )
    return {
        "two_library_donors": two_library_donors,
        "max_tolerance_cells": 2,
        "violations": violations,
        "passed": not violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5ad", type=Path, default=DEFAULT_H5AD)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    obs = load_obs(args.h5ad)
    report = {
        "created_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_head": git_head(),
        "h5ad": str(args.h5ad),
        "h5ad_sha256": h5ad_sha256(),
        "sampler": "p22.data.nn_sampling.sample_donor_stratified_cells",
        "strata": ["author_cell_type", "library"],
        "primary": cap_report(obs, cap=1000, seed=22),
        "reproduction": cap_report(obs, cap=256, seed=22),
    }
    report["primary"]["proportionality_audit"] = proportionality_audit(report["primary"])
    report["reproduction"]["proportionality_audit"] = proportionality_audit(
        report["reproduction"]
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    audit = report["primary"]["proportionality_audit"]
    print(
        f"wrote {args.out} | primary cells="
        f"{report['primary']['n_cells_selected']} | two-library donors="
        f"{audit['two_library_donors']} | violations={len(audit['violations'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
