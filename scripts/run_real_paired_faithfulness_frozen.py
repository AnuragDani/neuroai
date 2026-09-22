"""Held-out faithfulness and initialization sensitivity on the frozen final folds.

The real pilot ran the seven held-out interventions and the initialization-seed
sensitivity on one outer fold (``scripts/run_real_paired_faithfulness.py``). This
script repeats both on the frozen 5 x 5 donor-isolated split used by the internal
comparison, reusing each fold's training-only region subset of the measured union
matrix. No new network access is required: the union counts are already measured.

It closes the "applicable faithfulness tests" item for the frozen internal
comparison. It is still internal development evidence: external paired data were not
accessed, interventions are manipulation evidence rather than causal biology, and
the raw-count standard scaling is not separately frozen.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

from p22.data.group_splits import aggregate_donor_probabilities  # noqa: E402
from p22.data.resources import environment_record, measure_stage  # noqa: E402
from p22.eval.multiome_protocol import MultiomeProtocol  # noqa: E402
from p22.eval.multiome_runner import model_inputs, paired_model, prepare_paired_fold  # noqa: E402
from p22.eval.paired_faithfulness import (  # noqa: E402
    aggregate_interventions,
    donor_balanced_accuracy,
    initialization_seed_spread,
    run_donor_interventions,
)
from p22.eval.repeated_comparison import initialization_primary_sensitivity  # noqa: E402
from p22.models.fusion import VIEW_A, VIEW_B  # noqa: E402
from p22.training.loop import predict, train_model  # noqa: E402
from run_real_paired_comparison import _acceptance_decision, _fold_map, _indices  # noqa: E402
from run_real_paired_pilot import DEFAULT_H5AD, load_development_inputs  # noqa: E402

INTERVENTION_FAMILIES = ("rna_atac_concat", "gated_fusion", "token_concat", "cross_attention")
PRIMARY_FAMILIES = ("cross_attention", "token_concat")
DEFAULT_ATAC = "reports/generated/repeated_comparison_20260921/counts/counts.npz"
DEFAULT_REGIONS = "reports/generated/repeated_comparison_20260921/region_sets.json"
DEFAULT_INIT_SEEDS = (0, 1, 2)


def _fit(name, transformed, protocol, labels, donors, indices):
    model = paired_model(
        name, [transformed[VIEW_A].shape[1], transformed[VIEW_B].shape[1]], protocol
    )
    inputs = model_inputs(name, transformed)
    trained = train_model(
        model,
        {key: value[indices["train"]] for key, value in inputs.items()},
        labels[indices["train"]],
        {key: value[indices["val"]] for key, value in inputs.items()},
        labels[indices["val"]],
        max_epochs=protocol.max_epochs,
        patience=protocol.patience,
        batch_size=protocol.batch_size,
        learning_rate=protocol.learning_rate,
        seed=protocol.model_seed,
        train_donor_ids=donors[indices["train"]],
        val_donor_ids=donors[indices["val"]],
    )
    return trained.model


def _donor_score(model, family, transformed, rows, labels, donors):
    inputs = model_inputs(family, transformed)
    _, probabilities = predict(model, {key: value[rows] for key, value in inputs.items()})
    return donor_balanced_accuracy(probabilities[:, 1], donors[rows], labels[rows])["value"]


def _donor_predictions(model, family, transformed, rows, labels, donors):
    """Donor-level prediction table for one family on one held-out fold.

    Columns match the primary comparison (`donor_id`, `label`, `probability`), so the
    initialization sensitivity can reuse the declared pooled-donor estimand instead
    of a mean of per-fold balanced accuracies.
    """
    inputs = model_inputs(family, transformed)
    _, probabilities = predict(model, {key: value[rows] for key, value in inputs.items()})
    table = aggregate_donor_probabilities(probabilities[:, 1], donors[rows])
    truth = pd.Series(labels[rows], index=donors[rows]).groupby(level=0).first()
    table["label"] = table.donor_id.map(truth).astype(int)
    return table


def faithfulness_frozen_run(
    protocol,
    h5ad_path,
    atac_path,
    regions_path,
    output_dir,
    init_seeds=DEFAULT_INIT_SEEDS,
    req_path=None,
    man_path=None,
):
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

    labels = metadata.label.to_numpy()
    donors = metadata.donor_id.astype(str).to_numpy()
    seeds = sorted({int(seed) for seed in (*init_seeds, protocol.model_seed)})

    fold_tables: dict[str, list] = {family: [] for family in INTERVENTION_FAMILIES}
    seed_records: dict[int, list] = {seed: [] for seed in seeds}
    seed_tables: dict[int, dict[int, dict[str, list]]] = {seed: {} for seed in seeds}
    per_fold = []
    for entry in region_sets["per_fold"]:
        key = (entry["repeat"], entry["fold"])
        if key not in folds:
            raise ValueError(f"region set references an unknown fold {key}")
        outer = folds[key]
        columns = [union_index[region] for region in entry["regions"]]
        fold_views = {VIEW_A: views[VIEW_A], VIEW_B: views[VIEW_B][:, columns]}
        indices = _indices(metadata, outer)
        transformed, evidence = prepare_paired_fold(fold_views, metadata, indices, protocol)
        test, train = indices["test"], indices["train"]

        models = {}
        for family in INTERVENTION_FAMILIES:
            model = _fit(family, transformed, protocol, labels, donors, indices)
            models[family] = model
            test_views = {name: value[test] for name, value in transformed.items()}
            train_views = {name: value[train] for name, value in transformed.items()}
            fold_tables[family].append(
                run_donor_interventions(
                    model,
                    test_views,
                    train_views,
                    labels[test],
                    donors[test],
                    seed=protocol.model_seed,
                )
            )

        for seed in seeds:
            seed_protocol = (
                protocol if seed == protocol.model_seed else replace(protocol, model_seed=seed)
            )
            scores = {}
            for family in PRIMARY_FAMILIES:
                model = (
                    models[family]
                    if seed == protocol.model_seed
                    else _fit(family, transformed, seed_protocol, labels, donors, indices)
                )
                scores[family] = _donor_score(model, family, transformed, test, labels, donors)
                seed_tables[seed].setdefault(outer.repeat, {}).setdefault(family, []).append(
                    _donor_predictions(model, family, transformed, test, labels, donors)
                )
            seed_records[seed].append(
                {
                    "repeat": outer.repeat,
                    "fold": outer.fold,
                    "n_test_donors": len(outer.test_donors),
                    "test_donors": list(outer.test_donors),
                    "scores": scores,
                    "delta": float(scores["cross_attention"] - scores["token_concat"]),
                }
            )
        per_fold.append(
            {
                "repeat": outer.repeat,
                "fold": outer.fold,
                "regions_sha256": entry["regions_sha256"],
                "n_test_donors": len(outer.test_donors),
                "test_donors": list(outer.test_donors),
                "preprocessing_evidence": evidence,
            }
        )

    interventions = aggregate_interventions(fold_tables)
    seed_summary = {}
    for seed in seeds:
        records = seed_records[seed]
        deltas = [record["delta"] for record in records]
        seed_summary[seed] = {
            "n_folds": len(records),
            "cross_attention_mean": float(
                np.mean([record["scores"]["cross_attention"] for record in records])
            ),
            "token_concat_mean": float(
                np.mean([record["scores"]["token_concat"] for record in records])
            ),
            "delta_mean": float(np.mean(deltas)),
            "delta_min": float(np.min(deltas)),
            "delta_max": float(np.max(deltas)),
            "delta_spread": float(np.max(deltas) - np.min(deltas)),
            "delta_per_fold": {
                f"{record['repeat']}.{record['fold']}": record["delta"] for record in records
            },
        }

    seed_repeats: dict[int, list] = {}
    for seed in seeds:
        repeats = []
        for repeat in sorted(seed_tables[seed]):
            entry = {"repeat": int(repeat)}
            for family in PRIMARY_FAMILIES:
                entry[family] = pd.concat(
                    seed_tables[seed][repeat][family], ignore_index=True
                )
            repeats.append(entry)
        seed_repeats[seed] = repeats
    primary_sensitivity = initialization_primary_sensitivity(seed_repeats)

    donor_predictions = {
        str(seed): {
            str(repeat): {
                family: pd.concat(frames, ignore_index=True).to_dict(orient="records")
                for family, frames in families.items()
            }
            for repeat, families in sorted(seed_tables[seed].items())
        }
        for seed in seeds
    }

    delta_means = {seed: seed_summary[seed]["delta_mean"] for seed in seeds}
    return {
        "data_mode": "real_development_frozen_fold_faithfulness",
        "scientific_claim_allowed": acceptance.scientific_claim_allowed,
        "pilot": not acceptance.scientific_claim_allowed,
        "final_internal_estimate": False,
        "external_evaluation_performed": False,
        "acceptance": acceptance.to_dict(),
        "n_folds_run": len(per_fold),
        "input_fingerprints": fingerprints,
        "region_set_fingerprint": {
            "path": str(regions_path),
            "union_sha256": region_sets["union_sha256"],
            "n_union_regions": region_sets["n_union_regions"],
        },
        "per_fold": per_fold,
        "donor_predictions": donor_predictions,
        "interventions": interventions,
        "initialization_sensitivity": {
            "seeds": seeds,
            "families": list(PRIMARY_FAMILIES),
            "primary_estimand": primary_sensitivity,
            "per_fold_descriptive": seed_summary,
            "delta_mean_spread_across_seeds": initialization_seed_spread(delta_means),
            "cross_attention_mean_spread_across_seeds": initialization_seed_spread(
                {seed: seed_summary[seed]["cross_attention_mean"] for seed in seeds}
            ),
            "token_concat_mean_spread_across_seeds": initialization_seed_spread(
                {seed: seed_summary[seed]["token_concat_mean"] for seed in seeds}
            ),
            "note": (
                "The initialization-sensitivity claim uses the same pooled donor-level "
                "estimand as the primary contrast: donor predictions are pooled across "
                "each repeat's held-out folds, each repeat's cross-attention minus "
                "token-concat donor balanced accuracy is averaged across repeats, and "
                "donors are resampled for the interval (primary_estimand). "
                "per_fold_descriptive.delta_mean is the mean across folds of per-fold "
                "balanced accuracies, which is a different estimand retained only for "
                "description and must not be used as the seed-sensitivity claim."
            ),
        },
        "limitations": [
            "Internal development folds only; external paired data were not accessed.",
            "Interventions are held-out manipulation evidence, not causal biology.",
            "Raw-count standard scaling; the accepted normalization is not separately frozen.",
            "A zero seed spread is not a stability guarantee beyond the seeds actually run.",
            "Predictions must not be used to select outcome-favourable donors.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/paired_multiome.json")
    parser.add_argument("--h5ad", default=DEFAULT_H5AD)
    parser.add_argument("--atac-matrix", default=str(ROOT / DEFAULT_ATAC))
    parser.add_argument("--region-sets", default=str(ROOT / DEFAULT_REGIONS))
    parser.add_argument("--init-seeds", type=int, nargs="+", default=list(DEFAULT_INIT_SEEDS))
    parser.add_argument(
        "--acceptance-requirements",
        type=Path,
        default=ROOT / "configs/real_paired_acceptance_2026-09-21.json",
    )
    parser.add_argument("--acceptance-manifest", type=Path, default=None)
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
        "real_paired_frozen_faithfulness",
        lambda: faithfulness_frozen_run(
            protocol,
            args.h5ad,
            args.atac_matrix,
            args.region_sets,
            args.output_dir,
            tuple(args.init_seeds),
            args.acceptance_requirements,
            args.acceptance_manifest,
        ),
        cells_per_donor_cap=protocol.cell_cap,
        disk_path=args.output_dir,
        notes="Frozen-fold faithfulness and initialization sensitivity on CPU; not external",
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
    donor_predictions = report.pop("donor_predictions")
    (args.output_dir / "donor_predictions.json").write_text(
        json.dumps(donor_predictions, indent=2, default=str) + "\n"
    )
    (args.output_dir / "run.json").write_text(json.dumps(report, indent=2, default=str) + "\n")

    sensitivity = report["initialization_sensitivity"]
    primary = sensitivity["primary_estimand"]
    lines = [
        "# Frozen-fold faithfulness and initialization sensitivity",
        "",
        "Internal development folds only. External paired data were not accessed.",
        "",
        f"- Folds: {report['n_folds_run']} (5 repeats x 5 donor-isolated folds).",
        f"- Init seeds: {sensitivity['seeds']} (donor splits held fixed).",
        f"- Primary estimand delta (pooled donor, cross-attention minus token-concat) "
        f"per seed: {primary['estimate_spread']['scores']} "
        f"(spread {primary['estimate_spread']['spread']}, "
        f"margin {primary['per_seed'][sensitivity['seeds'][0]]['practical_margin']}).",
        f"- Descriptive per-fold balanced-accuracy mean per seed (different estimand): "
        f"{sensitivity['delta_mean_spread_across_seeds']['scores']} "
        f"(spread {sensitivity['delta_mean_spread_across_seeds']['spread']}).",
        "",
        "Held-out interventions, mean donor balanced accuracy drop across folds:",
    ]
    for family, table in report["interventions"].items():
        lines.append(f"- {family}:")
        for name, row in table.items():
            drop = row["donor_balanced_accuracy_drop_mean"]
            lines.append(
                f"  - {name}: drop {drop} over {row['n_folds_measured']} measured "
                f"/ {row['n_folds_not_applicable']} not-applicable folds"
            )
    lines.extend(
        [
            "",
            "See run.json for the full per-family intervention table and per-seed records;",
            "per_fold.json lists each fold's training-only region hash;",
            "donor_predictions.json stores donor-level probabilities per seed/repeat/family.",
        ]
    )
    (args.output_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    print(args.output_dir / "SUMMARY.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
