#!/usr/bin/env python3
"""
03_fusion_model.py — Cross-Attention Fusion Model + Naive Concat Ablation

Defines and trains:
  1. CrossAttentionFusion: encodes each modality, computes attention-weighted fusion,
     stores modality attention weights for built-in explainability.
  2. NaiveConcatFusion: simple concatenation baseline (no attention mechanism).

Evaluates both with AUROC, F1, accuracy, ECE, and bootstrap 95% CIs.

Run from project root:
    python notebooks/03_fusion_model.py
"""

import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.preprocessing import label_binarize

warnings.filterwarnings("ignore", category=UserWarning)

# ─── Configuration ───────────────────────────────────────────────────────────
SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "artifacts")

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Device: {DEVICE}")

BATCH_SIZE = 128
N_EPOCHS = 80
LR = 5e-4
PATIENCE = 15
N_BOOTSTRAP = 1000
EMBED_DIM = 128

# ─── Load Data ───────────────────────────────────────────────────────────────
print("=" * 70)
print("Loading preprocessed data")
print("=" * 70)

X_expr = np.load(os.path.join(ARTIFACTS_DIR, "modality1_gene_expr.npy"))
X_morph = np.load(os.path.join(ARTIFACTS_DIR, "modality2_gene_modules.npy"))
labels = np.load(os.path.join(ARTIFACTS_DIR, "labels.npy"))

with open(os.path.join(ARTIFACTS_DIR, "splits.json")) as f:
    splits = json.load(f)

train_idx = np.array(splits["train_idx"])
val_idx = np.array(splits["val_idx"])
test_idx = np.array(splits["test_idx"])
n_classes = splits["n_classes"]
class_names = splits["class_names"]

gene_dim = X_expr.shape[1]
morph_dim = X_morph.shape[1]

print(f"  Gene expression dim: {gene_dim}")
print(f"  Gene module dim: {morph_dim}")
print(f"  Classes: {n_classes} — {class_names}")

# Split
X_expr_train, X_expr_val, X_expr_test = X_expr[train_idx], X_expr[val_idx], X_expr[test_idx]
X_morph_train, X_morph_val, X_morph_test = X_morph[train_idx], X_morph[val_idx], X_morph[test_idx]
y_train, y_val, y_test = labels[train_idx], labels[val_idx], labels[test_idx]


# ─── Metrics (same as 02_baseline.py) ────────────────────────────────────────
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


# ─── Model Definitions ──────────────────────────────────────────────────────

class GenomicEncoder(nn.Module):
    """Encodes gene expression features into a fixed-dim embedding."""
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
    """Encodes gene module PCA features into a fixed-dim embedding."""
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
    """
    Computes attention-weighted fusion of two modality embeddings.

    Given embeddings z_g (genomic) and z_m (morphological), both of shape (B, D):
      1. Stack them: Z = [z_g, z_m] of shape (B, 2, D)
      2. Compute attention logits via a learned projection: a = Z @ w of shape (B, 2)
      3. Softmax over the modality dimension to get weights alpha in [0,1]
      4. Fused = alpha_g * z_g + alpha_m * z_m

    The attention weights alpha are stored as self.last_attention_weights
    for downstream explainability analysis.
    """
    def __init__(self, embed_dim=EMBED_DIM):
        super().__init__()
        # Attention mechanism: project each modality embedding to a scalar score
        self.attention_proj = nn.Sequential(
            nn.Linear(embed_dim, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
        )
        # Stores the most recent batch's attention weights for inspection
        self.last_attention_weights = None

    def forward(self, z_genomic, z_morph):
        # z_genomic, z_morph: (B, D)
        # Stack into (B, 2, D)
        stacked = torch.stack([z_genomic, z_morph], dim=1)  # (B, 2, D)

        # Compute attention logits for each modality
        attn_logits = self.attention_proj(stacked).squeeze(-1)  # (B, 2)

        # Softmax over modalities
        attn_weights = F.softmax(attn_logits, dim=1)  # (B, 2)

        # Store for explainability — detach to avoid graph retention
        self.last_attention_weights = attn_weights.detach()

        # Weighted sum
        fused = attn_weights[:, 0:1] * z_genomic + attn_weights[:, 1:2] * z_morph  # (B, D)
        return fused


class CrossAttentionFusionModel(nn.Module):
    """
    Full fusion model:
      GenomicEncoder -> z_g
      MorphEncoder   -> z_m
      CrossAttentionGate(z_g, z_m) -> z_fused
      Classifier(z_fused) -> logits
    """
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
        """Retrieve the attention weights from the last forward pass."""
        return self.attention_gate.last_attention_weights

    def get_embeddings(self, x_gene, x_morph):
        """Get per-modality embeddings (useful for analysis)."""
        z_g = self.genomic_encoder(x_gene)
        z_m = self.morph_encoder(x_morph)
        return z_g, z_m


class NaiveConcatFusionModel(nn.Module):
    """
    Ablation baseline: concatenate both modality features, no attention.
    Encodes each modality, concatenates, then classifies.
    """
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


# ─── Training Loop ───────────────────────────────────────────────────────────

def make_bimodal_loaders(X_expr_tr, X_morph_tr, y_tr,
                         X_expr_vl, X_morph_vl, y_vl,
                         X_expr_te, X_morph_te, y_te,
                         batch_size=BATCH_SIZE):
    def _make(xe, xm, y, shuffle):
        ds = TensorDataset(
            torch.tensor(xe, dtype=torch.float32),
            torch.tensor(xm, dtype=torch.float32),
            torch.tensor(y, dtype=torch.long),
        )
        return DataLoader(ds, batch_size=batch_size, shuffle=shuffle)
    return (_make(X_expr_tr, X_morph_tr, y_tr, True),
            _make(X_expr_vl, X_morph_vl, y_vl, False),
            _make(X_expr_te, X_morph_te, y_te, False))


def train_fusion(model, train_loader, val_loader, n_epochs=N_EPOCHS, lr=LR, patience=PATIENCE):
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5
    )
    criterion = nn.CrossEntropyLoss()

    best_val_loss = float("inf")
    best_state = None
    epochs_no_improve = 0

    for epoch in range(n_epochs):
        model.train()
        train_loss = 0.0
        n_batches = 0
        for xg, xm, yb in train_loader:
            xg, xm, yb = xg.to(DEVICE), xm.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            logits = model(xg, xm)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            n_batches += 1

        model.eval()
        val_loss = 0.0
        val_batches = 0
        with torch.no_grad():
            for xg, xm, yb in val_loader:
                xg, xm, yb = xg.to(DEVICE), xm.to(DEVICE), yb.to(DEVICE)
                loss = criterion(model(xg, xm), yb)
                val_loss += loss.item()
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

        if (epoch + 1) % 10 == 0 or epoch == 0:
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
    all_preds = []
    all_probs = []
    all_attn = []  # only for CrossAttentionFusionModel

    with torch.no_grad():
        for xg, xm, _ in data_loader:
            xg, xm = xg.to(DEVICE), xm.to(DEVICE)
            logits = model(xg, xm)
            probs = torch.softmax(logits, dim=1)
            all_preds.extend(logits.argmax(1).cpu().numpy())
            all_probs.append(probs.cpu().numpy())

            # Capture attention weights if available
            if hasattr(model, "get_attention_weights"):
                attn = model.get_attention_weights()
                if attn is not None:
                    all_attn.append(attn.cpu().numpy())

    preds = np.array(all_preds)
    probs = np.vstack(all_probs)
    attn = np.vstack(all_attn) if all_attn else None
    return preds, probs, attn


# ─── Create Loaders ──────────────────────────────────────────────────────────
train_loader, val_loader, test_loader = make_bimodal_loaders(
    X_expr_train, X_morph_train, y_train,
    X_expr_val, X_morph_val, y_val,
    X_expr_test, X_morph_test, y_test,
)

# ─── Train CrossAttentionFusion ──────────────────────────────────────────────
print("\n" + "=" * 70)
print("MODEL 1: CrossAttentionFusion")
print("=" * 70)

fusion_model = CrossAttentionFusionModel(gene_dim, morph_dim, n_classes).to(DEVICE)
n_params = sum(p.numel() for p in fusion_model.parameters())
print(f"  Parameters: {n_params:,}")
print(f"  Architecture: GenomicEncoder({gene_dim}->256->128) + "
      f"MorphEncoder({morph_dim}->128->128) + CrossAttentionGate + Linear({EMBED_DIM}->{n_classes})")

fusion_model = train_fusion(fusion_model, train_loader, val_loader)
fusion_pred, fusion_prob, fusion_attn = predict_fusion(fusion_model, test_loader)

fusion_metrics = evaluate_predictions(y_test, fusion_pred, fusion_prob)
fusion_ci = bootstrap_metrics(y_test, fusion_pred, fusion_prob)
fusion_metrics.update(fusion_ci)
fusion_metrics["model"] = "CrossAttentionFusion"

print(f"\n  Results:")
print(f"  Accuracy:    {fusion_metrics['accuracy']:.4f} "
      f"[{fusion_metrics['accuracy_ci_lo']:.4f}, {fusion_metrics['accuracy_ci_hi']:.4f}]")
print(f"  F1 weighted: {fusion_metrics['f1_weighted']:.4f} "
      f"[{fusion_metrics['f1_weighted_ci_lo']:.4f}, {fusion_metrics['f1_weighted_ci_hi']:.4f}]")
print(f"  AUROC macro: {fusion_metrics['auroc_macro']:.4f} "
      f"[{fusion_metrics['auroc_macro_ci_lo']:.4f}, {fusion_metrics['auroc_macro_ci_hi']:.4f}]")
print(f"  ECE:         {fusion_metrics['ece']:.4f} "
      f"[{fusion_metrics['ece_ci_lo']:.4f}, {fusion_metrics['ece_ci_hi']:.4f}]")

# Attention weight analysis
if fusion_attn is not None:
    print(f"\n  Attention weight analysis (test set):")
    print(f"    Genomic modality: mean={fusion_attn[:, 0].mean():.4f}, "
          f"std={fusion_attn[:, 0].std():.4f}")
    print(f"    Morphological modality: mean={fusion_attn[:, 1].mean():.4f}, "
          f"std={fusion_attn[:, 1].std():.4f}")

    # Per-class attention weights
    print(f"\n  Per-class attention weights:")
    for c_idx, c_name in enumerate(class_names):
        mask = y_test == c_idx
        if mask.sum() > 0:
            print(f"    {c_name}: genomic={fusion_attn[mask, 0].mean():.4f}, "
                  f"morphological={fusion_attn[mask, 1].mean():.4f}")

    # Save attention weights
    np.save(os.path.join(ARTIFACTS_DIR, "fusion_attention_weights.npy"), fusion_attn)
    print(f"  Saved: artifacts/fusion_attention_weights.npy")

# Save fusion model
torch.save(fusion_model.state_dict(), os.path.join(ARTIFACTS_DIR, "fusion_model.pt"))
# Also save model config for reloading
fusion_config = {
    "gene_dim": gene_dim,
    "morph_dim": morph_dim,
    "n_classes": n_classes,
    "embed_dim": EMBED_DIM,
}
with open(os.path.join(ARTIFACTS_DIR, "fusion_model_config.json"), "w") as f:
    json.dump(fusion_config, f, indent=2)
print(f"  Saved: artifacts/fusion_model.pt, artifacts/fusion_model_config.json")


# ─── Train NaiveConcatFusion ────────────────────────────────────────────────
print("\n" + "=" * 70)
print("MODEL 2: NaiveConcatFusion (ablation baseline)")
print("=" * 70)

concat_model = NaiveConcatFusionModel(gene_dim, morph_dim, n_classes).to(DEVICE)
n_params_concat = sum(p.numel() for p in concat_model.parameters())
print(f"  Parameters: {n_params_concat:,}")

concat_model = train_fusion(concat_model, train_loader, val_loader)
concat_pred, concat_prob, _ = predict_fusion(concat_model, test_loader)

concat_metrics = evaluate_predictions(y_test, concat_pred, concat_prob)
concat_ci = bootstrap_metrics(y_test, concat_pred, concat_prob)
concat_metrics.update(concat_ci)
concat_metrics["model"] = "NaiveConcatFusion"

print(f"\n  Results:")
print(f"  Accuracy:    {concat_metrics['accuracy']:.4f} "
      f"[{concat_metrics['accuracy_ci_lo']:.4f}, {concat_metrics['accuracy_ci_hi']:.4f}]")
print(f"  F1 weighted: {concat_metrics['f1_weighted']:.4f} "
      f"[{concat_metrics['f1_weighted_ci_lo']:.4f}, {concat_metrics['f1_weighted_ci_hi']:.4f}]")
print(f"  AUROC macro: {concat_metrics['auroc_macro']:.4f} "
      f"[{concat_metrics['auroc_macro_ci_lo']:.4f}, {concat_metrics['auroc_macro_ci_hi']:.4f}]")
print(f"  ECE:         {concat_metrics['ece']:.4f} "
      f"[{concat_metrics['ece_ci_lo']:.4f}, {concat_metrics['ece_ci_hi']:.4f}]")

# Save naive concat model
torch.save(concat_model.state_dict(), os.path.join(ARTIFACTS_DIR, "naive_concat_model.pt"))
concat_config = {
    "gene_dim": gene_dim,
    "morph_dim": morph_dim,
    "n_classes": n_classes,
    "embed_dim": EMBED_DIM,
}
with open(os.path.join(ARTIFACTS_DIR, "naive_concat_config.json"), "w") as f:
    json.dump(concat_config, f, indent=2)
print(f"  Saved: artifacts/naive_concat_model.pt")


# ─── Save All Fusion Metrics ────────────────────────────────────────────────
print("\n" + "=" * 70)
print("Saving fusion metrics")
print("=" * 70)

fusion_df = pd.DataFrame([fusion_metrics, concat_metrics])
fusion_path = os.path.join(ARTIFACTS_DIR, "fusion_metrics.csv")
fusion_df.to_csv(fusion_path, index=False)
print(f"  Saved: {fusion_path}")

# Also load baseline metrics and create combined table
baseline_path = os.path.join(ARTIFACTS_DIR, "baseline_metrics.csv")
if os.path.exists(baseline_path):
    baseline_df = pd.read_csv(baseline_path)
    combined = pd.concat([baseline_df, fusion_df], ignore_index=True)
else:
    combined = fusion_df

combined_path = os.path.join(ARTIFACTS_DIR, "all_metrics.csv")
combined.to_csv(combined_path, index=False)
print(f"  Saved: {combined_path}")

# Print combined summary
print("\n  Combined comparison:")
print("  " + "-" * 68)
print(f"  {'Model':<25} {'Accuracy':>10} {'F1 (wt)':>10} {'AUROC':>10} {'ECE':>10}")
print("  " + "-" * 68)
for _, row in combined.iterrows():
    print(f"  {row['model']:<25} {row['accuracy']:>10.4f} {row['f1_weighted']:>10.4f} "
          f"{row['auroc_macro']:>10.4f} {row['ece']:>10.4f}")
print("  " + "-" * 68)

print("\nFUSION MODEL TRAINING COMPLETE")
