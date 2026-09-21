"""Normalization-sensitivity check for the frozen internal paired comparison.

The frozen protocol (``configs/final_internal_comparison_2026-09-21.json``) uses
raw-count standard scaling and lists the accepted normalization as an unresolved
item. This script prospectively tests whether the frozen primary contrast is
sensitive to that choice, without replacing the primary estimate.

It runs the same 5 x 5 donor-isolated folds, the same per-fold training-only
region subsets, the same six neural families and the same initialization seed
under two preprocessing variants:

* ``raw_standard_scaler`` — the frozen primary (raw counts, training-only
  ``StandardScaler``); this must reproduce the frozen internal estimate.
* ``log1p_standard_scaler`` — ``log1p`` counts before the same training-only
  scaler. ``log1p`` is a fixed monotone per-value transform, not a fitted
  statistic, so applying it to every cell leaks no held-out information.

This is a robustness sensitivity, not a new primary endpoint, and it does not
alter the frozen study.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
from scipy import sparse  # noqa: E402

from p22.data.resources import environment_record, measure_stage  # noqa: E402
from p22.eval.multiome_protocol import MultiomeProtocol  # noqa: E402
from p22.eval.multiome_runner import run_paired_fold  # noqa: E402
from p22.eval.repeated_comparison import (  # noqa: E402
    repeated_model_accuracy,
    repeated_primary_contrast,
)
from p22.models.fusion import VIEW_A, VIEW_B  # noqa: E402
from run_real_paired_comparison import (  # noqa: E402
    ALL_FAMILIES,
    _fold_map,
    _indices,
    _predictions,
)
from run_real_paired_pilot import DEFAULT_H5AD, load_development_inputs  # noqa: E402

DEFAULT_ATAC = "reports/generated/repeated_comparison_20260921/counts/counts.npz"
DEFAULT_REGIONS = "reports/generated/repeated_comparison_20260921/region_sets.json"
VARIANTS = ("raw_standard_scaler", "log1p_standard_scaler")


def apply_log1p(matrix):
    """Return ``log1p`` of a sparse or dense non-negative count matrix."""
    if sparse.issparse(matrix):
        result = matrix.copy()
        result.data = np.log1p(result.data)
        return result
    return np.log1p(np.asarray(matrix, dtype=np.float64))


def variant_views(views, variant):
    if variant not in VARIANTS:
        raise ValueError(f"unknown normalization variant {variant!r}")
    if variant == "raw_standard_scaler":
        return views
    return {name: apply_log1p(matrix) for name, matrix in views.items()}


def _run_variant(protocol, views, metadata, folds, region_sets, union_index, variant):
    per_repeat: dict[int, dict[str, list[pd.DataFrame]]] = {}
    n_folds = 0
    for entry in region_sets["per_fold"]:
        key = (entry["repeat"], entry["fold"])
        outer = folds[key]
        columns = [union_index[region] for region in entry["regions"]]
        fold_views = {VIEW_A: views[VIEW_A], VIEW_B: views[VIEW_B][:, columns]}
        fold_views = variant_views(fold_views, variant)
        indices = _indices(metadata, outer)
        record = run_paired_fold(fold_views, metadata, indices, protocol)
        n_folds += 1
        for model in ALL_FAMILIES:
            table = _predictions(record, model)
            per_repeat.setdefault(outer.repeat, {}).setdefault(model, []).append(table)
    repeats = []
    for repeat in sorted(per_repeat):
        entry = {"repeat": repeat}
        for model in ALL_FAMILIES:
            entry[model] = pd.concat(per_repeat[repeat][model], ignore_index=True)
        repeats.append(entry)
    return {
        "variant": variant,
        "n_folds_run": n_folds,
        "n_repeats": len(repeats),
        "primary_comparison": repeated_primary_contrast(repeats),
        "model_summaries": {
            model: repeated_model_accuracy(repeats, model) for model in ALL_FAMILIES
        },
    }


def sensitivity_run(protocol, h5ad_path, atac_path, regions_path):
    views, metadata, fingerprints = load_development_inputs(h5ad_path, atac_path, protocol)
    region_sets = json.loads(Path(regions_path).read_text())
    union_regions = region_sets["union_regions"]
    union_index = {region: index for index, region in enumerate(union_regions)}
    if views[VIEW_B].shape[1] != len(union_regions):
        raise ValueError("ATAC matrix columns do not match the union region set")
    folds = _fold_map(metadata, protocol)
    if len(region_sets["per_fold"]) != len(folds):
        raise ValueError("region-set fold count does not match the split plan")
    variants = {
        variant: _run_variant(protocol, views, metadata, folds, region_sets, union_index, variant)
        for variant in VARIANTS
    }
    primary = variants["raw_standard_scaler"]["primary_comparison"]
    sensitivity = variants["log1p_standard_scaler"]["primary_comparison"]
    return {
        "data_mode": "real_development_normalization_sensitivity",
        "scientific_claim_allowed": False,
        "pilot": False,
        "primary_endpoint": False,
        "external_evaluation_performed": False,
        "input_fingerprints": fingerprints,
        "region_set_fingerprint": {
            "path": str(regions_path),
            "union_sha256": region_sets["union_sha256"],
            "n_union_regions": region_sets["n_union_regions"],
        },
        "variants": variants,
        "comparison": {
            "primary_estimate": primary["estimate"],
            "primary_interval": primary["interval"],
            "log1p_estimate": sensitivity["estimate"],
            "log1p_interval": sensitivity["interval"],
            "estimate_difference": (
                None
                if primary["estimate"] is None or sensitivity["estimate"] is None
                else float(sensitivity["estimate"] - primary["estimate"])
            ),
            "primary_advantage_demonstrated": primary["advantage_demonstrated"],
            "log1p_advantage_demonstrated": sensitivity["advantage_demonstrated"],
        },
        "limitations": [
            "Normalization sensitivity only; the frozen raw-count primary estimate is unchanged.",
            "Internal development folds only; external paired data were not accessed.",
            "No biological mechanism is claimed from attention or latent tokens.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/paired_multiome.json")
    parser.add_argument("--h5ad", default=DEFAULT_H5AD)
    parser.add_argument("--atac-matrix", default=str(ROOT / DEFAULT_ATAC))
    parser.add_argument("--region-sets", default=str(ROOT / DEFAULT_REGIONS))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        print("refusing to overwrite an existing output directory", file=sys.stderr)
        return 2
    config = json.loads(args.config.read_text())
    protocol = MultiomeProtocol(**config["protocol"])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    report, resource = measure_stage(
        "real_paired_normalization_sensitivity",
        lambda: sensitivity_run(protocol, args.h5ad, args.atac_matrix, args.region_sets),
        cells_per_donor_cap=protocol.cell_cap,
        disk_path=args.output_dir,
        notes="Normalization sensitivity on frozen folds; not a new primary endpoint",
    )
    report.update(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        protocol=asdict(protocol),
        protocol_sha256=protocol.fingerprint,
        environment=environment_record(),
        resources=resource.to_dict(),
    )
    (args.output_dir / "run.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    comparison = report["comparison"]
    summary = [
        "# Normalization sensitivity on the frozen internal folds",
        "",
        "Sensitivity only. The frozen raw-count primary estimate is unchanged.",
        "",
        f"- Raw standard scaler: cross-attention minus token-concat donor balanced "
        f"accuracy {comparison['primary_estimate']} (interval {comparison['primary_interval']}).",
        f"- log1p + standard scaler: {comparison['log1p_estimate']} "
        f"(interval {comparison['log1p_interval']}).",
        f"- Difference (log1p - raw): {comparison['estimate_difference']}.",
        "",
        "See run.json for both variants' per-repeat deltas and model summaries.",
    ]
    (args.output_dir / "SUMMARY.md").write_text("\n".join(summary) + "\n")
    print(args.output_dir / "SUMMARY.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
