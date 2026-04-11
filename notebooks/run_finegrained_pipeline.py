#!/usr/bin/env python3
"""
run_finegrained_pipeline.py — Fine-grained cell-type classification pipeline.

Uses `primary_type` labels (~50 subtypes) instead of `broad_type` (7 classes).
This breaks the near-perfect accuracy ceiling from the broad-type experiment.

Data: Tasic et al. 2016, Allen Institute, mouse visual cortex
      1,809 cells x 24,057 genes, SMART-seq single-cell RNA-seq

Key differences from broad-type pipeline:
  - Labels: primary_type (~50 fine-grained subtypes)
  - Drop types with <10 total cells (can't split meaningfully)
  - Drop "Unclassified" broad_type cells as before
  - Batch size 32 (smaller dataset per class)
  - Skip marker gene list comparison (no canonical markers for all subtypes)
  - Report top-5 genes per class for the 10 most common types
  - Skip SHAP (too slow on 50 types); IG + attention weights are sufficient

All artifacts saved with "finegrained_" prefix to /artifacts/.
"""

import os
import sys
import json
import warnings
import time
import numpy as np
import pandas as pd
import scanpy as sc
import anndata as ad
from scipy import sparse
from sklearn.model_selection import train_test_split
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.preprocessing import label_binarize
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
FIGURES_DIR = os.path.join(ARTIFACTS_DIR, "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
EXPLAIN_DEVICE = "cpu"  # Captum more stable on CPU
print(f"Compute device: {DEVICE}, Explainability device: {EXPLAIN_DEVICE}")

# Hyperparameters — tuned for fine-grained (many small classes)
BATCH_SIZE = 32
N_EPOCHS = 120
LR = 1e-3
PATIENCE = 15
N_BOOTSTRAP = 1000
EMBED_DIM = 128
N_TOP_GENES = 2000
N_PCA_COMPONENTS = 60
TOP_K_FEATURES = 20
MIN_CELLS_PER_TYPE = 10  # drop types with fewer cells


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_ece(y_true, y_prob, n_bins=15):
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (y_prob >= bin_boundaries[i]) & (y_prob < bin_boundaries[i + 1])
        if mask.sum() == 0:
            continue
        bin_conf = y_prob[mask].mean()
        bin_acc = y_true[mask].mean()
        ece += mask.sum() * np.abs(bin_acc - bin_conf)
    return ece / len(y_true)


def compute_multiclass_ece(y_true, y_prob, n_bins=15):
    n_cls = y_prob.shape[1]
    y_onehot = label_binarize(y_true, classes=list(range(n_cls)))
    if y_onehot.shape[1] == 1:
        y_onehot = np.hstack([1 - y_onehot, y_onehot])
    ece_per_class = []
    for c in range(n_cls):
        ece_per_class.append(compute_ece(y_onehot[:, c], y_prob[:, c], n_bins))
    return float(np.mean(ece_per_class))


def evaluate_predictions(y_true, y_pred, y_prob):
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    try:
        auroc = roc_auc_score(y_true, y_prob, multi_class="ovr", average="macro")
    except ValueError:
        auroc = float("nan")
    ece = compute_multiclass_ece(y_true, y_prob)
    return {"accuracy": acc, "f1_weighted": f1, "auroc_macro": auroc, "ece": ece}


def bootstrap_metrics(y_true, y_pred, y_prob, n_bootstrap=N_BOOTSTRAP, seed=SEED):
    rng = np.random.default_rng(seed)
    n = len(y_true)
    results = {"accuracy": [], "f1_weighted": [], "auroc_macro": [], "ece": []}
    for _ in range(n_bootstrap):
        idx = rng.choice(n, size=n, replace=True)
        if len(np.unique(y_true[idx])) < 2:
            continue
        m = evaluate_predictions(y_true[idx], y_pred[idx], y_prob[idx])
        for k, v in m.items():
            if not np.isnan(v):
                results[k].append(v)
    ci = {}
    for k, vals in results.items():
        if len(vals) > 0:
            ci[f"{k}_ci_lo"] = float(np.percentile(vals, 2.5))
            ci[f"{k}_ci_hi"] = float(np.percentile(vals, 97.5))
        else:
            ci[f"{k}_ci_lo"] = float("nan")
            ci[f"{k}_ci_hi"] = float("nan")
    return ci


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL DEFINITIONS (identical architecture to broad-type pipeline)
# ═══════════════════════════════════════════════════════════════════════════════

class BaselineMLP(nn.Module):
    def __init__(self, in_dim, n_classes, hidden_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, n_classes),
        )

    def forward(self, x):
        return self.net(x)


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
    def __init__(self, embed_dim=EMBED_DIM):
        super().__init__()
        self.attention_proj = nn.Sequential(
            nn.Linear(embed_dim, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
        )
        self.last_attention_weights = None

    def forward(self, z_genomic, z_morph):
        stacked = torch.stack([z_genomic, z_morph], dim=1)  # (B, 2, D)
        attn_logits = self.attention_proj(stacked).squeeze(-1)  # (B, 2)
        attn_weights = F.softmax(attn_logits, dim=1)  # (B, 2)
        self.last_attention_weights = attn_weights.detach()
        fused = attn_weights[:, 0:1] * z_genomic + attn_weights[:, 1:2] * z_morph
        return fused


class CrossAttentionFusionModel(nn.Module):
    def __init__(self, gene_dim, morph_dim, n_classes, embed_dim=EMBED_DIM):
        super().__init__()
        self.genomic_encoder = GenomicEncoder(gene_dim, embed_dim)
        self.morph_encoder = MorphEncoder(morph_dim, embed_dim)
        self.attention_gate = CrossAttentionGate(embed_dim)
        self.classifier = nn.Linear(embed_dim, n_classes)

    def forward(self, x_gene, x_morph):
        z_g = self.genomic_encoder(x_gene)
        z_m = self.morph_encoder(x_morph)
        z_fused = self.attention_gate(z_g, z_m)
        logits = self.classifier(z_fused)
        return logits

    def get_attention_weights(self):
        return self.attention_gate.last_attention_weights


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
        z_cat = torch.cat([z_g, z_m], dim=1)
        logits = self.classifier(z_cat)
        return logits


class FusionWrapper(nn.Module):
    """Wraps fusion model for Captum (single concatenated input)."""
    def __init__(self, model, gene_dim, morph_dim):
        super().__init__()
        self.model = model
        self.gene_dim = gene_dim
        self.morph_dim = morph_dim

    def forward(self, x_combined):
        x_gene = x_combined[:, :self.gene_dim]
        x_morph = x_combined[:, self.gene_dim:]
        return self.model(x_gene, x_morph)


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def make_loaders(X_train, X_val, X_test, y_train, y_val, y_test, batch_size=BATCH_SIZE):
    def _ds(X, y, shuffle):
        ds = TensorDataset(torch.tensor(X, dtype=torch.float32),
                           torch.tensor(y, dtype=torch.long))
        return DataLoader(ds, batch_size=batch_size, shuffle=shuffle)
    return _ds(X_train, y_train, True), _ds(X_val, y_val, False), _ds(X_test, y_test, False)


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


def train_mlp(model, train_loader, val_loader, n_epochs=N_EPOCHS, lr=LR,
              patience=PATIENCE, class_weights=None):
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5)
    if class_weights is not None:
        criterion = nn.CrossEntropyLoss(
            weight=torch.tensor(class_weights, dtype=torch.float32).to(DEVICE))
    else:
        criterion = nn.CrossEntropyLoss()

    best_val_loss = float("inf")
    best_state = None
    epochs_no_improve = 0

    for epoch in range(n_epochs):
        model.train()
        train_loss, n_batches = 0.0, 0
        for xb, yb in train_loader:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            n_batches += 1

        model.eval()
        val_loss, val_batches = 0.0, 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(DEVICE), yb.to(DEVICE)
                val_loss += criterion(model(xb), yb).item()
                val_batches += 1

        avg_train = train_loss / max(n_batches, 1)
        avg_val = val_loss / max(val_batches, 1)
        scheduler.step(avg_val)

        if avg_val < best_val_loss:
            best_val_loss = avg_val
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1

        if (epoch + 1) % 20 == 0 or epoch == 0:
            print(f"    Epoch {epoch+1:3d}/{n_epochs} — "
                  f"train_loss={avg_train:.4f}, val_loss={avg_val:.4f}")

        if epochs_no_improve >= patience:
            print(f"    Early stopping at epoch {epoch+1}")
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model


def predict_mlp(model, data_loader):
    model.eval()
    all_preds, all_probs = [], []
    with torch.no_grad():
        for xb, _ in data_loader:
            xb = xb.to(DEVICE)
            logits = model(xb)
            probs = torch.softmax(logits, dim=1)
            all_preds.extend(logits.argmax(1).cpu().numpy())
            all_probs.append(probs.cpu().numpy())
    return np.array(all_preds), np.vstack(all_probs)


def train_fusion(model, train_loader, val_loader, n_epochs=N_EPOCHS, lr=LR,
                 patience=PATIENCE, class_weights=None):
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5)
    if class_weights is not None:
        criterion = nn.CrossEntropyLoss(
            weight=torch.tensor(class_weights, dtype=torch.float32).to(DEVICE))
    else:
        criterion = nn.CrossEntropyLoss()

    best_val_loss = float("inf")
    best_state = None
    epochs_no_improve = 0

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

        avg_train = train_loss / max(n_batches, 1)
        avg_val = val_loss / max(val_batches, 1)
        scheduler.step(avg_val)

        if avg_val < best_val_loss:
            best_val_loss = avg_val
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1

        if (epoch + 1) % 20 == 0 or epoch == 0:
            print(f"    Epoch {epoch+1:3d}/{n_epochs} — "
                  f"train_loss={avg_train:.4f}, val_loss={avg_val:.4f}")

        if epochs_no_improve >= patience:
            print(f"    Early stopping at epoch {epoch+1}")
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model


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
    preds = np.array(all_preds)
    probs = np.vstack(all_probs)
    attn = np.vstack(all_attn) if all_attn else None
    return preds, probs, attn


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: DATA PREPROCESSING (Fine-Grained)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 1: DATA PREPROCESSING — Fine-Grained (primary_type labels)")
print("=" * 80)

t0 = time.time()

# Load
raw_path = os.path.join(ARTIFACTS_DIR, "real_brain_data.h5ad")
adata = sc.read_h5ad(raw_path)
print(f"  Loaded: {adata.n_obs} cells x {adata.n_vars} genes")

# Drop Unclassified (by broad_type, same as before)
n_before = adata.n_obs
adata = adata[adata.obs["broad_type"] != "Unclassified"].copy()
print(f"  Dropped 'Unclassified' broad_type: {n_before} -> {adata.n_obs} cells")

# Show primary_type distribution BEFORE filtering
print(f"\n  primary_type distribution BEFORE min-cell filter:")
pt_counts = adata.obs["primary_type"].value_counts()
print(f"    Total unique types: {len(pt_counts)}")
for ct, cnt in pt_counts.items():
    print(f"    {ct}: {cnt} cells")

# Drop primary_types with fewer than MIN_CELLS_PER_TYPE cells
types_to_keep = pt_counts[pt_counts >= MIN_CELLS_PER_TYPE].index.tolist()
types_dropped = pt_counts[pt_counts < MIN_CELLS_PER_TYPE].index.tolist()

print(f"\n  Dropping types with < {MIN_CELLS_PER_TYPE} cells:")
for ct in types_dropped:
    print(f"    DROPPED: {ct} ({pt_counts[ct]} cells)")
print(f"  Types dropped: {len(types_dropped)}, Types kept: {len(types_to_keep)}")

n_before = adata.n_obs
adata = adata[adata.obs["primary_type"].isin(types_to_keep)].copy()
print(f"  Cells after type filter: {n_before} -> {adata.n_obs}")

# Show final class distribution
print(f"\n  Final class distribution ({len(types_to_keep)} types):")
pt_final = adata.obs["primary_type"].value_counts()
for ct, cnt in pt_final.items():
    print(f"    {ct}: {cnt} cells ({cnt/adata.n_obs*100:.1f}%)")

# QC: filter cells and genes
print(f"\n  Running QC filters...")
if sparse.issparse(adata.X):
    X_dense_check = adata.X.toarray()
else:
    X_dense_check = adata.X.copy()

genes_per_cell = (X_dense_check > 0).sum(axis=1)
print(f"    Genes per cell: median={np.median(genes_per_cell):.0f}, "
      f"min={genes_per_cell.min()}, max={genes_per_cell.max()}")

# Filter cells with <200 genes detected
cell_mask = np.array(genes_per_cell >= 200).flatten()
n_before = adata.n_obs
adata = adata[cell_mask].copy()
print(f"    Cells after filtering (<200 genes): {n_before} -> {adata.n_obs}")

# Filter genes in <3 cells
sc.pp.filter_genes(adata, min_cells=3)
print(f"    Genes after filtering (<3 cells): {adata.n_vars}")

# Normalize
print(f"  Normalizing (target_sum=10000, log1p)...")
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)

# HVG selection
print(f"  Selecting top {N_TOP_GENES} HVGs...")
sc.pp.highly_variable_genes(adata, n_top_genes=N_TOP_GENES, subset=False, flavor="seurat")
adata_hvg = adata[:, adata.var["highly_variable"]].copy()
print(f"    HVG matrix: {adata_hvg.n_obs} cells x {adata_hvg.n_vars} genes")

# Modality 1: gene expression (HVGs)
X_expr = adata_hvg.X.toarray().astype(np.float32) if sparse.issparse(adata_hvg.X) else adata_hvg.X.astype(np.float32)
gene_names = list(adata_hvg.var_names.astype(str))
print(f"  Modality 1 (gene expression): {X_expr.shape}")

# Modality 2: PCA of full expression (proxy for morphological features)
print(f"  Computing Modality 2: {N_PCA_COMPONENTS} PCA components from full expression...")
X_full = adata.X.toarray().astype(np.float32) if sparse.issparse(adata.X) else adata.X.astype(np.float32)
pca = PCA(n_components=N_PCA_COMPONENTS, random_state=SEED)
X_morph = pca.fit_transform(X_full).astype(np.float32)
print(f"    PCA explained variance (top 10): {pca.explained_variance_ratio_[:10].round(4)}")
print(f"    Total explained variance ({N_PCA_COMPONENTS} PCs): {pca.explained_variance_ratio_.sum():.4f}")
print(f"  Modality 2 (PCA features): {X_morph.shape}")

# Labels — use primary_type
label_col = adata_hvg.obs["primary_type"].astype("category")
# Remove unused categories after filtering
label_col = label_col.cat.remove_unused_categories()
label_codes = label_col.cat.codes.values.astype(np.int64)
class_names = list(label_col.cat.categories.astype(str))
n_classes = len(class_names)
print(f"  Classes: {n_classes} fine-grained types")

# Determine the top 10 most common types (for reporting)
class_counts = pd.Series(label_codes).value_counts().sort_values(ascending=False)
top10_class_indices = class_counts.head(10).index.tolist()
top10_class_names = [class_names[i] for i in top10_class_indices]
print(f"\n  Top 10 most common types:")
for ci in top10_class_indices:
    print(f"    {class_names[ci]}: {class_counts[ci]} cells")

# Stratified 64/16/20 split — handle small classes
print(f"\n  Creating stratified 64/16/20 splits...")
idx = np.arange(adata_hvg.n_obs)

unique_labels, label_count_arr = np.unique(label_codes, return_counts=True)
min_class_size = label_count_arr.min()
print(f"    Minimum class size: {min_class_size} ({class_names[unique_labels[label_count_arr.argmin()]]})")

# For very small classes, stratified split needs at least 2 per split
# train_test_split requires at least 2 members per class in test
# We use stratify but with a safe fallback
try:
    train_idx, test_idx = train_test_split(
        idx, test_size=0.20, random_state=SEED, stratify=label_codes)
    train_idx, val_idx = train_test_split(
        train_idx, test_size=0.20, random_state=SEED, stratify=label_codes[train_idx])
except ValueError as e:
    print(f"    Stratified split failed ({e}), using stratified with adjusted ratios...")
    # Fall back: ensure each class has at least 1 in each split
    train_idx, test_idx = train_test_split(
        idx, test_size=0.20, random_state=SEED, stratify=label_codes)
    # For the second split, try a smaller val fraction if needed
    try:
        train_idx, val_idx = train_test_split(
            train_idx, test_size=0.20, random_state=SEED, stratify=label_codes[train_idx])
    except ValueError:
        train_idx, val_idx = train_test_split(
            train_idx, test_size=0.20, random_state=SEED)
        print(f"    WARNING: Val split not stratified due to small class sizes")

print(f"    Train: {len(train_idx)}, Val: {len(val_idx)}, Test: {len(test_idx)}")

# Show per-class distribution in each split (summary for top 10)
for split_name, split_idx in [("train", train_idx), ("val", val_idx), ("test", test_idx)]:
    split_labels = label_codes[split_idx]
    unique, counts = np.unique(split_labels, return_counts=True)
    n_empty = n_classes - len(unique)
    min_count = counts.min() if len(counts) > 0 else 0
    max_count = counts.max() if len(counts) > 0 else 0
    print(f"    {split_name}: {len(split_idx)} samples, "
          f"classes present={len(unique)}/{n_classes}, "
          f"min_per_class={min_count}, max_per_class={max_count}")

# Warn about small test classes
test_labels = label_codes[test_idx]
n_small_test = 0
for ci, cname in enumerate(class_names):
    test_count = (test_labels == ci).sum()
    if test_count < 3:
        n_small_test += 1
if n_small_test > 0:
    print(f"    WARNING: {n_small_test} classes have <3 samples in test set")

# Compute class weights for training (handle imbalance)
train_labels = label_codes[train_idx]
train_class_counts = np.bincount(train_labels, minlength=n_classes).astype(np.float32)
# Avoid division by zero for classes not in training set
train_class_counts = np.maximum(train_class_counts, 1.0)
class_weights = len(train_labels) / (n_classes * train_class_counts)
class_weights = class_weights / class_weights.sum() * n_classes  # normalize
print(f"    Class weight range: [{class_weights.min():.3f}, {class_weights.max():.3f}]")

# Save preprocessing artifacts
print(f"\n  Saving preprocessing artifacts...")
adata_hvg.write_h5ad(os.path.join(ARTIFACTS_DIR, "finegrained_preprocessed.h5ad"))
np.save(os.path.join(ARTIFACTS_DIR, "finegrained_modality1.npy"), X_expr)
np.save(os.path.join(ARTIFACTS_DIR, "finegrained_modality2.npy"), X_morph)
np.save(os.path.join(ARTIFACTS_DIR, "finegrained_labels.npy"), label_codes)

splits_data = {
    "train_idx": train_idx.tolist(),
    "val_idx": val_idx.tolist(),
    "test_idx": test_idx.tolist(),
    "seed": SEED,
    "n_classes": n_classes,
    "class_names": class_names,
    "top10_class_names": top10_class_names,
    "top10_class_indices": top10_class_indices,
}
with open(os.path.join(ARTIFACTS_DIR, "finegrained_splits.json"), "w") as f:
    json.dump(splits_data, f, indent=2)

with open(os.path.join(ARTIFACTS_DIR, "finegrained_gene_names.json"), "w") as f:
    json.dump(gene_names, f)

print(f"  STEP 1 complete in {time.time()-t0:.1f}s")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: BASELINES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 2: BASELINE MODELS (Fine-Grained)")
print("=" * 80)

t1 = time.time()

# Split data
X_expr_train, X_expr_val, X_expr_test = X_expr[train_idx], X_expr[val_idx], X_expr[test_idx]
X_morph_train, X_morph_val, X_morph_test = X_morph[train_idx], X_morph[val_idx], X_morph[test_idx]
y_train, y_val, y_test = label_codes[train_idx], label_codes[val_idx], label_codes[test_idx]

gene_dim = X_expr.shape[1]
morph_dim = X_morph.shape[1]

all_baseline_results = []

# --- Baseline (a): Logistic Regression ---
print("\n  BASELINE (a): Logistic Regression on gene expression")
lr_model = LogisticRegression(
    max_iter=3000, multi_class="multinomial", solver="lbfgs",
    random_state=SEED, C=1.0, class_weight="balanced")
lr_model.fit(X_expr_train, y_train)
lr_pred = lr_model.predict(X_expr_test)
lr_prob = lr_model.predict_proba(X_expr_test)

lr_metrics = evaluate_predictions(y_test, lr_pred, lr_prob)
lr_ci = bootstrap_metrics(y_test, lr_pred, lr_prob)
lr_metrics.update(lr_ci)
lr_metrics["model"] = "LogReg_GeneExpr"
all_baseline_results.append(lr_metrics)

print(f"    Accuracy:    {lr_metrics['accuracy']:.4f} [{lr_metrics['accuracy_ci_lo']:.4f}, {lr_metrics['accuracy_ci_hi']:.4f}]")
print(f"    F1 weighted: {lr_metrics['f1_weighted']:.4f} [{lr_metrics['f1_weighted_ci_lo']:.4f}, {lr_metrics['f1_weighted_ci_hi']:.4f}]")
print(f"    AUROC macro: {lr_metrics['auroc_macro']:.4f} [{lr_metrics['auroc_macro_ci_lo']:.4f}, {lr_metrics['auroc_macro_ci_hi']:.4f}]")
print(f"    ECE:         {lr_metrics['ece']:.4f} [{lr_metrics['ece_ci_lo']:.4f}, {lr_metrics['ece_ci_hi']:.4f}]")

# --- Baseline (b): MLP on Gene Expression ---
print("\n  BASELINE (b): MLP on gene expression (2000->256->128)")
expr_loaders = make_loaders(X_expr_train, X_expr_val, X_expr_test, y_train, y_val, y_test)
mlp_expr = BaselineMLP(gene_dim, n_classes, hidden_dim=256).to(DEVICE)
n_params = sum(p.numel() for p in mlp_expr.parameters())
print(f"    Parameters: {n_params:,}")
mlp_expr = train_mlp(mlp_expr, expr_loaders[0], expr_loaders[1],
                      class_weights=class_weights.tolist())
mlp_expr_pred, mlp_expr_prob = predict_mlp(mlp_expr, expr_loaders[2])

mlp_expr_metrics = evaluate_predictions(y_test, mlp_expr_pred, mlp_expr_prob)
mlp_expr_ci = bootstrap_metrics(y_test, mlp_expr_pred, mlp_expr_prob)
mlp_expr_metrics.update(mlp_expr_ci)
mlp_expr_metrics["model"] = "MLP_GeneExpr"
all_baseline_results.append(mlp_expr_metrics)

print(f"    Accuracy:    {mlp_expr_metrics['accuracy']:.4f} [{mlp_expr_metrics['accuracy_ci_lo']:.4f}, {mlp_expr_metrics['accuracy_ci_hi']:.4f}]")
print(f"    F1 weighted: {mlp_expr_metrics['f1_weighted']:.4f} [{mlp_expr_metrics['f1_weighted_ci_lo']:.4f}, {mlp_expr_metrics['f1_weighted_ci_hi']:.4f}]")
print(f"    AUROC macro: {mlp_expr_metrics['auroc_macro']:.4f} [{mlp_expr_metrics['auroc_macro_ci_lo']:.4f}, {mlp_expr_metrics['auroc_macro_ci_hi']:.4f}]")
print(f"    ECE:         {mlp_expr_metrics['ece']:.4f} [{mlp_expr_metrics['ece_ci_lo']:.4f}, {mlp_expr_metrics['ece_ci_hi']:.4f}]")

# --- Baseline (c): MLP on Morphological Proxy ---
print("\n  BASELINE (c): MLP on morphological proxy (60->128->128)")
morph_loaders = make_loaders(X_morph_train, X_morph_val, X_morph_test, y_train, y_val, y_test)
mlp_morph = BaselineMLP(morph_dim, n_classes, hidden_dim=128).to(DEVICE)
n_params_m = sum(p.numel() for p in mlp_morph.parameters())
print(f"    Parameters: {n_params_m:,}")
mlp_morph = train_mlp(mlp_morph, morph_loaders[0], morph_loaders[1],
                       class_weights=class_weights.tolist())
mlp_morph_pred, mlp_morph_prob = predict_mlp(mlp_morph, morph_loaders[2])

mlp_morph_metrics = evaluate_predictions(y_test, mlp_morph_pred, mlp_morph_prob)
mlp_morph_ci = bootstrap_metrics(y_test, mlp_morph_pred, mlp_morph_prob)
mlp_morph_metrics.update(mlp_morph_ci)
mlp_morph_metrics["model"] = "MLP_MorphProxy"
all_baseline_results.append(mlp_morph_metrics)

print(f"    Accuracy:    {mlp_morph_metrics['accuracy']:.4f} [{mlp_morph_metrics['accuracy_ci_lo']:.4f}, {mlp_morph_metrics['accuracy_ci_hi']:.4f}]")
print(f"    F1 weighted: {mlp_morph_metrics['f1_weighted']:.4f} [{mlp_morph_metrics['f1_weighted_ci_lo']:.4f}, {mlp_morph_metrics['f1_weighted_ci_hi']:.4f}]")
print(f"    AUROC macro: {mlp_morph_metrics['auroc_macro']:.4f} [{mlp_morph_metrics['auroc_macro_ci_lo']:.4f}, {mlp_morph_metrics['auroc_macro_ci_hi']:.4f}]")
print(f"    ECE:         {mlp_morph_metrics['ece']:.4f} [{mlp_morph_metrics['ece_ci_lo']:.4f}, {mlp_morph_metrics['ece_ci_hi']:.4f}]")

# Save baseline metrics
baseline_df = pd.DataFrame(all_baseline_results)
baseline_df.to_csv(os.path.join(ARTIFACTS_DIR, "finegrained_baseline_metrics.csv"), index=False)
print(f"\n  Saved: finegrained_baseline_metrics.csv")
print(f"  STEP 2 complete in {time.time()-t1:.1f}s")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: FUSION MODELS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 3: FUSION MODELS (Fine-Grained)")
print("=" * 80)

t2 = time.time()

bimodal_loaders = make_bimodal_loaders(
    X_expr_train, X_morph_train, y_train,
    X_expr_val, X_morph_val, y_val,
    X_expr_test, X_morph_test, y_test)

all_fusion_results = []

# --- CrossAttentionFusion ---
print("\n  MODEL: CrossAttentionFusion")
fusion_model = CrossAttentionFusionModel(gene_dim, morph_dim, n_classes).to(DEVICE)
n_params_f = sum(p.numel() for p in fusion_model.parameters())
print(f"    Parameters: {n_params_f:,}")
print(f"    Architecture: GenomicEncoder({gene_dim}->256->128) + "
      f"MorphEncoder({morph_dim}->128->128) + CrossAttentionGate + Linear(128->{n_classes})")

fusion_model = train_fusion(fusion_model, bimodal_loaders[0], bimodal_loaders[1],
                             class_weights=class_weights.tolist())
fusion_pred, fusion_prob, fusion_attn = predict_fusion(fusion_model, bimodal_loaders[2])

fusion_metrics = evaluate_predictions(y_test, fusion_pred, fusion_prob)
fusion_ci = bootstrap_metrics(y_test, fusion_pred, fusion_prob)
fusion_metrics.update(fusion_ci)
fusion_metrics["model"] = "CrossAttentionFusion"
all_fusion_results.append(fusion_metrics)

print(f"    Accuracy:    {fusion_metrics['accuracy']:.4f} [{fusion_metrics['accuracy_ci_lo']:.4f}, {fusion_metrics['accuracy_ci_hi']:.4f}]")
print(f"    F1 weighted: {fusion_metrics['f1_weighted']:.4f} [{fusion_metrics['f1_weighted_ci_lo']:.4f}, {fusion_metrics['f1_weighted_ci_hi']:.4f}]")
print(f"    AUROC macro: {fusion_metrics['auroc_macro']:.4f} [{fusion_metrics['auroc_macro_ci_lo']:.4f}, {fusion_metrics['auroc_macro_ci_hi']:.4f}]")
print(f"    ECE:         {fusion_metrics['ece']:.4f} [{fusion_metrics['ece_ci_lo']:.4f}, {fusion_metrics['ece_ci_hi']:.4f}]")

if fusion_attn is not None:
    print(f"\n    Attention weight analysis (test set, overall):")
    print(f"      Genomic: mean={fusion_attn[:, 0].mean():.4f}, std={fusion_attn[:, 0].std():.4f}")
    print(f"      Morphological: mean={fusion_attn[:, 1].mean():.4f}, std={fusion_attn[:, 1].std():.4f}")
    # Per-class for top 10
    print(f"\n    Per-class attention (top 10 types):")
    for ci_idx in top10_class_indices:
        cname = class_names[ci_idx]
        mask = y_test == ci_idx
        if mask.sum() > 0:
            print(f"      {cname}: genomic={fusion_attn[mask, 0].mean():.4f}, "
                  f"morph={fusion_attn[mask, 1].mean():.4f} (n={mask.sum()})")

# Save fusion model
torch.save(fusion_model.state_dict(), os.path.join(ARTIFACTS_DIR, "finegrained_fusion_model.pt"))
fusion_config = {"gene_dim": gene_dim, "morph_dim": morph_dim,
                 "n_classes": n_classes, "embed_dim": EMBED_DIM}
with open(os.path.join(ARTIFACTS_DIR, "finegrained_fusion_model_config.json"), "w") as f:
    json.dump(fusion_config, f, indent=2)

# --- NaiveConcatFusion ---
print("\n  MODEL: NaiveConcatFusion")
concat_model = NaiveConcatFusionModel(gene_dim, morph_dim, n_classes).to(DEVICE)
n_params_c = sum(p.numel() for p in concat_model.parameters())
print(f"    Parameters: {n_params_c:,}")

concat_model = train_fusion(concat_model, bimodal_loaders[0], bimodal_loaders[1],
                             class_weights=class_weights.tolist())
concat_pred, concat_prob, _ = predict_fusion(concat_model, bimodal_loaders[2])

concat_metrics = evaluate_predictions(y_test, concat_pred, concat_prob)
concat_ci = bootstrap_metrics(y_test, concat_pred, concat_prob)
concat_metrics.update(concat_ci)
concat_metrics["model"] = "NaiveConcatFusion"
all_fusion_results.append(concat_metrics)

print(f"    Accuracy:    {concat_metrics['accuracy']:.4f} [{concat_metrics['accuracy_ci_lo']:.4f}, {concat_metrics['accuracy_ci_hi']:.4f}]")
print(f"    F1 weighted: {concat_metrics['f1_weighted']:.4f} [{concat_metrics['f1_weighted_ci_lo']:.4f}, {concat_metrics['f1_weighted_ci_hi']:.4f}]")
print(f"    AUROC macro: {concat_metrics['auroc_macro']:.4f} [{concat_metrics['auroc_macro_ci_lo']:.4f}, {concat_metrics['auroc_macro_ci_hi']:.4f}]")
print(f"    ECE:         {concat_metrics['ece']:.4f} [{concat_metrics['ece_ci_lo']:.4f}, {concat_metrics['ece_ci_hi']:.4f}]")

# Save concat model
torch.save(concat_model.state_dict(), os.path.join(ARTIFACTS_DIR, "finegrained_naive_concat_model.pt"))

# Save fusion metrics
fusion_df = pd.DataFrame(all_fusion_results)
fusion_df.to_csv(os.path.join(ARTIFACTS_DIR, "finegrained_fusion_metrics.csv"), index=False)

# Combined metrics
all_results = all_baseline_results + all_fusion_results
all_df = pd.DataFrame(all_results)
all_df.to_csv(os.path.join(ARTIFACTS_DIR, "finegrained_all_metrics.csv"), index=False)

print(f"\n  Saved: finegrained_fusion_metrics.csv, finegrained_all_metrics.csv")
print(f"  STEP 3 complete in {time.time()-t2:.1f}s")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4: EXPLAINABILITY (Attention + IG only, skip SHAP for speed)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 4: EXPLAINABILITY ANALYSIS (Fine-Grained)")
print("=" * 80)

t3 = time.time()

# Move model to CPU for explainability
fusion_model_cpu = CrossAttentionFusionModel(gene_dim, morph_dim, n_classes).to(EXPLAIN_DEVICE)
fusion_model_cpu.load_state_dict(
    torch.load(os.path.join(ARTIFACTS_DIR, "finegrained_fusion_model.pt"),
               map_location=EXPLAIN_DEVICE, weights_only=True))
fusion_model_cpu.eval()

# --- Method (a): Attention Weights ---
print("\n  METHOD (a): Built-in attention weights from CrossAttentionFusion")
with torch.no_grad():
    x_gene_t = torch.tensor(X_expr_test, dtype=torch.float32).to(EXPLAIN_DEVICE)
    x_morph_t = torch.tensor(X_morph_test, dtype=torch.float32).to(EXPLAIN_DEVICE)
    _ = fusion_model_cpu(x_gene_t, x_morph_t)
    attn_weights = fusion_model_cpu.get_attention_weights().cpu().numpy()

print(f"    Overall — Genomic: mean={attn_weights[:, 0].mean():.4f}, std={attn_weights[:, 0].std():.4f}")
print(f"    Overall — Morphological: mean={attn_weights[:, 1].mean():.4f}, std={attn_weights[:, 1].std():.4f}")

attn_per_class = {}
for ci_idx in range(n_classes):
    cname = class_names[ci_idx]
    mask = y_test == ci_idx
    if mask.sum() > 0:
        attn_per_class[cname] = {
            "genomic_mean": float(attn_weights[mask, 0].mean()),
            "genomic_std": float(attn_weights[mask, 0].std()),
            "module_mean": float(attn_weights[mask, 1].mean()),
            "module_std": float(attn_weights[mask, 1].std()),
            "n_samples": int(mask.sum()),
        }

print(f"\n    Per-class attention weights (top 10 types):")
for ci_idx in top10_class_indices:
    cname = class_names[ci_idx]
    if cname in attn_per_class:
        v = attn_per_class[cname]
        print(f"      {cname}: genomic={v['genomic_mean']:.4f}+/-{v['genomic_std']:.4f}, "
              f"morph={v['module_mean']:.4f}+/-{v['module_std']:.4f} (n={v['n_samples']})")


# --- Method (b): Captum Integrated Gradients ---
print("\n  METHOD (b): Captum IntegratedGradients on CrossAttentionFusion")
from captum.attr import IntegratedGradients

wrapper = FusionWrapper(fusion_model_cpu, gene_dim, morph_dim).to(EXPLAIN_DEVICE)
wrapper.eval()
ig = IntegratedGradients(wrapper)

X_combined_test = np.hstack([X_expr_test, X_morph_test]).astype(np.float32)
baseline_vec = np.zeros((1, X_combined_test.shape[1]), dtype=np.float32)
baseline_t = torch.tensor(baseline_vec, dtype=torch.float32).to(EXPLAIN_DEVICE)

ig_attributions = np.zeros_like(X_combined_test)
ig_batch_size = 32

print(f"    Computing IG for {len(y_test)} test samples...")
for start in range(0, len(X_combined_test), ig_batch_size):
    end = min(start + ig_batch_size, len(X_combined_test))
    batch_input = torch.tensor(X_combined_test[start:end], dtype=torch.float32).to(EXPLAIN_DEVICE)
    batch_input.requires_grad_(True)
    batch_targets = torch.tensor(y_test[start:end], dtype=torch.long).to(EXPLAIN_DEVICE)
    batch_baseline = baseline_t.expand(end - start, -1)

    attr = ig.attribute(
        batch_input, baselines=batch_baseline, target=batch_targets,
        n_steps=50, internal_batch_size=32)
    ig_attributions[start:end] = attr.detach().cpu().numpy()

    if (start // ig_batch_size) % 5 == 0:
        print(f"      Processed {end}/{len(X_combined_test)} samples")

# Split IG by modality
ig_gene = ig_attributions[:, :gene_dim]
ig_morph = ig_attributions[:, gene_dim:]

ig_gene_importance = np.abs(ig_gene).sum(axis=1)
ig_morph_importance = np.abs(ig_morph).sum(axis=1)
ig_total = ig_gene_importance + ig_morph_importance + 1e-10

ig_gene_frac = ig_gene_importance / ig_total
ig_morph_frac = ig_morph_importance / ig_total

print(f"    IG modality attribution (overall):")
print(f"      Genomic: mean={ig_gene_frac.mean():.4f}, std={ig_gene_frac.std():.4f}")
print(f"      Morphological: mean={ig_morph_frac.mean():.4f}, std={ig_morph_frac.std():.4f}")

ig_per_class = {}
for ci_idx in range(n_classes):
    cname = class_names[ci_idx]
    mask = y_test == ci_idx
    if mask.sum() > 0:
        ig_per_class[cname] = {
            "genomic_frac": float(ig_gene_frac[mask].mean()),
            "module_frac": float(ig_morph_frac[mask].mean()),
        }

print(f"\n    IG modality attribution (top 10 types):")
for ci_idx in top10_class_indices:
    cname = class_names[ci_idx]
    if cname in ig_per_class:
        print(f"      {cname}: genomic={ig_per_class[cname]['genomic_frac']:.4f}, "
              f"morph={ig_per_class[cname]['module_frac']:.4f}")

# Top-5 genes per class by IG (for top 10 most common types)
print(f"\n    Top-5 genes per class by IG attribution (top 10 types):")
ig_top_genes_per_class = {}
for ci_idx in range(n_classes):
    cname = class_names[ci_idx]
    mask = y_test == ci_idx
    if mask.sum() == 0:
        continue
    mean_ig = np.abs(ig_gene[mask]).mean(axis=0)
    top_indices = np.argsort(mean_ig)[::-1][:TOP_K_FEATURES]
    top_genes = [gene_names[i] for i in top_indices]
    top_values = mean_ig[top_indices]
    ig_top_genes_per_class[cname] = {
        "genes": top_genes,
        "attributions": top_values.tolist(),
    }

# Print top 5 for the 10 most common types
for ci_idx in top10_class_indices:
    cname = class_names[ci_idx]
    if cname in ig_top_genes_per_class:
        genes = ig_top_genes_per_class[cname]["genes"][:5]
        attrs = ig_top_genes_per_class[cname]["attributions"][:5]
        gene_str = ", ".join([f"{g} ({a:.4f})" for g, a in zip(genes, attrs)])
        print(f"      {cname}: {gene_str}")

# --- Comparison table (Attention vs IG, no SHAP) ---
print("\n  COMPARISON: Modality attribution — Attention vs. IG")

comparison = {
    "method": ["Attention Weights", "Integrated Gradients"],
    "genomic_mean": [
        float(attn_weights[:, 0].mean()),
        float(ig_gene_frac.mean()),
    ],
    "genomic_std": [
        float(attn_weights[:, 0].std()),
        float(ig_gene_frac.std()),
    ],
    "module_mean": [
        float(attn_weights[:, 1].mean()),
        float(ig_morph_frac.mean()),
    ],
    "module_std": [
        float(attn_weights[:, 1].std()),
        float(ig_morph_frac.std()),
    ],
    "model": ["CrossAttentionFusion", "CrossAttentionFusion"],
}

comparison_df = pd.DataFrame(comparison)
comparison_df.to_csv(os.path.join(ARTIFACTS_DIR, "finegrained_explainability_comparison.csv"), index=False)
print(comparison_df.to_string(index=False))

# Save all explainability data
np.save(os.path.join(ARTIFACTS_DIR, "finegrained_attn_weights_test.npy"), attn_weights)
np.save(os.path.join(ARTIFACTS_DIR, "finegrained_ig_attributions_gene.npy"), ig_gene)
np.save(os.path.join(ARTIFACTS_DIR, "finegrained_ig_attributions_morph.npy"), ig_morph)

with open(os.path.join(ARTIFACTS_DIR, "finegrained_ig_top_genes_per_class.json"), "w") as f:
    json.dump(ig_top_genes_per_class, f, indent=2)
with open(os.path.join(ARTIFACTS_DIR, "finegrained_attn_per_class.json"), "w") as f:
    json.dump(attn_per_class, f, indent=2)
with open(os.path.join(ARTIFACTS_DIR, "finegrained_ig_per_class.json"), "w") as f:
    json.dump(ig_per_class, f, indent=2)

print(f"\n  STEP 4 complete in {time.time()-t3:.1f}s")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5: FIGURES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 5: GENERATING FIGURES (Fine-Grained)")
print("=" * 80)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight",
    "font.size": 10, "axes.titlesize": 12, "axes.labelsize": 11,
})

# --- Figure 1: AUROC comparison ---
fig, ax = plt.subplots(figsize=(10, 5))
models = all_df["model"].values
aurocs = all_df["auroc_macro"].values
ci_lo = all_df["auroc_macro_ci_lo"].values
ci_hi = all_df["auroc_macro_ci_hi"].values
errors = np.array([np.clip(aurocs - ci_lo, 0, None), np.clip(ci_hi - aurocs, 0, None)])
colors = sns.color_palette("Set2", n_colors=len(models))

bars = ax.bar(range(len(models)), aurocs, yerr=errors, capsize=5,
              color=colors, edgecolor="black", linewidth=0.5, alpha=0.85)
ax.set_xticks(range(len(models)))
ax.set_xticklabels([m.replace("_", "\n") for m in models], rotation=0, fontsize=9)
ax.set_ylabel("AUROC (macro, OVR)")
ax.set_title(f"Fine-Grained ({n_classes} types): AUROC by Model (with 95% CI)")
ax.set_ylim(0, 1.05)
for bar, val, lo, hi in zip(bars, aurocs, ci_lo, ci_hi):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.015,
            f"{val:.3f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
ax.axhline(y=0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "finegrained_auroc_comparison.png"))
plt.close(fig)
print("  Saved: finegrained_auroc_comparison.png")

# --- Figure 2: Multi-metric comparison ---
fig, axes = plt.subplots(1, 4, figsize=(18, 5))
for ax, metric, label in zip(axes,
    ["accuracy", "f1_weighted", "auroc_macro", "ece"],
    ["Accuracy", "F1 (Weighted)", "AUROC (Macro)", "ECE"]):
    vals = all_df[metric].values
    lo = all_df[f"{metric}_ci_lo"].values
    hi = all_df[f"{metric}_ci_hi"].values
    errs = np.array([np.clip(vals - lo, 0, None), np.clip(hi - vals, 0, None)])
    bars = ax.bar(range(len(models)), vals, yerr=errs, capsize=4,
                  color=colors, edgecolor="black", linewidth=0.5, alpha=0.85)
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels([m.replace("_", "\n") for m in models], rotation=45, ha="right", fontsize=7)
    ax.set_title(label)
    ax.grid(axis="y", alpha=0.3)
    if metric == "ece":
        ax.set_ylim(0, max(vals) * 1.5 + 0.01)
    else:
        ax.set_ylim(0, 1.05)
fig.suptitle(f"Fine-Grained ({n_classes} types): Model Comparison (95% Bootstrap CIs)", fontsize=13, y=1.02)
fig.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "finegrained_multi_metric_comparison.png"))
plt.close(fig)
print("  Saved: finegrained_multi_metric_comparison.png")

# --- Figure 3: Modality attribution heatmap (top 10 types) ---
if attn_per_class and ig_per_class:
    cell_types = [class_names[ci] for ci in top10_class_indices
                  if class_names[ci] in attn_per_class and class_names[ci] in ig_per_class]
    if cell_types:
        heatmap_data = np.zeros((len(cell_types), 4))
        col_labels = ["Attention\nGenomic", "Attention\nMorph", "IG\nGenomic", "IG\nMorph"]
        for i, ct in enumerate(cell_types):
            heatmap_data[i, 0] = attn_per_class[ct]["genomic_mean"]
            heatmap_data[i, 1] = attn_per_class[ct]["module_mean"]
            heatmap_data[i, 2] = ig_per_class[ct]["genomic_frac"]
            heatmap_data[i, 3] = ig_per_class[ct]["module_frac"]

        fig, ax = plt.subplots(figsize=(10, max(5, len(cell_types) * 0.7)))
        im = ax.imshow(heatmap_data, cmap="YlOrRd", aspect="auto", vmin=0, vmax=1)
        ax.set_xticks(range(4))
        ax.set_xticklabels(col_labels, fontsize=9)
        ax.set_yticks(range(len(cell_types)))
        ax.set_yticklabels(cell_types, fontsize=8)
        ax.set_title(f"Fine-Grained: Modality Attribution (Top 10 Types)")
        for i in range(len(cell_types)):
            for j in range(4):
                text_color = "white" if heatmap_data[i, j] > 0.6 else "black"
                ax.text(j, i, f"{heatmap_data[i, j]:.3f}",
                        ha="center", va="center", fontsize=8, color=text_color)
        plt.colorbar(im, ax=ax, label="Attribution Weight / Fraction", shrink=0.8)
        fig.tight_layout()
        fig.savefig(os.path.join(FIGURES_DIR, "finegrained_modality_attribution_heatmap.png"))
        plt.close(fig)
        print("  Saved: finegrained_modality_attribution_heatmap.png")

# --- Figure 4: Class distribution ---
fig, ax = plt.subplots(figsize=(14, 6))
pt_sorted = pt_final.sort_values(ascending=True)
bars = ax.barh(range(len(pt_sorted)), pt_sorted.values,
               color=sns.color_palette("husl", len(pt_sorted)), alpha=0.85, edgecolor="black", linewidth=0.3)
ax.set_yticks(range(len(pt_sorted)))
ax.set_yticklabels(pt_sorted.index, fontsize=7)
ax.set_xlabel("Number of cells")
ax.set_title(f"Fine-Grained Cell Type Distribution ({n_classes} types, {adata_hvg.n_obs} cells)")
for bar, val in zip(bars, pt_sorted.values):
    ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height() / 2,
            str(val), ha="left", va="center", fontsize=6)
ax.grid(axis="x", alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "finegrained_class_distribution.png"))
plt.close(fig)
print("  Saved: finegrained_class_distribution.png")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6: COMPREHENSIVE SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 6: COMPREHENSIVE RESULTS SUMMARY (Fine-Grained)")
print("=" * 80)

print("\n" + "=" * 80)
print(f"TABLE 1: MODEL PERFORMANCE — FINE-GRAINED ({n_classes} types)")
print("=" * 80)
print(f"\n{'Model':<25} {'Accuracy':>10} {'F1 (wt)':>10} {'AUROC':>10} {'ECE':>10}")
print("-" * 70)
for _, row in all_df.iterrows():
    print(f"{row['model']:<25} {row['accuracy']:>10.4f} {row['f1_weighted']:>10.4f} "
          f"{row['auroc_macro']:>10.4f} {row['ece']:>10.4f}")
print("-" * 70)

print("\n\nTABLE 1b: PERFORMANCE WITH 95% BOOTSTRAP CIs")
print("-" * 80)
for _, row in all_df.iterrows():
    print(f"\n  {row['model']}:")
    for metric in ["accuracy", "f1_weighted", "auroc_macro", "ece"]:
        val = row[metric]
        ci_lo = row.get(f"{metric}_ci_lo", np.nan)
        ci_hi = row.get(f"{metric}_ci_hi", np.nan)
        print(f"    {metric:>15}: {val:.4f} [{ci_lo:.4f}, {ci_hi:.4f}]")

print("\n\n" + "=" * 80)
print("TABLE 2: MODALITY ATTRIBUTION COMPARISON")
print("=" * 80)
print(f"\n{'Method':<25} {'Genomic (mean +/- std)':>25} {'Morph (mean +/- std)':>25}")
print("-" * 80)
for _, row in comparison_df.iterrows():
    g_str = f"{row['genomic_mean']:.4f} +/- {row['genomic_std']:.4f}"
    m_str = f"{row['module_mean']:.4f} +/- {row['module_std']:.4f}"
    print(f"{row['method']:<25} {g_str:>25} {m_str:>25}")
print("-" * 80)

print("\n\n" + "=" * 80)
print("TABLE 3: PER-CLASS ATTENTION WEIGHTS (Top 10 Types)")
print("=" * 80)
print(f"\n{'Cell Type':<35} {'Genomic (mean)':>15} {'Morph (mean)':>15} {'N samples':>10}")
print("-" * 80)
for ci_idx in top10_class_indices:
    cname = class_names[ci_idx]
    if cname in attn_per_class:
        v = attn_per_class[cname]
        print(f"{cname:<35} {v['genomic_mean']:>15.4f} {v['module_mean']:>15.4f} {v['n_samples']:>10}")

print("\n\n" + "=" * 80)
print("TABLE 4: TOP-5 GENES BY IG ATTRIBUTION (Top 10 Types)")
print("=" * 80)
for ci_idx in top10_class_indices:
    cname = class_names[ci_idx]
    if cname in ig_top_genes_per_class:
        genes = ig_top_genes_per_class[cname]["genes"][:5]
        attrs = ig_top_genes_per_class[cname]["attributions"][:5]
        gene_str = ", ".join([f"{g} ({a:.4f})" for g, a in zip(genes, attrs)])
        print(f"  {cname}: {gene_str}")

print("\n\n" + "=" * 80)
print("DATASET SUMMARY")
print("=" * 80)
print(f"  Source: Tasic et al. 2016, Allen Institute for Brain Science")
print(f"  Tissue: Mouse primary visual cortex (V1)")
print(f"  Technology: SMART-seq single-cell RNA-seq")
print(f"  Label column: primary_type (fine-grained)")
print(f"  Cells after QC & type filter (>={MIN_CELLS_PER_TYPE}): {adata_hvg.n_obs}")
print(f"  Types dropped (<{MIN_CELLS_PER_TYPE} cells): {len(types_dropped)}")
print(f"  HVGs selected: {adata_hvg.n_vars}")
print(f"  PCA components (Modality 2): {N_PCA_COMPONENTS}")
print(f"  PCA total variance explained: {pca.explained_variance_ratio_.sum():.4f}")
print(f"  Classes: {n_classes} fine-grained types")
print(f"  Train/Val/Test: {len(train_idx)}/{len(val_idx)}/{len(test_idx)}")

print(f"\n  Comparison to broad-type pipeline:")
print(f"    Broad types: 7 classes -> Fine-grained: {n_classes} classes")
print(f"    Expected: accuracy and AUROC should drop significantly")
print(f"    This validates that the fusion model has real discriminative value")

total_time = time.time() - t0
print(f"\n{'='*80}")
print(f"PIPELINE COMPLETE — Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
print(f"{'='*80}")

# List all saved artifacts
print("\n  Artifacts saved:")
for fname in sorted(os.listdir(ARTIFACTS_DIR)):
    if fname.startswith("finegrained_"):
        fpath = os.path.join(ARTIFACTS_DIR, fname)
        if os.path.isfile(fpath):
            size_kb = os.path.getsize(fpath) / 1024
            print(f"    {fname} ({size_kb:.1f} KB)")

print("\n  Figures saved:")
for fname in sorted(os.listdir(FIGURES_DIR)):
    if fname.startswith("finegrained_"):
        fpath = os.path.join(FIGURES_DIR, fname)
        size_kb = os.path.getsize(fpath) / 1024
        print(f"    {fname} ({size_kb:.1f} KB)")
