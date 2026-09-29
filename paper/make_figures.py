#!/usr/bin/env python3
"""Figure builder for the P22-NN paper (decision-tree N25).

Builds:

  * Fig 1 -- architecture / ladder schematic (no external source JSON);
  * Fig 2 -- planted-signal benchmark from ``docs/nn_v2/planted_benchmark.json``;
  * Fig 3 -- ladder forest (CA−TC per rung + logreg reference) from
    ``docs/nn_v2/ladder_summary.json``;
  * Fig 4 -- faithfulness Δ log-loss from ``docs/nn_v2/faithfulness.json``;
  * Fig 5 -- cell-state spectrum from ``docs/nn_v2/spectrum.json``;
  * Fig 6 -- per-fold vs pooled AUROC from ``docs/nn_v2/v5/per_fold_metrics.json``;
  * Fig 7 -- detectability (S4 CA−TC detection fraction vs δ) from
    ``docs/nn_v2/v6/detectability.json``.

IF a source JSON is missing, that figure is skipped and recorded in
``SKIPPED_FIGURES`` (decision-tree N25). Missing planted JSON still fails the
``--only planted`` CLI with exit code 2 (P2 contract).

Usage:
    python paper/make_figures.py --only all [--outdir paper/figures]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (must follow matplotlib.use)

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent
DEFAULT_PLANTED = _REPO_ROOT / "docs" / "nn_v2" / "planted_benchmark.json"
DEFAULT_LADDER = _REPO_ROOT / "docs" / "nn_v2" / "ladder_summary.json"
DEFAULT_FAITH = _REPO_ROOT / "docs" / "nn_v2" / "faithfulness.json"
DEFAULT_SPECTRUM = _REPO_ROOT / "docs" / "nn_v2" / "spectrum.json"
DEFAULT_PER_FOLD = _REPO_ROOT / "docs" / "nn_v2" / "v5" / "per_fold_metrics.json"
DEFAULT_DETECT = _REPO_ROOT / "docs" / "nn_v2" / "v6" / "detectability.json"
DEFAULT_OUTDIR = _HERE / "figures"
PER_FOLD_ARMS = ("R3_ca", "R3_tc", "logreg_rna", "majority", "chr21_dosage")

MODEL_ORDER = (
    "cross_attention",
    "gated_fusion",
    "token_concat",
    "rna_atac_concat",
    "logreg_concat",
)
MODEL_LABELS = {
    "cross_attention": "Cross-attention",
    "gated_fusion": "Gated fusion",
    "token_concat": "Token concat",
    "rna_atac_concat": "RNA+ATAC concat",
    "logreg_concat": "Logreg concat",
}
SCENARIOS = ("S1", "S2", "S3", "S4", "S5")
DELTAS = (0.25, 0.5, 1.0)
LADDER_RUNG_KEYS = (
    ("R1", "R1_ca_vs_R1_tc"),
    ("R2", "R2_ca_vs_R2_tc"),
    ("R3", "R3_ca_vs_R3_tc"),
    ("R4", "R4_ca_vs_R4_tc"),
)
FAITH_PRIMARY_ARM = "R3_ca"
FAITH_INTERVENTIONS = ("I1", "I2", "I3", "I4", "I5", "I6_01", "I6_10", "I6_55", "NC")

# Populated by ``main`` when a Fig 3–5 source is absent (skip/renumber rule).
SKIPPED_FIGURES: list[str] = []

class MissingSourceError(FileNotFoundError):
    """Raised when a figure's source JSON is absent."""


def load_source(path: Path) -> dict:
    if not path.exists():
        raise MissingSourceError(f"source JSON not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _ba(data: dict, scenario: str, delta: float, model: str) -> float:
    return data["regime_labels"][f"{scenario}@{delta}"]["mean_balanced_accuracy"][model]


def _box(ax, x: float, y: float, w: float, h: float, text: str, *, fontsize: float = 8.5) -> None:
    """Rounded FancyBboxPatch with centred wrapped-free text."""
    from matplotlib.patches import FancyBboxPatch

    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.1,
        edgecolor="black",
        facecolor="#eef3fb",
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize)


def _arrow(ax, x0: float, y0: float, x1: float, y1: float, *, style: str = "-|>") -> None:
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops=dict(arrowstyle=style, linewidth=1.1, color="black"),
    )


def _save(fig, outdir: Path, stem: str) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for ext in ("png", "pdf"):
        path = outdir / f"{stem}.{ext}"
        fig.savefig(path, dpi=300)
        written.append(path)
    plt.close(fig)
    return written


def _draw_ladder(ax) -> None:
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("(a) Model ladder: one refinement per rung", fontsize=10)
    rungs = [
        ("R0", "cell-level cross-entropy\n(donor labels inherited)"),
        ("R1", "gated-attention MIL\nover donor bags"),
        ("R2", "R1 + conditional nuisance\nadversary (gradient reversal)"),
        ("R3", "R2 + symmetric InfoNCE\npairing loss  (primary)"),
        ("R4", "R3 + program/NMF tokens\nand region modules"),
    ]
    top, height, gap = 8.6, 1.15, 0.35
    xs, w = 0.4, 5.6
    for i, (name, desc) in enumerate(rungs):
        y = top - i * (height + gap)
        _box(ax, xs, y, w, height, f"{name}\n{desc}", fontsize=7.6)
        if i:
            y_prev = top - (i - 1) * (height + gap)
            _arrow(ax, xs + w / 2, y_prev, xs + w / 2, y + height)
    ax.text(
        xs + w / 2,
        top - len(rungs) * (height + gap) - 0.05,
        "each rung trains a CA arm and a\nparameter-matched TC arm identically",
        ha="center",
        va="top",
        fontsize=7.5,
        style="italic",
    )


def _draw_architecture(ax) -> None:
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("(b) Donor-level architecture (R3 shown)", fontsize=10)
    # encoder columns
    _box(ax, 0.2, 7.6, 1.9, 1.0, "RNA counts", fontsize=8)
    _box(ax, 0.2, 5.9, 1.9, 1.0, "ATAC counts", fontsize=8)
    _box(ax, 2.6, 7.6, 1.9, 1.0, "RNA encoder\n(scaled dispersion)", fontsize=7.3)
    _box(ax, 2.6, 5.9, 1.9, 1.0, "ATAC encoder\n(TF-IDF regions)", fontsize=7.3)
    _box(ax, 5.0, 7.6, 1.7, 1.0, "RNA tokens", fontsize=8)
    _box(ax, 5.0, 5.9, 1.7, 1.0, "ATAC tokens", fontsize=8)
    _arrow(ax, 2.1, 8.1, 2.6, 8.1)
    _arrow(ax, 2.1, 6.4, 2.6, 6.4)
    _arrow(ax, 4.5, 8.1, 5.0, 8.1)
    _arrow(ax, 4.5, 6.4, 5.0, 6.4)
    # fusion + head
    _box(ax, 7.2, 6.75, 2.5, 1.5, "cross-modal\nattention", fontsize=8.5)
    _arrow(ax, 6.7, 8.1, 7.2, 7.7)
    _arrow(ax, 6.7, 6.4, 7.2, 7.3)
    _box(ax, 4.6, 4.1, 3.0, 1.0, "donor bag attention (MIL)", fontsize=8.3)
    _arrow(ax, 8.45, 6.75, 6.1, 5.1)
    _box(ax, 2.2, 2.3, 2.6, 1.0, "donor logit", fontsize=8.3)
    _arrow(ax, 6.1, 4.1, 4.8, 3.3)
    # auxiliary branches
    _box(ax, 1.0, 0.3, 3.2, 1.0, "nuisance adversary (GRL)\nlibrary / batch / QC", fontsize=7.3)
    _arrow(ax, 5.4, 4.1, 2.6, 1.3, style="-[")
    _box(ax, 5.2, 0.3, 4.4, 1.0, "InfoNCE pairing loss\n(L2 projections, tau=0.1)", fontsize=7.3)
    _arrow(ax, 5.85, 5.9, 7.4, 1.3, style="-[")
    ax.text(
        0.2,
        0.15,
        "attention weights are diagnostics, not explanations",
        fontsize=6.8,
        style="italic",
    )


def build_fig1(outdir: Path) -> list[Path]:
    """Architecture / ladder schematic (no external source JSON)."""
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.0))
    _draw_ladder(axes[0])
    _draw_architecture(axes[1])
    fig.tight_layout()
    return _save(fig, outdir, "fig1_schematic")


def _build_heatmap(ax, data: dict) -> None:
    rows = ["S0@0.0"] + [f"{s}@1.0" for s in SCENARIOS]
    labels = ["S0 (delta=0.0)"] + [f"{s} (delta=1.0)" for s in SCENARIOS]
    grid = np.array(
        [[data["regime_labels"][r]["mean_balanced_accuracy"][m] for m in MODEL_ORDER] for r in rows]
    )
    im = ax.imshow(grid, cmap="viridis", vmin=0.4, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(MODEL_ORDER)))
    ax.set_xticklabels([MODEL_LABELS[m] for m in MODEL_ORDER], rotation=30, ha="right")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            value = grid[i, j]
            color = "white" if value < 0.8 else "black"
            ax.text(j, i, f"{value:.3f}", ha="center", va="center", color=color, fontsize=8)
    ax.set_title("Planted benchmark: balanced accuracy\n(scenario x model)")
    ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="balanced accuracy")


def _build_delta_curve(ax, data: dict, scenario: str, show_legend: bool) -> None:
    for model in MODEL_ORDER:
        ys = [_ba(data, scenario, d, model) for d in DELTAS]
        lw = 2.4 if model == "cross_attention" else 1.2
        alpha = 1.0 if model == "cross_attention" else 0.75
        ax.plot(DELTAS, ys, marker="o", linewidth=lw, alpha=alpha, label=MODEL_LABELS[model])
    ax.set_xticks(DELTAS)
    ax.set_xticklabels([f"{d:g}" for d in DELTAS])
    ax.set_xlabel("planted delta")
    ax.set_ylim(0.4, 1.05)
    regime = data["regime_labels"][f"{scenario}@1.0"]["regime"]
    ax.set_title(f"{scenario}: balanced accuracy vs delta\n(regime at delta=1.0: {regime})")
    if show_legend:
        ax.legend(fontsize=7, loc="lower right", frameon=False)


def build_fig2(data: dict, outdir: Path) -> list[Path]:
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.6))
    _build_heatmap(axes[0], data)
    _build_delta_curve(axes[1], data, "S4", show_legend=False)
    _build_delta_curve(axes[2], data, "S5", show_legend=True)
    axes[1].set_ylabel("balanced accuracy")
    fig.suptitle("Planted synthetic signal only; no biological or clinical claim", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    return _save(fig, outdir, "fig2_planted")


def build_fig3(data: dict, outdir: Path) -> list[Path]:
    """Ladder forest: CA−TC per rung with CIs; logreg reference line."""
    contrasts = data["secondary_contrasts"]
    labels: list[str] = []
    estimates: list[float] = []
    lo_err: list[float] = []
    hi_err: list[float] = []
    for rung, key in LADDER_RUNG_KEYS:
        row = contrasts[key]
        est = float(row["estimate"])
        lo, hi = (float(row["interval"][0]), float(row["interval"][1]))
        labels.append(f"{rung} CA−TC")
        estimates.append(est)
        lo_err.append(est - lo)
        hi_err.append(hi - est)

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    y = np.arange(len(labels))[::-1]
    ax.errorbar(
        estimates,
        y,
        xerr=[lo_err, hi_err],
        fmt="o",
        color="#1f4e79",
        ecolor="#1f4e79",
        capsize=3,
        markersize=6,
        label="CA − TC (95% CI)",
    )
    ax.axvline(0.0, color="black", linestyle="--", linewidth=1.0, label="null (0)")
    margin = float(data["primary"]["margin"])
    ax.axvline(
        margin,
        color="#888888",
        linestyle=":",
        linewidth=1.0,
        label=f"practical margin ±{margin:g}",
    )
    ax.axvline(-margin, color="#888888", linestyle=":", linewidth=1.0)
    logreg = contrasts.get("R3_ca_vs_logreg_rna")
    if logreg is not None:
        ax.axvline(
            float(logreg["estimate"]),
            color="#b85c38",
            linestyle="-.",
            linewidth=1.4,
            label=f"R3_ca − logreg_rna ({float(logreg['estimate']):+.3f})",
        )
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("donor balanced-accuracy contrast")
    ax.set_title(
        f"Ladder CA−TC forest (outcome {data.get('outcome', '?')}; "
        f"primary ≈ {float(data['primary']['estimate']):+.4f})"
    )
    ax.legend(fontsize=7.5, loc="lower right", frameon=False)
    ax.set_xlim(-0.28, 0.16)
    fig.tight_layout()
    return _save(fig, outdir, "fig3_ladder")


def build_fig4(data: dict, outdir: Path) -> list[Path]:
    """Faithfulness: Δ log-loss per intervention with CIs (primary R3_ca)."""
    rows = [
        r
        for r in data["summary"]
        if r["arm"] == FAITH_PRIMARY_ARM and r["intervention"] in FAITH_INTERVENTIONS
    ]
    by_name = {r["intervention"]: r for r in rows}
    ordered = [by_name[name] for name in FAITH_INTERVENTIONS if name in by_name]
    if not ordered:
        raise ValueError(f"no faithfulness rows for arm {FAITH_PRIMARY_ARM}")

    labels = [r["intervention"] for r in ordered]
    estimates = [float(r["ll_drop"]) for r in ordered]
    lo_err = [float(r["ll_drop"]) - float(r["ll_drop_ci"][0]) for r in ordered]
    hi_err = [float(r["ll_drop_ci"][1]) - float(r["ll_drop"]) for r in ordered]
    used = [bool(r.get("used_by_model")) for r in ordered]
    colors = ["#1f4e79" if u else "#7a7a7a" for u in used]

    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    y = np.arange(len(labels))[::-1]
    ax.errorbar(
        estimates,
        y,
        xerr=[lo_err, hi_err],
        fmt="o",
        ecolor="#444444",
        capsize=3,
        markersize=6,
        color="none",
    )
    ax.scatter(estimates, y, c=colors, s=36, zorder=3)
    ax.axvline(0.0, color="black", linestyle="--", linewidth=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Δ donor log-loss (intervention − baseline)")
    tags = ",".join(data.get("decision", {}).get("tags", [])) or "untagged"
    ax.set_title(f"Faithfulness interventions on {FAITH_PRIMARY_ARM} ({tags})")
    ax.plot([], [], "o", color="#1f4e79", label="CI excludes 0 (used)")
    ax.plot([], [], "o", color="#7a7a7a", label="CI includes 0")
    ax.legend(fontsize=7.5, loc="lower right", frameon=False)
    fig.tight_layout()
    return _save(fig, outdir, "fig4_faithfulness")


def build_fig5(data: dict, outdir: Path) -> list[Path]:
    """Spectrum: eligible cell-type DS−CON donor effects with Holm markers."""
    eligible = set(data.get("eligible_types", []))
    rows = [r for r in data["results"] if r.get("eligible") and r["author_cell_type"] in eligible]
    rows = sorted(rows, key=lambda r: float(r["s"]["diff"]))
    if not rows:
        raise ValueError("no eligible spectrum rows to plot")

    labels = [r["author_cell_type"] for r in rows]
    estimates = [float(r["s"]["diff"]) for r in rows]
    lo_err = [float(r["s"]["diff"]) - float(r["s"]["ci_low"]) for r in rows]
    hi_err = [float(r["s"]["ci_high"]) - float(r["s"]["diff"]) for r in rows]
    sigs = [bool(r["s"].get("significant")) for r in rows]

    fig, ax = plt.subplots(figsize=(7.5, max(4.0, 0.42 * len(labels) + 1.2)))
    y = np.arange(len(labels))
    ax.errorbar(
        estimates,
        y,
        xerr=[lo_err, hi_err],
        fmt="o",
        color="#1f4e79",
        ecolor="#1f4e79",
        capsize=3,
        markersize=5.5,
    )
    for i, sig in enumerate(sigs):
        if sig:
            ax.text(
                estimates[i],
                y[i] + 0.22,
                "*",
                ha="center",
                va="bottom",
                color="#b00020",
                fontsize=14,
                fontweight="bold",
            )
    ax.axvline(0.0, color="black", linestyle="--", linewidth=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("DS − CON mean cell score (donor-level)")
    call = data.get("spectrum_call", "?")
    n_sig = sum(sigs)
    ax.set_title(f"Cell-state spectrum ({call}; {n_sig}/{len(rows)} Holm-significant)")
    fig.tight_layout()
    return _save(fig, outdir, "fig5_spectrum")


def build_fig6(data: dict, outdir: Path) -> list[Path]:
    """Per-fold AUROC mean (±SD) vs pooled AUROC for key arms."""
    arms = data.get("per_arm") or {}
    labels: list[str] = []
    means: list[float] = []
    sds: list[float] = []
    pooled: list[float] = []
    for arm in PER_FOLD_ARMS:
        row = arms.get(arm)
        if not row:
            raise ValueError(f"missing per-fold arm {arm}")
        labels.append(arm)
        means.append(float(row["per_fold_auroc_mean"]))
        sds.append(float(row["per_fold_auroc_sd"]))
        pooled.append(float(row["pooled_auroc"]))

    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.bar(
        x - width / 2,
        means,
        width,
        yerr=sds,
        color="#1f4e79",
        ecolor="#1f4e79",
        capsize=3,
        label="per-fold AUROC mean ± SD",
    )
    ax.bar(
        x + width / 2,
        pooled,
        width,
        color="#b85c38",
        label="pooled AUROC",
    )
    ax.axhline(0.5, color="black", linestyle="--", linewidth=1.0, label="chance 0.5")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("donor AUROC")
    ax.set_ylim(0.0, 1.05)
    ax.set_title("Per-fold AUROC vs pooled AUROC (canonical ladder)")
    ax.legend(fontsize=7.5, loc="lower left", frameon=False)
    fig.tight_layout()
    return _save(fig, outdir, "fig6_per_fold_auroc")


def build_fig7(data: dict, outdir: Path) -> list[Path]:
    """Detection fraction and mean CA−TC contrast vs planted δ (S4, 30 donors)."""
    per_delta = data.get("per_delta") or {}
    deltas = list(data.get("deltas") or sorted(float(k) for k in per_delta))
    if not deltas:
        raise ValueError("detectability.json missing deltas / per_delta")
    fractions: list[float] = []
    contrasts: list[float] = []
    for d in deltas:
        row = per_delta.get(str(d)) or per_delta.get(d)
        if not row:
            raise ValueError(f"missing per_delta entry for δ={d}")
        fractions.append(float(row["detection_fraction"]))
        contrasts.append(float(row["mean_contrast"]))

    threshold = float(data.get("detection_threshold") or 0.8)
    min_d = data.get("min_detectable_delta")
    title_extra = (
        f"min_detectable_delta={min_d}"
        if min_d is not None
        else "min_detectable_delta=null (not detectable up to δ=1.0)"
    )

    x = np.arange(len(deltas))
    fig, ax1 = plt.subplots(figsize=(7.2, 4.2))
    ax1.bar(x, fractions, color="#1f4e79", width=0.55, label="detection fraction")
    ax1.axhline(
        threshold,
        color="black",
        linestyle="--",
        linewidth=1.0,
        label=f"80% threshold ({threshold:g})",
    )
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(d) for d in deltas])
    ax1.set_xlabel("planted effect size δ (S4)")
    ax1.set_ylabel("detection fraction")
    ax1.set_ylim(-0.05, 1.05)
    ax1.set_title(f"Detectability at 30 donors: CA−TC CI excludes 0\n{title_extra}")

    ax2 = ax1.twinx()
    ax2.plot(x, contrasts, color="#b85c38", marker="o", linewidth=1.5, label="mean contrast")
    ax2.axhline(0.0, color="#b85c38", linestyle=":", linewidth=0.8)
    ax2.set_ylabel("mean CA−TC donor BA contrast")

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2[:1], l1 + l2[:1], fontsize=7.5, loc="upper right", frameon=False)
    fig.tight_layout()
    return _save(fig, outdir, "fig7_detectability")


def _try_build(
    label: str,
    source: Path,
    builder,
    outdir: Path,
    *,
    hard_fail: bool,
) -> int:
    """Build one figure; skip+record if source missing unless hard_fail."""
    try:
        data = load_source(source) if source is not None else None
        written = builder(data, outdir) if data is not None else builder(outdir)
        for path in written:
            print(f"wrote {path}")
        return 0
    except MissingSourceError as exc:
        if hard_fail:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        SKIPPED_FIGURES.append(f"{label}: {exc}")
        print(f"skipped {label}: {exc}")
        return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build P22-NN paper figures.")
    ap.add_argument(
        "--only",
        choices=(
            "schematic",
            "planted",
            "ladder",
            "faithfulness",
            "spectrum",
            "per_fold",
            "detectability",
            "all",
        ),
        default="all",
    )
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = ap.parse_args(argv)

    SKIPPED_FIGURES.clear()
    only = args.only

    try:
        if only in ("schematic", "all"):
            for path in build_fig1(args.outdir):
                print(f"wrote {path}")
        if only in ("planted", "all"):
            # P2 contract: planted missing → exit 2 (not silent skip).
            data = load_source(DEFAULT_PLANTED)
            for path in build_fig2(data, args.outdir):
                print(f"wrote {path}")
    except MissingSourceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if only in ("ladder", "all"):
        rc = _try_build(
            "fig3_ladder",
            DEFAULT_LADDER,
            build_fig3,
            args.outdir,
            hard_fail=(only == "ladder"),
        )
        if rc:
            return rc
    if only in ("faithfulness", "all"):
        rc = _try_build(
            "fig4_faithfulness",
            DEFAULT_FAITH,
            build_fig4,
            args.outdir,
            hard_fail=(only == "faithfulness"),
        )
        if rc:
            return rc
    if only in ("spectrum", "all"):
        rc = _try_build(
            "fig5_spectrum",
            DEFAULT_SPECTRUM,
            build_fig5,
            args.outdir,
            hard_fail=(only == "spectrum"),
        )
        if rc:
            return rc
    if only in ("per_fold", "all"):
        rc = _try_build(
            "fig6_per_fold_auroc",
            DEFAULT_PER_FOLD,
            build_fig6,
            args.outdir,
            hard_fail=(only == "per_fold"),
        )
        if rc:
            return rc
    if only in ("detectability", "all"):
        rc = _try_build(
            "fig7_detectability",
            DEFAULT_DETECT,
            build_fig7,
            args.outdir,
            hard_fail=(only == "detectability"),
        )
        if rc:
            return rc

    if only == "all":
        for line in SKIPPED_FIGURES:
            print(f"skipped {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
