#!/usr/bin/env python3
"""
run_tasic2018_pipeline.py — Scale-up experiments on Tasic 2018 (~24K cells).

Downloads Tasic et al. 2018 SMART-seq data from GEO GSE115746,
preprocesses identically to the Tasic 2016 pipeline, and runs all models.

Outputs saved to P22/experiments/:
  - tasic2018_broadtype_metrics.csv
  - tasic2018_finegrained_metrics.csv
  - tasic2018_ablation_broadtype.csv (attention weights per class, broad)
  - tasic2018_ablation_finegrained.csv (attention weights per class, fine)
  - tasic2018_mcnemar.json
  - tasic2018_mutual_information.json
  - tasic2018_summary.json
"""

import os
import sys
import json
import tempfile
import time
import gzip
import warnings
import numpy as np
import pandas as pd
import scanpy as sc
from io import StringIO
from scipy import sparse
from scipy.stats import spearmanr
from sklearn.model_selection import train_test_split
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score, confusion_matrix
)
from sklearn.preprocessing import label_binarize
from sklearn.feature_selection import mutual_info_classif
from sklearn.metrics import mutual_info_score
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

def writable_dir(preferred, fallback):
    """Use preferred output directory, falling back when sandbox blocks writes."""
    try:
        os.makedirs(preferred, exist_ok=True)
        probe = os.path.join(preferred, ".p22_write_test")
        with open(probe, "w"):
            pass
        os.remove(probe)
        return preferred
    except OSError:
        os.makedirs(fallback, exist_ok=True)
        print(f"Directory not writable: {preferred}; using {fallback}")
        return fallback


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RUNTIME_ROOT = os.path.join(tempfile.gettempdir(), "P22")
DATA_DIR = writable_dir(os.path.join(PROJECT_ROOT, "data"), os.path.join(RUNTIME_ROOT, "data"))
EXPERIMENTS_DIR = writable_dir(SCRIPT_DIR, os.path.join(RUNTIME_ROOT, "experiments"))

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Device: {DEVICE}")

# Hyperparameters
BATCH_SIZE = 64
N_EPOCHS = 120
LR = 1e-3
PATIENCE = 15
N_BOOTSTRAP = 1000
EMBED_DIM = 128
N_TOP_GENES = 2000
N_PCA_COMPONENTS = 60
MIN_CELLS_PER_TYPE = 10


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

class GenomicEncoder(nn.Module):
    def __init__(self, input_dim, embed_dim=EMBED_DIM):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, embed_dim),
        )
    def forward(self, x):
        return self.net(x)


class MorphEncoder(nn.Module):
    def __init__(self, input_dim, embed_dim=EMBED_DIM):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, embed_dim),
        )
    def forward(self, x):
        return self.net(x)


class CrossAttentionGate(nn.Module):
    def __init__(self, embed_dim=EMBED_DIM):
        super().__init__()
        self.attention_proj = nn.Sequential(
            nn.Linear(embed_dim, 64), nn.Tanh(), nn.Linear(64, 1),
        )
        self.last_attention_weights = None

    def forward(self, z_genomic, z_morph):
        stacked = torch.stack([z_genomic, z_morph], dim=1)
        attn_logits = self.attention_proj(stacked).squeeze(-1)
        attn_weights = F.softmax(attn_logits, dim=1)
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
        return self.classifier(z_fused)

    def get_attention_weights(self):
        return self.attention_gate.last_attention_weights


class NaiveConcatFusionModel(nn.Module):
    def __init__(self, gene_dim, morph_dim, n_classes, embed_dim=EMBED_DIM):
        super().__init__()
        self.genomic_encoder = GenomicEncoder(gene_dim, embed_dim)
        self.morph_encoder = MorphEncoder(morph_dim, embed_dim)
        self.classifier = nn.Sequential(
            nn.Linear(embed_dim * 2, embed_dim), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(embed_dim, n_classes),
        )

    def forward(self, x_gene, x_morph):
        z_g = self.genomic_encoder(x_gene)
        z_m = self.morph_encoder(x_morph)
        return self.classifier(torch.cat([z_g, z_m], dim=1))


class BaselineMLP(nn.Module):
    def __init__(self, in_dim, n_classes, hidden_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden_dim), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(hidden_dim, 128), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(128, n_classes),
        )
    def forward(self, x):
        return self.net(x)


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


def bootstrap_ci(y_true, y_pred, y_prob, n_bootstrap=N_BOOTSTRAP):
    rng = np.random.default_rng(SEED)
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
        if vals:
            ci[f"{k}_ci_lo"] = float(np.percentile(vals, 2.5))
            ci[f"{k}_ci_hi"] = float(np.percentile(vals, 97.5))
    return ci


def make_loaders(X_tr, X_vl, X_te, y_tr, y_vl, y_te, bs=BATCH_SIZE):
    def _ds(X, y, shuf):
        return DataLoader(TensorDataset(
            torch.tensor(X, dtype=torch.float32),
            torch.tensor(y, dtype=torch.long)
        ), batch_size=bs, shuffle=shuf)
    return _ds(X_tr, y_tr, True), _ds(X_vl, y_vl, False), _ds(X_te, y_te, False)


def make_bimodal_loaders(Xg_tr, Xm_tr, y_tr, Xg_vl, Xm_vl, y_vl,
                         Xg_te, Xm_te, y_te, bs=BATCH_SIZE):
    def _ds(xg, xm, y, shuf):
        return DataLoader(TensorDataset(
            torch.tensor(xg, dtype=torch.float32),
            torch.tensor(xm, dtype=torch.float32),
            torch.tensor(y, dtype=torch.long)
        ), batch_size=bs, shuffle=shuf)
    return (_ds(Xg_tr, Xm_tr, y_tr, True),
            _ds(Xg_vl, Xm_vl, y_vl, False),
            _ds(Xg_te, Xm_te, y_te, False))


def train_mlp(model, train_ld, val_ld, class_weights=None):
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, factor=0.5, patience=5)
    criterion = nn.CrossEntropyLoss(
        weight=torch.tensor(class_weights, dtype=torch.float32).to(DEVICE)
    ) if class_weights is not None else nn.CrossEntropyLoss()

    best_val, best_state, no_improve = float("inf"), None, 0
    t0 = time.time()
    for epoch in range(N_EPOCHS):
        model.train()
        for xb, yb in train_ld:
            xb, yb = xb.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
        model.eval()
        vl = 0.0; nb = 0
        with torch.no_grad():
            for xb, yb in val_ld:
                xb, yb = xb.to(DEVICE), yb.to(DEVICE)
                vl += criterion(model(xb), yb).item(); nb += 1
        avg_vl = vl / max(nb, 1)
        scheduler.step(avg_vl)
        if avg_vl < best_val:
            best_val = avg_vl
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            no_improve = 0
        else:
            no_improve += 1
        if no_improve >= PATIENCE:
            break
    if best_state:
        model.load_state_dict(best_state)
    return model, epoch + 1, time.time() - t0


def train_fusion(model, train_ld, val_ld, class_weights=None):
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, factor=0.5, patience=5)
    criterion = nn.CrossEntropyLoss(
        weight=torch.tensor(class_weights, dtype=torch.float32).to(DEVICE)
    ) if class_weights is not None else nn.CrossEntropyLoss()

    best_val, best_state, no_improve = float("inf"), None, 0
    t0 = time.time()
    for epoch in range(N_EPOCHS):
        model.train()
        for xg, xm, yb in train_ld:
            xg, xm, yb = xg.to(DEVICE), xm.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            loss = criterion(model(xg, xm), yb)
            loss.backward()
            optimizer.step()
        model.eval()
        vl = 0.0; nb = 0
        with torch.no_grad():
            for xg, xm, yb in val_ld:
                xg, xm, yb = xg.to(DEVICE), xm.to(DEVICE), yb.to(DEVICE)
                vl += criterion(model(xg, xm), yb).item(); nb += 1
        avg_vl = vl / max(nb, 1)
        scheduler.step(avg_vl)
        if avg_vl < best_val:
            best_val = avg_vl
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            no_improve = 0
        else:
            no_improve += 1
        if no_improve >= PATIENCE:
            break
    if best_state:
        model.load_state_dict(best_state)
    return model, epoch + 1, time.time() - t0


def predict_mlp(model, loader):
    model.eval()
    preds, probs = [], []
    with torch.no_grad():
        for xb, _ in loader:
            logits = model(xb.to(DEVICE))
            probs.append(torch.softmax(logits, 1).cpu().numpy())
            preds.extend(logits.argmax(1).cpu().numpy())
    return np.array(preds), np.vstack(probs)


def predict_fusion(model, loader):
    model.eval()
    preds, probs, attns = [], [], []
    with torch.no_grad():
        for xg, xm, _ in loader:
            xg, xm = xg.to(DEVICE), xm.to(DEVICE)
            logits = model(xg, xm)
            probs.append(torch.softmax(logits, 1).cpu().numpy())
            preds.extend(logits.argmax(1).cpu().numpy())
            if hasattr(model, 'get_attention_weights'):
                a = model.get_attention_weights()
                if a is not None:
                    attns.append(a.cpu().numpy())
    return np.array(preds), np.vstack(probs), np.vstack(attns) if attns else None


def run_all_models(X_expr, X_morph, label_codes, class_names, class_weights,
                   train_idx, val_idx, test_idx, tag=""):
    """Run all 5 models and return results dict + per-sample predictions."""
    gene_dim = X_expr.shape[1]
    morph_dim = X_morph.shape[1]
    n_classes = len(class_names)
    y_tr = label_codes[train_idx]
    y_vl = label_codes[val_idx]
    y_te = label_codes[test_idx]

    results = []
    all_preds = {}  # model_name -> predictions array

    # --- Logistic Regression ---
    print(f"  [{tag}] Logistic Regression...")
    lr = LogisticRegression(max_iter=2000, C=1.0, solver="lbfgs",
                            random_state=SEED)
    lr.fit(X_expr[train_idx], y_tr)
    lr_preds = lr.predict(X_expr[test_idx])
    lr_probs = lr.predict_proba(X_expr[test_idx])
    m = evaluate_predictions(y_te, lr_preds, lr_probs)
    ci = bootstrap_ci(y_te, lr_preds, lr_probs)
    m.update(ci); m["model"] = "LogReg_GeneExpr"
    results.append(m)
    all_preds["LogReg_GeneExpr"] = lr_preds
    print(f"    Acc={m['accuracy']:.4f}")

    # --- MLP Genomic ---
    print(f"  [{tag}] MLP Genomic...")
    torch.manual_seed(SEED)
    tr_ld, vl_ld, te_ld = make_loaders(
        X_expr[train_idx], X_expr[val_idx], X_expr[test_idx], y_tr, y_vl, y_te)
    mlp_g = BaselineMLP(gene_dim, n_classes).to(DEVICE)
    mlp_g, ep, wt = train_mlp(mlp_g, tr_ld, vl_ld, class_weights)
    mlp_g_preds, mlp_g_probs = predict_mlp(mlp_g, te_ld)
    m = evaluate_predictions(y_te, mlp_g_preds, mlp_g_probs)
    ci = bootstrap_ci(y_te, mlp_g_preds, mlp_g_probs)
    m.update(ci); m["model"] = "MLP_GeneExpr"; m["epochs"] = ep
    results.append(m)
    all_preds["MLP_GeneExpr"] = mlp_g_preds
    print(f"    Acc={m['accuracy']:.4f}, Epochs={ep}")

    # --- MLP Program Proxy ---
    print(f"  [{tag}] MLP Program Proxy...")
    torch.manual_seed(SEED)
    tr_ld, vl_ld, te_ld = make_loaders(
        X_morph[train_idx], X_morph[val_idx], X_morph[test_idx], y_tr, y_vl, y_te)
    mlp_m = BaselineMLP(morph_dim, n_classes, hidden_dim=128).to(DEVICE)
    mlp_m, ep, wt = train_mlp(mlp_m, tr_ld, vl_ld, class_weights)
    mlp_m_preds, mlp_m_probs = predict_mlp(mlp_m, te_ld)
    m = evaluate_predictions(y_te, mlp_m_preds, mlp_m_probs)
    ci = bootstrap_ci(y_te, mlp_m_preds, mlp_m_probs)
    m.update(ci); m["model"] = "MLP_MorphProxy"; m["epochs"] = ep
    results.append(m)
    all_preds["MLP_MorphProxy"] = mlp_m_preds
    print(f"    Acc={m['accuracy']:.4f}, Epochs={ep}")

    # --- Concat Fusion ---
    print(f"  [{tag}] Concat Fusion...")
    torch.manual_seed(SEED)
    tr_ld, vl_ld, te_ld = make_bimodal_loaders(
        X_expr[train_idx], X_morph[train_idx], y_tr,
        X_expr[val_idx], X_morph[val_idx], y_vl,
        X_expr[test_idx], X_morph[test_idx], y_te)
    concat = NaiveConcatFusionModel(gene_dim, morph_dim, n_classes).to(DEVICE)
    concat, ep, wt = train_fusion(concat, tr_ld, vl_ld, class_weights)
    concat_preds, concat_probs, _ = predict_fusion(concat, te_ld)
    m = evaluate_predictions(y_te, concat_preds, concat_probs)
    ci = bootstrap_ci(y_te, concat_preds, concat_probs)
    m.update(ci); m["model"] = "NaiveConcatFusion"; m["epochs"] = ep
    results.append(m)
    all_preds["NaiveConcatFusion"] = concat_preds
    print(f"    Acc={m['accuracy']:.4f}, Epochs={ep}")

    # --- Attention-Gated Fusion ---
    print(f"  [{tag}] Attention-Gated Fusion...")
    torch.manual_seed(SEED)
    tr_ld, vl_ld, te_ld = make_bimodal_loaders(
        X_expr[train_idx], X_morph[train_idx], y_tr,
        X_expr[val_idx], X_morph[val_idx], y_vl,
        X_expr[test_idx], X_morph[test_idx], y_te)
    attn = CrossAttentionFusionModel(gene_dim, morph_dim, n_classes).to(DEVICE)
    attn, ep, wt = train_fusion(attn, tr_ld, vl_ld, class_weights)
    attn_preds, attn_probs, attn_weights = predict_fusion(attn, te_ld)
    m = evaluate_predictions(y_te, attn_preds, attn_probs)
    ci = bootstrap_ci(y_te, attn_preds, attn_probs)
    m.update(ci); m["model"] = "CrossAttentionFusion"; m["epochs"] = ep
    results.append(m)
    all_preds["CrossAttentionFusion"] = attn_preds
    print(f"    Acc={m['accuracy']:.4f}, Epochs={ep}")

    return results, all_preds, attn_weights, attn_preds, concat_preds


def compute_per_class_attention(attn_weights, y_test, class_names, test_idx):
    """Compute per-class attention weight means with sample sizes."""
    rows = []
    for ci, cname in enumerate(class_names):
        mask = (y_test == ci)
        n = mask.sum()
        if n == 0:
            continue
        geno_mean = float(attn_weights[mask, 0].mean())
        prog_mean = float(attn_weights[mask, 1].mean())
        geno_std = float(attn_weights[mask, 0].std()) if n > 1 else 0.0
        rows.append({
            "cell_type": cname,
            "n_test": int(n),
            "genomic_mean": round(geno_mean, 4),
            "program_mean": round(prog_mean, 4),
            "genomic_std": round(geno_std, 4),
        })
    return pd.DataFrame(rows).sort_values("program_mean", ascending=False)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: DOWNLOAD TASIC 2018 DATA
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 1: DOWNLOAD TASIC 2018 DATA (GEO GSE115746)")
print("=" * 80)

import requests

GEO_BASE = "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE115nnn/GSE115746/suppl/"
COUNTS_FILE = "GSE115746_cells_exon_counts.csv.gz"
META_FILE = "GSE115746_complete_metadata_28706-cells.csv.gz"

counts_path = os.path.join(DATA_DIR, COUNTS_FILE)
meta_path = os.path.join(DATA_DIR, META_FILE)

for fname, fpath in [(COUNTS_FILE, counts_path), (META_FILE, meta_path)]:
    if os.path.exists(fpath):
        print(f"  Already downloaded: {fname} ({os.path.getsize(fpath)/1e6:.1f} MB)")
    else:
        url = GEO_BASE + fname
        print(f"  Downloading {fname}...")
        t0 = time.time()
        r = requests.get(url, stream=True, timeout=600)
        r.raise_for_status()
        with open(fpath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192*16):
                f.write(chunk)
        print(f"    Done in {time.time()-t0:.1f}s ({os.path.getsize(fpath)/1e6:.1f} MB)")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: LOAD AND BUILD ANNDATA
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 2: LOAD AND BUILD ANNDATA")
print("=" * 80)

h5ad_path = os.path.join(DATA_DIR, "tasic2018_raw.h5ad")

if os.path.exists(h5ad_path):
    print(f"  Loading cached h5ad: {h5ad_path}")
    adata = sc.read_h5ad(h5ad_path)
else:
    print("  Reading metadata...")
    t0 = time.time()
    meta = pd.read_csv(meta_path, compression='gzip', index_col=0)
    print(f"    Metadata: {meta.shape[0]} cells, columns: {list(meta.columns[:15])}...")
    print(f"    Read in {time.time()-t0:.1f}s")

    print("  Reading expression matrix (this may take a few minutes)...")
    t0 = time.time()
    # The counts file is genes x cells — read and transpose
    counts_df = pd.read_csv(counts_path, compression='gzip', index_col=0)
    print(f"    Raw matrix: {counts_df.shape} (genes x cells)")
    print(f"    Read in {time.time()-t0:.1f}s")

    # Transpose to cells x genes
    print("  Transposing to cells x genes...")
    counts_df = counts_df.T
    print(f"    Transposed: {counts_df.shape}")

    # Align metadata and expression
    common_cells = counts_df.index.intersection(meta.index)
    print(f"  Common cells: {len(common_cells)}")
    counts_df = counts_df.loc[common_cells]
    meta = meta.loc[common_cells]

    # Build AnnData
    print("  Building AnnData...")
    adata = sc.AnnData(
        X=sparse.csr_matrix(counts_df.values.astype(np.float32)),
        obs=meta,
        var=pd.DataFrame(index=counts_df.columns),
    )
    print(f"    AnnData: {adata.shape}")

    # Cache as h5ad
    print(f"  Caching to {h5ad_path}...")
    adata.write_h5ad(h5ad_path)
    print(f"    Saved ({os.path.getsize(h5ad_path)/1e6:.1f} MB)")

print(f"  Final: {adata.n_obs} cells x {adata.n_vars} genes")
print(f"  Obs columns: {list(adata.obs.columns[:15])}")

# Identify the label columns — Tasic 2018 uses different column names
# Look for class/subclass/cluster columns
print(f"\n  Looking for label columns...")
for col in adata.obs.columns:
    nunique = adata.obs[col].nunique()
    if 2 <= nunique <= 200:
        print(f"    {col}: {nunique} unique values")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: MAP LABELS TO MATCH PAPER FORMAT
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 3: MAP LABELS")
print("=" * 80)

# The Tasic 2018 metadata typically has:
#   - 'class' or 'class_label' for broad type (Glutamatergic, GABAergic, Non-Neuronal)
#   - 'subclass' or 'subclass_label' for medium granularity
#   - 'cluster' or 'cluster_label' for fine-grained types
# We need to identify the right columns

# Try common column names
broad_col = None
fine_col = None

for candidate in ['cell_class', 'class_label', 'class', 'broad_type']:
    if candidate in adata.obs.columns:
        broad_col = candidate
        break

for candidate in ['cell_cluster', 'cluster_label', 'cluster', 'primary_type']:
    if candidate in adata.obs.columns:
        fine_col = candidate
        break

if broad_col is None or fine_col is None:
    raise ValueError(f"Could not find label columns. Available: {list(adata.obs.columns)}")

print(f"  Broad-type column: '{broad_col}' ({adata.obs[broad_col].nunique()} classes)")
print(f"  Fine-grained column: '{fine_col}' ({adata.obs[fine_col].nunique()} classes)")

# Show distributions
print(f"\n  Broad-type distribution:")
for ct, n in adata.obs[broad_col].value_counts().items():
    print(f"    {ct}: {n}")

print(f"\n  Fine-grained top 20:")
for ct, n in adata.obs[fine_col].value_counts().head(20).items():
    print(f"    {ct}: {n}")

# Store as standard column names
adata.obs['broad_type'] = adata.obs[broad_col].astype(str)
adata.obs['primary_type'] = adata.obs[fine_col].astype(str)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4: PREPROCESSING (identical to Tasic 2016 pipeline)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 4: PREPROCESSING")
print("=" * 80)

# Drop low-quality / unclassified cells
# Filter out any cells with class labels that indicate low quality
exclude_patterns = ['Unclassified', 'Low Quality', 'Exclude', 'No Class',
                    'Noise', 'Doublet', 'no class', 'nan',
                    'ERCC', 'NTC', 'MouseWholeRNA', 'ControlTotalRNA']
mask = ~adata.obs['broad_type'].isin(exclude_patterns)
# Also exclude NaN
mask = mask & adata.obs['broad_type'].notna() & (adata.obs['broad_type'] != 'nan')
n_before = adata.n_obs
adata = adata[mask].copy()
print(f"  Dropped unclassified/low-quality: {n_before} -> {adata.n_obs}")

# QC: genes per cell, mitochondrial content
print("  Running QC...")
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
print(f"  After QC: {adata.n_obs} cells x {adata.n_vars} genes")

# Normalize
print("  Normalizing...")
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)

# HVG selection
print(f"  Selecting top {N_TOP_GENES} HVGs...")
sc.pp.highly_variable_genes(adata, n_top_genes=N_TOP_GENES, subset=False, flavor="seurat")
adata_hvg = adata[:, adata.var["highly_variable"]].copy()
print(f"  HVG matrix: {adata_hvg.shape}")

# Modality 1: HVG expression
X_expr = adata_hvg.X.toarray().astype(np.float32) if sparse.issparse(adata_hvg.X) else adata_hvg.X.astype(np.float32)
gene_names = list(adata_hvg.var_names.astype(str))

# Modality 2: PCA of full expression
print(f"  Computing PCA ({N_PCA_COMPONENTS} components) from full expression...")
X_full = adata.X.toarray().astype(np.float32) if sparse.issparse(adata.X) else adata.X.astype(np.float32)
pca = PCA(n_components=N_PCA_COMPONENTS, random_state=SEED)
X_morph = pca.fit_transform(X_full).astype(np.float32)
pca_var = pca.explained_variance_ratio_.sum()
print(f"  PCA variance explained ({N_PCA_COMPONENTS} PCs): {pca_var:.4f}")

print(f"\n  Modality 1: {X_expr.shape}, Modality 2: {X_morph.shape}")
print(f"  Total cells: {adata_hvg.n_obs}")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 5: BROAD-TYPE EXPERIMENT
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 5: BROAD-TYPE CLASSIFICATION")
print("=" * 80)

# Encode broad-type labels
broad_labels = adata_hvg.obs['broad_type'].astype('category')
broad_labels = broad_labels.cat.remove_unused_categories()
broad_codes = broad_labels.cat.codes.values.astype(np.int64)
broad_names = list(broad_labels.cat.categories.astype(str))
n_broad = len(broad_names)
print(f"  Classes: {n_broad} broad types")
for i, name in enumerate(broad_names):
    print(f"    {name}: {(broad_codes == i).sum()}")

# Stratified splits
idx = np.arange(len(broad_codes))
train_idx, test_idx = train_test_split(idx, test_size=0.20, random_state=SEED, stratify=broad_codes)
train_idx, val_idx = train_test_split(train_idx, test_size=0.20, random_state=SEED, stratify=broad_codes[train_idx])
print(f"  Splits: train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}")

# Class weights
y_tr_broad = broad_codes[train_idx]
tc = np.bincount(y_tr_broad, minlength=n_broad).astype(np.float32)
tc = np.maximum(tc, 1.0)
cw_broad = len(y_tr_broad) / (n_broad * tc)
cw_broad = cw_broad / cw_broad.sum() * n_broad

broad_results, broad_preds, broad_attn, broad_attn_preds, broad_concat_preds = run_all_models(
    X_expr, X_morph, broad_codes, broad_names, cw_broad,
    train_idx, val_idx, test_idx, tag="broad"
)

# Per-class attention
broad_attn_df = compute_per_class_attention(
    broad_attn, broad_codes[test_idx], broad_names, test_idx)

# Save
broad_metrics_df = pd.DataFrame(broad_results)
broad_metrics_df.to_csv(os.path.join(EXPERIMENTS_DIR, "tasic2018_broadtype_metrics.csv"), index=False)
broad_attn_df.to_csv(os.path.join(EXPERIMENTS_DIR, "tasic2018_attn_broadtype.csv"), index=False)
print(f"\n  Saved broad-type metrics and attention weights")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 6: FINE-GRAINED EXPERIMENT
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 6: FINE-GRAINED CLASSIFICATION")
print("=" * 80)

# Filter out noise cluster labels and types with <MIN_CELLS_PER_TYPE
noise_clusters = ['Low Quality', 'No Class', 'nan', 'Exclude']
clean_mask = ~adata_hvg.obs['primary_type'].isin(noise_clusters)
fine_counts = adata_hvg.obs.loc[clean_mask, 'primary_type'].value_counts()
types_keep = fine_counts[fine_counts >= MIN_CELLS_PER_TYPE].index.tolist()
types_drop = fine_counts[fine_counts < MIN_CELLS_PER_TYPE].index.tolist()
print(f"  Types kept: {len(types_keep)}, dropped: {len(types_drop)} (< {MIN_CELLS_PER_TYPE} cells)")

keep_mask = (adata_hvg.obs['primary_type'].isin(types_keep) & clean_mask).values
X_expr_fg = X_expr[keep_mask]
X_morph_fg = X_morph[keep_mask]

fine_labels = adata_hvg.obs.loc[keep_mask, 'primary_type'].astype('category')
fine_labels = fine_labels.cat.remove_unused_categories()
fine_codes = fine_labels.cat.codes.values.astype(np.int64)
fine_names = list(fine_labels.cat.categories.astype(str))
n_fine = len(fine_names)
print(f"  Classes: {n_fine} fine-grained types, {len(fine_codes)} cells")

# Stratified splits
idx_fg = np.arange(len(fine_codes))
try:
    train_fg, test_fg = train_test_split(idx_fg, test_size=0.20, random_state=SEED, stratify=fine_codes)
    train_fg, val_fg = train_test_split(train_fg, test_size=0.20, random_state=SEED, stratify=fine_codes[train_fg])
except ValueError:
    print("  WARNING: Stratified split failed for some classes, using non-stratified fallback")
    train_fg, test_fg = train_test_split(idx_fg, test_size=0.20, random_state=SEED)
    train_fg, val_fg = train_test_split(train_fg, test_size=0.20, random_state=SEED)
print(f"  Splits: train={len(train_fg)}, val={len(val_fg)}, test={len(test_fg)}")

# Class weights
y_tr_fg = fine_codes[train_fg]
tc_fg = np.bincount(y_tr_fg, minlength=n_fine).astype(np.float32)
tc_fg = np.maximum(tc_fg, 1.0)
cw_fg = len(y_tr_fg) / (n_fine * tc_fg)
cw_fg = cw_fg / cw_fg.sum() * n_fine

fine_results, fine_preds, fine_attn, fine_attn_preds, fine_concat_preds = run_all_models(
    X_expr_fg, X_morph_fg, fine_codes, fine_names, cw_fg,
    train_fg, val_fg, test_fg, tag="fine"
)

# Per-class attention
fine_attn_df = compute_per_class_attention(
    fine_attn, fine_codes[test_fg], fine_names, test_fg)

# Save
fine_metrics_df = pd.DataFrame(fine_results)
fine_metrics_df.to_csv(os.path.join(EXPERIMENTS_DIR, "tasic2018_finegrained_metrics.csv"), index=False)
fine_attn_df.to_csv(os.path.join(EXPERIMENTS_DIR, "tasic2018_attn_finegrained.csv"), index=False)
print(f"\n  Saved fine-grained metrics and attention weights")


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 7: McNEMAR'S TEST
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 7: McNEMAR'S TEST")
print("=" * 80)

y_te_fg = fine_codes[test_fg]
attn_correct = (fine_attn_preds == y_te_fg)
concat_correct = (fine_concat_preds == y_te_fg)

b = int(np.sum(attn_correct & ~concat_correct))
c = int(np.sum(~attn_correct & concat_correct))
if (b + c) > 0:
    chi2_val = (abs(b - c) - 1) ** 2 / (b + c)
    from scipy.stats import chi2 as chi2_dist
    p_val = float(1 - chi2_dist.cdf(chi2_val, df=1))
else:
    chi2_val, p_val = 0.0, 1.0

mcnemar = {
    "attn_correct_concat_wrong": b,
    "attn_wrong_concat_correct": c,
    "chi2_continuity_corrected": round(chi2_val, 4),
    "p_value": round(p_val, 6),
    "significant_005": p_val < 0.05,
    "attn_acc": float(accuracy_score(y_te_fg, fine_attn_preds)),
    "concat_acc": float(accuracy_score(y_te_fg, fine_concat_preds)),
}
print(f"  b (attn right, concat wrong): {b}")
print(f"  c (attn wrong, concat right): {c}")
print(f"  χ² = {chi2_val:.4f}, p = {p_val:.6f}")
print(f"  Significant: {p_val < 0.05}")

with open(os.path.join(EXPERIMENTS_DIR, "tasic2018_mcnemar.json"), "w") as f:
    json.dump(mcnemar, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 8: MUTUAL INFORMATION
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 8: MUTUAL INFORMATION")
print("=" * 80)

# Use fine-grained training data (subsample if too large for MI computation)
mi_n = min(5000, len(train_fg))  # cap at 5K for speed
mi_idx = np.random.choice(train_fg, mi_n, replace=False)

print(f"  Computing MI on {mi_n} training samples...")
mi_hvg = mutual_info_classif(X_expr_fg[mi_idx], fine_codes[mi_idx], random_state=SEED)
mi_pca = mutual_info_classif(X_morph_fg[mi_idx], fine_codes[mi_idx], random_state=SEED)

# Pairwise MI between first 60 HVG features and 60 PCA components
n_bins_mi = 10
sub_hvg = X_expr_fg[mi_idx, :60]
sub_pca = X_morph_fg[mi_idx]
hvg_binned = np.digitize(sub_hvg, bins=np.linspace(sub_hvg.min(), sub_hvg.max(), n_bins_mi))
pca_binned = np.digitize(sub_pca, bins=np.linspace(sub_pca.min(), sub_pca.max(), n_bins_mi))
pairwise = [mutual_info_score(hvg_binned[:, i], pca_binned[:, j])
            for i in range(60) for j in range(60)]

mi_results = {
    "hvg_to_label_mean": round(float(mi_hvg.mean()), 4),
    "hvg_to_label_max": round(float(mi_hvg.max()), 4),
    "pca_to_label_mean": round(float(mi_pca.mean()), 4),
    "pca_to_label_max": round(float(mi_pca.max()), 4),
    "pairwise_hvg_pca_mean": round(float(np.mean(pairwise)), 4),
    "pairwise_hvg_pca_max": round(float(np.max(pairwise)), 4),
    "pca_total_variance_explained": round(float(pca_var), 4),
    "n_samples_used": mi_n,
}
print(f"  MI(HVG→label): mean={mi_results['hvg_to_label_mean']}, max={mi_results['hvg_to_label_max']}")
print(f"  MI(PCA→label): mean={mi_results['pca_to_label_mean']}, max={mi_results['pca_to_label_max']}")
print(f"  Pairwise MI(HVG,PCA): mean={mi_results['pairwise_hvg_pca_mean']}, max={mi_results['pairwise_hvg_pca_max']}")

with open(os.path.join(EXPERIMENTS_DIR, "tasic2018_mutual_information.json"), "w") as f:
    json.dump(mi_results, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 9: SUMMARY JSON
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("STEP 9: SUMMARY")
print("=" * 80)

summary = {
    "dataset": {
        "source": "Tasic et al. 2018, GEO GSE115746",
        "total_cells_raw": int(adata.n_obs),
        "total_cells_after_qc": int(adata_hvg.n_obs),
        "total_genes_after_qc": int(adata.n_vars),
        "hvg_count": int(X_expr.shape[1]),
        "pca_components": N_PCA_COMPONENTS,
        "pca_variance_explained": round(float(pca_var), 4),
    },
    "broad_type": {
        "n_classes": n_broad,
        "class_names": broad_names,
        "results": {r["model"]: {k: v for k, v in r.items() if k != "model"}
                    for r in broad_results},
    },
    "fine_grained": {
        "n_classes": n_fine,
        "n_cells": int(len(fine_codes)),
        "train_val_test": [int(len(train_fg)), int(len(val_fg)), int(len(test_fg))],
        "results": {r["model"]: {k: v for k, v in r.items() if k != "model"}
                    for r in fine_results},
    },
    "mcnemar": mcnemar,
    "mutual_information": mi_results,
}

with open(os.path.join(EXPERIMENTS_DIR, "tasic2018_summary.json"), "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(f"\n  === BROAD-TYPE RESULTS ===")
for r in broad_results:
    print(f"  {r['model']:25s}  Acc={r['accuracy']:.4f}  F1={r['f1_weighted']:.4f}")

print(f"\n  === FINE-GRAINED RESULTS ===")
for r in fine_results:
    print(f"  {r['model']:25s}  Acc={r['accuracy']:.4f}  F1={r['f1_weighted']:.4f}")

print(f"\n  McNemar's: χ²={mcnemar['chi2_continuity_corrected']}, p={mcnemar['p_value']}")
print(f"  MI(HVG→label)={mi_results['hvg_to_label_mean']}, MI(PCA→label)={mi_results['pca_to_label_mean']}")

print(f"\n  All outputs saved to: {EXPERIMENTS_DIR}/")
print("DONE.")
