# P22 current status

Updated: 2026-09-28 02:45 PDT. Read this first, then [document index](docs/INDEX.md). This is a snapshot, not permission to run an experiment or change a scientific gate. For live work, recheck the linked status and verifier files before acting.

Companion research vault: [vault status](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/status.md>) and [vault MOM index](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/MOM/README.md>).

## Current work: NN v2

| Item | State | Evidence |
|---|---|---|
| Professor guidance | About 80% implemented, ~70% supported by completed evidence. Results verified (N23); paper draft still stale pending N24–N34. These are task-based estimates, not scientific metrics. | [Direction-to-task map](tasks/nn/plan.md#1-what-the-professor-asked-and-how-this-plan-answers-it), [July meeting records](MOM/README.md), [NN_V2_RESULTS](docs/nn_v2/NN_V2_RESULTS_2026-09-23.md) |
| Main real-data ladder | 450/450 expected fold outputs produced. Training run complete; **S6 gate accepted**. | [Run record](reports/generated/nn_20260923/ladder_v2/run.json), [verifier](docs/nn_v2/ladder_verification.json) |
| Ladder gate | **PASS**. Outcome `B_NULL`: primary R3_ca−R3_tc estimate −0.0067, CI includes 0 (summary ≈ [−0.0533, 0.0348]; verifier recomputed ≈ [−0.0528, 0.0348]). No complex-model superiority claim. Model-free chr21 dosage AUROC ≈ 0.998; majority pooled-BA caveat remains. | [Saved summary](docs/nn_v2/ladder_summary.json), [verifier](docs/nn_v2/ladder_verification.json), [LADDER.md](docs/nn_v2/LADDER.md) |
| Downstream NN work | **N11**–**N17** + optional **N21** + **N22** + **N23** accepted. Final label `NN_ASSIGNMENT_COMPLETE` (claim limits: PC N/A, chr21 score export DEFERRED). **N24**–**N34** paper phase remain. | [NN_V2_RESULTS](docs/nn_v2/NN_V2_RESULTS_2026-09-23.md), [Main task status](tasks/nn/todo.md) |
| Paper | [Draft](paper/draft.md) still says real-data ladder never ran; rewrite in S9 from N22/verified JSON. `paper/check_paper.py` currently fails number/claims checks. `paper/make_figures.py` P2 API restored for tests; Fig 3–5 builders deferred to N25. | [Draft](paper/draft.md), [results](docs/nn_v2/NN_V2_RESULTS_2026-09-23.md), [paper task list](tasks/nn/todo.md) |
| Old swarm | `p22agy4` kept hitting Gemini quota limits. Stopped at 13:44 PDT; tmux session and Python driver no longer running. Saved lane branches/outputs remain for verification. | [Swarm log](reports/generated/nn_agy/latest/swarm.log), [lane status](reports/generated/nn_agy/latest/status.json) |
| Manual GNHF finish | [Runbook](tasks/nn/GNHF_FINISH_RUNBOOK.md) active on `codex/p22-nn-finish-base`. S6–S8 through N23 done; next S9 paper (N24–N34). | [Runbook](tasks/nn/GNHF_FINISH_RUNBOOK.md), [saved gate](docs/nn_v2/ladder_verification.json), [results](docs/nn_v2/NN_V2_RESULTS_2026-09-23.md) |

**Resolved conflict:** N10 task label previously said DONE while the S6 hard gate said FAIL. Gate now `PASS` with rebuilt summary from all 450 fold files; N10 scientific result accepted as `B_NULL`.

## Other study tracks

- Earlier paired multiome study: corrected internal comparison is an accepted null within its own protocol; external paired validation remains unperformed. It is **not** the NN-v2 ladder. See [corrected handoff](MOM/2026-09-21/GNHF_P22_CORRECTED_RESULTS_AND_HANDOFF.md).
- Professor meeting records stay in [MOM](MOM/README.md), separate from plans and experiment outputs. June and July transcripts live in the linked Obsidian vault; September execution handoffs live here.
- Historical July [HANDOFF.md](HANDOFF.md) and September [session handoff](docs/P22_SESSION_HANDOFF_2026-09-23.md) are dated snapshots, not current status.

## Next verified milestones

1. S9 paper (N24–N34) from verified numbers; pass paper checker and evidence gate before vault copy.
2. Final vault paper copy only after N32 and decision-tree N33 allow-list.

## Status maintenance

Update this file after an accepted gate, material blocker, or final result. Include date, direct evidence links, and any disagreement between task labels and checks. Avoid updates for every quota retry. For scientific claims, verified raw evidence and gates outrank task labels; task labels outrank narrative handoffs.
