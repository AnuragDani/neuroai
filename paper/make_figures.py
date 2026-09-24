#!/usr/bin/env python3
"""Figure builder for the P22-NN paper (decision-tree N25).

Currently builds Fig 2 (planted-signal benchmark) from
``docs/nn_v2/planted_benchmark.json``:

  * scenario x model balanced-accuracy heatmap at delta = 1.0;
  * balanced accuracy vs delta curves for scenarios S4 and S5.

Later N25 modes (Fig 1, 3, 4, 5) are added separately. Missing source JSON fails
with a clear message and a non-zero exit code so the caller can skip/renumber.

Usage:
    python paper/make_figures.py --only planted [--outdir paper/figures]
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


class MissingSourceError(FileNotFoundError):
    """Raised when a figure's source JSON is absent."""


def load_source(path: Path) -> dict:
    if not path.exists():
        raise MissingSourceError(f"source JSON not found: {path}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _ba(data: dict, scenario: str, delta: float, model: str) -> float:
    return data["regime_labels"][f"{scenario}@{delta}"]["mean_balanced_accuracy"][model]


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

    outdir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for ext in ("png", "pdf"):
        path = outdir / f"fig2_planted.{ext}"
        fig.savefig(path, dpi=300)
        written.append(path)
    plt.close(fig)
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build P22-NN paper figures.")
    ap.add_argument("--only", choices=("planted", "all"), default="all")
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = ap.parse_args(argv)

    try:
        if args.only in ("planted", "all"):
            data = load_source(DEFAULT_PLANTED)
            written = build_fig2(data, args.outdir)
            for path in written:
                print(f"wrote {path}")
    except MissingSourceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
