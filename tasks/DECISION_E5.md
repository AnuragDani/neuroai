# E5 — Evidence-based GO/NO_GO for a separately scoped future pilot

**Disposition:** `NO_GO`  
**Date:** 2026-10-02  
**Branch:** `gnhf/p22-nn-cellstate`  
**Dependencies:** E4 independent no-fit review `PASS` on commit `3eb7f74279d5f27bfee1dc0d7c59a9a8996b8aed` with 17/17 immutable lock rematch.  
**Machine record:** [decision_e5.json](decision_e5.json).

No research fits, downloads, worktrees, counter resets, push, or professor messages in E5. Historical M9 remains **NOT_AUTHORIZED**. Primary **B_NULL** unchanged. Prior S10/S9/S7 **INVALID**, S8 **NO FIT**, Q2 **ENDPOINT_UNRESOLVED** retained. `scientific_fits_authorized=false`. Reviewed execution source unchanged.

This decision does **not** authorize fits. A hypothetical GO would also not have authorized fits.

---

## Verdict

**NO_GO** for a separately scoped future research pilot as the next action of this execution-repair track.

E4 established process readiness (full real-data path under reviewed hashes). Process readiness is necessary but not sufficient for a new pilot. Plan E5 requires scientific value **beyond** current diagnostic results, fixed design before outcomes, and alignment with July professor guidance — not automatic re-dispatch after control repair.

---

## Evidence used

| Evidence | Role |
|---|---|
| [INDEPENDENT_REVIEW_E4.md](INDEPENDENT_REVIEW_E4.md); [NO_FIT_REVIEW_E4.json](NO_FIT_REVIEW_E4.json) | E4 PASS; 17/17 lock; fits still unauthorized |
| M10 [HANDOFF.md](nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001/HANDOFF.md); [REPLAY.md](nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001/REPLAY.md) | Diagnostic TC−CA ≈+0.00154; bootstrap CI includes 0; exploratory advantage not met; scientific M9 NOT_AUTHORIZED; one next action was stop |
| [GUIDANCE_AND_CLAIMS.md](nn/professor_direction_investigation_20260929/failure_audit_20261001/GUIDANCE_AND_CLAIMS.md) | July 2/21 MOM → claim levels; G7 discriminating multimodal benchmark; claim-4 blocked by Q2 |
| [plan.md](plan.md) E5 + Checkpoint C | Value beyond diagnostics; GO ≠ fits; no automatic new pilot; biology needs orthogonal endpoint |
| Live rematch this decision | Reviewed commit is ancestor of HEAD; 17/17 immutable lock digests rematch; no `src/` / runner drift vs reviewed commit |

### Diagnostic numbers (not scientific acceptance)

Unauthorized M9 / diagnostic M10 replay (claim-level-2 ceiling only):

- Pooled donor-average cell log-loss **TC − CA ≈ +0.00154**
- Fixed-prediction bootstrap 95% CI **[−0.00220, +0.00475]** (seed 601001)
- Pre-fit practical margin **0.01** → exploratory advantage **not met**
- Counters preserved **30/40**; fits during repair/E5: **0**

These numbers **cannot** be promoted to scientific PASS (prospective gate FAIL). They **can** inform whether repeating the same estimand after outcome visibility adds scientific value. They do not overturn primary **B_NULL**.

---

## Comparison to July professor guidance

| Guidance | Implication for E5 |
|---|---|
| **G7** (Jul 21): find a case that differentiates models; concat baseline; independent modalities | Claim-2 masked-ATAC CA vs token-concat was a valid discriminating candidate. Diagnostic contrast is near zero and CI includes 0 — it does **not** currently justify another attempt at the same contrast as a differentiating benchmark. |
| **G4/G2**: prefer granular state/spectrum over coarse person-level subtype | Claim-4 biological state remains blocked by Q2 `ENDPOINT_UNRESOLVED`. E5 cannot unlock biology. |
| **G8**: faithfulness / held-out interventions for routing claims | No new faithfulness protocol is proposed here; repairing executor review does not create a faithfulness question. |
| **G9**: disease training pending objective/dataset approval | No disease-objective change; attestation is not treated as dated Fang endorsement of a new task. |
| Claim hierarchy (R4) | Levels 1–2 may proceed without orthogonal state; level 4 may not. Permission to *consider* claim-2 ≠ obligation to re-pilot after a near-null diagnostic peek. |

---

## Why NO_GO (scientific value test)

Plan acceptance: explain value **beyond** current diagnostic results; do not select dataset/model changes merely to improve results.

1. **Same estimand, already measured diagnostically.** The open claim-2 question (RNA + chromosome-masked visible ATAC predicting training-only binary accessibility; CA vs TC on donor-average cell log-loss) was already executed and replayed. Exploratory advantage was not met. Re-fitting under the E4 lock would mainly convert an unauthorized near-null into an authorized near-null — process hygiene, not new scientific information.
2. **Outcome visibility breaks clean pre-outcome design for a repeat.** Workers and this decision have seen the diagnostic contrast. Dispatching the identical success rule/budget after that peek is outcome-conditioned continuation, which the M10 closeout forbade as positive-result search and which E5 forbids as result-driven redesign.
3. **E4 readiness ≠ E5 justification.** Closing the prospective-review gap enables a future locked claim; it does not, by itself, justify spending a new attempt budget on the same contrast.
4. **Claim-4 remains blocked.** No independently measured cell-state endpoint exists (Q2). A GO that silently upgraded biology would violate guidance and Checkpoint C.
5. **Rejected result-chasing alternatives.** Changing targets, seeds, margins, architectures, or datasets to obtain a larger CA−TC after seeing the near-null is explicitly forbidden by plan E5 and M10 rejected actions.

### What this does *not* decide

- It does **not** rewrite M9 to PASS or FAIL as a scientific acceptance label (remains **NOT_AUTHORIZED**).
- It does **not** forbid a **later**, separately planned stage that defines a *new* question/estimand **before** outcomes (different claim-1 control, different claim-2 construct, or claim-4 after an orthogonal endpoint). Such a stage needs its own plan, protocol freeze, and independent pre-fit review — outside this repair loop.
- It does **not** revoke E0–E4 control repairs or the 17-key lock.

---

## Rejected alternatives (not selected)

| Alternative | Why rejected now |
|---|---|
| **GO** — re-authorize identical M5/M9 estimand under E4 lock | Fails “value beyond diagnostics”; outcome-conditioned; risks positive-result search |
| **GO** — same estimand with tightened/loosened success margin or new seeds | Result-driven threshold/seed change forbidden |
| **GO** — new dataset / model family to improve CA−TC | Plan E5 forbids dataset/model changes merely to improve results; NeMO role preserved |
| **GO** — biological cell-state pilot | Q2 `ENDPOINT_UNRESOLVED` (claim-4 blocked) |
| **GO** — claim-1 software re-control in this loop | S9/S10 already closed INVALID; not the E5 masked-pilot question; would need a separate failure-audit-style plan |
| Treat diagnostic near-null as scientific M9 FAIL/PASS | Prospective gate FAIL forbids promotion |

---

## Protocol proposal

**Not issued.** Plan E5 requires a next-stage protocol proposal only if justified. Under **NO_GO**, no question / cohort / estimand / success rule / attempt budget is frozen for dispatch.

---

## Preserved scientific labels

| Label | Status after E5 |
|---|---|
| Masked-ATAC M9 scientific acceptance | **NOT_AUTHORIZED** |
| Primary ladder | **B_NULL** |
| S10 / S9 / S7 | **INVALID** |
| S8 | **NO FIT** |
| Q2 endpoint | **ENDPOINT_UNRESOLVED** |
| `scientific_fits_authorized` | **false** |
| Research fits this stage | **0** |

---

## One next action

**Checkpoint C:** commit the verified E0–E5 repair/review/decision handoff and stop. Zero research fits. No automatic pilot, downloads, push, or professor messages.

---

## Acceptance checklist (plan E5)

1. Scientific value beyond diagnostics examined — **YES** (found insufficient for GO).
2. Fixed question/cohort/targets/estimand/success rule/budget before outcomes — **N/A** under NO_GO (no protocol proposal).
3. Compared to July guidance and current diagnostic/primary claims — **YES**.
4. Explicit **GO** or **NO_GO** with reasons — **NO_GO**.
5. GO does not dispatch fits — **N/A** (NO_GO); fits remain unauthorized either way.
6. Historical M9 / B_NULL / INVALID / NO FIT unchanged — **YES**.
7. Zero research fits — **YES**.
