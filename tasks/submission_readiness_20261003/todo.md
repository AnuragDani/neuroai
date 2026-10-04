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
- [x] Dependencies: S1 and S2 complete
- [x] Numerical source leaves, caption-to-figure agreement and figure provenance checked
- [ ] Citation meaning verified against primary-source text (C3; budget blocker)
- [x] Report PASS / unresolved / failed per item; distinguish automated vs manual checks
- [x] INPUTS_NEEDED lists only missing human facts with owner and exact completion condition

**Outputs:** [AUDIT.md](AUDIT.md), [INPUTS_NEEDED.md](INPUTS_NEEDED.md) — automated checker PASS; 14/14 numerical leaf checks PASS; figure path+caption PASS for fig6/fig7; citation PDF entailment unresolved (budget exhausted); human facts H1–H12 owner=Researcher. Accepted draft/short/claims hashes unchanged.

**Acceptance:** audit distinguishes automated and manual checks; every unresolved issue is explicit. Reporting is complete; required citation audit C3 is unfinished. **BLOCKED** under the stage stop rule.

### S4 — Final verification and handoff
- [ ] Dependencies: S1–S3 complete (S3 citation support unfinished)
- [x] Run required checkers from repo root (no `--write`); record exits and verdicts
- [x] Record final artifact hashes, focused diffs, request/byte totals, audit coverage, unresolved input owners
- [x] Confirm accepted manuscripts, claims, MOM and scientific gates unchanged
- [x] Update this task list; update `status.md` / `docs/INDEX.md` once at handoff
- [x] Status `READY_FOR_RESEARCHER_REVIEW` or evidence-backed `BLOCKED`

**Output:** [READINESS.md](READINESS.md) — corrected status **`BLOCKED`**: required source audit C3 unfinished. Original GNHF completion is preserved at commit `7d1da80e1c043b2f53711165727eef5333455fe6`. Commands: default `check_paper.py` exit 0 / ok; venue-copy `check_paper.py` exit 0 / ok; `verify_ladder.py` ladder_v3 exit 0 / PASS (`advantage=false`). Accepted draft/short/claims + prior CLOSEOUT registers rematch live. Network budget unchanged (≈25/24 requests; ≈0.56 MiB; S4 added 0 fetches). Readiness requires C3 first; submission also requires researcher H1–H12.

**Acceptance:** READINESS links every output, records checks/budget/hashes, and states submission pending researcher inputs (or BLOCKED with smallest unblock). **MET.**

## Preserved labels (do not rewrite)

Primary R3_ca − R3_tc **B_NULL**; M9 **NOT_AUTHORIZED**; M10 diagnostic-only; S7/S9/S10 **INVALID**; S8 **NO FIT**; E5 **NO_GO**; Q2 **ENDPOINT_UNRESOLVED**; power **POWER_UNESTABLISHED**.
