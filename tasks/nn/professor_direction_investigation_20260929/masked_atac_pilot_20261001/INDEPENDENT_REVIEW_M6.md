# M6 — Independent protocol and claim review (masked ATAC pilot)

**Reviewer identity:** cursor Task generalPurpose agent (independent of M0–M5 authoring session)  
**Agent ID:** `d3e35bc3-b15e-47e7-9300-a5271b324ad5`  
**Date:** 2026-10-01  
**Protocol under review:** `masked_atac_pilot_20261001`  
**Scope:** claim-level-2 computational masked-measurement prediction (NOT biological state / causal / external)  
**Interpreter:** `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python`  
**PYTHONPATH:** `<workspace>/src`  
**git commit at review:** `7c60f08841400d5ff89bac04eaee39dc4c8bcc1d` (authorization binds **working-tree** file hashes)  
**Correction cycle:** 0 of max 2  
**Self-certification:** false

Worker self-assertion was not used. File SHA-256 digests, attempt arithmetic, CA/TC param counts, live JSON dispositions, attempt counters, protocol self-hash, claim forbids, and focused M1–M5 tests were recomputed by this reviewer. No neural fits or smoke learning were run. Executor code does not exist yet; this review does **not** certify a future executor (M8 still required).

Machine record: [NO_FIT_REVIEW_M6.json](NO_FIT_REVIEW_M6.json).

---

## Overall verdict

**PASS**

No critical findings. Protocol/claim scope for M5 `PROTOCOL_FROZEN` is acceptable for claim-level-2 computational prediction. M7 may implement the smallest measured-target adapter under these hashes. M6 does **not** authorize fits or smoke learning; M8 still required before any learning. Prior S10/S9/S7 `INVALID`, S8 `NO FIT`, primary `B_NULL`, Q2 `ENDPOINT_UNRESOLVED` unchanged. Checkpoint C is **not** marked by this review.

---

## Exact hashes recomputed (SHA-256)

| Artifact | Recomputed SHA-256 |
|---|---|
| `PLAN.md` | `a9bf38e474e868bd0b32403cce5998ee825bde78e6947e9b28bf19bfbbe0e834` |
| `PILOT_PROTOCOL.md` | `178b9927483f8487c563be39553bfe889bd1b9288fd481536a9c0169862c98b0` |
| `PILOT_PROTOCOL.json` | `925560d95c18c28d528ea61ee040849037393d643836ee1c61b3ba56e0638249` |
| `BUDGET_LEDGER.md` | `e9f0809afca5966b7fc42c10cec28688183f4dbaa5f322e43fd58dcc56e2002e` |
| `budget_ledger.json` | `0c1251d41d22921ef2f09fdd67752be349baa324f644620ec42fd279e2777980` |
| `FALSIFICATION.md` | `08f28f037e36596378db8f909ecd013d8675b4d94596f0dc6362b122931f62a2` |
| `FALSIFICATION.json` | `20514e94873b46faf99bebd0077e3e44765d5df0c4193dc2267ef342002f4341` |
| `TARGET_FEASIBILITY.md` | `d3dfce63abe64b256cee558a6bc09a357bd48a2514173374ac336f586ff930e0` |
| `target_feasibility.json` | `09b6a5cf6c809f8674e661821d1dff933849e33f205910415b243c36940f9c3a` |
| `INPUT_AND_MASKING.md` | `4b56ecca59e85cab71f02100b43e4c8c67b6d2688bbd47d70b98d8ff5144cf39` |
| `input_and_masking.json` | `bbd02573dce3c74ca6a0c86e79ec51dd55ee6987d99afc9b3a922f2b66510922` |
| `SPLITS_AND_SAMPLING.md` | `8bd75c14449e94f143afd3bbd3d3046c835e006d20f511fb9e02fd0d15a4137a` |
| `SPLITS_AND_SAMPLING.json` | `3375f744825e0c383aecb410c9d8af2d6eb9887e7671a0ff18e624753a46f64f` |
| `CHECKPOINT_A.md` | `f5f8b9c59b1cc3e3f727e4c70d3ace75e939d78b4dec18402abe4699a6f403e7` |
| `CHECKPOINT_B.md` | `407e16f23f45b742a860538f33368dd051fc3995dc53c7162cf1f8799155ba18` |
| `PREFLIGHT.md` | `81e4eddce459a940ee5650067535d367a553af25d2e62c784bf8fc10b84a6645` |
| `src/p22/eval/masked_atac_target.py` | `c771f1069a9a6d40c3107efd65131f762af4285799eb01ef07e395b555d0cd02` |
| `src/p22/eval/masked_atac_splits.py` | `9c54324234cd3cffd5f622604bda00aee966b1147e205179b83cf182f1e8f415` |
| `src/p22/eval/masked_atac_metrics.py` | `64553c501ac3a0619d97fcdc547d7fb98a96555ab3d3f8ccea9cee2fc019a9c5` |
| `src/p22/eval/masked_atac_protocol.py` | `1ad3fdb97a470573254569195e712a7376ce1f1e581722c7aa3eb5939d22fb5d` |
| `tests/test_masked_atac_input_and_masking_m1.py` | `fe0dd488e5a086c33adc0d280f4616ae4fc0d385ab8d26e3076e80a6062956ad` |
| `tests/test_masked_atac_target_feasibility_m2.py` | `f4ab6ddcaf859ffcd3c7cda030435cd108235d0236b3998427d16b76124ab0a1` |
| `tests/test_masked_atac_splits_m3.py` | `56dee1036b36fcf7d75e5b9339c63da5e6ce9f0c84405395e6cbdb81b8f61c9f` |
| `tests/test_masked_atac_falsification_m4.py` | `373fca78764affeb1941094b9dde6391c55ab5fdfe9dbd8820ec5297b5d7ab2a` |
| `tests/test_masked_atac_protocol_m5.py` | `986e301284fe6e43a45001078a4def5aadb40a5ffe938e1650f4cf9a136d82d0` |
| `reports/generated/.../attempt_counter.json` | `5a801b6c1aa821b4e11ad8058f044c11efb3b65d0ff8af1112b00b606e1b8be1` |

**hashes_match:** `true` (all required paths present; `protocol_sha256` self-consistent; live CA/TC param-match equals JSON).

Paths above are under `tasks/nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001/` unless prefixed with `src/`, `tests/`, or `reports/`.

---

## Checklist (PLAN M6)

1. **Target-selection provenance — PASS.** Training-only inner-train ranking; outer-test excluded; 5/5 folds; 2 unique targets (`chr19:6424686-6425606`, `chr3:93470145-93471055`); estimand is selection-algorithm performance, not single locus; historical 256-panel outer-training-library prevalence disclosed (not strict inner-train-only).
2. **Mask/count semantics — PASS.** Whole-target-chromosome mask; union has 58 overlapping pairs; target-ID removal insufficient (45/465 still overlap); binary label `count > 0`; measured zeros retained vs missing regions not zero-filled.
3. **Trainer adaptation — PASS.** Mixed cell labels → equal-donor mean of within-donor mean cell binary log-loss; live `mil_loop` mixed-label refusal recorded; disease bags / donor-average probability / fake disease class forbidden as primary.
4. **Leakage — PASS.** Chromosome-mask exclusivity; visible-only TF-IDF/depth; target-count perturbation invariance; target-inclusive depth refused (M4 `FALSIFICATION_PASS`).
5. **Task usefulness (claim-level-2) — PASS.** Measured binary accessibility prediction under masking; not biological state/causal/external; binary rationale recorded; Q2 not required for this claim level.
6. **Fair comparisons — PASS.** CA vs token_concat relative error ≤10% at RNA128×ATAC{423,430,440} (live recomputed ≈4.6–4.7%); matched cells/targets (cap256/seed22, 7680 cells); shared budgets/epochs.
7. **Statistical assumptions — PASS.** Primary TC−CA donor cell-log-loss; exploratory margin 0.01 (not disease BA); fixed-prediction donor bootstrap 1000 / seed 601001 with disclosed limits; single-class draws retained for log-loss; no disease BA import.
8. **Claim hierarchy — PASS.** Forbidden promotions listed; S10 pairing-positive not a gate; Q2 endpoint not required; prior labels preserved.
9. **Resource caps — PASS.** 25 main + 5 smoke ≤ 40; constant arm 0 fits; headroom 10; 6 h / 4 GiB; workers 1×2; counters still zero.
10. **No-fit authorization — PASS.** M6 does not authorize fits/smoke; all planned jobs require `M8_PASS`; `masked_atac_execute.py` absent; attempt_counter used=0.

---

## Focused tests (reviewer)

```bash
cd <workspace> && PYTHONPATH=<workspace>/src \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest \
  tests/test_masked_atac_input_and_masking_m1.py \
  tests/test_masked_atac_target_feasibility_m2.py \
  tests/test_masked_atac_splits_m3.py \
  tests/test_masked_atac_falsification_m4.py \
  tests/test_masked_atac_protocol_m5.py -q
```

Exit 0; **21 passed**.

---

## Independent recompute

| Quantity | Value |
|---|---|
| Main fits | 25 (5 learned × 5 folds) |
| Smoke fits | 5 (≤5; one per learned arm, fold 0) |
| Constant arm fits | 0 |
| Intended total | 30 |
| Hard cap / headroom | 40 / 10 |
| CA/TC param-match (423/430/440) | matched; rel_err ≈0.0472 / 0.0467 / 0.0461 |
| Live dispositions | INPUT_AND_MASKING_PASS; TARGET_FEASIBILITY_PASS; SPLITS_AND_SAMPLING_FROZEN; FALSIFICATION_PASS; PROTOCOL_FROZEN |
| attempt_counter | scientific/smoke/total used = 0 |
| `protocol_sha256` | matches body (`cae381acf0ad8849d27ca3a8283ef59aa4a31b46195e442489017da8560f7c28`) |
| Executor present | no (`masked_atac_execute.py` absent) |

---

## Live disposition spot-check

| Artifact | Disposition |
|---|---|
| `input_and_masking.json` | `INPUT_AND_MASKING_PASS` |
| `target_feasibility.json` | `TARGET_FEASIBILITY_PASS` |
| `SPLITS_AND_SAMPLING.json` | `SPLITS_AND_SAMPLING_FROZEN` |
| `FALSIFICATION.json` | `FALSIFICATION_PASS` |
| `PILOT_PROTOCOL.json` | `PROTOCOL_FROZEN` |

---

## Critical findings

None.

## Non-critical notes

- Historical 256-region panels disclose outer-training-library prevalence selection; protocol correctly refuses “strict inner-train-only” provenance for those panels.
- Fixed-prediction bootstrap does not capture training/selection/init uncertainty (already disclosed in protocol limits).
- M7 implementation and any future executor remain unreviewed; M8 locks executor hashes before learning.
- This review does not mark Checkpoint C.

---

## Authorization boundary

**`m7_may_implement`:** true under these exact reviewed hashes and claim-level-2 scope.  
**`m8_still_required`:** true (no fits / no smoke until M8 PASS).  
**Next:** M7 smallest measured-target adapter (no learning until M8).
