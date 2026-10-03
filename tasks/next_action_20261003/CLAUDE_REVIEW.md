# CLAUDE_REVIEW — independent review of PLAN.md

Reviewer: claude. Date: 2026-10-03. One pass. No fits, downloads, browsing, contact or evidence edits.
Sources read: `PLAN.md`, `evidence/docs/nn_v2/ladder_verification.json`, `evidence/tasks/DECISION_E5.md`,
`evidence/tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001/GUIDANCE_AND_CLAIMS.md`,
`evidence/tasks/nn/professor_direction_investigation_20260929/failure_audit_20261001/TASK_DATA_OPTIONS.md`,
`evidence/tasks/nn/professor_direction_investigation_20260929/next_stage_20260930/external_feasibility.json`,
`evidence/paper/FULL_DRAFT_REVIEW_2026-10-02.md`.

## Verdict: PASS_WITH_CHANGES

Task 1 and Task 2 are correct and correctly ordered: the paper is the only deliverable with accepted numbers, and label
preservation is faithful to `DECISION_E5.md` and `FULL_DRAFT_REVIEW_2026-10-02.md`. The external branch is not wrong in
its gates but is wrong in its expected value. It is not a FAIL only because Task 4 sits behind a gate the plan itself
expects to stay shut. I do not endorse the Cursor PASS as written.

## Material objections, ranked

**1. The planned acquisition cannot satisfy the plan's own exact-region stop rule.** Task 4 forbids zero-fill and stops
unless the 465-region input transfers exactly. `external_feasibility.json` `feature_count_semantics` is UNRESOLVED with
"study-specific peak calling", and the only resolved payload is a counts MEX over that study's peaks
(1,540,753,269 bytes). A MEX count matrix on foreign peaks can never be remapped to a fixed 465-interval union without
fragment or alignment data, which Task 3 forbids and which is far larger. So the Checkpoint A proposal, as scoped, buys
a confirmation of impossibility. State this before costing, and name the fragment-level requirement and its size, or
drop the exact-transfer claim.

**2. There is no internal signal to transport.** `ladder_verification.json` `per_arm`: `R0_ca` BA 0.473 / AUROC 0.389;
`R1`–`R3` arms 0.34–0.40 BA with AUROC 0.33–0.38; best CA arm `R4_ca` 0.527 / 0.515; `pseudobulk_rna_logistic`
0.513 / 0.557. Most arms are at or below chance. Separately `chr21_dosage` scores BA 1.000 / AUROC 1.000 at zero
parameters. Task 4's question — do selected disease-prediction models transport across studies — presupposes
transportable performance and a non-trivial outcome; neither holds. PLAN.md never cites either number.

**3. Task 1's preserved set is incomplete.** It pins +0.02667, the CI, margin 0.07 and B_NULL but omits
`chr21_dosage` BA 1.000 and the verifier's own `notes` entry on pooled-threshold BA depression with AUROC below 0.5.
Those two facts bound every downstream claim; preserve them explicitly.

**4. Task 3 re-derives a settled conclusion.** `TASK_DATA_OPTIONS.md` §C1 already records public NeMO access, the 1.4G
listing, the 256 MiB exceedance and all three blocking contracts; `external_feasibility.json` already resolved URL,
bytes and MD5. Only the per-file Open/Controlled split and reuse terms are genuinely new. Collapse Task 3 to a desk
note citing those two records, with network only if file-level access is truly unknown.

**5. Donor arithmetic is finer than the grid.** `age_conventions.age_overlap` gives 8 control / 10 Ts21 donors at
PCW 13–20. Under equal donor weighting, BA moves in steps of 0.0625 and 0.05 per class, so the 0.07 margin is roughly
one donor flipping. The current primary already shows the failure mode: CI upper bound 0.0768 against margin 0.07, so
advantage is near-structurally unreachable. Say this in the plan, not just "support is not power".

**6. Professor alignment is disclosed but non-responsive.** G2/G4 in `GUIDANCE_AND_CLAIMS.md` call person-level output
too coarse and subtype saturated; G7 asks for a case that differentiates models; G9 keeps disease training pending
objective and dataset approval, with attestation `professor_approval_date: null`,
`independently_verified: false`. Task 4 knowingly adopts the person-level specimen outcome and a contrast whose CI spans
zero. "Examine the September attestation scope" must become a hard blocker: a new external cohort is outside the
attested existing-public-data scope.

**7. Three ceilings, one plan.** 32 MiB / 20 requests here, 64 MiB / 10 in `external_feasibility.json`, 256 MiB
historical. "Preserve earlier counters" does not say which register governs. Name it.

**8. Selection provenance.** Per `DECISION_E5.md` outcome-visibility reasoning, Task 4 must cite the specific frozen
selection record ID for CA/TC checkpoints, not "original selection records" generically.

## Next course

Do Task 1 with objections 3 and 5 folded in, then Task 2 to completion. Replace Task 3 with a one-page desk decision
emitting PAYLOAD_REQUIRED or NO_GO from existing records. Suspend Task 4 until a question exists that is not transport
of a chance-level model. No fits, payloads or acquisition authorized.
