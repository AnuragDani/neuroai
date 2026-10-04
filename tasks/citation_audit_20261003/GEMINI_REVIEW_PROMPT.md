You are Gemini acting as an independent scientific-audit planning reviewer. Review the self-contained plan below. Do not browse, run tools, edit files, train models or invent source findings. The human explicitly requests this consultation before execution. Return a concise review with (1) verdict PASS / PASS_WITH_CHANGES / BLOCKED, (2) necessary corrections ranked by importance, (3) executable acceptance criteria and definition of done, and (4) whether the new scoped audit is sufficient to close C3 without redoing experiments. Distinguish citation support from numerical validation. Do not approve merely because checkers pass. Identify risks in the atlas paired-cell claim, attention disagreement, donor-DE-to-classification extrapolation and mixed grouped citations.

# P22 citation-support audit — 2026-10-03

## Authority and scope
User authorizes branch consolidation/push, a Gemini plan review through acpx, and execution. Consolidation is complete: main fast-forwarded to d0f043c; all previous live branch heads are ancestors; merged local/remote develop and gnhf names removed; only primary worktree remains. Original GNHF handoff stays in history.

This is a separately authorized source-verification stage. The exhausted submission-preparation ledger (approximately 25/24 requests) remains unchanged. Scientific artifacts, frozen bibliography, accepted full/short manuscripts, claims ledger and original professor MOM are preserved. Edit only the provisional venue copy if citation wording needs repair. No fitting, plot regeneration, data acquisition, outbound contact or submission.

## Goal and Definition of Done
Close required source gate C3 by checking every citation-bearing scientific claim in paper/submission_20261003/draft.md against primary source text. Cover all 17 cited keys, including repeated uses and grouped citations. A title, DOI, bibliographic match, search snippet or model memory is not entailment evidence.

Done requires a claim/source inventory; exact primary URL and section/page; short supporting passage or faithful paraphrase; explicit PASS / narrowed-and-PASS / unresolved / failed for each claim; no retained unsupported claim; all automated checks PASS; accepted source hashes unchanged; Gemini review recorded and material concerns addressed; readiness and task marks agree with actual coverage. Missing human declarations remain submission inputs and cannot be invented.

## Tasks (sequential; checklist is in this plan)

### T1 — Gemini review (small)
- [ ] Review this plan with Gemini through acpx before execution.
- [ ] Save exact response and address each required change or explicitly justify rejection.
**Acceptance:** reviewer assesses scope, completeness, inference risks, resource accounting, blocked/ready rule and verification; returns PASS / PASS_WITH_CHANGES / BLOCKED with concrete acceptance criteria.
**Verification:** reviewer artifact exists, identifies Gemini/acpx, and dispositions are recorded. If review is unavailable, record tool evidence and do not claim consultation happened.
**Dependencies:** none. **Files:** this plan, GEMINI_PLAN_REVIEW.md.

### T2 — Inventory and primary-source support (medium)
- [ ] Enumerate all citation-bearing claims before References; distinguish published findings from this study's design choices and measured local cohort counts.
- [ ] Retrieve only primary citation documents; record source locations and support for all 17 keys and repeated claim uses.
- [ ] Check disputed attention-as-explanation positions, donor-replicate-to-classification extrapolation, source atlas population vs local processed subset/paired modality claim, and gene-activity window attribution explicitly.
**Acceptance:** every retained citation-bearing scientific statement has source-specific support; contradictions and scope differences are explicit. Whole sentence plus grouped references must be evaluated, not each key in isolation. Absence of accessible evidence is unresolved, not PASS. Source results do not validate this cohort or method.
**Verification:** inventory coverage vs regex extraction of draft keys/occurrences, manual entailment table, URL/section checks, bounded network ledger.
**Dependencies:** T1. **Files:** AUDIT.md, NETWORK.md, evidence excerpts (if needed; use existing artifacts).

### Checkpoint — Support established
- [ ] Every citation use has a disposition; no unresolved item is concealed by metadata PASS.

### T3 — Surgical wording repairs (small)
- [ ] Correct or remove unsupported provisional wording; split sources with differing positions; cite design choices as this study's choices where appropriate.
- [ ] Preserve accepted numerical results, scientific gate labels, figures and frozen citation keys/metadata.
**Acceptance:** minimal diff; every retained claim traceably supported. Explicitly unresolved essential cohort/source provenance blocks readiness rather than being erased to manufacture completion.
**Verification:** compare provisional diff and hash-check protected files; reread revised statements against cited passages.
**Dependencies:** T2. **Files:** provisional draft, AUDIT.md.

### T4 — Verification and handoff (medium)
- [ ] Run both paper checkers and saved-prediction ladder verifier with no --write.
- [ ] Rematch protected scientific/manuscript/MOM hashes; record audit coverage and resource limits.
- [ ] Update current READINESS.md, stage task marks, status.md and docs/INDEX.md at accepted gate or blocker; commit and push final work to main.
**Acceptance:** READY_FOR_RESEARCHER_REVIEW only if all required scientific/source checks are resolved; otherwise BLOCKED with unfinished tasks unchecked, exact evidence and smallest unblock. Human authors/funding/ethics/venue/export items stay separate.
**Verification commands:**
```
.venv-p22/bin/python paper/check_paper.py --json
.venv-p22/bin/python paper/check_paper.py --draft paper/submission_20261003/draft.md --refs paper/refs_frozen.bib --claims paper/claims.csv --json
.venv-p22/bin/python gnhf/verify_ladder.py --run reports/generated/nn_20260923/ladder_v3
```
**Dependencies:** T3. **Files:** current handoff/task list, status/index, AUDIT.md/this plan. Update the existing handoff rather than adding a second readiness authority.

## Resource limits and failure rules
This stage permits at most 32 primary-source retrieval attempts (including failures and explicitly initiated follow-ups) and 32 MiB retained response text/documentation; at most one fallback per inaccessible source. No venue/APC refresh, dataset download or dependency install. Start with exact primary URLs from frozen metadata and canonical conference/publisher archives. Prefer HTML/abstract for broad claims when sufficient; use full methods text for specific procedures. Record tools, URLs, attempt counts and limitations. If web tools conceal internal HTTP redirects or response byte totals, label accounting as logical retrieval attempts/retained text, never certify exact underlying HTTP requests or downloaded bytes. Stop when either measurable cap is reached; no reset of old stage. Gemini consultation is separate agent inference, not a literature request; forbid its browsing for the plan review.

## Risks and mitigation
- Opposing attention papers: represent disagreement; do not claim joint consensus.
- Donor replicate paper concerns differential expression: motivate design cautiously; do not imply it validates ML generalization.
- Atlas count/modality vs local subset: match exact cohort and processed data; numerical equality alone is not primary-source support.
- Paywalls: use author/conference primary text or sufficiently specific primary abstract once; otherwise unresolved.
- Frozen metadata errors: record erratum separately and block material attribution problems; do not silently change frozen bib.
- Budget/execution failures: record blocker; preserve completed work, original ledgers and evidence.

## Reviewer disposition
Pending Gemini review.
