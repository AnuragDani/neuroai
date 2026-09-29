# P22 current status

Updated: 2026-09-28 19:20 PDT. Read this first, then [document index](docs/INDEX.md). This is a snapshot, not permission to run an experiment or change a scientific gate. For live work, recheck the linked status and verifier files before acting.

Companion research vault: [vault status](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/status.md>) and [vault MOM index](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/MOM/README.md>).

## Current work: NN v2

| Item | State | Evidence |
|---|---|---|
| Professor guidance | About 100% implemented for the NN-v2 assignment scope; ~96% supported by completed evidence (claim limits: PC N/A; N21 secondary; external validation deferred T13). These are task-based estimates, not scientific metrics. | [Direction-to-task map](tasks/nn/plan.md#1-what-the-professor-asked-and-how-this-plan-answers-it), [July meeting records](MOM/README.md), [framing](paper/framing.md), [self-review](paper/self_review.md), [NN_V2_RESULTS](docs/nn_v2/NN_V2_RESULTS_2026-09-23.md), [v6 update](docs/nn_v2/v6/PROFESSOR_UPDATE_v6.md) |
| Main real-data ladder | Canonical is now **ladder_v3** (450/450) after v5 shared-path control-fit fix; `ladder_v2` retained. | [Run record](reports/generated/nn_20260923/ladder_v3/run.json), [CANONICAL_LADDER](docs/nn_v2/v5/CANONICAL_LADDER.txt), [verifier](docs/nn_v2/ladder_verification.json) |
| Ladder gate | **PASS** on ladder_v3. Primary outcome still `B_NULL`: R3_ca−R3_tc estimate ≈ 0.0267, CI includes 0. V1–V4 + P1–P6 DONE. Paper header `DRAFT_V3_COMPLETE`. **`python3 gnhf/v5_gate.py` → `V5_GATE PASS`.** v6 X1–X6 DONE; X7 merge/push pending after conflict prep. | [Saved summary](docs/nn_v2/ladder_summary.json), [verifier](docs/nn_v2/ladder_verification.json), [NN_V2_RESULTS](docs/nn_v2/NN_V2_RESULTS_2026-09-23.md), [P5 update](docs/nn_v2/v5/PROFESSOR_UPDATE_v5.md), [v6 update](docs/nn_v2/v6/PROFESSOR_UPDATE_v6.md), [Draft](paper/draft.md) |
| Downstream NN work | **N11**–**N17** refreshed on `ladder_v3`. **P2** no `CA_FAVOURED` on gene-matched S6. **P3** chr21-excluded spectrum `SPECTRUM_NULL`. **P4**–**P5** results + professor coverage table. **P6**/`X6` paper revision (`DRAFT_V3_COMPLETE`, fig6–fig7, vault synced). Study remains `STUDY_PARTIAL`. | [chr21_excluded](docs/nn_v2/chr21_excluded.json), [spectrum](docs/nn_v2/spectrum.json), [P3 spectrum](docs/nn_v2/v5/spectrum_chr21_excluded.json), [v6 chr21-forced](docs/nn_v2/v6/CHR21_FORCED.md), [detectability](docs/nn_v2/v6/DETECTABILITY.md), [Draft](paper/draft.md) |
| v6 sensitivities | **X1–X4** DONE: chr21-forced ladder_v4 (450/450, `CHR21FORCED_D_SMALL_POSITIVE`); per-fold primary contrast CI includes 0; detectability `min_detectable_delta=null` up to δ=1.0. Primary remains `B_NULL`. **X5–X6** docs/paper DONE. **X7** blocked pending clean merge after bringing `gnhf/p22-nn-cellstate` into finish-base. | [v6 summary](docs/nn_v2/v6/ladder_v4_summary.json), [per-fold](docs/nn_v2/v6/per_fold_contrast.json), [detectability.json](docs/nn_v2/v6/detectability.json), [lane log](tasks/nn/lanes/v6.md) |
| Paper | Framing **F4**; figures **fig1–fig7**; Results/Discussion/Abstract include ladder_v3 + per-fold AUROC + positive control + chr21-forced + detectability; **N31** checker PASS; vault `paper-nn/` copy. Header `DRAFT_V3_COMPLETE`. | [framing](paper/framing.md), [self-review](paper/self_review.md), [Draft](paper/draft.md), [claims](paper/claims.csv) |
| Old swarm | `p22agy4` kept hitting Gemini quota limits. Stopped at 13:44 PDT; tmux session and Python driver no longer running. Saved lane branches/outputs remain for verification. | [Swarm log](reports/generated/nn_agy/latest/swarm.log), [lane status](reports/generated/nn_agy/latest/status.json) |
| Manual GNHF finish | [Runbook](tasks/nn/GNHF_FINISH_RUNBOOK.md) on `codex/p22-nn-finish-base` reached N34 + v5 P6 + v6 X1–X6; X7 integrate/push remains. | [Runbook](tasks/nn/GNHF_FINISH_RUNBOOK.md), [self-review](paper/self_review.md), [saved gate](docs/nn_v2/ladder_verification.json) |

**Resolved conflict:** N10 task label previously said DONE while the S6 hard gate said FAIL. Gate now `PASS` with rebuilt summary from all 450 fold files; N10 scientific result accepted as `B_NULL`.

**X7 blocker (active):** merge of `codex/p22-nn-finish-base` into `gnhf/p22-nn-cellstate` aborted on add/add conflicts in `docs/INDEX.md` and `status.md`. Finish-base has now merged `gnhf/p22-nn-cellstate` and kept the finish-base/v6 versions of those two files so the reverse merge can retry cleanly.

## Other study tracks

- Earlier paired multiome study: corrected internal comparison is an accepted null within its own protocol; external paired validation remains unperformed. It is **not** the NN-v2 ladder. See [corrected handoff](MOM/2026-09-21/GNHF_P22_CORRECTED_RESULTS_AND_HANDOFF.md).
- Professor meeting records stay in [MOM](MOM/README.md), separate from plans and experiment outputs. June and July transcripts live in the linked Obsidian vault; September execution handoffs live here.
- Historical July [HANDOFF.md](HANDOFF.md) and September [session handoff](docs/P22_SESSION_HANDOFF_2026-09-23.md) are dated snapshots, not current status.

## Next verified milestones

1. Retry X7: merge finish-base into `gnhf/p22-nn-cellstate`, run `v6_gate`, push both remotes (no force).
2. Do not mark the professor note as sent; leave the unsent packets untouched.

## Status maintenance

Update this file after an accepted gate, material blocker, or final result. Include date, direct evidence links, and any disagreement between task labels and checks. Avoid updates for every quota retry. For scientific claims, verified raw evidence and gates outrank task labels; task labels outrank narrative handoffs.
