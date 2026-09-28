#!/usr/bin/env python3
"""N21 gene-activity secondary ladder (GA_ca / GA_tc + gene-activity view-B arms).

Uses the N20 gene-activity matrix as ATAC view B. Gene-aligned arms share a
500-gene label-free dispersion subset (decision_tree N21 amendment). Primary
ladder remains N10; this run is secondary only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import resource
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import torch

import run_nn_v2_comparison as comparison
from p22.data.group_splits import iter_repeated_stratified_group_folds
from p22.data.nn_fold import _atac_tfidf, _rna_lognorm
from p22.data.nn_inputs import load_nn_inputs, prepare_nn_fold
from p22.eval import nn_factory
from p22.eval.repeated_comparison import repeated_model_accuracy, repeated_primary_contrast
from p22.models.fusion import VIEW_A, VIEW_B
from p22.models.gene_aligned import (
    GeneAlignedCrossAttention,
    GeneAlignedTokenConcat,
    build_genomic_attention_mask,
)
from p22.models.mil import MILWrapper
from p22.training.loop import predict
from p22.training.mil_loop import predict_mil

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ATAC = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/"
    "gene_activity/counts/counts.npz"
)
DEFAULT_BED = ROOT / "configs/nn_gene_activity_2026-09-23.bed"
DEFAULT_GENE_CFG = ROOT / "configs/nn_gene_activity_2026-09-23.json"
DEFAULT_OUT = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/gene_activity_v2"
)
GA_ARMS = ("GA_ca", "GA_tc")
DEFAULT_ARMS = ["GA_ca", "GA_tc", "R3_ca", "R3_tc", "logreg_concat"]
GA_TOKEN_CAP = 500


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def select_ga_genes(gene_cfg: Path, cap: int = GA_TOKEN_CAP) -> dict:
    """Top-`cap` panel genes by stored label-free dispersion_z (stable argsort)."""
    cfg = json.loads(gene_cfg.read_text())
    genes = list(cfg["genes"])
    z = np.asarray([float(g["dispersion_z"]) for g in genes], dtype=np.float64)
    order = np.argsort(-z, kind="stable")[:cap]
    selected = [genes[int(i)] for i in order]
    return {
        "ga_token_cap": cap,
        "panel_n_genes": len(genes),
        "ga_n_genes": len(selected),
        "selection": "highest_label_free_dispersion_z",
        "dispersion_z_min": float(min(g["dispersion_z"] for g in selected)),
        "dispersion_z_max": float(max(g["dispersion_z"] for g in selected)),
        "amendment_reason": (
            "gene-aligned CA at full panel is memory/runtime heavy on CPU; "
            "decision_tree N21 500-gene amendment"
        ),
        "genes": selected,
        "names": [g["gene_name"] for g in selected],
        "chromosomes": [g["chrom"] for g in selected],
        "starts": [int(g["window_start"]) for g in selected],
    }


def _build_ga_arm(arm_name: str, widths: dict, cfg: dict | None, attn_mask: torch.Tensor | None):
    options = {**nn_factory.DEFAULT_ARCH, **nn_factory.DEFAULT_TRAIN, **dict(cfg or {})}
    num_genes = int(widths["n_features_a"])
    if arm_name == "GA_ca":
        base = GeneAlignedCrossAttention(
            num_genes=num_genes,
            dim=options["embed_dim"],
            heads=options["n_heads"],
            n_classes=int(widths.get("n_classes", 2)),
            dropout=options["dropout"],
            attn_mask=attn_mask,
        )
    else:
        base = GeneAlignedTokenConcat(
            num_genes=num_genes,
            dim=options["embed_dim"],
            n_classes=int(widths.get("n_classes", 2)),
            dropout=options["dropout"],
        )
    fused_dim = 2 * int(options["embed_dim"])
    model = MILWrapper(base, dim=fused_dim, attn_dim=options["attn_dim"])
    aux = []
    _adv, loss = nn_factory._adversary(model, fused_dim, widths, options)
    aux.append(loss)
    aux.append(nn_factory._add_pairing(model, options["embed_dim"], options))
    return model, tuple(aux), nn_factory._mil_trainer(tuple(aux), options)


_original_build_arm = nn_factory.build_arm
_ATTN_MASK: torch.Tensor | None = None


def _patched_build_arm(arm_name, widths, cfg=None):
    if arm_name in GA_ARMS:
        return _build_ga_arm(arm_name, widths, cfg, _ATTN_MASK)
    return _original_build_arm(arm_name, widths, cfg)


nn_factory.build_arm = _patched_build_arm
nn_factory.ARM_NAMES = tuple(list(nn_factory.ARM_NAMES) + list(GA_ARMS))


def _panel_name_to_region_index(bed_path: Path) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for i, line in enumerate(bed_path.read_text().splitlines()):
        if not line.strip():
            continue
        name = line.split("\t")[3]
        mapping[name] = i
    return mapping


def worker_task(
    out_dir,
    arm_name,
    repeat,
    fold,
    train_rows,
    test_rows,
    inputs,
    protocol,
    exclude_chr21,
    model_seed,
    cfg,
    selected_names,
    selected_chroms,
    selected_starts,
    bed_path,
):
    global _ATTN_MASK
    try:
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        t0 = time.time()

        region_rows = np.arange(len(inputs.regions), dtype=np.int64)
        fold_arrays = prepare_nn_fold(
            inputs,
            train_rows,
            test_rows,
            region_rows,
            n_hvg=protocol["representation"]["rna"].get("n_hvg", 2000),
            exclude_chr21=exclude_chr21,
        )

        if arm_name in GA_ARMS:
            name_to_rna = {str(n): i for i, n in enumerate(inputs.gene_names.tolist())}
            rna_cols = [name_to_rna[n] for n in selected_names]
            name_to_region = _panel_name_to_region_index(Path(bed_path))
            atac_cols = [name_to_region[n] for n in selected_names]

            rna_norm = _rna_lognorm(inputs.rna, inputs.rna_totals)[:, rna_cols]
            rna_dense = np.asarray(rna_norm.todense(), dtype=np.float32)
            from sklearn.preprocessing import StandardScaler

            scaler = StandardScaler()
            scaler.fit(rna_dense[fold_arrays.train_position])
            fold_arrays.rna = scaler.transform(rna_dense).astype(np.float32)

            atac_raw = inputs.atac[:, atac_cols]
            atac_tfidf, _ = _atac_tfidf(atac_raw, fold_arrays.train_position)
            fold_arrays.atac = np.asarray(atac_tfidf.todense(), dtype=np.float32)

            if arm_name == "GA_ca":
                _ATTN_MASK = build_genomic_attention_mask(
                    selected_chroms, selected_starts, k=5
                )
            else:
                _ATTN_MASK = None
        else:
            _ATTN_MASK = None

        fit_donors = set(fold_arrays.evidence["fit_donors"])
        outer_train_donors = set(inputs.metadata["donor_id"].iloc[train_rows].unique())
        assert fit_donors.issubset(outer_train_donors), "Leakage detected"

        donors_train = inputs.metadata["donor_id"].iloc[train_rows].to_numpy()
        labels_train = (
            inputs.metadata["disease"].iloc[train_rows] == "complete trisomy 21"
        ).astype(int).to_numpy()
        inner_train_idx, inner_val_idx = comparison._inner_split(
            donors_train, labels_train, protocol["splits"]["split_seed"]
        )
        inner_train_pos = inner_train_idx
        inner_val_pos = inner_val_idx
        test_pos = np.arange(len(train_rows), len(train_rows) + len(test_rows))

        def _make_arm_data(pos):
            views = {VIEW_A: fold_arrays.rna[pos], VIEW_B: fold_arrays.atac[pos]}
            cell_meta = {
                "labels": fold_arrays.label[pos],
                "library": fold_arrays.nuisance_codes["library"][pos],
                "batch": fold_arrays.nuisance_codes["batch_seq"][pos],
                "qc": fold_arrays.qc[pos],
            }
            return nn_factory.ArmData(
                views=views,
                labels=fold_arrays.label[pos],
                donors=fold_arrays.donor[pos],
                cell_meta=cell_meta,
            )

        train_data = _make_arm_data(inner_train_pos)
        val_data = _make_arm_data(inner_val_pos)
        test_data = _make_arm_data(test_pos)

        widths = {
            "n_features_a": fold_arrays.rna.shape[1],
            "n_features_b": fold_arrays.atac.shape[1],
            "n_library": len(np.unique(inputs.metadata["library"])),
            "n_batch": len(np.unique(inputs.metadata["batch_seq"])),
            "k_rna": 16,
            "k_atac": 8,
            "n_classes": 2,
        }
        cfg_copy = dict(cfg)
        cfg_copy["cell_meta"] = train_data.cell_meta
        model, aux, trainer = nn_factory.build_arm(arm_name, widths, cfg_copy)

        rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        trained = trainer(model, train_data, val_data)
        rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 / 1024.0
        del rss_after

        if hasattr(trained, "predict_proba"):
            probs = trained.predict_proba(test_data.views)
            donor_probs_dict: dict[str, list[float]] = {}
            for d, p in zip(test_data.donors, probs[:, 1], strict=False):
                donor_probs_dict.setdefault(d, []).append(float(p))
            donor_ids = sorted(donor_probs_dict)
            donor_probabilities = np.array(
                [float(np.mean(donor_probs_dict[d])) for d in donor_ids]
            )
            test_predictions = {
                "donor_ids": donor_ids,
                "donor_probabilities": donor_probabilities,
            }
        elif hasattr(trained, "model") and hasattr(trained.model, "forward_bag"):
            test_predictions = predict_mil(
                trained.model, test_data.views, test_data.donors
            )
        else:
            _preds, probs = predict(trained.model, test_data.views)
            donor_probs_dict = {}
            for d, p in zip(test_data.donors, probs[:, 1], strict=False):
                donor_probs_dict.setdefault(d, []).append(float(p))
            donor_ids = sorted(donor_probs_dict)
            test_predictions = {
                "donor_ids": donor_ids,
                "donor_probabilities": np.array(
                    [float(np.mean(donor_probs_dict[d])) for d in donor_ids]
                ),
            }

        elapsed = time.time() - t0
        donor_labels_dict = {}
        for d, lab in zip(test_data.donors, test_data.labels, strict=False):
            donor_labels_dict[d] = int(lab)
        donor_labels_list = [
            donor_labels_dict[d] for d in test_predictions["donor_ids"]
        ]

        out_dir = Path(out_dir)
        model_dir = out_dir / "models" / arm_name
        model_dir.mkdir(parents=True, exist_ok=True)
        if hasattr(trained, "model"):
            torch.save(trained.model.state_dict(), model_dir / f"r{repeat}_f{fold}.pt")
        with open(model_dir / f"r{repeat}_f{fold}.json", "w") as fh:
            json.dump(fold_arrays.evidence, fh)

        record = {
            "repeat": repeat,
            "fold": fold,
            "arm": arm_name,
            "donor_ids": list(test_predictions["donor_ids"]),
            "donor_labels": donor_labels_list,
            "donor_probabilities": np.asarray(
                test_predictions["donor_probabilities"]
            ).tolist(),
            "best_grid_point": cfg,
            "inner_val_log_loss": (
                -trained.best_val_score if hasattr(trained, "best_val_score") else None
            ),
            "epochs": trained.epochs_run if hasattr(trained, "epochs_run") else 0,
            "parameter_count": (
                sum(p.numel() for p in trained.model.parameters() if p.requires_grad)
                if hasattr(trained, "model")
                else 0
            ),
            "elapsed": elapsed,
            "rss_mb": rss_mb,
            "fit_donors": list(fold_arrays.evidence["fit_donors"]),
            "n_features_a": int(fold_arrays.rna.shape[1]),
            "n_features_b": int(fold_arrays.atac.shape[1]),
            "n_library": widths["n_library"],
            "n_batch": widths["n_batch"],
        }
        out_file = out_dir / "folds" / f"r{repeat}_f{fold}_{arm_name}.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w") as fh:
            json.dump(record, fh, indent=2)
        return record, None
    except Exception as exc:  # noqa: BLE001 - surface fold failures to run record
        import traceback

        return None, f"r{repeat}_f{fold}_{arm_name}: {exc}\n{traceback.format_exc()}"


comparison.worker_task = worker_task  # noqa: A001 — patch for any shared helpers


def _load_repeats(folds_dir: Path):
    per_repeat: dict[int, dict] = {}
    arms: set[str] = set()
    for path in folds_dir.glob("*.json"):
        rec = json.loads(path.read_text())
        rep = int(rec["repeat"])
        arm = rec["arm"]
        arms.add(arm)
        per_repeat.setdefault(rep, {}).setdefault(arm, []).append(
            pd.DataFrame(
                {
                    "donor_id": rec["donor_ids"],
                    "label": rec["donor_labels"],
                    "probability": rec["donor_probabilities"],
                }
            )
        )
    repeats = []
    for rep in sorted(per_repeat):
        entry = {"repeat": rep}
        for arm, frames in per_repeat[rep].items():
            entry[arm] = pd.concat(frames, ignore_index=True)
        repeats.append(entry)
    return repeats, arms


def summarize_gene_activity(run_dir: Path, out_json: Path, out_md: Path) -> dict:
    repeats, arms = _load_repeats(run_dir / "folds")
    run_meta = json.loads((run_dir / "run.json").read_text())
    per_arm = {}
    for arm in sorted(arms):
        acc = repeated_model_accuracy(repeats, model=arm)
        per_arm[arm] = {
            "mean_ba": acc.get("mean", 0.0),
            "mean_auroc": acc.get("mean_auroc", acc.get("auroc", 0.0)),
            "n_folds": sum(1 for _ in (run_dir / "folds").glob(f"*_{arm}.json")),
        }

    primary_raw = {}
    if "GA_ca" in arms and "GA_tc" in arms:
        primary_raw = repeated_primary_contrast(repeats, model="GA_ca", reference="GA_tc")
    primary = {
        "model": primary_raw.get("model", "GA_ca"),
        "reference": primary_raw.get("reference", "GA_tc"),
        "estimate": primary_raw.get("estimate", 0.0),
        "ci": list(primary_raw.get("interval", [0.0, 0.0])),
        "margin": primary_raw.get("practical_margin", 0.07),
        "advantage": primary_raw.get("advantage_demonstrated", False),
    }
    est, ci = primary["estimate"], primary["ci"]
    if not primary_raw:
        base = "UNKNOWN"
    elif ci[0] > 0 and est >= primary["margin"]:
        base = "A_ADVANTAGE"
    elif ci[0] <= 0 <= ci[1]:
        base = "B_NULL"
    elif ci[1] < 0:
        base = "C_DISADVANTAGE"
    else:
        base = "D_SMALL_POSITIVE"
    outcome = f"GA_{base}" if base != "UNKNOWN" else "GA_UNKNOWN"

    secondary = {}
    if "R3_ca" in arms and "R3_tc" in arms:
        secondary["R3_ca_vs_R3_tc"] = repeated_primary_contrast(
            repeats, model="R3_ca", reference="R3_tc"
        )
        # make JSON-safe
        secondary["R3_ca_vs_R3_tc"] = {
            k: (list(v) if hasattr(v, "__iter__") and not isinstance(v, (str, dict)) else v)
            for k, v in secondary["R3_ca_vs_R3_tc"].items()
            if k != "per_repeat"
        }

    summary = {
        "secondary_only": True,
        "never_independent_external_validation": True,
        "run_dir": str(run_dir),
        "run": run_meta,
        "arms": sorted(arms),
        "per_arm": per_arm,
        "primary": primary,
        "outcome": outcome,
        "secondary_contrasts": secondary,
        "ga_token_selection": run_meta.get("ga_token_selection"),
        "amendment": run_meta.get("amendment"),
        "counts_sha256": run_meta.get("counts_sha256"),
        "bed_sha256": run_meta.get("bed_sha256"),
        "protocol_sha256": run_meta.get("protocol_sha256"),
        "faithfulness_ga": run_meta.get("faithfulness_ga", "PENDING"),
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2, default=str) + "\n")

    lines = [
        "# Gene-activity secondary ladder (N21)",
        "",
        f"Outcome: **{outcome}** (secondary only; primary remains N10 `B_NULL`).",
        f"Primary GA_ca−GA_tc estimate {primary['estimate']:.4f}, "
        f"CI [{primary['ci'][0]:.4f}, {primary['ci'][1]:.4f}].",
        "",
        "Never claim this as independent external validation.",
        "",
        "| Arm | mean BA | n folds |",
        "|---|---|---|",
    ]
    for arm, stats in per_arm.items():
        lines.append(f"| {arm} | {stats['mean_ba']:.4f} | {stats['n_folds']} |")
    lines.extend(
        [
            "",
            f"Run directory: `{run_dir}`",
            f"Token selection: top {run_meta.get('ga_n_genes', GA_TOKEN_CAP)} / "
            f"{run_meta.get('n_genes', 548)} by label-free dispersion_z.",
            f"Source hashes: counts `{run_meta.get('counts_sha256')}`, "
            f"bed `{run_meta.get('bed_sha256')}`.",
            "",
        ]
    )
    out_md.write_text("\n".join(lines))
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT / "configs/nn_protocol_v2_2026-09-23.json",
    )
    parser.add_argument(
        "--inputs-manifest",
        type=Path,
        default=ROOT / "configs/nn_inputs_2026-09-23.json",
    )
    parser.add_argument(
        "--amendment",
        type=Path,
        default=ROOT / "configs/nn_protocol_v2_amendment_gene_activity.json",
    )
    parser.add_argument("--atac-matrix", type=Path, default=DEFAULT_ATAC)
    parser.add_argument("--atac-bed", type=Path, default=DEFAULT_BED)
    parser.add_argument("--gene-config", type=Path, default=DEFAULT_GENE_CFG)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--arms", nargs="+", default=DEFAULT_ARMS)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--model-seed", type=int, default=0)
    parser.add_argument("--sampling-seed", type=int, default=22)
    parser.add_argument("--summarize-only", action="store_true")
    parser.add_argument(
        "--results-json",
        type=Path,
        default=ROOT / "docs/nn_v2/gene_activity_results.json",
    )
    parser.add_argument(
        "--results-md",
        type=Path,
        default=ROOT / "docs/nn_v2/GENE_ACTIVITY.md",
    )
    args = parser.parse_args(argv)

    if args.summarize_only:
        summary = summarize_gene_activity(args.out, args.results_json, args.results_md)
        print(json.dumps({"outcome": summary["outcome"], "primary": summary["primary"]}, indent=2))
        return 0

    selection = select_ga_genes(args.gene_config, GA_TOKEN_CAP)
    # Verify against the existing gene_activity_v2 extremes when present.
    expected_min, expected_max = -0.41207420616229146, 14.044904881960885
    if not (
        np.isclose(selection["dispersion_z_min"], expected_min)
        and np.isclose(selection["dispersion_z_max"], expected_max)
    ):
        raise RuntimeError(
            f"GA gene selection extremes mismatch: got "
            f"{selection['dispersion_z_min']}, {selection['dispersion_z_max']}"
        )

    protocol = json.loads(args.protocol.read_text())
    manifest = json.loads(args.inputs_manifest.read_text())
    h5ad = manifest["inputs"]["h5ad"]["path"]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "folds").mkdir(parents=True, exist_ok=True)

    logging.info("Loading NN inputs with gene-activity ATAC…")
    inputs = load_nn_inputs(
        h5ad,
        str(args.atac_matrix),
        protocol["sampling"]["cap_per_donor"],
        args.sampling_seed,
        union_bed=str(args.atac_bed),
    )

    metadata = inputs.metadata
    donors = metadata["donor_id"].to_numpy()
    labels = (metadata["disease"] == "complete trisomy 21").astype(int).to_numpy()
    splits = list(
        iter_repeated_stratified_group_folds(
            donors,
            labels,
            n_repeats=args.repeats,
            n_folds=args.folds,
            base_seed=protocol["splits"]["split_seed"],
        )
    )

    tasks = []
    for split in splits:
        for arm in args.arms:
            out_file = args.out / "folds" / f"r{split.repeat}_f{split.fold}_{arm}.json"
            if args.resume and out_file.exists():
                continue
            cfg = {**protocol["architecture"], **protocol["training"]}
            cfg["seed"] = args.model_seed
            cfg["model_seed"] = args.model_seed
            cfg["device"] = "cpu"
            cfg["torch_threads_per_worker"] = 1
            cfg["max_workers"] = args.workers
            tasks.append(
                (arm, split.repeat, split.fold, split.train_index, split.test_index, cfg)
            )

    expected = len(splits) * len(args.arms)
    done = expected - len(tasks) if args.resume else 0
    failures: list[str] = []
    logging.info("Scheduled %d fold-arm tasks (%d already done)", len(tasks), done)

    selected_names = selection["names"]
    selected_chroms = selection["chromosomes"]
    selected_starts = selection["starts"]

    if tasks:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = [
                executor.submit(
                    worker_task,
                    args.out,
                    arm,
                    rep,
                    fold,
                    train_rows,
                    test_rows,
                    inputs,
                    protocol,
                    False,
                    args.model_seed,
                    cfg,
                    selected_names,
                    selected_chroms,
                    selected_starts,
                    str(args.atac_bed),
                )
                for arm, rep, fold, train_rows, test_rows, cfg in tasks
            ]
            for fut in as_completed(futures):
                record, error = fut.result()
                if error:
                    logging.error(error)
                    failures.append(error.split("\n", 1)[0])
                else:
                    done += 1
                    logging.info(
                        "done %s r%s_f%s (%d/%d)",
                        record["arm"],
                        record["repeat"],
                        record["fold"],
                        done,
                        expected,
                    )

    # Preserve prior run metadata keys; refresh counts.
    prior = {}
    if (args.out / "run.json").exists():
        prior = json.loads((args.out / "run.json").read_text())
    present_arms = sorted(
        {"_".join(p.stem.split("_")[2:]) for p in (args.out / "folds").glob("*.json")}
    )
    n_done = len(list((args.out / "folds").glob("*.json")))
    run_record = {
        **prior,
        "folds_expected": max(int(prior.get("folds_expected", 0)), expected, n_done),
        "folds_done": n_done,
        "failures": failures,
        "run_dir": str(args.out.resolve()),
        "protocol": str(args.protocol.resolve()),
        "protocol_sha256": _sha256(args.protocol),
        "amendment": str(args.amendment.resolve()),
        "atac_matrix": str(args.atac_matrix.resolve()),
        "atac_bed": str(args.atac_bed.resolve()),
        "counts_sha256": _sha256(args.atac_matrix),
        "bed_sha256": _sha256(args.atac_bed),
        "n_genes": selection["panel_n_genes"],
        "ga_n_genes": selection["ga_n_genes"],
        "ga_token_selection": {
            k: selection[k]
            for k in (
                "ga_token_cap",
                "panel_n_genes",
                "ga_n_genes",
                "selection",
                "dispersion_z_min",
                "dispersion_z_max",
                "amendment_reason",
            )
        },
        "sampling_seed": args.sampling_seed,
        "model_seed": args.model_seed,
        "arms": present_arms,
        "n_library": 37,
        "n_batch": 12,
        "secondary_only": True,
    }
    (args.out / "run.json").write_text(json.dumps(run_record, indent=2) + "\n")

    summary = summarize_gene_activity(args.out, args.results_json, args.results_md)
    logging.info("Wrote %s outcome=%s", args.results_json, summary["outcome"])
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
