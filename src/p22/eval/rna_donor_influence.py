"""Frozen post-hoc RNA donor influence; never replaces replication evidence."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from p22.data.census import sha256_file
from p22.data.real_cohort import DonorPseudobulk
from p22.eval.external_validation import MIN_SHARED_GENES, DiscoveryEffects, fit_discovery_effects

# Amended 2026-09-21 for the P22 RNA-input repair: the config's
# ``source_code_sha256`` pin for ``src/p22/data/real_cohort.py`` was refreshed
# after ``load_cell_matrix`` defaulted to ``raw/X`` and ``read_matrix_axis`` was
# hardened. The prior frozen value was
# d51a69cc997fe3a80615ea76bdf9d9504a5334c05fe09eb8fe77a623d266cf58; the old pin
# is preserved in the config's ``source_code_amendments``. The scientific
# parameters (gene rules, model, rho tolerance) are unchanged and no diagnostic
# replay is claimed.
CONFIG_SHA256 = "8c069f73ced3815842c88b76aa4c7957a40a1dfdc35172f7d32abe0a6bb6745e"


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _unique_object(pairs: list[tuple]) -> dict:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate key in frozen config")
    return result


def load_config(path: str | Path) -> dict:
    """Only the independently reviewed contract is executable; paths are root-relative."""
    with Path(path).open() as handle:
        config = json.load(handle, object_pairs_hook=_unique_object)
    if canonical_hash(config) != CONFIG_SHA256:
        raise ValueError("frozen config mismatch; review a new protocol before execution")
    return config


def verify_inputs(root: Path, config: dict) -> dict:
    expected = {item["path"]: item["sha256"] for item in config["sources"].values()}
    expected.update(config["source_code_sha256"])
    for relative, digest in expected.items():
        if sha256_file(root / relative) != digest:
            raise ValueError(f"source hash mismatch: {relative}")
    return expected


def _expected(config: dict, comparison: dict) -> dict:
    donors = config["donors"]
    return {
        "spearman_rho": comparison["rho"],
        "n_shared_genes": comparison["shared_count"],
        "n_primary_eligible": comparison["discovery_eligible_genes"],
        "n_expression_eligible": comparison["expression_eligible_genes"],
        "primary_cells": comparison["retained_cells"],
        "min_cells_per_donor": comparison["min_cells_per_donor"],
        "n_ds_donors": donors["ds_count"],
        "n_control_donors": donors["control_count"],
        "design_rank": donors["baseline_design_rank"],
        "residual_df": donors["baseline_residual_df"],
        "donor_ids": donors["ordered_ids"],
        "batch_modelled": False,
    }


def _verify_reference(root: Path, config: dict) -> None:
    spec = config["sources"]["reference"]
    reference = pd.read_csv(root / spec["path"], float_precision="round_trip")
    reference = reference.loc[reference.analysis == spec["analysis"]]
    if len(reference) != 4:
        raise ValueError("reference baseline mismatch: expected four comparisons")
    for comparison in config["comparisons"]:
        match = reference.loc[
            (reference.discovery_population == comparison["population"])
            & (reference.external_population == comparison["sheet"])
        ]
        if len(match) != 1 or match.iloc[0].primary_labels != "|".join(comparison["labels"]):
            raise ValueError("reference baseline mismatch: population or labels")
        row = match.iloc[0].to_dict()
        row["donor_ids"] = ast.literal_eval(row["donor_ids"])
        for key, value in _expected(config, comparison).items():
            if row[key] != value:
                raise ValueError(f"reference baseline mismatch: {key}")


def _write_json(path: Path, value: dict) -> None:
    with path.open("x") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)


def _effect_table(frame: pd.DataFrame, *, omission: bool = False) -> pd.DataFrame:
    columns = ["gene", "coefficient", "avg_log2FC"]
    required = ["gene", "avg_log2FC"] if omission else columns
    if not set(columns).issubset(frame) or frame[required].isna().any().any():
        raise ValueError("effect table schema or missing values")
    if frame.gene.duplicated().any() or frame.gene.astype(str).str.strip().eq("").any():
        raise ValueError("effect genes must be unique and nonempty")
    numeric = ["avg_log2FC"] if omission else ["coefficient", "avg_log2FC"]
    if not np.isfinite(frame[numeric].to_numpy(dtype=float)).all():
        raise ValueError("non-finite effect table")
    return frame[columns].set_index("gene").sort_index()


def _rho(frame: pd.DataFrame) -> float:
    if len(frame) < MIN_SHARED_GENES:
        raise ValueError(f"fewer than {MIN_SHARED_GENES} shared genes")
    if not np.isfinite(frame[["coefficient", "avg_log2FC"]].to_numpy(dtype=float)).all():
        raise ValueError("non-finite effect vector")
    if (
        frame[["coefficient", "avg_log2FC"]].max() == frame[["coefficient", "avg_log2FC"]].min()
    ).any():
        raise ValueError("constant effect vector")
    value = float(spearmanr(frame.coefficient, frame.avg_log2FC).statistic)
    if not np.isfinite(value):
        raise ValueError("non-finite Spearman correlation")
    return value


def same_support_components(baseline: pd.DataFrame, omission: pd.DataFrame) -> dict:
    """Compare on Gi, retaining G0 and unchanged external measurements explicitly."""
    base, omitted = _effect_table(baseline), _effect_table(omission, omission=True)
    shared = base.index.intersection(omitted.index).sort_values()
    lost = base.index.difference(omitted.index).sort_values().tolist()
    new = omitted.index.difference(base.index).sort_values().tolist()
    if not np.array_equal(base.loc[shared, "avg_log2FC"], omitted.loc[shared, "avg_log2FC"]):
        raise ValueError("external effects changed between baseline and omission")
    result = {
        "status": "UNAVAILABLE",
        "reason": "",
        "n_baseline_genes": len(base),
        "n_shared_genes": len(shared),
        "n_lost_genes": len(lost),
        "n_new_genes": len(new),
        "lost_genes": json.dumps(lost),
        "new_genes": json.dumps(new),
        "shared_gene_sha256": canonical_hash(shared.tolist()),
        **dict.fromkeys(
            [
                "rho_baseline",
                "rho_baseline_same_support",
                "rho_loo",
                "same_support_delta",
                "support_delta",
                "total_delta",
            ]
        ),
    }
    try:
        result["rho_baseline"] = _rho(base)
        result["rho_baseline_same_support"] = _rho(base.loc[shared])
        result["rho_loo"] = _rho(omitted.loc[shared])
    except ValueError as exc:
        result["reason"] = str(exc)
        return result
    same = result["rho_loo"] - result["rho_baseline_same_support"]
    support = result["rho_baseline_same_support"] - result["rho_baseline"]
    return result | {
        "status": "AVAILABLE",
        "same_support_delta": same,
        "support_delta": support,
        "total_delta": same + support,
    }


def _join(fitted: DiscoveryEffects, external: pd.DataFrame) -> pd.DataFrame:
    joined = (
        fitted.effects.merge(external[["gene", "avg_log2FC"]], on="gene", validate="one_to_one")
        .sort_values("gene")
        .reset_index(drop=True)
    )
    _effect_table(joined)
    return joined


def prepare_baselines(
    bulk: DonorPseudobulk,
    metadata: pd.DataFrame,
    genes: pd.DataFrame,
    external: dict[str, pd.DataFrame],
) -> tuple[DiscoveryEffects, dict[str, pd.DataFrame]]:
    fitted = fit_discovery_effects(bulk, metadata, genes)
    return fitted, {sheet: _join(fitted, frame) for sheet, frame in external.items()}


def validate_baseline(
    fitted: DiscoveryEffects,
    bulk: DonorPseudobulk,
    table: pd.DataFrame,
    expected: dict,
) -> None:
    actual = fitted.audit | {
        "spearman_rho": _rho(_effect_table(table)),
        "n_shared_genes": len(table),
        "primary_cells": int(bulk.n_cells.sum()),
        "donor_ids": list(bulk.donor_ids),
    }
    for key, value in expected.items():
        matches = (
            np.isclose(actual.get(key, np.nan), value, atol=1e-10, rtol=0)
            if key == "spearman_rho"
            else actual.get(key) == value
        )
        if not matches:
            raise ValueError(f"baseline mismatch for {key}: {actual.get(key)!r} != {value!r}")


def omission_rows(
    bulk: DonorPseudobulk,
    metadata: pd.DataFrame,
    genes: pd.DataFrame,
    external: dict[str, pd.DataFrame],
    baselines: dict[str, pd.DataFrame],
) -> list[dict]:
    """One full-gene row-subset fit per omitted donor, reused across external sheets."""
    if tuple(metadata.index) != bulk.donor_ids or tuple(genes.index.astype(str)) != bulk.gene_ids:
        raise ValueError("donor or gene alignment mismatch before omissions")
    rows = []
    for position, donor in enumerate(bulk.donor_ids):
        keep = np.arange(len(bulk.donor_ids)) != position
        kept_metadata = metadata.iloc[keep]
        info = {
            "omitted_donor": donor,
            "remaining_donor_ids": json.dumps(kept_metadata.index.tolist()),
            "n_ds_donors": int(kept_metadata.label.sum()),
            "n_control_donors": int((kept_metadata.label == 0).sum()),
            "remaining_cells": int(bulk.n_cells[keep].sum()),
        }
        try:
            # Retain ALL raw gene columns: the existing estimator owns CPM and its floor.
            subset = replace(
                bulk,
                donor_ids=tuple(np.asarray(bulk.donor_ids)[keep]),
                conditions=tuple(np.asarray(bulk.conditions)[keep]),
                labels=bulk.labels[keep],
                n_cells=bulk.n_cells[keep],
                total_counts=bulk.total_counts[keep],
                gene_sums=bulk.gene_sums[keep],
                chr21_fraction=None if bulk.chr21_fraction is None else bulk.chr21_fraction[keep],
            )
            fitted = fit_discovery_effects(subset, kept_metadata, genes)
        except ValueError as exc:
            for sheet, base in baselines.items():
                rows.append(
                    info
                    | {
                        "sheet": sheet,
                        "fit_status": "FAILED",
                        "status": "UNAVAILABLE",
                        "reason": str(exc),
                        "n_baseline_genes": len(base),
                        "rho_baseline": _rho(_effect_table(base)),
                        **dict.fromkeys(
                            [
                                "n_shared_genes",
                                "n_lost_genes",
                                "n_new_genes",
                                "same_support_delta",
                                "support_delta",
                                "total_delta",
                            ]
                        ),
                    }
                )
            continue
        for sheet, base in baselines.items():
            rows.append(
                info
                | same_support_components(base, _join(fitted, external[sheet]))
                | {
                    "sheet": sheet,
                    "fit_status": "PASS",
                    "design_rank": fitted.audit["design_rank"],
                    "residual_df": fitted.audit["residual_df"],
                }
            )
    return rows


def _write_report(frame: pd.DataFrame, config: dict, output_dir: Path) -> None:
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 2, figsize=(15, 12), constrained_layout=True)
    lines = [
        "# RNA donor influence: POST_HOC_EXPLORATORY",
        "",
        "Original four RNA comparisons and headline remain inconclusive; G8 is unchanged.",
        "This diagnostic measures sensitivity to discovery-donor omission, not new replication.",
        "",
        "Same-support delta = rho_loo(Gi) - rho_baseline(Gi).",
        "Support delta = rho_baseline(Gi) - rho_baseline(G0); total delta is their sum.",
        "Newly eligible genes are counted but excluded from Gi and the endpoint.",
        "Rank uses absolute same-support delta, with donor ID breaking ties.",
        "",
    ]
    for axis, comparison in zip(axes.flat, config["comparisons"], strict=True):
        sheet = comparison["sheet"]
        rows = frame.loc[frame.sheet == sheet]
        valid = rows.loc[rows.status == "AVAILABLE"]
        y = np.arange(len(rows))
        axis.barh(y - 0.18, rows.same_support_delta, height=0.36, label="Same-support delta")
        axis.barh(y + 0.18, rows.support_delta, height=0.36, label="Support delta")
        labels = [
            f"{row.omitted_donor} [Gi={int(row.n_shared_genes)}]"
            if row.status == "AVAILABLE"
            else f"{row.omitted_donor} [UNAVAILABLE]"
            for row in rows.itertuples()
        ]
        axis.set_yticks(y, labels=labels, fontsize=7)
        axis.invert_yaxis()
        axis.axvline(0, color="black", linewidth=0.6)
        axis.set_title(
            f"{comparison['population']} → {sheet}; baseline rho={comparison['rho']:.5f}"
        )
        axis.set_xlabel("Change in Spearman rho")
        axis.legend(fontsize=7)
        lines.extend([f"## {comparison['population']} → {sheet}", ""])
        lines.append(f"Available omissions: {len(valid)}/{len(rows)}.")
        if not valid.empty:
            top = valid.iloc[0]
            total_abs = float(valid.absolute_same_support_delta.sum())
            concentration = (
                f"{100 * top.absolute_same_support_delta / total_abs:.1f}%"
                if total_abs > 0
                else "undefined (all deltas zero)"
            )
            lines.extend(
                [
                    f"Largest absolute influence: {top.omitted_donor}; same-support delta "
                    f"{top.same_support_delta:+.6f}, support delta {top.support_delta:+.6f}.",
                    f"Its share of summed absolute same-support deltas: {concentration}. "
                    "This is descriptive, not a significance or causality threshold.",
                    f"Gi ranges {int(valid.n_shared_genes.min())}"
                    f"–{int(valid.n_shared_genes.max())}; "
                    f"lost genes {int(valid.n_lost_genes.min())}–{int(valid.n_lost_genes.max())}; "
                    f"new genes {int(valid.n_new_genes.min())}–{int(valid.n_new_genes.max())}.",
                ]
            )
        for row in rows.loc[rows.status != "AVAILABLE"].itertuples():
            lines.append(f"UNAVAILABLE: {row.omitted_donor}: {row.reason}")
        lines.append("")
    figure.suptitle(
        "POST_HOC_EXPLORATORY: shared discovery donors; RG panels also share cells\n"
        "Original inconclusive RNA results unchanged; external donor uncertainty unresolved",
        fontsize=12,
    )
    figure.savefig(output_dir / "donor_influence.png", dpi=150)
    plt.close(figure)
    lines.extend(
        [
            "## Limits and next decision",
            "",
            config["output"]["non_independence"],
            config["output"]["limitations"],
            "Published external summary effects stay fixed; "
            "external donor uncertainty is not estimated.",
            "No independent-cell resampling, donor-level bootstrap, "
            "permutation or power test was run.",
            "Do not remove donors to improve agreement. Preserve the original RNA conclusion. "
            "Next decision: review this diagnostic alongside unresolved paired-input feasibility "
            "gates before proposing any separate data acquisition or training step.",
            "",
            "Completion requires run.json AND supervisor resources.json both marked COMPLETED.",
            "RSS is sampled with early stop at 5 GiB under a 6 GiB budget, "
            "not a kernel hard ceiling.",
        ]
    )
    with (output_dir / "SUMMARY.md").open("x") as handle:
        handle.write("\n".join(lines) + "\n")


def run_analysis(root: Path, config_path: Path, output_dir: Path) -> dict:
    """Reproduce all four baselines before omissions; write new diagnostic artifacts only."""
    import h5py
    from anndata.io import read_elem

    from p22.data.real_cohort import donor_pseudobulk
    from p22.data.resources import environment_record
    from p22.eval import real_pipeline
    from p22.eval.external_validation import (
        collapse_donor_metadata,
        gene_eligibility,
        load_external_effects,
    )

    config = load_config(config_path)
    if os.environ.get("P22_PROFESSOR_APPROVED") != "1":
        raise ValueError("existing per-run approval attestation required")
    if not output_dir.is_dir() or any(
        (output_dir / name).exists() for name in config["files_to_create"]
    ):
        raise FileExistsError("diagnostic requires a fresh supervisor-created output directory")
    sources_before = verify_inputs(root, config)
    _verify_reference(root, config)
    path = root / config["sources"]["h5ad"]["path"]
    with h5py.File(path, "r") as handle:
        source_obs, genes = read_elem(handle["obs"]), read_elem(handle["var"])
        if not read_elem(handle["raw/var"]).index.equals(genes.index):
            raise ValueError("raw count gene order differs from var")
    state = real_pipeline.run_schema_qc_census(path, real_pipeline.RealAnalysisState())
    if state.qc.get("status") != "PASS" or state.obs is None:
        raise ValueError("primary cohort QC did not pass")
    obs, keep = state.obs, np.asarray(state.keep_mask)
    columns = ["donor_id", "disease", "dev_PCW", "sex", "author_cell_type"]
    if not obs.index.equals(source_obs.index) or not obs[columns].astype("string").equals(
        source_obs[columns].astype("string")
    ):
        raise ValueError("QC metadata does not match source cell order and annotations")
    if keep.dtype != bool or keep.shape != (len(obs),):
        raise ValueError("QC keep mask must be row-aligned boolean values")
    collapse_donor_metadata(obs.loc[keep])
    window = keep & pd.to_numeric(obs.dev_PCW).between(13, 19).to_numpy()
    external = load_external_effects(
        root / config["sources"]["workbook"]["path"],
        gene_metadata=genes,
        expected_sha256=config["sources"]["workbook"]["sha256"],
    )
    populations, baseline_records, baseline_tables = {}, [], []
    identifiers, _ = gene_eligibility(genes)
    identifiers = identifiers.loc[identifiers.eligible, ["gene"]].assign(
        primary_gene_id=lambda frame: frame.index.astype(str)
    )
    for comparison in config["comparisons"]:
        population, sheet = comparison["population"], comparison["sheet"]
        if population not in populations:
            mask = window & obs.author_cell_type.isin(comparison["labels"]).to_numpy()
            bulk = donor_pseudobulk(path, obs, mask)
            metadata = collapse_donor_metadata(obs.loc[mask], bulk.donor_ids)
            sheets = {
                item["sheet"]: external[item["sheet"]]
                for item in config["comparisons"]
                if item["population"] == population
            }
            fitted, joined = prepare_baselines(bulk, metadata, genes, sheets)
            populations[population] = (bulk, metadata, fitted, sheets, joined)
        bulk, _, fitted, _, joined = populations[population]
        validate_baseline(fitted, bulk, joined[sheet], _expected(config, comparison))
        table = joined[sheet].merge(identifiers, on="gene", validate="one_to_one")
        baseline_tables.append(table.assign(population=population, sheet=sheet))
        baseline_records.append(
            _expected(config, comparison)
            | {
                "population": population,
                "sheet": sheet,
                "actual_rho": _rho(_effect_table(table)),
                "G0_sha256": canonical_hash(table.gene.tolist()),
                "G0_gene_ids_sha256": canonical_hash(table.primary_gene_id.tolist()),
            }
        )
    # No omission runs until every frozen baseline has passed the preflight above.
    rows = []
    for population, (bulk, metadata, _, sheets, joined) in populations.items():
        rows.extend(
            row | {"population": population, "evidence_scope": "POST_HOC_EXPLORATORY"}
            for row in omission_rows(bulk, metadata, genes, sheets, joined)
        )
    frame = pd.DataFrame(rows)
    for column in ("same_support_delta", "support_delta", "total_delta"):
        frame[column] = frame[column].astype(float)
    frame["absolute_same_support_delta"] = frame.same_support_delta.abs()
    frame = frame.sort_values(
        ["sheet", "absolute_same_support_delta", "omitted_donor"],
        ascending=[True, False, True],
        na_position="last",
    ).reset_index(drop=True)
    frame["influence_rank"] = (
        frame.groupby("sheet").cumcount().add(1).where(frame.status.eq("AVAILABLE")).astype("Int64")
    )
    pd.concat(baseline_tables, ignore_index=True).to_csv(
        output_dir / "baseline_genes.csv", index=False, mode="x"
    )
    frame.to_csv(output_dir / "donor_influence.csv", index=False, mode="x")
    _write_report(frame, config, output_dir)
    sources_after = verify_inputs(root, config)
    if sources_before != sources_after:
        raise ValueError("source files changed during execution")
    code = [
        "src/p22/eval/rna_donor_influence.py",
        "scripts/diagnose_rna_replication.py",
    ]
    report = {
        "status": "COMPLETED",
        "evidence_scope": "POST_HOC_EXPLORATORY",
        "completion_requires": "resources.json status COMPLETED from the supervisor",
        "config_sha256": canonical_hash(config),
        "config_file_sha256": sha256_file(config_path),
        "git_head": subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip(),
        "implementation_sha256": {name: sha256_file(root / name) for name in code},
        "inputs_before": sources_before,
        "inputs_after": sources_after,
        "environment": environment_record(),
        "baseline_preflight": baseline_records,
        "historical_gene_ids_saved": False,
        "gene_identity_note": "G0 derived and fingerprinted now after reproducing saved summaries",
        "qc_status": state.qc["status"],
        "omission_rows": len(frame),
        "available_rows": int(frame.status.eq("AVAILABLE").sum()),
        "original_headline": "inconclusive; unchanged",
        "original_G8": "unchanged",
        "artifact_sha256": {
            name: sha256_file(output_dir / name)
            for name in config["files_to_create"]
            if name not in {"run.json", "resources.json"}
        },
    }
    _write_json(output_dir / "run.json", report)
    return report
