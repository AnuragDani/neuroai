#!/usr/bin/env python3
"""Driver-owned ground truth: per-donor chr21 share of raw RNA counts, no model.

Trisomy 21 raises chr21 expression; this AUROC must be high if labels and genes are right.
Reads raw/X in row chunks (CSR) so memory stays small. Writes docs/nn_v2/chr21_sanity.json.
Usage: .venv-p22/bin/python gnhf/chr21_sanity.py [--h5ad PATH] [--write]
"""
import argparse
import json
from pathlib import Path

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
H5AD = "/Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"


def cat(g, key):
    node = g[key]
    if isinstance(node, h5py.Group):
        cats = [c.decode() if isinstance(c, bytes) else str(c) for c in node["categories"][:]]
        return np.asarray(cats, dtype=object)[node["codes"][:]]
    return np.asarray([c.decode() if isinstance(c, bytes) else str(c) for c in node[:]], dtype=object)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--h5ad", default=H5AD)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    with h5py.File(a.h5ad, "r") as f:
        chrom = cat(f["raw/var"], "seqnames")
        mask = np.isin(chrom, ["chr21", "21"])
        donor, disease = cat(f["obs"], "donor_id"), cat(f["obs"], "disease")
        X = f["raw/X"]
        indptr = X["indptr"][:]
        n = len(indptr) - 1
        tot, c21 = np.zeros(n), np.zeros(n)
        step = 20000
        for s in range(0, n, step):
            e = min(n, s + step)
            lo, hi = indptr[s], indptr[e]
            data, idx = X["data"][lo:hi].astype(np.float64), X["indices"][lo:hi]
            rows = np.repeat(np.arange(s, e), np.diff(indptr[s:e + 1]))
            np.add.at(tot, rows, data)
            np.add.at(c21, rows, data * mask[idx])
    frac = np.divide(c21, tot, out=np.zeros(n), where=tot > 0)
    donors = sorted(set(donor))
    rec = []
    for d in donors:
        m = donor == d
        rec.append({"donor": d, "ds": int(disease[m][0] == "complete trisomy 21"),
                    "chr21_fraction_pooled": float(c21[m].sum() / tot[m].sum()),
                    "chr21_fraction_cell_mean": float(frac[m].mean()), "n_cells": int(m.sum())})
    pos = [r["chr21_fraction_pooled"] for r in rec if r["ds"]]
    neg = [r["chr21_fraction_pooled"] for r in rec if not r["ds"]]
    auroc = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg) / (len(pos) * len(neg))
    out = {"record_type": "chr21_sanity", "n_chr21_genes": int(mask.sum()), "n_donors": len(rec),
           "auroc_unsupervised": auroc, "ds_mean": float(np.mean(pos)), "con_mean": float(np.mean(neg)),
           "ratio_ds_over_con": float(np.mean(pos) / np.mean(neg)), "donors": rec}
    if a.write:
        (ROOT / "docs/nn_v2/chr21_sanity.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "donors"}, indent=2))


if __name__ == "__main__":
    main()
