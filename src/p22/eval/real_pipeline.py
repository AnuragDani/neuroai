"""End-to-end real-analysis orchestrator for the canonical notebook.

Simulation mode never calls this module. Real mode runs stages in order:
schema/QC, resource/ATAC branch, estimand freeze, donor-held-out models,
RNA-only interventions, marker/validation status, and package inputs.

Synthetic outputs are never mixed into the returned metric tables.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from p22.data.adequacy import evaluate_donor_adequacy
from p22.data.group_splits import build_repeated_group_split_report
from p22.data.real_cohort import (
    POSITIVE_CONDITION,
    Chr21Mapping,
    QcThresholds,
    audit_schema,
    derive_cell_qc,
    donor_pseudobulk,
    load_cell_matrix,
    read_var,
    run_cohort_qc,
    sample_capped_cells,
    sample_nested_capped_cells,
    symbol_series,
)
from p22.data.resources import (
    PRIMARY_CAP,
    SENSITIVITY_CAPS,
    assess_fragment_build,
    decide_atac_branch,
    disk_free_gb,
    environment_record,
    measure_stage,
    peak_rss_gb,
)
from p22.eval.estimand import freeze_estimand
from p22.eval.marker_validation import (
    CHR21_DOSAGE_PANEL,
    CHR21_DOSAGE_PANEL_NAME,
    CONTROL_PANEL,
    CONTROL_PANEL_NAME,
    check_geo_accession,
    evaluate_panel,
)
from p22.eval.real_interventions import intervention_rows, run_rna_only_interventions
from p22.eval.real_runner import (
    CAPPED_LAYER,
    FULL_COHORT_LAYER,
    ModelRun,
    not_applicable_run,
    paired_donor_delta,
    run_cell_level_model,
    run_donor_level_model,
    run_majority_baseline,
)
from p22.eval.validation import build_validation_report

SEED = 20260728


@dataclass
class RealAnalysisState:
    """Mutable container filled stage-by-stage by the notebook."""

    schema: dict[str, Any] = field(default_factory=dict)
    qc: dict[str, Any] = field(default_factory=dict)
    adequacy: dict[str, Any] = field(default_factory=dict)
    resource: dict[str, Any] = field(default_factory=dict)
    atac_branch: dict[str, Any] = field(default_factory=dict)
    estimand: dict[str, Any] = field(default_factory=dict)
    split: dict[str, Any] = field(default_factory=dict)
    metrics_rows: list[dict[str, Any]] = field(default_factory=list)
    paired_deltas: list[dict[str, Any]] = field(default_factory=list)
    same_cap_summary: dict[str, Any] = field(default_factory=dict)
    intervention_rows: list[dict[str, Any]] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)
    validation_rows: list[dict[str, Any]] = field(default_factory=list)
    panel_rows: list[dict[str, Any]] = field(default_factory=list)
    evidence_buckets: dict[str, list[str]] = field(
        default_factory=lambda: {
            "verified_real": [],
            "synthetic": [],
            "metadata_only": [],
            "blocked_or_unknown": [],
        }
    )
    data_layer_label: str = "unknown"
    atac_branch_label: str = "unknown"
    headline: list[str] = field(default_factory=list)
    keep_mask: np.ndarray | None = None
    obs: pd.DataFrame | None = None
    model_runs: dict[str, ModelRun] = field(default_factory=dict)
    bulk: Any = None


def _chr21_from_schema(schema: dict[str, Any]) -> Chr21Mapping | None:
    payload = schema.get("chr21_mapping")
    if not payload:
        return None
    return Chr21Mapping(
        status=str(payload.get("status")),
        source=str(payload.get("source")),
        id_scheme=str(payload.get("id_scheme")),
        chromosome_column=payload.get("chromosome_column"),
        n_genes_total=int(payload.get("n_genes_total") or 0),
        n_chr21_genes=int(payload.get("n_chr21_genes") or 0),
        mapping_sha256=payload.get("mapping_sha256"),
        example_genes=tuple(payload.get("example_genes") or ()),
        reason=payload.get("reason"),
    )


def _donor_covariate_matrix(
    obs: pd.DataFrame,
    keep_mask: np.ndarray,
    donor_ids: tuple[str, ...],
) -> tuple[np.ndarray | None, list[str], list[str]]:
    """Observed/derived donor covariates only. Never invent batch values."""
    kept = obs.loc[keep_mask].copy()
    kept["donor_id"] = kept["donor_id"].astype(str)
    numeric_candidates = [
        name
        for name in (
            "nFeature_RNA",
            "nCount_RNA",
            "percent.mt",
            "derived_n_genes",
            "derived_total_counts",
            "derived_pct_mito",
            "dev_PCW",
            "nCount_ATAC",
            "nFeature_ATAC",
            "nucleosome_signal",
            "TSS.enrichment",
        )
        if name in kept.columns
    ]
    missing = [name for name in ("batch", "batch_id") if name not in kept.columns]
    if "library" not in kept.columns and "batch_seq" not in kept.columns:
        missing.append("batch/library/batch_seq")

    parts: list[pd.DataFrame] = []
    if numeric_candidates:
        numeric = (
            kept.groupby("donor_id", sort=True)[numeric_candidates]
            .median()
            .reindex(list(donor_ids))
        )
        parts.append(numeric)

    for column in ("stage", "sex", "batch_seq", "library"):
        if column not in kept.columns:
            continue
        first = kept.groupby("donor_id", sort=True)[column].agg(lambda values: str(values.iloc[0]))
        first = first.reindex(list(donor_ids))
        parts.append(pd.get_dummies(first.astype(str), prefix=column, dtype=float))

    if not parts:
        return None, [], missing
    frame = pd.concat(parts, axis=1)
    matrix = frame.to_numpy(dtype=float)
    if np.isnan(matrix).any():
        col_medians = np.nanmedian(matrix, axis=0)
        inds = np.where(np.isnan(matrix))
        matrix[inds] = np.take(col_medians, inds[1])
    return matrix, list(frame.columns), missing


def run_schema_qc_census(h5ad_path: str | Path, state: RealAnalysisState) -> RealAnalysisState:
    """C24: schema audit, derived QC, exclusions, G2/R2/R3 inputs."""
    path = Path(h5ad_path)
    thresholds = QcThresholds()
    schema, schema_measurement = measure_stage(
        "schema_audit",
        lambda: audit_schema(path),
        disk_path=path.parent,
        input_bytes=path.stat().st_size if path.is_file() else None,
        notes="obs/var/uns only; no dense matrix",
    )
    derived, derived_measurement = measure_stage(
        "derive_cell_qc",
        lambda: derive_cell_qc(path),
        disk_path=path.parent,
        notes="streamed raw/X n_genes, total counts, pct_mito",
    )
    qc, qc_measurement = measure_stage(
        "cohort_qc",
        lambda: run_cohort_qc(path, thresholds, derived=derived),
        disk_path=path.parent,
        notes="frozen thresholds before filtering",
    )
    if qc.donor_table_post_qc:
        donor_frame = pd.DataFrame(qc.donor_table_post_qc)
        if "condition" not in donor_frame.columns and "disease" in donor_frame.columns:
            donor_frame = donor_frame.rename(columns={"disease": "condition"})
        donor_frame = donor_frame[["donor_id", "condition", "n_cells"]]
    else:
        donor_frame = pd.DataFrame(columns=["donor_id", "condition", "n_cells"])
    pairing_known = bool(
        (schema.atac or {}).get("same_nucleus_evidence") not in (None, "absent", "")
    )
    adequacy = evaluate_donor_adequacy(donor_frame, pairing_known=pairing_known)
    state.schema = schema.to_dict() | {
        "wall_seconds": schema_measurement.elapsed_seconds,
        "peak_rss_gb": schema_measurement.peak_rss_gb,
    }
    state.qc = qc.to_dict() | {
        "wall_seconds": qc_measurement.elapsed_seconds,
        "peak_rss_gb": qc_measurement.peak_rss_gb,
        "derive_wall_seconds": derived_measurement.elapsed_seconds,
    }
    state.adequacy = adequacy.to_dict()
    state.keep_mask = qc.keep_mask
    state.obs = qc.obs
    state.data_layer_label = "full_cohort_post_qc"
    state.evidence_buckets["verified_real"].append(
        f"C24 schema/QC: {qc.n_cells_post_qc} cells / {qc.n_donors_post_qc} donors retained"
    )
    if schema.chr21 is not None and schema.chr21.usable:
        state.evidence_buckets["verified_real"].append(
            f"chr21 mapping verified ({schema.chr21.n_chr21_genes} genes)"
        )
    else:
        reason = None if schema.chr21 is None else schema.chr21.reason
        state.evidence_buckets["blocked_or_unknown"].append(f"chr21 mapping not usable: {reason}")
    if qc.status != "PASS":
        state.evidence_buckets["blocked_or_unknown"].append(
            f"QC status={qc.status}; stop={list(qc.stop_reasons)}"
        )
    return state


def run_resource_and_atac(
    h5ad_path: str | Path,
    state: RealAnalysisState,
    *,
    fragment_asset: dict[str, Any] | None = None,
    fragment_build_approved: bool = False,
) -> RealAnalysisState:
    """C26: measure resources and resolve B1/B2a/B2b."""
    path = Path(h5ad_path)
    peak_present = bool((state.schema.get("atac") or {}).get("peak_block_present"))
    fragment_present = bool((fragment_asset or {}).get("present"))
    fragment_bytes = (fragment_asset or {}).get("file_size")
    free = disk_free_gb(path.parent)
    feasibility = assess_fragment_build(
        None if fragment_bytes is None else int(fragment_bytes),
        free,
    )
    # B2a requires explicit build approval AND disk budget. Default remains B2b.
    resource_budget_ok = bool(feasibility.feasible and fragment_build_approved)
    branch = decide_atac_branch(
        peak_block_present=peak_present,
        fragment_asset_present=fragment_present,
        fragment_build_approved=fragment_build_approved,
        resource_budget_ok=resource_budget_ok,
    )

    measurements = []
    if state.obs is not None and state.keep_mask is not None:
        for cap in (PRIMARY_CAP, *SENSITIVITY_CAPS):

            def _cap_load(current_cap: int = cap) -> dict[str, int]:
                rows = sample_capped_cells(state.obs, state.keep_mask, current_cap, seed=0)
                matrix = load_cell_matrix(path, rows)
                return {"n_cells": int(len(rows)), "n_features": int(matrix.shape[1])}

            _, measurement = measure_stage(
                f"cap_{cap}_load",
                _cap_load,
                cells_per_donor_cap=cap,
                disk_path=path.parent,
                input_bytes=path.stat().st_size,
                notes="backed sparse slice; never densify full matrix",
            )
            measurements.append(measurement)

    storage = {
        "backed_reads": True,
        "dense_full_matrix_conversion": False,
        "h5ad_bytes": path.stat().st_size if path.is_file() else None,
        "peak_rss_gb_now": peak_rss_gb(),
        "disk_free_gb": free,
    }
    status = "PASS" if measurements else "INCONCLUSIVE"
    state.atac_branch = branch.to_dict()
    state.atac_branch_label = branch.branch
    state.resource = {
        "status": status,
        "measurements": [item.to_dict() for item in measurements],
        "atac_branch": branch.to_dict(),
        "environment": environment_record(),
        "fragment_feasibility": feasibility.to_dict(),
        "storage": storage,
        "blocking_problems": [],
        "open_questions": (
            ["ATAC peak build not run; multimodal models NOT_APPLICABLE"]
            if branch.branch == "B2b"
            else []
        ),
    }
    if branch.branch == "B2b":
        state.evidence_buckets["verified_real"].append(
            "C26 ATAC branch B2b: RNA-only path; no multimodal claim"
        )
        state.headline.append("ATAC branch B2b — RNA-only analysis continues")
    else:
        state.evidence_buckets["verified_real"].append(f"C26 ATAC branch {branch.branch}")
    state.evidence_buckets["verified_real"].append(
        f"C26 resource caps measured: {[item.cells_per_donor_cap for item in measurements]}"
    )
    return state


def freeze_real_estimand(state: RealAnalysisState, seed: int = SEED) -> RealAnalysisState:
    """C27: freeze estimand from post-QC donor counts before prediction."""
    checks = state.adequacy.get("checks") or {}
    n_control = int(checks.get("n_control_donors") or 15)
    n_ds = int(checks.get("n_ds_donors") or 15)
    report = freeze_estimand(
        n_control_donors=n_control,
        n_ds_donors=n_ds,
        marker_set=CHR21_DOSAGE_PANEL_NAME,
        multimodal_validation_accession=None,
        already_predicted=False,
    )
    if state.obs is None or state.keep_mask is None:
        raise RuntimeError("QC must run before estimand freeze")
    kept = state.obs.loc[state.keep_mask]
    cell_donors = kept["donor_id"].astype(str).to_numpy()
    cell_labels = (kept["disease"].astype(str) == POSITIVE_CONDITION).astype(int).to_numpy()
    split = build_repeated_group_split_report(
        cell_donors,
        cell_labels,
        n_repeats=report.estimand.split_repeats,
        n_folds=report.estimand.folds_per_repeat,
        base_seed=seed,
    )
    state.estimand = report.to_dict()
    state.split = split.to_dict()
    state.evidence_buckets["verified_real"].append(
        "C27 estimand frozen; "
        f"margin={report.estimand.margin}; split_overlap={split.donor_overlap_count}"
    )
    if split.donor_overlap_count != 0:
        state.evidence_buckets["blocked_or_unknown"].append("donor overlap detected in splits")
    return state


def _log_cpm(gene_sums: np.ndarray) -> np.ndarray:
    totals = gene_sums.sum(axis=1, keepdims=True)
    totals = np.where(totals > 0, totals, 1.0)
    return np.log1p(gene_sums / totals * 1e6)


CAP_MODEL_NAMES = ("chr21_dosage", "pseudobulk_rna_logistic", "rna_only")
CAP_MODEL_LABELS = {
    "chr21_dosage": "Chromosome 21 dosage",
    "pseudobulk_rna_logistic": "Pseudobulk RNA",
    "rna_only": "RNA-only",
}


def summarize_same_cap_results(
    metric_rows: list[dict[str, Any]],
    paired_deltas: list[dict[str, Any]],
    *,
    primary_cap: int,
    margin: float = 0.07,
) -> dict[str, Any]:
    """Give a conservative plain-language conclusion for the capped comparison."""
    scores_by_cap: dict[int, dict[str, float]] = {}
    for row in metric_rows:
        cap = row.get("cap")
        model = row.get("model")
        score = row.get("donor_balanced_accuracy")
        if (
            cap is None
            or model not in CAP_MODEL_NAMES
            or row.get("status") != "measured"
            or score is None
        ):
            continue
        scores_by_cap.setdefault(int(cap), {})[str(model)] = float(score)

    point_winner_by_cap: dict[int, str | None] = {}
    for cap, scores in scores_by_cap.items():
        if set(scores) != set(CAP_MODEL_NAMES):
            point_winner_by_cap[cap] = None
            continue
        best = max(scores.values())
        winners = [name for name, score in scores.items() if np.isclose(score, best)]
        point_winner_by_cap[cap] = winners[0] if len(winners) == 1 else None

    winners = set(point_winner_by_cap.values())
    stable_winner = next(iter(winners)) if len(winners) == 1 and None not in winners else None
    primary_winner = point_winner_by_cap.get(primary_cap)
    summary = {
        "status": "INCONCLUSIVE",
        "primary_cap": int(primary_cap),
        "practical_margin": float(margin),
        "scores_by_cap": scores_by_cap,
        "point_winner_by_cap": point_winner_by_cap,
        "primary_point_winner": primary_winner,
        "stable_point_winner": stable_winner,
    }

    if primary_cap not in scores_by_cap or len(scores_by_cap[primary_cap]) != len(CAP_MODEL_NAMES):
        summary["conclusion"] = "The primary same-cap comparison is incomplete."
        return summary
    if stable_winner is None:
        summary["conclusion"] = (
            "The point-estimate ranking changes across cell caps or contains a tie. "
            "The comparison remains sampling-sensitive and inconclusive."
        )
        return summary

    primary_deltas = {
        str(row.get("reference")): row
        for row in paired_deltas
        if row.get("cap") == primary_cap and row.get("model") == "rna_only"
    }
    label = CAP_MODEL_LABELS[stable_winner]
    if stable_winner == "rna_only":
        supported = all(
            primary_deltas.get(reference, {}).get(
                "comparison_result",
                "model_better"
                if primary_deltas.get(reference, {}).get("verdict") == "success"
                else "inconclusive",
            )
            == "model_better"
            for reference in ("chr21_dosage", "pseudobulk_rna_logistic")
        )
        if supported:
            summary["status"] = "SUPPORTED"
            summary["conclusion"] = (
                f"{label} has the highest point estimate at every cap and exceeds both capped "
                f"baselines by the {margin:.2f} margin at the primary cap."
            )
        else:
            summary["conclusion"] = (
                f"{label} has the highest point estimate at every cap, but paired donor "
                "intervals do not support superiority."
            )
        return summary

    comparison = primary_deltas.get(stable_winner, {})
    delta = comparison.get("donor_balanced_accuracy_delta")
    upper = comparison.get("bootstrap_upper")
    supported = comparison.get("comparison_result") == "reference_better" or bool(
        delta is not None and upper is not None and float(delta) <= -margin and float(upper) < 0.0
    )
    if supported:
        summary["status"] = "SUPPORTED"
        summary["conclusion"] = (
            f"{label} has the highest point estimate at every cap and exceeds RNA-only by "
            f"the {margin:.2f} margin at the primary cap. Baseline-to-baseline superiority "
            "was not tested."
        )
    else:
        summary["conclusion"] = (
            f"{label} has the highest point estimate at every cap, but the paired donor "
            "interval does not support superiority over RNA-only."
        )
    return summary


def run_real_model_comparison(
    h5ad_path: str | Path,
    state: RealAnalysisState,
    *,
    primary_cap: int = PRIMARY_CAP,
    sensitivity_caps: tuple[int, ...] = SENSITIVITY_CAPS,
    n_features: int = 2000,
) -> RealAnalysisState:
    """Run full-cohort context and fair cap-matched models under shared splits."""
    path = Path(h5ad_path)
    if state.obs is None or state.keep_mask is None:
        raise RuntimeError("QC must run before model comparison")
    chr21 = _chr21_from_schema(state.schema)

    bulk, bulk_measurement = measure_stage(
        "donor_pseudobulk",
        lambda: donor_pseudobulk(path, state.obs, state.keep_mask, chr21_mapping=chr21),
        disk_path=path.parent,
        notes="all retained cells per donor; full-cohort layer",
    )
    state.bulk = bulk
    state.resource.setdefault("measurements", []).append(bulk_measurement.to_dict())

    n_repeats = int(((state.estimand or {}).get("estimand") or {}).get("split_repeats") or 5)
    n_folds = int(((state.estimand or {}).get("estimand") or {}).get("folds_per_repeat") or 5)
    donor_split = build_repeated_group_split_report(
        list(bulk.donor_ids),
        bulk.labels,
        n_repeats=n_repeats,
        n_folds=n_folds,
        base_seed=SEED,
    )
    folds = donor_split.folds

    runs: dict[str, ModelRun] = {}
    runs["majority_class"] = run_majority_baseline(bulk.labels, bulk.donor_ids, folds)

    if chr21 is not None and chr21.usable and bulk.chr21_fraction is not None:
        runs["chr21_dosage"] = run_donor_level_model(
            "chr21_dosage",
            bulk.chr21_fraction,
            bulk.labels,
            bulk.donor_ids,
            folds,
            layer=FULL_COHORT_LAYER,
            detail={
                "mapping_sha256": chr21.mapping_sha256,
                "n_chr21_genes": chr21.n_chr21_genes,
            },
        )
    else:
        reason = "chr21 mapping not verified" if chr21 is None else (chr21.reason or "unusable")
        runs["chr21_dosage"] = not_applicable_run("chr21_dosage", reason, layer=FULL_COHORT_LAYER)

    cov_matrix, cov_names, cov_missing = _donor_covariate_matrix(
        state.obs, state.keep_mask, bulk.donor_ids
    )
    if cov_matrix is not None and cov_matrix.size:
        runs["qc_covariate_logistic"] = run_donor_level_model(
            "qc_covariate_logistic",
            cov_matrix,
            bulk.labels,
            bulk.donor_ids,
            folds,
            layer=FULL_COHORT_LAYER,
            detail={"covariates": cov_names, "missing_fields": cov_missing},
        )
    else:
        runs["qc_covariate_logistic"] = not_applicable_run(
            "qc_covariate_logistic",
            "no observed or derived numeric covariates present",
            layer=FULL_COHORT_LAYER,
        )

    runs["pseudobulk_rna_logistic"] = run_donor_level_model(
        "pseudobulk_rna_logistic",
        bulk.gene_sums,
        bulk.labels,
        bulk.donor_ids,
        folds,
        layer=FULL_COHORT_LAYER,
        n_features=n_features,
        detail={"n_cells_total": int(bulk.n_cells.sum())},
    )

    caps = tuple(sorted({primary_cap, *sensitivity_caps}))
    sampled_rows = sample_nested_capped_cells(state.obs, state.keep_mask, caps=caps, seed=0)
    capped_runs: dict[int, dict[str, ModelRun]] = {}
    for cap in caps:
        rows = sampled_rows[cap]
        sample_hash = hashlib.sha256(np.asarray(rows, dtype="<i8").tobytes()).hexdigest()
        cell_obs = state.obs.iloc[rows]
        cell_labels = (cell_obs["disease"].astype(str) == POSITIVE_CONDITION).astype(int).to_numpy()
        cell_donors = cell_obs["donor_id"].astype(str).to_numpy()
        donor_counts = pd.Series(cell_donors).value_counts()
        detail = {
            "cap": cap,
            "sample_seed": 0,
            "sample_row_sha256": sample_hash,
            "n_cells": int(rows.size),
            "cells_per_donor_min": int(donor_counts.min()),
            "cells_per_donor_median": float(donor_counts.median()),
            "cells_per_donor_max": int(donor_counts.max()),
        }

        cap_mask = np.zeros_like(state.keep_mask, dtype=bool)
        cap_mask[rows] = True
        cap_bulk, cap_measurement = measure_stage(
            f"donor_pseudobulk_cap_{cap}",
            lambda current_mask=cap_mask: donor_pseudobulk(
                path,
                state.obs,
                current_mask,
                chr21_mapping=chr21,
            ),
            cells_per_donor_cap=cap,
            disk_path=path.parent,
            notes="same sampled cells as cap-matched RNA-only model",
        )
        state.resource.setdefault("measurements", []).append(cap_measurement.to_dict())
        cell_matrix = load_cell_matrix(path, rows)

        cap_models: dict[str, ModelRun] = {}
        if chr21 is not None and chr21.usable and cap_bulk.chr21_fraction is not None:
            cap_models["chr21_dosage"] = run_donor_level_model(
                "chr21_dosage",
                cap_bulk.chr21_fraction,
                cap_bulk.labels,
                cap_bulk.donor_ids,
                folds,
                layer=f"{CAPPED_LAYER}_{cap}",
                detail=detail
                | {
                    "mapping_sha256": chr21.mapping_sha256,
                    "n_chr21_genes": chr21.n_chr21_genes,
                },
            )
        else:
            reason = "chr21 mapping not verified" if chr21 is None else (chr21.reason or "unusable")
            cap_models["chr21_dosage"] = not_applicable_run(
                "chr21_dosage", reason, layer=f"{CAPPED_LAYER}_{cap}"
            )
        cap_models["pseudobulk_rna_logistic"] = run_donor_level_model(
            "pseudobulk_rna_logistic",
            cap_bulk.gene_sums,
            cap_bulk.labels,
            cap_bulk.donor_ids,
            folds,
            layer=f"{CAPPED_LAYER}_{cap}",
            n_features=n_features,
            detail=detail,
        )
        cap_models["rna_only"] = run_cell_level_model(
            "rna_only",
            cell_matrix,
            cell_labels,
            cell_donors,
            folds,
            n_features=n_features,
            layer=f"{CAPPED_LAYER}_{cap}",
            detail=detail,
        )
        capped_runs[cap] = cap_models
        for name, run in cap_models.items():
            runs[f"{name}_cap_{cap}"] = run

    multimodal_allowed = bool(state.atac_branch.get("multimodal_claim_allowed"))
    branch = state.atac_branch.get("branch")
    if not multimodal_allowed:
        reason = f"ATAC branch {branch}; multimodal models not applicable"
        for name in ("atac_only", "rna_atac_concat", "gated_fusion"):
            runs[name] = not_applicable_run(name, reason)

    margin = float(((state.estimand or {}).get("estimand") or {}).get("practical_margin") or 0.07)
    deltas = []
    for cap, cap_models in capped_runs.items():
        for name in ("chr21_dosage", "pseudobulk_rna_logistic"):
            if cap_models["rna_only"].status != "measured" or cap_models[name].status != "measured":
                continue
            deltas.append(
                paired_donor_delta(
                    cap_models["rna_only"], cap_models[name], margin=margin
                ).to_dict()
                | {"cap": cap}
            )

    state.model_runs = runs
    state.metrics_rows = [run.to_row() for run in runs.values()]
    state.paired_deltas = deltas
    state.same_cap_summary = summarize_same_cap_results(
        state.metrics_rows,
        deltas,
        primary_cap=primary_cap,
        margin=margin,
    )
    state.split = {
        **state.split,
        "donor_level_status": donor_split.status,
        "donor_level_overlap": donor_split.donor_overlap_count,
        "cell_level_status": donor_split.status,
        "cell_level_overlap": donor_split.donor_overlap_count,
        "shared_across_caps": True,
    }
    for run in runs.values():
        if run.status == "measured":
            state.evidence_buckets["verified_real"].append(
                f"{run.name} donor BA={run.balanced_accuracy}"
            )
        else:
            state.evidence_buckets["blocked_or_unknown"].append(f"{run.name}: {run.not_applicable}")

    state.headline.append(str(state.same_cap_summary["conclusion"]))
    state.evidence_buckets["verified_real"].append(
        "Same-cap comparison: " + str(state.same_cap_summary["status"])
    )
    return state


def run_real_interventions(
    h5ad_path: str | Path,
    state: RealAnalysisState,
    *,
    primary_cap: int = PRIMARY_CAP,
    n_features: int = 64,
) -> RealAnalysisState:
    """C29: held-out RNA interventions; ATAC/gate interventions NOT_APPLICABLE under B2b."""
    path = Path(h5ad_path)
    if state.obs is None or state.keep_mask is None:
        raise RuntimeError("QC must run before interventions")
    rows = sample_capped_cells(state.obs, state.keep_mask, primary_cap, seed=0)
    matrix = load_cell_matrix(path, rows)
    if hasattr(matrix, "tocsr"):
        mean = np.asarray(matrix.mean(axis=0)).ravel()
        mean_square = np.asarray(matrix.multiply(matrix).mean(axis=0)).ravel()
        variance = np.maximum(mean_square - mean**2, 0.0)
        selected = np.argsort(variance)[::-1][:n_features]
        dense = np.asarray(matrix[:, selected].todense())
    else:
        variance = np.asarray(matrix).var(axis=0)
        selected = np.argsort(variance)[::-1][:n_features]
        dense = np.asarray(matrix[:, selected])
    cell_obs = state.obs.iloc[rows]
    labels = (cell_obs["disease"].astype(str) == POSITIVE_CONDITION).astype(int).to_numpy()
    donors = cell_obs["donor_id"].astype(str).to_numpy()
    split = build_repeated_group_split_report(
        donors, labels, n_repeats=1, n_folds=5, base_seed=SEED
    )
    fold = split.folds[0]
    branch_reason = (
        f"ATAC branch {state.atac_branch.get('branch')}; "
        "two-view routing interventions not applicable"
    )
    effects = run_rna_only_interventions(
        dense[fold.train_index],
        labels[fold.train_index],
        dense[fold.test_index],
        labels[fold.test_index],
        donors[fold.test_index],
        branch_reason=branch_reason,
        seed=0,
    )
    state.intervention_rows = intervention_rows(effects)
    state.evidence_buckets["verified_real"].append(
        f"C29 RNA-only interventions on held-out donors (n_test_cells={int(fold.test_index.size)})"
    )
    state.evidence_buckets["blocked_or_unknown"].append(
        "C29 multimodal routing interventions NOT_APPLICABLE under B2b"
    )
    return state


def run_real_validation(h5ad_path: str | Path, state: RealAnalysisState) -> RealAnalysisState:
    """C30: frozen marker panels on held-out donors; external matrix remains UNKNOWN."""
    path = Path(h5ad_path)
    if state.obs is None or state.keep_mask is None:
        raise RuntimeError("QC must run before validation")
    chr21 = _chr21_from_schema(state.schema)
    if state.bulk is None:
        bulk = donor_pseudobulk(path, state.obs, state.keep_mask, chr21_mapping=chr21)
    else:
        bulk = state.bulk
    log_cpm = _log_cpm(bulk.gene_sums)
    symbols = symbol_series(read_var(path))
    cell_donors = state.obs.loc[state.keep_mask, "donor_id"].astype(str).to_numpy()
    cell_labels = (
        (state.obs.loc[state.keep_mask, "disease"].astype(str) == POSITIVE_CONDITION)
        .astype(int)
        .to_numpy()
    )
    split = build_repeated_group_split_report(
        cell_donors, cell_labels, n_repeats=1, n_folds=5, base_seed=SEED
    )
    held_out = set(split.folds[0].test_donors)
    dosage = evaluate_panel(
        CHR21_DOSAGE_PANEL_NAME,
        CHR21_DOSAGE_PANEL,
        "up_in_trisomy_21",
        log_cpm,
        symbols,
        bulk.labels,
        bulk.donor_ids,
        held_out,
    )
    control = evaluate_panel(
        CONTROL_PANEL_NAME,
        CONTROL_PANEL,
        "no_systematic_shift",
        log_cpm,
        symbols,
        bulk.labels,
        bulk.donor_ids,
        held_out,
    )
    geo = check_geo_accession("GSE280175")
    validation = build_validation_report(
        marker_set=CHR21_DOSAGE_PANEL_NAME,
        findings_available=True,
        approval_present=True,
        external_matrix_ingested=False,
        internal_holdout_measured=True,
    )
    state.panel_rows = [dosage.to_row(), control.to_row(), geo]
    state.validation = validation.to_dict()
    state.validation_rows = [
        item.to_dict() | {"gate_status": validation.status} for item in validation.resources
    ] + state.panel_rows
    state.evidence_buckets["verified_real"].append(
        "C30 internal held-out panels measured; "
        f"GSE280175 listed={geo.get('listed')} matrix_ingested=False"
    )
    state.evidence_buckets["blocked_or_unknown"].append(
        "C30 independent multimodal validation UNKNOWN; RNA-only external matrix not ingested"
    )
    state.headline.append(
        f"G8={validation.status}: internal panels measured; "
        "external matrix/predictive validation UNKNOWN/INCONCLUSIVE"
    )
    return state


def run_external_rna_replication(
    h5ad_path: str | Path,
    external_xlsx: str | Path,
    *,
    state: RealAnalysisState | None = None,
    approval_present: bool = False,
    expected_sha256: str | None = None,
    n_bootstrap: int = 1_000,
    n_permutations: int = 1_000,
    seed: int = 22,
) -> dict[str, Any]:
    """Append four summary-effect rows in place; never upgrade external G8.

    The approval argument is the existing per-run attestation, not an amendment
    of the historical approval policy. An alternate workbook hash is explicit
    for fixture verification; the canonical run always uses the pinned source.
    """
    import time

    import h5py
    from anndata.io import read_elem

    from p22.data.census import sha256_file
    from p22.eval.external_validation import (
        COMPARISONS,
        EVIDENCE_SCOPE,
        EXTERNAL_ACCESSION,
        EXTERNAL_SHA256,
        collapse_donor_metadata,
        compare_effect_directions,
        fit_discovery_effects,
        load_external_effects,
        summarize_headline_outcome,
    )

    started = time.perf_counter()
    state = RealAnalysisState() if state is None else state
    source_hash = expected_sha256 or EXTERNAL_SHA256
    rows = [
        {
            "analysis": "external_rna_direction_replication",
            "discovery_population": population,
            "primary_labels": "|".join(labels),
            "external_population": sheet,
            "external_accession": EXTERNAL_ACCESSION,
            "external_sha256": None,
            "expected_external_sha256": source_hash,
            "evidence_scope": EVIDENCE_SCOPE,
            "execution_status": "failed",
            "scientific_outcome": "not_evaluated",
            "headline_outcome": "not_evaluated",
            "external_matrix_ingested": False,
        }
        for population, labels, sheet in COMPARISONS
    ]
    result: dict[str, Any] = {
        "rows": rows,
        "gene_tables": {},
        "external_matrix_ingested": False,
        "execution_status": "failed",
        "headline_outcome": "not_evaluated",
        "approval_attested": approval_present is True,
        "protocol": {
            "pcw_range": [13, 19],
            "min_cells_per_donor": 50,
            "n_bootstrap": n_bootstrap,
            "n_permutations": n_permutations,
            "seed": seed,
            "top_n": 100,
            "min_shared_genes": 500,
        },
    }
    try:
        if approval_present is not True:
            raise ValueError("explicit per-run professor approval attestation required")
        path = Path(h5ad_path)
        with h5py.File(path, "r") as handle:
            source_obs = read_elem(handle["obs"])
            var = read_elem(handle["var"])
            raw_var = read_elem(handle["raw/var"])
            if not raw_var.index.equals(var.index):
                raise ValueError("raw count gene order differs from var")
            result["data_mode"] = (
                read_elem(handle["uns/data_mode"])
                if "uns/data_mode" in handle
                else "real_public_summary_replication"
            )
        external = load_external_effects(
            external_xlsx, gene_metadata=var, expected_sha256=source_hash
        )
        for row in rows:
            row["external_sha256"] = source_hash
        result["primary_sha256"] = sha256_file(path)
        if state.obs is None or state.keep_mask is None:
            run_schema_qc_census(path, state)
        if state.qc.get("status") != "PASS":
            raise ValueError("primary cohort QC did not pass")
        obs = state.obs
        columns = ["donor_id", "disease", "dev_PCW", "sex", "author_cell_type"]
        if not obs.index.equals(source_obs.index) or not obs[columns].astype("string").equals(
            source_obs[columns].astype("string")
        ):
            raise ValueError("QC metadata does not match source cell order and annotations")
        keep = np.asarray(state.keep_mask)
        if keep.dtype != bool or keep.shape != (len(obs),):
            raise ValueError("QC keep mask must be row-aligned boolean values")
        collapse_donor_metadata(obs.loc[keep])
        window = keep & pd.to_numeric(obs.dev_PCW).between(13, 19).to_numpy()
        streams = np.random.SeedSequence(seed).spawn(len(COMPARISONS))
        discovery = {}
        for row, (population, labels, sheet), stream in zip(
            rows, COMPARISONS, streams, strict=True
        ):
            if population not in discovery:
                mask = window & obs.author_cell_type.isin(labels).to_numpy()
                bulk = donor_pseudobulk(path, obs, mask)
                metadata = collapse_donor_metadata(obs.loc[mask], bulk.donor_ids)
                discovery[population] = (fit_discovery_effects(bulk, metadata, var), bulk)
            fitted, bulk = discovery[population]
            comparison = compare_effect_directions(
                fitted,
                external[sheet],
                n_bootstrap=n_bootstrap,
                n_permutations=n_permutations,
                seed=stream,
            )
            result["gene_tables"][sheet] = comparison.pop("joined_effects")
            row.update(comparison)
            row.update(
                primary_cells=int(bulk.n_cells.sum()),
                min_cells_per_donor=int(bulk.n_cells.min()),
                donor_ids=list(bulk.donor_ids),
            )
        failed = [row["reason"] for row in rows if row["execution_status"] != "completed"]
        if failed:
            raise ValueError("; ".join(failed))
        result["headline_outcome"] = summarize_headline_outcome(rows)
        result["execution_status"] = "completed"
        state.validation["processed_rna_summary"] = {
            "execution_status": "completed",
            "headline_outcome": result["headline_outcome"],
            "external_sha256": source_hash,
            "evidence_scope": EVIDENCE_SCOPE,
            "external_matrix_ingested": False,
        }
        for row in rows:
            row["headline_outcome"] = result["headline_outcome"]
    except (ValueError, RuntimeError, OSError, KeyError, np.linalg.LinAlgError) as exc:
        # A partial execution is not a four-comparison scientific conclusion.
        for row in rows:
            row.update(
                execution_status="failed",
                scientific_outcome="not_evaluated",
                headline_outcome="not_evaluated",
                reason=str(exc),
            )
        result["reason"] = str(exc)
    result["wall_seconds"] = time.perf_counter() - started
    result["peak_rss_gb"] = peak_rss_gb()
    state.validation_rows.extend(rows)
    return result
