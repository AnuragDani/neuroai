"""Frozen repeated donor-split internal comparison on real development paired data.

This is the final internal step the pilot deferred. It reuses the real paired
ingestion (:mod:`scripts.run_real_paired_pilot`) and the six-family adapter
(:func:`p22.eval.multiome_runner.run_paired_fold`) but runs the frozen 5 x 5
donor-isolated split, with a training-only region set for every outer fold. The
per-fold region sets are subsets of one measured union matrix, so the ATAC counts
are measured once and no unmeasured interval is zero-filled.

The primary estimand is the cross-attention minus matched token-concatenation
donor-level balanced-accuracy difference, averaged across repeats; uncertainty is a
donor-cluster bootstrap over that across-repeat mean. This is an internal comparison:
external paired data were not accessed and no biological mechanism is claimed.
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

import pandas as pd  # noqa: E402
import torch  # noqa: E402

from p22.data.group_splits import (  # noqa: E402
    iter_repeated_stratified_group_folds,
    validate_group_folds,
)
from p22.data.resources import environment_record, measure_stage  # noqa: E402
from p22.eval.multiome_protocol import MultiomeProtocol  # noqa: E402
from p22.eval.multiome_runner import NEURAL_FAMILIES, run_paired_fold  # noqa: E402
from p22.eval.real_paired_acceptance import (  # noqa: E402
    build_evidence,
    evaluate_input_acceptance,
    load_manifest,
    load_requirements,
)
from p22.eval.repeated_comparison import (  # noqa: E402
    repeated_model_accuracy,
    repeated_primary_contrast,
)
from p22.models.fusion import VIEW_A, VIEW_B  # noqa: E402
from run_real_paired_pilot import DEFAULT_H5AD, load_development_inputs  # noqa: E402

DEFAULT_ATAC = "reports/generated/repeated_comparison_20260921/counts/counts.npz"
DEFAULT_REGIONS = "reports/generated/repeated_comparison_20260921/region_sets.json"
ALL_FAMILIES = (*NEURAL_FAMILIES, "majority_control")


def _fold_map(metadata, protocol):
    folds = list(
        iter_repeated_stratified_group_folds(
            metadata.donor_id,
            metadata.label,
            protocol.n_repeats,
            protocol.n_folds,
            protocol.split_seed,
        )
    )
    problems = validate_group_folds(folds)
    if problems:
        raise ValueError("; ".join(problems))
    return {(fold.repeat, fold.fold): fold for fold in folds}


def _indices(metadata, outer):
    training = metadata.iloc[outer.train_index]
    inner = next(
        iter_repeated_stratified_group_folds(
            training.donor_id, training.label, n_repeats=1, n_folds=3, base_seed=outer.split_seed
        )
    )
    return {
        "train": outer.train_index[inner.train_index],
        "val": outer.train_index[inner.test_index],
        "test": outer.test_index,
    }


def _inner_validation_map(metadata, folds):
    """Inner-validation donor record per outer fold, from the executable split."""
    mapping = {}
    for outer in folds:
        indices = _indices(metadata, outer)
        val_donors = sorted(set(metadata.iloc[indices["val"]].donor_id.astype(str)))
        mapping[(outer.repeat, outer.fold)] = {
            "val_donors": val_donors,
            "selection_split": "val",
            "selection_unit": "donor",
        }
    return mapping


def _predictions(record, model):
    if model == "majority_control":
        return pd.DataFrame(record["majority_control"]["predictions"])
    return pd.DataFrame(record["models"][model]["predictions"])


def _protocol_evidence(protocol):
    return {
        "families": list(NEURAL_FAMILIES),
        "donor_aggregation": "mean_predicted_probability",
        "donor_threshold": 0.5,
        "practical_margin": 0.07,
        "uncertainty_method": "donor_cluster_percentile_bootstrap",
        "uncertainty_seed": 22,
        "n_repeats": protocol.n_repeats,
        "n_folds": protocol.n_folds,
        "split_seed": protocol.split_seed,
    }


def _population_evidence(metadata):
    donors = metadata.donor_id.astype(str)
    labels = metadata.label.astype(int)
    donor_labels = pd.Series(labels.to_numpy(), index=donors.to_numpy()).groupby(level=0).first()
    return {
        "n_donors": int(donor_labels.size),
        "n_control": int((donor_labels == 0).sum()),
        "n_positive": int((donor_labels == 1).sum()),
        "label_rule": "disease == 'complete trisomy 21'",
    }


def _acceptance_decision(
    protocol,
    fingerprints,
    region_sets,
    folds,
    metadata,
    atac_path,
    regions_path,
    req_path,
    man_path,
):
    if req_path is None:
        req_path = ROOT / "configs/real_paired_acceptance_2026-09-21.json"
    sidecar_path = Path(atac_path).parent / "counts.json"
    atac_sidecar = json.loads(sidecar_path.read_text()) if sidecar_path.is_file() else {}
    regions_file = atac_sidecar.get("regions_file")
    if regions_file and not Path(regions_file).is_absolute():
        regions_file = ROOT / regions_file
    evidence = build_evidence(
        fingerprints=fingerprints,
        region_sets=region_sets,
        folds=folds,
        protocol_evidence=_protocol_evidence(protocol),
        population=_population_evidence(metadata),
        atac_sidecar=atac_sidecar,
        regions_file=regions_file if regions_file else regions_path,
        inner_validation=_inner_validation_map(metadata, folds),
    )
    requirements = load_requirements(req_path)
    manifest = load_manifest(man_path)
    return evaluate_input_acceptance(
        requirements,
        manifest,
        evidence,
        n_folds_run=len(folds),
        expected_n_folds=protocol.n_repeats * protocol.n_folds,
    )


def comparison_run(protocol, h5ad_path, atac_path, regions_path, output_dir, req_path, man_path):
    views, metadata, fingerprints = load_development_inputs(h5ad_path, atac_path, protocol)
    region_sets = json.loads(Path(regions_path).read_text())
    union_regions = region_sets["union_regions"]
    union_index = {region: index for index, region in enumerate(union_regions)}
    if views[VIEW_B].shape[1] != len(union_regions):
        raise ValueError("ATAC matrix columns do not match the union region set")
    folds = _fold_map(metadata, protocol)
    if len(region_sets["per_fold"]) != len(folds):
        raise ValueError("region-set fold count does not match the split plan")
    acceptance = _acceptance_decision(
        protocol,
        fingerprints,
        region_sets,
        list(folds.values()),
        metadata,
        atac_path,
        regions_path,
        req_path,
        man_path,
    )

    per_fold_records = []
    per_repeat: dict[int, dict[str, list[pd.DataFrame]]] = {}
    for entry in region_sets["per_fold"]:
        key = (entry["repeat"], entry["fold"])
        if key not in folds:
            raise ValueError(f"region set references an unknown fold {key}")
        outer = folds[key]
        columns = [union_index[region] for region in entry["regions"]]
        fold_views = {VIEW_A: views[VIEW_A], VIEW_B: views[VIEW_B][:, columns]}
        indices = _indices(metadata, outer)
        record = run_paired_fold(fold_views, metadata, indices, protocol)
        per_fold_records.append(
            {
                "repeat": outer.repeat,
                "fold": outer.fold,
                "regions_sha256": entry["regions_sha256"],
                "n_test_donors": len(outer.test_donors),
                "test_donors": list(outer.test_donors),
                "record": record,
            }
        )
        for model in ALL_FAMILIES:
            table = _predictions(record, model)
            per_repeat.setdefault(outer.repeat, {}).setdefault(model, []).append(table)

    repeats = []
    for repeat in sorted(per_repeat):
        entry = {"repeat": repeat}
        for model in ALL_FAMILIES:
            entry[model] = pd.concat(per_repeat[repeat][model], ignore_index=True)
        repeats.append(entry)

    primary = repeated_primary_contrast(repeats)
    model_summaries = {model: repeated_model_accuracy(repeats, model) for model in ALL_FAMILIES}
    return {
        "data_mode": "real_development_internal_comparison",
        "scientific_claim_allowed": acceptance.scientific_claim_allowed,
        "pilot": not acceptance.scientific_claim_allowed,
        "final_internal_estimate": acceptance.final_internal_estimate,
        "external_evaluation_performed": False,
        "acceptance": acceptance.to_dict(),
        "n_folds_run": len(per_fold_records),
        "n_repeats": len(repeats),
        "input_fingerprints": fingerprints,
        "region_set_fingerprint": {
            "path": str(regions_path),
            "union_sha256": region_sets["union_sha256"],
            "n_union_regions": region_sets["n_union_regions"],
        },
        "per_fold": per_fold_records,
        "primary_comparison": primary,
        "model_summaries": model_summaries,
        "limitations": [
            "Internal development comparison only; external paired data were not accessed.",
            "Raw-count standard scaling; the accepted normalization is not separately frozen.",
            "No biological mechanism is claimed from attention or latent tokens.",
            "Predictions must not be used to select outcome-favourable donors.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/paired_multiome.json")
    parser.add_argument("--h5ad", default=DEFAULT_H5AD)
    parser.add_argument("--atac-matrix", default=str(ROOT / DEFAULT_ATAC))
    parser.add_argument("--region-sets", default=str(ROOT / DEFAULT_REGIONS))
    parser.add_argument(
        "--acceptance-requirements",
        type=Path,
        default=ROOT / "configs/real_paired_acceptance_2026-09-21.json",
    )
    parser.add_argument(
        "--acceptance-manifest",
        type=Path,
        default=None,
        help="measured artifact manifest; without it the run stays exploratory",
    )
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
        "real_paired_internal_comparison",
        lambda: comparison_run(
            protocol,
            args.h5ad,
            args.atac_matrix,
            args.region_sets,
            args.output_dir,
            args.acceptance_requirements,
            args.acceptance_manifest,
        ),
        cells_per_donor_cap=protocol.cell_cap,
        disk_path=args.output_dir,
        notes="Frozen repeated donor-split internal comparison on CPU; not external",
    )
    report.update(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        protocol=asdict(protocol),
        protocol_sha256=protocol.fingerprint,
        environment=environment_record(),
        resources=resource.to_dict(),
    )
    per_fold = report.pop("per_fold")
    (args.output_dir / "per_fold.json").write_text(
        json.dumps(per_fold, indent=2, default=str) + "\n"
    )
    (args.output_dir / "run.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    primary = report["primary_comparison"]
    summary = [
        "# Frozen repeated donor-split internal comparison",
        "",
        "Internal development comparison. External paired data were not accessed.",
        "",
        f"- Acceptance: {report['acceptance']['status']} "
        f"(scientific claim allowed: {report['scientific_claim_allowed']}; "
        f"final internal estimate: {report['final_internal_estimate']}).",
        f"- Blocking acceptance checks: {report['acceptance']['blocking_checks']}.",
        f"- Folds: {report['n_folds_run']} ({report['n_repeats']} repeats x 5); "
        f"donors tested per repeat: {primary['n_donors']} "
        f"({primary['n_control']} control / {primary['n_positive']} DS).",
        f"- Cross-attention minus token-concat donor balanced accuracy: "
        f"{primary['estimate']} (95% interval {primary['interval']}).",
        f"- Practical margin: {primary['practical_margin']}; "
        f"advantage demonstrated: {primary['advantage_demonstrated']}.",
        f"- Per-repeat delta: {primary['per_repeat_delta']}.",
        f"- Bootstrap valid/failed replicates: {primary['n_valid']}/{primary['n_failed']}.",
        "",
        "Per-model donor balanced accuracy (mean across repeats):",
        *[
            f"- {model}: {values['mean']} (per repeat {values['per_repeat']})"
            for model, values in report["model_summaries"].items()
        ],
        "",
        "See run.json for the primary record and per_fold.json for per-fold predictions.",
    ]
    (args.output_dir / "SUMMARY.md").write_text("\n".join(summary) + "\n")
    print(args.output_dir / "SUMMARY.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
