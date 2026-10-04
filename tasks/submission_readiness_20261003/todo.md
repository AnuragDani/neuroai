# Submission readiness — 2026-10-03

Bounded submission-preparation stage. Researcher-authorized; not waiting for Professor Fang.
Do not rerun `tasks/next_action_20261003/`. GNHF handles commits. No fits, push, contact or submission.

Shared network budget for this stage (new counter): **24 external requests / 32 MiB** documentation only.
Record usage in [VENUES.md](VENUES.md) / [AUDIT.md](AUDIT.md).

## Tasks

### S1 — Compare venues
- [x] Sourced comparison of 3–5 plausible venues from official publisher pages
- [x] Provisional recommendation with evidence for a bounded null benchmark (not a proven superior method)
- [x] Costs/limits current or explicitly unresolved; unknowns marked
- [x] URL, access date, exact requirement and uncertainty for each material recommendation

**Output:** [VENUES.md](VENUES.md) — provisional target **BMC Research Notes** (Research note); alternate BMC Bioinformatics; OUP/PLOS APC dollar amounts partly unresolved after access/parsing limits. Network budget exhausted (≈25/24 requests; ≈0.56 MiB docs); no further external fetches this stage.

**Acceptance:** sourced comparison exists; recommendation is provisional; costs/limits are current or explicitly unresolved. **MET.**

### S2 — Adapt a copy of the manuscript
- [x] Dependency: S1 complete
- [x] Copy accepted full draft to `paper/submission_20261003/draft.md` (do not alter accepted `paper/draft.md`, `paper/short_paper.md`, `paper/claims.csv`)
- [x] Adapt sections/refs/figure paths to provisional venue rules; keep accepted numerical results and frozen citation keys
- [x] Expand references from `refs_frozen.bib` with verified metadata; state remaining export requirement if venue format unsupported

**Output:** [paper/submission_20261003/draft.md](../../paper/submission_20261003/draft.md) — provisional BMC Research Notes Research note; Abstract Objective/Results; Intro+main+Limitations ≈850 words (≤2000); 1 table + 2 figures (≤3); paths `../figures/…`; Markdown retained with Word/portal export remaining. Checker on this draft: ok=true, failures=0. Accepted draft/short/claims SHA-256 unchanged vs CLOSEOUT.

**Acceptance:** draft is clearly provisional, complies with known venue rules, preserves original scientific scope. **MET.**

### S3 — Audit sources and list missing human facts
- [ ] Dependencies: S1 and S2 complete
- [ ] Numerical source leaves, citation meaning, caption-to-figure agreement, figure provenance audited
- [ ] Report PASS / unresolved / failed per item; distinguish automated vs manual checks
- [ ] INPUTS_NEEDED lists only missing human facts with owner and exact completion condition

**Outputs:** [AUDIT.md](AUDIT.md), [INPUTS_NEEDED.md](INPUTS_NEEDED.md)

**Acceptance:** audit distinguishes automated and manual checks; every unresolved scientific/source issue or human fact is explicit.

### S4 — Final verification and handoff
- [ ] Dependencies: S1–S3 complete
- [ ] Run required checkers from repo root (no `--write`); record exits and verdicts
- [ ] Record final artifact hashes, focused diffs, request/byte totals, audit coverage, unresolved input owners
- [ ] Confirm accepted manuscripts, claims, MOM and scientific gates unchanged
- [ ] Update this task list; update `status.md` / `docs/INDEX.md` once at handoff
- [ ] Status `READY_FOR_RESEARCHER_REVIEW` or evidence-backed `BLOCKED`

**Output:** [READINESS.md](READINESS.md)

**Acceptance:** READINESS links every output, records checks/budget/hashes, and states submission pending researcher inputs (or BLOCKED with smallest unblock).

## Preserved labels (do not rewrite)

Primary R3_ca − R3_tc **B_NULL**; M9 **NOT_AUTHORIZED**; M10 diagnostic-only; S7/S9/S10 **INVALID**; S8 **NO FIT**; E5 **NO_GO**; Q2 **ENDPOINT_UNRESOLVED**; power **POWER_UNESTABLISHED**.
