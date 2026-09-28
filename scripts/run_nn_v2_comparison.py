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
from p22.data.nn_fold import _rna_lognorm, _hvg_indices, _atac_tfidf, _qc_matrix, QC_RAW_COLUMNS, NUISANCE_CATEGORICAL, LABEL_DISEASE, _array_sha256
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


def _make_synthetic_inputs(seed=42, protocol=None):
    rng = np.random.default_rng(seed)
    n_cells = 600
    n_genes = 300
    
    regions = None
    if protocol is not None and "representation" in protocol:
        try:
            with open(protocol["representation"]["atac"]["region_set_config"]) as f:
                atac_regions = json.load(f)
            union = set()
            for item in atac_regions["per_fold"]:
                union.update(item["regions"])
            regions = sorted(list(union))
        except Exception:
            pass
            
    if not regions:
        n_regions = 200
        regions = [f"chr1:{i}-{i+100}" for i in range(n_regions)]
    else:
        n_regions = len(regions)

    
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
    exclude_chr21, model_seed, cfg, force_include_chr21=False,
):
    try:
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        t0 = time.time()
        
        with open(protocol["representation"]["atac"]["region_set_config"]) as f:
            atac_regions = json.load(f)
        fold_regions = None
        for item in atac_regions["per_fold"]:
            if item["repeat"] == repeat and item["fold"] == fold:
                fold_regions = item["regions"]
                break
        if fold_regions is None:
            raise ValueError(f"Could not find regions for repeat {repeat} fold {fold}")
        region_rows = region_indices(inputs, fold_regions)

        force_mask = inputs.chr21_gene_mask() if force_include_chr21 else None
        fold_arrays = prepare_nn_fold(
            inputs,
            train_rows,
            test_rows,
            region_rows,
            n_hvg=protocol["representation"]["rna"].get("n_hvg", 2000),
            exclude_chr21=exclude_chr21,
            force_include_gene_mask=force_mask,
        )
        
        if arm_name.startswith("R4_"):
            from p22.data.nn_fold import _rna_lognorm, _atac_tfidf
            from p22.models.program_tokens import fit_programs, program_activities, annotate_programs
            
            # Recreate unscaled non-negative matrices for NMF
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
            
            fold_arrays.evidence["programs"] = annotate_programs(
                rna_nmf, atac_nmf, fold_arrays.gene_ids, fold_arrays.region_ids
            )

        if arm_name == "latent_pca_lsi_head":
            from sklearn.decomposition import PCA, TruncatedSVD
            
            rna_dense = np.asarray(fold_arrays.rna, dtype=np.float32)
            atac_dense = np.asarray(fold_arrays.atac, dtype=np.float32)
            
            rna_pca = PCA(n_components=32, random_state=model_seed)
            atac_svd = TruncatedSVD(n_components=32, random_state=model_seed)
            
            rna_pca.fit(rna_dense[fold_arrays.train_position])
            atac_svd.fit(atac_dense[fold_arrays.train_position])
            
            fold_arrays.rna = np.concatenate([
                rna_pca.transform(rna_dense), 
                atac_svd.transform(atac_dense)
            ], axis=1).astype(np.float32)
            fold_arrays.atac = np.zeros((fold_arrays.atac.shape[0], 0), dtype=np.float32)

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
        # Sklearn controls discard val and have no hyperparameter search in this
        # runner; fit them on the full outer train so hold-out donors are not
        # wasted (positive-control and ladder control arms).
        _CONTROL_FIT_FULL_TRAIN = {
            "logreg_rna",
            "logreg_concat",
            "pseudobulk_rna_logistic",
            "chr21_dosage",
            "majority",
        }
        if arm_name in _CONTROL_FIT_FULL_TRAIN:
            inner_train_pos = np.arange(len(train_rows))
            inner_val_pos = inner_train_pos
        
        def _make_arm_data(pos):
            views = {}
            if arm_name.startswith("logreg_rna") or arm_name in {"pseudobulk_rna_logistic", "chr21_dosage", "majority", "latent_pca_lsi_head"}:
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


# Absolute main-checkout run root: do not copy ladder_v2 into finish-base.
_SEEDS_V2_ROOT = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/seeds_v2"
)
_LADDER_V2_ROOT = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v2"
)
_EXPECTED_R3_CA_PARAMS = 384250
_EXPECTED_R3_TC_PARAMS = 380026


def _reuse_ladder_v2_as_m0_s22(dest: Path) -> None:
    """m_0_s_22 under frozen protocol is the accepted ladder_v2 R3_ca/R3_tc folds."""
    import shutil

    src_folds = _LADDER_V2_ROOT / "folds"
    dest_folds = dest / "folds"
    dest_folds.mkdir(parents=True, exist_ok=True)
    n = 0
    for arm in ("R3_ca", "R3_tc"):
        for src in sorted(src_folds.glob(f"*_{arm}.json")):
            shutil.copy2(src, dest_folds / src.name)
            n += 1
    if n != 50:
        raise RuntimeError(f"expected 50 R3_ca/R3_tc folds from ladder_v2, got {n}")
    (dest / "run.json").write_text(
        json.dumps(
            {
                "folds_expected": 50,
                "folds_done": 50,
                "failures": [],
                "source": str(_LADDER_V2_ROOT),
                "reused_arms": ["R3_ca", "R3_tc"],
                "model_seed": 0,
                "sampling_seed": 22,
            },
            indent=2,
        )
        + "\n"
    )


def _assert_seed_fold_protocol(folds_dir: Path) -> dict:
    """Reject buggy ~99k-width folds; require frozen ladder_v2 widths."""
    counts = {"R3_ca": [], "R3_tc": []}
    for path in folds_dir.glob("*.json"):
        with open(path) as fp:
            rec = json.load(fp)
        arm = rec["arm"]
        if arm not in counts:
            continue
        counts[arm].append(int(rec["parameter_count"]))
    for arm, expected in (
        ("R3_ca", _EXPECTED_R3_CA_PARAMS),
        ("R3_tc", _EXPECTED_R3_TC_PARAMS),
    ):
        if len(counts[arm]) != 25:
            raise RuntimeError(f"{folds_dir}: expected 25 {arm} folds, got {len(counts[arm])}")
        bad = [c for c in counts[arm] if c != expected]
        if bad:
            raise RuntimeError(
                f"{folds_dir}: {arm} parameter_count {bad[0]} != expected {expected} "
                "(buggy-protocol seed run; do not summarize)"
            )
    return {
        "R3_ca_parameter_count": _EXPECTED_R3_CA_PARAMS,
        "R3_tc_parameter_count": _EXPECTED_R3_TC_PARAMS,
        "n_folds": 50,
    }


def _load_repeats_seed(folds_dir: Path):
    per_repeat = {}
    for path in Path(folds_dir).glob("*.json"):
        with open(path) as fp:
            rec = json.load(fp)
        rep = rec["repeat"]
        arm = rec["arm"]
        if arm not in ("R3_ca", "R3_tc"):
            continue
        per_repeat.setdefault(rep, {}).setdefault(arm, []).append(
            pd.DataFrame(
                {
                    "donor_id": rec["donor_ids"],
                    "label": rec["donor_labels"],
                    "probability": rec["donor_probabilities"],
                }
            )
        )
    repeats = []
    for rep in sorted(per_repeat.keys()):
        entry = {"repeat": rep}
        for arm in per_repeat[rep]:
            entry[arm] = pd.concat(per_repeat[rep][arm], ignore_index=True)
        repeats.append(entry)
    return repeats


def _run_seed_sensitivity(args) -> int:
    """N12: fixed-protocol init/sampling seed sensitivity against ladder_v2 widths."""
    import subprocess

    from p22.eval.repeated_comparison import repeated_primary_contrast

    m_seeds = [0, 1, 2, 3, 4]
    s_seeds = [23, 24]
    runs = [(m, 22) for m in m_seeds] + [(0, s) for s in s_seeds]
    seeds_root = _SEEDS_V2_ROOT
    seeds_root.mkdir(parents=True, exist_ok=True)

    for m, s in runs:
        out_dir = seeds_root / f"m_{m}_s_{s}"
        if m == 0 and s == 22:
            logging.info("Reusing ladder_v2 R3_ca/R3_tc as m_0_s_22 under %s", out_dir)
            _reuse_ladder_v2_as_m0_s22(out_dir)
            _assert_seed_fold_protocol(out_dir / "folds")
            continue
        cmd = [
            sys.executable,
            __file__,
            "--protocol",
            str(args.protocol),
            "--out",
            str(out_dir),
            "--arms",
            "R3_ca",
            "R3_tc",
            "--model-seed",
            str(m),
            "--sampling-seed",
            str(s),
            "--resume",
            "--workers",
            str(args.workers if args.workers else 5),
        ]
        logging.info("Running fixed-protocol seed m=%s s=%s -> %s", m, s, out_dir)
        subprocess.run(cmd, check=True)
        _assert_seed_fold_protocol(out_dir / "folds")

    results = {
        "record_type": "nn_v2_seed_sensitivity",
        "protocol_source": str(args.protocol.resolve()),
        "ladder_source": str(_LADDER_V2_ROOT),
        "seeds_root": str(seeds_root),
        "rejected_buggy_seeds_root": str(
            Path("/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/seeds")
        ),
        "expected_parameter_counts": {
            "R3_ca": _EXPECTED_R3_CA_PARAMS,
            "R3_tc": _EXPECTED_R3_TC_PARAMS,
        },
        "runs": {},
    }
    model_seed_estimates = []
    sampling_seed_estimates = []

    for m, s in runs:
        key = f"m_{m}_s_{s}"
        folds_dir = seeds_root / key / "folds"
        protocol_info = _assert_seed_fold_protocol(folds_dir)
        repeats = _load_repeats_seed(folds_dir)
        diff_stats = repeated_primary_contrast(repeats, model="R3_ca", reference="R3_tc")
        est = float(diff_stats["estimate"])
        ci = [float(diff_stats["interval"][0]), float(diff_stats["interval"][1])]
        entry = {
            "estimate": est,
            "ci": ci,
            "model_seed": m,
            "sampling_seed": s,
            **protocol_info,
            "source": "ladder_v2_reuse" if (m == 0 and s == 22) else str(folds_dir.parent),
        }
        results["runs"][key] = entry
        # Flat keys retained for decision-tree consumers / prior schema.
        results[key] = {"estimate": est, "ci": ci}
        if s == 22:
            model_seed_estimates.append(est)
        if m == 0:
            sampling_seed_estimates.append(est)

    model_spread = max(model_seed_estimates) - min(model_seed_estimates)
    sampling_spread = max(sampling_seed_estimates) - min(sampling_seed_estimates)
    results["model_seed_spread"] = float(model_spread)
    results["sampling_seed_spread"] = float(sampling_spread)

    with open("docs/nn_v2/ladder_summary.json") as f:
        lsum = json.load(f)
    outcome = lsum.get("outcome", "")
    labels = []
    if outcome.startswith("A_"):
        n_above = sum(1 for e in model_seed_estimates if e >= 0.07)
        if n_above >= 4:
            labels.append("A_ROBUST_INIT")
        else:
            labels.append("A_FRAGILE")
    else:
        labels.append("SPREAD_ONLY")
    if sampling_spread > 0.07:
        labels.append("SAMPLING_SENSITIVE")
    results["ladder_outcome"] = outcome
    results["labels"] = labels

    Path("docs/nn_v2").mkdir(parents=True, exist_ok=True)
    with open("docs/nn_v2/seed_sensitivity.json", "w") as f:
        json.dump(results, f, indent=2)
        f.write("\n")

    logging.info(
        "N12 seed sensitivity done: model_spread=%.4f sampling_spread=%.4f labels=%s",
        model_spread,
        sampling_spread,
        labels,
    )
    return 0


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
    parser.add_argument("--summarize-chr21", action="store_true")
    parser.add_argument("--seed-sensitivity", action="store_true")
    parser.add_argument("--model-seed", type=int, default=0)
    parser.add_argument("--sampling-seed", type=int, default=22)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--n10b", action="store_true")
    args = parser.parse_args(argv)
    
    # Seed-sensitivity must not fall through into a full ladder train on --out.
    if getattr(args, "seed_sensitivity", False):
        return _run_seed_sensitivity(args)

    args.out.mkdir(parents=True, exist_ok=True)

        
    if args.n10b:
        import subprocess, shutil
        out_dir = Path("reports/generated/nn_20260923/reproduction")
        if out_dir.exists():
            shutil.rmtree(out_dir)
        import run_real_paired_comparison as rpc
        rpc.ALL_FAMILIES = ("cross_attention", "token_concat")
        try:
            with open("configs/nn_inputs_2026-09-23.json") as f:
                input_manifest = json.load(f)
            h5ad_path = input_manifest["inputs"]["h5ad"]["path"]
            atac_path = input_manifest["inputs"]["atac_tiebreak_counts"]["path"]
            regions_path = input_manifest["inputs"]["region_sets_sha256_json"]["path"]
            
            # create the missing union bed file expected by the acceptance gate
            os.makedirs("reports/generated/atac_tiebreak_sensitivity_20260921", exist_ok=True)
            shutil.copy(input_manifest["inputs"]["tracked_union_bed"]["path"], "reports/generated/atac_tiebreak_sensitivity_20260921/union_sha256.bed")
            
            rpc.main([
                "--output-dir", str(out_dir),
                "--h5ad", h5ad_path,
                "--atac-matrix", atac_path,
                "--region-sets", regions_path
            ])
        except SystemExit as e:
            if e.code != 0: raise RuntimeError("Reproduction run failed")
        with open(out_dir / "run.json") as f:
            rep = json.load(f)
        repro_estimate = rep["primary_comparison"]["estimate"]
        
        with open(args.protocol) as f:
            protocol = json.load(f)
        arms = protocol["arms"]
        
        with open("configs/nn_inputs_2026-09-23.json") as f:
            input_manifest = json.load(f)
        inputs = load_nn_inputs(
            input_manifest["inputs"]["h5ad"]["path"],
            input_manifest["inputs"]["atac_tiebreak_counts"]["path"],
            protocol["sampling"]["cap_per_donor"], 
            args.sampling_seed, 
            union_bed=input_manifest["inputs"]["tracked_union_bed"]["path"]
        )
        splits = list(iter_repeated_stratified_group_folds(
            inputs.metadata["donor_id"].to_numpy(),
            (inputs.metadata["disease"] == "complete trisomy 21").astype(int).to_numpy(),
            n_repeats=1, n_folds=5, base_seed=protocol["splits"]["split_seed"]
        ))
        split = splits[0]
        cfg = protocol["architecture"].copy()
        cfg.update(protocol["training"])
        cfg["seed"] = args.model_seed
        
        total_elapsed = 0.0
        for arm in arms:
            rec, err = worker_task(args.out, arm, split.repeat, split.fold, split.train_index, split.test_index, inputs, protocol, False, args.model_seed, cfg)
            if err: raise RuntimeError(err)
            total_elapsed += rec["elapsed"]
            
        projected = total_elapsed * 25.0 / 14.0 / 3600.0
        cap = 512 if projected > 6 else 1000
        Path("docs/nn_v2").mkdir(parents=True, exist_ok=True)
        repro_dict = {
            "estimate": float(repro_estimate),
            "expected": -0.02,
            "abs_diff": abs(float(repro_estimate) - (-0.02))
        }
        with open("docs/nn_v2/ladder_timing.json", "w") as f:
            json.dump({
                "smoke_seconds": float(total_elapsed),
                "projected_hours": float(projected),
                "reproduction": repro_dict,
                "cap": cap
            }, f, indent=2)
        if cap == 512:
            with open("configs/nn_protocol_v2_amendment_cap512.json", "w") as f:
                json.dump({"reason": f"projected {projected:.1f}h > 6h", "cap_per_donor": 512}, f, indent=2)
        return 0
    
    with open(args.protocol) as f:
        protocol = json.load(f)
        
    arms = args.arms if args.arms else protocol["arms"]
    
    if args.synthetic:
        inputs = _make_synthetic_inputs(args.sampling_seed, protocol)
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
            cfg = protocol["architecture"].copy()
            cfg.update(protocol["training"])
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

    # Never clobber docs/nn_v2/ladder_run.json from seed/chr21/partial arm runs.
    # Only refresh the tracked ladder run record when writing into ladder_v2 itself.
    out_resolved = args.out.resolve()
    if out_resolved.name == "ladder_v2" or out_resolved == _LADDER_V2_ROOT.resolve():
        Path("docs/nn_v2").mkdir(parents=True, exist_ok=True)
        with open("docs/nn_v2/ladder_run.json", "w") as f:
            json.dump(run_record, f, indent=2)
        
    if args.summarize_chr21:
        from p22.eval.repeated_comparison import repeated_primary_contrast, repeated_model_accuracy
        
        def load_repeats(folds_dir):
            per_repeat = {}
            arms = set()
            for f in Path(folds_dir).glob("*.json"):
                with open(f) as fp:
                    rec = json.load(fp)
                    rep = rec["repeat"]
                    arm = rec["arm"]
                    arms.add(arm)
                    
                    if rep not in per_repeat:
                        per_repeat[rep] = {}
                    if arm not in per_repeat[rep]:
                        per_repeat[rep][arm] = []
                        
                    df = pd.DataFrame({
                        "donor_id": rec["donor_ids"],
                        "label": rec["donor_labels"],
                        "probability": rec["donor_probabilities"]
                    })
                    per_repeat[rep][arm].append(df)
                    
            repeats = []
            for rep in sorted(per_repeat.keys()):
                entry = {"repeat": rep}
                for arm in per_repeat[rep]:
                    entry[arm] = pd.concat(per_repeat[rep][arm], ignore_index=True)
                repeats.append(entry)
            return repeats, arms

        # With-chr21 baseline follows CANONICAL_LADDER (ladder_v3 after V4);
        # never the superseded buggy ladder/ directory. Excluded folds come
        # from this run's --out (chr21_excluded_v3 under P1).
        canon_ptr = Path("docs/nn_v2/v5/CANONICAL_LADDER.txt")
        if canon_ptr.is_file():
            ladder_root = Path(canon_ptr.read_text().strip())
        else:
            ladder_root = Path("reports/generated/nn_20260923/ladder_v3")
        ladder_dir = ladder_root / "folds"
        excluded_dir = args.out / "folds"

        ladder_repeats, ladder_arms = load_repeats(ladder_dir)
        excluded_repeats, excluded_arms = load_repeats(excluded_dir)
        
        arms_to_check = ["R3_ca", "R3_tc", "logreg_rna", "logreg_concat"]
        
        results = {}
        
        for arm in arms_to_check:
            if arm not in excluded_arms or arm not in ladder_arms:
                continue
                
            acc_ladder = repeated_model_accuracy(ladder_repeats, model=arm)
            acc_excluded = repeated_model_accuracy(excluded_repeats, model=arm)
            
            joint_repeats = []
            for l_rep, e_rep in zip(ladder_repeats, excluded_repeats):
                joint = {"repeat": l_rep["repeat"]}
                joint[f"{arm}_with"] = l_rep.get(arm, pd.DataFrame())
                joint[f"{arm}_without"] = e_rep.get(arm, pd.DataFrame())
                if not joint[f"{arm}_with"].empty and not joint[f"{arm}_without"].empty:
                    joint_repeats.append(joint)
                
            diff_stats = repeated_primary_contrast(joint_repeats, model=f"{arm}_with", reference=f"{arm}_without")
            
            results[arm] = {
                "ba_with_chr21": acc_ladder.get("mean", 0.0),
                "ba_without_chr21": acc_excluded.get("mean", 0.0),
                "paired_difference": diff_stats.get("estimate", 0.0),
                "ci": diff_stats.get("interval", [0.0, 0.0])
            }
            
        Path("docs/nn_v2").mkdir(parents=True, exist_ok=True)
        with open("docs/nn_v2/chr21_excluded.json", "w") as f:
            json.dump(results, f, indent=2)
            
        # Write paragraph to ROBUSTNESS.md
        with open("docs/nn_v2/ROBUSTNESS.md", "a") as f:
            f.write("\n## chr21-excluded sensitivity\n\n")
            f.write("Model performance was re-evaluated after excluding chromosome 21 features. ")
            
            all_below_55 = True
            any_above_60 = False
            arm_above_60 = None
            for arm in arms_to_check:
                if arm in results:
                    ba = results[arm]["ba_without_chr21"]
                    if ba > 0.55:
                        all_below_55 = False
                    if ba >= 0.60:
                        any_above_60 = True
                        arm_above_60 = arm
            
            if all_below_55:
                label = "DOSAGE_DOMINATED"
                desc = "All models perform near chance without chr21, suggesting predictions are dosage dominated."
            elif any_above_60:
                label = f"BEYOND_DOSAGE ({arm_above_60})"
                desc = f"At least one arm ({arm_above_60}) maintains performance above 0.60 without chr21, showing signal beyond dosage."
            else:
                label = "PARTIAL_DOSAGE"
                desc = "Models lose some performance but remain partially predictive without chr21."
                
            f.write(f"Results indicate {label}. {desc}\n")

    return 0 if not failures else 1

if __name__ == "__main__":
    sys.exit(main())

