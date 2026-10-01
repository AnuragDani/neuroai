# C1 — Lane A evidence recovery (saved outputs only)

**Disposition:** C1 PASS (no code changes, no fits).  
**Recorded:** 2026-09-30.  
**Base commit:** `808fa734a8dc2d89d34853204251bd9decea2a06`.  
**Prior Lane A:** branch `gnhf/read-users-anuragdan-27ac1d` stopped mid-iteration (graceful stop) with 0 commits and no `outputs/LANE_A.md`. Recovery rebuilt from durable artifacts below; `LANE_A.log` only confirms sidecar-schema inspection had started.

## 1. Inventory (protocols, raw roots, hashes, coverage)

| Artifact | Path | SHA256 / count | Confidence |
|---|---|---|---|
| Canonical ladder pointer | `docs/nn_v2/v5/CANONICAL_LADDER.txt` | text → `reports/generated/nn_20260923/ladder_v3` | KNOWN |
| Ladder fold files | `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v3/folds/` | **450** JSON; 18 arms × 5 repeats × 5 folds | KNOWN |
| Ladder run record | `…/ladder_v3/run.json` | `folds_done=450`, `failures=[]`; sha256 `b5cf3d48…` | KNOWN |
| Ladder summary | `docs/nn_v2/ladder_summary.json` | sha256 `9add634e…`; primary est `0.026666…`, CI `[−0.0267, 0.0770]` | KNOWN |
| Ladder verifier (archived) | `docs/nn_v2/ladder_verification.json` | sha256 `aec19fda…`; `verdict=PASS`; CI `[−0.0250, 0.0768]` | KNOWN |
| NN protocol config | `configs/nn_protocol_v2_2026-09-23.json` | sha256 `98b169f6…` | KNOWN |
| NN inputs config | `configs/nn_inputs_2026-09-23.json` | sha256 `45d9b540…` (matches S7-v2 provenance) | KNOWN |
| Protocol freeze doc | `docs/nn_v2/PROTOCOL_FREEZE.md` | sha256 `c07712e2…` | KNOWN |
| Verifier script | `gnhf/verify_ladder.py` | sha256 `e63224dc…` | KNOWN |
| S7-v1 spec | `tasks/nn/finish_20260928/BENCHMARK_SPEC.json` | sha256 `66225413…`; protocol `S7_covariance_20260929` | KNOWN |
| S7-v1 durable root | `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_20260929/` | 14 smoke donor sidecars; `screen_label=INCOMPLETE`; scientific **`INVALID`** (split-class) | KNOWN |
| S7-v1 blocker | `…/split_class_blocker_evidence.json` | sha256 `415b3dee…`; fold-0 test all fake-label 0 | KNOWN |
| S7-v2 spec | `tasks/nn/s7_v2/BENCHMARK_SPEC.json` | sha256 `e8b127ad…`; id `S7_covariance_split_v2_20260929` | KNOWN |
| S7-v2 durable root | `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/` | immutable for this run | KNOWN |
| S7-v2 ledger | `…/ledger/fit_ledger.jsonl` | sha256 `53920364…`; **119** unique `ok` (14 smoke + 105 screen) | KNOWN |
| S7-v2 donor sidecars | `…/donor_predictions/` | **119** files (14 smoke + 105 screen) | KNOWN |
| S7-v2 checkpoints | `…/checkpoints/` | includes 5 CA ρ=1 screen `.pt` used by PC | KNOWN |
| S7-v2 stage_state | `…/stage_state.json` | sha256 `705e185b…`; INVALID / PC_FAIL / CONFIRM_SKIPPED | KNOWN |
| S7-v2 provenance | `…/ledger/provenance.json` | sha256 `52cde0ba…`; live `s7_*.py` hashes **MATCH** frozen | KNOWN |
| S7-v2 independent review | `docs/nn_v2/s7_v2/CODEX_REVIEW_20260929.md` | sha256 `f25b3786…` | KNOWN |
| S7-v2 result handoff | `docs/nn_v2/s7_v2/S7_V2_RESULT.md` | sha256 `24356a28…`; scientific **`INVALID`** | KNOWN |
| Gate scripts | `src/p22/eval/s7_{setup,runner,ledger,screen,pairing,pairing_exec,confirmation,confirm_exec,pipeline,handoff}.py`; CLI `scripts/run_nn_s7_covariance.py` | hashes match provenance for audited modules | KNOWN |

**Missing / not freshly re-executed (retained as archived):** live retrain of any ladder or S7 fit; independent re-run of 32 pairing interventions (PC gate checked from saved `stage_state` + T8 docs only). No `nn_s8_*` root exists.

## 2. Claim / source / recomputed value / gate table

| Claim | Source | Recomputed this iteration | Gate | Confidence |
|---|---|---|---|---|
| ladder_v3 450/450 complete | `run.json`; 450 fold files | Counted 450 folds; 18 arms × 25 each | Coverage PASS | KNOWN |
| Primary CA−TC estimate 0.0267 | `ladder_summary.json` / verifier | `python3 gnhf/verify_ladder.py --run …/ladder_v3 --summary docs/nn_v2/ladder_summary.json` (no `--write`) → estimate `0.026666…` | Matches archived | KNOWN |
| Primary 95% CI includes 0; advantage false | verifier `primary_recomputed` | Fresh verify: CI `[−0.0250, 0.076785…]`, `advantage=false`, `valid_draws=1000`, `verdict=PASS` | **`B_NULL`** retained | KNOWN |
| Summary vs verifier CI micro-delta | summary `[−0.0267, 0.0770]` vs verifier `[−0.0250, 0.0768]` | Both share estimate; bootstrap path differs slightly between summarizer and verifier | Documented; use verifier for scientific CI | KNOWN |
| S7-v1 INVALID (split-class) | `docs/nn_v2/s7/S7_RESULT.md`; blocker JSON | Not re-fit; blocker states fold-0 test 6/6 class 0 under frozen split; 14/14 smoke `single_class` | Retain **`INVALID`** | KNOWN |
| S7-v2 screen coverage 105/105 | ledger + sidecars | 105 screen sidecars; 7 models × 3 ρ × 5 folds; 30 unique donors/arm/ρ | Coverage PASS | KNOWN |
| S7-v2 ρ=0 pooled null FAIL | sidecars + sklearn-equivalent BA | See §3 table: `token_concat` **0.330357**, `gated_fusion` **0.325893** both &lt; 0.35 | Spec null FAIL → **`INVALID`** | KNOWN |
| S7-v2 ρ=0 mean-fold null (implementation) | `s7_screen.null_check`; stage_state | `token_concat` **0.341667** FAIL; `gated_fusion` **0.350000** PASS (border) | Impl FAIL on TC only; still INVALID | KNOWN |
| Spec vs impl statistic mismatch | SPEC L100 “pooled”; `s7_screen.py` L116–144 mean-fold | Confirmed by recomputing both statistics from same sidecars | Protocol deviation **KNOWN**; does not rescue batch | KNOWN |
| S7-v2 ρ=1 marginal PASS | stage_state + recompute | mean-fold `logreg_rna` 0.366667, `logreg_atac` 0.475 ≤ 0.60 | Marginal PASS | KNOWN |
| CA vs comparators at ρ=1 (pooled) | sidecars | CA BA **0.321429**; best N4 fusion `rna_atac_concat` **0.392857**; gap **−0.071429** | Not `CA_FAVOURED` even if null had passed | KNOWN |
| Pairing PC `PC_FAIL` | `stage_state.pairing_pc`; T8 | Saved: ll-drop est `−1.434e-4`, CI `[−3.847e-3, 4.451e-3]`, lower ≤ 0; identity `max_abs_diff=0.0`; 0 new fits; 1000/1000 draws | **`PC_FAIL`**; interventions **not** re-executed here | KNOWN (gate record); LIKELY for intervention arithmetic |
| Confirmation skipped | stage_state `confirm_label=CONFIRM_SKIPPED`; pipeline policy | `confirmation_eligible=false`; reason screen/PC ineligible | Correct skip | KNOWN |
| Cumulative fits 119/480 | ledger | 119 unique ok IDs; confirmation 0 | Cap respected | KNOWN |
| Live source matches frozen S7-v2 provenance | `ledger/provenance.json` vs worktree files | `s7_screen/pipeline/runner/pairing_exec/ledger/handoff/planted_signal` all MATCH | No silent source drift | KNOWN |

## 3. S7-v2 recomputed BA (screen, all seven arms)

Balanced accuracy = mean per-class recall on donor labels vs hard predictions from each sidecar’s `donor_probabilities` arrays. **Pooled** = one BA over all 30 held-out donors. **Mean-fold** = mean of five per-fold BAs (implementation null statistic).

| Model | ρ=0 pooled | ρ=0 mean-fold | ρ=1 pooled | ρ=1 mean-fold | Donors |
|---|---:|---:|---:|---:|---:|
| cross_attention | 0.357143 | 0.375000 | 0.321429 | 0.325000 | 30 |
| token_concat | **0.330357** | **0.341667** | 0.357143 | 0.375000 | 30 |
| rna_atac_concat | 0.357143 | 0.375000 | 0.392857 | 0.408333 | 30 |
| gated_fusion | **0.325893** | 0.350000 | 0.357143 | 0.358333 | 30 |
| logreg_concat | 0.388393 | 0.391667 | 0.357143 | 0.366667 | 30 |
| logreg_rna | 0.357143 | 0.366667 | 0.357143 | 0.366667 | 30 |
| logreg_atac | 0.441964 | 0.475000 | 0.441964 | 0.475000 | 30 |

Matches independent review pooled table exactly. Implementation `null_check` failures list only `token_concat` (mean-fold); pooled also fails `gated_fusion`. **Keep `INVALID` even if a future evaluator switches to pooled.**

ρ=0.5 values recomputed for completeness (descriptive only; not decision rho): CA pooled 0.392857; TC 0.357143; gated 0.361607.

## 4. Executed-path trace (CLI → gate → writer)

```
scripts/run_nn_s7_covariance.py
  --split-v2 → protocol_version=v2; resolve_s7_paths (disjoint from v1 root)   [L84–87, L240–282]
  run_preflight (all-seed class support, param match, disk)                     [L69+]
  execute_next_stage loop (s7_pipeline)                                         [L307; pipeline L418+]
    smoke/screen: plant_and_fit_job (s7_runner) → fake labels + train-only
                  transforms → fit → donor sidecar + checkpoint → ledger
    screen gate: evaluate_screen → null_check (mean-fold) + marginal_check
                  + rho1_regime                                                  [s7_screen L116–255; pipeline L290, L505]
    pairing-PC: run_pairing_pc_diagnostic (reload CA ρ=1 ckpts; within-donor
                shuffle; 0 new fits)                                            [pipeline L510]
    confirmation: only if CA_FAVOURED_SCREEN ∧ PC_PASS; else CONFIRM_SKIPPED   [decide_next_action L69+]
    handoff: finalize_scientific_label → write_s7_result                        [s7_handoff]
```

Counterexample for pooled vs mean-fold (same raw predictions): `gated_fusion` ρ=0 pooled **0.325893** (fails `[0.35,0.65]`) vs mean-fold **0.350000** (passes). File/line: SPEC `BENCHMARK_SPEC.json:100` vs `s7_screen.py:123` docstring and `_mean_ba_by_model` aggregation at L107–114.

Ladder path (archived primary, not re-fit): fold JSONs under `ladder_v3/folds/` → `scripts/summarize_nn_v2.py` → `gnhf/verify_ladder.py` donor-bootstrap of R3_ca−R3_tc.

## 5. Ranked cause tree (S7 failures; separate causes)

1. **KNOWN — Protocol/implementation statistic mismatch (evaluator defect).** Spec requires ρ=0 **pooled** donor BA; `null_check` implements **mean-fold**. Evidence: SPEC L100; `s7_screen.py` L107–144; §3 counterexample on `gated_fusion`. Minimal prospective repair (for a *new* protocol only): gate on pooled BA and log mean-fold descriptively. **Do not relabel this batch.**

2. **KNOWN — Null/control design failure under both statistics.** Even the implemented mean-fold check fails (`token_concat` 0.341667 &lt; 0.35). Pooled fails two arms. This is an invalid null/control outcome, not evidence that CA works. Retain **`INVALID`**.

3. **KNOWN — Pairing intervention insensitive on this screen (`PC_FAIL`).** Saved CA log-loss drop CI lower ≤ 0 after within-donor ATAC shuffle; BA drop 0. Checkpoint identity PASS; 0 new fits. Does not unlock confirmation. Separate from (1)/(2): even a repaired null evaluator would still need a sensitive pairing check for method claims.

4. **KNOWN — No CA advantage signal at decision ρ=1 in this INVALID screen.** Pooled CA BA below every comparator; gap vs best fusion −0.071. Descriptive only under INVALID screen; not a method win/loss claim.

5. **KNOWN — S7-v1 separate root cause: frozen split class support.** Fold-0 test donors all fake-label 0 → smoke single_class → screen incomplete. Plant/full-cohort mismatch diagnosis withdrawn. Immutable **`INVALID`**; v2 was the split-repair attempt.

6. **KNOWN — Orchestration noise ≠ scientific failure.** Independent review: one GNHF parse-failure iteration during smoke still left 14 smoke + 105 screen unique ok rows. Lane A original run: external graceful stop with 0 commits (no scientific artifact loss beyond missing Lane A report).

7. **LIKELY — Fixed `[0.35,0.65]` null band at n=30 donors is a hard design check, not a tuned discovery threshold.** Review already flagged suitability for any future control. Not proven “wrong amplitude” from these data alone; marked for C2 scientific gate, not repaired here.

8. **UNKNOWN — Whether optimization underfit caused ρ=0 arms to leave the null band.** Would require training-curve / hyperparameter evidence not present in sidecars; cannot infer from composite INVALID alone.

9. **UNKNOWN — Exact external operator who issued Lane A graceful stop.** Log shows stop UI only; does not affect recomputed gates.

## 6. Separation summary (PLAN Q2)

| Category | Finding |
|---|---|
| Confirmed protocol deviation | Mean-fold null vs pooled spec (§5.1) |
| Invalid control / design outcome | ρ=0 null FAIL under both stats; v1 split-class |
| Possible optimization failure | UNKNOWN (no training diagnostics in sidecars) |
| Pairing sensitivity | PC_FAIL on saved diagnostic |
| Cohort/design limits | 30 donors; POWER_UNESTABLISHED unchanged; primary B_NULL |
| GNHF orchestration | Parse failure iteration + Lane A graceful stop; neither invents fits nor clears INVALID |

## 7. C1 acceptance checklist

| Requirement | Status |
|---|---|
| Inventory ladder_v3, S7-v1, S7-v2 protocols/source/hashes/coverage | Done (§1) |
| Recompute CA−TC from saved records or state missing raw | Fresh `verify_ladder` PASS; estimate/CI match archived verifier (§2) |
| Recompute S7-v2 pooled + mean-fold BA, coverage, null/marginal, CA gaps, PC summary, confirmation skip | Done (§2–§3); **`INVALID` retained** |
| Trace CLI→…→writer with file/line; ranked cause tree; KNOWN/LIKELY/UNKNOWN | Done (§4–§6) |
| No code change or fit | Held |

**C1 result: PASS.** Next ordered unit: **C2** — audit Lane B/C and write `continuation/DECISION.md` (critical S8 chance-null review; NO FIT if gate fails).
