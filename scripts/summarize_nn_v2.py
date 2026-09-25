import argparse
import json
import logging
from pathlib import Path
import pandas as pd
import numpy as np
import sys

from p22.eval.repeated_comparison import repeated_primary_contrast

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    args = parser.parse_args(argv)
    
    folds_dir = args.out / "folds"
    if not folds_dir.exists():
        logging.error("No folds directory")
        return 1
        
    # Group by repeat
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
                "probability": rec["donor_probabilities"]
            })
            per_repeat[rep][arm].append(df)
            
    repeats = []
    for rep in sorted(per_repeat.keys()):
        entry = {"repeat": rep}
        for arm in per_repeat[rep]:
            entry[arm] = pd.concat(per_repeat[rep][arm], ignore_index=True)
        repeats.append(entry)
        
    # Wait, the summary uses repeated_primary_contrast(repeats, model="R3_ca", reference="R3_tc")
    primary = {}
    if "R3_ca" in arms and "R3_tc" in arms:
        primary = repeated_primary_contrast(repeats, model="R3_ca", reference="R3_tc")
        
    # Outcome logic
    outcome = "UNKNOWN"
    if primary:
        est = primary.get("estimate", 0)
        ci = primary.get("interval", [0, 0])
        if est >= 0.07 and ci[0] > 0:
            outcome = "A_ADVANTAGE"
        elif ci[0] <= 0 <= ci[1]:
            outcome = "B_NULL"
        elif ci[1] < 0:
            outcome = "C_DISADVANTAGE"
        elif ci[0] > 0 and est < 0.07:
            outcome = "D_SMALL_POSITIVE"
            
    # Secondary linear check
    if "logreg_rna" in arms or "logreg_concat" in arms:
        # simplistic check for LINEAR_SUFFICIENT, would calculate actual mean BAs
        pass
        
    summary = {
        "primary": primary,
        "outcome": outcome,
        "rung_decisions": {},
        "per_arm": {}
    }
    
    docs_dir = Path("docs/nn_v2")
    docs_dir.mkdir(parents=True, exist_ok=True)
    with open(docs_dir / "ladder_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
        
    with open(docs_dir / "LADDER.md", "w") as f:
        f.write("# Ladder Summary\n\n")
        f.write(f"Outcome: {outcome}\n")
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
