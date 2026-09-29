#!/usr/bin/env python3
"""V2: positive control through the full NN ladder path with all chr21 genes forced in.

Runs repeat 0 (5 folds) for ``logreg_rna`` and ``R3_tc`` using the same fold
preparation, training loop and donor aggregation as the ladder
(``run_nn_v2_comparison.worker_task``), with HVGs unioned with every chr21 gene.
Writes ``docs/nn_v2/v5/positive_control.json``.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

from p22.data.group_splits import iter_repeated_stratified_group_folds
from p22.data.nn_inputs import load_nn_inputs, prepare_nn_fold, region_indices

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = Path("configs/nn_protocol_v2_2026-09-23.json")
DEFAULT_INPUTS = Path("configs/nn_inputs_2026-09-23.json")
DEFAULT_SANITY = Path("docs/nn_v2/chr21_sanity.json")
DEFAULT_OUT = Path("docs/nn_v2/v5/positive_control.json")
ARMS = ("logreg_rna", "R3_tc")


def _load_worker():
    path = ROOT / "scripts" / "run_nn_v2_comparison.py"
    spec = importlib.util.spec_from_file_location("run_nn_v2_comparison", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def count_chr21_in_default_hvg(
    inputs,
    train_rows: np.ndarray,
    test_rows: np.ndarray,
    region_rows: np.ndarray,
    n_hvg: int,
) -> int:
    """How many chr21 genes default HVG selection keeps (no force-include)."""
    fold = prepare_nn_fold(
        inputs,
        train_rows,
        test_rows,
        region_rows,
        n_hvg=n_hvg,
        exclude_chr21=False,
    )
    chr21_ids = set(inputs.gene_ids[inputs.chr21_gene_mask()].tolist())
    return int(sum(gid in chr21_ids for gid in fold.gene_ids))


def _donor_auroc(labels: list[int], probs: list[float]) -> float:
    y = np.asarray(labels, dtype=int)
    p = np.asarray(probs, dtype=float)
    return float(roc_auc_score(y, p))


def _orientation_check(
    donor_ids: list[str],
    donor_probs: list[float],
    sanity: dict[str, Any],
) -> dict[str, Any]:
    share = {d["donor"]: float(d["chr21_fraction_pooled"]) for d in sanity["donors"]}
    xs: list[float] = []
    ys: list[float] = []
    for donor, prob in zip(donor_ids, donor_probs):
        if donor not in share:
            continue
        xs.append(float(prob))
        ys.append(share[donor])
    if len(xs) < 3:
        return {"spearman_rho": None, "n_donors": len(xs), "note": "too few donors"}
    rho, pval = spearmanr(xs, ys)
    return {
        "spearman_rho": float(rho),
        "spearman_pvalue": float(pval),
        "n_donors": len(xs),
        "chr21_share_field": "chr21_fraction_pooled",
    }


def run_positive_control(
    *,
    protocol_path: Path = DEFAULT_PROTOCOL,
    inputs_path: Path = DEFAULT_INPUTS,
    sanity_path: Path = DEFAULT_SANITY,
    out_path: Path = DEFAULT_OUT,
    out_dir: Path | None = None,
    model_seed: int = 0,
) -> dict[str, Any]:
    """Train forced-chr21 arms on repeat 0 and write the evidence JSON."""
    worker = _load_worker()
    protocol = json.loads(protocol_path.read_text())
    manifest = json.loads(inputs_path.read_text())
    sanity = json.loads(sanity_path.read_text())
    inputs = load_nn_inputs(
        manifest["inputs"]["h5ad"]["path"],
        manifest["inputs"]["atac_tiebreak_counts"]["path"],
        protocol["sampling"]["cap_per_donor"],
        protocol["sampling"]["seed"],
        union_bed=manifest["inputs"]["tracked_union_bed"]["path"],
    )
    donors = inputs.metadata["donor_id"].to_numpy()
    labels = (inputs.metadata["disease"] == "complete trisomy 21").astype(int).to_numpy()
    splits = [
        s
        for s in iter_repeated_stratified_group_folds(
            donors,
            labels,
            n_repeats=1,
            n_folds=5,
            base_seed=protocol["splits"]["split_seed"],
        )
        if s.repeat == 0
    ]
    if len(splits) != 5:
        raise RuntimeError(f"expected 5 folds for repeat 0, got {len(splits)}")

    with open(protocol["representation"]["atac"]["region_set_config"]) as fh:
        atac_regions = json.load(fh)
    region_by_fold = {
        (item["repeat"], item["fold"]): item["regions"] for item in atac_regions["per_fold"]
    }
    n_hvg = int(protocol["representation"]["rna"].get("n_hvg", 2000))

    run_root = out_dir or Path("reports/generated/nn_20260923/v5_positive_control")
    run_root.mkdir(parents=True, exist_ok=True)

    chr21_default: list[int] = []
    per_arm: dict[str, Any] = {}
    cfg = protocol["architecture"].copy()
    cfg.update(protocol["training"])
    cfg["seed"] = model_seed

    for arm in ARMS:
        fold_aurocs: list[float] = []
        all_ids: list[str] = []
        all_labels: list[int] = []
        all_probs: list[float] = []
        per_fold: list[dict[str, Any]] = []
        for split in splits:
            regions = region_by_fold[(split.repeat, split.fold)]
            region_rows = region_indices(inputs, regions)
            if arm == ARMS[0]:
                chr21_default.append(
                    count_chr21_in_default_hvg(
                        inputs,
                        split.train_index,
                        split.test_index,
                        region_rows,
                        n_hvg,
                    )
                )
            rec, err = worker.worker_task(
                run_root,
                arm,
                split.repeat,
                split.fold,
                split.train_index,
                split.test_index,
                inputs,
                protocol,
                False,
                model_seed,
                cfg,
                force_include_chr21=True,
            )
            if err:
                raise RuntimeError(err)
            assert rec is not None
            auroc = _donor_auroc(rec["donor_labels"], rec["donor_probabilities"])
            fold_aurocs.append(auroc)
            all_ids.extend(rec["donor_ids"])
            all_labels.extend(rec["donor_labels"])
            all_probs.extend(rec["donor_probabilities"])
            per_fold.append(
                {
                    "repeat": int(split.repeat),
                    "fold": int(split.fold),
                    "donor_auroc": auroc,
                    "n_features_rna": int(
                        json.loads(
                            (run_root / "models" / arm / f"r{split.repeat}_f{split.fold}.json")
                            .read_text()
                        )["n_hvg"]
                    ),
                }
            )
        pooled = _donor_auroc(all_labels, all_probs)
        per_arm[arm] = {
            "donor_auroc": pooled,
            "per_fold_auroc": fold_aurocs,
            "per_fold": per_fold,
            "orientation_check": _orientation_check(all_ids, all_probs, sanity),
        }

    # Gate reads top-level donor_auroc; logistic arm is the primary positive
    # control (R3_tc reported alongside). Require logreg pooled >= 0.9.
    primary = "logreg_rna"
    payload = {
        "record_type": "v5_positive_control",
        "repeat": 0,
        "n_folds": 5,
        "arms": list(ARMS),
        "force_include": "all_chr21_genes_union_hvg",
        "chr21_genes_in_hvg_default": int(round(float(np.mean(chr21_default)))),
        "chr21_genes_in_hvg_default_per_fold": chr21_default,
        "n_chr21_genes_total": int(inputs.chr21_gene_mask().sum()),
        "donor_auroc": float(per_arm[primary]["donor_auroc"]),
        "per_fold_auroc": per_arm[primary]["per_fold_auroc"],
        "orientation_check": per_arm[primary]["orientation_check"],
        "primary_arm": primary,
        "shared_path_fix": (
            "sklearn controls now fit on the full outer-train split; previously "
            "worker_task passed only the inner-train third and _control_trainer "
            "discarded val, wasting one third of training donors"
        ),
        "per_arm": per_arm,
        "run_dir": str(run_root).replace("\\", "/"),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--sanity", type=Path, default=DEFAULT_SANITY)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--model-seed", type=int, default=0)
    args = parser.parse_args(argv)
    payload = run_positive_control(
        protocol_path=args.protocol,
        inputs_path=args.inputs,
        sanity_path=args.sanity,
        out_path=args.out,
        out_dir=args.out_dir,
        model_seed=args.model_seed,
    )
    print(
        f"wrote {args.out} donor_auroc={payload['donor_auroc']:.4f} "
        f"chr21_in_hvg_default={payload['chr21_genes_in_hvg_default']}"
    )
    for arm, block in payload["per_arm"].items():
        print(f"  {arm}: pooled={block['donor_auroc']:.4f} per_fold={block['per_fold_auroc']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
