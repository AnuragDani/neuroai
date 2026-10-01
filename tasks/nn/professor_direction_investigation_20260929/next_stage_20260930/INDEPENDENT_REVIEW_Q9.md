# Q9 — Independent scientific/code review (S9 analytic pairing-use)

**Reviewer identity:** cursor Task generalPurpose agent (independent of Q7/Q8 authoring session)  
**Date:** 2026-10-01  
**Protocol under review:** `S9_analytic_pairing_use_synthetic_20260930`  
**Scope:** analytic synthetic pairing-use software control (NOT a biological disease claim)  
**Interpreter:** `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python`  
**PYTHONPATH:** `<workspace>/src`

Worker self-assertion was not used. Hashes, oracle BAs, fit arithmetic, seeds, refusals, and focused tests were recomputed by this reviewer.

---

## Overall verdict

**PASS**

No critical findings. Checkpoint C may proceed (Q7 `PROTOCOL_FROZEN` + Q8 `IMPLEMENT_PASS` + this Q9 PASS on exact hashes). This review does **not** itself mark Checkpoint C in todo/status.

---

## Exact hashes recomputed (SHA-256)

| Artifact | Expected | Recomputed | Match |
|---|---|---|---|
| `SYNTHETIC_PROTOCOL.json` | `eedf5e77c4ba08d8a801609e5a2bdfccc5d882e2d297d9469c4af364ad25ec7a` | `eedf5e77c4ba08d8a801609e5a2bdfccc5d882e2d297d9469c4af364ad25ec7a` | YES |
| `SPLIT_MANIFEST.json` | `2d9a3b9fac7bfd8dd48b7517e0ad22e297eab9a4e9f775ac814dd99b8c50fd4d` | `2d9a3b9fac7bfd8dd48b7517e0ad22e297eab9a4e9f775ac814dd99b8c50fd4d` | YES |
| `FIT_LEDGER.json` | `841c8468b6b17a43628d14af00f277ffb156b774264fe1dad0545b2ab5cd3563` | `841c8468b6b17a43628d14af00f277ffb156b774264fe1dad0545b2ab5cd3563` | YES |
| `src/p22/eval/s9_analytic.py` | `dad126cd6dc33e9e8226b9924baa7c0b0fd3e88f8b413a6b06c9313c06d4ea02` | `dad126cd6dc33e9e8226b9924baa7c0b0fd3e88f8b413a6b06c9313c06d4ea02` | YES |
| `tests/test_next_stage_s9_implement_q8.py` | `e2902507396691f58865e2448ee4c8c486c76eb0146d06dfcfeb5bb705b35836` | `e2902507396691f58865e2448ee4c8c486c76eb0146d06dfcfeb5bb705b35836` | YES |
| `tests/test_next_stage_synthetic_protocol_q7.py` | `1235f661bc2baad860662ba614e21b7db65091bf1461dc718bfeb4b2b091df43` | `1235f661bc2baad860662ba614e21b7db65091bf1461dc718bfeb4b2b091df43` | YES |

### Additional hashes (for the record)

| Artifact | Recomputed SHA-256 |
|---|---|
| `SYNTHETIC_PROTOCOL.md` | `52c041048f92746b29290a5d2ece59ebe8e59fa29030efc91f0e70b50b0e543a` |
| `IMPLEMENT.md` | `740f743e2877b68e47f8dbe63907673385c5af34059084ea359fb7745076e439` |
| `implement.json` | `3eb32833921aac273064a06a157872fda6d689d2bae4fb8c5c5f7e9515505968` |
| `scripts/report_next_stage_s9_implement.py` | `2a4168146e2178478f1e5c36280c79495f122fa55ac0cb0c27d97b7f5abcf19e` |
| `scripts/report_next_stage_synthetic_protocol.py` | `d2a9d988995b576f1c26fe748f9a2a24fec44cd77b55b0f587c6e018889bf41a` |

**hashes_match:** `true` (all six required artifacts).

---

## Checklist (PLAN Q9 acceptance)

### 1. Equations — PASS

`s9_analytic.generate_analytic_arrays` implements the frozen equations in `SYNTHETIC_PROTOCOL.json`:

- Labels: SHA256(`s9-label`, seed, donor_id) rank → first 12 class 0 / remaining class 1.
- Planted k∈{0..3}: z,w from SHA256 SeedSequence; centre/scale; orthogonalize w⊥z;  
  `ATAC = (2*y_d-1)*rho*z + sqrt(1-rho^2)*w`.
- Nuisance k∈{4..15}: independent per-view Gaussians + `0.5 * donor_shift`.

Independent checks: planted RNA rho-invariant; per-donor planted mean≈0 / var≈1; live split matches `SPLIT_MANIFEST.json`; rho=0 features unchanged under label flip (latents/nuisance not label-stuffed beyond documented signed plant).

### 2. Estimand — PASS

Primary: `pairing_use_donor_logloss_drop` on **CA** at rho=1 (`applies_to: cross_attention`).  
Advantage contrast `ca_minus_token_concat_pooled_ba` labelled **`SEPARATE_NON_PRIMARY`** in protocol JSON/MD and Q7 tests.

### 3. Null validity — PASS

Null kind `fitted_pairing_plant_null` (rho=0 same pairing intervention; CI lower ≤ 0 required).  
`rejects_chance_bernoulli_ba_band: true`; `prior_s8_no_fit_unchanged: true`.  
FIT_LEDGER selects `selected_pairing_use_fitted_plant_null`, not a chance-BA band.

### 4. Oracle interpretation — PASS

Protocol role text: validates planted pairing / shuffle destruction only; **does not validate learned models**.  
Independent in-memory oracle (seed 9001):

| Quantity | Value |
|---|---|
| rho1 oracle BA | **1.0** |
| rho0 oracle BA | **0.625** |
| rho1 shuffled oracle BA | **0.5** |
| oracle_gate | **PASS** |

Matches frozen toy_verification.

### 5. Arm/multiplicity rule — PASS

Seven equally supervised arms listed identically in protocol, code `ARMS`, and ledger.  
Joint coverage: all seven must complete smoke+screen before interpreting pairing.  
`fitted_ba_montecarlo_joint_calibration` remains in `design_unresolved_paths` and is **not** selected.

### 6. Leakage — PASS

Donor isolation enforced (`assert_donor_isolation`; fold-0 verified; induced leakage raises `S9Refusal`).  
Within-donor ATAC shuffle only (`permute_atac_within_donor`); marginal multisets preserved.  
Plant latents/nuisance do not ingest labels except via the documented signed-rho plant equation (verified by label-flip invariance at rho=0).

### 7. Power language — PASS

No biological power claim. `POWER_UNESTABLISHED` retained in scientific_invariants and unresolved flags.  
F=3 fold_rationale: prospective planted-detectability software control — **not** biological power and **not** post-hoc S7 5-fold shrink.

### 8. Fit arithmetic — PASS

Independent recompute:

- smoke fold0 ρ1 = **7**
- screen ρ0 = **21**, screen ρ1 = **21**
- smoke+screen jobs = **7+42=49 ≤ 60**
- pairing interventions counted as fits = **0**
- headroom = **11**
- decision generator seed **9001** ∉ headroom `{9101,9102,9103}`
- job IDs unique: 49/49

### 9. Output root safety — PASS

Allowed: `reports/generated/nn_s9_analytic_pairing_20260930/`.  
Refuses S7 v1/v2 roots and `nn_s8_*` (verified via `refuse_if_not_allowed_raw_root` and Q8 tests). No S9 research-fit root populated.

### 10. Change scope — PASS

New module `p22.eval.s9_analytic` + dry-run reporter; reuses `paired_model` / `model_inputs` / `predict` / S7 pairing helpers / `make_fit_id`. No broad rewrite of factory/ladder.  
`research_fits_executed: 0`; trainability-with-learning **`REFUSED_UNTIL_CHECKPOINT_C`**.

---

## Unresolved flags / scientific invariants (retained)

Verified present in `SYNTHETIC_PROTOCOL.json`, `IMPLEMENT.md`, and `implement.json`:

| Flag / invariant | Status |
|---|---|
| Q2 `ENDPOINT_UNRESOLVED` | retained |
| Q3 `REGULATORY_ADEQUACY_UNRESOLVED` | retained |
| Q5 confirmatory `EXTERNAL_FEASIBILITY_BOUNDED/... UNRESOLVED` | retained |
| `POWER_UNESTABLISHED` | retained |
| `fitted_ba_montecarlo_joint_calibration DESIGN_UNRESOLVED` | retained (not used) |
| Primary | `B_NULL` |
| S7-v1 / S7-v2 | `INVALID` |
| Prior S8 | `NO FIT` |
| Study | `STUDY_PARTIAL` |

Trainability-with-learning refused until Checkpoint C: confirmed (`refuse_unreviewed_trainability` raises `S9Refusal`; implement disposition field `REFUSED_UNTIL_CHECKPOINT_C`).

---

## Critical findings

*(empty)*

---

## Non-critical notes

1. PLAN Q9 acceptance text names `NO_FIT_REVIEW.json`; this review is filed as `INDEPENDENT_REVIEW_Q9.md` per the Q9 task instruction (same gate role).
2. Finite-gradient / state-dict reload checks exercise neural arms without optimizer steps and are correctly excluded from the research-fit count.
3. `refuse_forbidden_raw_root` alone is soft for non-S7/S8 paths; hard S9-root requirement is enforced by `refuse_if_not_allowed_raw_root` (tested).
4. Equal-supervision training-loop identity across arms is protocol-declared; full learned-arm equality is deferred to post–Checkpoint C execution (Q10), which is appropriate given 0 research fits.

---

## Checkpoint C authorization

**May proceed:** YES — overall **PASS**, no critical FAIL/UNRESOLVED on checklist items 1–10, required hashes match, focused tests exit 0.

This file does **not** edit `tasks/todo.md` or `status.md`. Downstream workers may record Checkpoint C only after reading this PASS.

---

## Commands run (with exit codes)

```bash
# Hash recomputation (all required + record hashes)
python3 - <<'PY' ... hashlib.sha256 ...
# exit 0; all six required digests matched

# Focused tests
PYTHONPATH=<workspace>/src \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest \
  tests/test_next_stage_synthetic_protocol_q7.py \
  tests/test_next_stage_s9_implement_q8.py -q
# exit 0; 13 passed in ~1.58s

# Independent in-memory oracle / fit-arithmetic / seed / refusal checks
PYTHONPATH=<workspace>/src \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python - <<'PY' ...
# exit 0; oracle BA 1.0 / 0.625 / 0.5; jobs 7+42=49; seeds disjoint; refusals OK
```

**No research fits executed by this reviewer.**
**No protocol/code/test modifications except writing this review file.**
