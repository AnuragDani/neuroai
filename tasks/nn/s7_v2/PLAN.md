# S7-v2 end-to-end execution plan — 2026-09-29

## Objective and authority

Repair only the split defect that made S7-v1 `INVALID`, then execute the same bounded semisynthetic covariance control once. Cursor may implement, verify, and run this synthetic batch after the researcher manually starts GNHF. A negative or invalid result is a complete handoff. No search for an attention win. This is not a new biological primary: ladder_v3 remains `B_NULL`, biological power remains `POWER_UNESTABLISHED`, study remains `STUDY_PARTIAL`.

This task uses [BENCHMARK_SPEC.json](BENCHMARK_SPEC.json) as the frozen v2 design and [TODO.md](TODO.md) as the execution ledger. Generic `tasks/plan.md` and `tasks/todo.md` contain unfinished work for a different study; do not overwrite or bulk-edit them. Prior [S7-v1 result](../../../docs/nn_v2/s7/S7_RESULT.md), original [spec](../finish_20260928/BENCHMARK_SPEC.json), and durable v1 ledger are immutable historical evidence. Original MOM records and professor packet remain untouched.

## Why v2 is needed

S7-v1 fixed seed 1001 gave 16 fake-label-0 and 14 fake-label-1 donors, but `StratifiedGroupKFold` assigned all six fold-0 test donors class 0. All 14 smoke fits were unscorable; no screen, pairing PC, or confirmation occurred. Independent reconstruction from saved split log reproduced test-fold class counts `(6,0), (2,4), (2,4), (3,3), (3,3)`. The old preflight recorded donor IDs but never checked class support before fitting. This is a split-design/preflight defect, not evidence that CA, TC, or any baseline failed to learn S7. Old `INVALID` result stays `INVALID` forever; v2 uses a new protocol ID and ledger.

## Frozen decisions

| Item | S7-v2 rule |
|---|---|
| Scientific scenario | Same 20-channel signed RNA/ATAC covariance construction, rho `[0, 0.5, 1]`, fixed decision rho `1`, synthetic donor labels by `prospective-s7:<generator_seed>`; no scenario/amplitude/feature changes. |
| Inputs | Same configured H5AD, ATAC counts, train-only RNA/ATAC transforms, cap 256/cell stratum, sampling seed 22, and five region panels; verify paths and hashes live. |
| Models | `cross_attention`, `token_concat`, `rna_atac_concat`, `gated_fusion`, `logreg_concat`, `logreg_rna`, `logreg_atac`; same N4 hyperparameters and CA/TC ≤10% parameter gap. |
| Seeds | Screen 1001; confirmation 2001–2010; pairing shuffles 3001–3032; split seed 0. No trial substitution after seeing outcomes. |
| Split change | S7-only deterministic hash-ranked **donor** quota splitter. Do not alter shared real-data `StratifiedGroupKFold`, N4, or completed primary. |
| Outer tests | Full-cohort fake donor labels must be exactly 16 class 0 / 14 class 1 for every declared generator seed. SHA256 rank donors separately within each class using UTF-8 text `s7-split-v2\n0\n<generator_seed>\nouter\n<label>\n<donor_id>`; sort by `(digest, donor_id)`. Class-0 quotas across folds 0–4: `[4,3,3,3,3]`; class-1 quotas `[2,3,3,3,3]`. Each fold tests six donors; each donor tests exactly once. |
| Inner validation | For each outer fold, re-rank its 24 remaining donors by class with stage `inner:<outer_fold>` in same hash format; first four donors per class form one fixed eight-donor validation set; remaining sixteen train. Never use feature values, predictions, or metrics to assign donors. |
| Preflight hard gate | Before creating/freezing result ledger **or any fit**, build all 11 seed-specific fold packs and validate all 55 outer train/val/test triplets: 16/8/6 donors, both fake classes in every partition, donor purity/disjointness, exactly-once test coverage, stable cell-ID alignment, matching full-cohort and planted labels, deterministic replay. Log donor IDs, labels and counts. Any fail => `INVALID_PREFLIGHT`, zero fits. |
| Screen | 3 rho × 5 folds × 7 models = 105 fits. Complete coverage, rho-0 null and rho-1 single-view controls; fixed rho-1 N4 `CA_FAVOURED` and ≥0.07 CA minus best non-attention required. Rho 0.5 descriptive. |
| Pairing PC | Retained CA/TC rho-1 checkpoints; reload/identity; 32 within-donor ATAC shuffles. CA donor log-loss drop 95% donor-bootstrap CI lower >0 required. |
| Confirmation | Only after screen and PC pass: 10 fresh generator/label/model seeds × 5 folds × 7 models = 350 fits. Joint CA−TC estimate ≥0.07 and CI lower >0; beat all six non-attention arms; report successes/10 and Wilson interval. ≥8/10 remains exploratory synthetic reliability, never biological power. |
| Compute | Smoke ≤14, screen 105, confirmation 350: planned maximum 469, absolute ceiling 480 fits. ≤2 CPU workers, 2 torch threads each, ≤12 fitting hours, ≤2 GiB new artifacts, ≥11 GiB free disk, ≤32 GiB RSS. No package install or fallback tuning. |
| Outputs | New durable root `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929`; worktree report pointer `reports/generated/nn_s7_covariance_split_v2_20260929`; result `docs/nn_v2/s7_v2/`. Never copy v1 predictions, fit rows or checkpoints into v2. |

The 16/14 split is a predeclared input property, checked for all eleven seeds in a read-only calculation. If cohort contents or labels differ, stop and report changed input; do not adjust quotas automatically. The split guarantees class support; it does **not** guarantee attention advantage. Conditioning on synthetic fake labels for splitting is part of the design, not outcome-based model selection. The original v1 invalid evidence motivates this prospective amendment; do not present v2 as an independent replication.

## Dependency graph and execution order

```text
v1 evidence + frozen v2 spec
    ↓
T1 split helper → T2 split validator → T3 v2 CLI/paths
    ↓                     ↓
    └──────────────→ T4 source audit + focused/full checks
                              ↓
                    T5 live no-fit preflight
                              ↓ (only all PASS)
                    T6 provenance freeze + smoke
                              ↓ (only complete/scoreable)
                    T7 screen → T8 pairing PC
                                      ↓ (only both PASS)
                                 T9 confirmation
                                      ↓
                            T10 evidence handoff
```

T1–T5 form no-fit implementation gate. T6–T10 are one bounded synthetic run. Cursor must stop at first hard blocker, write evidence, and skip dependent fit tasks. Tasks and checkpoints below live in [TODO.md](TODO.md); never infer completion from a checked box without its verification artifact.

## Cursor task contracts

### T1 — Deterministic donor allocation (S, ~2 files)

**Description.** Add S7-v2-only split helper in `src/p22/eval/s7_setup.py` or the smallest existing S7 module; use SHA256/stdlib. Return explicit donor partitions. Keep shared real-data and old v1 split APIs unchanged.

**Acceptance criteria.** Exact hash string and quotas above; 30 unique/pure donors; five six-donor test folds, each class represented, no overlap and exactly-once coverage. With 24 outer-training donors, choose eight validation (four/class) and sixteen train. Repeated input and permuted metadata row order yield identical donor partitions; different generator tags change rankings without altering quotas.

**Verification.** Focused tests in `tests/test_nn_s7_setup.py` (or one new v2 test file) cover expected 16/14, mixed-label donor refusal, duplicate donor refusal, row-order invariance, deterministic replay, and exactly-once coverage. Do not run model fits.

### T2 — Complete preflight and refusal path (M, ~3 files)

**Description.** Replace S7-v2 preflight's reliance on donor-count-only checks. Prepare all 11 declared seed packs before any fitting; validate every outer/inner partition and fake-label agreement. Make `--preflight-only` executable on new v2 root without touching v1 root.

**Acceptance criteria.** Manifest lists seed, all fold donor IDs, per-partition class counts, unique cell-ID hash, and exact class-purity/overlap/coverage checks. A deliberately single-class test fold or wrong planted/full-cohort label raises before `fit_s7_arm`, checkpoint creation, or ledger fit row. One failing confirmation seed also blocks entire v2 batch before smoke; no partial seed selection.

**Verification.** Inject bad fold in focused test and assert zero fit calls/rows. Run no-fit CLI on live inputs; independently recount saved manifest for 11×5 folds. Exact expected partition counts 16/8/6, all class counts positive, 30 test donors covered once/seed. Report preflight runtime and input hashes.

### T3 — Versioned identity, paths and resume guard (M, ~3 files)

**Description.** Wire CLI/ledger/result writer to v2 spec ID and new durable/worktree paths; keep v1 files readable but immutable. Prefer parameterized constants over copying the 8k-line S7 stack. Any changed fitting-source/spec/input/split-manifest hash after first v2 fit invalidates v2 ledger; resume only identical completed fit IDs.

**Acceptance criteria.** V2 CLI cannot resolve to v1 durable root or v1 result path; v1 ledger hash/mtime unchanged in tests. No v1 sidecar/checkpoint appears in v2 manifest. New ledger starts empty, includes v2 protocol ID and all hashes; refuses conflicting resume and never mixes models from changed source. No `--skip-disk-check` for live runs.

**Verification.** Focused path/provenance/immutability tests. Inspect absolute `realpath` of v1/v2 roots and staged output paths. No fits.

### Checkpoint A — implementation gate, zero fits

T1–T3 focused tests pass; `git diff --check` pass. Diff limited to split/preflight/versioning plus necessary test or result plumbing. Any finding requiring scenario/threshold/seed/model change returns to new planning, not ad hoc implementation. Review exact v2 spec diff against v1 and old result immutability.

### T4 — Source audit and verification (S–M, no speculative rewrite)

**Description.** Audit v1's 8,414-line change for paths used by this run: generator label consistency, row identity, model seeds, checkpoint reload, donor pooling/bootstrap, coverage, stage transitions, resource/time caps, and result labels. Reuse tested code. Remove only clearly redundant code when doing so shrinks review surface without changing scientific behavior; do not undertake a full refactor campaign.

**Acceptance criteria.** Write concise audit in v2 report folder with each scientific risk and evidence, plus any corrected issue before provenance freeze. Verify `screen` cannot treat missing or `single_class` rows as PASS; PC cannot run from missing checkpoint; confirmation cannot start after failed gate; label `CA_FAVOURED_CONTROL` requires screen+PC+reliability. No source changes after result fits.

**Verification.** Focused `tests/test_nn_s7_*.py`, adjacent planted/N4 tests, then repository full suite once after final source change. Run `git diff --check`; save commands/counts. A failing full suite is a blocker or must receive a justified focused repair before T5.

### T5 — Live no-fit preflight and freeze review (S)

**Description.** Run v2 CLI `--preflight-only` on existing inputs. Check all 55 partitions, parameter match, data hashes, capacity, and available resources. This is a real read/transform pass, not a model fit. Only after all checks pass may v2 provenance be frozen.

**Acceptance criteria.** Every declared seed, class count, donor partition, cell-ID mapping, fold feature shape, CA/TC parameter gap, and v1/v2 path separation pass. New v2 fit ledger has zero rows. No source or spec uncertainty remains. If any fail, write `INVALID_PREFLIGHT` report with zero fits and stop; no seed hunt.

**Verification.** Independently parse manifest and assert 11 seeds, five folds/seed, 16/8/6 donor counts each, both classes each partition, exactly-once test coverage. Save CLI stdout, manifest hash, and zero-fit ledger count. Check old ledger unchanged.

### Checkpoint B — immutable v2 run start

Record Git commit, v2 spec/input/source/split hashes, exact command, remaining disk, RSS baseline, and no-fit gate. Freeze before T6. A changed fitting source after T6 marks v2 run `INVALID`; preserve completed artifacts and start no replacement batch within this GNHF task. Never overwrite v1.

### T6 — Smoke (S, ≤14 fits)

**Description.** Run fixed rho 0/1 × fold 0 × seven arms, using v2 folds. Count attempted fits (including errors) against cap. Keep CA/TC checkpoints at rho 1 and donor prediction sidecars.

**Acceptance criteria.** Exactly 14 scoreable, complete rows with finite donor BA/AUROC/log-loss and both held-out classes; checkpoint reload agrees within `atol=1e-6`; provenance and resource gates pass. Any `single_class`, missing row, exception, cap breach, or changed hash stops before screen and yields `INVALID` or `INCOMPLETE` as appropriate.

**Verification.** Inspect ledger IDs/statuses, per-fold fake-label counts, sidecars and reload evidence. No model or seed adjustment.

### T7 — Fixed screen (S, 105 fits)

**Description.** Run 3 rho × 5 folds × seven models at seed 1001; evaluate only after full coverage. Report pooled donor and mean-fold BA/AUROC, paired CIs to all baselines, null and marginal controls. Keep rho-1 CA/TC models.

**Acceptance criteria.** Exactly 105 screen job IDs, all scoreable. Rho-0 pooled BA of all seven arms within `[0.35,0.65]`; rho-1 single-view controls ≤0.60. Fixed rho-1 existing N4 `CA_FAVOURED` rule and CA–best-non-attention ≥0.07 decide screen PASS; rho 0.5 cannot be selected instead. Invalid controls stop scientific claim; ordinary lack of advantage yields `CONTROL_NEGATIVE` and no confirmation.

**Verification.** Recompute coverage and regime from saved rows, compare to frozen rules, preserve failures. Check cumulative attempts ≤119 including smoke and resource/time caps.

### T8 — Pairing intervention (S, no new fits)

**Description.** Reload retained screen CA/TC checkpoints and apply 32 predeclared within-donor ATAC shuffles on held-out cells. Diagnostic may be completed from saved checkpoints after a negative screen; it cannot reopen confirmation eligibility.

**Acceptance criteria.** Identity reload `atol≤1e-6`; within-donor ATAC multisets preserved; fixed seeds 3001–3032; CA mean donor log-loss(shuffled)−original paired donor-bootstrap 95% CI lower >0 for PC PASS. Report BA drop as descriptive. Missing checkpoints or <950 valid bootstrap draws => incomplete, never PASS.

**Verification.** Check checkpoint hashes, intervention seeds, donor count, CI draw counts, and original-versus-shuffled scores. Confirmation eligibility requires both T7 and T8 PASS.

### T9 — Conditional confirmation (M, ≤350 fits)

**Description.** Only after eligible screen+PC, run ten fixed fresh generator/model seeds 2001–2010 at rho 1 across five folds and seven arms. Use prevalidated seed-specific v2 splits. No additional candidates.

**Acceptance criteria.** Full 350 unique job IDs and 30 pooled held-out donors per seed. Joint CA−TC condition is estimate≥0.07 **and** paired 95% donor-bootstrap lower>0; all-baseline joint success meets same rule versus each of six non-attention arms. Report counts/10 with Wilson 95% intervals; ≥8/10 is exploratory synthetic reliability only. Any coverage, hash, time or resource failure => `INCOMPLETE`/`INVALID`, never favourable.

**Verification.** Recompute pooled predictions and paired contrasts using shared donor-bootstrap draws (1000, seed 22), count invalid draws, compare with saved report. Confirm total attempted fits ≤469 planned and ≤480 hard cap.

### T10 — Final handoff and local review (M, docs/evidence only)

**Description.** Write `docs/nn_v2/s7_v2/S7_V2_RESULT.md` plus machine-readable JSON, compact raw ledger/index and source provenance. Use one of `CA_FAVOURED_CONTROL`, `CONTROL_NEGATIVE`, `INVALID`, `INCOMPLETE`. Explicitly state whether T9 ran or why skipped. Preserve old v1 result. Update `status.md` and `docs/INDEX.md` only after accepted gate or material blocker; do not edit canonical primary JSON, paper claim ledger, professor note/packet, or MOM.

**Acceptance criteria.** Every numeric claim links to raw fit rows/seed/fold/model and recomputable summary; gate labels match rules. Note biological primary `B_NULL`, power `POWER_UNESTABLISHED`, external validity untested. Review diff for unintended source/gate changes, run appropriate focused checks and `git diff --check`, commit locally. No push, PR, merge, email or real-label fit.

**Verification.** Independent saved-record audit of counts, hashes, outcome precedence, old ledger/result immutability, and clean worktree. GNHF stop condition is a complete truthful handoff **or** precise blocker with evidence; “16 good iterations” and task checkboxes alone prove nothing.

## Failure handling and result precedence

1. Inputs absent, donor labels changed, preflight class/support/identity fail, v2 path collision, or source mismatch before fits → `INVALID_PREFLIGHT`, **zero fits**.
2. Changed fitting code/spec/input/split manifest after first fit, donor leakage, invalid null/marginal control, or scientific protocol deviation → `INVALID`. Preserve old and v2 ledgers; no replacement run in this task.
3. Fit/coverage/CI/bootstrap/checkpoint/resource/time gaps without protocol violation → `INCOMPLETE`; report exact missing jobs and blocker. Do not fill them with unplanned variants.
4. Complete valid screen lacking `CA_FAVOURED`, or PC insensitive, or eligible confirmation below frozen reliability → `CONTROL_NEGATIVE`; do not claim equivalence or attention failure in general.
5. Only complete valid screen+PC+confirmation meeting frozen reliability → `CA_FAVOURED_CONTROL`. This is synthetic-control feasibility, **not** real-label `A_ADVANTAGE`, biological power, or external replication.

## Risks and mitigations

| Risk | Control |
|---|---|
| Split design selected after seeing v1 blocker | Freeze deterministic donor quotas and same generator seeds before any v2 model outcome; disclose v1 invalidation and amendment. |
| Preflight repeats v1 mistake | Verify class counts of **every train/val/test partition** for all 11 seeds before any fit; negative test proves zero-fit refusal. |
| Source stack is large | Audit only executed path; reuse existing modules; no broad rewrite after fit freeze. Preserve focused and full-suite evidence. |
| Old and new artifacts mix | Distinct protocol ID/result/ledger/checkpoint roots; provenance includes split-manifest hash; compare old path fingerprints. |
| Conditional result mistaken for biology | Gate labels and handoff always retain B_NULL/POWER_UNESTABLISHED/STUDY_PARTIAL; no real-label, packet or canonical-gate edits. |
| GNHF keeps fitting after negative or invalid gate | Stage transition assertions, fit ledger budget, `--stop-when`, and explicit no-retune rules; stop when no independent safe task remains. |

## Manual launch boundary

Researcher reviews these files, then starts GNHF manually with [GNHF_PROMPT.md](GNHF_PROMPT.md). This plan authorizes only bounded synthetic execution on this local branch. Cursor may make local commits but must not push or merge. If available environment cannot enforce a resource cap, record blocker rather than silently relax it. No concurrent GNHF process may use same worktree or ledger.
