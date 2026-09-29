# P22 current status

Updated: 2026-09-27 15:52 PDT. Read this first, then [document index](docs/INDEX.md). This is a snapshot, not permission to run an experiment or change a scientific gate. For live work, recheck the linked status and verifier files before acting.

Companion research vault: [vault status](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/status.md>) and [vault MOM index](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/MOM/README.md>).

## Current work: NN v2

| Item | State | Evidence |
|---|---|---|
| Professor guidance | About 60% implemented, 30–40% supported by completed evidence. Cell-state spectrum remains missing. These are task-based estimates, not scientific metrics. | [Direction-to-task map](tasks/nn/plan.md#1-what-the-professor-asked-and-how-this-plan-answers-it), [July meeting records](MOM/README.md) |
| Main real-data ladder | 450/450 expected fold outputs produced. Training run complete; result **not accepted**. | [Run record](reports/generated/nn_20260923/ladder_v2/run.json), [verifier](docs/nn_v2/ladder_verification.json) |
| Ladder gate | **FAIL**. Saved summary says contrast 0, CI [0, 0]; independent fold-file recomputation says −0.0067, CI [−0.0528, 0.0348]. Recomputed values are provisional until gate passes. | [Saved summary](docs/nn_v2/ladder_summary.json), [verifier](docs/nn_v2/ladder_verification.json) |
| Downstream NN work | Main checklist remains stale. Running GNHF branch `codex/p22-nn-finish-base` has committed N11–N17 through eight iterations; independent final review and integration remain pending. N21 is in progress there. | [Main task status](tasks/nn/todo.md), [finish runbook](tasks/nn/GNHF_FINISH_RUNBOOK.md) |
| Paper | [Draft](paper/draft.md) exists but says real-data ladder never ran. Its current-result sections need rewriting; `paper/check_paper.py` currently fails number/claims checks. | [Draft](paper/draft.md), [paper task list](tasks/nn/todo.md) |
| Old swarm | `p22agy4` kept hitting Gemini quota limits. Stopped at 13:44 PDT; tmux session and Python driver no longer running. Saved lane branches/outputs remain for verification. | [Swarm log](reports/generated/nn_agy/latest/swarm.log), [lane status](reports/generated/nn_agy/latest/status.json) |
| Manual GNHF finish | **Running** in isolated branch `codex/p22-nn-finish-base`. Its verifier says `PASS`, primary outcome `B_NULL`, and N11–N17 have committed; these have not been merged or independently reviewed. This main checkout's saved gate still says `FAIL`. | [Runbook](tasks/nn/GNHF_FINISH_RUNBOOK.md), [main saved gate](docs/nn_v2/ladder_verification.json) |

**Conflict to resolve:** `tasks/nn/status/N10` says DONE, but the S6 hard gate and `ladder_verification.json` say FAIL. Treat N10's scientific result as unaccepted until the gate passes. Do not cite `docs/nn_v2/LADDER.md` or the saved summary as final results.

## Other study tracks

- Earlier paired multiome study: corrected internal comparison is an accepted null within its own protocol; external paired validation remains unperformed. It is **not** the NN-v2 ladder. See [corrected handoff](MOM/2026-09-21/GNHF_P22_CORRECTED_RESULTS_AND_HANDOFF.md).
- Professor meeting records stay in [MOM](MOM/README.md), separate from plans and experiment outputs. June and July transcripts live in the linked Obsidian vault; September execution handoffs live here.
- Historical July [HANDOFF.md](HANDOFF.md) and September [session handoff](docs/P22_SESSION_HANDOFF_2026-09-23.md) are dated snapshots, not current status.
- For the next professor update, first read [packet status](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/external_shared/STATUS.md>) and [packet guide](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/UPDATE_GUIDE.md>). The last confirmed **sent** update remains August 16; the September 27 packet is prepared but unsent.

## Next verified milestones

1. Reconcile ladder summary with all fold files; rerun `gnhf/verify_ladder.py` and require `PASS`.
2. Recheck and integrate N11/N12; finish remaining S7 work with evidence and explicit BLOCKED labels where needed.
3. Complete S8 results and S9 paper from verified numbers; pass paper checker and evidence gate before vault copy.

## Status maintenance

Update this file after an accepted gate, material blocker, or final result. Include date, direct evidence links, and any disagreement between task labels and checks. Avoid updates for every quota retry. For scientific claims, verified raw evidence and gates outrank task labels; task labels outrank narrative handoffs.
