"""
Run held-out faithfulness interventions (N13).
"""

import json
import logging
import os
import sys
from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from concurrent.futures import ProcessPoolExecutor

from p22.data.nn_fold import prepare_nn_fold
from p22.data.nn_inputs import load_nn_inputs
from p22.eval.nn_factory import build_arm
from p22.eval.planted_signal import plant
from p22.models.fusion import VIEW_A, VIEW_B
from p22.training.mil_loop import predict_mil
from p22.training.loop import predict, train_model
from p22.eval.metrics import balanced_accuracy
from p22.data.group_splits import iter_repeated_stratified_group_folds

def clamp_to_train_mean(matrix: np.ndarray, train_matrix: np.ndarray) -> np.ndarray:
    reference = np.asarray(train_matrix, dtype=np.float64)
    return np.tile(reference.mean(axis=0), (matrix.shape[0], 1))

def permute_within_donor_celltype(
    matrix: np.ndarray, donor_ids: np.ndarray, cell_types: np.ndarray, seed: int = 0
) -> np.ndarray:
    array = np.asarray(matrix).copy()
    donors = np.asarray(donor_ids)
    types = np.asarray(cell_types)
    rng = np.random.default_rng(seed)
    for donor in np.unique(donors):
        for ct in np.unique(types):
            mask = (donors == donor) & (types == ct)
            rows = np.flatnonzero(mask)
            if rows.size < 2:
                continue
            array[rows] = array[rng.permutation(rows)]
    return array

class MockAttention(nn.Module):
    def __init__(self, fixed_context):
        super().__init__()
        self.fixed_context = fixed_context
    def forward(self, query, key, value, need_weights=False, **kwargs):
        n_cells = query.shape[0]
        context = self.fixed_context.expand(n_cells, -1, -1)
        return context, None

class MockPool(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.dim = dim
    def forward(self, h):
        n = h.shape[0]
        attention = torch.full((n,), 1.0 / n, device=h.device, dtype=h.dtype)
        pooled = h.mean(dim=0)
        return pooled, attention

class MockGate(nn.Module):
    def __init__(self, override, original_gate):
        super().__init__()
        self.override = torch.tensor(override, dtype=torch.float32)
        self.original_gate = original_gate
    def forward(self, embeddings, override=None):
        return self.original_gate(embeddings, override=self.override.to(embeddings[0].device))

def get_attention_module(model: nn.Module) -> nn.Module | None:
    if not hasattr(model, "encoder"):
        return None
    encoder = model.encoder
    if hasattr(encoder, "attention"):
        return encoder.attention
    if hasattr(encoder, "inner") and hasattr(encoder.inner, "attention"):
        return encoder.inner.attention
    return None

def get_gate_module(model: nn.Module) -> nn.Module | None:
    if hasattr(model, "gate"):
        return model.gate
    if not hasattr(model, "encoder"):
        return None
    encoder = model.encoder
    if hasattr(encoder, "gate"):
        return encoder.gate
    if hasattr(encoder, "inner") and hasattr(encoder.inner, "gate"):
        return encoder.inner.gate
    return None

def run_intervention(
    name: str,
    model: nn.Module,
    test_views: Mapping[str, np.ndarray],
    test_labels: np.ndarray,
    test_donors: np.ndarray,
    test_cell_types: np.ndarray,
    train_views: Mapping[str, np.ndarray],
    seed: int,
    baseline_donor_pred: np.ndarray,
    baseline_cell_pred: np.ndarray,
    donor_truth: np.ndarray,
    is_mil: bool = True
):
    views = dict(test_views)

    orig_pool = getattr(model, "pool", None)
    orig_attn = get_attention_module(model)
    orig_gate = get_gate_module(model)

    if name == "I1":
        views[VIEW_B] = clamp_to_train_mean(views[VIEW_B], train_views[VIEW_B])
    elif name == "I2":
        views[VIEW_A] = clamp_to_train_mean(views[VIEW_A], train_views[VIEW_A])
    elif name == "I3":
        views[VIEW_B] = permute_within_donor_celltype(views[VIEW_B], test_donors, test_cell_types, seed)
    elif name == "I4":
        if orig_attn is None:
            return None
        train_contexts = []
        def hook(module, args, output):
            context, _ = output
            train_contexts.append(context.detach().cpu())
        handle = orig_attn.register_forward_hook(hook)
        
        with torch.no_grad():
            try:
                n_train = train_views[VIEW_A].shape[0]
                for i in range(0, n_train, 1000):
                    batch_views = {k: v[i:i+1000] for k, v in train_views.items()}
                    batch_tensors = {k: torch.tensor(v, dtype=torch.float32) for k, v in batch_views.items()}
                    if hasattr(model, "forward_bag_full"):
                        model.forward_bag_full(batch_tensors)
                    else:
                        model(batch_tensors[VIEW_A], batch_tensors[VIEW_B])
            except Exception as e:
                handle.remove()
                raise e
        handle.remove()
        mean_context = torch.cat(train_contexts, dim=0).mean(dim=0, keepdim=True)
        if hasattr(model.encoder, "attention"):
            model.encoder.attention = MockAttention(mean_context)
        else:
            model.encoder.inner.attention = MockAttention(mean_context)
    elif name == "I5":
        if not is_mil: return None
        model.pool = MockPool(model.dim)
    elif name == "I6":
        if orig_gate is None:
            return None
        mock_gate = MockGate([0.5, 0.5], orig_gate)
        if hasattr(model, "gate"):
            model.gate = mock_gate
        elif hasattr(model.encoder, "gate"):
            model.encoder.gate = mock_gate
        else:
            model.encoder.inner.gate = mock_gate
    elif name == "NC":
        pass
    else:
        return None

    try:
        if is_mil:
            pred = predict_mil(model, views, test_donors)
            prob_donor = pred["donor_probabilities"]
            logits = pred["cell_logits"]
            attn = pred["attention"]
        else:
            pred = predict(model, views)
            logits = pred.logits
            import pandas as pd
            df = pd.DataFrame({"donor": test_donors, "p": pred.probabilities[:, 1]})
            prob_donor = df.groupby("donor", sort=True)["p"].mean().values
            
    finally:
        if orig_pool is not None:
            model.pool = orig_pool
        if orig_attn is not None:
            if hasattr(model.encoder, "attention"):
                model.encoder.attention = orig_attn
            elif hasattr(model.encoder, "inner") and hasattr(model.encoder.inner, "attention"):
                model.encoder.inner.attention = orig_attn
        if orig_gate is not None:
            if hasattr(model, "gate"):
                model.gate = orig_gate
            elif hasattr(model.encoder, "gate"):
                model.encoder.gate = orig_gate
            elif hasattr(model.encoder, "inner") and hasattr(model.encoder.inner, "gate"):
                model.encoder.inner.gate = orig_gate

    donor_pred = (prob_donor >= 0.5).astype(int)
    ba_after = balanced_accuracy(donor_truth, donor_pred)
    ba_before = balanced_accuracy(donor_truth, baseline_donor_pred)
    ba_drop = ba_before.value - ba_after.value if (ba_before.value is not None and ba_after.value is not None) else None

    def log_loss(y, p):
        p = np.clip(p, 1e-15, 1 - 1e-15)
        return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
    ll_after = log_loss(donor_truth, prob_donor)

    cell_pred = (logits >= 0).astype(int)
    flip_rate = float(np.mean(cell_pred != baseline_cell_pred))

    return {
        "flip_rate": flip_rate,
        "ba_drop": ba_drop,
        "ll_after": ll_after,
        "donor_pred": donor_pred,
        "prob_donor": prob_donor
    }

def compute_bootstrap_ci(metric_fn, y, p_before, p_after, donors, n_bootstrap=1000, seed=22):
    rng = np.random.default_rng(seed)
    unique_donors = np.unique(donors)
    n_donors = len(unique_donors)
    deltas = []
    
    # We aggregate p_before and p_after per donor first to save time!
    import pandas as pd
    df = pd.DataFrame({"donor": donors, "y": y, "p_before": p_before, "p_after": p_after})
    # Since y is same for donor, p is same for donor in MIL (or cell level grouped)
    # The input here is already at DONOR level! Wait, if y, p_before, p_after are donor-level:
    if len(y) == n_donors:
        df_donor = df
    else:
        df_donor = df.groupby("donor").mean().reset_index()
        # For label, take mode or first
        df_donor["y"] = df.groupby("donor")["y"].first().values
        
    y_d = df_donor["y"].values
    pb_d = df_donor["p_before"].values
    pa_d = df_donor["p_after"].values
    
    for _ in range(n_bootstrap):
        idx = rng.choice(n_donors, size=n_donors, replace=True)
        val_b = metric_fn(y_d[idx], pb_d[idx])
        val_a = metric_fn(y_d[idx], pa_d[idx])
        if val_b is not None and val_a is not None:
            deltas.append(val_b - val_a)
            
    if not deltas:
        return None, None, None
    deltas = np.array(deltas)
    return np.mean(deltas), np.percentile(deltas, 2.5), np.percentile(deltas, 97.5)

def ba_metric(y, p):
    from p22.eval.metrics import balanced_accuracy
    pred = (p >= 0.5).astype(int)
    val = balanced_accuracy(y, pred).value
    return float(val) if val is not None else None

def ll_metric(y, p):
    p = np.clip(p, 1e-15, 1 - 1e-15)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))

def evaluate_fold(repeat, fold, arm, inputs, train_rows, holdout_rows, region_rows, cfg, state_dict_path):
    print(f"Evaluating {arm} repeat {repeat} fold {fold}")
    fold_arrays = prepare_nn_fold(inputs, train_rows, holdout_rows, region_rows, cfg)
    model, _, _ = build_arm(arm, fold_arrays.widths, cfg)
    if state_dict_path and os.path.exists(state_dict_path):
        model.load_state_dict(torch.load(state_dict_path, map_location="cpu"))
    else:
        # Refit for PC
        print(f"Refitting {arm} for PC")
        _, _, trainer = build_arm(arm, fold_arrays.widths, cfg)
        from p22.eval.nn_factory import ArmData
        train_data = ArmData(fold_arrays.train.views, fold_arrays.train.labels, fold_arrays.train.donors)
        val_data = ArmData(fold_arrays.val.views, fold_arrays.val.labels, fold_arrays.val.donors)
        trained = trainer(model, train_data, val_data)
        model = trained.model

    test_views = fold_arrays.test.views
    test_labels = fold_arrays.test.labels
    test_donors = fold_arrays.test.donors
    # get author_cell_type from inputs metadata
    test_cell_types = inputs.metadata["author_cell_type"].values[holdout_rows]
    train_views = fold_arrays.train.views

    # Baseline prediction
    is_mil = hasattr(model, "pool") or hasattr(model, "encoder")
    if is_mil:
        pred = predict_mil(model, test_views, test_donors)
        prob_donor = pred["donor_probabilities"]
        logits = pred["cell_logits"]
    else:
        pred = predict(model, test_views)
        logits = pred.logits
        import pandas as pd
        df = pd.DataFrame({"donor": test_donors, "p": pred.probabilities[:, 1]})
        prob_donor = df.groupby("donor", sort=True)["p"].mean().values

    baseline_donor_pred = (prob_donor >= 0.5).astype(int)
    baseline_cell_pred = (logits >= 0).astype(int)
    
    # get donor_truth
    df_truth = pd.DataFrame({"donor": test_donors, "y": test_labels}).groupby("donor").first()
    donor_truth = df_truth["y"].values
    unique_donors = df_truth.index.values

    results = []
    # Determine applicable interventions
    interventions = ["I1", "I2", "NC"]
    if "ca" in arm or "gated" in arm:
        interventions.append("I3")
    if "ca" in arm:
        interventions.append("I4")
    if is_mil:
        interventions.append("I5")
    if "gated" in arm:
        interventions.append("I6")
        
    for name in interventions:
        res = run_intervention(
            name, model, test_views, test_labels, test_donors, test_cell_types,
            train_views, cfg["seed"], baseline_donor_pred, baseline_cell_pred, donor_truth, is_mil
        )
        if res is not None:
            results.append({
                "intervention": name,
                "arm": arm,
                "repeat": repeat,
                "fold": fold,
                "donors": unique_donors,
                "y": donor_truth,
                "p_before": prob_donor,
                "p_after": res["prob_donor"],
                "flip_rate": res["flip_rate"]
            })
    return results

def main():
    with open("configs/nn_protocol_v2_2026-09-23.json") as f:
        cfg = json.load(f)
    with open("configs/nn_inputs_2026-09-23.json") as f:
        inputs_cfg = json.load(f)
    h5ad = inputs_cfg["inputs"]["h5ad"]["path"]
    atac = inputs_cfg["inputs"]["atac_tiebreak_counts"]["path"]
    union_bed = inputs_cfg["inputs"]["tracked_union_bed"]["path"]
    inputs = load_nn_inputs(h5ad, atac, 1000, 22, union_bed=union_bed)
    
    # We will test R3_ca, R3_tc, R3_gated, R4_ca
    test_arms = ["R3_ca", "R3_tc", "R3_gated", "R4_ca"]
    
    all_results = []
    
    # Ladder models
    for repeat, fold, train_rows, holdout_rows in iter_repeated_stratified_group_folds(
        inputs.metadata["donor_id"].values, inputs.metadata["disease"].values,
        cfg["n_repeats"], cfg["n_folds"], cfg["split_seed"]
    ):
        region_rows = inputs.region_indices(cfg["region_set_sha256"])
        for arm in test_arms:
            state_dict_path = f"reports/generated/nn_20260923/ladder/models/{arm}/r{repeat}_f{fold}_state.pt"
            res = evaluate_fold(repeat, fold, arm, inputs, train_rows, holdout_rows, region_rows, cfg, state_dict_path)
            all_results.extend(res)
            
        # For PC, plant signal S4 and S5 at delta 1.0, on R3_ca
        fold_arrays = prepare_nn_fold(inputs, train_rows, holdout_rows, region_rows, cfg)
        for s in ["S4", "S5"]:
            planted_arrays, fake_labels = plant(fold_arrays, s, 1.0, cfg["seed"])
            # refit R3_ca on planted
            model, _, trainer = build_arm("R3_ca", planted_arrays.widths, cfg)
            from p22.eval.nn_factory import ArmData
            train_data = ArmData(planted_arrays.train.views, planted_arrays.train.labels, planted_arrays.train.donors)
            val_data = ArmData(planted_arrays.val.views, planted_arrays.val.labels, planted_arrays.val.donors)
            trained = trainer(model, train_data, val_data)
            model = trained.model
            
            # Predict baseline
            pred = predict_mil(model, planted_arrays.test.views, planted_arrays.test.donors)
            prob_donor = pred["donor_probabilities"]
            logits = pred["cell_logits"]
            baseline_donor_pred = (prob_donor >= 0.5).astype(int)
            baseline_cell_pred = (logits >= 0).astype(int)
            df_truth = pd.DataFrame({"donor": planted_arrays.test.donors, "y": planted_arrays.test.labels}).groupby("donor").first()
            donor_truth = df_truth["y"].values
            test_cell_types = inputs.metadata["author_cell_type"].values[holdout_rows]
            
            res_pc = run_intervention(
                "I3", model, planted_arrays.test.views, planted_arrays.test.labels, planted_arrays.test.donors, test_cell_types,
                planted_arrays.train.views, cfg["seed"], baseline_donor_pred, baseline_cell_pred, donor_truth, True
            )
            if res_pc is not None:
                all_results.append({
                    "intervention": f"PC_{s}",
                    "arm": "R3_ca",
                    "repeat": repeat,
                    "fold": fold,
                    "donors": df_truth.index.values,
                    "y": donor_truth,
                    "p_before": prob_donor,
                    "p_after": res_pc["prob_donor"],
                    "flip_rate": res_pc["flip_rate"]
                })

    # Aggregate over folds/repeats
    # We pool the (donor, y, p_before, p_after) across all 25 runs (actually we can just average p for each donor)
    summary = []
    df_res = pd.DataFrame(all_results)
    
    for (intervention, arm), group in df_res.groupby(["intervention", "arm"]):
        donors = np.concatenate(group["donors"].values)
        y = np.concatenate(group["y"].values)
        p_before = np.concatenate(group["p_before"].values)
        p_after = np.concatenate(group["p_after"].values)
        flip_rate = group["flip_rate"].mean()
        
        ba_drop, ba_low, ba_high = compute_bootstrap_ci(ba_metric, y, p_before, p_after, donors)
        ll_drop, ll_low, ll_high = compute_bootstrap_ci(ll_metric, y, p_before, p_after, donors)
        
        summary.append({
            "intervention": intervention,
            "arm": arm,
            "flip_rate": flip_rate,
            "ba_drop": ba_drop,
            "ba_drop_ci": [ba_low, ba_high],
            "ll_drop": ll_drop,
            "ll_drop_ci": [ll_low, ll_high]
        })
        
    Path("docs/nn_v2").mkdir(parents=True, exist_ok=True)
    with open("docs/nn_v2/faithfulness.json", "w") as f:
        json.dump(summary, f, indent=2)
        
    # Write FAITHFULNESS.md
    with open("docs/nn_v2/FAITHFULNESS.md", "w") as f:
        f.write("# Faithfulness Interventions\n\n")
        f.write("| Intervention | Arm | Flip Rate | BA Drop (CI) | Log-Loss Drop (CI) | Used? |\n")
        f.write("|---|---|---|---|---|---|\n")
        for s in summary:
            ba_str = f"{s['ba_drop']:.4f} [{s['ba_drop_ci'][0]:.4f}, {s['ba_drop_ci'][1]:.4f}]" if s['ba_drop'] is not None else "N/A"
            ll_str = f"{s['ll_drop']:.4f} [{s['ll_drop_ci'][0]:.4f}, {s['ll_drop_ci'][1]:.4f}]" if s['ll_drop'] is not None else "N/A"
            used = "Yes" if s['ll_drop'] is not None and (s['ll_drop_ci'][0] > 0 or s['ll_drop_ci'][1] < 0) else "No"
            f.write(f"| {s['intervention']} | {s['arm']} | {s['flip_rate']:.4f} | {ba_str} | {ll_str} | {used} |\n")

if __name__ == "__main__":
    main()
