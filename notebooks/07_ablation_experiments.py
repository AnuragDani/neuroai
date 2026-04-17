#!/usr/bin/env python3
"""
07_ablation_experiments.py — Ablation study and error analysis for P22 revision.

Runs all experiments needed to fill [CONFIRM] placeholders in the paper:
  1. Ablation: fixed gate, temperature variants, PCA component sweep
  2. Error analysis: confused pairs, class-size correlation, error overlap
  3. McNemar's test: attention-gated vs. concatenation
  4. Mutual information: HVG features vs. PCA components
  5. Per-class test sample sizes for Table 4
  6. Training time and convergence epochs
  7. Cumulative variance at different PCA component counts

Reuses preprocessed data from run_finegrained_pipeline.py.
"""

import os
import sys
import json
import time
import warnings
import numpy as np
import pandas as pd
import scanpy as sc
from scipy import sparse
from scipy.stats import spearmanr
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score, confusion_matrix
)
from sklearn.preprocessing import label_binarize
from sklearn.feature_selection import mutual_info_classif
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import TensorDataset, DataLoader

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "artifacts")
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Device: {DEVICE}")

N_EPOCHS = 120
LR = 1e-3
PATIENCE = 15
BATCH_SIZE = 32
N_BOOTSTRAP = 1000
EMBED_DIM = 128


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL DEFINITIONS (from run_finegrained_pipeline.py)
# ═══════════════════════════════════════════════════════════════════════════════

class GenomicEncoder(nn.Module):
    def __init__(self, input_dim, embed_dim=EMBED_DIM):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, embed_dim),
        )

    def forward(self, x):
        return self.net(x)


class MorphEncoder(nn.Module):
    def __init__(self, input_dim, embed_dim=EMBED_DIM):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, embed_dim),
        )

    def forward(self, x):
        return self.net(x)


class CrossAttentionGate(nn.Module):
    def __init__(self, embed_dim=EMBED_DIM, temperature=1.0):
        super().__init__()
        self.attention_proj = nn.Sequential(
            nn.Linear(embed_dim, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
        )
        self.temperature = temperature
        self.last_attention_weights = None

    def forward(self, z_genomic, z_morph):
        stacked = torch.stack([z_genomic, z_morph], dim=1)
        attn_logits = self.attention_proj(stacked).squeeze(-1) / self.temperature
        attn_weights = F.softmax(attn_logits, dim=1)
        self.last_attention_weights = attn_weights.detach()
        fused = attn_weights[:, 0:1] * z_genomic + attn_weights[:, 1:2] * z_morph
        return fused


class FixedGate(nn.Module):
    """Fixed 50/50 gate — no learned parameters."""
    def __init__(self):
        super().__init__()
        self.last_attention_weights = None

    def forward(self, z_genomic, z_morph):
        batch_size = z_genomic.shape[0]
        self.last_attention_weights = torch.full(
            (batch_size, 2), 0.5, device=z_genomic.device
        )
        return 0.5 * z_genomic + 0.5 * z_morph


class CrossAttentionFusionModel(nn.Module):
    def __init__(self, gene_dim, morph_dim, n_classes, embed_dim=EMBED_DIM,
                 temperature=1.0, fixed_gate=False):
        super().__init__()
        self.genomic_encoder = GenomicEncoder(gene_dim, embed_dim)
        self.morph_encoder = MorphEncoder(morph_dim, embed_dim)
        if fixed_gate:
            self.attention_gate = FixedGate()
        else:
            self.attention_gate = CrossAttentionGate(embed_dim, temperature)
        self.classifier = nn.Linear(embed_dim, n_classes)

    def forward(self, x_gene, x_morph):
        z_g = self.genomic_encoder(x_gene)
        z_m = self.morph_encoder(x_morph)
        z_fused = self.attention_gate(z_g, z_m)
        return self.classifier(z_fused)

    def get_attention_weights(self):
        return self.attention_gate.last_attention_weights


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING / EVALUATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_ece(y_true, y_prob, n_bins=15):
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (y_prob >= bin_boundaries[i]) & (y_prob < bin_boundaries[i + 1])
        if mask.sum() == 0:
            continue
        ece += mask.sum() * np.abs(y_true[mask].mean() - y_prob[mask].mean())
    return ece / len(y_true)


def compute_multiclass_ece(y_true, y_prob, n_bins=15):
    n_cls = y_prob.shape[1]
    y_onehot = label_binarize(y_true, classes=list(range(n_cls)))
    if y_onehot.shape[1] == 1:
        y_onehot = np.hstack([1 - y_onehot, y_onehot])
    return float(np.mean([
        compute_ece(y_onehot[:, c], y_prob[:, c], n_bins) for c in range(n_cls)
    ]))


def evaluate_predictions(y_true, y_pred, y_prob):
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    try:
        auroc = roc_auc_score(y_true, y_prob, multi_class="ovr", average="macro")
    except ValueError:
        auroc = float("nan")
    ece = compute_multiclass_ece(y_true, y_prob)
    return {"accuracy": acc, "f1_weighted": f1, "auroc_macro": auroc, "ece": ece}


def make_bimodal_loaders(Xg_tr, Xm_tr, y_tr, Xg_vl, Xm_vl, y_vl,
                         Xg_te, Xm_te, y_te, batch_size=BATCH_SIZE):
    def _ds(xg, xm, y, shuffle):
        ds = TensorDataset(torch.tensor(xg, dtype=torch.float32),
                           torch.tensor(xm, dtype=torch.float32),
                           torch.tensor(y, dtype=torch.long))
        return DataLoader(ds, batch_size=batch_size, shuffle=shuffle)
    return (_ds(Xg_tr, Xm_tr, y_tr, True),
            _ds(Xg_vl, Xm_vl, y_vl, False),
            _ds(Xg_te, Xm_te, y_te, False))


def train_fusion(model, train_loader, val_loader, n_epochs=N_EPOCHS, lr=LR,
                 patience=PATIENCE, class_weights=None):
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5)
    criterion = nn.CrossEntropyLoss(
        weight=torch.tensor(class_weights, dtype=torch.float32).to(DEVICE)
    ) if class_weights is not None else nn.CrossEntropyLoss()

    best_val_loss = float("inf")
    best_state = None
    epochs_no_improve = 0
    final_epoch = 0

    t_start = time.time()
    for epoch in range(n_epochs):
        model.train()
        train_loss, n_batches = 0.0, 0
        for xg, xm, yb in train_loader:
            xg, xm, yb = xg.to(DEVICE), xm.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            loss = criterion(model(xg, xm), yb)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            n_batches += 1

        model.eval()
        val_loss, val_batches = 0.0, 0
        with torch.no_grad():
            for xg, xm, yb in val_loader:
                xg, xm, yb = xg.to(DEVICE), xm.to(DEVICE), yb.to(DEVICE)
                val_loss += criterion(model(xg, xm), yb).item()
                val_batches += 1

        avg_val = val_loss / max(val_batches, 1)
        scheduler.step(avg_val)

        if avg_val < best_val_loss:
            best_val_loss = avg_val
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1

        final_epoch = epoch + 1
        if epochs_no_improve >= patience:
            break

    wall_time = time.time() - t_start
    if best_state is not None:
        model.load_state_dict(best_state)
    return model, final_epoch, wall_time


def predict_fusion(model, data_loader):
    model.eval()
    all_preds, all_probs, all_attn = [], [], []
    with torch.no_grad():
        for xg, xm, _ in data_loader:
            xg, xm = xg.to(DEVICE), xm.to(DEVICE)
            logits = model(xg, xm)
            probs = torch.softmax(logits, dim=1)
            all_preds.extend(logits.argmax(1).cpu().numpy())
            all_probs.append(probs.cpu().numpy())
            if hasattr(model, "get_attention_weights"):
                attn = model.get_attention_weights()
                if attn is not None:
                    all_attn.append(attn.cpu().numpy())
    return (np.array(all_preds), np.vstack(all_probs),
            np.vstack(all_attn) if all_attn else None)


# ═══════════════════════════════════════════════════════════════════════════════
# LOAD PREPROCESSED DATA
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("LOADING PREPROCESSED DATA")
print("=" * 80)

X_expr = np.load(os.path.join(ARTIFACTS_DIR, "finegrained_modality1.npy"))
X_morph_60 = np.load(os.path.join(ARTIFACTS_DIR, "finegrained_modality2.npy"))
label_codes = np.load(os.path.join(ARTIFACTS_DIR, "finegrained_labels.npy"))

with open(os.path.join(ARTIFACTS_DIR, "finegrained_splits.json")) as f:
    splits = json.load(f)
train_idx = np.array(splits["train_idx"])
val_idx = np.array(splits["val_idx"])
test_idx = np.array(splits["test_idx"])
class_names = splits["class_names"]
n_classes = splits["n_classes"]

y_train = label_codes[train_idx]
y_val = label_codes[val_idx]
y_test = label_codes[test_idx]

# Class weights
train_class_counts = np.bincount(y_train, minlength=n_classes).astype(np.float32)
train_class_counts = np.maximum(train_class_counts, 1.0)
class_weights = len(y_train) / (n_classes * train_class_counts)
class_weights = class_weights / class_weights.sum() * n_classes

gene_dim = X_expr.shape[1]
print(f"  Gene dim: {gene_dim}, Classes: {n_classes}")
print(f"  Train: {len(train_idx)}, Val: {len(val_idx)}, Test: {len(test_idx)}")

# We also need the full expression matrix for PCA recomputation
raw_path = os.path.join(ARTIFACTS_DIR, "finegrained_preprocessed.h5ad")
adata = sc.read_h5ad(raw_path)
X_full = adata.X.toarray().astype(np.float32) if sparse.issparse(adata.X) else adata.X.astype(np.float32)
print(f"  Full expression matrix: {X_full.shape}")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT 1: PCA VARIANCE AT DIFFERENT COMPONENT COUNTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("EXPERIMENT 1: PCA VARIANCE CURVE")
print("=" * 80)

pca_full = PCA(n_components=150, random_state=SEED)
pca_full.fit(X_full)
cumvar = np.cumsum(pca_full.explained_variance_ratio_)
for nc in [30, 60, 90, 120, 150]:
    print(f"  PCA {nc} components: {cumvar[nc-1]*100:.1f}% variance explained")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT 2: MUTUAL INFORMATION BETWEEN HVG AND PCA
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("EXPERIMENT 2: MUTUAL INFORMATION (HVG vs PCA)")
print("=" * 80)

# Compute MI between each PCA component and a subset of HVG features
# using the label as target (estimate shared discriminative info)
# Method: compare MI(HVG, label) vs MI(PCA, label) and their overlap
mi_hvg = mutual_info_classif(X_expr[train_idx], y_train, random_state=SEED)
mi_pca = mutual_info_classif(X_morph_60[train_idx], y_train, random_state=SEED)

print(f"  MI(HVG features → label): mean={mi_hvg.mean():.4f}, "
      f"median={np.median(mi_hvg):.4f}, max={mi_hvg.max():.4f}")
print(f"  MI(PCA components → label): mean={mi_pca.mean():.4f}, "
      f"median={np.median(mi_pca):.4f}, max={mi_pca.max():.4f}")
print(f"  Total MI (sum) — HVG: {mi_hvg.sum():.2f}, PCA: {mi_pca.sum():.2f}")

# Direct MI between representations: subsample HVG to match PCA dimension
# and compute pairwise MI
from sklearn.metrics import mutual_info_score
# Discretize for MI estimation
n_bins_mi = 10
X_hvg_binned = np.digitize(X_expr[train_idx, :60],
                            bins=np.linspace(X_expr[train_idx, :60].min(),
                                             X_expr[train_idx, :60].max(), n_bins_mi))
X_pca_binned = np.digitize(X_morph_60[train_idx],
                            bins=np.linspace(X_morph_60[train_idx].min(),
                                             X_morph_60[train_idx].max(), n_bins_mi))
# Average pairwise MI between first 60 HVG features and 60 PCA components
pairwise_mi = []
for i in range(60):
    for j in range(60):
        pairwise_mi.append(mutual_info_score(X_hvg_binned[:, i], X_pca_binned[:, j]))
mean_pairwise_mi = np.mean(pairwise_mi)
max_pairwise_mi = np.max(pairwise_mi)
print(f"  Pairwise MI (HVG[0:60] vs PCA[0:60]): mean={mean_pairwise_mi:.4f}, max={max_pairwise_mi:.4f}")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT 3: ABLATION — GATE VARIANTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("EXPERIMENT 3: GATE ABLATION (fixed, sharp, soft)")
print("=" * 80)

ablation_results = []

for variant_name, temp, fixed in [
    ("Fixed gate (equal)", 1.0, True),
    ("Learned gate, sharp (τ=0.5)", 0.5, False),
    ("Learned gate, default (τ=1.0)", 1.0, False),
    ("Learned gate, soft (τ=2.0)", 2.0, False),
]:
    print(f"\n  Training: {variant_name}")
    torch.manual_seed(SEED)

    X_morph_tr = X_morph_60[train_idx]
    X_morph_vl = X_morph_60[val_idx]
    X_morph_te = X_morph_60[test_idx]

    train_loader, val_loader, test_loader = make_bimodal_loaders(
        X_expr[train_idx], X_morph_tr, y_train,
        X_expr[val_idx], X_morph_vl, y_val,
        X_expr[test_idx], X_morph_te, y_test,
    )

    model = CrossAttentionFusionModel(
        gene_dim, 60, n_classes, EMBED_DIM,
        temperature=temp, fixed_gate=fixed
    ).to(DEVICE)

    model, epochs, wall_time = train_fusion(
        model, train_loader, val_loader, class_weights=class_weights
    )
    preds, probs, attn = predict_fusion(model, test_loader)
    metrics = evaluate_predictions(y_test, preds, probs)

    print(f"    Acc={metrics['accuracy']:.4f}, F1={metrics['f1_weighted']:.4f}, "
          f"Epochs={epochs}, Time={wall_time:.1f}s")

    ablation_results.append({
        "variant": variant_name,
        "accuracy": metrics["accuracy"],
        "f1_weighted": metrics["f1_weighted"],
        "epochs": epochs,
        "wall_time_s": wall_time,
        "predictions": preds.copy(),
    })


# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT 4: PCA COMPONENT SWEEP
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("EXPERIMENT 4: PCA COMPONENT SWEEP")
print("=" * 80)

for n_pca in [30, 90, 120]:
    print(f"\n  PCA components: {n_pca}")
    torch.manual_seed(SEED)

    pca_variant = PCA(n_components=n_pca, random_state=SEED)
    X_morph_var = pca_variant.fit_transform(X_full).astype(np.float32)

    train_loader, val_loader, test_loader = make_bimodal_loaders(
        X_expr[train_idx], X_morph_var[train_idx], y_train,
        X_expr[val_idx], X_morph_var[val_idx], y_val,
        X_expr[test_idx], X_morph_var[test_idx], y_test,
    )

    model = CrossAttentionFusionModel(
        gene_dim, n_pca, n_classes, EMBED_DIM
    ).to(DEVICE)

    model, epochs, wall_time = train_fusion(
        model, train_loader, val_loader, class_weights=class_weights
    )
    preds, probs, attn = predict_fusion(model, test_loader)
    metrics = evaluate_predictions(y_test, preds, probs)

    print(f"    Acc={metrics['accuracy']:.4f}, F1={metrics['f1_weighted']:.4f}, "
          f"Epochs={epochs}, Time={wall_time:.1f}s")

    ablation_results.append({
        "variant": f"{n_pca} PCA components",
        "accuracy": metrics["accuracy"],
        "f1_weighted": metrics["f1_weighted"],
        "epochs": epochs,
        "wall_time_s": wall_time,
    })

# Save ablation results
print("\n  === ABLATION SUMMARY ===")
for r in ablation_results:
    print(f"  {r['variant']:40s}  Acc={r['accuracy']:.4f}  F1={r['f1_weighted']:.4f}")

ablation_df = pd.DataFrame(ablation_results)
ablation_df.to_csv(os.path.join(ARTIFACTS_DIR, "ablation_results.csv"), index=False)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT 5: McNEMAR'S TEST
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("EXPERIMENT 5: McNEMAR'S TEST")
print("=" * 80)

# Load existing predictions from the attention-gated and concat models
# Re-run the default attention-gated model to get per-sample predictions
torch.manual_seed(SEED)
train_loader, val_loader, test_loader = make_bimodal_loaders(
    X_expr[train_idx], X_morph_60[train_idx], y_train,
    X_expr[val_idx], X_morph_60[val_idx], y_val,
    X_expr[test_idx], X_morph_60[test_idx], y_test,
)

# Load saved model
from run_finegrained_pipeline import NaiveConcatFusionModel
# Actually, just redefine it here
class NaiveConcatFusionModel(nn.Module):
    def __init__(self, gene_dim, morph_dim, n_classes, embed_dim=EMBED_DIM):
        super().__init__()
        self.genomic_encoder = GenomicEncoder(gene_dim, embed_dim)
        self.morph_encoder = MorphEncoder(morph_dim, embed_dim)
        self.classifier = nn.Sequential(
            nn.Linear(embed_dim * 2, embed_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(embed_dim, n_classes),
        )

    def forward(self, x_gene, x_morph):
        z_g = self.genomic_encoder(x_gene)
        z_m = self.morph_encoder(x_morph)
        return self.classifier(torch.cat([z_g, z_m], dim=1))

# Train both from scratch with same seed for fair comparison
print("  Training attention-gated model...")
torch.manual_seed(SEED)
attn_model = CrossAttentionFusionModel(gene_dim, 60, n_classes, EMBED_DIM).to(DEVICE)
attn_model, attn_epochs, attn_time = train_fusion(
    attn_model, train_loader, val_loader, class_weights=class_weights
)
attn_preds, attn_probs, _ = predict_fusion(attn_model, test_loader)
attn_correct = (attn_preds == y_test)
print(f"    Acc={accuracy_score(y_test, attn_preds):.4f}, Epochs={attn_epochs}, Time={attn_time:.1f}s")

print("  Training concat fusion model...")
torch.manual_seed(SEED)
concat_model = NaiveConcatFusionModel(gene_dim, 60, n_classes, EMBED_DIM).to(DEVICE)
concat_model, concat_epochs, concat_time = train_fusion(
    concat_model, train_loader, val_loader, class_weights=class_weights
)
concat_preds, concat_probs, _ = predict_fusion(concat_model, test_loader)
concat_correct = (concat_preds == y_test)
print(f"    Acc={accuracy_score(y_test, concat_preds):.4f}, Epochs={concat_epochs}, Time={concat_time:.1f}s")

# McNemar's test
# b = attn correct, concat wrong; c = attn wrong, concat correct
b = np.sum(attn_correct & ~concat_correct)
c = np.sum(~attn_correct & concat_correct)
n_disagree = b + c
if n_disagree > 0:
    chi2 = (abs(b - c) - 1) ** 2 / (b + c)  # with continuity correction
    from scipy.stats import chi2 as chi2_dist
    p_value = 1 - chi2_dist.cdf(chi2, df=1)
else:
    chi2 = 0.0
    p_value = 1.0

print(f"\n  McNemar's test:")
print(f"    Attn correct & Concat wrong (b): {b}")
print(f"    Attn wrong & Concat correct (c): {c}")
print(f"    Chi-squared (continuity corrected): {chi2:.4f}")
print(f"    p-value: {p_value:.4f}")
print(f"    Significant at α=0.05: {p_value < 0.05}")

# Also run logistic regression for error overlap analysis
print("\n  Training logistic regression...")
lr_model = LogisticRegression(
    max_iter=2000, C=1.0, solver="lbfgs", multi_class="multinomial",
    random_state=SEED, n_jobs=-1
)
lr_model.fit(X_expr[train_idx], y_train)
lr_preds = lr_model.predict(X_expr[test_idx])
lr_correct = (lr_preds == y_test)
print(f"    LR Acc={accuracy_score(y_test, lr_preds):.4f}")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT 6: ERROR ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("EXPERIMENT 6: ERROR ANALYSIS")
print("=" * 80)

# Confusion matrix for attention-gated model
cm = confusion_matrix(y_test, attn_preds)
n_errors = (y_test != attn_preds).sum()
print(f"  Total errors: {n_errors} / {len(y_test)} ({n_errors/len(y_test)*100:.1f}%)")

# Top confused pairs
confused_pairs = []
for i in range(n_classes):
    for j in range(n_classes):
        if i != j and cm[i, j] > 0:
            confused_pairs.append({
                "true_class": class_names[i],
                "pred_class": class_names[j],
                "count": int(cm[i, j]),
                "true_idx": i,
                "pred_idx": j,
            })
confused_pairs.sort(key=lambda x: x["count"], reverse=True)

print(f"\n  Top 10 confused pairs:")
for cp in confused_pairs[:10]:
    # Check if both are excitatory (start with L)
    both_exc = cp["true_class"].startswith("L") and cp["pred_class"].startswith("L")
    print(f"    {cp['true_class']:20s} → {cp['pred_class']:20s}  "
          f"count={cp['count']}  {'(both excitatory)' if both_exc else ''}")

# Per-class accuracy vs. class size
per_class_acc = []
per_class_size_train = []
per_class_size_test = []
for ci in range(n_classes):
    test_mask = (y_test == ci)
    train_count = (y_train == ci).sum()
    test_count = test_mask.sum()
    if test_count > 0:
        class_acc = (attn_preds[test_mask] == y_test[test_mask]).mean()
    else:
        class_acc = np.nan
    per_class_acc.append(class_acc)
    per_class_size_train.append(int(train_count))
    per_class_size_test.append(int(test_count))

per_class_acc = np.array(per_class_acc)
per_class_size_train = np.array(per_class_size_train)
per_class_size_test = np.array(per_class_size_test)

# Filter out classes with no test samples
valid_mask = ~np.isnan(per_class_acc)
rho, rho_p = spearmanr(per_class_size_train[valid_mask], per_class_acc[valid_mask])
print(f"\n  Per-class accuracy vs. training class size:")
print(f"    Spearman rho={rho:.3f}, p={rho_p:.4f}")

# Accuracy by size bucket
large_mask = per_class_size_train >= 30
small_mask = (per_class_size_train < 15) & valid_mask
large_acc = per_class_acc[large_mask & valid_mask].mean() if (large_mask & valid_mask).sum() > 0 else np.nan
small_acc = per_class_acc[small_mask].mean() if small_mask.sum() > 0 else np.nan
print(f"    Classes with ≥30 train cells ({(large_mask & valid_mask).sum()} types): "
      f"mean acc={large_acc:.3f}")
print(f"    Classes with <15 train cells ({small_mask.sum()} types): "
      f"mean acc={small_acc:.3f}")

# Error overlap: attention-gated vs. logistic regression
attn_errors = set(np.where(~attn_correct)[0])
lr_errors = set(np.where(~lr_correct)[0])
shared_errors = attn_errors & lr_errors
attn_only = attn_errors - lr_errors
lr_only = lr_errors - attn_errors

print(f"\n  Error overlap (attention-gated vs. logistic regression):")
print(f"    Attn errors: {len(attn_errors)}")
print(f"    LR errors: {len(lr_errors)}")
print(f"    Shared errors: {len(shared_errors)} "
      f"({len(shared_errors)/max(len(attn_errors),1)*100:.1f}% of attn errors)")
print(f"    Attn-only errors: {len(attn_only)}")
print(f"    LR-only errors: {len(lr_only)}")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPERIMENT 7: PER-CLASS TEST SAMPLE SIZES (for Table 4)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("EXPERIMENT 7: PER-CLASS TEST SIZES (Table 4 types)")
print("=" * 80)

table4_types = [
    "L4 Scnn1a", "L2 Ngb",  # L2/3 variant
    "L6a Sla", "L5a Batf3",
    "Pvalb Gpx3", "Pvalb Wt1", "Sst Cbln4"
]
# Also check all L2/3 types
l23_types = [cn for cn in class_names if cn.startswith("L2") or cn.startswith("L2/3")]
pvalb_types = [cn for cn in class_names if cn.startswith("Pvalb")]

print(f"  L2/3-related types in dataset: {l23_types}")
print(f"  Pvalb types in dataset: {pvalb_types}")

for cname in class_names:
    ci = class_names.index(cname)
    test_n = (y_test == ci).sum()
    train_n = (y_train == ci).sum()
    if cname in table4_types or cname.startswith(("L4", "L5a", "L6a", "Pvalb", "Sst", "L2")):
        acc = per_class_acc[ci] if not np.isnan(per_class_acc[ci]) else 0.0
        print(f"    {cname:25s}  train={train_n:3d}  test={test_n:2d}  acc={acc:.3f}")


# ═══════════════════════════════════════════════════════════════════════════════
# SAVE ALL RESULTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("SAVING RESULTS")
print("=" * 80)

results = {
    "pca_variance": {str(nc): float(cumvar[nc-1]) for nc in [30, 60, 90, 120]},
    "mutual_information": {
        "hvg_to_label_mean": float(mi_hvg.mean()),
        "pca_to_label_mean": float(mi_pca.mean()),
        "pairwise_hvg_pca_mean": float(mean_pairwise_mi),
        "pairwise_hvg_pca_max": float(max_pairwise_mi),
    },
    "mcnemar": {
        "b_attn_correct_concat_wrong": int(b),
        "c_attn_wrong_concat_correct": int(c),
        "chi2": float(chi2),
        "p_value": float(p_value),
        "significant_005": bool(p_value < 0.05),
    },
    "training": {
        "attn_epochs": attn_epochs,
        "attn_wall_time_s": round(attn_time, 1),
        "concat_epochs": concat_epochs,
        "concat_wall_time_s": round(concat_time, 1),
    },
    "error_analysis": {
        "total_errors": int(n_errors),
        "total_test": int(len(y_test)),
        "spearman_rho": float(rho),
        "spearman_p": float(rho_p),
        "large_class_mean_acc": float(large_acc) if not np.isnan(large_acc) else None,
        "small_class_mean_acc": float(small_acc) if not np.isnan(small_acc) else None,
        "shared_errors_pct": float(len(shared_errors) / max(len(attn_errors), 1) * 100),
        "attn_only_errors": int(len(attn_only)),
        "lr_only_errors": int(len(lr_only)),
        "top_confused_pairs": confused_pairs[:10],
    },
    "per_class_test_sizes": {
        class_names[ci]: int((y_test == ci).sum()) for ci in range(n_classes)
    },
}

with open(os.path.join(ARTIFACTS_DIR, "ablation_analysis.json"), "w") as f:
    json.dump(results, f, indent=2)

print(f"\n  Results saved to {ARTIFACTS_DIR}/ablation_analysis.json")
print(f"  Ablation CSV saved to {ARTIFACTS_DIR}/ablation_results.csv")
print("\nDONE.")
