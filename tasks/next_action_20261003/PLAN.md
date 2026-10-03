# P22 next action — execution plan and Definition of Done

Date: 2026-10-03. Scope: planning and paper preparation. No professor response is required for these tasks.
Cursor final verdict: PASS. Claude final verdict: PASS_WITH_CHANGES, with no blockers. All requested source/provenance corrections are applied below.
No research fits, external scores, payload downloads or outbound messages are authorized.

## Decision

Finish the bounded paper. Make one offline external-data desk decision from existing records. Suspend external scoring and acquisition planning.

Reason: the paper contains accepted evidence. Neural training is complete, but useful disease discrimination and a CA advantage are not established.
The exact-input external test is also unresolved. Repeating metadata work or buying foreign-peak counts does not establish either scientific value or transfer feasibility.
This plan prioritizes a concrete deliverable and a clear scientific limit. It does not promise a positive model result or journal acceptance.

## Task order and records

The task list target is `tasks/todo.md`, section **Next action execution — 2026-10-03**.
The dated `todo.md` contains detailed acceptance and checkpoint criteria for the same task IDs.
Preserve every unrelated unfinished task in the root list.

```text
Task 1: evidence boundary -> Checkpoint A
                             |-> Task 2: bounded paper --|
                             |-> Task 3: offline desk ---|-> Checkpoint B -> Task 4: closeout
```

Tasks 2 and 3 can proceed independently after Checkpoint A. Task 4 requires both outputs.
Do not let the desk decision change the paper's accepted scientific evidence.

## Definition of Done

This definition applies to the preparation stage. It does not certify submission readiness or authorize experiments.

- [ ] **Outputs exist:** `EVIDENCE_BOUNDARY.md`, updated manuscripts, `PAPER_COMPLETION.md`, `EXTERNAL_DESK_DECISION.md` and `CLOSEOUT.md` are linked.
- [ ] **Evidence is traceable:** numbers identify exact arm pairs, source leaves and dated source hashes. Original MOM and raw artifacts remain intact.
- [ ] **Paper checks pass:** the existing numerical checker and saved-fold replay report PASS. Manual claim, citation and figure checks are recorded.
- [ ] **Scientific limits remain explicit:** all historical gates, power limits, dosage interpretation and endpoint limits remain unchanged.
- [ ] **Desk decision is bounded:** `NO_GO_NOW` names the unresolved contracts and future evidence required, without acquisition or a repeated audit.
- [ ] **Open items are honest:** researcher-only declarations and venue requirements name an owner and completion condition. They prevent a submission-ready label.
- [ ] **Completion is evidenced:** the closeout links outputs, current hashes, commands, outcomes and unresolved items before task boxes are marked complete.
- [ ] **Scope remains intact:** zero research fits, external scores, research network requests, downloads, counter resets, outbound messages or automatic research continuation.

Any unresolved discrepancy in a manuscript claim or its supporting source blocks preparation completion.
Named declaration facts and venue requirements can remain open if clearly tracked. Use **preparation complete; submission pending** for that result.
Known external-data blockers are the desk decision's outcome. They do not prevent this preparation stage from completing.

## Checkpoint A — evidence boundary accepted

**Dependencies:** Task 1. **Verification:** compare `EVIDENCE_BOUNDARY.md` with live gates and exact source leaves.

- [x] Evidence record exists with source paths, hashes and professor/worker distinction.
- [x] Primary R3 pair, replay CI, absolute metrics and every scientific label agree with live evidence.
- [x] Any disagreement is resolved or reported as a blocker before Tasks 2 and 3 start.

Checkpoint A **PASS** (2026-10-03): [EVIDENCE_BOUNDARY.md](EVIDENCE_BOUNDARY.md); live `verify_ladder.py` replay PASS without `--write`.

## Task 1 — pin the complete evidence boundary

**Description:** Record the accepted scientific boundary before paper edits or the desk decision.
**Dependencies:** None.
**Files likely touched:** `tasks/next_action_20261003/EVIDENCE_BOUNDARY.md`.
**Estimated scope:** Small, one output file, about 30 minutes.
**Output:** One dated record with source paths, exact source leaves, SHA-256 digests, live labels and the professor/worker distinction.
Read the live verifier, E5 and original professor MOM. Separate professor statements from worker decisions.

**Acceptance criteria:**
- [x] Preserve primary R3_ca minus R3_tc BA +0.02667, CI [-0.0250,+0.07679], margin 0.07 and primary B_NULL.
- [x] Preserve M9 NOT_AUTHORIZED, M10 diagnostic-only, S7/S9/S10 INVALID, S8 NO FIT, E5 NO_GO, ENDPOINT_UNRESOLVED and POWER_UNESTABLISHED.
- [x] Include absolute performance, dosage baseline and the pooled-threshold caveat below. Do not assert new professor endorsement.

Task 1 complete: [EVIDENCE_BOUNDARY.md](EVIDENCE_BOUNDARY.md).

| Accepted saved-result arm | BA | AUROC | Recorded parameters |
|---|---:|---:|---:|
| R3_ca | 0.4000 | 0.3582 | 384,250 |
| R3_tc | 0.3733 | 0.3316 | 380,026 |
| R4_ca | 0.5267 | 0.5147 | 29,970 |
| R4_tc | 0.5000 | 0.4427 | 25,746 |
| logreg_concat | 0.4133 | 0.3822 | 0* |
| Pseudobulk RNA logistic | 0.5133 | 0.5573 | 0* |
| chr21_dosage | 1.0000 | 1.0000 | 0 |

Source: docs/nn_v2/ladder_verification.json, record_type=ladder_verification, per_arm.<arm>.
These are descriptive saved-result metrics, not new model selection. R4 has a different capacity from R3.
*Zeros are the verifier's recorded entries. They do not establish that fitted logistic models have zero coefficients.
Primary arm identity: docs/nn_v2/ladder_summary.json primary.model=R3_ca, primary.reference=R3_tc, also gnhf/verify_ladder.py's explicit arm pair.
Primary CI source: docs/nn_v2/ladder_verification.json primary_recomputed.ci. Use this replay CI rather than the summary's older CI.

The verifier notes that fold-wise thresholds depress pooled majority BA to 0.300. Majority pooled AUROC is also 0.300.
Report AUROC alongside BA. Do not explain every below-chance neural result solely as a threshold artifact.
The zero-parameter dosage control is not neural multimodal improvement or a cell-state endpoint.
Chance-level metrics do not prove that no signal exists. They provide no current evidence for useful transportable neural performance.

**Verification:** Compare each value and label with its exact source leaf. Prefer the verification gate over conflicting task status.
Run the saved-fold replay command below without `--write`. Record its verdict and the source hashes in the evidence record.
**Failure rule:** Stop this stage if the replay fails or scientific labels disagree. Record the discrepancy before any paper edits.

## Task 2 — complete the bounded paper

**Description:** Prepare the existing manuscripts with accepted claims and a concrete submission checklist.
**Dependencies:** Task 1 and Checkpoint A.
**Files likely touched:** `paper/draft.md`, `paper/short_paper.md`, `tasks/next_action_20261003/PAPER_COMPLETION.md`.
**Estimated scope:** Medium, three files, one focused session of at most two hours.
**Output:** Updated manuscripts and a checklist covering scientific claims, references, figures, declarations and remaining venue requirements.
Finish venue-neutral formatting and declarations identified by paper/FULL_DRAFT_REVIEW_2026-10-02.md.

**Acceptance criteria:**
- [ ] Accepted numerical claims remain pinned. Explain absolute performance, dosage dominance, null contrast and power limits. Exclude M9 from accepted results.
- [ ] List remaining citation, figure, declaration and submission requirements. Mark unknown researcher-only facts as unresolved.
- [ ] Do not invent funding, conflicts, professor approval or submission readiness. Do not submit or send a packet.

**Verification:** Run the existing paper source checker. Examine scientific wording against the scoped paper review and live gate records.
In `PAPER_COMPLETION.md`, record command outcomes, changed sections and manual claim/citation/figure checks.
For each unresolved declaration or venue item, record an owner and the exact completion condition.
**Failure rule:** Do not mark Task 2 complete if a claim lacks accepted support or a required numerical check fails.
A numerical checker does not certify citation meaning, figure contents or full submission readiness.

## Task 3 — one offline desk decision

**Description:** Produce one offline decision from the completed external-data evidence.
**Dependencies:** Task 1 and Checkpoint A. Safe in parallel with Task 2.
**Files likely touched:** `tasks/next_action_20261003/EXTERNAL_DESK_DECISION.md`.
**Estimated scope:** Small, one file, at most 30 minutes.
**Output:** One-page `NO_GO_NOW` decision with source citations, inherited blockers and specific future evidence required.
Read TASK_DATA_OPTIONS.md section C1 and next_stage_20260930/external_feasibility.json. Reuse their bags, metadata and hashes.
Do not repeat Q5/R5 or browse in this task. Record file-level Open/Controlled access and reuse as known or unresolved.

**Acceptance criteria:**
- [ ] Emit NO_GO_NOW for acquisition/scoring under the current question and contracts. Record the exact blockers and future evidence required.
- [ ] Preserve unresolved specimen independence, QC release and exact feature/count semantics. Different donor IDs and annotation-count agreement are insufficient.
- [ ] Record ATAC counts package 1,540,753,269 bytes and the historical 256 MiB payload ceiling. Do not issue a purchase/download recommendation.
The ceiling source is failure_audit_20261001/TASK_DATA_OPTIONS.md, section C1 Metadata / payload and section D predictive-ingestion constraint.
It is distinct from external_feasibility.json network.budget_ceiling_bytes=67108864, the completed Q5 metadata budget.

A MEX matrix over different peak intervals generally cannot reproduce counts on the fixed 465-region panel.
Exact transfer requires documented identical intervals/count semantics or compatible fragment/alignment data for exact recounting.
The supplied sources do not establish either path. Fragment availability and size remain unknown. Do not invent a size or declare all transfer mathematically impossible.
RNA features and saved training transformations also require an exact contract. Never zero-fill missing measured regions.

**Verification:** Cite the existing source URL, payload hash, byte declaration and unresolved contracts.
Compare the decision against the existing Q5/R5 records. Record unknown fragment size and access as unknown.
**Failure rule:** Unsupported access, size or compatibility claims prevent Task 3 completion. Retain unresolved labels instead of inventing a PASS.
No new requests, bytes or counter changes.

## Budget register

This revision allows zero network requests, zero downloaded bytes, zero fits and zero external scores.
The previous 32 MiB/20-request proposal is retired. The old Q5 64 MiB/10-request ceiling belongs to its completed historical ledger.
The 256 MiB payload ceiling remains historical and is not raised. Preserve every old ledger. Do not reset or combine their counters.

## Checkpoint B — paper and desk outputs accepted

**Dependencies:** Tasks 2 and 3.

- [ ] Manuscripts and `PAPER_COMPLETION.md` exist. The paper checker reports PASS and manual checks are recorded.
- [ ] `EXTERNAL_DESK_DECISION.md` reports `NO_GO_NOW` with source-backed blockers and no unsupported acquisition recommendation.
- [ ] No unsupported scientific/source discrepancy remains. Open declaration and venue items have owners and completion conditions.

## Task 4 — record closeout

**Description:** Publish the preparation-stage completion evidence and its remaining submission items.
**Dependencies:** Tasks 1–3 and Checkpoints A–B.
**Files likely touched:** `tasks/next_action_20261003/CLOSEOUT.md`, `status.md`, `tasks/todo.md`, dated `todo.md`.
**Estimated scope:** Medium, four files, about 30 minutes.
**Output:** A dated closeout with artifact links, final hashes, command outcomes, manual checks and open items.

**Acceptance criteria:**
- [ ] Every Definition of Done item has a linked output or explicit check result.
- [ ] Closeout states **preparation complete; submission pending** when researcher-only or venue requirements remain open.
- [ ] Task completion marks agree with closeout evidence. Update `status.md` once at the accepted completion gate.

**Verification:** Repeat the two commands below after the manuscript edits. Compare current hashes and labels with Task 1's source record.
Check that output links resolve. Confirm no fits, downloads, external scores, messages, counter resets or new research stages occurred.
**Failure rule:** A failed required check or missing output leaves the corresponding task and closeout unchecked.
Stop after closeout. No automatic dataset search, acquisition, refitting or external inference follows this stage.

## Runnable verification

Run from `/Users/anuragdani/Github/niw-eb1a/P22`:

```sh
.venv-p22/bin/python paper/check_paper.py --json
.venv-p22/bin/python gnhf/verify_ladder.py --run reports/generated/nn_20260923/ladder_v3
```

These commands examine existing artifacts. Do not add `--write`, rerun training or regenerate figures automatically.
This stage changes documents. No software build, dependency install or new test suite is required.
Record command verdicts in the task outputs. A past PASS is not evidence for later manuscript edits.

## Risks and open items

| Risk or unknown | Required handling |
|---|---|
| Dated narrative conflicts with a live gate | Use the gate and record the discrepancy |
| Numerical checks miss meaning or figure provenance | Record manual source/claim/figure checks |
| Funding, conflicts or author facts are unknown | Name the researcher as owner, list the required fact, retain submission pending |
| Venue is not selected | Finish venue-neutral preparation, list venue formatting as pending |
| External counts do not establish exact region semantics | Preserve `NO_GO_NOW`, do not acquire or zero-fill data |

## Future research trigger — outside this active plan

A later research proposal must state a distinct information-bearing question aligned with professor guidance, before any new outcome.
G2/G4 favor granular state over coarse specimen classification. G7 requires a discriminating multimodal benchmark and a concat comparator.
Independent biological-state claims require a defensible orthogonal endpoint. Computational prediction alone does not unlock biology.
Record researcher authorization separately from professor endorsement. Planning authorization is not a scientific acceptance gate.
Do not assume that the September attestation independently certifies a new cohort or changed objective.

Any later external design needs exact feature and specimen/QC contracts, costed inputs, complete reviewed inference/execution hashes and untouched external outcomes.
Name specific frozen checkpoint/selection record IDs before choosing any ensemble. Missing records block that evaluation.
At PCW 13–20, Q5 supports 8 controls and 10 Ts21 donors. One changed prediction contributes 0.0625 or 0.05 to BA.
A 0.07 margin is therefore large relative to this donor grid. This arithmetic is not a power calculation or proof of impossibility.
The present CI does not establish superiority beyond 0.07 or equivalence. Do not change margins after seeing outcomes.

## Review resolution

| Material objection | Revision |
|---|---|
| Metadata audit repeated | One offline desk decision, zero network |
| Counts package cannot establish exact recount | No acquisition recommendation, explicit identical-interval or fragment requirements |
| Weak internal discrimination omitted | Absolute neural and dosage metrics plus threshold caveat added |
| Coarse external objective over-prioritized | External scoring task suspended, new question required separately |
| Budget registers mixed | Zero-budget active stage, historical registers identified |
| Checkpoint selection unspecified | No selection/scoring now, exact frozen IDs required for any future evaluation |

Two review overstatements are not adopted as facts: absent demonstrated signal is not proof of no signal, and a coarse donor grid does not prove impossible superiority.
All original scientific gates and professor records remain unchanged.

## Final review disposition

Both GNHF reviews completed. Cursor PASS. Claude PASS_WITH_CHANGES with no blockers.
Claude RC1–RC4 are resolved by exact R3 pair/replay provenance, the concat row, the budget source and recorded parameter counts.
These are source-checked corrections after review. Do not describe Claude as issuing an unconditional PASS.
See CURSOR_FINAL_ACCEPTANCE.md, CLAUDE_FINAL_ACCEPTANCE.md and REVIEW_STATUS.json.

## Planning update — Definition of Done

This operational update adds task outputs, estimates, checkpoints, runnable checks and the explicit Definition of Done.
It preserves the reviewed scientific scope. Prior Cursor/Claude verdicts refer to their saved snapshots, not a new review of this update.
Implementation task boxes remain unchecked until their output evidence exists.
