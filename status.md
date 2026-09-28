# P22 current status

Updated: 2026-09-28 14:15 PDT. Read this first, then [document index](docs/INDEX.md). This is a snapshot, not permission to run an experiment or change a scientific gate. For live work, recheck the linked status and verifier files before acting.

Companion research vault: [vault status](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/status.md>) and [vault MOM index](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/MOM/README.md>).

## Current work: NN v2

| Item | State | Evidence |
|---|---|---|
| Professor guidance | About 100% implemented for the NN-v2 assignment scope; ~96% supported by completed evidence (claim limits: PC N/A; chr21 score export DEFERRED; N21 secondary). These are task-based estimates, not scientific metrics. | [Direction-to-task map](tasks/nn/plan.md#1-what-the-professor-asked-and-how-this-plan-answers-it), [July meeting records](MOM/README.md), [framing](paper/framing.md), [self-review](paper/self_review.md), [NN_V2_RESULTS](docs/nn_v2/NN_V2_RESULTS_2026-09-23.md) |
| Main real-data ladder | Canonical is now **ladder_v3** (450/450) after v5 shared-path control-fit fix; `ladder_v2` retained. | [Run record](reports/generated/nn_20260923/ladder_v3/run.json), [CANONICAL_LADDER](docs/nn_v2/v5/CANONICAL_LADDER.txt), [verifier](docs/nn_v2/ladder_verification.json) |
| Ladder gate | **PASS** on ladder_v3. Outcome still `B_NULL`: primary R3_ca−R3_tc estimate ≈ 0.0267, CI includes 0 (summary ≈ [−0.0267, 0.0770]; verifier ≈ [−0.0250, 0.0768]). No complex-model superiority claim. chr21_dosage AUROC 1.0; majority pooled-BA caveat remains. V1–V4 + P1 (N11–N17) + P2 + P3 + P4 + P5 DONE; P6 and `v5_gate` still open. P2: no CA_FAVOURED on gene-matched S6. P3: chr21-excluded spectrum `SPECTRUM_NULL`. P4: results doc §§5–7 + unsent note. P5: `PROFESSOR_UPDATE_v5.md` D1–D13 table (unsent). | [Saved summary](docs/nn_v2/ladder_summary.json), [verifier](docs/nn_v2/ladder_verification.json), [LADDER.md](docs/nn_v2/LADDER.md), [NN_V2_RESULTS](docs/nn_v2/NN_V2_RESULTS_2026-09-23.md), [v5 per-fold](docs/nn_v2/v5/per_fold_metrics.json), [P3 spectrum](docs/nn_v2/v5/spectrum_chr21_excluded.json), [P5 update](docs/nn_v2/v5/PROFESSOR_UPDATE_v5.md) |
| Downstream NN work | **N11**–**N17** refreshed on `ladder_v3` (`chr21_excluded_v3` `DOSAGE_DOMINATED`; `seeds_v3` `SPREAD_ONLY`; `faithfulness_v3` NC=0, tags `CA_PAIRING_UNUSED`/`ATAC_USED`; `nuisance_v3` `R2_REJECTED`/`PROBE_DROP_INSUFFICIENT`; `spectrum_v3` 120k OOF + 60k chr21-excluded EXPORTED; N16 `SPECTRUM_NULL` with chr21 compare `COMPARED`/`SPECTRUM_NULL`; N17 `routing_v3` folds_used=75, all tags `NOT_SHOWN_USED`). **P2** no `CA_FAVOURED` on gene-matched S6. **P3** chr21-excluded spectrum `SPECTRUM_NULL` (9 eligible). **P4** results doc + unsent note refreshed for ladder_v3 / V1–V4 / P2 / P3. **P5** professor update with D1–D13 coverage table. Optional **N21** + **N22**–**N25** + **N27** + **N29**–**N34** accepted under prior ladder. Draft label `DRAFT_V1_COMPLETE`. Study remains `STUDY_PARTIAL`. | [chr21_excluded](docs/nn_v2/chr21_excluded.json), [seed_sensitivity](docs/nn_v2/seed_sensitivity.json), [faithfulness](docs/nn_v2/faithfulness.json), [nuisance_probe](docs/nn_v2/nuisance_probe.json), [cell_scores_export](docs/nn_v2/cell_scores_export.json), [spectrum](docs/nn_v2/spectrum.json), [P3 spectrum](docs/nn_v2/v5/spectrum_chr21_excluded.json), [routing_attention](docs/nn_v2/routing_attention.json), [P5 update](docs/nn_v2/v5/PROFESSOR_UPDATE_v5.md), [ROBUSTNESS](docs/nn_v2/ROBUSTNESS.md), [NN_V2_RESULTS](docs/nn_v2/NN_V2_RESULTS_2026-09-23.md), [Main task status](tasks/nn/todo.md) |
| Paper | Framing **F4**; figures **fig1–fig5**; Results/Discussion/Abstract rewritten; **N31** checker PASS; **N32** self-review; **N33** vault `paper-nn/` copy; **N34** final verification PASS (`pytest` 1192; `check_paper` 5/5). Header `DRAFT_V1_COMPLETE`. | [framing](paper/framing.md), [self-review](paper/self_review.md), [Draft](paper/draft.md), [claims](paper/claims.csv), vault `paper-nn/` |
| Old swarm | `p22agy4` kept hitting Gemini quota limits. Stopped at 13:44 PDT; tmux session and Python driver no longer running. Saved lane branches/outputs remain for verification. | [Swarm log](reports/generated/nn_agy/latest/swarm.log), [lane status](reports/generated/nn_agy/latest/status.json) |
| Manual GNHF finish | [Runbook](tasks/nn/GNHF_FINISH_RUNBOOK.md) on `codex/p22-nn-finish-base` reached N34. S6–S9 through N34 done pending independent Codex review. | [Runbook](tasks/nn/GNHF_FINISH_RUNBOOK.md), [self-review](paper/self_review.md), [saved gate](docs/nn_v2/ladder_verification.json) |

**Resolved conflict:** N10 task label previously said DONE while the S6 hard gate said FAIL. Gate now `PASS` with rebuilt summary from all 450 fold files; N10 scientific result accepted as `B_NULL`.

## Other study tracks

- Earlier paired multiome study: corrected internal comparison is an accepted null within its own protocol; external paired validation remains unperformed. It is **not** the NN-v2 ladder. See [corrected handoff](MOM/2026-09-21/GNHF_P22_CORRECTED_RESULTS_AND_HANDOFF.md).
- Professor meeting records stay in [MOM](MOM/README.md), separate from plans and experiment outputs. June and July transcripts live in the linked Obsidian vault; September execution handoffs live here.
- Historical July [HANDOFF.md](HANDOFF.md) and September [session handoff](docs/P22_SESSION_HANDOFF_2026-09-23.md) are dated snapshots, not current status.

## Next verified milestones

1. Independent Codex review of the finish-base branch evidence and paper deliverables.
2. Do not mark the professor note as sent; leave the unsent 2026-09-27 packet untouched.

## Status maintenance

Update this file after an accepted gate, material blocker, or final result. Include date, direct evidence links, and any disagreement between task labels and checks. Avoid updates for every quota retry. For scientific claims, verified raw evidence and gates outrank task labels; task labels outrank narrative handoffs.
