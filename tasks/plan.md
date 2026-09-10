# Paired DS multiome development plan

Updated: 2026-09-08. Status: retained-cell ingestion, donor-aware networks, final
saved models/scalers and one-shot scoring implemented. 150 synthetic internal fits
plus six final refits verified. Real-data scientific gates remain pending.

## Scope

Extend P22 toward real RNA+ATAC comparisons using GSE305146 for development and Vuong/NeMO as the reserved external candidate. The scientific contract and source evidence live in [the dataset proposal](../docs/PAIRED_DS_MULTIOME_DATASET_OPTIONS.md). This plan does not replace [external RNA replication](../docs/EXTERNAL_RNA_REPLICATION_PLAN.md) or change historical results or legacy plan-guard state.

The ingestion/compatibility report is available through [the audit guide](../docs/PAIRED_MULTIOME_AUDIT.md).
The [training guide](../docs/PAIRED_MULTIOME_TRAINING.md) records donor-aware selection,
genuine cross-attention, matched token concatenation, paired uncertainty, and a completed
synthetic benchmark, final refit and reload/scoring. The author's filtered library
table now exactly matches final-release membership. Real-data training still depends on an accepted cohort, valid ATAC
representation and frozen scientific protocol. The user has now reported professor
approval through the [scoped per-run attestation](../plan/real_data_attestation_2026-09-08.json);
the actual professor approval date remains unknown and historical policy is unchanged.

## Decisions

- NeMO's 3,731 RNA `Unk` rows explain the count difference exactly. Record this candidate reconciliation separately from unresolved upstream QC; do not apply it as an accepted exclusion without source evidence.
- Map all GSE305146 libraries to biological donors and retained cells. Check specimen provenance across studies; different donor names do not establish independence.
- Normalize documented obstetric GW to approximate PCW with an explicit minus-two conversion. Preserve original values and unresolved units.
- Require common measured ATAC regions/count semantics for confirmatory evaluation. Peak-derived gene scores can support an exploratory pilot; exact recounting and its resource budget remain possible.
- Primary proposed question: external donor balanced-accuracy improvement of cross-attention over concatenation. Keep chromosome-21 dosage and simpler controls; record negative/inconclusive outcomes without changing the endpoint.
- Reuse donor splits, aggregation, resource reporting, preprocessing fingerprints, baseline/gated models, and training code. Add donor-level checkpoint scoring and a real-data adapter without removing synthetic-only safeguards from the existing synthetic runner.
- Implement genuine cross-attention separately from gating, with multiple key/value tokens, explicit token construction, and matched concatenation controls.

## Ordered tasks

All task state, acceptance criteria, likely files, and verification are in [todo.md](todo.md).

1. M1 — Source release, QC, and specimen contract.
2. M2 — Developmental-age normalization.
3. M3 — Bounded paired sparse ingestion.
4. M4 — Shared ATAC feature compatibility.
5. M5 — Freeze donor-level research protocol.
6. M6 — Donor-aware baseline training adapter.
7. M7 — Explicit cross-attention comparison.
8. M8 — Locked external evaluation and report.

Checkpoints follow M1–M2, M3–M4, M5–M6, and M7–M8. M3 diagnostics can proceed with unresolved release questions, but confirmatory training/evaluation cannot bypass their relevant gates. No external predictive result may choose preprocessing, thresholds, or architecture.

## Remaining evidence requirements

The dataset proposal addresses all six review findings, but the empirical questions remain open: release/QC reconciliation, specimen provenance, age conventions, compatible ATAC counts, resource measurements, and whether an attention model adds value with 30 development donors and at most 26 external donors. Architectural hyperparameters and approximation acceptance limits must be written into the protocol before fitting/evaluation; they are not implicit defaults.

The [2026-09-08 source check](../docs/PAIRED_MULTIOME_REMAINING_EVIDENCE_2026-09-08.md)
now documents UCLA/NIH procurement versus HDBR and the exact annotation count match.
The executable audit reports these findings without certifying specimen identity,
reproduced QC, or compatible ATAC counts. Original RNA replication is implemented
and [executed locally](../docs/EXTERNAL_RNA_REPLICATION_RESULTS_2026-09-08.md): all
four comparisons are inconclusive, with exactly matching results in three runs.
Original RNA Tasks 1–5 are complete: fresh free-CPU Colab archive retrieved, hashes
verified and results exactly matched locally (2026-09-09). Approval remains recorded.
RNA results cannot satisfy paired-data gates.

## Completion evidence

A completed extension has versioned input/QC/feature/protocol manifests, passing focused integrity tests, donor-disjoint internal results, clearly labeled model families, and an external report with uncertainty and limitations. A failed compatibility or independent-evaluation check is reported explicitly; it is not converted into a successful multimodal claim.
