# Next action checklist

- [x] Draft proposal from current evidence.
- [x] Obtain Cursor critique through GNHF.
- [x] Obtain independent Claude critique through GNHF after restored login.
- [x] Resolve material objections and narrow the plan.
- [x] Final dual review: Cursor PASS, Claude PASS_WITH_CHANGES, no blockers.
- [x] Resolve Claude RC1–RC4 with exact source checks.

## Execution checklist

Root task list: `../todo.md`, section **Next action execution — 2026-10-03**. Keep these task IDs consistent with the root list.

### Task 1 — evidence boundary

- [x] `EVIDENCE_BOUNDARY.md` exists with live sources, exact leaves and hashes.
- [x] Primary R3 contrast, absolute metrics and scientific labels agree with the sources.
- [x] Professor instructions and worker gates are distinguished. Original records remain unchanged.

Evidence: [EVIDENCE_BOUNDARY.md](EVIDENCE_BOUNDARY.md). Live replay PASS (`gnhf/verify_ladder.py --run reports/generated/nn_20260923/ladder_v3`, no `--write`).

### Checkpoint A

- [x] Saved-fold replay reports PASS without learning or source writes.
- [x] Source disagreements are resolved or block the next tasks.

Disposition: **PASS**. No label/value disagreement with live gate leaves. Tasks 2 and 3 authorized from the pinned boundary.

### Task 2 — bounded paper

- [x] Short/full papers preserve accepted claims and exclusions.
- [x] `PAPER_COMPLETION.md` records the paper checker and manual claim/citation/figure checks.
- [x] Open declaration and venue items name an owner and completion condition. No submission-ready claim is made.

Evidence: [PAPER_COMPLETION.md](PAPER_COMPLETION.md); manuscripts `paper/draft.md`, `paper/short_paper.md` (venue-neutral Declarations; revision `PREPARATION_2026-10-03`). Post-edit `check_paper.py --json` PASS; saved-fold replay PASS.

### Task 3 — offline desk decision

- [x] `EXTERNAL_DESK_DECISION.md` exists and reports `NO_GO_NOW`.
- [x] It cites existing payload/access sources and the unresolved specimen, QC and exact-input contracts.
- [x] It makes no new acquisition recommendation and records no network activity or counter changes.

Evidence: [EXTERNAL_DESK_DECISION.md](EXTERNAL_DESK_DECISION.md). Disposition `NO_GO_NOW`; ATAC counts 1,540,753,269 bytes exceed historical 256 MiB ceiling; Q5 blockers inherited; zero network/fits/scores.

### Checkpoint B

- [x] Task 2 and Task 3 outputs satisfy their criteria.
- [x] No unresolved manuscript claim/source discrepancy remains.

Disposition: **PASS**. Paper checker + replay PASS after manuscript edits; desk remains `NO_GO_NOW`; open declaration/venue items tracked with owner and completion conditions (submission pending).

### Task 4 — closeout and Definition of Done

- [ ] `CLOSEOUT.md` links every required output and current artifact hash.
- [ ] Final paper checker and saved-fold replay report PASS. Manual checks and open items are recorded.
- [ ] Every Definition of Done item in `PLAN.md` has completion evidence.
- [ ] Root/detailed task marks and `status.md` agree with the closeout.
- [ ] Record preparation complete; submission pending where required. Stop without automatic research continuation.

These are planned completion checks, not claims that execution occurred.
