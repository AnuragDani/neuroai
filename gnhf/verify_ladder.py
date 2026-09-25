#!/usr/bin/env python3
"""Driver-owned, independent check of the N10 ladder. Agents cannot edit gnhf/.

Recomputes, from the raw fold files, each arm's donor balanced accuracy (pooled per repeat,
then averaged over repeats, as in repeated_primary_contrast) and the primary R3_ca - R3_tc
contrast with a 1,000-draw donor bootstrap. Compares with docs/nn_v2/ladder_summary.json and
checks protocol conformance and sanity. Writes docs/nn_v2/ladder_verification.json.

Usage: verify_ladder.py [--run DIR] [--summary FILE] [--protocol FILE] [--write]
Exit 0 only when every check passes.
"""
import argparse
import collections
import glob
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ba(pairs):
    pos = [p >= 0.5 for y, p in pairs if y == 1]
    neg = [p < 0.5 for y, p in pairs if y == 0]
    return (sum(pos) / len(pos) + sum(neg) / len(neg)) / 2 if pos and neg else None


def auroc(pairs):
    pos = [p for y, p in pairs if y == 1]
    neg = [p for y, p in pairs if y == 0]
    if not pos or not neg:
        return None
    wins = sum((a > b) + 0.5 * (a == b) for a in pos for b in neg)
    return wins / (len(pos) * len(neg))


def load(run):
    arms = collections.defaultdict(dict)  # arm -> repeat -> donor -> (y, p)
    params = collections.defaultdict(set)
    for f in glob.glob(str(Path(run) / "folds" / "*.json")):
        d = json.loads(Path(f).read_text())
        rep = arms[d["arm"]].setdefault(d["repeat"], {})
        for i, y, p in zip(d["donor_ids"], d["donor_labels"], d["donor_probabilities"], strict=True):
            rep[str(i)] = (int(y), float(p))
        params[d["arm"]].add(d.get("parameter_count"))
    return arms, params


def arm_metric(arms, arm, fn, donors=None):
    vals = [fn([dd[k] for k in (donors or dd) if k in dd]) for dd in arms[arm].values()]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(ROOT / "reports/generated/nn_20260923/ladder"))
    ap.add_argument("--summary", default=str(ROOT / "docs/nn_v2/ladder_summary.json"))
    ap.add_argument("--protocol", default=str(ROOT / "configs/nn_protocol_v2_2026-09-23.json"))
    ap.add_argument("--counts", default=str(ROOT / "docs/nn_v2/parameter_counts.json"))
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    arms, params = load(a.run)
    proto = json.loads(Path(a.protocol).read_text())
    problems, notes = [], []
    expected_arms = proto["arms"]
    missing = [x for x in expected_arms if x not in arms]
    if missing:
        problems.append(f"arms missing from fold files: {missing}")
    for arm in arms:
        n_reps = len(arms[arm])
        n_don = [len(dd) for dd in arms[arm].values()]
        if n_reps != 5 or any(n != 30 for n in n_don):
            problems.append(f"{arm}: {n_reps} repeats, donors per repeat {n_don} (expected 5 x 30)")
    per_arm = {arm: {"balanced_accuracy": arm_metric(arms, arm, ba), "auroc": arm_metric(arms, arm, auroc),
                     "parameter_count": sorted(x for x in params[arm] if x is not None)} for arm in sorted(arms)}
    ca, tc = "R3_ca", "R3_tc"
    primary = None
    if ca in arms and tc in arms:
        donors = sorted(next(iter(arms[ca].values())))
        est = arm_metric(arms, ca, ba) - arm_metric(arms, tc, ba)
        rng, draws = random.Random(22), []
        for _ in range(1000):
            s = [rng.choice(donors) for _ in donors]
            x, y = arm_metric(arms, ca, ba, s), arm_metric(arms, tc, ba, s)
            if x is not None and y is not None:
                draws.append(x - y)
        draws.sort()
        lo, hi = draws[int(0.025 * len(draws))], draws[int(0.975 * len(draws)) - 1]
        primary = {"estimate": est, "ci": [lo, hi], "valid_draws": len(draws), "margin": 0.07,
                   "advantage": est >= 0.07 and lo > 0}
        if hi - lo <= 0:
            problems.append("primary CI has zero width: bootstrap is degenerate")
    # summary agreement
    try:
        summ = json.loads(Path(a.summary).read_text())
        sp_ = summ.get("primary", {})
        if primary and (abs(float(sp_.get("estimate", 1e9)) - primary["estimate"]) > 1e-6):
            problems.append(f"summary primary.estimate {sp_.get('estimate')} != recomputed {primary['estimate']:.6f}")
        ci = sp_.get("ci") or [0, 0]
        if primary and max(abs(ci[0] - primary["ci"][0]), abs(ci[1] - primary["ci"][1])) > 0.02:
            problems.append(f"summary primary.ci {ci} disagrees with recomputed {primary['ci']} (tolerance 0.02)")
    except (OSError, ValueError, TypeError) as exc:
        problems.append(f"cannot read summary: {exc}")
    # protocol conformance: parameter counts vs the frozen N9 record (amendment may explain)
    frozen = json.loads(Path(a.counts).read_text()).get("counts", {})
    amendments = sorted(glob.glob(str(ROOT / "configs/nn_protocol_v2_amendment_*.json")))
    width_keys = ("n_hvg", "hidden_dim", "embed_dim", "n_tokens", "feature_budget", "cap_per_donor", "n_params")
    # ponytail: an amendment excuses a size change only if it names a width field; text match, not a schema.
    width_amend = [f for f in amendments if any(k in Path(f).read_text() for k in width_keys)]
    for arm, rec in frozen.items():
        want = (rec or {}).get("n_params") if isinstance(rec, dict) else None
        got = per_arm.get(arm, {}).get("parameter_count")
        if want and got and all(abs(g - want) / want > 0.01 for g in got):
            msg = f"{arm}: fold parameter_count {got} vs frozen {want}"
            (notes if width_amend else problems).append(msg + (f" (amended: {width_amend})" if width_amend else
                                                                 " - no amendment names the changed width"))
    # sanity: a constant predictor must score 0.5 per fold; pooled scores below 0.5 mean pooling artefact
    maj = per_arm.get("majority", {}).get("balanced_accuracy")
    if maj is not None and maj < 0.45:
        notes.append(f"majority pooled BA {maj:.3f} < 0.5: fold-wise thresholds pooled across folds depress BA "
                     "(stratified folds flip the training majority); report AUROC alongside BA")
    chr21 = per_arm.get("chr21_dosage", {}).get("auroc")
    truth = ROOT / "docs/nn_v2/chr21_sanity.json"
    gt = json.loads(truth.read_text())["auroc_unsupervised"] if truth.exists() else None
    if chr21 is None or chr21 < 0.85:
        problems.append(f"chr21_dosage AUROC {chr21} < 0.85 while the model-free donor chr21 share gives AUROC {gt} "
                        "(gnhf/chr21_sanity.py): the pipeline misaligns labels, rows, genes or probabilities")
    out = {"record_type": "ladder_verification", "primary_recomputed": primary, "per_arm": per_arm,
           "problems": problems, "notes": notes, "amendments": amendments, "verdict": "PASS" if not problems else "FAIL"}
    if a.write:
        (ROOT / "docs/nn_v2/ladder_verification.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("verdict", "primary_recomputed", "problems", "notes")}, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
