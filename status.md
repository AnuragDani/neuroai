# P22 current status

Updated: 2026-09-30. Read this first, then [document index](docs/INDEX.md). This is a snapshot, not permission to run an experiment or change a scientific gate. For live work, recheck the linked status and verifier files before acting.

Companion research vault: [vault status](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/status.md>) and [vault MOM index](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/MOM/README.md>).

## Data-driven continuation Q3 — REGULATORY_ADEQUACY_UNRESOLVED — 2026-09-30

**Q3 DONE** with disposition **`REGULATORY_ADEQUACY_UNRESOLVED`** and structural label **`STRUCTURAL_COVERAGE_PASS`** on `gnhf/execute-the-p22-data-146414`. All 25 training-only 256-region panels (5×5) reported from the exact counted 465-region union (GRCh38, `unique_fragment_overlap`); independent fold-0/repeat-0 BED+matrix replay matched; gene-body/flank and gene-activity BED overlaps recorded as descriptive only (no regulatory-element catalog in repo). One alternate representation proposed: existing gene-activity exact counts (no new recount; no biological-zero fill). Unresolved regulatory adequacy **cannot** authorize a biological regulatory-feature claim; Q2 endpoint unresolved still blocks cell-state fits. Q4–Q5 may continue. Primary remains **`B_NULL`**; S7-v1/v2 **`INVALID`**; prior S8 **`NO FIT`**; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`. [REGULATORY_COVERAGE](tasks/nn/professor_direction_investigation_20260929/next_stage_20260930/REGULATORY_COVERAGE.md); [coverage JSON](tasks/nn/professor_direction_investigation_20260929/next_stage_20260930/regulatory_coverage.json).

## Data-driven continuation Q2 — ENDPOINT_UNRESOLVED — 2026-09-30

**Q2 DONE** with disposition **`ENDPOINT_UNRESOLVED`** on `gnhf/execute-the-p22-data-146414`. Live H5AD obs audit found no independently measured cell-state/maturation endpoint orthogonal to NN RNA inputs: disease/`group` is specimen-level (existing primary, not state); `dev_PCW` is age (not interchangeable with state); `author_cell_type`/SCT clusters and N16 OOF disease scores are RNA-/model-derived proxies; no pseudotime/maturation assay columns present. Identity uniqueness PASS (248,998). Unresolved endpoint **cannot** authorize a biological cell-state fit (Checkpoint A); Q3–Q5 may continue. Primary remains **`B_NULL`**; S7-v1/v2 **`INVALID`**; prior S8 **`NO FIT`**; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`. [ENDPOINTS](tasks/nn/professor_direction_investigation_20260929/next_stage_20260930/ENDPOINTS.md); [inventory](tasks/nn/professor_direction_investigation_20260929/next_stage_20260930/endpoint_inventory.json).

## Data-driven continuation Q1 — diagnostic replay PASS — 2026-09-30

**Q1 PASS** on `gnhf/execute-the-p22-data-146414`. Fresh replay under `reports/generated/nn_next_stage_q1_replay_20260930/` is byte-identical (SHA-256) to the three immutable next_stage diagnostic JSONs; overwrite/tamper/order/missing-column refusals covered by `tests/test_next_stage_diagnostic_replay.py`; `gnhf/verify_ladder.py` on shared ladder_v3 returned **PASS** / `advantage=false` without `--write`. No fits. Primary remains **`B_NULL`**; S7-v1/v2 **`INVALID`**; prior S8 **`NO FIT`**; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`. Next: Q2–Q5 read-only reports. [REPLAY](tasks/nn/professor_direction_investigation_20260929/next_stage_20260930/REPLAY.md); [script](scripts/replay_next_stage_diagnostics.py).

## Data-driven continuation Q0 — provenance PASS — 2026-09-30

New ordered continuation Q0–Q12 started on local branch `gnhf/execute-the-p22-data-146414` from base `04282f0`. **Q0 PASS:** owned dated plan/prompt/three diagnostic JSONs copied with matching SHA-256; root `tasks/todo.md` / `tasks/plan.md` appended without overwriting older sections; interpreter imports and shared read-only inputs verified; `p22` loads from this worktree `src`. No fits, downloads, or package installs. Dirty main (`gnhf/p22-nn-cellstate` @ `9a1e777`) preserved; unrelated dirty files not copied. Primary remains **`B_NULL`**; S7-v1/v2 **`INVALID`**; prior S8 **`NO FIT`**; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`. [PREFLIGHT](tasks/nn/professor_direction_investigation_20260929/next_stage_20260930/PREFLIGHT.md); [PLAN](tasks/nn/professor_direction_investigation_20260929/next_stage_20260930/PLAN.md); [Q checklist](tasks/todo.md#data-driven-investigation-continuation-q0q12).

## Professor-direction continuation — NO FIT closeout — 2026-09-30

Ordered continuation `CONTINUATION_20260930` finished on local branch `gnhf/read-users-anuragdan-b61180` with scientific label **`NO FIT`**. C0–C2 complete; C3–C5 skipped (I2 control-design FAIL). Lane B S8 draft rejected for invalid chance-null calibration (constant/Bernoulli band does not match fitted seven-arm pooled-BA). Chosen path: **bounded internal null / detectability paper (F4)**. No S8 freeze, no synthetic fits (budget 0), no `nn_s8_*` root, no real-label refit, no external acquisition, no push/merge/vault/packet/MOM edit. Old S7-v1/v2 remain **`INVALID`**; primary remains **`B_NULL`**; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`. [HANDOFF](tasks/nn/professor_direction_investigation_20260929/continuation/HANDOFF.md); [DECISION](tasks/nn/professor_direction_investigation_20260929/continuation/DECISION.md); [Lane A recovery](tasks/nn/professor_direction_investigation_20260929/continuation/LANE_A_RECOVERY.md); [PREFLIGHT](tasks/nn/professor_direction_investigation_20260929/continuation/PREFLIGHT.md). Local only — not pushed.

## S7-v2 complete — INVALID handoff — 2026-09-29

Versioned S7-v2 continuation on `codex/p22-s7-v2-plan-20260929` finished with scientific label **`INVALID`**. Split repair made all screen folds scoreable (55/55 preflight; smoke 14/14; screen 105/105; cumulative fits=119/480), but rho-0 null FAIL (`token_concat` BA 0.341667 < 0.35) and pairing-PC `PC_FAIL` (ll-drop CI lower ≤ 0; 0 new fits). **T9 skipped**. Truthful handoff written; Checkpoints C–D complete; GNHF stop. Old S7-v1 remains **`INVALID`** and immutable. Biological primary remains **`B_NULL`**; power `POWER_UNESTABLISHED`; study `STUDY_PARTIAL`. [S7_V2_RESULT](docs/nn_v2/s7_v2/S7_V2_RESULT.md); [T10 handoff](docs/nn_v2/s7_v2/T10_HANDOFF.md); durable v2 `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/`.

**Independent review:** [dated review](docs/nn_v2/s7_v2/CODEX_REVIEW_20260929.md) recomputed the frozen **pooled-donor** rho-0 gate from saved predictions. Token-concat BA 0.330357 and gated-fusion BA 0.325893 both fail `[0.35,0.65]`, so `INVALID` stands. GNHF's cited 0.341667 was **mean-fold** BA from an implementation/spec mismatch; versioned `S7_V2_RESULT` is the handoff entrypoint. One failed GNHF iteration was an output-parse error; 119 unique successful fit rows survived. No further fits under this freeze.

## S7-v2 pairing PC FAIL — 2026-09-29

T8 pairing-PC diagnostic after T7 `INVALID` screen: **0 new fits** (cumulative 119), identity `max_abs_diff=0.0`, seeds 3001–3032, 30 donors, bootstrap 1000/1000 valid, CA ll-drop 95% CI lower `−0.003847` ≤ 0 → **`pc_label=PC_FAIL`**. [T8 evidence](docs/nn_v2/s7_v2/T8_PAIRING_PC.md).

## S7-v2 screen INVALID — 2026-09-29

T7 fixed screen: **105/105** scoreable (cumulative 119), both classes all folds, rho-1 marginal PASS, rho-0 null **FAIL** → **`screen_label=INVALID`**. [T7 evidence](docs/nn_v2/s7_v2/T7_SCREEN.md).

## S7-v2 smoke PASS — 2026-09-29

T6 smoke under Checkpoint B: **14/14** scoreable fold-0 jobs, held-out classes `{0:4,1:2}`, CA/TC reload identity `≤1e-6`. [T6 evidence](docs/nn_v2/s7_v2/T6_SMOKE.md).

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

1. Data-driven continuation Q0–Q3 done (Q2 `ENDPOINT_UNRESOLVED`; Q3 structural PASS / `REGULATORY_ADEQUACY_UNRESOLVED`); execute Q4–Q5 read-only reports next. Unresolved endpoint/regulatory adequacy block biological cell-state / regulatory-feature fits; synthetic/control paths still gated separately. Prior S8 `NO FIT` preserved; not a stop on all future designs.
2. Professor-direction continuation closeout complete (`NO FIT`); no S8 fits authorized. Bounded internal null/detectability paper (F4) remains a valid later writing path, not the predetermined destination of Q0–Q12.
3. S7-v2 handoff remains (`INVALID`); no further S7-v2 fits under frozen rules. Local review of branch + durable ledger; no push/merge from this status.
4. Independent review corrections are complete; reviewed finish branch and unsent packet are ready. Merge/push remain a separate milestone.
5. Do not mark the professor note or packet as sent; leave last-sent baseline as August 16.
6. External validation (T13) remains deferred; NeMO blockers unchanged; do not execute acquisition from this status.

## Status maintenance

Update this file after an accepted gate, material blocker, or final result. Include date, direct evidence links, and any disagreement between task labels and checks. Avoid updates for every quota retry. For scientific claims, verified raw evidence and gates outrank task labels; task labels outrank narrative handoffs.
