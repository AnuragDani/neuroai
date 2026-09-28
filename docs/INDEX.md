# P22 document index

Start at [current status](../status.md). This index points to one entry per job; dated records remain available but do not override current evidence.

| Need | Open | Role |
|---|---|---|
| What is happening now? | [status.md](../status.md) | Current snapshot, blockers, next milestones |
| What did professor ask? | [MOM index](../MOM/README.md), [direction map](../tasks/nn/plan.md#1-what-the-professor-asked-and-how-this-plan-answers-it) | Original meeting sources and task mapping |
| What is NN-v2 protocol? | [Protocol freeze](nn_v2/PROTOCOL_FREEZE.md), [NN plan](../tasks/nn/plan.md) | Frozen scientific design |
| What has NN-v2 produced? | [Ladder verifier](nn_v2/ladder_verification.json), [v4 stage plan](../tasks/nn/swarm/plan_v4_agy.md) | Gate result and remaining work; verifier PASS (`B_NULL`) |
| How do I finish NN v2 with GNHF? | [Manual finish runbook](../tasks/nn/GNHF_FINISH_RUNBOOK.md) | Preflight, manual command, IF/ELSE completion rules; S6–S9 through N34 done (`DRAFT_V1_COMPLETE`) |
| Where are NN-v2 written results? | [NN_V2_RESULTS_2026-09-23.md](nn_v2/NN_V2_RESULTS_2026-09-23.md), [PROFESSOR_NOTE_UNSENT.md](nn_v2/PROFESSOR_NOTE_UNSENT.md) | N22–N23: B_NULL + `NN_ASSIGNMENT_COMPLETE`; note unsent |
| Where is robustness evidence? | [chr21_excluded.json](nn_v2/chr21_excluded.json), [seed_sensitivity.json](nn_v2/seed_sensitivity.json), [ROBUSTNESS.md](nn_v2/ROBUSTNESS.md) | N11 DOSAGE_DOMINATED; N12 SPREAD_ONLY (seeds_v2 fixed protocol) |
| Where is faithfulness evidence? | [faithfulness.json](nn_v2/faithfulness.json), [FAITHFULNESS.md](nn_v2/FAITHFULNESS.md) | N13: NC=0; CA_PAIRING_UNUSED; ATAC_USED; PC N/A |
| Where is nuisance-probe evidence? | [nuisance_probe.json](nn_v2/nuisance_probe.json), [NUISANCE_PROBE.md](nn_v2/NUISANCE_PROBE.md) | N14: R2_REJECTED; PROBE_DROP_INSUFFICIENT; library unscorable |
| Where are per-cell scores? | [cell_scores_export.json](nn_v2/cell_scores_export.json), [CELL_SCORES.md](nn_v2/CELL_SCORES.md), [donor_celltype_scores.csv.gz](nn_v2/donor_celltype_scores.csv.gz) | N15: 120k OOF rows from ladder_v2; 5 repeats/arm asserted |
| Where is the cell-state spectrum? | [spectrum.json](nn_v2/spectrum.json), [SPECTRUM.md](nn_v2/SPECTRUM.md) | N16: SPECTRUM_NULL on ladder_v2 R3_ca (9 eligible); interpret LOCALIZED superseded |
| Where are attention readouts? | [routing_attention.json](nn_v2/routing_attention.json), [ROUTING_ATTENTION.md](nn_v2/ROUTING_ATTENTION.md) | N17: all readouts NOT_SHOWN_USED (I4/I6 CIs include 0) |
| Where is gene-activity secondary? | [gene_activity_results.json](nn_v2/gene_activity_results.json), [GENE_ACTIVITY.md](nn_v2/GENE_ACTIVITY.md) | N21: GA_B_NULL; 500-gene amendment; secondary only |
| Where is paper? | [framing.md](../paper/framing.md), [claims.csv](../paper/claims.csv), [self_review.md](../paper/self_review.md), [figures/](../paper/figures/), [Draft](../paper/draft.md), [paper tasks](../tasks/nn/todo.md) | N24–N34: F4 through final verification; `check_paper` PASS; `DRAFT_V1_COMPLETE`; vault `paper-nn/` synced |
| What happened in earlier paired study? | [Corrected handoff](../MOM/2026-09-21/GNHF_P22_CORRECTED_RESULTS_AND_HANDOFF.md), [paired audit](PAIRED_MULTIOME_AUDIT.md) | Separate study and input decisions |
| What happened in RNA replication? | [External RNA results](EXTERNAL_RNA_REPLICATION_RESULTS_2026-09-08.md), [donor influence](RNA_DONOR_INFLUENCE_RESULTS_2026-09-10.md) | Earlier completed analyses |
| Where are source runs/logs? | [`reports/generated/`](../reports/generated/) | Raw, mostly ignored output; use specific links from status/evidence docs |
| What were past decisions? | [Decision log](decision_log.md), [MOM index](../MOM/README.md) | Dated decisions and source meetings |

## Filing rule

- `status.md`: current cross-project truth, updated at meaningful gates.
- `MOM/YYYY-MM-DD/`: meeting records and dated execution handoffs. Keep MOM first-class; distinguish professor statements from worker summaries.
- `tasks/`: plans, checklists, and machine-readable task status.
- `docs/nn_v2/` and other study docs: protocols, analyses, verified summaries. Mark superseded material explicitly.
- `paper/`: manuscript and its claim ledger. `reports/generated/`: raw outputs, not hand-edited narrative.

Current paths stay in place while swarm runs: code and task checks reference them. When run ends, move study documents only with link/path checks and a clear old-to-new map. Do not treat a move as a new scientific result.
