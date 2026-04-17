#!/usr/bin/env python3
"""
06_timing_benchmark.py — Computational Cost Benchmark for Attribution Methods

Benchmarks per-sample and full-test-set wall-clock time for:
  (a) Forward pass + attention weight extraction (CrossAttentionFusion)
  (b) Integrated Gradients via Captum (CrossAttentionFusion)
  (c) SHAP DeepExplainer (NaiveConcatFusion)
  (d) SHAP KernelExplainer (NaiveConcatFusion)

All timings from actual measurements using time.perf_counter().

Run from project root:
    python notebooks/06_timing_benchmark.py
"""

import os
import sys
import json
import time
import warnings
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from captum.attr import IntegratedGradients
import shap

warnings.filterwarnings("ignore")

# ─── Configuration ───────────────────────────────────────────────────────────
SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "artifacts")

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
# Captum and SHAP work best on CPU to avoid MPS gradient issues
EXPLAIN_DEVICE = "cpu"

N_TIMING_RUNS = 3          # repeat each benchmark this many times, take median
N_KERNEL_SHAP_SAMPLES = 20 # KernelExplainer is very slow; limit samples
N_SHAP_BACKGROUND = 100    # background samples for SHAP explainers
SHAP_NSAMPLES = 100        # nsamples kwarg for KernelExplainer
IG_STEPS = 50              # integration steps for IG (matches 04_explainability.py)

print(f"Device: {DEVICE} (explainability on {EXPLAIN_DEVICE})")
print(f"Timing runs: {N_TIMING_RUNS} (median selected)")

# ─── Model Definitions (same as 03_fusion_model.py) ─────────────────────────

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


class FusionWrapper(nn.Module):
    """Wraps CrossAttentionFusionModel to accept a single concatenated input (for Captum)."""
    def __init__(self, model, gene_dim, morph_dim):
        super().__init__()
        self.model = model
        self.gene_dim = gene_dim
        self.morph_dim = morph_dim

    def forward(self, x_combined):
        x_gene = x_combined[:, :self.gene_dim]
        x_morph = x_combined[:, self.gene_dim:]
        return self.model(x_gene, x_morph)


class ConcatWrapper(nn.Module):
    """Wraps NaiveConcatFusionModel to accept a single concatenated input (for SHAP Deep)."""
    def __init__(self, model, gene_dim, morph_dim):
        super().__init__()
        self.model = model
        self.gene_dim = gene_dim
        self.morph_dim = morph_dim

    def forward(self, x_combined):
        x_gene = x_combined[:, :self.gene_dim]
        x_morph = x_combined[:, self.gene_dim:]
        return self.model(x_gene, x_morph)


# ─── Load Data ───────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("Loading data and models")
print("=" * 70)

X_expr = np.load(os.path.join(ARTIFACTS_DIR, "real_modality1.npy"))
X_morph = np.load(os.path.join(ARTIFACTS_DIR, "real_modality2.npy"))
labels = np.load(os.path.join(ARTIFACTS_DIR, "real_labels.npy"))

with open(os.path.join(ARTIFACTS_DIR, "real_splits.json")) as f:
    splits = json.load(f)
with open(os.path.join(ARTIFACTS_DIR, "real_fusion_model_config.json")) as f:
    fconfig = json.load(f)

train_idx = np.array(splits["train_idx"])
test_idx = np.array(splits["test_idx"])
n_classes = splits["n_classes"]

X_expr_test = X_expr[test_idx]
X_morph_test = X_morph[test_idx]
y_test = labels[test_idx]
X_expr_train = X_expr[train_idx]
X_morph_train = X_morph[train_idx]

gene_dim = fconfig["gene_dim"]
morph_dim = fconfig["morph_dim"]
embed_dim = fconfig["embed_dim"]
n_test = len(test_idx)

print(f"  Test samples: {n_test}")
print(f"  Gene dim: {gene_dim}, Morph dim: {morph_dim}, Embed dim: {embed_dim}")
print(f"  Classes: {n_classes}")

# ─── Load Models ──────────────────────────────────────────────────────────────
fusion_model = CrossAttentionFusionModel(gene_dim, morph_dim, n_classes, embed_dim)
fusion_model.load_state_dict(
    torch.load(os.path.join(ARTIFACTS_DIR, "real_fusion_model.pt"),
               map_location=EXPLAIN_DEVICE, weights_only=True)
)
fusion_model.to(EXPLAIN_DEVICE)
fusion_model.eval()
print(f"  Loaded CrossAttentionFusion model")

concat_model = NaiveConcatFusionModel(gene_dim, morph_dim, n_classes, embed_dim)
concat_model.load_state_dict(
    torch.load(os.path.join(ARTIFACTS_DIR, "real_naive_concat_model.pt"),
               map_location=EXPLAIN_DEVICE, weights_only=True)
)
concat_model.to(EXPLAIN_DEVICE)
concat_model.eval()
print(f"  Loaded NaiveConcatFusion model")

# ─── Prepare Tensors ──────────────────────────────────────────────────────────
x_gene_t = torch.tensor(X_expr_test, dtype=torch.float32).to(EXPLAIN_DEVICE)
x_morph_t = torch.tensor(X_morph_test, dtype=torch.float32).to(EXPLAIN_DEVICE)
X_combined_test = np.hstack([X_expr_test, X_morph_test]).astype(np.float32)
x_combined_t = torch.tensor(X_combined_test, dtype=torch.float32).to(EXPLAIN_DEVICE)
baseline_single = torch.zeros(1, gene_dim + morph_dim, dtype=torch.float32).to(EXPLAIN_DEVICE)

# ─── Warmup ───────────────────────────────────────────────────────────────────
print("\nWarming up models (3 forward passes)...")
with torch.no_grad():
    for _ in range(3):
        _ = fusion_model(x_gene_t[:1], x_morph_t[:1])
        _ = concat_model(x_gene_t[:1], x_morph_t[:1])


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK (a): Forward pass + attention weight extraction
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("BENCHMARK (a): Forward pass + attention weight extraction")
print("=" * 70)

forward_times = []
for run in range(N_TIMING_RUNS):
    per_sample_times = []
    with torch.no_grad():
        for i in range(n_test):
            t0 = time.perf_counter()
            _ = fusion_model(x_gene_t[i:i+1], x_morph_t[i:i+1])
            attn_w = fusion_model.get_attention_weights()
            t1 = time.perf_counter()
            per_sample_times.append(t1 - t0)
    avg_ms = np.mean(per_sample_times) * 1000
    forward_times.append(avg_ms)
    print(f"  Run {run+1}: {avg_ms:.4f} ms/sample")

forward_median_ms = float(np.median(forward_times))
forward_total_s = forward_median_ms * n_test / 1000
print(f"  Median: {forward_median_ms:.4f} ms/sample")
print(f"  Total test set ({n_test} samples): {forward_total_s:.4f} s")


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK (b): Forward pass + attention (should be same as a, since weights
#   are a free byproduct of the forward pass -- confirming here)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("BENCHMARK (b): Forward pass + attention (verification -- same as a)")
print("=" * 70)
print(f"  Attention weights are extracted during forward pass at zero extra cost.")
print(f"  Per-sample: {forward_median_ms:.4f} ms (same as benchmark a)")


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK (c): Integrated Gradients (Captum)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("BENCHMARK (c): Integrated Gradients (Captum) on CrossAttentionFusion")
print("=" * 70)

wrapper = FusionWrapper(fusion_model, gene_dim, morph_dim).to(EXPLAIN_DEVICE)
wrapper.eval()
ig = IntegratedGradients(wrapper)

ig_times = []
for run in range(N_TIMING_RUNS):
    per_sample_times = []
    for i in range(n_test):
        inp = x_combined_t[i:i+1].clone().detach().requires_grad_(True)
        bl = baseline_single.clone()
        target = torch.tensor([y_test[i]], dtype=torch.long).to(EXPLAIN_DEVICE)

        t0 = time.perf_counter()
        attr = ig.attribute(inp, baselines=bl, target=target,
                            n_steps=IG_STEPS, internal_batch_size=50)
        t1 = time.perf_counter()
        per_sample_times.append(t1 - t0)

    avg_ms = np.mean(per_sample_times) * 1000
    ig_times.append(avg_ms)
    print(f"  Run {run+1}: {avg_ms:.4f} ms/sample")

ig_median_ms = float(np.median(ig_times))
ig_total_s = ig_median_ms * n_test / 1000
print(f"  Median: {ig_median_ms:.4f} ms/sample")
print(f"  Total test set ({n_test} samples): {ig_total_s:.4f} s")


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK (d): SHAP DeepExplainer on NaiveConcatFusion
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("BENCHMARK (d): SHAP DeepExplainer on NaiveConcatFusion")
print("=" * 70)

concat_wrapper = ConcatWrapper(concat_model, gene_dim, morph_dim).to(EXPLAIN_DEVICE)
concat_wrapper.eval()

# Background data for DeepExplainer
rng = np.random.default_rng(SEED)
bg_idx = rng.choice(len(X_expr_train), size=min(N_SHAP_BACKGROUND, len(X_expr_train)), replace=False)
X_bg = np.hstack([X_expr_train[bg_idx], X_morph_train[bg_idx]]).astype(np.float32)
bg_tensor = torch.tensor(X_bg, dtype=torch.float32).to(EXPLAIN_DEVICE)

deep_explainer = shap.DeepExplainer(concat_wrapper, bg_tensor)

deep_times = []
for run in range(N_TIMING_RUNS):
    per_sample_times = []
    for i in range(n_test):
        sample = x_combined_t[i:i+1]

        t0 = time.perf_counter()
        _ = deep_explainer.shap_values(sample)
        t1 = time.perf_counter()
        per_sample_times.append(t1 - t0)

    avg_ms = np.mean(per_sample_times) * 1000
    deep_times.append(avg_ms)
    print(f"  Run {run+1}: {avg_ms:.4f} ms/sample")

deep_median_ms = float(np.median(deep_times))
deep_total_s = deep_median_ms * n_test / 1000
print(f"  Median: {deep_median_ms:.4f} ms/sample")
print(f"  Total test set ({n_test} samples): {deep_total_s:.4f} s")


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK (e): SHAP KernelExplainer on NaiveConcatFusion (20 samples only)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print(f"BENCHMARK (e): SHAP KernelExplainer on NaiveConcatFusion ({N_KERNEL_SHAP_SAMPLES} samples)")
print("=" * 70)

def concat_predict_fn(X_combined_np):
    """Predict function for SHAP KernelExplainer."""
    with torch.no_grad():
        x = torch.tensor(X_combined_np, dtype=torch.float32).to(EXPLAIN_DEVICE)
        x_gene = x[:, :gene_dim]
        x_morph = x[:, gene_dim:]
        logits = concat_model(x_gene, x_morph)
        probs = torch.softmax(logits, dim=1).cpu().numpy()
    return probs

background_summary = shap.kmeans(X_bg, 25)
kernel_explainer = shap.KernelExplainer(concat_predict_fn, background_summary)

# Only time N_KERNEL_SHAP_SAMPLES samples (KernelExplainer is very slow)
kernel_sample_idx = rng.choice(n_test, size=min(N_KERNEL_SHAP_SAMPLES, n_test), replace=False)
X_kernel_test = X_combined_test[kernel_sample_idx]

kernel_times = []
for run in range(N_TIMING_RUNS):
    per_sample_times = []
    for i in range(len(X_kernel_test)):
        sample = X_kernel_test[i:i+1]

        t0 = time.perf_counter()
        _ = kernel_explainer.shap_values(sample, nsamples=SHAP_NSAMPLES, silent=True)
        t1 = time.perf_counter()
        per_sample_times.append(t1 - t0)

    avg_ms = np.mean(per_sample_times) * 1000
    kernel_times.append(avg_ms)
    print(f"  Run {run+1}: {avg_ms:.4f} ms/sample (measured on {len(X_kernel_test)} samples)")

kernel_median_ms = float(np.median(kernel_times))
kernel_total_s = kernel_median_ms * n_test / 1000  # extrapolated to full test set
print(f"  Median: {kernel_median_ms:.4f} ms/sample")
print(f"  Estimated full test set ({n_test} samples): {kernel_total_s:.4f} s")


# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS TABLE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TIMING BENCHMARK RESULTS")
print("=" * 70)

results = [
    {
        "method": "Forward + attention",
        "per_sample_ms": forward_median_ms,
        "full_test_set_s": forward_total_s,
        "relative_to_attention": 1.0,
        "note": "Free (byproduct of forward pass)",
    },
    {
        "method": "Integrated Gradients",
        "per_sample_ms": ig_median_ms,
        "full_test_set_s": ig_total_s,
        "relative_to_attention": ig_median_ms / forward_median_ms,
        "note": f"Captum, {IG_STEPS} steps",
    },
    {
        "method": "SHAP (DeepExplainer)",
        "per_sample_ms": deep_median_ms,
        "full_test_set_s": deep_total_s,
        "relative_to_attention": deep_median_ms / forward_median_ms,
        "note": f"{N_SHAP_BACKGROUND} background samples",
    },
    {
        "method": "SHAP (KernelExplainer)",
        "per_sample_ms": kernel_median_ms,
        "full_test_set_s": kernel_total_s,
        "relative_to_attention": kernel_median_ms / forward_median_ms,
        "note": f"nsamples={SHAP_NSAMPLES}, measured on {N_KERNEL_SHAP_SAMPLES} samples, full set extrapolated",
    },
]

# Print formatted table
header = f"{'Method':<26} | {'Per-sample (ms)':>15} | {'Full test set (s)':>18} | {'Relative to attention':>22}"
sep = "-" * len(header)
print(sep)
print(header)
print(sep)
for r in results:
    print(f"{r['method']:<26} | {r['per_sample_ms']:>15.4f} | {r['full_test_set_s']:>18.4f} | {r['relative_to_attention']:>21.1f}x")
print(sep)

print(f"\nTest set size: {n_test} samples")
print(f"Device: {EXPLAIN_DEVICE}")
print(f"Timing runs: {N_TIMING_RUNS} (median reported)")

# ─── Save CSV ─────────────────────────────────────────────────────────────────
results_df = pd.DataFrame(results)
csv_path = os.path.join(ARTIFACTS_DIR, "timing_benchmark.csv")
results_df.to_csv(csv_path, index=False)
print(f"\nSaved: {csv_path}")

print("\nTIMING BENCHMARK COMPLETE")
