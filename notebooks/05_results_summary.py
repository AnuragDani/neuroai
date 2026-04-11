#!/usr/bin/env python3
"""
05_results_summary.py — Results Aggregation and Visualization

Loads all metrics from artifacts/ and produces:
  (a) AUROC comparison bar chart
  (b) Calibration plot (ECE)
  (c) Modality attribution heatmap
  (d) Top-feature attribution comparison
  (e) Summary tables for the paper

Run from project root:
    python notebooks/05_results_summary.py
"""

import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for saving figures
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import label_binarize

warnings.filterwarnings("ignore")

# ─── Configuration ───────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(PROJECT_ROOT, "artifacts")
FIGURES_DIR = os.path.join(ARTIFACTS_DIR, "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

# Plot style
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.figsize": (8, 5),
})

# ─── Load All Metrics ────────────────────────────────────────────────────────
print("=" * 70)
print("Loading all experimental results")
print("=" * 70)

# Combined metrics
all_metrics_path = os.path.join(ARTIFACTS_DIR, "all_metrics.csv")
if os.path.exists(all_metrics_path):
    all_metrics = pd.read_csv(all_metrics_path)
else:
    # Fallback: load separately and combine
    dfs = []
    for fname in ["baseline_metrics.csv", "fusion_metrics.csv"]:
        path = os.path.join(ARTIFACTS_DIR, fname)
        if os.path.exists(path):
            dfs.append(pd.read_csv(path))
    all_metrics = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

print(f"  Models evaluated: {len(all_metrics)}")
print(f"  Columns: {list(all_metrics.columns)}")

# Load explainability data
explainability_path = os.path.join(ARTIFACTS_DIR, "explainability_comparison.csv")
explainability_df = pd.read_csv(explainability_path) if os.path.exists(explainability_path) else None

# Load per-class attention and IG data
attn_per_class = {}
attn_path = os.path.join(ARTIFACTS_DIR, "attn_per_class.json")
if os.path.exists(attn_path):
    with open(attn_path) as f:
        attn_per_class = json.load(f)

ig_per_class = {}
ig_path = os.path.join(ARTIFACTS_DIR, "ig_per_class.json")
if os.path.exists(ig_path):
    with open(ig_path) as f:
        ig_per_class = json.load(f)

# Load top genes
ig_top_genes = {}
top_genes_path = os.path.join(ARTIFACTS_DIR, "ig_top_genes_per_class.json")
if os.path.exists(top_genes_path):
    with open(top_genes_path) as f:
        ig_top_genes = json.load(f)

# Load marker agreement
marker_agreement = {}
marker_agree_path = os.path.join(ARTIFACTS_DIR, "marker_agreement.json")
if os.path.exists(marker_agree_path):
    with open(marker_agree_path) as f:
        marker_agreement = json.load(f)

# Load splits for class names
with open(os.path.join(ARTIFACTS_DIR, "splits.json")) as f:
    splits = json.load(f)
class_names = splits["class_names"]
n_classes = splits["n_classes"]


# ─── Figure (a): AUROC Comparison Bar Chart ──────────────────────────────────
print("\n" + "=" * 70)
print("Figure (a): AUROC comparison bar chart")
print("=" * 70)

fig, ax = plt.subplots(figsize=(9, 5))

models = all_metrics["model"].values
aurocs = all_metrics["auroc_macro"].values
ci_lo = all_metrics["auroc_macro_ci_lo"].values if "auroc_macro_ci_lo" in all_metrics.columns else np.zeros_like(aurocs)
ci_hi = all_metrics["auroc_macro_ci_hi"].values if "auroc_macro_ci_hi" in all_metrics.columns else np.zeros_like(aurocs)
errors = np.array([np.clip(aurocs - ci_lo, 0, None), np.clip(ci_hi - aurocs, 0, None)])

colors = sns.color_palette("Set2", n_colors=len(models))
bars = ax.bar(range(len(models)), aurocs, yerr=errors, capsize=5,
              color=colors, edgecolor="black", linewidth=0.5, alpha=0.85)

ax.set_xticks(range(len(models)))
ax.set_xticklabels([m.replace("_", "\n") for m in models], rotation=0)
ax.set_ylabel("AUROC (macro, OVR)")
ax.set_title("Classification Performance: AUROC by Model")
ax.set_ylim(0, 1.05)

# Add value labels on bars
for bar, val, lo, hi in zip(bars, aurocs, ci_lo, ci_hi):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
            f"{val:.3f}\n[{lo:.3f}, {hi:.3f}]",
            ha="center", va="bottom", fontsize=8)

ax.axhline(y=0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.5, label="Random baseline")
ax.legend(loc="lower right")
ax.grid(axis="y", alpha=0.3)

auroc_path = os.path.join(FIGURES_DIR, "auroc_comparison.png")
fig.savefig(auroc_path)
plt.close(fig)
print(f"  Saved: {auroc_path}")

# Also save a multi-metric comparison
fig, axes = plt.subplots(1, 4, figsize=(16, 5))
metric_names = ["accuracy", "f1_weighted", "auroc_macro", "ece"]
metric_labels = ["Accuracy", "F1 (Weighted)", "AUROC (Macro)", "ECE"]

for ax, metric, label in zip(axes, metric_names, metric_labels):
    vals = all_metrics[metric].values
    ci_lo_col = f"{metric}_ci_lo"
    ci_hi_col = f"{metric}_ci_hi"
    if ci_lo_col in all_metrics.columns:
        lo = all_metrics[ci_lo_col].values
        hi = all_metrics[ci_hi_col].values
        # Clip to non-negative (bootstrap CI can occasionally cross point estimate)
        errs = np.array([np.clip(vals - lo, 0, None), np.clip(hi - vals, 0, None)])
    else:
        errs = None

    bars = ax.bar(range(len(models)), vals, yerr=errs, capsize=4,
                  color=colors, edgecolor="black", linewidth=0.5, alpha=0.85)
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels([m.replace("_", "\n") for m in models], rotation=45, ha="right", fontsize=7)
    ax.set_title(label)
    ax.grid(axis="y", alpha=0.3)

    # For ECE, lower is better
    if metric == "ece":
        ax.set_ylim(0, max(vals) * 1.5 + 0.01)
    else:
        ax.set_ylim(0, 1.05)

fig.suptitle("Model Comparison Across All Metrics (with 95% Bootstrap CIs)", fontsize=13, y=1.02)
fig.tight_layout()
multi_metric_path = os.path.join(FIGURES_DIR, "multi_metric_comparison.png")
fig.savefig(multi_metric_path)
plt.close(fig)
print(f"  Saved: {multi_metric_path}")


# ─── Figure (b): Calibration Plot ───────────────────────────────────────────
print("\n" + "=" * 70)
print("Figure (b): Calibration comparison (ECE)")
print("=" * 70)

fig, ax = plt.subplots(figsize=(7, 5))

ece_vals = all_metrics["ece"].values
ece_colors = sns.color_palette("coolwarm", n_colors=len(models))

bars = ax.barh(range(len(models)), ece_vals, color=ece_colors,
               edgecolor="black", linewidth=0.5, alpha=0.85, height=0.6)

ax.set_yticks(range(len(models)))
ax.set_yticklabels(models)
ax.set_xlabel("Expected Calibration Error (ECE)")
ax.set_title("Model Calibration: Lower ECE = Better Calibrated")

for bar, val in zip(bars, ece_vals):
    ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height() / 2,
            f"{val:.4f}", ha="left", va="center", fontsize=9)

ax.axvline(x=0, color="black", linewidth=0.8)
ax.grid(axis="x", alpha=0.3)
ax.invert_yaxis()

calibration_path = os.path.join(FIGURES_DIR, "calibration_ece.png")
fig.savefig(calibration_path)
plt.close(fig)
print(f"  Saved: {calibration_path}")


# ─── Figure (c): Modality Attribution Heatmap ────────────────────────────────
print("\n" + "=" * 70)
print("Figure (c): Modality attribution heatmap")
print("=" * 70)

if attn_per_class and ig_per_class:
    # Build a matrix: rows = cell types, columns = [Attn_Genomic, Attn_Module, IG_Genomic, IG_Module]
    cell_types = sorted(set(attn_per_class.keys()) & set(ig_per_class.keys()))

    if cell_types:
        heatmap_data = np.zeros((len(cell_types), 4))
        col_labels = ["Attention\nGenomic", "Attention\nModule", "IG\nGenomic", "IG\nModule"]

        for i, ct in enumerate(cell_types):
            heatmap_data[i, 0] = attn_per_class[ct]["genomic_mean"]
            heatmap_data[i, 1] = attn_per_class[ct]["module_mean"]
            heatmap_data[i, 2] = ig_per_class[ct]["genomic_frac"]
            heatmap_data[i, 3] = ig_per_class[ct]["module_frac"]

        fig, ax = plt.subplots(figsize=(8, max(4, len(cell_types) * 0.8)))
        im = ax.imshow(heatmap_data, cmap="YlOrRd", aspect="auto", vmin=0, vmax=1)

        ax.set_xticks(range(4))
        ax.set_xticklabels(col_labels, fontsize=9)
        ax.set_yticks(range(len(cell_types)))
        ax.set_yticklabels([ct.replace("_", " ") for ct in cell_types], fontsize=9)
        ax.set_title("Modality Attribution by Cell Type and Method")

        # Annotate cells
        for i in range(len(cell_types)):
            for j in range(4):
                text_color = "white" if heatmap_data[i, j] > 0.6 else "black"
                ax.text(j, i, f"{heatmap_data[i, j]:.3f}",
                        ha="center", va="center", fontsize=8, color=text_color)

        plt.colorbar(im, ax=ax, label="Attribution Weight / Fraction", shrink=0.8)
        fig.tight_layout()

        heatmap_path = os.path.join(FIGURES_DIR, "modality_attribution_heatmap.png")
        fig.savefig(heatmap_path)
        plt.close(fig)
        print(f"  Saved: {heatmap_path}")
    else:
        print("  No overlapping cell types between attention and IG data")
else:
    print("  Skipping — per-class attribution data not available")


# ─── Figure (d): Top Feature Attribution Comparison ──────────────────────────
print("\n" + "=" * 70)
print("Figure (d): Top feature attribution comparison")
print("=" * 70)

if ig_top_genes:
    n_types_to_plot = min(len(ig_top_genes), 6)
    cell_types_to_plot = list(ig_top_genes.keys())[:n_types_to_plot]

    fig, axes = plt.subplots(1, n_types_to_plot, figsize=(5 * n_types_to_plot, 6))
    if n_types_to_plot == 1:
        axes = [axes]

    for ax, ct_name in zip(axes, cell_types_to_plot):
        genes = ig_top_genes[ct_name]["genes"][:10]  # top 10
        attrs = ig_top_genes[ct_name]["attributions"][:10]

        # Highlight known markers
        is_marker = []
        if marker_agreement and ct_name in marker_agreement:
            known_markers = set(marker_agreement[ct_name].get("overlap_genes", []))
            for g in genes:
                is_marker.append(g in known_markers)
        else:
            is_marker = [False] * len(genes)

        bar_colors = ["#e74c3c" if m else "#3498db" for m in is_marker]

        y_pos = range(len(genes))
        ax.barh(y_pos, attrs, color=bar_colors, edgecolor="black", linewidth=0.3, height=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(genes, fontsize=8)
        ax.set_xlabel("Mean |IG Attribution|", fontsize=9)
        ax.set_title(ct_name.replace("_", " "), fontsize=10)
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.3)

    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#e74c3c", edgecolor="black", label="Known marker"),
        Patch(facecolor="#3498db", edgecolor="black", label="Other gene"),
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=2, fontsize=10,
               bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Top-10 Genes by Integrated Gradients Attribution per Cell Type", fontsize=12, y=1.02)
    fig.tight_layout()

    top_features_path = os.path.join(FIGURES_DIR, "top_feature_attribution.png")
    fig.savefig(top_features_path)
    plt.close(fig)
    print(f"  Saved: {top_features_path}")
else:
    print("  Skipping — IG top genes data not available")


# ─── Figure (e): Attribution Method Agreement ────────────────────────────────
print("\n" + "=" * 70)
print("Figure (e): Attribution method comparison")
print("=" * 70)

if explainability_df is not None and len(explainability_df) > 0:
    fig, ax = plt.subplots(figsize=(8, 4))

    methods = explainability_df["method"].values
    x = np.arange(len(methods))
    width = 0.35

    bars1 = ax.bar(x - width/2, explainability_df["genomic_mean"], width,
                   yerr=explainability_df["genomic_std"], capsize=5,
                   label="Genomic Modality", color="#2ecc71", alpha=0.85,
                   edgecolor="black", linewidth=0.5)
    bars2 = ax.bar(x + width/2, explainability_df["module_mean"], width,
                   yerr=explainability_df["module_std"], capsize=5,
                   label="Module Modality", color="#9b59b6", alpha=0.85,
                   edgecolor="black", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(methods, fontsize=9)
    ax.set_ylabel("Attribution Weight / Fraction")
    ax.set_title("Modality Attribution: Attention vs. IG vs. SHAP")
    ax.legend()
    ax.set_ylim(0, 1.1)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    method_comp_path = os.path.join(FIGURES_DIR, "attribution_method_comparison.png")
    fig.savefig(method_comp_path)
    plt.close(fig)
    print(f"  Saved: {method_comp_path}")
else:
    print("  Skipping — explainability comparison data not available")


# ─── Marker Gene Agreement Figure ───────────────────────────────────────────
if marker_agreement:
    print("\n" + "=" * 70)
    print("Figure (f): Marker gene agreement")
    print("=" * 70)

    fig, ax = plt.subplots(figsize=(8, max(4, len(marker_agreement) * 0.8)))

    ct_names_sorted = sorted(marker_agreement.keys())
    precision_vals = [marker_agreement[ct]["precision"] for ct in ct_names_sorted]
    recall_vals = [marker_agreement[ct]["recall"] for ct in ct_names_sorted]
    f1_vals = [marker_agreement[ct]["f1"] for ct in ct_names_sorted]

    x = np.arange(len(ct_names_sorted))
    width = 0.25

    ax.barh(x - width, precision_vals, width, label="Precision", color="#3498db", alpha=0.85)
    ax.barh(x, recall_vals, width, label="Recall", color="#e74c3c", alpha=0.85)
    ax.barh(x + width, f1_vals, width, label="F1", color="#2ecc71", alpha=0.85)

    ax.set_yticks(x)
    ax.set_yticklabels([ct.replace("_", " ") for ct in ct_names_sorted], fontsize=9)
    ax.set_xlabel("Score")
    ax.set_title("Marker Gene Attribution Agreement\n(IG Top-20 vs. Known Markers)")
    ax.legend(loc="lower right")
    ax.set_xlim(0, 1.05)
    ax.grid(axis="x", alpha=0.3)

    fig.tight_layout()
    marker_path = os.path.join(FIGURES_DIR, "marker_gene_agreement.png")
    fig.savefig(marker_path)
    plt.close(fig)
    print(f"  Saved: {marker_path}")


# ─── Print Summary Tables (Paper-Ready) ─────────────────────────────────────
print("\n" + "=" * 70)
print("PAPER-READY SUMMARY TABLES")
print("=" * 70)

# Table 1: Model Performance Comparison
print("\n--- Table 1: Model Performance Comparison ---")
print("(Copy-paste into paper LaTeX or Markdown)")
print()

header = f"| {'Model':<25} | {'Accuracy':>12} | {'F1 (Weighted)':>15} | {'AUROC (Macro)':>15} | {'ECE':>10} |"
sep = f"|{'-'*27}|{'-'*14}|{'-'*17}|{'-'*17}|{'-'*12}|"
print(header)
print(sep)

for _, row in all_metrics.iterrows():
    model_name = row["model"]
    acc_str = f"{row['accuracy']:.3f}"
    f1_str = f"{row['f1_weighted']:.3f}"
    auroc_str = f"{row['auroc_macro']:.3f}"
    ece_str = f"{row['ece']:.4f}"

    if "accuracy_ci_lo" in row and not pd.isna(row.get("accuracy_ci_lo", np.nan)):
        acc_str += f" [{row['accuracy_ci_lo']:.3f}, {row['accuracy_ci_hi']:.3f}]"
        f1_str += f" [{row['f1_weighted_ci_lo']:.3f}, {row['f1_weighted_ci_hi']:.3f}]"
        auroc_str += f" [{row['auroc_macro_ci_lo']:.3f}, {row['auroc_macro_ci_hi']:.3f}]"

    # Truncate for table width
    print(f"| {model_name:<25} | {row['accuracy']:>12.3f} | {row['f1_weighted']:>15.3f} | {row['auroc_macro']:>15.3f} | {row['ece']:>10.4f} |")

print(sep)

# Table 1b: With CIs
print("\n--- Table 1b: Performance with 95% Bootstrap CIs ---")
print()
for _, row in all_metrics.iterrows():
    print(f"  {row['model']}:")
    for metric in ["accuracy", "f1_weighted", "auroc_macro", "ece"]:
        val = row[metric]
        ci_lo = row.get(f"{metric}_ci_lo", np.nan)
        ci_hi = row.get(f"{metric}_ci_hi", np.nan)
        if not pd.isna(ci_lo):
            print(f"    {metric:>15}: {val:.4f} [{ci_lo:.4f}, {ci_hi:.4f}]")
        else:
            print(f"    {metric:>15}: {val:.4f}")
    print()


# Table 2: Modality Attribution Comparison
if explainability_df is not None:
    print("\n--- Table 2: Modality Attribution Comparison ---")
    print()
    header2 = f"| {'Method':<30} | {'Genomic (mean +/- std)':>24} | {'Module (mean +/- std)':>24} | {'Model':<25} |"
    sep2 = f"|{'-'*32}|{'-'*26}|{'-'*26}|{'-'*27}|"
    print(header2)
    print(sep2)
    for _, row in explainability_df.iterrows():
        g_str = f"{row['genomic_mean']:.3f} +/- {row['genomic_std']:.3f}"
        m_str = f"{row['module_mean']:.3f} +/- {row['module_std']:.3f}"
        print(f"| {row['method']:<30} | {g_str:>24} | {m_str:>24} | {row['model']:<25} |")
    print(sep2)

# Table 3: Marker Gene Agreement
if marker_agreement:
    print("\n--- Table 3: Marker Gene Attribution Agreement (IG top-20 vs known markers) ---")
    print()
    header3 = f"| {'Cell Type':<22} | {'Known':>6} | {'Top-20':>6} | {'Overlap':>7} | {'Precision':>9} | {'Recall':>6} | {'F1':>6} |"
    sep3 = f"|{'-'*24}|{'-'*8}|{'-'*8}|{'-'*9}|{'-'*11}|{'-'*8}|{'-'*8}|"
    print(header3)
    print(sep3)
    for ct_name in sorted(marker_agreement.keys()):
        v = marker_agreement[ct_name]
        print(f"| {ct_name:<22} | {v['known_markers']:>6} | {v['top_attributed']:>6} | {v['overlap']:>7} | {v['precision']:>9.3f} | {v['recall']:>6.3f} | {v['f1']:>6.3f} |")
    print(sep3)

    # Compute means
    prec_mean = np.mean([v["precision"] for v in marker_agreement.values()])
    rec_mean = np.mean([v["recall"] for v in marker_agreement.values()])
    f1_mean = np.mean([v["f1"] for v in marker_agreement.values()])
    print(f"| {'MEAN':<22} | {'':>6} | {'':>6} | {'':>7} | {prec_mean:>9.3f} | {rec_mean:>6.3f} | {f1_mean:>6.3f} |")
    print(sep3)


# ─── Summary of All Saved Figures ────────────────────────────────────────────
print("\n" + "=" * 70)
print("ALL SAVED ARTIFACTS")
print("=" * 70)

print("\n  Figures:")
for fname in sorted(os.listdir(FIGURES_DIR)):
    fpath = os.path.join(FIGURES_DIR, fname)
    size_kb = os.path.getsize(fpath) / 1024
    print(f"    {fname} ({size_kb:.0f} KB)")

print("\n  Data files:")
for fname in sorted(os.listdir(ARTIFACTS_DIR)):
    fpath = os.path.join(ARTIFACTS_DIR, fname)
    if os.path.isfile(fpath) and not fname.startswith("."):
        size_kb = os.path.getsize(fpath) / 1024
        ext = os.path.splitext(fname)[1]
        print(f"    {fname} ({size_kb:.0f} KB)")

print("\nRESULTS SUMMARY COMPLETE")
