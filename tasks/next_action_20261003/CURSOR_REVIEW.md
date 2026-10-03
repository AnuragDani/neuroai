# Independent plan review — P22 next-action proposal

**Reviewer:** cursor (independent; scratch-repo evidence only)  
**Date:** 2026-10-03  
**Proposal:** `PROPOSAL.md` (2026-10-03)  
**Verdict:** `PASS_WITH_CHANGES`

This is a challenge review, not an approval stamp. The proposal correctly refuses same-task pilot revival and preserves closed scientific gates, but its lead track still largely re-opens work Q5/R5 already bounded, under constraints that make `GO_FOR_PROTOCOL` near-impossible without raising the acquisition ceiling the proposal itself refuses to raise.

---

## Verdict summary

| Dimension | Assessment |
|---|---|
| Novelty vs completed Q5/R5 | Partial only — file-level Open/Controlled access is new; QC / specimen / feature contracts are largely re-litigation |
| Best-information ranking | Weak — paper deliverable is clearer near-term value than a four-contract NeMO re-close |
| Professor guidance | Mostly aligned on claim-4 block and no M9 repeat; soft on G9 dataset/objective approval for Task 3 |
| Source access / budgets | Internally consistent on not silently raising the ceiling; inconsistent with claiming Task 2 can “close” feature/count without payload |
| Model transfer / zero-fit | Strong zero-fit and no-refit language; transfer exactness likely fails for 465-region inputs |
| Independence / QC | Correct that donor-ID non-overlap ≠ independence; acceptance criteria for “resolve” are underspecified |
| Closed E5 | Respected for same-task pilot; external disease-transport is a different estimand and is allowed in principle |

---

## What the proposal gets right

1. **Primary numbers and labels match live evidence.**  
   CA−TC BA +0.02667 with CI [-0.0250, +0.07679] below margin 0.07 matches `evidence/docs/nn_v2/ladder_verification.json` (`estimate` 0.026666…, CI [-0.0250, 0.0767857…], `advantage: false`, `verdict: PASS`).  
   N11 dosage dominance, N13 pairing unused, N16 `SPECTRUM_NULL`, power unestablished, M9 `NOT_AUTHORIZED`, M10 diagnostic-only, E5 `NO_GO`, and Q2 biology block are consistent with `evidence/status.md`, `evidence/tasks/DECISION_E5.md`, and `evidence/docs/INDEX.md`.

2. **E5 is not silently reopened.**  
   `evidence/tasks/DECISION_E5.md` NO_GO applies to another same-estimand masked-ATAC pilot after diagnostic peek. The proposal rejects repeating M9 / seed-threshold churn and keeps `scientific_fits_authorized` implicitly false for this stage. E5 also explicitly leaves room for a later separately planned stage with a *new* question — external transport of the existing disease estimand can qualify if scoped tightly.

3. **Zero-fit / no hidden retuning intent is mostly sound.**  
   No matrices/fragments in Task 2; no external outcomes for tuning; do not alter the development panel to fit NeMO; CI overlap ≠ equivalence; equal donor weighting; paper must not absorb external results before acceptance — all match the spirit of E4/E5 and `evidence/paper/FULL_DRAFT_REVIEW_2026-10-02.md`.

4. **NeMO is correctly treated as a candidate, not a PASS.**  
   Matches Q5 `overall_confirmatory_status: UNRESOLVED` and `confirmatory_ready: false` in `evidence/tasks/nn/professor_direction_investigation_20260929/next_stage_20260930/external_feasibility.json`, and R5 preservation of the external-test role in `…/TASK_DATA_OPTIONS.md` §C1.

---

## Objections (ranked by severity)

### 1. HIGH — Task 2 mostly repeats completed Q5/R5 under a new label

**Claim in proposal:** “Prior Q5/R5 already examined metadata. Do not repeat those audits. Resolve their specific remaining contracts or stop.”

**Evidence conflict:** Q5 already closed as `EXTERNAL_FEASIBILITY_BOUNDED` with confirmatory `UNRESOLVED`, and named the same blockers the proposal wants to “close”:

| Contract | Q5 status (`external_feasibility.json`) | Still open after R5 (`TASK_DATA_OPTIONS.md` §C1) |
|---|---|---|
| QC release discrepancy | `UNRESOLVED` (117,532 vs 113,801; `ANNOTATION_COUNT_MATCH_QC_UNVERIFIED`) | UNRESOLVED |
| Specimen provenance | `UNRESOLVED` (`no_overlap_evidence`, `specimen_independence_certified: false`) | UNRESOLVED |
| Feature / count semantics | `UNRESOLVED` (`paired_matrices_checked: false`; study-specific peaks) | UNRESOLVED |
| Source / payload declaration | `ACCEPTED` at **1,540,753,269 bytes** | Still ~1.4G / ~1.54 GiB; exceeds 256 MiB ceiling |

R5 explicitly concluded: no public candidate ready for ≤256 MiB predictive ingestion; NeMO counts ~1.4G; QC/specimen/feature still unresolved (`TASK_DATA_OPTIONS.md` §D).

**Why this matters:** A two-hour “close four contracts” session that reuses the same bags and restates the same UNRESOLVED leaves will not advance P22; it will re-emit Checkpoint A as `PAYLOAD_REQUIRED` or `NO_GO`. The only clearly new slice in the proposal is **file-level Open vs Controlled access** on the 2026-10-03 collection read. That slice should be the Task 2 scope — not a full feasibility re-audit.

### 2. HIGH — Internal contradiction: feature contract “close” vs acquisition ceiling

Proposal Task 2 acceptance requires “exact required region counts, count units, RNA features and saved training transformations” and “Never zero-fill absent measured regions,” while stating the declared ATAC payload is 1,540,753,269 bytes and “This plan does not silently raise” the historical 256 MiB ceiling.

Q5 already resolved the payload *declaration* and forbade download under budget (`external_feasibility.json` `feature_count_semantics`, `costed_payload_note`). Exact measured-region overlap versus the development 465-region union cannot be demonstrated without matrix/peak payloads or an equivalent local recount — both out of scope.

**Consequence:** Under the proposal’s own rules, Checkpoint A `GO_FOR_PROTOCOL` is effectively unreachable for a true multimodal external score. Ranking “resolve contracts → freeze protocol” as the primary path overstates decision value. The honest terminal states for this candidate in this stage are almost certainly `PAYLOAD_REQUIRED` (costed ≥1.54 GiB ATAC package) or `NO_GO` (if ceiling stays binding).

### 3. MEDIUM-HIGH — Best-information ranking should put the paper first (or truly equal), not NeMO-first

`evidence/paper/FULL_DRAFT_REVIEW_2026-10-02.md` already has numerical/source reconciliation PASS; remaining work is publication formatting/declarations and a dated unsent professor update — with **zero** research fits. `evidence/status.md` (2026-10-02) likewise points next writing work at packet/formatting, not another NeMO metadata pass. The short paper already states that no independent paired cohort tested transport (`evidence/paper/short_paper.md` §VII–VIII).

Expected information per cost: finishing the bounded negative paper converts accepted `B_NULL` into a durable deliverable regardless of NeMO. Another metadata session on three already-documented UNRESOLVED contracts has a predictable non-informative outcome. The proposal’s option table therefore mis-ranks.

### 4. MEDIUM — Professor / dataset-approval boundary softens at Task 3

`GUIDANCE_AND_CLAIMS.md` G9: disease-specific training pending objective/dataset approval; user attestation covers **existing** public-data RNA/paired plans, not a dated Fang endorsement of a *changed* disease objective/dataset. Planning without a professor response is fine for Task 1 evidence boundary and a narrow access ledger. Freezing an external evaluation protocol that scores selected CA/TC disease models on NeMO (Task 3) is closer to adopting a new evaluation dataset for the disease objective.

The proposal says “new professor endorsement is not asserted” and “Do not wait for professor to execute planning,” but does not require an explicit attestation-scope check before Task 3 authorization. That gap should be closed: Task 3 must remain protocol-prep only, and any later acquisition/scoring needs a separate authorization record that does not invent professor approval.

### 5. MEDIUM — “Resolve QC / specimen with source documentation” lacks a stop definition

Q5 already showed annotation-count match without QC reproduction, and empty donor-ID overlap without certified independence. Without defining what countable evidence upgrades `UNRESOLVED` → pass (and forbidding author contact / payload as R5 did), Task 2 can churn on the same diagnostics. Default if documentation cannot certify independence or reproduce QC: keep `UNRESOLVED` and route to Checkpoint A `NO_GO` / `PAYLOAD_REQUIRED` — do not invent a PASS.

### 6. LOW — Collection “restricted / mixed open-controlled” is useful but not a feasibility PASS

The proposal’s 2026-10-03 NeMO note (26 donors; mixed Open/Controlled; top access restricted) is appropriately caveated. Keep it as an access-ledger input only; do not let it substitute for the three Q5 blockers.

---

## Challenge answers (review checklist)

| Question | Answer |
|---|---|
| Repeats completed Q5/R5? | **Yes, substantially**, unless Task 2 is narrowed to new file-level access + inherited blocker restatement |
| Advances P22? | **Only if** paper proceeds and NeMO work terminates in a single costed blocker / NO_GO without protocol theater |
| Best-information recommendation sound? | **Not as ranked** — paper ≥ NeMO access ledger; full four-contract close is low EV |
| Professor guidance? | Claim-4 / E5 / no M9: good. G9 dataset adoption for Task 3: needs hardening |
| Source access? | Ceiling honesty good; feature-close claim incompatible with ceiling |
| Model transfer? | Zero-fit good; exact 465-region transfer likely incompatible — mark early, do not redesign |
| Independence/QC? | Principle correct; resolution criteria incomplete |
| Zero-fit scope? | Acceptable if Task 3 stays dry-run/synthetic and no downloads |
| Closed E5? | Preserved; do not treat this stage as E5 override or automatic pilot |

---

## Required changes before execution

1. **Narrow Task 2** to: (a) file-level Open vs Controlled package inventory and reuse conditions from existing bags/collection metadata; (b) **inherit** Q5/R5 UNRESOLVED dispositions for QC, specimen, and feature/count without re-deriving them; (c) if any remaining contract requires >256 MiB or controlled retrieval, emit `PAYLOAD_REQUIRED` or `NO_GO` immediately with the single measured blocker.
2. **Re-rank options:** Task 4 (paper formatting + declarations per `FULL_DRAFT_REVIEW_2026-10-02.md`) becomes primary or true parallel default; NeMO work is a bounded access/blocker ledger, not the lead scientific bet.
3. **Pre-declare Checkpoint A priors:** under current ceiling, do not plan as if `GO_FOR_PROTOCOL` is the expected path; require explicit separate authorization before any ceiling exception or controlled-access request.
4. **Gate Task 3:** only after true `GO_FOR_PROTOCOL`; add attestation-scope / non-endorsement check; forbid treating protocol freeze as dataset approval.
5. **Define QC/specimen stop rules:** documentation insufficient → remain UNRESOLVED → fail external scoring gate; empty donor-ID overlap never upgrades to certified independence (already stated — make it an acceptance fail condition).
6. **Keep all scientific labels immutable** as in Task 1 (`B_NULL`, `NOT_AUTHORIZED`, `INVALID`, `POWER_UNESTABLISHED`, `ENDPOINT_UNRESOLVED`, E5 `NO_GO`).

---

## Revised brief course of action

1. **Task 1 (keep):** one short decision record pinning live ladder leaves, E5, M9/M10, Q2, and professor-vs-worker separation. No new endorsement claim.  
2. **Task 4 (promote):** complete venue-neutral formatting and missing declarations from `evidence/paper/FULL_DRAFT_REVIEW_2026-10-02.md`; keep numerical claims pinned; exclude M9; do not mark submission-ready or sent.  
3. **Task 2′ (replace Task 2):** ≤2 h, metadata-only, ≤20 requests / 32 MiB: file-level Open/Controlled access ledger only; cite Q5 hashes/bytes for payload declaration (1,540,753,269; MD5 `796c8b3aa587b257af0a46615a437dba`); list inherited UNRESOLVED blockers; abort to single-blocker `PAYLOAD_REQUIRED` or `NO_GO`. No matrix/fragment download, no installs, no author contact.  
4. **Checkpoint A:** expect `PAYLOAD_REQUIRED` or `NO_GO` unless Open packages unexpectedly supply exact transferable measured features under ceiling — do not broaden search.  
5. **Task 3:** skip unless Checkpoint A is genuinely `GO_FOR_PROTOCOL` under unchanged ceiling and attestation-scope check passes. Protocol prep only; zero external predictions; incompatibility ⇒ mark, do not refit development panel.  
6. **Stop rule:** paper preserved; NeMO track closed or parked behind one costed acquisition proposal; still no professor message, no fits, no E5 reopen.

---

## Evidence cited

- `PROPOSAL.md`
- `evidence/status.md`
- `evidence/docs/INDEX.md`
- `evidence/docs/nn_v2/ladder_verification.json`
- `evidence/tasks/DECISION_E5.md`
- `evidence/tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001/GUIDANCE_AND_CLAIMS.md`
- `evidence/tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001/TASK_DATA_OPTIONS.md`
- `evidence/tasks/nn/professor_direction_investigation_20260929/next_stage_20260930/external_feasibility.json`
- `evidence/paper/FULL_DRAFT_REVIEW_2026-10-02.md`
- `evidence/paper/short_paper.md`
