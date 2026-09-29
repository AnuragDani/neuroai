"""N14 held-out nuisance probes against accepted ladder_v2 fold models.

For R1/R2/R3 (CA and TC): extract outer-train/test cell embeddings, fit
within-disease LogisticRegression probes for library and batch_seq, score on
test cells whose nuisance class was seen in train, and report QC linear R² plus
fold donor BA. Apply plan §4.2 R2 rejection (probe drop < 5 points or BA drop
> 0.05).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from p22.data.group_splits import iter_repeated_stratified_group_folds
from p22.data.nn_fold import prepare_nn_fold
from p22.data.nn_inputs import load_nn_inputs, region_indices
from p22.eval.metrics import balanced_accuracy
from p22.eval.nn_factory import build_arm
from p22.eval.nuisance_probe import (
    decide_r2_rejection,
    held_out_within_label_probe_accuracy,
    held_out_within_label_qc_r2,
)
from p22.models.fusion import VIEW_A, VIEW_B

_LADDER_V2_ROOT = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v2"
)
_DEFAULT_ARMS = ("R1_ca", "R1_tc", "R2_ca", "R2_tc", "R3_ca", "R3_tc")
_N_LIBRARY = 37
_N_BATCH = 12
_CHUNK = 2048


def _dummy_cell_meta(n: int = 8) -> dict[str, np.ndarray]:
    return {
        "labels": np.zeros(n, dtype=np.int64),
        "library": np.zeros(n, dtype=np.int64),
        "batch": np.zeros(n, dtype=np.int64),
        "qc": np.zeros((n, 5), dtype=np.float32),
    }


def _load_fold_model(
    arm: str,
    widths: Mapping[str, Any],
    grid: Mapping[str, Any],
    state_path: Path,
) -> nn.Module:
    cfg = dict(grid)
    cfg["cell_meta"] = _dummy_cell_meta()
    model, _aux, _trainer = build_arm(arm, widths, cfg)
    state = torch.load(state_path, map_location="cpu", weights_only=True)
    missing, unexpected = model.load_state_dict(state, strict=True)
    if missing or unexpected:
        raise RuntimeError(
            f"state_dict mismatch for {state_path}: missing={missing} unexpected={unexpected}"
        )
    model.eval()
    return model


def _embed_cells(
    model: nn.Module, views: Mapping[str, np.ndarray], chunk: int = _CHUNK
) -> np.ndarray:
    n = int(next(iter(views.values())).shape[0])
    if n == 0:
        return np.zeros((0, int(model.dim)), dtype=np.float32)
    pieces: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, n, chunk):
            batch = {
                key: torch.as_tensor(value[start : start + chunk], dtype=torch.float32)
                for key, value in views.items()
            }
            pieces.append(model.embed(batch).cpu().numpy())
    return np.concatenate(pieces, axis=0)


def _donor_ba_from_fold(fold_rec: Mapping[str, Any]) -> float | None:
    y = np.asarray(fold_rec["donor_labels"], dtype=int)
    p = np.asarray(fold_rec["donor_probabilities"], dtype=np.float64)
    pred = (p >= 0.5).astype(int)
    value = balanced_accuracy(y, pred).value
    return float(value) if value is not None else None


def evaluate_fold(
    *,
    run_dir: Path,
    arm: str,
    repeat: int,
    fold: int,
    inputs,
    train_rows: np.ndarray,
    holdout_rows: np.ndarray,
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    with open(protocol["representation"]["atac"]["region_set_config"]) as handle:
        atac_regions = json.load(handle)
    fold_regions = None
    for item in atac_regions["per_fold"]:
        if item["repeat"] == repeat and item["fold"] == fold:
            fold_regions = item["regions"]
            break
    if fold_regions is None:
        raise ValueError(f"missing region set for r{repeat}_f{fold}")
    region_rows = region_indices(inputs, fold_regions)

    evidence_path = run_dir / "models" / arm / f"r{repeat}_f{fold}.json"
    state_path = run_dir / "models" / arm / f"r{repeat}_f{fold}.pt"
    fold_path = run_dir / "folds" / f"r{repeat}_f{fold}_{arm}.json"
    if not state_path.exists():
        raise FileNotFoundError(state_path)
    saved_evidence = json.loads(evidence_path.read_text())
    fold_rec = json.loads(fold_path.read_text())

    fold_arrays = prepare_nn_fold(
        inputs,
        train_rows,
        holdout_rows,
        region_rows,
        n_hvg=protocol["representation"]["rna"].get("n_hvg", 2000),
        exclude_chr21=False,
    )
    if fold_arrays.evidence["idf_sha256"] != saved_evidence["idf_sha256"]:
        raise RuntimeError(
            f"idf_sha256 mismatch for {arm} r{repeat}_f{fold}: "
            f"{fold_arrays.evidence['idf_sha256']} != {saved_evidence['idf_sha256']}"
        )

    train_pos = fold_arrays.train_position
    test_pos = ~train_pos
    train_views = {VIEW_A: fold_arrays.rna[train_pos], VIEW_B: fold_arrays.atac[train_pos]}
    test_views = {VIEW_A: fold_arrays.rna[test_pos], VIEW_B: fold_arrays.atac[test_pos]}

    widths = {
        "n_features_a": int(fold_arrays.rna.shape[1]),
        "n_features_b": int(fold_arrays.atac.shape[1]),
        "n_library": _N_LIBRARY,
        "n_batch": _N_BATCH,
        "k_rna": 16,
        "k_atac": 8,
        "n_classes": 2,
    }
    model = _load_fold_model(arm, widths, fold_rec["best_grid_point"], state_path)
    train_emb = _embed_cells(model, train_views)
    test_emb = _embed_cells(model, test_views)

    train_labels = fold_arrays.label[train_pos]
    test_labels = fold_arrays.label[test_pos]
    train_library = fold_arrays.nuisance_codes["library"][train_pos]
    test_library = fold_arrays.nuisance_codes["library"][test_pos]
    train_batch = fold_arrays.nuisance_codes["batch_seq"][train_pos]
    test_batch = fold_arrays.nuisance_codes["batch_seq"][test_pos]
    train_qc = fold_arrays.qc[train_pos]
    test_qc = fold_arrays.qc[test_pos]

    library_acc = held_out_within_label_probe_accuracy(
        train_emb, train_labels, train_library, test_emb, test_labels, test_library
    )
    batch_acc = held_out_within_label_probe_accuracy(
        train_emb, train_labels, train_batch, test_emb, test_labels, test_batch
    )
    qc_r2 = held_out_within_label_qc_r2(
        train_emb, train_labels, train_qc, test_emb, test_labels, test_qc
    )
    probe_vals = [v for v in (library_acc, batch_acc) if v is not None]
    primary_probe = float(np.mean(probe_vals)) if probe_vals else None
    donor_ba = _donor_ba_from_fold(fold_rec)

    return {
        "arm": arm,
        "repeat": repeat,
        "fold": fold,
        "n_train_cells": int(train_pos.sum()),
        "n_test_cells": int(test_pos.sum()),
        "library_accuracy": library_acc,
        "batch_accuracy": batch_acc,
        "primary_probe_accuracy": primary_probe,
        "qc_r2": qc_r2,
        "donor_ba": donor_ba,
        "parameter_count": int(fold_rec["parameter_count"]),
        "idf_sha256": fold_arrays.evidence["idf_sha256"],
    }


def _mean_or_none(values: Sequence[float | None]) -> float | None:
    kept = [float(v) for v in values if v is not None]
    if not kept:
        return None
    return float(np.mean(kept))


def _summarize_arm(rows: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    arm_rows = [row for row in rows if row["arm"] == arm]
    return {
        "arm": arm,
        "n_folds": len(arm_rows),
        "library_accuracy": _mean_or_none([r["library_accuracy"] for r in arm_rows]),
        "batch_accuracy": _mean_or_none([r["batch_accuracy"] for r in arm_rows]),
        "primary_probe_accuracy": _mean_or_none(
            [r["primary_probe_accuracy"] for r in arm_rows]
        ),
        "qc_r2": _mean_or_none([r["qc_r2"] for r in arm_rows]),
        "donor_ba": _mean_or_none([r["donor_ba"] for r in arm_rows]),
        "parameter_count": (
            int(arm_rows[0]["parameter_count"]) if arm_rows else None
        ),
    }


def _pair_decisions(summaries: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
    decisions: dict[str, Any] = {}
    for fusion in ("ca", "tc"):
        r1 = summaries.get(f"R1_{fusion}")
        r2 = summaries.get(f"R2_{fusion}")
        if (
            r1 is None
            or r2 is None
            or r1["primary_probe_accuracy"] is None
            or r2["primary_probe_accuracy"] is None
            or r1["donor_ba"] is None
            or r2["donor_ba"] is None
        ):
            decisions[fusion] = {
                "decision": "R2_UNEVALUATED",
                "reason": "missing R1/R2 probe or BA",
            }
            continue
        decisions[fusion] = decide_r2_rejection(
            r1_probe_accuracy=r1["primary_probe_accuracy"],
            r2_probe_accuracy=r2["primary_probe_accuracy"],
            r1_donor_ba=r1["donor_ba"],
            r2_donor_ba=r2["donor_ba"],
        )
        decisions[fusion]["r1_arm"] = f"R1_{fusion}"
        decisions[fusion]["r2_arm"] = f"R2_{fusion}"
        decisions[fusion]["r1_primary_probe"] = r1["primary_probe_accuracy"]
        decisions[fusion]["r2_primary_probe"] = r2["primary_probe_accuracy"]
        decisions[fusion]["r1_donor_ba"] = r1["donor_ba"]
        decisions[fusion]["r2_donor_ba"] = r2["donor_ba"]
    return decisions


def _overall_decision(
    pair_decisions: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    labels: list[str] = []
    rejected_any = False
    unevaluated = False
    for _fusion, row in pair_decisions.items():
        decision = row.get("decision")
        if decision == "R2_UNEVALUATED":
            unevaluated = True
            continue
        if decision == "R2_REJECTED":
            rejected_any = True
        for tag in row.get("labels", []):
            if tag not in labels:
                labels.append(tag)
    if unevaluated and not pair_decisions:
        overall = "R2_UNEVALUATED"
    elif unevaluated and rejected_any:
        overall = "R2_REJECTED"
    elif unevaluated:
        overall = "R2_UNEVALUATED"
    elif rejected_any:
        overall = "R2_REJECTED"
    else:
        overall = "R2_ACCEPTED"
    n_lib = sum(1 for row in rows if row.get("library_accuracy") is not None)
    return {
        "r2_rejection_decision": overall,
        "labels": labels,
        "by_fusion": dict(pair_decisions),
        "primary_probe_definition": (
            "Mean of held-out within-disease library and batch_seq LogisticRegression "
            "accuracies when both are scorable; otherwise the scorable subset. "
            f"library was scorable on {n_lib}/{len(rows)} fold-arm rows "
            "(donor-held-out libraries are almost always unseen within disease)."
        ),
        "rule": (
            "R2 rejected if held-out within-disease nuisance-probe accuracy "
            "(mean of library and batch_seq when both scorable; else batch_seq) "
            "does not drop ≥ 5 points vs R1, OR donor BA drops > 0.05 vs R1 "
            "(plan §4.2 / decision_tree N14)."
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=_LADDER_V2_ROOT)
    parser.add_argument("--out", type=Path, default=Path("docs/nn_v2"))
    parser.add_argument("--protocol", default="configs/nn_protocol_v2_2026-09-23.json")
    parser.add_argument("--inputs-config", default="configs/nn_inputs_2026-09-23.json")
    parser.add_argument("--arms", default=",".join(_DEFAULT_ARMS))
    parser.add_argument("--smoke", action="store_true", help="Only repeat 0 fold 0")
    args = parser.parse_args(argv)

    torch.set_num_threads(1)
    run_dir = args.run.resolve()
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    protocol = json.loads(Path(args.protocol).read_text())
    input_manifest = json.loads(Path(args.inputs_config).read_text())

    inputs = load_nn_inputs(
        input_manifest["inputs"]["h5ad"]["path"],
        input_manifest["inputs"]["atac_tiebreak_counts"]["path"],
        protocol["sampling"]["cap_per_donor"],
        protocol["sampling"]["seed"],
        union_bed=input_manifest["inputs"]["tracked_union_bed"]["path"],
    )
    donors = inputs.metadata["donor_id"].to_numpy()
    labels = (inputs.metadata["disease"] == "complete trisomy 21").astype(int).to_numpy()
    splits = list(
        iter_repeated_stratified_group_folds(
            donors,
            labels,
            n_repeats=protocol["splits"]["n_repeats"],
            n_folds=protocol["splits"]["n_folds"],
            base_seed=protocol["splits"]["split_seed"],
        )
    )
    if args.smoke:
        splits = [s for s in splits if s.repeat == 0 and s.fold == 0]

    rows: list[dict[str, Any]] = []
    for split in splits:
        for arm in arms:
            print(f"N14 {arm} r{split.repeat}_f{split.fold}", flush=True)
            rows.append(
                evaluate_fold(
                    run_dir=run_dir,
                    arm=arm,
                    repeat=split.repeat,
                    fold=split.fold,
                    inputs=inputs,
                    train_rows=split.train_index,
                    holdout_rows=split.test_index,
                    protocol=protocol,
                )
            )

    arm_summaries = {arm: _summarize_arm(rows, arm) for arm in arms}
    pair_decisions = _pair_decisions(arm_summaries)
    decision = _overall_decision(pair_decisions, rows)
    payload = {
        "task": "N14",
        "title": "Nuisance-probe diagnostics (R2 rejection rule)",
        "status": "DONE" if decision["r2_rejection_decision"] != "R2_UNEVALUATED" else "BLOCKED",
        "source_run": str(run_dir),
        "arms": arms,
        "smoke": bool(args.smoke),
        "n_fold_rows": len(rows),
        "arm_summaries": list(arm_summaries.values()),
        "decision": decision,
        "folds": rows if args.smoke else [],
        "acceptance": {
            "r2_rejection_decision": decision["r2_rejection_decision"],
            "rule": decision["rule"],
        },
    }
    # Keep full fold table for non-smoke too (needed for audit); omit only if huge.
    if not args.smoke:
        payload["folds"] = rows

    args.out.mkdir(parents=True, exist_ok=True)
    out_json = args.out / (
        "nuisance_probe_smoke.json" if args.smoke else "nuisance_probe.json"
    )
    out_json.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        json.dumps(
            {
                "wrote": str(out_json),
                "decision": decision["r2_rejection_decision"],
                "labels": decision["labels"],
                "n_fold_rows": len(rows),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
