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
    # This exactly mimics `run_nn_v2_comparison.py`
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    
    fold_arrays = prepare_nn_fold(
        inputs, 
        train_rows, 
        test_rows, 
        region_rows, 
        n_hvg=protocol["representation"]["rna"].get("n_hvg", 2000),
        exclude_chr21=False
    )
    
    test_pos = np.arange(len(train_rows), len(train_rows) + len(test_rows))
    chr21_mask = inputs.chr21_gene_mask()
    chr21_genes_in_hvg = np.isin(fold_arrays.gene_ids, inputs.gene_ids[chr21_mask])
    chr21_dosage = fold_arrays.rna[test_pos][:, chr21_genes_in_hvg].mean(axis=1) if chr21_genes_in_hvg.any() else np.zeros(len(test_pos))
    
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
        
        # In run_nn_v2_comparison, model_seed=0 was passed as args.model_seed
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
    return views, widths, fold_arrays, chr21_dosage

def main(argv=None):
    parser = argparse.ArgumentParser()
    args = parser.parse_args(argv)

    out_dir = Path("reports/generated/nn_20260923/spectrum")
    out_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    # We load regions dynamically from test fold just in case, but they are all same right now.
    region_rows = np.arange(len(inputs.regions))
    
    metadata = inputs.metadata
    donors = metadata["donor_id"].to_numpy()
    labels = (metadata["disease"] == "complete trisomy 21").astype(int).to_numpy()
    
    splits = list(iter_repeated_stratified_group_folds(
        donors, labels, n_repeats=protocol["splits"]["n_repeats"], 
        n_folds=protocol["splits"]["n_folds"], base_seed=protocol["splits"]["split_seed"]
    ))
    
    arms_to_export = ["R1_ca", "R3_ca", "R3_tc", "R4_ca"]
    records = []
    
    # Store predictions for each cell across repeats
    # structure: cell_scores[arm][cell_id] = {"s": [], "a": [], "chr21_dosage": [], "nCount_RNA": ..., "nCount_ATAC": ...}
    cell_scores = {arm: defaultdict(lambda: {"s": [], "a": [], "chr21": []}) for arm in arms_to_export}
    cell_metadata_cache = {}

    for arm_name in arms_to_export:
        print(f"Processing arm {arm_name}...")
        for split in splits:
            print(f"  Fold {split.fold} Repeat {split.repeat}")
            # Load the model state_dict
            model_path = Path(f"reports/generated/nn_20260923/ladder/models/{arm_name}/r{split.repeat}_f{split.fold}.pt")
            if not model_path.exists():
                print(f"  WARNING: missing {model_path}")
                continue
                
            cfg = protocol["training"].copy()
            cfg["seed"] = 0
            
            views, widths, fold_arrays, chr21_dosage = compute_fold_features(
                inputs, split.train_index, split.test_index, region_rows, arm_name, protocol
            )
            
            # The exact grid point was saved in folds JSON, but it's identical unless a grid search was run. 
            # From run_nn_v2_comparison.py, cfg was just protocol["training"].copy(). 
            # But wait, N9 specifies lambda_adv=1.0 by default in protocol. The grid search might have chosen 0.1.
            # Let's read the actual best_grid_point from the fold JSON!
            fold_json_path = Path(f"reports/generated/nn_20260923/ladder/folds/r{split.repeat}_f{split.fold}_{arm_name}.json")
            if fold_json_path.exists():
                with open(fold_json_path) as f:
                    fold_rec = json.load(f)
                cfg = fold_rec["best_grid_point"]
            
            # predict_mil doesn't use the adversary aux_loss, so we can just mock cell_meta
            # to satisfy the validation inside adversary_aux_loss.
            cfg["cell_meta"] = {
                "labels": np.zeros(1),
                "library": np.zeros(1),
                "batch": np.zeros(1),
                "qc": np.zeros((1, 5))
            }
            
            model, aux, trainer = build_arm(arm_name, widths, cfg)
            model.load_state_dict(torch.load(model_path, map_location="cpu", weights_only=True))
            model.eval()
            
            test_donors = fold_arrays.donor[len(split.train_index):]
            test_predictions = predict_mil(model, views, test_donors)
            
            cell_logits = test_predictions["cell_logits"]
            attention = test_predictions["attention"]
            
            test_cell_ids = metadata.index[split.test_index].to_numpy()
            
            for i, cell_id in enumerate(test_cell_ids):
                cell_scores[arm_name][cell_id]["s"].append(cell_logits[i])
                cell_scores[arm_name][cell_id]["a"].append(attention[i])
                cell_scores[arm_name][cell_id]["chr21"].append(chr21_dosage[i])
                
                if cell_id not in cell_metadata_cache:
                    row = metadata.iloc[split.test_index[i]]
                    cell_metadata_cache[cell_id] = {
                        "cell_id": cell_id,
                        "donor": row["donor_id"],
                        "label": 1 if row["disease"] == "complete trisomy 21" else 0,
                        "author_cell_type": row["author_cell_type"],
                        "cell_class": row["cell_class"],
                        "dev_PCW": row["dev_PCW"],
                        "log1p_nCount_RNA": np.log1p(row["nCount_RNA"]),
                        "log1p_nCount_ATAC": np.log1p(row["nCount_ATAC"])
                    }
                    
    # Generate final export
    out_rows = []
    for arm_name in arms_to_export:
        arm_scores = cell_scores[arm_name]
        for cell_id, metrics in arm_scores.items():
            if len(metrics["s"]) != 5:
                raise AssertionError(f"ASSERTION FAILED: {cell_id} in {arm_name} appeared {len(metrics['s'])} times")
            
            s_mean = np.mean(metrics["s"])
            s_sd = np.std(metrics["s"], ddof=1) if len(metrics["s"]) > 1 else np.nan
            a_mean = np.mean(metrics["a"])
            chr21_mean = np.mean(metrics["chr21"])
            
            meta = cell_metadata_cache[cell_id]
            out_rows.append({
                "cell_id": meta["cell_id"],
                "donor": meta["donor"],
                "label": meta["label"],
                "author_cell_type": meta["author_cell_type"],
                "cell_class": meta["cell_class"],
                "dev_PCW": meta["dev_PCW"],
                "arm": arm_name,
                "s_mean": s_mean,
                "s_sd": s_sd,
                "a_mean": a_mean,
                "chr21_dosage": chr21_mean,
                "log1p_nCount_RNA": meta["log1p_nCount_RNA"],
                "log1p_nCount_ATAC": meta["log1p_nCount_ATAC"],
            })
            
    df = pd.DataFrame(out_rows)
    out_csv = out_dir / "cell_scores.csv.gz"
    df.to_csv(out_csv, index=False, compression="gzip")
    
    # Also output docs/nn_v2/donor_celltype_scores.csv.gz
    # donor x cell-type means
    compact = df.groupby(["arm", "donor", "author_cell_type"]).agg({
        "label": "first",
        "cell_class": "first",
        "dev_PCW": "first",
        "s_mean": "mean",
        "a_mean": "mean",
        "chr21_dosage": "mean",
        "log1p_nCount_RNA": "mean",
        "log1p_nCount_ATAC": "mean",
        "cell_id": "count" # use as n_cells
    }).rename(columns={"cell_id": "n_cells"}).reset_index()
    
    compact_csv = Path("docs/nn_v2/donor_celltype_scores.csv.gz")
    compact_csv.parent.mkdir(parents=True, exist_ok=True)
    compact.to_csv(compact_csv, index=False, compression="gzip")
    
    print(f"Exported {len(df)} rows to {out_csv}")
    print(f"Exported {len(compact)} rows to {compact_csv}")

if __name__ == "__main__":
    sys.exit(main())
