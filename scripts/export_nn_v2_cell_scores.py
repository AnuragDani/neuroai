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


def run_export(protocol_path, models_dir, out_cells, out_compact, exclude_chr21):
    out_cells_path = Path(out_cells)
    out_cells_path.parent.mkdir(parents=True, exist_ok=True)
    out_compact_path = Path(out_compact)
    out_compact_path.parent.mkdir(parents=True, exist_ok=True)

    with open(protocol_path) as f:
        protocol = json.load(f)

    # 1. Load inputs
    with open("configs/nn_inputs_2026-09-23.json") as f:
        input_manifest = json.load(f)
        
    h5ad = input_manifest["inputs"]["h5ad"]["path"]
    atac_npz = input_manifest["inputs"]["atac_tiebreak_counts"]["path"]
    union_bed_path = input_manifest["inputs"]["tracked_union_bed"]["path"]
    
    inputs = load_nn_inputs(
        h5ad, atac_npz,
        cap=protocol["sampling"]["cap_per_donor"],
        seed=protocol["sampling"]["seed"],
        union_bed=union_bed_path
    )

    donors = inputs.metadata["donor_id"].to_numpy()
    labels = (inputs.metadata["disease"] == "complete trisomy 21").astype(int).to_numpy()

    splits = list(iter_repeated_stratified_group_folds(
        donors, labels, n_repeats=5, n_folds=5, base_seed=protocol["splits"]["split_seed"]
    ))

    arms_to_export = ["R3_ca", "R3_tc", "R4_ca", "R1_ca"]
    
    available_arms = []
    for arm in arms_to_export:
        if (Path(models_dir) / arm).exists():
            available_arms.append(arm)
        else:
            logging.warning(f"Models for arm {arm} not found in {models_dir}, skipping.")

    if not available_arms:
        logging.error(f"No arms found to export in {models_dir}!")
        return

    n_cells = len(inputs.metadata)
    
    cell_arm_scores = {arm: { "s": np.zeros((n_cells, 5), dtype=np.float32), "a": np.zeros((n_cells, 5), dtype=np.float32) } for arm in available_arms}
    cell_chr21_dosage = np.zeros((n_cells, 5), dtype=np.float32)
    cell_counts = np.zeros(n_cells, dtype=np.int32) 
    
    depth_rna = np.log1p(inputs.metadata["nCount_RNA"].astype(float).to_numpy())
    depth_atac = np.log1p(inputs.metadata["nCount_ATAC"].astype(float).to_numpy())

    for split in splits:
        logging.info(f"Processing repeat {split.repeat} fold {split.fold}")
        
        from p22.data.nn_inputs import region_indices
        rs_path = protocol["representation"]["atac"]["region_set_config"]
        with open(rs_path) as f:
            rs_data = json.load(f)
        fold_regions = next(
            x["regions"] for x in rs_data["per_fold"]
            if x["repeat"] == split.repeat and x["fold"] == split.fold
        )
        
        region_rows = region_indices(inputs, fold_regions)

        fold_arrays = prepare_nn_fold(
            inputs, split.train_index, split.test_index, region_rows,
            n_hvg=protocol["representation"]["rna"]["n_hvg"],
            exclude_chr21=exclude_chr21
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
        
        widths = {
            "n_features_a": fold_arrays.rna.shape[1],
            "n_features_b": fold_arrays.atac.shape[1],
            "n_library": len(np.unique(inputs.metadata["library"])),
            "n_batch": len(np.unique(inputs.metadata["batch_seq"])),
            "k_rna": 16,
            "k_atac": 8,
            "n_classes": 2
        }
        
        for arm in available_arms:
            model_path = Path(models_dir) / arm / f"r{split.repeat}_f{split.fold}.pt"
            if not model_path.exists():
                logging.error(f"Missing model {model_path}")
                continue
                
            cfg = protocol["architecture"].copy()
            cfg.update(protocol["training"])
            model, _, _ = build_arm(arm, widths, cfg)
            
            # Load state dict
            sd = torch.load(model_path, map_location="cpu", weights_only=True)
            model.load_state_dict(sd)
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=str, default="configs/nn_protocol_v2_2026-09-23.json")
    args = parser.parse_args()
    
    # 1. Main ladder v2
    run_export(
        protocol_path=args.protocol,
        models_dir="reports/generated/nn_20260923/ladder_v2/models",
        out_cells="reports/generated/nn_20260923/spectrum/cell_scores.csv.gz",
        out_compact="docs/nn_v2/donor_celltype_scores.csv.gz",
        exclude_chr21=False
    )
    
    # 2. chr21 excluded ladder
    if Path("reports/generated/nn_20260923/chr21_excluded/models").exists():
        run_export(
            protocol_path=args.protocol,
            models_dir="reports/generated/nn_20260923/chr21_excluded/models",
            out_cells="reports/generated/nn_20260923/spectrum/cell_scores_chr21_excluded.csv.gz",
            out_compact="docs/nn_v2/donor_celltype_scores_chr21_excluded.csv.gz",
            exclude_chr21=True
        )

if __name__ == "__main__":
    main()
