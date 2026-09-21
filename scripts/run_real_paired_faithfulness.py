"""Held-out faithfulness and initialization sensitivity for the real paired pilot.

This extends the real paired pilot (:mod:`scripts.run_real_paired_pilot`) with the
two evidence items the pilot omitted:

* **faithfulness** — the seven held-out interventions (clamp to the training mean,
  permutation within donor, branch ablation, fixed uniform route) scored with the
  donor-level balanced accuracy used by the primary estimand, on the held-out test
  donors only; and
* **initialization-seed sensitivity** — the primary cross-attention vs matched
  token-concat contrast re-fit under several model initialization seeds while the
  donor split is held fixed.

It remains a **pilot**: one outer fold, one donor split. It is not a final estimate,
not external validation, and its predictions must not be used to select
outcome-favourable donors.
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

import pandas as pd  # noqa: E402
import torch  # noqa: E402

from p22.data.group_splits import (  # noqa: E402
    aggregate_donor_probabilities,
    iter_repeated_stratified_group_folds,
    validate_group_folds,
)
from p22.data.resources import environment_record, measure_stage  # noqa: E402
from p22.eval.metrics import balanced_accuracy  # noqa: E402
from p22.eval.multiome_protocol import MultiomeProtocol, paired_comparison  # noqa: E402
from p22.eval.multiome_runner import (  # noqa: E402
    model_inputs,
    paired_model,
    prepare_paired_fold,
)
from p22.eval.paired_faithfulness import (  # noqa: E402
    initialization_seed_spread,
    run_donor_interventions,
)
from p22.models.fusion import VIEW_A, VIEW_B  # noqa: E402
from p22.training.loop import predict, train_model  # noqa: E402
from run_real_paired_pilot import (  # noqa: E402
    DEFAULT_ATAC,
    DEFAULT_H5AD,
    load_development_inputs,
)

INTERVENTION_FAMILIES = ("rna_atac_concat", "gated_fusion", "token_concat", "cross_attention")
PRIMARY_FAMILIES = ("cross_attention", "token_concat")
DEFAULT_INIT_SEEDS = (0, 1, 2)


def _fold_indices(metadata, protocol):
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
    outer = folds[0]
    training = metadata.iloc[outer.train_index]
    inner = next(
        iter_repeated_stratified_group_folds(
            training.donor_id, training.label, n_repeats=1, n_folds=3, base_seed=outer.split_seed
        )
    )
    indices = {
        "train": outer.train_index[inner.train_index],
        "val": outer.train_index[inner.test_index],
        "test": outer.test_index,
    }
    return outer, indices


def _donor_scores(model, views, rows, labels, donors):
    _, probabilities = predict(model, {key: value[rows] for key, value in views.items()})
    table = aggregate_donor_probabilities(probabilities[:, 1], donors[rows])
    truth = pd.Series(labels[rows], index=donors[rows]).groupby(level=0).first()
    table["label"] = table.donor_id.map(truth).astype(int)
    metric = balanced_accuracy(table.label, table.prediction)
    return table, metric


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


def faithfulness_run(protocol, h5ad_path, atac_path, output_dir, init_seeds=DEFAULT_INIT_SEEDS):
    views, metadata, fingerprints = load_development_inputs(h5ad_path, atac_path, protocol)
    outer, indices = _fold_indices(metadata, protocol)
    transformed, evidence = prepare_paired_fold(views, metadata, indices, protocol)
    labels = metadata.label.to_numpy()
    donors = metadata.donor_id.astype(str).to_numpy()
    train, val, test = (indices[name] for name in ("train", "val", "test"))

    models, intervention_rows, donor_scores = {}, {}, {}
    for name in INTERVENTION_FAMILIES:
        model = _fit(name, transformed, protocol, labels, donors, indices)
        models[name] = model
        table, metric = _donor_scores(model, transformed, test, labels, donors)
        donor_scores[name] = {
            "donor_balanced_accuracy": metric.value,
            "n_donors": int(len(table)),
            "n_control": int((table.label == 0).sum()),
            "n_positive": int((table.label == 1).sum()),
        }
        test_views = {key: value[test] for key, value in transformed.items()}
        train_views = {key: value[train] for key, value in transformed.items()}
        intervention_rows[name] = run_donor_interventions(
            model, test_views, train_views, labels[test], donors[test], seed=protocol.model_seed
        )

    seed_scores = {int(seed): {} for seed in sorted({*init_seeds, protocol.model_seed})}
    for seed in sorted(seed_scores):
        seed_protocol = (
            protocol if seed == protocol.model_seed else replace(protocol, model_seed=seed)
        )
        for name in PRIMARY_FAMILIES:
            model = (
                models[name]
                if seed == protocol.model_seed
                else _fit(name, transformed, seed_protocol, labels, donors, indices)
            )
            _, metric = _donor_scores(model, transformed, test, labels, donors)
            seed_scores[seed][name] = metric.value

    primary_tables = {}
    for name in PRIMARY_FAMILIES:
        table, _ = _donor_scores(models[name], transformed, test, labels, donors)
        primary_tables[name] = table
    comparison = paired_comparison(
        primary_tables["cross_attention"], primary_tables["token_concat"]
    )
    seed_deltas = {
        int(seed): float(seed_scores[seed]["cross_attention"] - seed_scores[seed]["token_concat"])
        for seed in seed_scores
    }
    return {
        "data_mode": "real_development_pilot_faithfulness",
        "scientific_claim_allowed": False,
        "pilot": True,
        "final_estimate": False,
        "external_evaluation_performed": False,
        "n_folds_run": 1,
        "input_fingerprints": fingerprints,
        "fold": outer.to_dict(),
        "indices_sizes": {name: int(len(value)) for name, value in indices.items()},
        "preprocessing_evidence": evidence,
        "donor_scores": donor_scores,
        "interventions": intervention_rows,
        "primary_comparison": comparison,
        "initialization_sensitivity": {
            "families": list(PRIMARY_FAMILIES),
            "per_seed": seed_scores,
            "delta_per_seed": seed_deltas,
            "cross_attention_spread": initialization_seed_spread(
                {seed: seed_scores[seed]["cross_attention"] for seed in seed_scores}
            ),
            "token_concat_spread": initialization_seed_spread(
                {seed: seed_scores[seed]["token_concat"] for seed in seed_scores}
            ),
            "delta_spread": initialization_seed_spread(seed_deltas),
        },
        "limitations": [
            "Pilot only: one outer fold and one donor split.",
            "Interventions are held-out manipulation evidence, not causal biology.",
            "Raw-count standard scaling; the accepted normalization is not frozen.",
            "Predictions must not be used to select outcome-favourable donors.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/paired_multiome.json")
    parser.add_argument("--h5ad", default=DEFAULT_H5AD)
    parser.add_argument("--atac-matrix", default=str(ROOT / DEFAULT_ATAC))
    parser.add_argument("--init-seeds", type=int, nargs="+", default=list(DEFAULT_INIT_SEEDS))
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
        "real_paired_faithfulness",
        lambda: faithfulness_run(
            protocol, args.h5ad, args.atac_matrix, args.output_dir, tuple(args.init_seeds)
        ),
        cells_per_donor_cap=protocol.cell_cap,
        disk_path=args.output_dir,
        notes="Real pilot faithfulness/seed sensitivity on CPU; not final or external",
    )
    report.update(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        protocol=asdict(protocol),
        protocol_sha256=protocol.fingerprint,
        environment=environment_record(),
        resources=resource.to_dict(),
    )
    (args.output_dir / "run.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    comparison = report["primary_comparison"]
    sensitivity = report["initialization_sensitivity"]
    summary = [
        "# Real paired pilot: faithfulness and initialization sensitivity",
        "",
        "Pilot only. Not a final estimate and not external validation.",
        "",
        f"- Held-out test donors: {report['donor_scores']['cross_attention']['n_donors']} "
        f"({report['donor_scores']['cross_attention']['n_control']} control / "
        f"{report['donor_scores']['cross_attention']['n_positive']} DS).",
        f"- Cross-attention minus token-concat donor balanced accuracy: "
        f"{comparison['estimate']} (interval {comparison['interval']}).",
        f"- Cross-attention donor balanced accuracy across init seeds "
        f"{sensitivity['cross_attention_spread']['seeds']}: "
        f"{sensitivity['cross_attention_spread']['scores']} "
        f"(spread {sensitivity['cross_attention_spread']['spread']}).",
        f"- Primary delta across init seeds: {sensitivity['delta_per_seed']} "
        f"(spread {sensitivity['delta_spread']['spread']}).",
        "",
        "Interventions are per-model held-out manipulations; see run.json for the full",
        "seven-row table per family, including not-applicable uniform-route rows.",
    ]
    (args.output_dir / "SUMMARY.md").write_text("\n".join(summary) + "\n")
    print(args.output_dir / "SUMMARY.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
