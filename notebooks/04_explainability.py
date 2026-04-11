#!/usr/bin/env python3
"""
04_explainability.py — Explainability Analysis

Runs three explainability methods and compares modality-level attribution:
  (a) Built-in attention weights from CrossAttentionFusion
  (b) Captum IntegratedGradients on the fusion model (per-feature, per-modality)
  (c) SHAP (KernelExplainer) on the NaiveConcatFusion model

Also validates whether top-attributed genes match known cell-type markers.

Run from project root:
    python notebooks/04_explainability.py
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
from captum.attr import IntegratedGradients
import shap
from sklearn.preprocessing import label_binarize

warnings.filterwarnings("ignore")

# ─── Configuration ───────────────────────────────────────────────────────────
SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "artifacts")
FIGURES_DIR = os.path.join(ARTIFACTS_DIR, "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
# Captum and SHAP work best on CPU for stability; MPS can cause issues
# with gradient computations in Captum
EXPLAIN_DEVICE = "cpu"
print(f"Training device: {DEVICE}, Explainability device: {EXPLAIN_DEVICE}")

N_SHAP_SAMPLES = 150  # number of test samples for SHAP (expensive)
N_SHAP_BACKGROUND = 100  # background samples for KernelExplainer
TOP_K_FEATURES = 20  # top features to analyze

# ─── Load Data ───────────────────────────────────────────────────────────────
print("=" * 70)
print("Loading data and models")
print("=" * 70)

X_expr = np.load(os.path.join(ARTIFACTS_DIR, "modality1_gene_expr.npy"))
X_morph = np.load(os.path.join(ARTIFACTS_DIR, "modality2_gene_modules.npy"))
labels = np.load(os.path.join(ARTIFACTS_DIR, "labels.npy"))

with open(os.path.join(ARTIFACTS_DIR, "splits.json")) as f:
    splits = json.load(f)
with open(os.path.join(ARTIFACTS_DIR, "gene_names.json")) as f:
    gene_names = json.load(f)

test_idx = np.array(splits["test_idx"])
train_idx = np.array(splits["train_idx"])
n_classes = splits["n_classes"]
class_names = splits["class_names"]

X_expr_test = X_expr[test_idx]
X_morph_test = X_morph[test_idx]
y_test = labels[test_idx]
X_expr_train = X_expr[train_idx]
X_morph_train = X_morph[train_idx]

gene_dim = X_expr.shape[1]
morph_dim = X_morph.shape[1]

# Load marker genes if available
marker_genes = None
marker_path = os.path.join(ARTIFACTS_DIR, "marker_genes.json")
if os.path.exists(marker_path):
    with open(marker_path) as f:
        marker_genes = json.load(f)
    print(f"  Loaded marker genes for {len(marker_genes)} cell types")

print(f"  Test set: {len(test_idx)} samples")
print(f"  Gene features: {gene_dim}, Module features: {morph_dim}")


# ─── Recreate Model Classes ─────────────────────────────────────────────────
# (Same architecture definitions as 03_fusion_model.py)

EMBED_DIM = 128

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


# ─── Load Trained Models ────────────────────────────────────────────────────
print("\nLoading trained models...")

with open(os.path.join(ARTIFACTS_DIR, "fusion_model_config.json")) as f:
    fconfig = json.load(f)

fusion_model = CrossAttentionFusionModel(
    fconfig["gene_dim"], fconfig["morph_dim"], fconfig["n_classes"], fconfig["embed_dim"]
)
fusion_model.load_state_dict(
    torch.load(os.path.join(ARTIFACTS_DIR, "fusion_model.pt"), map_location=EXPLAIN_DEVICE, weights_only=True)
)
fusion_model.to(EXPLAIN_DEVICE)
fusion_model.eval()
print(f"  Loaded CrossAttentionFusion model")

with open(os.path.join(ARTIFACTS_DIR, "naive_concat_config.json")) as f:
    cconfig = json.load(f)

concat_model = NaiveConcatFusionModel(
    cconfig["gene_dim"], cconfig["morph_dim"], cconfig["n_classes"], cconfig["embed_dim"]
)
concat_model.load_state_dict(
    torch.load(os.path.join(ARTIFACTS_DIR, "naive_concat_model.pt"), map_location=EXPLAIN_DEVICE, weights_only=True)
)
concat_model.to(EXPLAIN_DEVICE)
concat_model.eval()
print(f"  Loaded NaiveConcatFusion model")


# ─── Method (a): Attention Weights ──────────────────────────────────────────
print("\n" + "=" * 70)
print("METHOD (a): Built-in attention weights from CrossAttentionFusion")
print("=" * 70)

# Run forward pass on test set to collect attention weights
with torch.no_grad():
    x_gene_t = torch.tensor(X_expr_test, dtype=torch.float32).to(EXPLAIN_DEVICE)
    x_morph_t = torch.tensor(X_morph_test, dtype=torch.float32).to(EXPLAIN_DEVICE)
    _ = fusion_model(x_gene_t, x_morph_t)
    attn_weights = fusion_model.get_attention_weights().cpu().numpy()

print(f"  Attention weights shape: {attn_weights.shape}")
print(f"  Genomic modality: mean={attn_weights[:, 0].mean():.4f}, std={attn_weights[:, 0].std():.4f}")
print(f"  Module modality:  mean={attn_weights[:, 1].mean():.4f}, std={attn_weights[:, 1].std():.4f}")

# Per-class attention
attn_per_class = {}
for c_idx, c_name in enumerate(class_names):
    mask = y_test == c_idx
    if mask.sum() > 0:
        attn_per_class[c_name] = {
            "genomic_mean": float(attn_weights[mask, 0].mean()),
            "genomic_std": float(attn_weights[mask, 0].std()),
            "module_mean": float(attn_weights[mask, 1].mean()),
            "module_std": float(attn_weights[mask, 1].std()),
            "n_samples": int(mask.sum()),
        }
        print(f"  {c_name}: genomic={attn_per_class[c_name]['genomic_mean']:.4f} "
              f"({attn_per_class[c_name]['genomic_std']:.4f}), "
              f"module={attn_per_class[c_name]['module_mean']:.4f} "
              f"({attn_per_class[c_name]['module_std']:.4f})")


# ─── Method (b): Captum Integrated Gradients ────────────────────────────────
print("\n" + "=" * 70)
print("METHOD (b): Captum IntegratedGradients on CrossAttentionFusion")
print("=" * 70)

# Wrapper that takes a single concatenated input and splits into two modalities
# (Captum expects a single input tensor for IntegratedGradients)
class FusionWrapper(nn.Module):
    """Wraps the fusion model to accept a single concatenated input."""
    def __init__(self, model, gene_dim, morph_dim):
        super().__init__()
        self.model = model
        self.gene_dim = gene_dim
        self.morph_dim = morph_dim

    def forward(self, x_combined):
        x_gene = x_combined[:, :self.gene_dim]
        x_morph = x_combined[:, self.gene_dim:]
        return self.model(x_gene, x_morph)

wrapper = FusionWrapper(fusion_model, gene_dim, morph_dim).to(EXPLAIN_DEVICE)
wrapper.eval()

ig = IntegratedGradients(wrapper)

# Compute IG for all test samples, class by class
print(f"  Computing Integrated Gradients for {len(y_test)} test samples...")
print(f"  (This takes a while — IG requires multiple forward passes per sample)")

# Create combined input
X_combined_test = np.hstack([X_expr_test, X_morph_test]).astype(np.float32)
baseline = np.zeros_like(X_combined_test[0:1])  # zero baseline
baseline_t = torch.tensor(baseline, dtype=torch.float32).to(EXPLAIN_DEVICE)

# Process in batches to manage memory
ig_attributions = np.zeros_like(X_combined_test)
batch_size = 32

for start in range(0, len(X_combined_test), batch_size):
    end = min(start + batch_size, len(X_combined_test))
    batch_input = torch.tensor(X_combined_test[start:end], dtype=torch.float32).to(EXPLAIN_DEVICE)
    batch_input.requires_grad_(True)
    batch_targets = torch.tensor(y_test[start:end], dtype=torch.long).to(EXPLAIN_DEVICE)

    # Expand baseline to batch size
    batch_baseline = baseline_t.expand(end - start, -1)

    attr = ig.attribute(
        batch_input,
        baselines=batch_baseline,
        target=batch_targets,
        n_steps=50,
        internal_batch_size=32,
    )
    ig_attributions[start:end] = attr.detach().cpu().numpy()

    if (start // batch_size) % 5 == 0:
        print(f"    Processed {end}/{len(X_combined_test)} samples")

print(f"  IG attributions shape: {ig_attributions.shape}")

# Split IG attributions back into modalities
ig_gene = ig_attributions[:, :gene_dim]  # per-gene attributions
ig_morph = ig_attributions[:, gene_dim:]  # per-module-PC attributions

# Modality-level attribution from IG: sum of absolute attributions per modality
ig_gene_importance = np.abs(ig_gene).sum(axis=1)  # (n_test,)
ig_morph_importance = np.abs(ig_morph).sum(axis=1)  # (n_test,)
ig_total = ig_gene_importance + ig_morph_importance + 1e-10  # avoid division by zero

ig_gene_frac = ig_gene_importance / ig_total
ig_morph_frac = ig_morph_importance / ig_total

print(f"  IG modality attribution:")
print(f"    Genomic: mean={ig_gene_frac.mean():.4f}, std={ig_gene_frac.std():.4f}")
print(f"    Module:  mean={ig_morph_frac.mean():.4f}, std={ig_morph_frac.std():.4f}")

# Per-class IG modality attribution
ig_per_class = {}
for c_idx, c_name in enumerate(class_names):
    mask = y_test == c_idx
    if mask.sum() > 0:
        ig_per_class[c_name] = {
            "genomic_frac": float(ig_gene_frac[mask].mean()),
            "module_frac": float(ig_morph_frac[mask].mean()),
        }
        print(f"    {c_name}: genomic={ig_per_class[c_name]['genomic_frac']:.4f}, "
              f"module={ig_per_class[c_name]['module_frac']:.4f}")

# Top attributed genes per class
print(f"\n  Top {TOP_K_FEATURES} attributed genes per class (by IG):")
ig_top_genes_per_class = {}
for c_idx, c_name in enumerate(class_names):
    mask = y_test == c_idx
    if mask.sum() == 0:
        continue
    # Mean absolute IG attribution across samples of this class
    mean_ig = np.abs(ig_gene[mask]).mean(axis=0)
    top_indices = np.argsort(mean_ig)[::-1][:TOP_K_FEATURES]
    top_genes = [gene_names[i] for i in top_indices]
    top_values = mean_ig[top_indices]
    ig_top_genes_per_class[c_name] = {
        "genes": top_genes,
        "attributions": top_values.tolist(),
    }
    print(f"    {c_name}: {', '.join(top_genes[:5])} ...")


# ─── Method (c): SHAP on NaiveConcatFusion ──────────────────────────────────
print("\n" + "=" * 70)
print("METHOD (c): SHAP KernelExplainer on NaiveConcatFusion")
print("=" * 70)

# SHAP wrapper: takes numpy, returns numpy predictions
def concat_predict_fn(X_combined_np):
    """Predict function for SHAP: input is numpy, output is class probabilities."""
    with torch.no_grad():
        x = torch.tensor(X_combined_np, dtype=torch.float32).to(EXPLAIN_DEVICE)
        x_gene = x[:, :gene_dim]
        x_morph = x[:, gene_dim:]
        logits = concat_model(x_gene, x_morph)
        probs = torch.softmax(logits, dim=1).cpu().numpy()
    return probs

# Use a subsample of training data as background
rng = np.random.default_rng(SEED)
bg_idx = rng.choice(len(X_expr_train), size=min(N_SHAP_BACKGROUND, len(X_expr_train)), replace=False)
X_background = np.hstack([X_expr_train[bg_idx], X_morph_train[bg_idx]]).astype(np.float32)

# Subsample test set for SHAP (expensive)
n_shap = min(N_SHAP_SAMPLES, len(X_expr_test))
shap_idx = rng.choice(len(X_expr_test), size=n_shap, replace=False)
X_shap_test = np.hstack([X_expr_test[shap_idx], X_morph_test[shap_idx]]).astype(np.float32)
y_shap_test = y_test[shap_idx]

print(f"  Background samples: {len(X_background)}")
print(f"  Test samples for SHAP: {n_shap}")
print(f"  Feature dimensions: {X_shap_test.shape[1]} (gene: {gene_dim}, module: {morph_dim})")
print(f"  Running KernelExplainer (this is slow — ~5-15 min)...")

# Use KernelExplainer with kmeans summarization for speed
background_summary = shap.kmeans(X_background, 25)
explainer = shap.KernelExplainer(concat_predict_fn, background_summary)

# Compute SHAP values
shap_values = explainer.shap_values(X_shap_test, nsamples=100, silent=True)

# shap_values can be:
#   - a list of arrays, one per class: each is (n_shap, n_features)
#   - a 3D numpy array: (n_shap, n_features, n_classes)
#   - a 2D numpy array: (n_shap, n_features) for binary
if isinstance(shap_values, list):
    shap_array = np.array(shap_values)  # (n_classes, n_shap, n_features)
    shap_per_sample = np.zeros((n_shap, X_shap_test.shape[1]))
    for i in range(n_shap):
        pred_class = y_shap_test[i]
        shap_per_sample[i] = shap_array[pred_class, i, :]
elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
    # Shape is (n_shap, n_features, n_classes) — select predicted class per sample
    shap_per_sample = np.zeros((n_shap, X_shap_test.shape[1]))
    for i in range(n_shap):
        pred_class = y_shap_test[i]
        shap_per_sample[i] = shap_values[i, :, pred_class]
else:
    shap_per_sample = shap_values

print(f"  SHAP values shape: {shap_per_sample.shape}")

# Split SHAP into modalities
shap_gene = shap_per_sample[:, :gene_dim]
shap_morph = shap_per_sample[:, gene_dim:]

# Modality-level attribution from SHAP
shap_gene_importance = np.abs(shap_gene).sum(axis=1)
shap_morph_importance = np.abs(shap_morph).sum(axis=1)
shap_total = shap_gene_importance + shap_morph_importance + 1e-10

shap_gene_frac = shap_gene_importance / shap_total
shap_morph_frac = shap_morph_importance / shap_total

print(f"  SHAP modality attribution:")
print(f"    Genomic: mean={shap_gene_frac.mean():.4f}, std={shap_gene_frac.std():.4f}")
print(f"    Module:  mean={shap_morph_frac.mean():.4f}, std={shap_morph_frac.std():.4f}")


# ─── Comparison: All Three Methods ──────────────────────────────────────────
print("\n" + "=" * 70)
print("COMPARISON: Modality attribution across methods")
print("=" * 70)

comparison = {
    "method": ["Attention Weights", "Integrated Gradients", "SHAP (KernelExplainer)"],
    "genomic_mean": [
        float(attn_weights[:, 0].mean()),
        float(ig_gene_frac.mean()),
        float(shap_gene_frac.mean()),
    ],
    "genomic_std": [
        float(attn_weights[:, 0].std()),
        float(ig_gene_frac.std()),
        float(shap_gene_frac.std()),
    ],
    "module_mean": [
        float(attn_weights[:, 1].mean()),
        float(ig_morph_frac.mean()),
        float(shap_morph_frac.mean()),
    ],
    "module_std": [
        float(attn_weights[:, 1].std()),
        float(ig_morph_frac.std()),
        float(shap_morph_frac.std()),
    ],
    "model": [
        "CrossAttentionFusion",
        "CrossAttentionFusion",
        "NaiveConcatFusion",
    ],
}

comparison_df = pd.DataFrame(comparison)
print(comparison_df.to_string(index=False))

comparison_path = os.path.join(ARTIFACTS_DIR, "explainability_comparison.csv")
comparison_df.to_csv(comparison_path, index=False)
print(f"\n  Saved: {comparison_path}")


# ─── Marker Gene Attribution Agreement ───────────────────────────────────────
if marker_genes is not None:
    print("\n" + "=" * 70)
    print("MARKER GENE ATTRIBUTION AGREEMENT")
    print("=" * 70)
    print("  Checking if top-attributed genes (by IG) match known markers.")

    agreement_results = {}
    for c_idx, c_name in enumerate(class_names):
        if c_name not in marker_genes:
            continue
        known_markers = set(marker_genes[c_name])
        if c_name not in ig_top_genes_per_class:
            continue
        top_genes = set(ig_top_genes_per_class[c_name]["genes"])

        overlap = known_markers & top_genes
        precision = len(overlap) / len(top_genes) if top_genes else 0
        recall = len(overlap) / len(known_markers) if known_markers else 0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0

        agreement_results[c_name] = {
            "known_markers": len(known_markers),
            "top_attributed": len(top_genes),
            "overlap": len(overlap),
            "overlap_genes": sorted(list(overlap)),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
        print(f"  {c_name}:")
        print(f"    Known markers: {len(known_markers)}, Top-{TOP_K_FEATURES} by IG: {len(top_genes)}")
        print(f"    Overlap: {len(overlap)} genes — {sorted(list(overlap))[:5]}{'...' if len(overlap)>5 else ''}")
        print(f"    Precision={precision:.3f}, Recall={recall:.3f}, F1={f1:.3f}")

    # Save agreement results
    agreement_path = os.path.join(ARTIFACTS_DIR, "marker_agreement.json")
    with open(agreement_path, "w") as f:
        json.dump(agreement_results, f, indent=2)
    print(f"\n  Saved: {agreement_path}")

    # Summary table
    agreement_df = pd.DataFrame([
        {"cell_type": k, **{kk: vv for kk, vv in v.items() if kk != "overlap_genes"}}
        for k, v in agreement_results.items()
    ])
    if len(agreement_df) > 0:
        print(f"\n  Mean precision: {agreement_df['precision'].mean():.3f}")
        print(f"  Mean recall:    {agreement_df['recall'].mean():.3f}")
        print(f"  Mean F1:        {agreement_df['f1'].mean():.3f}")
        agreement_df.to_csv(os.path.join(ARTIFACTS_DIR, "marker_agreement.csv"), index=False)


# ─── Save All Attribution Data ───────────────────────────────────────────────
print("\n" + "=" * 70)
print("Saving attribution data")
print("=" * 70)

np.save(os.path.join(ARTIFACTS_DIR, "ig_attributions_gene.npy"), ig_gene)
np.save(os.path.join(ARTIFACTS_DIR, "ig_attributions_morph.npy"), ig_morph)
np.save(os.path.join(ARTIFACTS_DIR, "shap_values_gene.npy"), shap_gene)
np.save(os.path.join(ARTIFACTS_DIR, "shap_values_morph.npy"), shap_morph)
np.save(os.path.join(ARTIFACTS_DIR, "attn_weights_test.npy"), attn_weights)

# Save top genes per class from IG
with open(os.path.join(ARTIFACTS_DIR, "ig_top_genes_per_class.json"), "w") as f:
    json.dump(ig_top_genes_per_class, f, indent=2)

# Save per-class attention and IG breakdowns
with open(os.path.join(ARTIFACTS_DIR, "attn_per_class.json"), "w") as f:
    json.dump(attn_per_class, f, indent=2)
with open(os.path.join(ARTIFACTS_DIR, "ig_per_class.json"), "w") as f:
    json.dump(ig_per_class, f, indent=2)

print("  Saved: ig_attributions_gene.npy, ig_attributions_morph.npy")
print("  Saved: shap_values_gene.npy, shap_values_morph.npy")
print("  Saved: attn_weights_test.npy")
print("  Saved: ig_top_genes_per_class.json, attn_per_class.json, ig_per_class.json")

print("\nEXPLAINABILITY ANALYSIS COMPLETE")
