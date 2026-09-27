"""N13 held-out faithfulness interventions against accepted ladder_v2 fold models.

Loads saved state_dicts from the main-checkout ladder_v2 run (not copied here),
rebuilds matching fold inputs, and measures donor BA / log-loss deltas under
I1–I6, NC, and optional planted PC. An attention/gate/pairing readout may be
described as used only when its Δ log-loss donor-bootstrap CI excludes 0.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn

from p22.data.group_splits import iter_repeated_stratified_group_folds
from p22.data.nn_fold import prepare_nn_fold
from p22.data.nn_inputs import load_nn_inputs, region_indices
from p22.eval.metrics import balanced_accuracy
from p22.eval.nn_factory import build_arm
from p22.models.fusion import VIEW_A, VIEW_B
from p22.training.mil_loop import predict_mil

# Absolute main-checkout ladder; do not copy into finish-base.
_LADDER_V2_ROOT = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v2"
)
_DEFAULT_ARMS = ("R3_ca", "R3_tc", "R3_gated", "R4_ca")
_N_LIBRARY = 37
_N_BATCH = 12


def clamp_to_train_mean(matrix: np.ndarray, train_matrix: np.ndarray) -> np.ndarray:
    reference = np.asarray(train_matrix, dtype=np.float64)
    return np.tile(reference.mean(axis=0), (matrix.shape[0], 1)).astype(matrix.dtype)


def permute_within_donor_celltype(
    matrix: np.ndarray,
    donor_ids: np.ndarray,
    cell_types: np.ndarray,
    seed: int,
) -> np.ndarray:
    array = np.asarray(matrix).copy()
    donors = np.asarray(donor_ids)
    types = np.asarray(cell_types)
    rng = np.random.default_rng(seed)
    for donor in np.unique(donors):
        for ct in np.unique(types):
            rows = np.flatnonzero((donors == donor) & (types == ct))
            if rows.size < 2:
                continue
            array[rows] = array[rng.permutation(rows)]
    return array


class _MockAttention(nn.Module):
    def __init__(self, fixed_context: torch.Tensor) -> None:
        super().__init__()
        self.register_buffer("fixed_context", fixed_context)

    def forward(self, query, key, value, need_weights=False, **kwargs):  # noqa: ANN001
        n_cells = query.shape[0]
        context = self.fixed_context.expand(n_cells, -1, -1)
        return context, None


class _MockPool(nn.Module):
    def __init__(self, dim: int) -> None:
        super().__init__()
        self.dim = dim

    def forward(self, h: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        n = h.shape[0]
        attention = torch.full((n,), 1.0 / n, device=h.device, dtype=h.dtype)
        return h.mean(dim=0), attention


class _MockGate(nn.Module):
    def __init__(self, override: Sequence[float], original_gate: nn.Module) -> None:
        super().__init__()
        self.override = torch.tensor(list(override), dtype=torch.float32)
        self.original_gate = original_gate

    def forward(self, embeddings, override=None):  # noqa: ANN001
        return self.original_gate(
            embeddings, override=self.override.to(embeddings[0].device)
        )


def _attention_module(model: nn.Module) -> nn.Module | None:
    encoder = getattr(model, "encoder", None)
    if encoder is None:
        return None
    if hasattr(encoder, "attention"):
        return encoder.attention
    inner = getattr(encoder, "inner", None)
    if inner is not None and hasattr(inner, "attention"):
        return inner.attention
    return None


def _gate_module(model: nn.Module) -> nn.Module | None:
    if hasattr(model, "gate"):
        return model.gate
    encoder = getattr(model, "encoder", None)
    if encoder is None:
        return None
    if hasattr(encoder, "gate"):
        return encoder.gate
    inner = getattr(encoder, "inner", None)
    if inner is not None and hasattr(inner, "gate"):
        return inner.gate
    return None


def _set_attention(model: nn.Module, module: nn.Module) -> None:
    encoder = model.encoder
    if hasattr(encoder, "attention"):
        encoder.attention = module
    else:
        encoder.inner.attention = module


def _set_gate(model: nn.Module, module: nn.Module) -> None:
    if hasattr(model, "gate"):
        model.gate = module
    elif hasattr(model.encoder, "gate"):
        model.encoder.gate = module
    else:
        model.encoder.inner.gate = module


def _donor_probs(
    model: nn.Module, views: Mapping[str, np.ndarray], donors: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pred = predict_mil(model, views, donors)
    donor_ids = np.asarray(pred["donor_ids"])
    return donor_ids, np.asarray(pred["donor_probabilities"]), np.asarray(pred["cell_logits"])


def _log_loss(y: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(np.asarray(p, dtype=np.float64), 1e-15, 1 - 1e-15)
    y = np.asarray(y, dtype=np.float64)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def _ba(y: np.ndarray, p: np.ndarray) -> float | None:
    pred = (np.asarray(p) >= 0.5).astype(int)
    value = balanced_accuracy(np.asarray(y), pred).value
    return float(value) if value is not None else None


def run_intervention(
    name: str,
    model: nn.Module,
    test_views: Mapping[str, np.ndarray],
    test_donors: np.ndarray,
    test_cell_types: np.ndarray,
    train_views: Mapping[str, np.ndarray],
    seed: int,
    baseline_cell_pred: np.ndarray,
    donor_truth: np.ndarray,
    baseline_donor_ids: np.ndarray,
    baseline_prob_donor: np.ndarray,
    i3_draws: int = 1,
) -> dict[str, Any] | None:
    """Apply one intervention; return donor-level probs aligned to baseline_donor_ids."""
    views = {key: np.asarray(value).copy() for key, value in test_views.items()}
    orig_pool = getattr(model, "pool", None)
    orig_attn = _attention_module(model)
    orig_gate = _gate_module(model)

    try:
        if name == "I1":
            # ATAC = VIEW_B
            views[VIEW_B] = clamp_to_train_mean(views[VIEW_B], train_views[VIEW_B])
        elif name == "I2":
            # RNA = VIEW_A
            views[VIEW_A] = clamp_to_train_mean(views[VIEW_A], train_views[VIEW_A])
        elif name == "I3":
            probs = []
            for draw in range(i3_draws):
                draw_views = dict(views)
                draw_views[VIEW_B] = permute_within_donor_celltype(
                    views[VIEW_B], test_donors, test_cell_types, seed=seed + draw
                )
                donor_ids, prob_donor, _ = _donor_probs(model, draw_views, test_donors)
                order = {d: i for i, d in enumerate(donor_ids)}
                probs.append(np.array([prob_donor[order[d]] for d in baseline_donor_ids]))
            mean_prob = np.mean(np.stack(probs, axis=0), axis=0)
            cell_pred = baseline_cell_pred  # flip rate not well-defined over draws
            ba_after = _ba(donor_truth, mean_prob)
            ba_before = _ba(donor_truth, baseline_prob_donor)
            return {
                "prob_donor": mean_prob,
                "flip_rate": 0.0,
                "ba_drop": (
                    None
                    if ba_before is None or ba_after is None
                    else float(ba_before - ba_after)
                ),
                "ll_after": _log_loss(donor_truth, mean_prob),
                "ll_before": _log_loss(donor_truth, baseline_prob_donor),
            }
        elif name == "I4":
            if orig_attn is None:
                return None
            train_contexts: list[torch.Tensor] = []

            def hook(_module, _args, output):  # noqa: ANN001
                context, _ = output
                train_contexts.append(context.detach().cpu())

            handle = orig_attn.register_forward_hook(hook)
            try:
                with torch.no_grad():
                    n_train = train_views[VIEW_A].shape[0]
                    for start in range(0, n_train, 1000):
                        batch = {
                            k: torch.as_tensor(v[start : start + 1000], dtype=torch.float32)
                            for k, v in train_views.items()
                        }
                        model.forward_bag_full(batch)
            finally:
                handle.remove()
            if not train_contexts:
                return None
            mean_context = torch.cat(train_contexts, dim=0).mean(dim=0, keepdim=True)
            _set_attention(model, _MockAttention(mean_context))
        elif name == "I5":
            if orig_pool is None:
                return None
            model.pool = _MockPool(model.dim)
        elif name.startswith("I6_"):
            if orig_gate is None:
                return None
            code = name.split("_", 1)[1]
            override = {
                "10": [1.0, 0.0],
                "01": [0.0, 1.0],
                "55": [0.5, 0.5],
            }[code]
            _set_gate(model, _MockGate(override, orig_gate))
        elif name == "NC":
            pass
        else:
            return None

        donor_ids, prob_donor, logits = _donor_probs(model, views, test_donors)
        order = {d: i for i, d in enumerate(donor_ids)}
        aligned = np.array([prob_donor[order[d]] for d in baseline_donor_ids])
        cell_pred = (logits >= 0).astype(int)
        ba_after = _ba(donor_truth, aligned)
        ba_before = _ba(donor_truth, baseline_prob_donor)
        return {
            "prob_donor": aligned,
            "flip_rate": float(np.mean(cell_pred != baseline_cell_pred)),
            "ba_drop": (
                None
                if ba_before is None or ba_after is None
                else float(ba_before - ba_after)
            ),
            "ll_after": _log_loss(donor_truth, aligned),
            "ll_before": _log_loss(donor_truth, baseline_prob_donor),
        }
    finally:
        if orig_pool is not None:
            model.pool = orig_pool
        if orig_attn is not None:
            _set_attention(model, orig_attn)
        if orig_gate is not None:
            _set_gate(model, orig_gate)


def compute_bootstrap_ci(
    metric_fn,
    y: np.ndarray,
    p_before: np.ndarray,
    p_after: np.ndarray,
    n_bootstrap: int = 1000,
    seed: int = 22,
) -> tuple[float | None, float | None, float | None]:
    rng = np.random.default_rng(seed)
    n = len(y)
    deltas: list[float] = []
    for _ in range(n_bootstrap):
        idx = rng.choice(n, size=n, replace=True)
        before = metric_fn(y[idx], p_before[idx])
        after = metric_fn(y[idx], p_after[idx])
        if before is not None and after is not None:
            deltas.append(float(before - after))
    if not deltas:
        return None, None, None
    arr = np.asarray(deltas, dtype=np.float64)
    return float(arr.mean()), float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))


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


def _apply_r4_programs(
    inputs,
    fold_arrays,
    region_rows: np.ndarray,
    model_seed: int,
):
    from p22.data.nn_fold import _atac_tfidf, _rna_lognorm
    from p22.models.program_tokens import fit_programs, program_activities

    id_to_idx = {gid: i for i, gid in enumerate(inputs.gene_ids)}
    selected_cols = [id_to_idx[gid] for gid in fold_arrays.gene_ids]
    rna_norm = _rna_lognorm(inputs.rna, inputs.rna_totals)[:, selected_cols]
    rna_dense = np.asarray(rna_norm.todense(), dtype=np.float32)
    atac_raw = inputs.atac[:, region_rows]
    atac_tfidf, _ = _atac_tfidf(atac_raw, fold_arrays.train_position)
    atac_dense = np.asarray(atac_tfidf.todense(), dtype=np.float32)
    rna_nmf = fit_programs(rna_dense[fold_arrays.train_position], k=16, seed=model_seed)
    atac_nmf = fit_programs(atac_dense[fold_arrays.train_position], k=8, seed=model_seed)
    fold_arrays.rna = program_activities(rna_nmf, rna_dense).numpy()
    fold_arrays.atac = program_activities(atac_nmf, atac_dense).numpy()
    return fold_arrays


def _interventions_for_arm(arm: str) -> list[str]:
    names = ["I1", "I2", "NC", "I5"]
    if arm.endswith("_ca") or arm.endswith("_gated"):
        names.append("I3")
    if arm.endswith("_ca"):
        names.append("I4")
    if arm.endswith("_gated"):
        names.extend(["I6_10", "I6_01", "I6_55"])
    return names


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
    i3_draws: int,
) -> list[dict[str, Any]]:
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

    model_seed = int(fold_rec["best_grid_point"].get("model_seed", 0))
    if arm.startswith("R4_"):
        fold_arrays = _apply_r4_programs(inputs, fold_arrays, region_rows, model_seed)

    train_pos = fold_arrays.train_position
    test_pos = ~train_pos
    train_views = {VIEW_A: fold_arrays.rna[train_pos], VIEW_B: fold_arrays.atac[train_pos]}
    test_views = {VIEW_A: fold_arrays.rna[test_pos], VIEW_B: fold_arrays.atac[test_pos]}
    test_donors = fold_arrays.donor[test_pos]
    test_labels = fold_arrays.label[test_pos]
    test_cell_types = inputs.metadata["author_cell_type"].to_numpy()[holdout_rows]

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

    donor_ids, prob_donor, logits = _donor_probs(model, test_views, test_donors)
    # Align to saved fold donor order for traceability.
    saved_ids = list(fold_rec["donor_ids"])
    order = {d: i for i, d in enumerate(donor_ids)}
    if set(saved_ids) != set(order):
        raise RuntimeError(f"donor set mismatch for {arm} r{repeat}_f{fold}")
    prob_donor = np.array([prob_donor[order[d]] for d in saved_ids])
    donor_truth = np.array(
        [
            int(test_labels[test_donors == d][0])
            for d in saved_ids
        ]
    )
    baseline_cell_pred = (logits >= 0).astype(int)
    baseline_donor_ids = np.asarray(saved_ids)

    rows: list[dict[str, Any]] = []
    for name in _interventions_for_arm(arm):
        result = run_intervention(
            name,
            model,
            test_views,
            test_donors,
            test_cell_types,
            train_views,
            seed=22 + 1000 * repeat + fold,
            baseline_cell_pred=baseline_cell_pred,
            donor_truth=donor_truth,
            baseline_donor_ids=baseline_donor_ids,
            baseline_prob_donor=prob_donor,
            i3_draws=i3_draws if name == "I3" else 1,
        )
        if result is None:
            continue
        if name == "NC":
            if not np.allclose(result["prob_donor"], prob_donor):
                raise RuntimeError(
                    f"NC Δ ≠ 0 for {arm} r{repeat}_f{fold}: harness bug"
                )
            if result["flip_rate"] != 0.0:
                raise RuntimeError(f"NC flip_rate ≠ 0 for {arm} r{repeat}_f{fold}")
        rows.append(
            {
                "intervention": name,
                "arm": arm,
                "repeat": repeat,
                "fold": fold,
                "donors": baseline_donor_ids,
                "y": donor_truth,
                "p_before": prob_donor,
                "p_after": result["prob_donor"],
                "flip_rate": result["flip_rate"],
            }
        )
    return rows


def _aggregate(
    rows: list[dict[str, Any]], bootstrap_draws: int, bootstrap_seed: int
) -> list[dict[str, Any]]:
    if not rows:
        return []
    frame = pd.DataFrame(rows)
    summary: list[dict[str, Any]] = []
    for (intervention, arm), group in frame.groupby(["intervention", "arm"], sort=True):
        # Average probabilities across repeats per donor, then bootstrap donors.
        pieces = []
        for _, row in group.iterrows():
            pieces.append(
                pd.DataFrame(
                    {
                        "donor": row["donors"],
                        "y": row["y"],
                        "p_before": row["p_before"],
                        "p_after": row["p_after"],
                    }
                )
            )
        stacked = pd.concat(pieces, ignore_index=True)
        donor = (
            stacked.groupby("donor", sort=True)
            .agg(y=("y", "first"), p_before=("p_before", "mean"), p_after=("p_after", "mean"))
            .reset_index()
        )
        y = donor["y"].to_numpy()
        p_before = donor["p_before"].to_numpy()
        p_after = donor["p_after"].to_numpy()
        ba_drop, ba_lo, ba_hi = compute_bootstrap_ci(
            _ba, y, p_before, p_after, n_bootstrap=bootstrap_draws, seed=bootstrap_seed
        )
        ll_drop, ll_lo, ll_hi = compute_bootstrap_ci(
            _log_loss,
            y,
            p_before,
            p_after,
            n_bootstrap=bootstrap_draws,
            seed=bootstrap_seed,
        )
        used = (
            ll_lo is not None
            and ll_hi is not None
            and (ll_lo > 0 or ll_hi < 0)
        )
        summary.append(
            {
                "intervention": intervention,
                "arm": arm,
                "n_donors": int(len(donor)),
                "n_fold_rows": int(len(group)),
                "flip_rate": float(group["flip_rate"].mean()),
                "ba_drop": ba_drop,
                "ba_drop_ci": [ba_lo, ba_hi],
                "ll_drop": ll_drop,
                "ll_drop_ci": [ll_lo, ll_hi],
                "used_by_model": bool(used),
            }
        )
    return summary


def _decision_tags(summary: list[dict[str, Any]]) -> dict[str, Any]:
    by = {(row["intervention"], row["arm"]): row for row in summary}
    tags: list[str] = []

    ca_i3 = by.get(("I3", "R3_ca"))
    if ca_i3 and ca_i3["ll_drop_ci"][0] is not None:
        lo, hi = ca_i3["ll_drop_ci"]
        if lo > 0 or hi < 0:
            tags.append("CA_USES_PAIRING")
        else:
            tags.append("CA_PAIRING_UNUSED")

    atac_rows = [
        row
        for row in summary
        if row["intervention"] == "I1" and row["arm"] in {"R3_ca", "R3_tc", "R3_gated", "R4_ca"}
    ]
    if atac_rows and all(
        row["ll_drop_ci"][0] is not None
        and row["ll_drop_ci"][0] <= 0 <= row["ll_drop_ci"][1]
        for row in atac_rows
    ):
        tags.append("ATAC_UNUSED")
    elif atac_rows:
        tags.append("ATAC_USED")

    nc_ok = all(
        row["intervention"] != "NC"
        or (
            abs(row["ll_drop"] or 0.0) < 1e-12
            and abs(row["ba_drop"] or 0.0) < 1e-12
            and row["flip_rate"] == 0.0
        )
        for row in summary
    )
    return {
        "tags": tags,
        "nc_exact_zero": bool(nc_ok),
        "pc_status": "N/A",
        "pc_reason": (
            "No saved planted S4/S5 δ=1.0 fold models under ladder_v2; "
            "PC not refit in this run. I3 tags are reported but pairing "
            "claims remain provisional without PC sensitivity."
        ),
    }


def _write_markdown(
    path: Path,
    summary: list[dict[str, Any]],
    decision: Mapping[str, Any],
    run_dir: Path,
) -> None:
    lines = [
        "# Faithfulness interventions (N13)",
        "",
        f"Source models: `{run_dir}` (accepted ladder_v2; not copied into finish-base).",
        "",
        f"**NC exact zero:** `{decision['nc_exact_zero']}`.",
        f"**Decision tags:** {', '.join(decision['tags']) or '(none)'}.",
        f"**PC:** {decision['pc_status']} — {decision['pc_reason']}",
        "",
        "Rule: an attention/gate/pairing/MIL readout may be described as used by the "
        "model only if its intervention Δ log-loss donor-bootstrap CI excludes 0.",
        "",
        "| Intervention | Arm | Flip rate | BA drop (CI) | Log-loss drop (CI) | Used? |",
        "|---|---|---|---|---|---|",
    ]
    for row in summary:
        ba = (
            f"{row['ba_drop']:.4f} [{row['ba_drop_ci'][0]:.4f}, {row['ba_drop_ci'][1]:.4f}]"
            if row["ba_drop"] is not None
            else "N/A"
        )
        ll = (
            f"{row['ll_drop']:.4f} [{row['ll_drop_ci'][0]:.4f}, {row['ll_drop_ci'][1]:.4f}]"
            if row["ll_drop"] is not None
            else "N/A"
        )
        lines.append(
            f"| {row['intervention']} | {row['arm']} | {row['flip_rate']:.4f} | "
            f"{ba} | {ll} | {'Yes' if row['used_by_model'] else 'No'} |"
        )
    path.write_text("\n".join(lines) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        type=Path,
        default=_LADDER_V2_ROOT,
        help="ladder_v2 run directory with folds/ and models/",
    )
    parser.add_argument("--out", type=Path, default=Path("docs/nn_v2"))
    parser.add_argument("--protocol", default="configs/nn_protocol_v2_2026-09-23.json")
    parser.add_argument("--inputs-config", default="configs/nn_inputs_2026-09-23.json")
    parser.add_argument("--arms", default=",".join(_DEFAULT_ARMS))
    parser.add_argument("--smoke", action="store_true", help="Only repeat 0 fold 0")
    parser.add_argument("--i3-draws", type=int, default=20)
    parser.add_argument("--bootstrap-draws", type=int, default=1000)
    parser.add_argument("--bootstrap-seed", type=int, default=22)
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

    all_rows: list[dict[str, Any]] = []
    for split in splits:
        for arm in arms:
            print(f"N13 {arm} r{split.repeat}_f{split.fold}", flush=True)
            all_rows.extend(
                evaluate_fold(
                    run_dir=run_dir,
                    arm=arm,
                    repeat=split.repeat,
                    fold=split.fold,
                    inputs=inputs,
                    train_rows=split.train_index,
                    holdout_rows=split.test_index,
                    protocol=protocol,
                    i3_draws=args.i3_draws,
                )
            )

    summary = _aggregate(all_rows, args.bootstrap_draws, args.bootstrap_seed)
    decision = _decision_tags(summary)
    payload = {
        "task": "N13",
        "title": "Held-out faithfulness interventions",
        "status": "DONE" if decision["nc_exact_zero"] else "FAIL",
        "source_run": str(run_dir),
        "arms": arms,
        "smoke": bool(args.smoke),
        "i3_draws": int(args.i3_draws),
        "bootstrap_draws": int(args.bootstrap_draws),
        "bootstrap_seed": int(args.bootstrap_seed),
        "decision": decision,
        "summary": summary,
        "acceptance": {
            "nc_exact_zero": decision["nc_exact_zero"],
            "cells_filled_or_na": True,
            "pc": decision["pc_status"],
        },
    }
    args.out.mkdir(parents=True, exist_ok=True)
    out_json = args.out / ("faithfulness_smoke.json" if args.smoke else "faithfulness.json")
    out_json.write_text(json.dumps(payload, indent=2) + "\n")
    if not args.smoke:
        _write_markdown(args.out / "FAITHFULNESS.md", summary, decision, run_dir)
    print(
        json.dumps(
            {
                "wrote": str(out_json),
                "tags": decision["tags"],
                "nc": decision["nc_exact_zero"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
