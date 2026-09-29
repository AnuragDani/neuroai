# Prospective path — bounded protocol, feasibility, ordered tasks (2026-09-28)

Planning only. No fits performed by this planning document. Synthetic execution continuation is specified below; no downloads, canonical gate changes, external validation, email, or push.
Depends on [DIAGNOSIS.md](DIAGNOSIS.md) and [HYPOTHESIS.md](HYPOTHESIS.md).
Finished primary (`ladder_v3` `B_NULL`) and gates stay unchanged.
Raw evidence under `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/` was read, not modified.

## Bounded protocol (scope lock)

**In scope (prospective, not authorized to run by this document):**

1. Redesign + evaluate a **pairing-sensitive planted control** aiming for `CA_FAVOURED` under HYPOTHESIS Gate 0 (must beat best of matched TC, `logreg_concat`, `rna_atac_concat`, `gated_fusion`).
2. Save δ=1.0 (or declared PC-cell) CA fold models and run **I3 pairing PC** (Gate 0b); forbid `pc_status=N/A`.
3. Only after Gate 0 + 0b PASS: a **precision gate** that states whether available donor n can support A_ADVANTAGE detection for the observed control contrast magnitude.
4. Only after that precision gate PASS: one new real-label protocol instance with frozen comparison set and A_ADVANTAGE rule from HYPOTHESIS.md.

**Out of scope here:** finished-primary variant search; beyond-dosage redefinition; external paired acquisition (T13); weakening margin 0.07; continuous runs until positive.

**Hard stops (retain finished internal null):** Gate 0 FAIL; Gate 0b FAIL/N/A; precision gate FAIL/unknown with no larger cohort; cohort/access blocker.

## Donor / sample feasibility

| Resource | Status from saved evidence | Feasibility |
|---|---|---|
| Internal multiome cohort | **n=30 donors** (15 DS / 15 CON pattern in spectrum docs; ladder/detectability use `n_donors=30`) | **Available** for Gate 0/0b planted work and for any later same-cohort real-label instance; no new download required |
| Planted / synthetic labels on existing representation | Prior S0–S6 + X4 already ran on this cohort size | **Available** for redesign; compute-bounded |
| Saved S4/S5 δ=1.0 CA fold models for PC | Finished `pc_status=N/A` ([faithfulness.json](../../../docs/nn_v2/faithfulness.json)) | **Not available** today → Gate 0b **requires explicit model retention** in any future Gate 0 run |
| Larger internal donor n | Not present in current study | **Unavailable** without new acquisition (not authorized) |
| Independent external paired cohort | Deferred T13; study `STUDY_PARTIAL` | **Unavailable** → transportability phase blocked; does **not** block Gate 0/0b on internal cohort |

**Feasibility verdict.** Gate 0 / 0b can be attempted on the **existing n=30** cohort without new sample access. A method-advantage **real-label** claim at A_ADVANTAGE remains **power-unproven** at this n (see below). External replication is a separate blocked phase, not a substitute for Gate 0.

## Power / precision design (honest; n not established)

### What saved evidence shows

1. **X4** ([detectability.json](../../../docs/nn_v2/v6/detectability.json); raw `reports/generated/nn_20260923/detectability_s4/`): at **n=30**, planted S4 CA−TC detection fraction **0** for all δ ≤ 1.0; `min_detectable_delta=null`. Mean CA−TC contrasts stay ~0.00–0.03 — far below the **0.07** practical margin — so non-detection mixes **small CA−TC gap under current S4** with donor-bootstrap width.
2. **Primary verifier** ([ladder_verification.json](../../../docs/nn_v2/ladder_verification.json)): estimate **0.0267**, CI **[−0.0250, 0.0768]** at n=30. Half-width ≈ **0.051**. Estimate sits **0.043** below margin; CI includes 0. Precision alone does not explain the null: the point estimate never cleared 0.07.
3. **Diagnosis:** S4/S6 are solved by strong non-attention arms → current planted grid does **not** create a CA-unique contrast large enough for A_ADVANTAGE. Therefore **donor n required for a reliable CA−TC contrast is not established** by X4 (PLAN item 3). Scaling n without a CA-unique signal is not a plan.

### Corrected precision and detection rules

CI width is descriptive, not proof of 80% power. A planted amplitude is not the resulting CA-minus-TC effect. Selected-screen control estimates must not set an assumed true effect or establish biological-cohort power.

| Rule | Meaning | Evidence / disposition |
|---|---|---|
| P0 | Comparative control | Fixed rho=1.0 screen must beat every fair non-attention arm by >=0.07; complete donor/fold/arm coverage required. No selection of a winning amplitude. |
| P1 | Descriptive uncertainty | Report paired donor CIs and half-widths only. No <=0.07 pass shortcut and no authorization inferred from CI width. |
| P2 | Fresh simulation confirmation | Ten predeclared fresh generator/label/model seeds on fixed rho=1.0; joint success is estimate >=0.07 AND CI lower >0. Report success count/10 with a Wilson 95% interval. These are conditional synthetic trials on reused cohort background, not ten independent biological cohorts. Rate >=0.8 is an exploratory design screen, not proof of >=80% population power; uncertainty remains explicit. |
| P3 | Biological continuation | Biological-cohort power/precision remains POWER_UNESTABLISHED; synthetic confirmation cannot authorize real-label reruns. A later study needs an independently justified design effect, full joint success rule, donor sampling design and prospective adequacy assessment. |

New [EXECUTION_RUNBOOK.md](EXECUTION_RUNBOOK.md) and [BENCHMARK_SPEC.json](BENCHMARK_SPEC.json) instantiate T1 and bound synthetic implementation/execution. The researcher requested planning/setup and a manual GNHF command to perform this bounded work on September 29. That continuation supersedes planning-only restrictions for this synthetic batch when the researcher launches it; no model fits are started during setup. T5–T7 remain out of this run. Failure rejects this bounded scenario/protocol, not all attention architectures.

## Ordered execution tasks (prospective; not started)

| ID | Task | Depends | Verifiable exit | On fail |
|---|---|---|---|---|
| T1 | Write planted-scenario **amendment spec**: pairing-sensitive label; explicit failure modes for linear/additive and gated-fusion solvers; freeze representation unless named secondary | DIAGNOSIS + HYPOTHESIS | Spec reviewed; no fits | Revise spec; do not fit |
| T2 | **Gate 0** fixed S7 rho grid on existing cohort; seven arms frozen in spec; **retain** CA/TC fold models at rho=1 | T1 + manual launch | Fixed rho=1 cell `CA_FAVOURED`; models on disk; null/marginal controls pass | **Stop method path**; keep `B_NULL` |
| T3 | **Gate 0b** I3 pairing PC on saved Gate-0 CA models | T2 PASS | `used_by_model=true`; not `N/A` | **Stop method path** |
| T4 | Fresh-seed synthetic confirmation and descriptive uncertainty | T3 PASS | Full joint detection rule, 10 trials, Wilson interval; biological power explicitly unestablished | Preserve null/partial; no real-label method fit |
| T5 | One real-label ladder/protocol instance; frozen HYPOTHESIS comparison set + A_ADVANTAGE; confound/dosage reporting | T4 PASS + separate authorization | Outcome labeled A_ADVANTAGE / B_NULL / A_FRAGILE per frozen rules | Report supported null/negative; **do not retune** |
| T6 | Robustness seeds (≥4/5) + CA_USES_PAIRING package for method-paper framing | T5 A_ADVANTAGE | Seeds + pairing evidence PASS | A_FRAGILE / mechanism claim withheld |
| T7 | Independent external paired evaluation | Separate cohort access + T5/T6 scope closed | External protocol PASS/FAIL | Remain `STUDY_PARTIAL`; do not claim transportability |

**Authorization update (September 29).** T1 is instantiated; the new runbook covers bounded synthetic T2–T4 after manual launch. Real-label T5–T7 remain out of scope. Never loop on primary variants until significant.

## Feasibility summary

| Question | Answer |
|---|---|
| Can Gate 0/0b be attempted without new donors? | **Yes** (n=30 internal cohort present) |
| Is CA−TC donor n for A_ADVANTAGE established? | **No** (`min_detectable_delta=null`; X4 mean contrasts ≪ 0.07) |
| Is method-advantage path ready to run? | **Synthetic batch ready for manual launch** after setup checks; scientific Gate 0 remains open |
| Precise blocker if stopping without runs? | Not a sample-access blocker for Gate 0. Real-label method path remains **POWER_UNESTABLISHED** pending a separate prospective adequacy assessment; synthetic P0/P2 passes do not clear it. External phase blocked on cohort access (T13) |
| Recommended researcher decision now | Run the frozen synthetic batch via the new runbook, or retain the bounded internal null paper; never infer a guaranteed method win |

## Explicit non-claims

- No new experiment was run.
- Required donor n is **unknown**; any numeric n>30 suggestion would be speculation beyond saved evidence and is **not** stated as a target.
- H1 remains unsupported until Gate 0 produces `CA_FAVOURED`.
- Finished estimate 0.0267 / CI including 0 remains `B_NULL`.

## Status of planning deliverables

| Deliverable | Status |
|---|---|
| Evidence-linked diagnosis | COMPLETE — [DIAGNOSIS.md](DIAGNOSIS.md) |
| One proposed hypothesis + estimand | COMPLETE — [HYPOTHESIS.md](HYPOTHESIS.md) |
| Frozen comparison / positive-result criteria | COMPLETE — [HYPOTHESIS.md](HYPOTHESIS.md) |
| Feasibility + ordered execution tasks | **This file — COMPLETE** |

Planning-only next research path (PLAN items 1–3) is complete. Item 4 (external paired phase) stays a separate prospective phase after scope/inputs resolve; not claimed done.
