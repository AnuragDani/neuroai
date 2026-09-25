#!/usr/bin/env python3
"""Figure builder for the P22-NN paper (decision-tree N25).

Builds:

  * Fig 1 -- architecture / ladder schematic (no external source JSON);
  * Fig 2 -- planted-signal benchmark from ``docs/nn_v2/planted_benchmark.json``
    (scenario x model heatmap at delta = 1.0; accuracy vs delta for S4 and S5).

Figures 3-5 are skipped: their source evidence is absent or not estimable (see
``SKIPPED_FIGURES``). Missing source JSON fails with a clear message and a
non-zero exit code so the caller can skip/renumber.

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
DEFAULT_OUTDIR = _HERE / "figures"

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

# Figures whose evidence sources are absent / not estimable; recorded, renumbered.
SKIPPED_FIGURES = (
    "fig3_ladder (N10 BLOCKED: reports/generated/nn_20260923/ladder absent)",
    "fig4_faithfulness (N13 BLOCKED: interventions N/A, no numeric delta)",
    "fig5_spectrum (N16 NOT_ESTIMABLE: input_missing)",
)


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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build P22-NN paper figures.")
    ap.add_argument("--only", choices=("schematic", "planted", "all"), default="all")
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = ap.parse_args(argv)

    try:
        if args.only in ("schematic", "all"):
            for path in build_fig1(args.outdir):
                print(f"wrote {path}")
        if args.only in ("planted", "all"):
            data = load_source(DEFAULT_PLANTED)
            for path in build_fig2(data, args.outdir):
                print(f"wrote {path}")
    except MissingSourceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.only == "all":
        for line in SKIPPED_FIGURES:
            print(f"skipped {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
