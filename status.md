# P22 current status

Updated: 2026-09-29. Read this first, then [document index](docs/INDEX.md). This is a snapshot, not permission to run an experiment or change a scientific gate. For live work, recheck the linked status and verifier files before acting.

Companion research vault: [vault status](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/status.md>) and [vault MOM index](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/MOM/README.md>).

## S7-v2 screen INVALID — 2026-09-29

Versioned S7-v2 continuation on `codex/p22-s7-v2-plan-20260929` completed T7 fixed screen under frozen Checkpoint B: **105/105** scoreable jobs (cumulative fits=119 / remaining 361), both classes all folds, rho-1 marginal PASS, but rho-0 null **FAIL** (`token_concat` mean-fold donor BA 0.341667 < 0.35) → **`screen_label=INVALID`**. Confirmation ineligible; no retuning. Next authorized stage is T8 pairing-PC diagnostic only (no new fits; cannot unlock T9), then T10 handoff. Old S7-v1 remains **`INVALID`** and immutable. Biological primary remains **`B_NULL`**; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`. [T7 evidence](docs/nn_v2/s7_v2/T7_SCREEN.md); durable v2 `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/`.

## S7-v2 smoke PASS — 2026-09-29

Versioned S7-v2 continuation on `codex/p22-s7-v2-plan-20260929` completed T6 smoke under frozen Checkpoint B: **14/14** scoreable fold-0 jobs (`status=ok`), held-out classes `{0:4,1:2}`, CA/TC reload identity `≤1e-6`, cumulative fits=14 / remaining 466, artifacts 0.003 GiB. Old S7-v1 remains **`INVALID`** and immutable. Biological primary remains **`B_NULL`**; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`. [T6 evidence](docs/nn_v2/s7_v2/T6_SMOKE.md).

## S7 prospective control — INVALID blocker — 2026-09-29

Bounded S7 synthetic-control run on `codex/p22-prospective-controls-20260929` stopped with scientific label **`INVALID`**. Frozen `split_seed=0` + `prospective-s7:1001` assigns all six fold-0 test donors fake label 0 (16/14 donor-level fake balance); smoke (fold 0 only) recorded 14/14 `single_class`. Screen cannot complete under this freeze; no seed/setting retune. Live check withdrew the earlier plant-recompute diagnosis (`plant_covariance` matches full-cohort labels). Biological power `POWER_UNESTABLISHED`; finished primary remains **`B_NULL`**; study `STUDY_PARTIAL`. No canonical gate, packet, or paper-claim edits. [S7_RESULT](docs/nn_v2/s7/S7_RESULT.md); durable ledger `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_20260929/`; [blocker evidence](/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_20260929/split_class_blocker_evidence.json).

## Accepted finish closeout — 2026-09-28

Current internal finish task **COMPLETE** after independent review corrections. Canonical results now say advantage not demonstrated (not equivalence); results/professor note report verified local tests. Earlier integrated evidence: 1278 tests PASS and V6_GATE PASS; source/tests/protocol/scientific JSON unchanged in this prose-only closeout. Fresh paper/CI checks, safe-display notebook (6 cells/zero errors), HTML, 30 local links, 22 hashes, ZIP and vault sync PASS. [Definition of done / positive-result plan](tasks/nn/finish_20260928/PLAN.md); [closeout checks](reports/generated/nn_finish_20260928/CODEX_CLOSEOUT_CHECKS.json). Earlier review findings resolved; [dated review](reports/generated/nn_finish_20260928/CODEX_REVIEW.md) remains historical. Final deliverables live on `codex/p22-finish-engineering-20260928`; local only, no canonical merge/push. September 28 packet prepared/unsent; last sent August 16. Scientific outcome remains `B_NULL`, broader study `STUDY_PARTIAL`.

## Current work: NN v2

| Item | State | Evidence |
|---|---|---|
| Professor guidance | About 100% implemented for the NN-v2 assignment scope; ~96% supported by completed evidence (claim limits: PC N/A; N21 secondary; external validation deferred T13). These are task-based estimates, not scientific metrics. | [Direction-to-task map](tasks/nn/plan.md#1-what-the-professor-asked-and-how-this-plan-answers-it), [July meeting records](MOM/README.md), [framing](paper/framing.md), [self-review](paper/self_review.md), [NN_V2_RESULTS](docs/nn_v2/NN_V2_RESULTS_2026-09-23.md), [v6 update](docs/nn_v2/v6/PROFESSOR_UPDATE_v6.md) |
| Main real-data ladder | Canonical is now **ladder_v3** (450/450) after v5 shared-path control-fit fix; `ladder_v2` retained. | [Run record](reports/generated/nn_20260923/ladder_v3/run.json), [CANONICAL_LADDER](docs/nn_v2/v5/CANONICAL_LADDER.txt), [verifier](docs/nn_v2/ladder_verification.json) |
| Ladder gate | **PASS** on ladder_v3. Primary outcome still `B_NULL`: R3_ca−R3_tc estimate ≈ 0.0267, CI includes 0. V1–V4 + P1–P6 DONE. Paper header `DRAFT_V3_COMPLETE`. **`python3 gnhf/v5_gate.py` → `V5_GATE PASS`.** v6 X1–X6 DONE; **X7 DONE** for finish-base→cellstate merge/push at `9a1e777` (stale conflict label cleared). | [Saved summary](docs/nn_v2/ladder_summary.json), [verifier](docs/nn_v2/ladder_verification.json), [NN_V2_RESULTS](docs/nn_v2/NN_V2_RESULTS_2026-09-23.md), [P5 update](docs/nn_v2/v5/PROFESSOR_UPDATE_v5.md), [v6 update](docs/nn_v2/v6/PROFESSOR_UPDATE_v6.md), [Draft](paper/draft.md), [X7 status](tasks/nn/status/X7) |
| Downstream NN work | **N11**–**N17** refreshed on `ladder_v3`. **P2** no `CA_FAVOURED` on gene-matched S6. **P3** chr21-excluded spectrum `SPECTRUM_NULL`. **P4**–**P5** results + professor coverage table. **P6**/`X6` paper revision (`DRAFT_V3_COMPLETE`, fig6–fig7, vault synced). Study remains `STUDY_PARTIAL`. | [chr21_excluded](docs/nn_v2/chr21_excluded.json), [spectrum](docs/nn_v2/spectrum.json), [P3 spectrum](docs/nn_v2/v5/spectrum_chr21_excluded.json), [v6 chr21-forced](docs/nn_v2/v6/CHR21_FORCED.md), [detectability](docs/nn_v2/v6/DETECTABILITY.md), [Draft](paper/draft.md) |
| v6 sensitivities | **X1–X4** DONE: chr21-forced ladder_v4 (450/450, `CHR21FORCED_D_SMALL_POSITIVE`); per-fold primary contrast CI includes 0; detectability `min_detectable_delta=null` up to δ=1.0. Primary remains `B_NULL`. **X5–X6** docs/paper DONE. **X7** DONE on main refs (`finish-base` ancestor of `gnhf/p22-nn-cellstate`; local == `origin`). | [v6 summary](docs/nn_v2/v6/ladder_v4_summary.json), [per-fold](docs/nn_v2/v6/per_fold_contrast.json), [detectability.json](docs/nn_v2/v6/detectability.json), [lane log](tasks/nn/lanes/v6.md) |
| Parallel finish 2026-09-28 | **E1–E3 + C1–C3 COMPLETE** on local review branch `codex/p22-finish-engineering-20260928` gate snapshot `c23769e` (writing `0948a4a` merged). Full suite **1278 passed**; integrated `v6_gate` **V6_GATE PASS**. Branch is **local review only — not pushed**. Packet `external_shared/2026-09-28/` remains **prepared / unsent**. | [E1 pytest log](reports/generated/nn_finish_20260928/engineering-pytest.log), [E2 handoff](reports/generated/nn_finish_20260928/engineering-e2-handoff.md), [E2 gate log](reports/generated/nn_finish_20260928/engineering-v6-gate-e2.log), [writing-ready](reports/generated/nn_finish_20260928/writing-ready.json) |
| Paper | Framing **F4**; figures **fig1–fig7**; Results/Discussion/Abstract include ladder_v3 + per-fold AUROC + positive control + chr21-forced + detectability; **N31** checker PASS; vault `paper-nn/` copy. Header `DRAFT_V3_COMPLETE`. W1 claim audit on writing branch. | [framing](paper/framing.md), [self-review](paper/self_review.md), [Draft](paper/draft.md), [claims](paper/claims.csv) |
| Old swarm | `p22agy4` kept hitting Gemini quota limits. Stopped at 13:44 PDT; tmux session and Python driver no longer running. Saved lane branches/outputs remain for verification. | [Swarm log](reports/generated/nn_agy/latest/swarm.log), [lane status](reports/generated/nn_agy/latest/status.json) |
| Manual GNHF finish | [Runbook](tasks/nn/GNHF_FINISH_RUNBOOK.md) on `codex/p22-nn-finish-base` reached N34 + v5 P6 + v6 X1–X7 (cellstate merge/push). Parallel finish engineering/writing branches remain local review. | [Runbook](tasks/nn/GNHF_FINISH_RUNBOOK.md), [self-review](paper/self_review.md), [saved gate](docs/nn_v2/ladder_verification.json) |

**Resolved conflict:** N10 task label previously said DONE while the S6 hard gate said FAIL. Gate now `PASS` with rebuilt summary from all 450 fold files; N10 scientific result accepted as `B_NULL`.

**X7 (resolved):** stale `BLOCKED` conflict label cleared. Verified: `codex/p22-nn-finish-base` is an ancestor of `gnhf/p22-nn-cellstate` at `9a1e777`, and `gnhf/p22-nn-cellstate` equals `origin/gnhf/p22-nn-cellstate`. Do **not** treat that as a push of the parallel finish-engineering/writing branches (`c23769e` / `0948a4a` have no upstream).

## Other study tracks

- Earlier paired multiome study: corrected internal comparison is an accepted null within its own protocol; external paired validation remains unperformed. It is **not** the NN-v2 ladder. See [corrected handoff](MOM/2026-09-21/GNHF_P22_CORRECTED_RESULTS_AND_HANDOFF.md).
- Professor meeting records stay in [MOM](MOM/README.md), separate from plans and experiment outputs. June and July transcripts live in the linked Obsidian vault; September execution handoffs live here.
- Historical July [HANDOFF.md](HANDOFF.md) and September [session handoff](docs/P22_SESSION_HANDOFF_2026-09-23.md) are dated snapshots, not current status.

## Next verified milestones

1. S7-v2: run T8 pairing-PC diagnostic after T7 `INVALID` screen (`--split-v2 --once`); cannot unlock T9; then T10 handoff. Old S7-v1 `INVALID` remains immutable.
2. Independent review corrections are complete; reviewed finish branch and unsent packet are ready. Merge/push remain a separate milestone.
3. Do not mark the professor note or packet as sent; leave last-sent baseline as August 16.
4. Follow-up decision only: bounded internal paper versus later external validation (T13); do not execute external validation from this status.

## Status maintenance

Update this file after an accepted gate, material blocker, or final result. Include date, direct evidence links, and any disagreement between task labels and checks. Avoid updates for every quota retry. For scientific claims, verified raw evidence and gates outrank task labels; task labels outrank narrative handoffs.
