# P22 submission preparation — Cursor Auto / GNHF

Execute this new, bounded submission-preparation stage. The researcher authorizes preparation without waiting for Professor Fang.
Do not rerun the completed four-task next_action_20261003 stage.

## Entry and source priority

Read AGENTS.md, status.md and docs/INDEX.md once at entry. Then read:
- tasks/next_action_20261003/CLOSEOUT.md
- tasks/next_action_20261003/PAPER_COMPLETION.md
- tasks/next_action_20261003/EVIDENCE_BOUNDARY.md
- paper/draft.md, paper/short_paper.md, paper/claims.csv and paper/refs_frozen.bib

Use focused source reads after entry. Recheck exact live gate leaves when a scientific claim depends on them.
Do not load the full historical task backlog, past GNHF streams, previous reviewer logs, raw matrices or model checkpoints.
Read the current GNHF iteration notes as the orchestrator requires. Later iterations reuse completed outputs rather than repeating research.
Preserve original MOM, accepted source artifacts, previous closeouts and review snapshots. A changed live file does not retroactively alter a dated hash snapshot.

## Goal

Prepare a venue-specific manuscript draft, source/figure audit and a concise list of researcher facts required before submission.
A recommendation is provisional until the researcher selects the venue. Do not invent author facts or claim submission readiness.

## Tasks and dependency order

Create tasks/submission_readiness_20261003/todo.md with these four tasks and their acceptance criteria.
Each task must produce a usable artifact. The final iteration must close out rather than start another audit.

### Task S1: compare venues

Output: tasks/submission_readiness_20261003/VENUES.md.
Use current official publisher/journal pages for 3–5 plausible venues. Compare aims/scope, article type, negative-result suitability,
length limits, required declarations, artifact policy and publication charges or waivers. Mark unknown requirements explicitly.
Recommend one provisional target with evidence and explain fit for a bounded null benchmark, not a proven superior method.
Do not promise acceptance or infer that a venue accepts negative results solely because it publishes computational biology.
Capture URL, access date, exact requirement and uncertainty for each material recommendation. Never use a search snippet as the final authority.

Network scope is new and separate from the completed zero-network research stage: official venue instructions and primary citation verification only.
Hard cap: 24 external requests and 32 MiB aggregate downloaded documentation. Record requests/bytes in VENUES.md or AUDIT.md.
Abort oversized responses before reading their bodies. Stop at the cap. No datasets, fragments, matrices, controlled-access requests or author contact.
Do not reset any historical counter. Do not install dependencies. If access fails, record that fact instead of repeated retrieval attempts.

Acceptance: sourced comparison exists, recommendation is provisional, and costs/limits are current or explicitly unresolved.

### Task S2: adapt a copy of the manuscript

Dependency: S1.
Output: paper/submission_20261003/draft.md.
Copy the accepted full draft. Adapt its sections, references and figure paths to the provisional venue's documented requirements.
Keep all accepted numerical results unchanged. Retain frozen citation keys so existing checks still work.
Expand references from refs_frozen.bib with verified metadata. Reuse existing tools and files.
Do not change the accepted paper/draft.md, paper/short_paper.md or paper/claims.csv merely to fit a provisional venue.
Fix relative image paths in the new copy. Do not regenerate figures, rerun analyses or create a new build pipeline.
If the venue-specific format is unsupported, preserve the Markdown source and state the remaining export requirement.

Acceptance: the new draft is clearly provisional, complies with known venue rules and preserves the original scientific scope.

### Task S3: audit sources and list missing human facts

Dependencies: S1 and S2.
Outputs: tasks/submission_readiness_20261003/AUDIT.md and INPUTS_NEEDED.md.
Examine numerical source leaves, citation meaning, caption-to-figure agreement and figure provenance.
Use existing primary source material first. Retrieve primary citation documents only within the shared documentation budget.
Report PASS, unresolved or failed per item. Existing checker PASS does not prove citation entailment or figure content.
Do not silently relabel a figure/path check as a full scientific-content audit. Record omissions and reasons if a legacy figure is unsupported.
No new learning, predictions or analyses are authorized.

INPUTS_NEEDED.md must ask only for facts not already available: venue confirmation, authors/affiliations/contributions,
funding, conflicts, ethics/data-use confirmation, publication-budget constraints and any needed release URLs.
Name the owner and exact completion condition per missing fact. Complete all independent work before stopping for these inputs.
Never assume none for funding/conflicts, invent an ethics approval, select authors or fabricate researcher approval.

Acceptance: audit distinguishes automated and manual checks, and every unresolved scientific/source issue or human fact is explicit.

### Task S4: final verification and handoff

Dependencies: S1–S3.
Output: tasks/submission_readiness_20261003/READINESS.md.
Run from the repository root:

```sh
.venv-p22/bin/python paper/check_paper.py --json
.venv-p22/bin/python paper/check_paper.py --draft paper/submission_20261003/draft.md --refs paper/refs_frozen.bib --claims paper/claims.csv --json
.venv-p22/bin/python gnhf/verify_ladder.py --run reports/generated/nn_20260923/ladder_v3
```

Do not add --write. Record command exits and verdicts. Do not modify a checker or source ledger merely to obtain PASS.
Record final artifact hashes, focused diffs, request/byte totals, source/figure audit coverage and unresolved input owners.
Confirm that accepted manuscripts, claims, original MOM and scientific gates remain unchanged.
Update only this stage's task list. Update status.md/docs/INDEX.md once at the final handoff or a verified blocker.
Do not edit past closeouts or their hash registers to make them describe this new stage.

## Definition of Done and stop conditions

All of the following are required for READY_FOR_RESEARCHER_REVIEW:
- The venue comparison and provisional recommendation are backed by official sources or documented unknowns.
- The venue-specific copy exists with correct references/image paths and unchanged accepted numerical results.
- All required automated checks pass. Manual source/figure audit coverage and its actual limits are recorded.
- No unsupported scientific/source claim remains in the provisional draft. Remaining human/venue/export items are named explicitly.
- INPUTS_NEEDED.md identifies owners and completion conditions without invented facts.
- READINESS.md links every output, records current hashes/checks/budget and states submission is pending researcher inputs.
- Task marks agree with the evidence. No completed task is repeated merely because another iteration is available.

If a required scientific/source check fails, access/budget prevents the audit, or an essential tool is unavailable,
write READINESS.md with status BLOCKED, direct evidence, the exact smallest unblock and unfinished tasks left unchecked. Stop.
A missing funding/author/venue confirmation alone permits READY_FOR_RESEARCHER_REVIEW if all independent work and scientific checks are complete.
Do not mark submission-ready, contact anyone, submit, publish, push or acquire research data.

## Preserved scientific labels and scope

Primary R3_ca minus R3_tc remains B_NULL. M9 stays NOT_AUTHORIZED. M10 stays diagnostic-only.
S7/S9/S10 stay INVALID, S8 stays NO FIT, E5 stays NO_GO, Q2 stays ENDPOINT_UNRESOLVED and power stays POWER_UNESTABLISHED.
No claim of equivalence, proven absence of signal, CA superiority, validated cell-state biology or new professor endorsement.
No research fits, dataset downloads, external scoring, new model search, worktrees or automated research continuation.
GNHF handles commits. Do not create git commits yourself inside an iteration. Do not push.

At a valid terminal handoff, set should_fully_stop=true in the GNHF output. End after READY_FOR_RESEARCHER_REVIEW or an evidence-backed BLOCKED handoff.
