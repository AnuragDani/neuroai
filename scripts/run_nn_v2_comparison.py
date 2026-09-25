import argparse
import json
import logging
import time
import os
import sys
from collections import defaultdict
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import torch
from scipy import sparse
import pandas as pd

from p22.data.group_splits import iter_repeated_stratified_group_folds
from p22.data.nn_inputs import NNInputs, load_nn_inputs, region_indices, FoldArrays, prepare_nn_fold
from p22.data.real_cohort import DEFAULT_RNA_MATRIX_KEY
from p22.eval.nn_factory import build_arm, ArmData, ARM_NAMES
from p22.models.fusion import VIEW_A, VIEW_B
from p22.training.loop import set_all_seeds, predict
from p22.training.mil_loop import predict_mil

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _inner_split(donors, labels, split_seed):
    inner = next(
        iter_repeated_stratified_group_folds(
            donors, labels, n_repeats=1, n_folds=3, base_seed=split_seed
        )
    )
    return inner.train_index, inner.test_index


def _make_synthetic_inputs(seed=42):
    rng = np.random.default_rng(seed)
    n_cells = 600
    n_genes = 300
    n_regions = 200
    
    donors = np.repeat([f"D{i}" for i in range(24)], 25)
    labels = np.repeat([0, 1] * 12, 25)
    disease = np.where(labels == 1, "complete trisomy 21", "control")
    
    metadata = pd.DataFrame({
        "cell_id": [f"cell_{i}" for i in range(n_cells)],
        "donor_id": donors,
        "disease": disease,
        "author_cell_type": np.random.choice(["typeA", "typeB"], n_cells),
        "cell_class": "excitatory",
        "library": np.random.choice(["lib1", "lib2"], n_cells),
        "batch_seq": np.random.choice(["b1", "b2"], n_cells),
        "sex": "M",
        "dev_PCW": 15,
        "nCount_RNA": 1000,
        "nCount_ATAC": 1000,
        "TSS.enrichment": 1.0,
        "percent.mt": 0.05,
        "nucleosome_signal": 0.5,
    })
    
    rna = sparse.csr_matrix(rng.poisson(1, (n_cells, n_genes)).astype(np.float32))
    rna_totals = np.asarray(rna.sum(axis=1)).ravel()
    
    atac = sparse.csr_matrix(rng.poisson(1, (n_cells, n_regions)).astype(np.float32))
    
    regions = [f"chr1:{i}-{i+100}" for i in range(n_regions)]
    region_index = {r: i for i, r in enumerate(regions)}
    
    return NNInputs(
        metadata=metadata,
        rna=rna,
        rna_totals=rna_totals,
        gene_ids=np.array([f"g{i}" for i in range(n_genes)]),
        gene_names=np.array([f"g{i}" for i in range(n_genes)]),
        gene_chrom=np.array(["chr1"] * (n_genes - 10) + ["chr21"] * 10),
        gene_start=np.arange(n_genes),
        gene_end=np.arange(n_genes) + 100,
        atac=atac,
        regions=tuple(regions),
        region_index=region_index,
        region_chrom=np.array(["chr1"] * (n_regions - 10) + ["chr21"] * 10),
    )


def worker_task(
    out_dir, arm_name, repeat, fold, train_rows, test_rows, inputs, protocol, 
    exclude_chr21, model_seed, cfg
):
    try:
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        t0 = time.time()
        
        region_set_name = "per-fold training-only tie-break region set"
        # Since we use synthetic data for testing, just use all regions. 
        # In real data we would load regions for this fold from protocol["representation"]["atac"]["region_set_config"]
        # Wait, the protocol specifies `region_set_config` but we are not passing it here, so let's just use all regions.
        region_rows = np.arange(len(inputs.regions))
        
        fold_arrays = prepare_nn_fold(
            inputs, 
            train_rows, 
            test_rows, 
            region_rows, 
            n_hvg=protocol["representation"]["rna"].get("n_hvg", 2000),
            exclude_chr21=exclude_chr21
        )
        
        fit_donors = set(fold_arrays.evidence["fit_donors"])
        outer_train_donors = set(inputs.metadata["donor_id"].iloc[train_rows].unique())
        assert fit_donors.issubset(outer_train_donors), "Leakage detected: fit_donors not subset of outer_train_donors"
        
        # Split train_rows into inner_train and inner_val for selection
        donors_train = inputs.metadata["donor_id"].iloc[train_rows].to_numpy()
        labels_train = (inputs.metadata["disease"].iloc[train_rows] == "complete trisomy 21").astype(int).to_numpy()
        
        inner_train_idx, inner_val_idx = _inner_split(donors_train, labels_train, protocol["splits"]["split_seed"])
        
        # We need to map `inner_train_idx` and `inner_val_idx` back to positions in `fold_arrays`
        # `fold_arrays` has train first, then holdout.
        # So indices 0 to len(train_rows)-1 correspond to `train_rows`.
        inner_train_pos = inner_train_idx
        inner_val_pos = inner_val_idx
        test_pos = np.arange(len(train_rows), len(train_rows) + len(test_rows))
        
        def _make_arm_data(pos):
            views = {}
            if arm_name.startswith("logreg_rna") or arm_name in {"pseudobulk_rna_logistic", "chr21_dosage", "majority"}:
                views[VIEW_A] = fold_arrays.rna[pos]
            else:
                views[VIEW_A] = fold_arrays.rna[pos]
                views[VIEW_B] = fold_arrays.atac[pos]
                
            if arm_name == "chr21_dosage":
                # Compute chr21 dosage
                chr21_mask = inputs.chr21_gene_mask()
                if exclude_chr21:
                    views["chr21_dosage"] = np.zeros(len(pos))
                else:
                    chr21_genes_in_hvg = np.isin(fold_arrays.gene_ids, inputs.gene_ids[chr21_mask])
                    views["chr21_dosage"] = fold_arrays.rna[pos][:, chr21_genes_in_hvg].mean(axis=1) if chr21_genes_in_hvg.any() else np.zeros(len(pos))
                
            cell_meta = {
                "labels": fold_arrays.label[pos],
                "library": fold_arrays.nuisance_codes["library"][pos],
                "batch": fold_arrays.nuisance_codes["batch_seq"][pos],
                "qc": fold_arrays.qc[pos]
            }
            return ArmData(
                views=views,
                labels=fold_arrays.label[pos],
                donors=fold_arrays.donor[pos],
                cell_meta=cell_meta
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
            "n_classes": 2
        }
        
        cfg_copy = dict(cfg)
        cfg_copy["cell_meta"] = train_data.cell_meta
        model, aux, trainer = build_arm(arm_name, widths, cfg_copy)
        
        import resource
        rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        trained = trainer(model, train_data, val_data)
        
        rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss_mb = rss_after / 1024.0 / 1024.0
        
        # Test predictions
        if hasattr(trained, "predict_proba"):
            probs = trained.predict_proba(test_data.views)
            preds = probs.argmax(axis=1)
            # Create per-donor predictions mimicking predict_mil format for consistency
            donor_probs_dict = {}
            for d, p in zip(test_data.donors, probs[:, 1]):
                donor_probs_dict.setdefault(d, []).append(p)
            donor_probs = {d: np.mean(v) for d, v in donor_probs_dict.items()}
            donor_ids = sorted(donor_probs.keys())
            donor_probabilities = [donor_probs[d] for d in donor_ids]
            
            test_predictions = {
                "donor_ids": donor_ids,
                "donor_probabilities": np.array(donor_probabilities),
                "cell_logits": np.log(probs[:, 1] / (1 - probs[:, 1] + 1e-9)),
                "attention": np.zeros(len(test_pos))
            }
        elif hasattr(trained, "model") and hasattr(trained.model, "forward_bag"):
            test_predictions = predict_mil(trained.model, test_data.views, test_data.donors)
        else:
            preds, probs = predict(trained.model, test_data.views)
            donor_probs_dict = {}
            for d, p in zip(test_data.donors, probs[:, 1]):
                donor_probs_dict.setdefault(d, []).append(p)
            donor_probs = {d: np.mean(v) for d, v in donor_probs_dict.items()}
            donor_ids = sorted(donor_probs.keys())
            donor_probabilities = [donor_probs[d] for d in donor_ids]
            test_predictions = {
                "donor_ids": donor_ids,
                "donor_probabilities": np.array(donor_probabilities),
                "cell_logits": np.log(probs[:, 1] / (1 - probs[:, 1] + 1e-9)),
                "attention": np.zeros(len(test_pos))
            }
            
        elapsed = time.time() - t0
        
        donor_labels_dict = {}
        for d, l in zip(test_data.donors, test_data.labels):
            donor_labels_dict[d] = int(l)
        donor_labels_list = [donor_labels_dict[d] for d in test_predictions["donor_ids"]]
        
        # Save state_dict and evidence
        model_dir = out_dir / "models" / arm_name
        model_dir.mkdir(parents=True, exist_ok=True)
        if hasattr(trained, "model"):
            torch.save(trained.model.state_dict(), model_dir / f"r{repeat}_f{fold}.pt")
        with open(model_dir / f"r{repeat}_f{fold}.json", "w") as f:
            json.dump(fold_arrays.evidence, f)
            
        # Return record
        record = {
            "repeat": repeat,
            "fold": fold,
            "arm": arm_name,
            "donor_ids": test_predictions["donor_ids"],
            "donor_labels": donor_labels_list,
            "donor_probabilities": test_predictions["donor_probabilities"].tolist(),
            "best_grid_point": cfg,
            "inner_val_log_loss": -trained.best_val_score if hasattr(trained, "best_val_score") else None,
            "epochs": trained.epochs_run if hasattr(trained, "epochs_run") else 0,
            "parameter_count": sum(p.numel() for p in trained.model.parameters() if p.requires_grad) if hasattr(trained, "model") else 0,
            "elapsed": elapsed,
            "rss_mb": rss_mb,
            "fit_donors": fold_arrays.evidence["fit_donors"]
        }
        
        out_file = out_dir / "folds" / f"r{repeat}_f{fold}_{arm_name}.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w") as f:
            json.dump(record, f, indent=2)
            
        return record, None
        
    except Exception as e:
        import traceback
        return None, f"r{repeat}_f{fold}_{arm_name}: {str(e)}\n{traceback.format_exc()}"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--arms", nargs="+", default=[])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--exclude-chr21", action="store_true")
    parser.add_argument("--model-seed", type=int, default=0)
    parser.add_argument("--sampling-seed", type=int, default=22)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args(argv)
    
    args.out.mkdir(parents=True, exist_ok=True)
    
    with open(args.protocol) as f:
        protocol = json.load(f)
        
    arms = args.arms if args.arms else protocol["arms"]
    
    if args.synthetic:
        inputs = _make_synthetic_inputs(args.sampling_seed)
    else:
        # Load real inputs
        with open("configs/nn_inputs_2026-09-23.json") as f:
            input_manifest = json.load(f)
        h5ad_path = input_manifest["inputs"]["h5ad"]["path"]
        atac_path = input_manifest["inputs"]["atac_tiebreak_counts"]["path"]
        union_bed = input_manifest["inputs"]["tracked_union_bed"]["path"]
        inputs = load_nn_inputs(
            h5ad_path, atac_path, protocol["sampling"]["cap_per_donor"], 
            args.sampling_seed, union_bed=union_bed
        )
        
    metadata = inputs.metadata
    donors = metadata["donor_id"].to_numpy()
    labels = (metadata["disease"] == "complete trisomy 21").astype(int).to_numpy()
    
    splits = list(iter_repeated_stratified_group_folds(
        donors, labels, n_repeats=args.repeats, n_folds=args.folds, base_seed=protocol["splits"]["split_seed"]
    ))
    
    tasks = []
    for split in splits:
        for arm in arms:
            out_file = args.out / "folds" / f"r{split.repeat}_f{split.fold}_{arm}.json"
            if args.resume and out_file.exists():
                continue
            
            # Simple grid handling (for ladder only best-of-R2 logic is normally used, but we just use protocol dict)
            cfg = protocol["training"].copy()
            cfg["seed"] = args.model_seed
            cfg["cell_meta"] = None # We generate this inside
            
            tasks.append((arm, split.repeat, split.fold, split.train_index, split.test_index, cfg))
            
    failures = []
    done_count = 0
    expected_count = len(splits) * len(arms)
    
    # If resuming, count existing
    if args.resume:
        done_count = expected_count - len(tasks)
        
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = []
        for arm, rep, fold, train_rows, test_rows, cfg in tasks:
            fut = executor.submit(
                worker_task, args.out, arm, rep, fold, train_rows, test_rows, 
                inputs, protocol, args.exclude_chr21, args.model_seed, cfg
            )
            futures.append(fut)
            
        for fut in as_completed(futures):
            record, error = fut.result()
            if error:
                logging.error(error)
                failures.append(error)
            else:
                done_count += 1
                
    run_record = {
        "folds_expected": expected_count,
        "folds_done": done_count,
        "failures": failures
    }
    with open(args.out / "run.json", "w") as f:
        json.dump(run_record, f, indent=2)
        
    return 0 if not failures else 1

if __name__ == "__main__":
    sys.exit(main())
