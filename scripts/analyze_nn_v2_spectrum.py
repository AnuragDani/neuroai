"""N16 cell-state spectrum analysis.

Donor-unit readout of where the DS model signal lives across author cell types.
Consumes the N15 per-cell export (``cell_scores.csv.gz``). NumPy/SciPy only.

If the N15 export is absent (N15 BLOCKED) the script writes a ``NOT_ESTIMABLE``
spectrum document and exits 0; it never fabricates a table.

Usage:
    PYTHONPATH=src:scripts $PY scripts/analyze_nn_v2_spectrum.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
CELL_SCORES = ROOT / "reports/generated/nn_20260923/spectrum/cell_scores.csv.gz"
DONOR_MEANS = ROOT / "docs/nn_v2/donor_celltype_scores.csv.gz"
OUT_JSON = ROOT / "docs/nn_v2/spectrum.json"
OUT_MD = ROOT / "docs/nn_v2/SPECTRUM.md"

DS_LABEL = 1
CON_LABEL = 0

# Support floor: a group is eligible for a cell type only if at least this many
# donors carry at least this many cells of that type.
MIN_CELLS_PER_DONOR = 20
MIN_DONORS_PER_GROUP = 8

# Stage strata used for the stratified donor-label permutation.
STAGE_BINS = ((11, 13, "PCW11_12"), (13, 17, "PCW13_16"), (17, 21, "PCW17_20"))

CONFOUND_COLUMNS = {
    "chr21_dosage": "chr21_dosage",
    "dev_PCW": "dev_PCW",
    "log_nCount_RNA": "log_nCount_RNA",
    "log_nCount_ATAC": "log_nCount_ATAC",
}


def holm_adjust(pvals) -> np.ndarray:
    """Holm-Bonferroni step-down adjustment; NaNs stay NaN."""
    p = np.asarray(pvals, dtype=float)
    out = np.full(p.shape, np.nan, dtype=float)
    ok = np.where(~np.isnan(p))[0]
    if ok.size == 0:
        return out
    order = ok[np.argsort(p[ok], kind="mergesort")]
    m = order.size
    running = 0.0
    adjusted = np.empty(m, dtype=float)
    for rank, idx in enumerate(order):
        raw = min(1.0, (m - rank) * p[idx])
        running = max(running, raw)
        adjusted[rank] = running
    out[order] = adjusted
    return out


def bootstrap_diff_ci(a, b, n_boot: int, seed: int, alpha: float = 0.05):
    """Percentile bootstrap CI for mean(a) - mean(b), resampling donors."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size == 0 or b.size == 0:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx_a = rng.integers(0, a.size, size=(n_boot, a.size))
    idx_b = rng.integers(0, b.size, size=(n_boot, b.size))
    diffs = a[idx_a].mean(axis=1) - b[idx_b].mean(axis=1)
    lo, hi = np.percentile(diffs, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def _diff(a, b) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size == 0 or b.size == 0:
        return float("nan")
    return float(a.mean() - b.mean())


def permutation_p(a, b, n_perm: int, seed: int) -> float:
    """Two-sided donor-label permutation p for mean(a) - mean(b).

    Labels are permuted among donors (without strata) when strata is None;
    callers that need stratification call ``permutation_p_stratified``.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size == 0 or b.size == 0:
        return float("nan")
    observed = abs(_diff(a, b))
    pool = np.concatenate([a, b])
    n_a = a.size
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(n_perm):
        perm = rng.permutation(pool)
        if abs(_diff(perm[:n_a], perm[n_a:])) >= observed:
            count += 1
    return float((1 + count) / (1 + n_perm))


def permutation_p_stratified(values, labels, groups, n_perm: int, seed: int) -> float:
    """Two-sided permutation p with labels permuted within each stratum.

    ``values`` and ``groups`` are donor-level arrays aligned to ``labels``
    (0/1). The test statistic is mean(values | label=1) - mean(values | label=0).
    """
    values = np.asarray(values, dtype=float)
    labels = np.asarray(labels, dtype=int)
    groups = np.asarray(groups, dtype=object)
    if values.size == 0:
        return float("nan")
    observed = abs(_diff(values[labels == 1], values[labels == 0]))
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(n_perm):
        shuffled = labels.copy()
        for stratum in np.unique(groups):
            idx = np.where(groups == stratum)[0]
            shuffled[idx] = rng.permutation(shuffled[idx])
        if abs(_diff(values[shuffled == 1], values[shuffled == 0])) >= observed:
            count += 1
    return float((1 + count) / (1 + n_perm))


def derive_stage(dev_pcw) -> np.ndarray:
    """Map a development PCW value to the frozen stage stratum label."""
    pcw = np.asarray(dev_pcw, dtype=float)
    out = np.full(pcw.shape, "unknown", dtype=object)
    for lo, hi, name in STAGE_BINS:
        out[(pcw >= lo) & (pcw < hi)] = name
    return out


def _support_ok(counts: pd.Series) -> bool:
    """True if at least MIN_DONORS_PER_GROUP donors carry >= MIN_CELLS_PER_DONOR."""
    return int((counts >= MIN_CELLS_PER_DONOR).sum()) >= MIN_DONORS_PER_GROUP


def eligible_types(cells: pd.DataFrame) -> tuple[list[str], list[dict]]:
    """Return (eligible author_cell_types, exclusion records)."""
    eligible = []
    excluded = []
    for ctype, block in cells.groupby("author_cell_type", sort=True):
        n_ds_donors = block.loc[block["label"] == DS_LABEL, "donor"].nunique()
        n_con_donors = block.loc[block["label"] == CON_LABEL, "donor"].nunique()
        counts_ds = block.loc[block["label"] == DS_LABEL].groupby("donor").size()
        counts_con = block.loc[block["label"] == CON_LABEL].groupby("donor").size()
        ok_ds = _support_ok(counts_ds)
        ok_con = _support_ok(counts_con)
        if ok_ds and ok_con:
            eligible.append(str(ctype))
        else:
            excluded.append(
                {
                    "author_cell_type": str(ctype),
                    "n_cells": int(block.shape[0]),
                    "n_ds_donors": int(n_ds_donors),
                    "n_con_donors": int(n_con_donors),
                    "reason": "support_floor",
                }
            )
    return eligible, excluded


def _donor_means(block: pd.DataFrame, value_col: str, donor_col: str = "donor") -> pd.Series:
    return block.groupby(donor_col)[value_col].mean()


def _spearman(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return float("nan"), float("nan")
    rho, p = stats.spearmanr(x, y)
    return float(rho), float(p)


def _residualize(values: np.ndarray, covariates: np.ndarray) -> np.ndarray:
    """OLS residuals of values on covariates (with intercept)."""
    values = np.asarray(values, dtype=float)
    covariates = np.asarray(covariates, dtype=float)
    design = np.column_stack([np.ones(values.size), covariates])
    beta, *_ = np.linalg.lstsq(design, values, rcond=None)
    return values - design @ beta


def analyze_type(block: pd.DataFrame, eligible: bool, n_boot: int, n_perm: int, seed: int):
    """Full spectrum record for one author cell type."""
    donor_rows = block.groupby("donor").agg(
        label=("label", "first"),
        stage=("stage", "first"),
        s=("s_mean", "mean"),
        a=("a_mean", "mean"),
        **{name: (col, "mean") for name, col in CONFOUND_COLUMNS.items() if col in block.columns},
    )
    ds = donor_rows.loc[donor_rows["label"] == DS_LABEL]
    con = donor_rows.loc[donor_rows["label"] == CON_LABEL]
    rec: dict = {
        "author_cell_type": str(block["author_cell_type"].iloc[0]) if not block.empty else None,
        "eligible": bool(eligible),
        "n_cells": int(block.shape[0]),
        "n_donors_ds": int(ds.shape[0]),
        "n_donors_con": int(con.shape[0]),
    }
    for value_name, col in (("s", "s"), ("attention", "a"), ("chr21", "chr21_dosage")):
        if col not in ds.columns:
            continue
        a_vals = ds[col].to_numpy(dtype=float)
        b_vals = con[col].to_numpy(dtype=float)
        diff = _diff(a_vals, b_vals)
        lo, hi = bootstrap_diff_ci(a_vals, b_vals, n_boot=n_boot, seed=seed)
        p = permutation_p_stratified(
            donor_rows[col].to_numpy(dtype=float),
            donor_rows["label"].to_numpy(dtype=int),
            donor_rows["stage"].to_numpy(dtype=object),
            n_perm=n_perm,
            seed=seed,
        )
        rec[value_name] = {
            "mean_ds": float(np.nanmean(a_vals)) if a_vals.size else None,
            "mean_con": float(np.nanmean(b_vals)) if b_vals.size else None,
            "diff": diff,
            "ci_low": lo,
            "ci_high": hi,
            "p_perm": p,
        }
    # Confound Spearman on donor means.
    confounds = {}
    if eligible:
        s_all = donor_rows["s"].to_numpy(dtype=float)
        for name in CONFOUND_COLUMNS:
            if name in donor_rows.columns:
                rho, p = _spearman(s_all, donor_rows[name].to_numpy(dtype=float))
                confounds[name] = {"spearman_rho": rho, "p": p}
    rec["confounds"] = confounds
    # Residualised sensitivity: regress s on dev_PCW + depth, repeat the test.
    residual = None
    if eligible and {"dev_PCW", "log_nCount_RNA", "log_nCount_ATAC"} <= set(donor_rows.columns):
        cov = donor_rows[["dev_PCW", "log_nCount_RNA", "log_nCount_ATAC"]].to_numpy(dtype=float)
        resid = _residualize(donor_rows["s"].to_numpy(dtype=float), cov)
        r_a = resid[donor_rows["label"].to_numpy() == DS_LABEL]
        r_b = resid[donor_rows["label"].to_numpy() == CON_LABEL]
        r_diff = _diff(r_a, r_b)
        r_lo, r_hi = bootstrap_diff_ci(r_a, r_b, n_boot=n_boot, seed=seed + 1)
        r_p = permutation_p_stratified(
            resid,
            donor_rows["label"].to_numpy(dtype=int),
            donor_rows["stage"].to_numpy(dtype=object),
            n_perm=n_perm,
            seed=seed + 2,
        )
        residual = {
            "diff": r_diff,
            "ci_low": r_lo,
            "ci_high": r_hi,
            "p_perm": r_p,
        }
    rec["residualized"] = residual
    return rec


def analyze_cells(cells: pd.DataFrame, n_boot: int = 2000, n_perm: int = 10000, seed: int = 22):
    """Run the full N16 analysis over a per-cell score table."""
    cells = cells.copy()
    cells["donor"] = cells["donor"].astype(str)
    cells["label"] = cells["label"].astype(int)
    cells["author_cell_type"] = cells["author_cell_type"].astype(str)
    if "stage" not in cells.columns:
        dev = cells["dev_PCW"] if "dev_PCW" in cells else np.full(len(cells), np.nan)
        cells["stage"] = derive_stage(dev)
    eligible, excluded = eligible_types(cells)
    records = []
    for ctype, block in cells.groupby("author_cell_type", sort=True):
        is_eligible = str(ctype) in eligible
        if not is_eligible:
            continue
        records.append(analyze_type(block, True, n_boot=n_boot, n_perm=n_perm, seed=seed))
    # Holm across eligible types, separately for s, attention, and chr21.
    for key in ("s", "attention", "chr21"):
        pvals = [r[key]["p_perm"] for r in records if key in r]
        if not pvals:
            continue
        adjusted = holm_adjust(pvals)
        for rec, padj in zip(records, adjusted, strict=True):
            if key in rec:
                rec[key]["p_holm"] = float(padj) if not np.isnan(padj) else None
                rec[key]["significant"] = bool(padj < 0.05) if not np.isnan(padj) else False
    # Residualised sensitivity label.
    for rec in records:
        res = rec.get("residualized")
        raw_sig = rec["s"]["significant"]
        res_sig = bool(res["p_perm"] < 0.05) if res else False
        rec["confound_sensitive"] = bool(raw_sig and not res_sig)
    result = {
        "status": "estimated",
        "arm": "primary",
        "n_boot": n_boot,
        "n_perm": n_perm,
        "seed": seed,
        "support_floor": {
            "min_cells_per_donor": MIN_CELLS_PER_DONOR,
            "min_donors_per_group": MIN_DONORS_PER_GROUP,
        },
        "eligible_types": eligible,
        "excluded_types": excluded,
        "significance_alpha": 0.05,
        "results": records,
    }
    sig_types = [r["author_cell_type"] for r in records if r["s"]["significant"]]
    sig_types_chr21 = [r["author_cell_type"] for r in records if r.get("chr21", {}).get("significant")]
    if not records:
        result["spectrum_call"] = "NOT_ESTIMABLE"
    elif sig_types:
        call = "SPECTRUM_LOCALIZED:" + ",".join(sig_types)
        if set(sig_types) == set(sig_types_chr21) and len(sig_types) > 0:
            call += " (dosage-aligned)"
        result["spectrum_call"] = call
    else:
        result["spectrum_call"] = "SPECTRUM_NULL"
    return result


def _not_estimable(reason: str, detail: str) -> dict:
    return {
        "status": "NOT_ESTIMABLE",
        "reason": reason,
        "detail": detail,
        "spectrum_call": "NOT_ESTIMABLE",
        "eligible_types": [],
        "excluded_types": [],
        "results": [],
    }


def _write_md(payload: dict, path: Path) -> None:
    lines = ["# N16 cell-state spectrum", ""]
    if payload.get("status") == "NOT_ESTIMABLE":
        lines += [
            f"Status: `NOT_ESTIMABLE` ({payload.get('reason', 'unknown')}).",
            "",
            payload.get("detail", ""),
        ]
        path.write_text("\n".join(lines) + "\n")
        return
    lines.append(f"Call: `{payload.get('spectrum_call', 'SPECTRUM_NULL')}`")
    lines.append("")
    lines.append(
        "| cell type | n donors DS | n donors CON | diff s | 95% CI | "
        "p (Holm) | sig | confound-sensitive |"
    )
    lines.append("| --- | ---: | ---: | ---: | --- | ---: | :---: | :---: |")
    for rec in payload.get("results", []):
        s = rec.get("s", {})
        ci = f"[{s.get('ci_low', float('nan')):.3f}, {s.get('ci_high', float('nan')):.3f}]"
        lines.append(
            "| {t} | {nd} | {nc} | {d:.3f} | {ci} | {p} | {sig} | {cs} |".format(
                t=rec.get("author_cell_type"),
                nd=rec.get("n_donors_ds"),
                nc=rec.get("n_donors_con"),
                d=s.get("diff", float("nan")),
                ci=ci,
                p=("NA" if s.get("p_holm") is None else f"{s['p_holm']:.4f}"),
                sig="yes" if s.get("significant") else "no",
                cs="yes" if rec.get("confound_sensitive") else "no",
            )
        )
    lines.append("")
    lines.append(
        "Reading: the model signal is associated with the cell types above; a cell type "
        "with no significant difference carries no detectable model signal at this "
        "donor count. Attention mass is descriptive only."
    )
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    if not CELL_SCORES.exists():
        payload = _not_estimable(
            "input_missing",
            f"N15 export absent: {CELL_SCORES.relative_to(ROOT)}; "
            "N15 is BLOCKED so per-cell s_i/a_i do not exist.",
        )
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n")
        _write_md(payload, OUT_MD)
        print(json.dumps({k: payload[k] for k in ("status", "reason", "spectrum_call")}))
        return 0
    cells = pd.read_csv(CELL_SCORES)
    payload = analyze_cells(cells)
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    _write_md(payload, OUT_MD)
    print(json.dumps({"status": payload["status"], "spectrum_call": payload["spectrum_call"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
