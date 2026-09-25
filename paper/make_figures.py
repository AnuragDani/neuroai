import json
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def make_fig1(out_prefix):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.axis('off')
    
    # Simple schematic
    # Draw boxes
    boxes = [
        ("RNA Input", 0.1, 0.7),
        ("ATAC Input", 0.6, 0.7),
        ("RNA Encoder", 0.1, 0.5),
        ("ATAC Encoder", 0.6, 0.5),
        ("Cross Attention", 0.35, 0.3),
        ("Prediction", 0.35, 0.1)
    ]
    
    for text, x, y in boxes:
        rect = patches.Rectangle((x, y), 0.3, 0.1, linewidth=1, edgecolor='black', facecolor='lightgray')
        ax.add_patch(rect)
        ax.text(x + 0.15, y + 0.05, text, ha='center', va='center', fontsize=10)
        
    # Arrows
    arrows = [
        (0.25, 0.7, 0.25, 0.6),
        (0.75, 0.7, 0.75, 0.6),
        (0.25, 0.5, 0.4, 0.4),
        (0.75, 0.5, 0.6, 0.4),
        (0.5, 0.3, 0.5, 0.2)
    ]
    for x1, y1, x2, y2 in arrows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->"))
        
    plt.savefig(f"{out_prefix}.png", dpi=300, bbox_inches='tight')
    plt.savefig(f"{out_prefix}.pdf", bbox_inches='tight')
    plt.close()

def make_fig2(out_prefix):
    path = "docs/nn_v2/planted_benchmark.json"
    if not os.path.exists(path):
        print(f"Skipping {out_prefix}, missing {path}")
        return
        
    with open(path) as f:
        data = json.load(f)
        
    regimes = data.get("regime_labels", {})
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Heatmap for delta=1.0
    scenarios = ["S0@0.0", "S1@1.0", "S2@1.0", "S3@1.0", "S4@1.0", "S5@1.0"]
    models = ["cross_attention", "gated_fusion", "logreg_concat", "rna_atac_concat", "token_concat"]
    
    heatmap_data = np.zeros((len(scenarios), len(models)))
    for i, s in enumerate(scenarios):
        if s in regimes:
            for j, m in enumerate(models):
                heatmap_data[i, j] = regimes[s]["mean_balanced_accuracy"].get(m, np.nan)
                
    im = ax1.imshow(heatmap_data, cmap="viridis", vmin=0.3, vmax=1.0)
    ax1.set_xticks(np.arange(len(models)))
    ax1.set_yticks(np.arange(len(scenarios)))
    ax1.set_xticklabels(models, rotation=45, ha="right")
    ax1.set_yticklabels([s.split("@")[0] for s in scenarios])
    ax1.set_title("Benchmark Heatmap (delta=1.0)")
    fig.colorbar(im, ax=ax1)
    
    # Lines for S4/S5
    deltas = [0.25, 0.5, 1.0]
    for s_name in ["S4", "S5"]:
        for m in models:
            y = []
            for d in deltas:
                key = f"{s_name}@{d}"
                if key in regimes:
                    y.append(regimes[key]["mean_balanced_accuracy"].get(m, np.nan))
                else:
                    y.append(np.nan)
            if not all(np.isnan(y)):
                ax2.plot(deltas, y, marker='o', label=f"{s_name} {m}")
                
    ax2.set_xlabel("Delta")
    ax2.set_ylabel("Balanced Accuracy")
    ax2.set_title("S4 & S5 by Delta")
    # ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    plt.savefig(f"{out_prefix}.png", dpi=300, bbox_inches='tight')
    plt.savefig(f"{out_prefix}.pdf", bbox_inches='tight')
    plt.close()

def make_fig3(out_prefix):
    path = "docs/nn_v2/ladder_summary.json"
    if not os.path.exists(path):
        print(f"Skipping {out_prefix}, missing {path}")
        return
        
    with open(path) as f:
        data = json.load(f)
        
    fig, ax = plt.subplots(figsize=(6, 4))
    
    if "primary" in data:
        est = data["primary"].get("estimate", 0)
        ci = data["primary"].get("ci", [0, 0])
        model = data["primary"].get("model", "R3_ca")
        ref = data["primary"].get("reference", "R3_tc")
        
        ax.errorbar([est], [0], xerr=[[est - ci[0]], [ci[1] - est]], fmt='o', label=f"{model} vs {ref}")
        
    ax.axvline(0, color='black', linestyle='--')
    ax.set_yticks([0])
    ax.set_yticklabels(["Primary Contrast"])
    ax.set_xlabel("Difference in Balanced Accuracy")
    ax.set_title("Ladder Forest Plot")
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(f"{out_prefix}.png", dpi=300, bbox_inches='tight')
    plt.savefig(f"{out_prefix}.pdf", bbox_inches='tight')
    plt.close()

def make_fig4_spectrum(out_prefix):
    path = "docs/nn_v2/spectrum.json"
    if not os.path.exists(path):
        print(f"Skipping {out_prefix}, missing {path}")
        return
        
    with open(path) as f:
        data = json.load(f)
        
    results = data.get("results", [])
    if not results:
        print(f"No results in {path}")
        return
        
    cell_types = []
    diffs = []
    ci_lows = []
    ci_highs = []
    sigs = []
    
    for r in results:
        cell_types.append(r["author_cell_type"])
        diffs.append(r["s"]["diff"])
        ci_lows.append(r["s"]["ci_low"])
        ci_highs.append(r["s"]["ci_high"])
        sigs.append(r["s"]["significant"])
        
    fig, ax = plt.subplots(figsize=(8, max(4, len(cell_types)*0.4)))
    
    y = np.arange(len(cell_types))
    xerr = [np.array(diffs) - np.array(ci_lows), np.array(ci_highs) - np.array(diffs)]
    
    ax.errorbar(diffs, y, xerr=xerr, fmt='o')
    
    for i, sig in enumerate(sigs):
        if sig:
            ax.text(diffs[i], y[i] + 0.2, "*", ha='center', va='bottom', color='red', fontsize=14)
            
    ax.axvline(0, color='black', linestyle='--')
    ax.set_yticks(y)
    ax.set_yticklabels(cell_types)
    ax.set_xlabel("DS - CON (Donor Effect)")
    ax.set_title("Cell-State Spectrum")
    
    plt.tight_layout()
    plt.savefig(f"{out_prefix}.png", dpi=300, bbox_inches='tight')
    plt.savefig(f"{out_prefix}.pdf", bbox_inches='tight')
    plt.close()

def main():
    os.makedirs("paper/figures", exist_ok=True)
    make_fig1("paper/figures/fig1_architecture")
    make_fig2("paper/figures/fig2_planted")
    make_fig3("paper/figures/fig3_ladder")
    
    faith_blocked = False
    if os.path.exists("docs/nn_v2/faithfulness.json"):
        with open("docs/nn_v2/faithfulness.json") as f:
            fdata = json.load(f)
            if fdata.get("status") == "BLOCKED":
                faith_blocked = True
                
    if faith_blocked:
        print("Faithfulness task BLOCKED. Skipping fig4_faithfulness, renumbering spectrum to fig4.")
        make_fig4_spectrum("paper/figures/fig4_spectrum")
    else:
        make_fig4_spectrum("paper/figures/fig5_spectrum")

if __name__ == "__main__":
    main()
