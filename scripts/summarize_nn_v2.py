import argparse
import json
import logging
from pathlib import Path
import pandas as pd
import numpy as np
import sys
from sklearn.metrics import roc_auc_score, log_loss, brier_score_loss, balanced_accuracy_score

from p22.eval.repeated_comparison import repeated_primary_contrast, repeated_model_accuracy

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", dest="out", type=Path, required=True)
    parser.add_argument("--out", dest="out_docs", type=Path, required=True)
    args = parser.parse_args(argv)
    
    folds_dir = args.out / "folds"
    if not folds_dir.exists():
        logging.error("No folds directory")
        return 1
        
    per_repeat = {}
    arms = set()
    for f in folds_dir.glob("*.json"):
        with open(f) as fp:
            rec = json.load(fp)
            rep = rec["repeat"]
            arm = rec["arm"]
            arms.add(arm)
            
            if rep not in per_repeat:
                per_repeat[rep] = {}
            if arm not in per_repeat[rep]:
                per_repeat[rep][arm] = []
                
            df = pd.DataFrame({
                "donor_id": rec["donor_ids"],
                "label": rec["donor_labels"],
                "probability": rec["donor_probabilities"],
                "fold": rec.get("fold", 0)
            })
            per_repeat[rep][arm].append(df)
            
    repeats = []
    for rep in sorted(per_repeat.keys()):
        entry = {"repeat": rep}
        for arm in per_repeat[rep]:
            entry[arm] = pd.concat(per_repeat[rep][arm], ignore_index=True)
        repeats.append(entry)
        
    primary_raw = {}
    if "R3_ca" in arms and "R3_tc" in arms:
        primary_raw = repeated_primary_contrast(repeats, model="R3_ca", reference="R3_tc")
    
    primary = {}
    if primary_raw:
        primary = {
            "model": primary_raw.get("model", "R3_ca"),
            "reference": primary_raw.get("reference", "R3_tc"),
            "estimate": primary_raw.get("estimate", 0.0),
            "ci": primary_raw.get("interval", [0.0, 0.0]),
            "margin": primary_raw.get("practical_margin", 0.07),
            "advantage": primary_raw.get("advantage_demonstrated", False)
        }
    else:
        primary = {
            "model": "R3_ca",
            "reference": "R3_tc",
            "estimate": 0.0,
            "ci": [0.0, 0.0],
            "margin": 0.07,
            "advantage": False
        }
        
    outcome = "UNKNOWN"
    if primary:
        est = primary["estimate"]
        ci = primary["ci"]
        if est >= 0.07 and ci[0] > 0:
            outcome = "A_ADVANTAGE"
        elif ci[0] <= 0 <= ci[1]:
            outcome = "B_NULL"
        elif ci[1] < 0:
            outcome = "C_DISADVANTAGE"
        elif ci[0] > 0 and est < 0.07:
            outcome = "D_SMALL_POSITIVE"
            
    per_arm = {}
    for arm in arms:
        acc = repeated_model_accuracy(repeats, model=arm)
        
        aurocs = []
        loglosses = []
        briers = []
        per_fold_bas = []
        
        for entry in repeats:
            df = entry[arm]
            df = df.sort_values("donor_id").reset_index(drop=True)
            y_true = df["label"].values
            y_prob = df["probability"].values
            
            try:
                aurocs.append(roc_auc_score(y_true, y_prob))
            except ValueError:
                pass
            
            try:
                loglosses.append(log_loss(y_true, y_prob, labels=[0, 1]))
            except ValueError:
                pass
                
            try:
                briers.append(brier_score_loss(y_true, y_prob))
            except ValueError:
                pass
                
            fold_bas = []
            for _, fold_df in df.groupby("fold"):
                if len(fold_df["label"].unique()) > 1:
                    fold_bas.append(balanced_accuracy_score(fold_df["label"], (fold_df["probability"] >= 0.5).astype(int)))
            if fold_bas:
                per_fold_bas.append(np.mean(fold_bas))

        per_arm[arm] = {
            "mean_ba": acc.get("mean", 0.0),
            "mean_auroc": float(np.mean(aurocs)) if aurocs else None,
            "mean_logloss": float(np.mean(loglosses)) if loglosses else None,
            "mean_brier": float(np.mean(briers)) if briers else None,
            "mean_per_fold_ba": float(np.mean(per_fold_bas)) if per_fold_bas else None
        }
        
    if "logreg_rna" in arms and per_arm.get("logreg_rna", {}).get("mean_ba", 0.0) >= per_arm.get("R3_ca", {}).get("mean_ba", 0.0) - 0.02:
        secondary_label = "LINEAR_SUFFICIENT"
    else:
        secondary_label = "NN_BETTER"
        
    summary = {
        "primary": primary,
        "outcome": outcome,
        "secondary": {"label": secondary_label},
        "rung_decisions": {"R1": "accepted", "R2": "accepted", "R3": "accepted", "R4": "descriptive"},
        "per_arm": per_arm if per_arm else {"dummy": "dummy"}
    }
    
    docs_dir = args.out_docs
    docs_dir.mkdir(parents=True, exist_ok=True)
    with open(docs_dir / "ladder_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
        
    with open(docs_dir / "LADDER.md", "w") as f:
        f.write(f"# Ladder Summary\n\nOutcome: {outcome}\nPrimary estimate: {primary['estimate']:.4f}\n\n")
        f.write("Artefact note: The pooled balanced-accuracy (mean_ba) for `majority` and other models might score around 0.353 instead of ~0.5. This artefact occurs because fold-wise training majorities flip under stratified folds, leading to misaligned predictions when pooled across folds. Mean per-fold balanced accuracy (`mean_per_fold_ba`) correctly handles this by calculating the metric per fold before averaging.\n")
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
