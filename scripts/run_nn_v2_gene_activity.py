import argparse
import json
import logging
import time
import sys
from pathlib import Path

import numpy as np
import torch

from p22.data.group_splits import iter_repeated_stratified_group_folds
from p22.data.nn_inputs import load_nn_inputs, prepare_nn_fold
from p22.eval import nn_factory
from p22.models.fusion import VIEW_A, VIEW_B
import run_nn_v2_comparison

# Patch nn_factory
from p22.models.gene_aligned import GeneAlignedCrossAttention, GeneAlignedTokenConcat
from p22.models.mil import MILWrapper

original_build_arm = nn_factory.build_arm

def new_build_arm(arm_name, widths, cfg=None):
    if arm_name in ("GA_ca", "GA_tc"):
        options = {**nn_factory.DEFAULT_ARCH, **nn_factory.DEFAULT_TRAIN, **dict(cfg or {})}
        num_genes = widths["n_features_a"]
        
        if arm_name == "GA_ca":
            base = GeneAlignedCrossAttention(
                num_genes=num_genes, 
                dim=options["embed_dim"],
                heads=options["n_heads"],
                n_classes=widths.get("n_classes", 2),
                dropout=options["dropout"],
                k_nearest=5
            )
        else:
            base = GeneAlignedTokenConcat(
                num_genes=num_genes,
                dim=options["embed_dim"],
                n_classes=widths.get("n_classes", 2),
                dropout=options["dropout"]
            )
            
        fused_dim = 2 * options["embed_dim"]
        model = MILWrapper(base, dim=fused_dim, attn_dim=options["attn_dim"])
        
        aux = []
        _adv, loss = nn_factory._adversary(model, fused_dim, widths, options)
        aux.append(loss)
        aux.append(nn_factory._add_pairing(model, options["embed_dim"], options))
        
        return model, tuple(aux), nn_factory._mil_trainer(tuple(aux), options)
        
    return original_build_arm(arm_name, widths, cfg)

nn_factory.build_arm = new_build_arm
nn_factory.ARM_NAMES = tuple(list(nn_factory.ARM_NAMES) + ["GA_ca", "GA_tc"])

# Replace worker task logic to handle GA_ arms and gene activity regions
original_worker_task = run_nn_v2_comparison.worker_task

def worker_task(
    out_dir, arm_name, repeat, fold, train_rows, test_rows, inputs, protocol, 
    exclude_chr21, model_seed, cfg
):
    try:
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        t0 = time.time()
        
        # Use ALL regions from the ATAC matrix (which is the gene activity matrix)
        region_rows = np.arange(len(inputs.regions))
        
        fold_arrays = prepare_nn_fold(
            inputs, 
            train_rows, 
            test_rows, 
            region_rows, 
            n_hvg=protocol["representation"]["rna"].get("n_hvg", 2000),
            exclude_chr21=exclude_chr21
        )
        
        if arm_name in ("GA_ca", "GA_tc"):
            from p22.data.nn_fold import _rna_lognorm, _atac_tfidf
            from sklearn.preprocessing import StandardScaler
            
            # Align RNA to ATAC features
            bed_lines = Path("configs/nn_gene_activity_2026-09-23.bed").read_text().splitlines()
            atac_gene_names = [line.split("\t")[3] for line in bed_lines if line.strip()]
            
            name_to_idx = {name: i for i, name in enumerate(inputs.gene_names)}
            selected_cols = [name_to_idx[name] for name in atac_gene_names]
            
            rna_norm = _rna_lognorm(inputs.rna, inputs.rna_totals)[:, selected_cols]
            rna_dense = np.asarray(rna_norm.todense(), dtype=np.float32)
            
            scaler = StandardScaler()
            scaler.fit(rna_dense[fold_arrays.train_position])
            fold_arrays.rna = scaler.transform(rna_dense)
            
        fit_donors = set(fold_arrays.evidence["fit_donors"])
        outer_train_donors = set(inputs.metadata["donor_id"].iloc[train_rows].unique())
        assert fit_donors.issubset(outer_train_donors), "Leakage detected: fit_donors not subset of outer_train_donors"
        
        donors_train = inputs.metadata["donor_id"].iloc[train_rows].to_numpy()
        labels_train = (inputs.metadata["disease"].iloc[train_rows] == "complete trisomy 21").astype(int).to_numpy()
        
        inner_train_idx, inner_val_idx = run_nn_v2_comparison._inner_split(donors_train, labels_train, protocol["splits"]["split_seed"])
        
        inner_train_pos = inner_train_idx
        inner_val_pos = inner_val_idx
        test_pos = np.arange(len(train_rows), len(train_rows) + len(test_rows))
        
        def _make_arm_data(pos):
            views = {}
            if arm_name.startswith("logreg_rna") or arm_name in {"pseudobulk_rna_logistic", "chr21_dosage", "majority", "latent_pca_lsi_head"}:
                views[VIEW_A] = fold_arrays.rna[pos]
            else:
                views[VIEW_A] = fold_arrays.rna[pos]
                views[VIEW_B] = fold_arrays.atac[pos]
                
            if arm_name == "chr21_dosage":
                chr21_mask = inputs.chr21_gene_mask()
                if exclude_chr21:
                    views["chr21_dosage"] = np.zeros(len(pos))
                else:
                    original_rows = np.concatenate([train_rows, test_rows])[pos]
                    chr21_counts = np.asarray(inputs.rna[original_rows][:, chr21_mask].sum(axis=1)).ravel()
                    totals = inputs.rna_totals[original_rows]
                    views["chr21_dosage"] = chr21_counts / np.maximum(totals, 1.0)
                
            cell_meta = {
                "labels": fold_arrays.label[pos],
                "library": fold_arrays.nuisance_codes["library"][pos],
                "batch": fold_arrays.nuisance_codes["batch_seq"][pos],
                "qc": fold_arrays.qc[pos]
            }
            return nn_factory.ArmData(
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
        model, aux, trainer = nn_factory.build_arm(arm_name, widths, cfg_copy)
        
        import resource
        rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        trained = trainer(model, train_data, val_data)
        
        rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss_mb = rss_after / 1024.0 / 1024.0
        
        from p22.training.loop import predict
        from p22.training.mil_loop import predict_mil
        
        if hasattr(trained, "predict_proba"):
            probs = trained.predict_proba(test_data.views)
            preds = probs.argmax(axis=1)
            donor_probs_dict = {}
            for d, p in zip(test_data.donors, probs[:, 1]):
                donor_probs_dict.setdefault(d, []).append(p)
            donor_probs = {d: np.mean(v) for d, v in donor_probs_dict.items()}
            donor_ids = sorted(donor_probs.keys())
            donor_probabilities = [donor_probs[d] for d in donor_ids]
            
            test_predictions = {
                "donor_ids": donor_ids,
                "donor_probabilities": np.array(donor_probabilities),
                "cell_logits": np.log((probs[:, 1] + 1e-9) / (1 - probs[:, 1] + 1e-9)),
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
                "cell_logits": np.log((probs[:, 1] + 1e-9) / (1 - probs[:, 1] + 1e-9)),
                "attention": np.zeros(len(test_pos))
            }
            
        elapsed = time.time() - t0
        
        donor_labels_dict = {}
        for d, l in zip(test_data.donors, test_data.labels):
            donor_labels_dict[d] = int(l)
        donor_labels_list = [donor_labels_dict[d] for d in test_predictions["donor_ids"]]
        
        model_dir = out_dir / "models" / arm_name
        model_dir.mkdir(parents=True, exist_ok=True)
        if hasattr(trained, "model"):
            torch.save(trained.model.state_dict(), model_dir / f"r{repeat}_f{fold}.pt")
        with open(model_dir / f"r{repeat}_f{fold}.json", "w") as f:
            json.dump(fold_arrays.evidence, f)
            
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
            "fit_donors": list(fold_arrays.evidence["fit_donors"])
        }
        
        out_file = out_dir / "folds" / f"r{repeat}_f{fold}_{arm_name}.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w") as f:
            json.dump(record, f, indent=2)
            
        return record, None
        
    except Exception as e:
        import traceback
        return None, f"r{repeat}_f{fold}_{arm_name}: {str(e)}\n{traceback.format_exc()}"

run_nn_v2_comparison.worker_task = worker_task

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--arms", nargs="+", default=["GA_ca", "GA_tc", "R3_ca", "R3_tc", "logreg_concat"])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--exclude-chr21", action="store_true")
    parser.add_argument("--model-seed", type=int, default=0)
    parser.add_argument("--sampling-seed", type=int, default=22)
    parser.add_argument("--atac-matrix", type=str, default="reports/generated/nn_20260923/gene_activity/counts/counts.npz")
    parser.add_argument("--atac-bed", type=str, default="configs/nn_gene_activity_2026-09-23.bed")
    args = parser.parse_args()
    
    args.out.mkdir(parents=True, exist_ok=True)
    
    with open(args.protocol) as f:
        protocol = json.load(f)
        
    with open("configs/nn_inputs_2026-09-23.json") as f:
        input_manifest = json.load(f)
        
    h5ad_path = input_manifest["inputs"]["h5ad"]["path"]
    
    inputs = load_nn_inputs(
        h5ad_path, args.atac_matrix, protocol["sampling"]["cap_per_donor"], 
        args.sampling_seed, union_bed=args.atac_bed
    )
    
    metadata = inputs.metadata
    donors = metadata["donor_id"].to_numpy()
    labels = (metadata["disease"] == "complete trisomy 21").astype(int).to_numpy()
    
    splits = list(iter_repeated_stratified_group_folds(
        donors, labels, n_repeats=args.repeats, n_folds=args.folds, base_seed=protocol["splits"]["split_seed"]
    ))
    
    tasks = []
    for split in splits:
        for arm in args.arms:
            out_file = args.out / "folds" / f"r{split.repeat}_f{split.fold}_{arm}.json"
            if args.resume and out_file.exists():
                continue
                
            cfg = protocol["architecture"].copy()
            cfg.update(protocol["training"])
            cfg["seed"] = args.model_seed
            cfg["cell_meta"] = None
            
            tasks.append((arm, split.repeat, split.fold, split.train_index, split.test_index, cfg))
            
    failures = []
    done_count = 0
    expected_count = len(splits) * len(args.arms)
    
    if args.resume:
        done_count = expected_count - len(tasks)
        
    from concurrent.futures import ProcessPoolExecutor, as_completed
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
        
    import subprocess
    subprocess.run([sys.executable, "scripts/summarize_nn_v2.py", "--run", str(args.out), "--out", "docs/nn_v2/gene_activity_results.json"], check=True)

if __name__ == "__main__":
    main()
