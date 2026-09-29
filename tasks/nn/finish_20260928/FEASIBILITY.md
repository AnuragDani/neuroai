# Prospective path — bounded protocol, feasibility, ordered tasks (2026-09-28)

Planning only. No new fits, downloads, gate changes, external validation, email, or push.
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

### Prospective precision rules (declare before real-label fit)

Use empirical bootstrap precision; do **not** invent a fitted power curve in this planning pass.

| Rule ID | Rule | Pass condition |
|---|---|---|
| P0 | Binding Gate 0 contrast | Observed CA − best non-attention donor BA on the Gate-0 cell ≥ **0.07** (same margin family as A_ADVANTAGE); else Gate 0 cannot motivate real-label power for method advantage |
| P1 | Same-n precision proxy | On Gate-0 CA vs matched TC (or declared primary contrast twin), donor-bootstrap **half-width at n=30** must be **≤ 0.07** so a true margin-sized effect can in principle yield CI LB > 0; report half-width explicitly |
| P2 | Detection-rate target (if a future authorized n-sweep exists) | Fraction of repeats with CA−TC CI excluding 0 ≥ **0.8** at the design δ/contrast (X4 convention). **Current grid provides no such n**; until an authorized sweep exists, treat required n as **unknown** |
| P3 | Real-label authorization | Require P0 + P1 PASS **and** Gate 0b PASS. If P0 or P1 FAIL at available n=30 and no larger cohort is accessible → outcome **`BLOCKED_POWER`**: stop method-advantage real-label fits; retain finished `B_NULL`; complete bounded paper |

**Interpretation for continuation decision.** At n=30, primary half-width (~0.05) is not wildly larger than 0.07, so **insufficient n is not proven to be the sole barrier** if a true CA−TC gap ≥ 0.07 existed. The binding prospective barrier is still **absence of a pairing-sensitive CA-favoured control** (Gate 0), then PC sensitivity (Gate 0b), then P0/P1. Do not authorize “run until significant.”

## Ordered execution tasks (prospective; not started)

| ID | Task | Depends | Verifiable exit | On fail |
|---|---|---|---|---|
| T1 | Write planted-scenario **amendment spec**: pairing-sensitive label; explicit failure modes for linear/additive and gated-fusion solvers; freeze representation unless named secondary | DIAGNOSIS + HYPOTHESIS | Spec reviewed; no fits | Revise spec; do not fit |
| T2 | **Gate 0** planted grid on existing cohort; arms include CA, matched TC, `logreg_concat`, `rna_atac_concat`, `gated_fusion`; **retain** CA fold models at PC cell | T1 + run authorization | ≥1 cell `CA_FAVOURED`; models on disk | **Stop method path**; keep `B_NULL` |
| T3 | **Gate 0b** I3 pairing PC on saved Gate-0 CA models | T2 PASS | `used_by_model=true`; not `N/A` | **Stop method path** |
| T4 | **Precision gate** P0–P1 (and P2 only if n-sweep authorized) | T3 PASS | Document half-width + contrast; P0∧P1 | **`BLOCKED_POWER`**; no real-label method fit |
| T5 | One real-label ladder/protocol instance; frozen HYPOTHESIS comparison set + A_ADVANTAGE; confound/dosage reporting | T4 PASS + separate authorization | Outcome labeled A_ADVANTAGE / B_NULL / A_FRAGILE per frozen rules | Report supported null/negative; **do not retune** |
| T6 | Robustness seeds (≥4/5) + CA_USES_PAIRING package for method-paper framing | T5 A_ADVANTAGE | Seeds + pairing evidence PASS | A_FRAGILE / mechanism claim withheld |
| T7 | Independent external paired evaluation | Separate cohort access + T5/T6 scope closed | External protocol PASS/FAIL | Remain `STUDY_PARTIAL`; do not claim transportability |

**Authorization boundary.** T1 is documentation-only and may proceed under a future planning/implementation ticket. **T2–T7 require explicit researcher authorization**; this file does not grant it. No task may loop on primary variants until significant.

## Feasibility summary

| Question | Answer |
|---|---|
| Can Gate 0/0b be attempted without new donors? | **Yes** (n=30 internal cohort present) |
| Is CA−TC donor n for A_ADVANTAGE established? | **No** (`min_detectable_delta=null`; X4 mean contrasts ≪ 0.07) |
| Is method-advantage path ready to run? | **No** — waiting on redesign + authorization; binding scientific gap is Gate 0 |
| Precise blocker if stopping without runs? | Not a sample-access blocker for Gate 0. Real-label method path is **conditionally blocked on power** (`BLOCKED_POWER`) until P0/P1 pass or larger n arrives. External phase blocked on cohort access (T13) |
| Recommended researcher decision now | Either authorize T1→T2 under a new ticket, or close method-advantage as unsupported by saved controls and keep the bounded internal null paper |

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
