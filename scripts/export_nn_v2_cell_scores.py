import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from p22.data.group_splits import iter_repeated_stratified_group_folds
from p22.data.nn_inputs import load_nn_inputs, prepare_nn_fold
from p22.eval.nn_factory import build_arm
from p22.models.fusion import VIEW_A, VIEW_B
from p22.training.loop import set_all_seeds

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=str, default="configs/nn_protocol_v2_2026-09-23.json")
    parser.add_argument("--models-dir", type=str, default="reports/generated/nn_20260923/ladder/models")
    parser.add_argument("--out-cells", type=str, default="reports/generated/nn_20260923/spectrum/cell_scores.csv.gz")
    parser.add_argument("--out-compact", type=str, default="docs/nn_v2/donor_celltype_scores.csv.gz")
    args = parser.parse_args()

    out_cells_path = Path(args.out_cells)
    out_cells_path.parent.mkdir(parents=True, exist_ok=True)
    out_compact_path = Path(args.out_compact)
    out_compact_path.parent.mkdir(parents=True, exist_ok=True)

    with open(args.protocol) as f:
        protocol = json.load(f)

    # 1. Load inputs
    h5ad = "data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
    atac_npz = "reports/generated/atac_tiebreak_measured_20260921/counts/counts.npz"
    inputs = load_nn_inputs(
        h5ad, atac_npz,
        cap=protocol["data"]["cell_cap"],
        seed=protocol["data"]["sampling_seed"]
    )

    donors = inputs.metadata["donor_id"].to_numpy()
    labels = (inputs.metadata["disease"] == "complete trisomy 21").astype(int).to_numpy()

    splits = list(iter_repeated_stratified_group_folds(
        donors, labels, n_repeats=5, n_folds=5, base_seed=protocol["splits"]["split_seed"]
    ))

    arms_to_export = ["R3_ca", "R3_tc", "R4_ca", "R1_ca"]
    
    # Check if models exist.
    available_arms = []
    for arm in arms_to_export:
        if (Path(args.models_dir) / arm).exists():
            available_arms.append(arm)
        else:
            logging.warning(f"Models for arm {arm} not found, skipping.")

    if not available_arms:
        logging.error("No arms found to export!")
        return

    n_cells = len(inputs.metadata)
    
    cell_arm_scores = {arm: { "s": np.zeros((n_cells, 5), dtype=np.float32), "a": np.zeros((n_cells, 5), dtype=np.float32) } for arm in available_arms}
    cell_chr21_dosage = np.zeros((n_cells, 5), dtype=np.float32)
    cell_counts = np.zeros(n_cells, dtype=np.int32) 
    
    depth_rna = np.log1p(inputs.metadata["nCount_RNA"].astype(float).to_numpy())
    depth_atac = np.log1p(inputs.metadata["nCount_ATAC"].astype(float).to_numpy())

    built_models = {}
    for arm in available_arms:
        cfg = protocol["architecture"].copy()
        cfg.update(protocol["training"])
        model, _, _ = build_arm(arm, inputs.metadata, cfg)
        model.eval()
        built_models[arm] = model

    for split in splits:
        logging.info(f"Processing repeat {split.repeat} fold {split.fold}")
        
        with open("configs/atac_tiebreak_union_2026-09-21.bed") as f:
            union_ids = [line.split()[3] for line in f if line.strip()]
        rs_path = f"reports/generated/atac_tiebreak_sensitivity_20260921/region_sets_sha256.json"
        with open(rs_path) as f:
            rs_data = json.load(f)
        fold_rs_id = f"repeat{split.repeat}_fold{split.fold}"
        fold_regions = rs_data["sets"][fold_rs_id]
        
        union_indices = {rid: i for i, rid in enumerate(union_ids)}
        region_rows = np.array([union_indices[rid] for rid in fold_regions], dtype=np.int64)

        fold_arrays = prepare_nn_fold(
            inputs, split.train_index, split.test_index, region_rows,
            n_hvg=protocol["representation"]["n_hvg"],
            exclude_chr21=False
        )
        
        test_mask = ~fold_arrays.train_position
        test_indices = np.concatenate([split.train_index, split.test_index])[test_mask]
        
        if available_arms:
            cell_counts[test_indices] += 1
            
        gene_ids = fold_arrays.gene_ids
        gene_id_to_idx = {g: i for i, g in enumerate(inputs.gene_ids)}
        chr21_cols = np.array([i for i, g in enumerate(gene_ids) if inputs.chr21_gene_mask()[gene_id_to_idx[g]]])
        
        if len(chr21_cols) > 0:
            dosage = fold_arrays.rna[test_mask][:, chr21_cols].mean(axis=1)
        else:
            dosage = np.zeros(test_mask.sum())
            
        cell_chr21_dosage[test_indices, split.repeat] = dosage
        
        test_rna = torch.from_numpy(fold_arrays.rna[test_mask])
        test_atac = torch.from_numpy(fold_arrays.atac[test_mask])
        test_qc = torch.from_numpy(fold_arrays.qc[test_mask])
        test_donor = fold_arrays.donor[test_mask]
        
        for arm in available_arms:
            model_path = Path(args.models_dir) / arm / f"r{split.repeat}_f{split.fold}.pt"
            if not model_path.exists():
                logging.error(f"Missing model {model_path}")
                continue
                
            model = built_models[arm]
            model.load_state_dict(torch.load(model_path, map_location="cpu", weights_only=True))
            model.eval()
            
            with torch.no_grad():
                s_i = np.zeros(len(test_donor), dtype=np.float32)
                a_i = np.zeros(len(test_donor), dtype=np.float32)
                
                if hasattr(model, "forward_bag"):
                    unique_donors = np.unique(test_donor)
                    for d in unique_donors:
                        d_mask = test_donor == d
                        views = {
                            "rna": test_rna[d_mask],
                            "atac": test_atac[d_mask],
                            "qc": test_qc[d_mask]
                        }
                        _, attn, cell_logits = model.forward_bag(views)
                        s_i[d_mask] = cell_logits.numpy()
                        a_i[d_mask] = attn.numpy()
                    
            cell_arm_scores[arm]["s"][test_indices, split.repeat] = s_i
            cell_arm_scores[arm]["a"][test_indices, split.repeat] = a_i

    if not np.all(cell_counts == 5):
        missing = np.unique(cell_counts)
        raise AssertionError(f"Every sampled cell must appear exactly 5 times. Found appearances: {missing}")
        
    logging.info("Averaging across repeats...")
    records = []
    
    chr21_mean = cell_chr21_dosage.mean(axis=1)
    
    cell_ids = inputs.metadata.index.to_numpy()
    donors_meta = inputs.metadata["donor_id"].to_numpy()
    labels_meta = inputs.metadata["disease"].to_numpy()
    cell_types = inputs.metadata["author_cell_type"].to_numpy()
    cell_classes = inputs.metadata["cell_class"].to_numpy()
    dev_pcw = inputs.metadata["dev_PCW"].to_numpy()
    
    for arm in available_arms:
        s_mean = cell_arm_scores[arm]["s"].mean(axis=1)
        s_sd = cell_arm_scores[arm]["s"].std(axis=1)
        a_mean = cell_arm_scores[arm]["a"].mean(axis=1)
        
        for i in range(n_cells):
            records.append({
                "cell_id": cell_ids[i],
                "donor": donors_meta[i],
                "label": labels_meta[i],
                "author_cell_type": cell_types[i],
                "cell_class": cell_classes[i],
                "dev_PCW": dev_pcw[i],
                "arm": arm,
                "s_mean": s_mean[i],
                "s_sd": s_sd[i],
                "a_mean": a_mean[i],
                "chr21_dosage": chr21_mean[i],
                "log1p_nCount_RNA": depth_rna[i],
                "log1p_nCount_ATAC": depth_atac[i]
            })

    df = pd.DataFrame(records)
    df.to_csv(out_cells_path, index=False, compression="gzip")
    logging.info(f"Wrote {out_cells_path}")
    
    compact = df.groupby(["donor", "label", "author_cell_type", "dev_PCW", "arm"], observed=True)[
        ["s_mean", "a_mean", "chr21_dosage", "log1p_nCount_RNA", "log1p_nCount_ATAC"]
    ].mean().reset_index()
    compact.to_csv(out_compact_path, index=False, compression="gzip")
    logging.info(f"Wrote {out_compact_path}")

if __name__ == "__main__":
    main()
