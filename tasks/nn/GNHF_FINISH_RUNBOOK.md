# P22 NN v2: manual GNHF finish runbook

Prepared 2026-09-27. Cursor does implementation. Codex reviews final evidence and fixes only defects left after review. The researcher starts GNHF; this file does not start a run.

## Operator preflight and command

Run from the dedicated clean checkout at `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-base` (branch `codex/p22-nn-finish-base`). Its base commit is `e61b329`; the main checkout has uncommitted documentation and must not be used with GNHF rollback. Raw fold files remain at `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v2` and are **not** copied into this checkout.

Before starting, confirm all four conditions. At 13:45 PDT on 2026-09-27, disk and checkout passed, Cursor CLI was signed in from the normal terminal environment, and the quota-stalled `p22agy4` session was stopped. Recheck if starting later:

1. `cursor-agent status` reports logged in. If not, run `cursor-agent login` yourself and check again.
2. `tmux has-session -t p22agy4` reports no session. If it exists, inspect its log and stop it yourself after preserving any finished lane work. Do not run two writers at once.
3. `df -Pk /Users/anuragdani/Github/niw-eb1a/P22` reports at least **11 GiB available** (11,534,336 KiB). Preserve experimental outputs; free space by reviewing files, not by blindly deleting runs.
4. `git -C /Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-base status --porcelain` is empty. Also check that the 450-fold run still has `folds_done=450`, `failures=[]`.

Then invoke GNHF yourself. This starts a detached tmux session; it writes a persistent log and does not need an open terminal:

```bash
tmux new-session -d -s p22gnhf "cd /Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-base && exec gnhf --agent cursor --model auto --current-branch --max-iterations 120 --max-rate-limit-wait 12h --prevent-sleep on --meteor-frequency 0 --stop-when 'Stop when the NN v2 ladder gate, downstream evidence, paper checker, final verification, and vault paper copy pass; or when a hard blocker is recorded with evidence and no independent safe task remains. Do not declare scientific completion from a task label alone.' < /Users/anuragdani/Github/niw-eb1a/P22/tasks/nn/GNHF_FINISH_RUNBOOK.md > /Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_gnhf_finish.log 2>&1"
```

No `--push`. GNHF commits to the dedicated branch. Read progress at `reports/generated/nn_gnhf_finish.log`; do not start a second session. Return with its final branch/path and log; Codex will independently review before treating the result as accepted. If quota stops the run, preserve the branch and resume the same GNHF run. Do not restart the 450-fold ladder by default.

## Agent instructions

Work only in the dedicated checkout. Read the live main-checkout `/Users/anuragdani/Github/niw-eb1a/P22/status.md` and `docs/INDEX.md` first; they are currently uncommitted and absent from this checkout. Recheck raw evidence, `tasks/nn/plan.md`, `tasks/nn/todo.md`, `tasks/nn/decision_tree.md` section G and each task's own IF/ELSE rule, `docs/nn_v2/PROTOCOL_FREEZE.md`, and professor MOM before scientific claims. Meeting notes and worker handoffs are different sources. The hard gate outranks N10's `DONE` label. Do not edit another worktree or the main checkout. Do not touch the prepared, unsent `external_shared/2026-09-27` professor packet; it concerns a separate paired analysis.

Use `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with `PYTHONPATH=src:scripts` and `PYTHONDONTWRITEBYTECODE=1`. Prior raw outputs are under the **main checkout's absolute path** above. Do not copy the 377 MB ladder run to this checkout. For new work, choose a new run directory and record source paths and hashes. Keep each iteration to one bounded task step; run its focused check and leave a clear run-log entry. Preserve completed output across quota limits. No new packages, frozen-protocol changes, gate weakening, hand-edited result JSON, or tuning toward a positive result. No subagents.

### S6: accept or reject the ladder

Current live run record says 450/450 folds complete, no failures. The saved `ladder_summary.json` is stale: contrast 0 and CI [0, 0]. Independent fold-file recomputation is about −0.0067, CI [−0.0528, 0.0348], 5 repeats × 30 donors, chr21 dosage AUROC about 0.998. These numbers are provisional until the saved summary and gate agree.

1. Check that all expected fold files, donor sets, arm names, parameter counts, input hashes and frozen protocol match. IF missing/corrupt/changed, diagnose the exact cause and rerun **only** affected folds under a documented amendment if scientifically allowed. ELSE reuse all 450 saved folds.
2. Rebuild summary and LADDER from fold files using `scripts/summarize_nn_v2.py --run /Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v2 --out docs/nn_v2`. Do not patch summary numbers by hand. A scratch run of this script on 2026-09-27 produced outcome `B_NULL` and made the independent verifier return `PASS`. The script and verifier use different seeded bootstrap implementations, so their CI endpoints can differ slightly; the verifier's stated tolerance, full donor coverage and interpretation must all pass.
3. Run `gnhf/verify_ladder.py --run /Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v2 --summary docs/nn_v2/ladder_summary.json --write`. IF verdict is `FAIL`, fix source cause and rerun; after two focused repair attempts, record exact blocker and stop scientific downstream claims. ELSE mark N10 accepted with gate path. Copy the main checkout's `status.md` snapshot into this branch and update this branch's copy for the accepted gate; leave main checkout untouched. Report null result without a complex-model superiority claim. Keep model-free chr21 dosage and the pooled-majority metric caveat visible.

### S7: finish downstream evidence

First inspect current `faith`, `export`, `geneact`, and `robust` worktree branches and their evidence. The main checklist may say TODO even when a lane has finished. For each output: IF its data hashes, fold/split identities, 5-repeat design and exact ladder source match, integrate the specific code/evidence into this branch and run its check. ELSE fix or rerun only that output. Do not cherry-pick stale status or unrelated files. N11/N12 already have candidate results in `.worktrees/robust`; verify before reuse.

| Work | IF / ELSE action | Acceptance |
|---|---|---|
| N11 chr21 exclusion | IF all no-chr21 BA ≤0.55, `DOSAGE_DOMINATED`; ELSE IF any ≥0.60, `BEYOND_DOSAGE`; ELSE `PARTIAL_DOSAGE`. | Correct cells/splits, evidence JSON, interpretation limited to this cohort. |
| N12 seed sensitivity | IF outcome A, require ≥4/5 init seeds above margin or relabel `A_FRAGILE`; ELSE report spread. IF sampling spread >0.07, `SAMPLING_SENSITIVE`. | Seeds, donor sets and spread recorded. |
| N13/N14 faithfulness and nuisance | IF identity intervention changes output, fix harness. IF pairing control is insensitive, do not claim pairing use. IF probe drop is too small, reject adversary rung per decision tree. | Held-out interventions, CIs, control sensitivity and probe evidence. |
| N15 cell scores | IF any cell appears other than five times per arm, fix export; do not average partial repeats. | Complete out-of-fold export with traceable model/fold IDs. |
| N21 gene-aligned optional | IF available output passes source/hash, memory and protocol checks, retain as secondary. IF 1,500 tokens exceed memory, use the decision-tree 500-gene amendment. ELSE `BLOCKED` with reason. | Never claim this as independent external validation. |

On provider quota: save work and stop at bounded wait; resume later on same branch. On data or computation failure: use decision tree's specific fallback, then mark `BLOCKED:<reason>:<evidence>` if no valid path remains. A blocked optional task cannot erase successful mandatory evidence. A blocked N13 limits claims about attention; a blocked N15 blocks N16 and must be visible in the paper.

### S8: results and interpretation

N16: IF eligible cell types exist, run donor-level spectrum and Holm correction; record `SPECTRUM_LOCALIZED`, `SPECTRUM_NULL`, or `CONFOUND_SENSITIVE` as specified. ELSE `NOT_ESTIMABLE` with support counts. N17: IF N13 lacks valid intervention evidence, label every attention readout `NOT_SHOWN_USED`. N22: write results and an **unsent** professor note from verified JSON; list upstream blockers and their claim consequences in first ten lines. N23: run full tests and `gnhf/check_evidence.py` against results. IF a mandatory gate fails, repair source or mark hard blocker; do not proceed as though passed.

### S9: draft and final checks

Apply N24 framing truth table in order; for current provisional null, F1 is unavailable. Use F2 only if planted benchmark actually supports it; otherwise test F3 then F4. N25 figures from evidence, omit missing-source figures. Finish N27–N32 with every Results/Abstract number traced through `paper/claims.csv`, required limitations, correct citations, and an adversarial self-review. Replace stale "ladder never ran" text. Run `paper/check_paper.py`, full tests, and verified-CI checks; IF any fail, repair before N33/N34. Keep accepted result separate from earlier August same-cap and September paired studies.

After gates pass, N33 may copy **only** the paper deliverables specified in `tasks/nn/decision_tree.md` to the vault's `paper-nn/`. Preserve MOM and the existing unsent professor packet. N34 requires final checks and `DRAFT_V1_COMPLETE` or an explicit `DRAFT_V1_PARTIAL:<missing>` label. Update this branch's `status.md` for accepted gates or material blockers; update vault `status.md` only after the final paper copy. Leave the dirty main checkout untouched. Do not mark a professor update as sent and do not send email.

### Stop and handoff

Stop with success only when S6 gate is `PASS`, S8 and S9 evidence/checks pass, statuses N10–N34 are truthful, the draft and claims ledger match verified data, and vault copy is checked. A scientific null is a valid completed result. IF a hard gate remains blocked after bounded repair, stop with a precise blocker, preserved branch/output, and next action; never report 100% completion. Final message: branch, commit, accepted/blocked tasks, test/gate commands and outcomes, evidence paths, remaining limits, and task-based professor-guidance/paper progress estimates. Codex performs independent final review and any required fix after the run.
