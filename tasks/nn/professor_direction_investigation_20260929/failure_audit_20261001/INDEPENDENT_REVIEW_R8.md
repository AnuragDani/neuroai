# R8 — Independent full-path review (S10 corrected null)

**Reviewer identity:** cursor Task generalPurpose agent (independent of R7 authoring session)  
**Agent ID:** `fd860419-c20a-4e11-8c6f-f56ddc15fdec`  
**Date:** 2026-10-01  
**Protocol under review:** `S10_corrected_null_pairing_use_20261001`  
**Scope:** claim-level-1 corrected software null (NOT a biological disease claim)  
**Interpreter:** `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python`  
**PYTHONPATH:** `<workspace>/src`  
**git commit at review:** `aa9d2e10f36affef94faacfe11a9651523280a0e` (authorization binds **working-tree** file hashes)

Worker self-assertion was not used. Hashes, oracle BAs, exchangeability, fit arithmetic, seeds, executor path, refusals, and focused tests were recomputed by this reviewer.

Machine record: [NO_FIT_REVIEW_R8.json](NO_FIT_REVIEW_R8.json); lock: [R8_REVIEWED_HASHES.json](R8_REVIEWED_HASHES.json).

---

## Overall verdict

**PASS**

No critical findings. Checkpoint C may proceed (R7 `PROTOCOL_FROZEN` + `IMPLEMENT_PASS` + this R8 PASS on exact hashes including **actual executor**). Historical S9 `INVALID` / primary `B_NULL` / Q2 `ENDPOINT_UNRESOLVED` unchanged.

---

## Exact hashes recomputed (SHA-256)

| Artifact | Recomputed | Match IMPLEMENT |
|---|---|---|
| `S10_PROTOCOL.json` | `f16e503df4e4ba19029ddf06354b3c95aa1612a6ba0c49dbc2d891e8beb1798c` | YES |
| `S10_SPLIT_MANIFEST.json` | `ec210b253386938a62047728992c094107e6e65f0169aa04ef7e59ff6b676ba6` | YES |
| `S10_SEED_SCHEDULE.json` | `4ef154fe783db23aa0df09ba31d38e409a3efd2070cb581603a226b8b25c33ec` | YES |
| `src/p22/eval/s10_analytic.py` | `5440d8cd42feb69c4c8f0e6416620315b6916dd2d980d655b8ff1b409ad3fb9e` | YES |
| `src/p22/eval/s10_execute.py` | `2aed78eaf2f0e9ef9643acfad9ddc7a8e7d81afca35ac7e92ad426e012eefe77` | YES |
| `src/p22/eval/s7_runner.py` (dep; not lock key) | `290b5e2769629d139691be52c2be292bc03c5af986c3c33bf8a1feefe8d84790` | n/a |

**hashes_match:** `true` (five lock keys). External lock avoids self-referential executor digests (S9 chronology gap repair).

---

## Checklist (PLAN R8)

1. **Equations / corrected generator — PASS.** Independent Gaussians; no exact orthogonalization; ρ=0 exchangeable.
2. **Estimand — PASS.** Primary CA ρ=1 pairing log-loss drop; advantage `SEPARATE_NON_PRIMARY`.
3. **Null validity — PASS.** Candidate `independent_gaussian_rho0_within_donor_shuffle_20261001`; chance-Bernoulli rejected; S9 INVALID retained.
4. **Oracle interpretation — PASS.** Toy only; does not validate learned models.
5. **Arm multiplicity / fit arithmetic — PASS.** 7+42=49 ≤ 90; headroom 41.
6. **Leakage — PASS.** Donor isolation; train-only fits; within-donor shuffle marginals.
7. **Seeds — PASS.** Prospective 9301/17/9301; disjoint from S9/R2 panels.
8. **Output root safety — PASS.** Only `s10_corrected_null_pairing_20261001`; S7/S8/S9 refused.
9. **Executor full path — PASS.** Serial `workers=1`; per-job reserve before dispatch; hours stop; external `R8_REVIEWED_HASHES.json`; checkpoints with `initial_state_sha256`/learning history; donor predictions; `skip_fits`; pairing reload via `generate_corrected_arrays`.
10. **Claim hierarchy — PASS.** Claim-1 only; Q2/biology unchanged.
11. **Resource caps — PASS.** 90 fits / 6 h / 4 GiB / 0 payloads; diagnostic 12/12.
12. **Change scope — PASS.** Minimal s10 modules; additive `s7_runner` history fields only.

---

## Focused tests (reviewer)

```bash
PYTHONPATH=<workspace>/src .venv-p22/bin/python -m pytest \
  tests/test_failure_audit_protocol_r7.py \
  tests/test_failure_audit_decision_r6.py \
  tests/test_nn_s7_runner.py -q
```

Exit 0; **18 passed**.

---

## Independent recompute

| Quantity | Value |
|---|---|
| ρ=1 oracle BA | 1.0 |
| ρ=0 oracle BA | ≈0.5417 |
| ρ=1 shuffled BA | ≈0.5417 |
| Exchangeability mean ratio | ≈1.0043 (within [0.95, 1.05]) |
| Jobs | 49 ≤ 90 |
| `WORKERS` | 1 |
| Lock complete before write | False |

---

## Critical findings

None.

## Non-critical notes

- Commit working-tree executor/s7_runner before scientific dispatch.
- `s7_runner.py` not in five-key lock; SHA recorded for provenance.
- Hours-cap after reserve can consume an attempt without a completed fit.

---

## Checkpoint C

**`authorized_by_review`: true** under exact lock hashes, serial workers=1, allowed S10 raw root, and this PASS record. Next: R9 bounded batch (0 fits yet).
