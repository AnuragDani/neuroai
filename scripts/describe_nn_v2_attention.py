import argparse
import json
import logging
import os
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
import torch
import scipy.sparse as sparse

from p22.data.group_splits import iter_repeated_stratified_group_folds
from p22.data.nn_inputs import load_nn_inputs, prepare_nn_fold
from p22.eval.nn_factory import build_arm
from p22.models.fusion import VIEW_A, VIEW_B
from p22.training.mil_loop import predict_mil

def compute_fold_features(inputs, train_rows, test_rows, region_rows, arm_name, protocol):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    fold_arrays = prepare_nn_fold(
        inputs, train_rows, test_rows, region_rows, 
        n_hvg=protocol["representation"]["rna"].get("n_hvg", 2000),
        exclude_chr21=False
    )
    test_pos = np.arange(len(train_rows), len(train_rows) + len(test_rows))
    
    if arm_name.startswith("R4_"):
        from p22.data.nn_fold import _rna_lognorm, _atac_tfidf
        from p22.models.program_tokens import fit_programs, program_activities
        
        id_to_idx = {gid: i for i, gid in enumerate(inputs.gene_ids)}
        selected_cols = [id_to_idx[gid] for gid in fold_arrays.gene_ids]
        
        rna_norm = _rna_lognorm(inputs.rna, inputs.rna_totals)[:, selected_cols]
        rna_dense = np.asarray(rna_norm.todense(), dtype=np.float32)
        
        atac_raw = inputs.atac[:, region_rows]
        atac_tfidf, _ = _atac_tfidf(atac_raw, fold_arrays.train_position)
        atac_dense = np.asarray(atac_tfidf.todense(), dtype=np.float32)
        
        model_seed = 0
        rna_nmf = fit_programs(rna_dense[fold_arrays.train_position], k=16, seed=model_seed)
        atac_nmf = fit_programs(atac_dense[fold_arrays.train_position], k=8, seed=model_seed)
        
        fold_arrays.rna = program_activities(rna_nmf, rna_dense).numpy()
        fold_arrays.atac = program_activities(atac_nmf, atac_dense).numpy()
        
    views = {
        VIEW_A: fold_arrays.rna[test_pos],
        VIEW_B: fold_arrays.atac[test_pos],
    }
    widths = {
        "n_features_a": fold_arrays.rna.shape[1],
        "n_features_b": fold_arrays.atac.shape[1],
        "n_library": len(np.unique(inputs.metadata["library"])),
        "n_batch": len(np.unique(inputs.metadata["batch_seq"])),
        "k_rna": 16,
        "k_atac": 8,
        "n_classes": 2
    }
    return views, widths, fold_arrays

def main(argv=None):
    parser = argparse.ArgumentParser()
    args = parser.parse_args(argv)

    with open("configs/nn_protocol_v2_2026-09-23.json") as f:
        protocol = json.load(f)
    with open("configs/nn_inputs_2026-09-23.json") as f:
        input_manifest = json.load(f)
        
    inputs = load_nn_inputs(
        input_manifest["inputs"]["h5ad"]["path"],
        input_manifest["inputs"]["atac_tiebreak_counts"]["path"],
        protocol["sampling"]["cap_per_donor"],
        protocol["sampling"]["seed"],
        union_bed=input_manifest["inputs"]["tracked_union_bed"]["path"]
    )
    
    metadata = inputs.metadata
    donors = metadata["donor_id"].to_numpy()
    labels = (metadata["disease"] == "complete trisomy 21").astype(int).to_numpy()
    
    splits = list(iter_repeated_stratified_group_folds(
        donors, labels, n_repeats=protocol["splits"]["n_repeats"], 
        n_folds=protocol["splits"]["n_folds"], base_seed=protocol["splits"]["split_seed"]
    ))
    
    arms_to_export = ["R3_gated", "R3_ca", "R4_ca"]
    
    r3_gated_sum = defaultdict(lambda: np.zeros(2))
    r3_gated_count = defaultdict(int)
    
    r3_ca_entropy_sum = defaultdict(float)
    r3_ca_count = defaultdict(int)
    
    r4_ca_attn_sum = defaultdict(lambda: np.zeros((16, 8)))
    r4_ca_count = defaultdict(int)
    
    r4_ca_annotations = None
    
    for arm_name in arms_to_export:
        print(f"Processing {arm_name}...")
        for split in splits:
            model_path = Path(f"reports/generated/nn_20260923/ladder/models/{arm_name}/r{split.repeat}_f{split.fold}.pt")
            if not model_path.exists():
                continue
                
            cfg = protocol["training"].copy()
            cfg["seed"] = 0
            
            region_rows = np.arange(len(inputs.regions))
            views, widths, fold_arrays = compute_fold_features(
                inputs, split.train_index, split.test_index, region_rows, arm_name, protocol
            )
            
            fold_json_path = Path(f"reports/generated/nn_20260923/ladder/folds/r{split.repeat}_f{split.fold}_{arm_name}.json")
            if fold_json_path.exists():
                with open(fold_json_path) as f:
                    cfg = json.load(f)["best_grid_point"]
                    
            cfg["cell_meta"] = {
                "labels": np.zeros(1), "library": np.zeros(1),
                "batch": np.zeros(1), "qc": np.zeros((1, 5))
            }
            
            model, aux, trainer = build_arm(arm_name, widths, cfg)
            model.load_state_dict(torch.load(model_path, map_location="cpu", weights_only=True))
            model.eval()
            
            test_types = metadata.iloc[split.test_index]["author_cell_type"].to_numpy()
            
            device = "cpu"
            views_t = {k: torch.tensor(v, device=device) for k, v in views.items()}
            with torch.no_grad():
                if arm_name == "R3_gated":
                    output = model.encoder(views_t[VIEW_A], views_t[VIEW_B])
                    weights = output.routing_weights.numpy() # (n_cells, 2)
                    for i, ct in enumerate(test_types):
                        r3_gated_sum[ct] += weights[i]
                        r3_gated_count[ct] += 1
                elif arm_name == "R3_ca":
                    encoder_model = model.encoder
                    from p22.models.fusion import _encode_branches
                    branches = _encode_branches(encoder_model.encoder_a, encoder_model.encoder_b, views_t[VIEW_A], views_t[VIEW_B], ())
                    tokens_a = branches[VIEW_A].reshape(-1, encoder_model.n_tokens, encoder_model.embed_dim)
                    tokens_b = branches[VIEW_B].reshape(-1, encoder_model.n_tokens, encoder_model.embed_dim)
                    context, attn_w = encoder_model.attention(tokens_a, tokens_b, tokens_b, need_weights=True)
                    attn_w = attn_w.numpy()
                    entropy = -np.sum(attn_w * np.log(attn_w + 1e-9), axis=2)
                    entropy = np.mean(entropy, axis=1)
                    for i, ct in enumerate(test_types):
                        r3_ca_entropy_sum[ct] += entropy[i]
                        r3_ca_count[ct] += 1
                elif arm_name == "R4_ca":
                    output = model.encoder(views_t[VIEW_A], views_t[VIEW_B], need_weights=True)
                    attn_w = model.encoder.attention_weights.numpy()
                    for i, ct in enumerate(test_types):
                        r4_ca_attn_sum[ct] += attn_w[i]
                        r4_ca_count[ct] += 1
                        
            if arm_name == "R4_ca" and r4_ca_annotations is None:
                model_json_path = Path(f"reports/generated/nn_20260923/ladder/models/R4_ca/r{split.repeat}_f{split.fold}.json")
                if model_json_path.exists():
                    with open(model_json_path) as f:
                        ev = json.load(f)
                        if "programs" in ev:
                            r4_ca_annotations = ev["programs"]

    out_data = []
    all_types = sorted(set(r3_gated_count.keys()) | set(r3_ca_count.keys()) | set(r4_ca_count.keys()))
    
    for ct in all_types:
        rec = {"cell_type": ct}
        if r3_gated_count[ct] > 0:
            rec["R3_gated_routing_weight_rna"] = r3_gated_sum[ct][0] / r3_gated_count[ct]
            rec["R3_gated_routing_weight_atac"] = r3_gated_sum[ct][1] / r3_gated_count[ct]
            rec["R3_gated_tag"] = "NOT_SHOWN_USED"
            
        if r3_ca_count[ct] > 0:
            rec["R3_ca_attention_entropy"] = r3_ca_entropy_sum[ct] / r3_ca_count[ct]
            rec["R3_ca_tag"] = "NOT_SHOWN_USED"
            
        if r4_ca_count[ct] > 0:
            rec["R4_ca_attention_matrix"] = (r4_ca_attn_sum[ct] / r4_ca_count[ct]).tolist()
            rec["R4_ca_tag"] = "NOT_SHOWN_USED"
            
        out_data.append(rec)
        
    out_dir = Path("docs/nn_v2")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with open(out_dir / "routing_attention.json", "w") as f:
        json.dump({
            "cell_types": out_data,
            "R4_ca_annotations": r4_ca_annotations
        }, f, indent=2)
        
    with open(out_dir / "ROUTING_ATTENTION.md", "w") as f:
        f.write("# Routing and Attention\n\n")
        f.write("Descriptive readouts by cell type. Tags indicate if the model relies on these pathways.\n\n")
        f.write("| Cell Type | R3_gated RNA | R3_gated ATAC | R3_ca Entropy | Tag |\n")
        f.write("|---|---|---|---|---|\n")
        for rec in out_data:
            rw_r = rec.get("R3_gated_routing_weight_rna", np.nan)
            rw_a = rec.get("R3_gated_routing_weight_atac", np.nan)
            ent = rec.get("R3_ca_attention_entropy", np.nan)
            tag = rec.get("R3_gated_tag", "NOT_SHOWN_USED")
            f.write(f"| {rec['cell_type']} | {rw_r:.3f} | {rw_a:.3f} | {ent:.3f} | {tag} |\n")
            
        f.write("\n## R4_ca Program Attention\n")
        f.write("Not shown due to blocked faithfulness test.\n")

if __name__ == "__main__":
    sys.exit(main())
