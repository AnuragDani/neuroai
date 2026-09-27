"""N17 routing/attention description by cell type against accepted ladder_v2.

Reloads saved fold models from the main-checkout ladder_v2 run (not copied
here), aggregates descriptive readouts per author_cell_type, and tags each
readout USED_BY_MODEL or NOT_SHOWN_USED from N13 faithfulness interventions.
Descriptive only: attention is not explanation.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from p22.data.group_splits import iter_repeated_stratified_group_folds
from p22.data.nn_fold import prepare_nn_fold
from p22.data.nn_inputs import load_nn_inputs, region_indices
from p22.eval.nn_factory import build_arm
from p22.models.fusion import VIEW_A, VIEW_B, _encode_branches

_LADDER_V2_ROOT = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v2"
)
_DEFAULT_ARMS = ("R3_gated", "R3_ca", "R4_ca")
_N_LIBRARY = 37
_N_BATCH = 12

# N13 intervention → N17 readout mapping (decision_tree / todo N13–N17).
_READOUT_INTERVENTIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "R3_gated_routing_weight": (
        ("I6_01", "R3_gated"),
        ("I6_10", "R3_gated"),
        ("I6_55", "R3_gated"),
    ),
    "R3_ca_attention_entropy": (("I4", "R3_ca"),),
    "R4_ca_program_module_attention": (("I4", "R4_ca"),),
}


def _dummy_cell_meta(n: int = 8) -> dict[str, np.ndarray]:
    return {
        "labels": np.zeros(n, dtype=np.int64),
        "library": np.zeros(n, dtype=np.int64),
        "batch": np.zeros(n, dtype=np.int64),
        "qc": np.zeros((n, 5), dtype=np.float32),
    }


def tags_from_faithfulness(faith: Mapping[str, Any]) -> dict[str, str]:
    """Map N13 intervention used_by_model flags onto N17 readout tags.

    IF N13 is not DONE (or summary missing) → every readout NOT_SHOWN_USED.
    ELSE a readout is USED_BY_MODEL only if any mapped intervention CI excluded 0.
    """
    status = str(faith.get("status", ""))
    summary = faith.get("summary")
    if status != "DONE" or not isinstance(summary, list):
        return {readout: "NOT_SHOWN_USED" for readout in _READOUT_INTERVENTIONS}

    used: dict[tuple[str, str], bool] = {}
    for row in summary:
        if not isinstance(row, Mapping):
            continue
        key = (str(row.get("intervention")), str(row.get("arm")))
        used[key] = bool(row.get("used_by_model"))

    out: dict[str, str] = {}
    for readout, keys in _READOUT_INTERVENTIONS.items():
        out[readout] = (
            "USED_BY_MODEL" if any(used.get(k, False) for k in keys) else "NOT_SHOWN_USED"
        )
    return out


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


def _apply_r4_programs(inputs, fold_arrays, region_rows: np.ndarray, model_seed: int):
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


def _attention_entropy(attn: np.ndarray) -> np.ndarray:
    """Mean Shannon entropy over query tokens; attn shape (n_cells, n_q, n_k)."""
    entropy = -np.sum(attn * np.log(attn + 1e-9), axis=2)
    return np.mean(entropy, axis=1)


def _ca_attention_entropy(encoder: nn.Module, views_t: Mapping[str, torch.Tensor]) -> np.ndarray:
    branches = _encode_branches(
        encoder.encoder_a, encoder.encoder_b, views_t[VIEW_A], views_t[VIEW_B], ()
    )
    tokens_a = branches[VIEW_A].reshape(-1, encoder.n_tokens, encoder.embed_dim)
    tokens_b = branches[VIEW_B].reshape(-1, encoder.n_tokens, encoder.embed_dim)
    _context, attn_w = encoder.attention(tokens_a, tokens_b, tokens_b, need_weights=True)
    return _attention_entropy(attn_w.detach().cpu().numpy())


def _r4_attention_matrix(encoder: nn.Module, views_t: Mapping[str, torch.Tensor]) -> np.ndarray:
    inner = getattr(encoder, "inner", encoder)
    inner(views_t[VIEW_A], views_t[VIEW_B], need_weights=True)
    weights = getattr(inner, "attention_weights", None)
    if weights is None:
        raise RuntimeError("R4_ca forward with need_weights=True left attention_weights unset")
    return weights.detach().cpu().numpy()


def _top_program_annotations(programs: Mapping[str, Any], top_n: int = 5) -> dict[str, Any]:
    """Compact top-feature lists from the first fold's saved N8 program annotation."""
    out: dict[str, Any] = {"rna": [], "atac": []}
    for modality in ("rna", "atac"):
        items = programs.get(modality, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, Mapping):
                continue
            feats = list(item.get("features", []))[:top_n]
            weights = list(item.get("weights", []))[:top_n]
            out[modality].append(
                {
                    "program": item.get("program"),
                    "top_features": feats,
                    "top_weights": weights,
                }
            )
    return out


def describe_run(
    *,
    run_dir: Path,
    arms: Sequence[str],
    inputs,
    splits: Sequence[Any],
    protocol: Mapping[str, Any],
    faith: Mapping[str, Any],
    smoke: bool = False,
) -> dict[str, Any]:
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    tags = tags_from_faithfulness(faith)
    metadata = inputs.metadata

    r3_gated_sum: dict[str, np.ndarray] = defaultdict(lambda: np.zeros(2, dtype=np.float64))
    r3_gated_count: dict[str, int] = defaultdict(int)
    r3_ca_entropy_sum: dict[str, float] = defaultdict(float)
    r3_ca_count: dict[str, int] = defaultdict(int)
    r4_ca_attn_sum: dict[str, np.ndarray] = defaultdict(
        lambda: np.zeros((16, 8), dtype=np.float64)
    )
    r4_ca_count: dict[str, int] = defaultdict(int)
    r4_annotations: dict[str, Any] | None = None
    folds_used = 0
    parameter_counts: dict[str, int] = {}

    with open(protocol["representation"]["atac"]["region_set_config"]) as handle:
        atac_regions = json.load(handle)
    region_by_split = {
        (item["repeat"], item["fold"]): item["regions"]
        for item in atac_regions["per_fold"]
    }

    for arm_name in arms:
        print(f"Processing arm {arm_name}...", flush=True)
        for split in splits:
            if smoke and not (split.repeat == 0 and split.fold == 0):
                continue
            region_list = region_by_split.get((split.repeat, split.fold))
            if region_list is None:
                raise ValueError(f"missing region set for r{split.repeat}_f{split.fold}")
            region_rows = region_indices(inputs, region_list)

            state_path = run_dir / "models" / arm_name / f"r{split.repeat}_f{split.fold}.pt"
            evidence_path = (
                run_dir / "models" / arm_name / f"r{split.repeat}_f{split.fold}.json"
            )
            fold_path = (
                run_dir / "folds" / f"r{split.repeat}_f{split.fold}_{arm_name}.json"
            )
            if not state_path.exists():
                raise FileNotFoundError(state_path)
            saved_evidence = json.loads(evidence_path.read_text())
            fold_rec = json.loads(fold_path.read_text())
            parameter_counts[arm_name] = int(fold_rec["parameter_count"])

            fold_arrays = prepare_nn_fold(
                inputs,
                split.train_index,
                split.test_index,
                region_rows,
                n_hvg=protocol["representation"]["rna"].get("n_hvg", 2000),
                exclude_chr21=False,
            )
            if fold_arrays.evidence["idf_sha256"] != saved_evidence["idf_sha256"]:
                raise RuntimeError(
                    f"idf_sha256 mismatch for {arm_name} r{split.repeat}_f{split.fold}: "
                    f"{fold_arrays.evidence['idf_sha256']} != {saved_evidence['idf_sha256']}"
                )

            model_seed = int(fold_rec["best_grid_point"].get("model_seed", 0))
            if arm_name.startswith("R4_"):
                fold_arrays = _apply_r4_programs(
                    inputs, fold_arrays, region_rows, model_seed
                )

            test_pos = ~fold_arrays.train_position
            views = {
                VIEW_A: fold_arrays.rna[test_pos],
                VIEW_B: fold_arrays.atac[test_pos],
            }
            widths = {
                "n_features_a": int(fold_arrays.rna.shape[1]),
                "n_features_b": int(fold_arrays.atac.shape[1]),
                "n_library": _N_LIBRARY,
                "n_batch": _N_BATCH,
                "k_rna": 16,
                "k_atac": 8,
                "n_classes": 2,
            }
            model = _load_fold_model(
                arm_name, widths, fold_rec["best_grid_point"], state_path
            )
            test_types = metadata.iloc[split.test_index]["author_cell_type"].to_numpy()
            views_t = {k: torch.as_tensor(v, dtype=torch.float32) for k, v in views.items()}

            with torch.no_grad():
                if arm_name == "R3_gated":
                    output = model.encoder(views_t[VIEW_A], views_t[VIEW_B])
                    weights = output.routing_weights.detach().cpu().numpy()
                    for i, ct in enumerate(test_types):
                        r3_gated_sum[ct] += weights[i]
                        r3_gated_count[ct] += 1
                elif arm_name == "R3_ca":
                    entropy = _ca_attention_entropy(model.encoder, views_t)
                    for i, ct in enumerate(test_types):
                        r3_ca_entropy_sum[ct] += float(entropy[i])
                        r3_ca_count[ct] += 1
                elif arm_name == "R4_ca":
                    attn_w = _r4_attention_matrix(model.encoder, views_t)
                    for i, ct in enumerate(test_types):
                        r4_ca_attn_sum[ct] += attn_w[i]
                        r4_ca_count[ct] += 1
                    if r4_annotations is None and "programs" in saved_evidence:
                        r4_annotations = _top_program_annotations(saved_evidence["programs"])

            folds_used += 1
            print(
                f"  done {arm_name} r{split.repeat}_f{split.fold} n_test={len(test_types)}",
                flush=True,
            )

    all_types = sorted(
        set(r3_gated_count) | set(r3_ca_count) | set(r4_ca_count)
    )
    cell_types: list[dict[str, Any]] = []
    for ct in all_types:
        rec: dict[str, Any] = {"cell_type": ct}
        if r3_gated_count[ct] > 0:
            mean_w = r3_gated_sum[ct] / r3_gated_count[ct]
            rec["R3_gated_routing_weight_rna"] = float(mean_w[0])
            rec["R3_gated_routing_weight_atac"] = float(mean_w[1])
            rec["R3_gated_n_cells"] = int(r3_gated_count[ct])
            rec["R3_gated_tag"] = tags["R3_gated_routing_weight"]
        if r3_ca_count[ct] > 0:
            rec["R3_ca_attention_entropy"] = float(
                r3_ca_entropy_sum[ct] / r3_ca_count[ct]
            )
            rec["R3_ca_n_cells"] = int(r3_ca_count[ct])
            rec["R3_ca_tag"] = tags["R3_ca_attention_entropy"]
        if r4_ca_count[ct] > 0:
            rec["R4_ca_attention_matrix"] = (
                r4_ca_attn_sum[ct] / r4_ca_count[ct]
            ).tolist()
            rec["R4_ca_n_cells"] = int(r4_ca_count[ct])
            rec["R4_ca_tag"] = tags["R4_ca_program_module_attention"]
        cell_types.append(rec)

    return {
        "task": "N17",
        "title": "Routing/attention description by cell type",
        "status": "DONE",
        "source_run": str(run_dir),
        "smoke": smoke,
        "arms": list(arms),
        "folds_used": folds_used,
        "n_library": _N_LIBRARY,
        "n_batch": _N_BATCH,
        "parameter_counts": parameter_counts,
        "n13_status": faith.get("status"),
        "n13_decision_tags": list(faith.get("decision", {}).get("tags", [])),
        "readout_tags": tags,
        "tag_rule": (
            "USED_BY_MODEL only if the mapped N13 intervention Δ log-loss "
            "donor-bootstrap CI excludes 0; else NOT_SHOWN_USED. "
            "Descriptive only; attention is not explanation."
        ),
        "readouts": [
            {
                "id": "R3_gated_routing_weight",
                "n13_interventions": ["I6_01", "I6_10", "I6_55"],
                "n13_tag": tags["R3_gated_routing_weight"],
            },
            {
                "id": "R3_ca_attention_entropy",
                "n13_interventions": ["I4"],
                "n13_tag": tags["R3_ca_attention_entropy"],
            },
            {
                "id": "R4_ca_program_module_attention",
                "n13_interventions": ["I4"],
                "n13_tag": tags["R4_ca_program_module_attention"],
            },
        ],
        "cell_types": cell_types,
        "R4_ca_annotations": r4_annotations,
    }


def write_markdown(payload: Mapping[str, Any], path: Path) -> None:
    tags = payload["readout_tags"]
    lines = [
        "# Routing and attention (N17)",
        "",
        (
            f"Source models: `{payload['source_run']}` "
            "(accepted ladder_v2; not copied into finish-base)."
        ),
        "",
        f"**N13 status:** `{payload['n13_status']}` "
        f"(decision tags: {', '.join(payload.get('n13_decision_tags') or ['none'])}).",
        "",
        "Descriptive readouts only. An attention/gate readout may be described as "
        "`USED_BY_MODEL` only when its mapped N13 intervention Δ log-loss CI excludes 0; "
        "otherwise `NOT_SHOWN_USED`. Attention is not explanation.",
        "",
        "| Readout | N13 interventions | Tag |",
        "|---|---|---|",
    ]
    for row in payload["readouts"]:
        lines.append(
            f"| {row['id']} | {', '.join(row['n13_interventions'])} | `{row['n13_tag']}` |"
        )
    lines.extend(
        [
            "",
            "| Cell type | R3_gated RNA | R3_gated ATAC | R3_gated tag | "
            "R3_ca entropy | R3_ca tag | R4_ca tag |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for rec in payload["cell_types"]:
        rw_r = rec.get("R3_gated_routing_weight_rna", float("nan"))
        rw_a = rec.get("R3_gated_routing_weight_atac", float("nan"))
        ent = rec.get("R3_ca_attention_entropy", float("nan"))
        lines.append(
            f"| {rec['cell_type']} | "
            f"{rw_r:.3f} | {rw_a:.3f} | `{rec.get('R3_gated_tag', 'n/a')}` | "
            f"{ent:.3f} | `{rec.get('R3_ca_tag', 'n/a')}` | "
            f"`{rec.get('R4_ca_tag', 'n/a')}` |"
        )
    lines.extend(
        [
            "",
            "## R4_ca program-module attention",
            "",
            f"Per-cell-type mean k_R×k_A matrices are in `routing_attention.json` "
            f"(`R4_ca_tag` = `{tags['R4_ca_program_module_attention']}`). "
            "Top genes/regions per token (first fold annotation) are under "
            "`R4_ca_annotations`. No biological interpretation is offered for "
            "`NOT_SHOWN_USED` readouts.",
            "",
        ]
    )
    path.write_text("\n".join(lines))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=_LADDER_V2_ROOT)
    parser.add_argument("--out-docs", type=Path, default=Path("docs/nn_v2"))
    parser.add_argument("--protocol", default="configs/nn_protocol_v2_2026-09-23.json")
    parser.add_argument("--inputs-config", default="configs/nn_inputs_2026-09-23.json")
    parser.add_argument(
        "--faithfulness",
        type=Path,
        default=Path("docs/nn_v2/faithfulness.json"),
    )
    parser.add_argument("--arms", default=",".join(_DEFAULT_ARMS))
    parser.add_argument("--smoke", action="store_true", help="Only repeat 0 fold 0")
    args = parser.parse_args(argv)

    protocol = json.loads(Path(args.protocol).read_text())
    input_manifest = json.loads(Path(args.inputs_config).read_text())
    faith = json.loads(args.faithfulness.read_text())
    inputs = load_nn_inputs(
        input_manifest["inputs"]["h5ad"]["path"],
        input_manifest["inputs"]["atac_tiebreak_counts"]["path"],
        protocol["sampling"]["cap_per_donor"],
        protocol["sampling"]["seed"],
        union_bed=input_manifest["inputs"]["tracked_union_bed"]["path"],
    )
    metadata = inputs.metadata
    donors = metadata["donor_id"].to_numpy()
    labels = (metadata["disease"] == "complete trisomy 21").astype(int).to_numpy()
    splits = list(
        iter_repeated_stratified_group_folds(
            donors,
            labels,
            n_repeats=protocol["splits"]["n_repeats"],
            n_folds=protocol["splits"]["n_folds"],
            base_seed=protocol["splits"]["split_seed"],
        )
    )
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    payload = describe_run(
        run_dir=args.run,
        arms=arms,
        inputs=inputs,
        splits=splits,
        protocol=protocol,
        faith=faith,
        smoke=args.smoke,
    )
    out_docs = args.out_docs
    out_docs.mkdir(parents=True, exist_ok=True)
    json_path = out_docs / "routing_attention.json"
    md_path = out_docs / "ROUTING_ATTENTION.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n")
    write_markdown(payload, md_path)
    print(
        f"Wrote {json_path} and {md_path}; folds_used={payload['folds_used']}; "
        f"tags={payload['readout_tags']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
