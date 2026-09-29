# P22 parallel finish — 2026-09-28

User authorized planning and starting GNHF with Cursor in parallel. This run supersedes the old finish runbook for its bounded scope only. No new experiments, protocol changes, acquisitions, packages, gate weakening, email, publication or push. No subagents. Preserve original MOM and September 27 packet.

Baseline: integration HEAD 9a1e777, canonical ladder_v3 B_NULL; v6 gate scientific/paper/merge checks pass but full tests fail. Exact failing tests are unknown. Do not reuse the old ladder_v2 headline. Scientific null means advantage not demonstrated, not equivalence. Study remains STUDY_PARTIAL without external validation. Planted non-detection does not by itself isolate donor power from benchmark/model limitations.

## Parallel ownership

| Lane | Branch / checkout | Writes | Does not write |
|---|---|---|---|
| Engineering | codex/p22-finish-engineering-20260928 / .worktrees/finish-engineering-20260928 | Minimum source/test repair; own engineering handoff; final integrated status/index/X7 reconciliation after writing handoff | Paper, results prose, professor notes or vault while writing lane runs; gnhf gates |
| Writing | codex/p22-finish-writing-20260928 / .worktrees/finish-writing-20260928 | paper/draft.md, claims.csv, self_review.md; results prose/header; v6 professor note; vault paper-nn, vault status/docs index; fresh dated professor packet and package indexes | Code, tests, gnhf, repository status.md/docs INDEX, tasks status/X7, experimental JSON/raw outputs |

Both read repository AGENTS.md, status.md, docs/INDEX.md and live evidence first. Meeting notes are professor sources; execution handoffs are worker sources. Do not edit main checkout or another worktree. Use main .venv-p22/bin/python, PYTHONPATH=src:scripts, PYTHONDONTWRITEBYTECODE=1. Raw saved runs linked into each checkout are read-only. Save temporary summaries/check output in lane-local scratch or the run log folder; never write through raw symlinks. GNHF rollback affects only isolated checkout. External vault writes are authorized for writing lane only; record hashes and preserve originals on failure.

## Tasks and acceptance

- [x] E1: Capture full pytest output to persistent engineering-pytest.log. Identify first real failure with pytest -q -x; distinguish environment restrictions from code defects. Trace all callers before minimal source repair. No blanket skips, deleting tests, changing acceptance thresholds, or fitting models. Acceptance: named failure/root cause, focused check passes, then full suite passes; log exact count. If no safe repair after two focused attempts, write precise blocker with evidence.
- [x] W1: Audit title/abstract/discussion/professor note against saved JSON; remove unsupported absence/equivalence/transportability claims, retain chr21-forced pooled positive as secondary and distinguish mean-fold null. Reconcile DRAFT_V3 header and limitations, PC N/A, N21 secondary. Acceptance: paper/check_paper.py and gnhf/check_evidence.py verified-CI check pass; every changed numeric claim traced to source; no JSON changed.
- [x] W2: Sync revised manuscript deliverables to vault and correct stale vault summaries with provenance. Prepare fresh UNSENT dated packet from August 16 last-sent baseline, not September 27 prepared packet. Read vault UPDATE_GUIDE.md and external_shared/STATUS.md, last sent report and professor MOM first. Follow packet guide: two-page Markdown, email draft with placeholders, source/executed notebook, HTML, evidence, guide snapshot, hashes, ZIP and link checks. Reuse existing notebook/build/export workflow; safe-mode display of saved records only, no model fits. Apply specified prose skills. Keep three studies separate; mark final engineering check pending while E1 runs. Acceptance: zero notebook execution errors, checked HTML/ZIP/links/hashes, no sent date changed. If guide cannot be completed safely, record missing deliverable instead of claiming packet complete.
- [x] W3: Commit only writing-owned tracked files; write writing handoff with checks, changed file list, vault output paths/hashes and blockers. AFTER commit, create writing-ready.json at shared log folder with committed SHA and branch, or writing-blocked.md if incomplete. Writing runner then stops; no later changes to committed files or packet.
- [x] E2 (depends E1 + W3): Read writing-ready.json and verify SHA equals writing branch HEAD; inspect diff ownership and clean working tree; merge writing branch into engineering branch (no force, no automatic ours/theirs). If conflicts, preserve state and report blocker. Run full suite only if merge changed relevant source/test inputs; run v6 gate on integrated checkout, keep complete log and explicit full-suite evidence. Current gate checks original main branch refs, so passing those lines does not prove new branches merged/pushed. Record new integration as local review branch, no push.
- [x] E3 (depends E2): Reconcile repository status/index and X7 stale conflict label with exact verified state; never say new work was pushed. If accepted, change packet's engineering-pending statement to verified outcome, rerun affected notebook/export/link/hash/ZIP checks using existing workflow and update vault status. Writing runner must be stopped before engineering edits these external packet files. If failed, retain provisional/failed gate notice. Final handoff: branch/SHA, exact gate/test results and logs, packet paths, remaining limits. Codex independently reviews before user treats finish as accepted.

## Checkpoints and stop rules

After E1 and W1: source repair and writing checks independently pass or precise blockers are preserved. After W3: immutable writing handoff; integration becomes sequential. Stop success only after E1-W3/E2-E3 checks pass, gates are truthful and packet stays unsent. On auth/quota/data blocker preserve branch and log; no destructive cleanup, retries of full scientific ladders, or endless waiting. Engineering waits at most 30 minutes for writing handoff using short bounded polls, then records resumable WAITING_WRITING rather than success. Final follow-up decision for researcher/Professor Fang: bounded internal paper versus reopening external validation; do not execute external validation.

## Logs and launch

Shared persistent folder: /Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_finish_20260928.
Sessions: p22finish-engineering-20260928 and p22finish-writing-20260928. Both use gnhf --agent cursor --model auto, max 30 iterations, max rate-limit wait 1h, current branch, no push. Existing uncommitted main status.md remains untouched.

## Definition of done and positive-result criteria — researcher continuation

This continuation closes the current internal study honestly and records the next research decision. It does not require or promise a positive result. GNHF/Cursor startup is manual only at the researcher's preference; Codex may finish these bounded documentation repairs/checks directly. No unattended runner restart.

### Current task definition of done

Reviewed scientific evidence and full-suite gate pass; manuscript/results/note/status agree; changed claims match saved JSON; vault deliverables match; safe-display notebook runs without errors; HTML/links/hash manifest/ZIP pass; independent review findings resolved. Final local branch and commit are recorded. Packet remains unsent and last sent stays August 16. Merge/push, professor sending, publication and external validation are separate milestones. A completed internal null is a valid completed task; broader study remains STUDY_PARTIAL.

### What counts as positive

Frozen primary A_ADVANTAGE requires R3_ca minus matched R3_tc donor balanced-accuracy estimate >= 0.07 AND 95% donor-bootstrap CI lower bound > 0, with all scientific validity gates PASS. This is the protocol's estimate-plus-CI rule; it does not require CI lower bound >= 0.07. Full method-paper framing further requires the decision tree's robustness (>=4/5 initialization seeds meet margin, otherwise A_FRAGILE) and valid CA_USES_PAIRING evidence, including sensitive pairing control. Independent external replication would strengthen transportability but has not occurred and is not part of the current frozen internal endpoint.

Current canonical estimate is 0.0267, verified CI [-0.0250,0.0768]: B_NULL, estimate 0.0433 below the practical margin and uncertainty includes zero. Chr21-forced pooled estimate 0.060, CI [0.011,0.113]: secondary D_SMALL_POSITIVE, not a replacement primary. These are numeric gaps, not completion percentages, tuning targets or predictions of future success. Dosage AUROC 1.0 is strong cohort discrimination, not an attention advantage or beyond-dosage mechanism claim.

### Closeout tasks

- [x] C1: Resolve review's results conclusion and stale engineering-pending wording in live results/professor note. Refresh the packet's current note copy with a labelled revision; preserve earlier note snapshot outside the share package. Acceptance: no stale pending statement in current docs, no equivalence claim, paper/CI checks PASS, no scientific JSON changed.
- [x] C2: Refresh affected packet hashes/ZIP and safe-display notebook/HTML; recheck links, 6 executed cells/zero errors, manifest, archive bytes and vault manuscript match. Acceptance: prepared/unsent remains truthful; last-sent baseline unchanged.
- [x] C3: Record independent review closure, final accepted gate evidence and local commit; update plan/task/status. Existing 1278-test PASS and E3 V6_GATE PASS can be reused if scientific code/test inputs unchanged; rerun prose/evidence checks affected by this revision. Acceptance: current finish task complete, no push or runner restart inferred.

### Next research path (planning only; outcome open)

1. Diagnose from saved controls whether the constructed interaction is learnable, whether both comparators learn it, and whether labels/representation/pooling hide a measurable contrast. Do not equate CA-versus-TC non-detection with failure to learn disease or low donor power alone. **Saved-evidence diagnosis recorded in [DIAGNOSIS.md](DIAGNOSIS.md) (2026-09-28).**
2. Choose one prospective hypothesis and estimand: an attention advantage over fair matched/simple baselines, or a biologically justified beyond-dosage question. Declare pairing intervention/positive-control sensitivity, donor-level uncertainty, confound checks, representation and practical margin before new real-label fits. Do not change the finished primary or search variants until something becomes significant. **Hypothesis, estimand, frozen comparison set and positive-result/stop criteria recorded in [HYPOTHESIS.md](HYPOTHESIS.md) (2026-09-28); method-advantage path selected; beyond-dosage deferred; feasibility/protocol still open.**
3. Before any proposed new run, produce a bounded protocol with donor/sample feasibility and power/precision design. Number of donors needed is not established by current planted grid. If no pairing-sensitive learnable control can be demonstrated, stop that method-advantage path and retain the internal null; if cohort/access are unavailable, preserve that blocker and complete the bounded paper.
4. Independent paired cohort evaluation is a separate prospective phase after scope and inputs are resolved. A convincing general method result would retain reproducible internal advantage, pairing-use evidence and independent replication; no such result is claimed now.

Research completion means executing the declared protocol and reporting its supported result, including null/negative/blocked. It never means running indefinitely until positive. No new experiments or external acquisition are authorized by this planning section.

## Accepted current-task closeout

E1: 1278 tests passed, no repair needed; earlier main-checkout failure not reproduced and its cause not established. E2/E3: saved integrated V6_GATE PASS logs. C1: canonical results and professor note corrected. C2: freshly executed safe-display notebook (6 cells/zero errors), HTML, 30 local links, 22 hashes and ZIP checked; vault manuscript matches; scientific JSON unchanged. C3: independent findings resolved with checked local handoff. Full suite not repeated for this prose-only closeout because source/tests/protocol/data are unchanged. See main reports/generated/nn_finish_20260928/CODEX_CLOSEOUT_CHECKS.json and CODEX_CLOSEOUT.md. Finish task COMPLETE; outcome B_NULL; study STUDY_PARTIAL. GNHF remains stopped; no merge into main, push or sending performed. Prospective research path above is planning only, not a completed positive-result study.
