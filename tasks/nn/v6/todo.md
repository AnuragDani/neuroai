# P22-NN v6 task list

Plan: `tasks/nn/v6/plan.md`. Status in this file (checkboxes); evidence path on DONE.

## Phase 1: Integrate

### T1: Merge v5 work into the integration branch
**Acceptance:** `codex/p22-nn-finish-base` is an ancestor of `gnhf/p22-nn-cellstate`; no conflicts left.
**Verification:** `git merge-base --is-ancestor codex/p22-nn-finish-base gnhf/p22-nn-cellstate`; `python3 gnhf/v5_gate.py` → `V5_GATE PASS` in the main checkout.
**Dependencies:** none. **Scope:** XS.
- [ ] T1

### T2: Push and open PR to main
**Acceptance:** `origin/gnhf/p22-nn-cellstate` equals local; PR open against `main` with results summary.
**Verification:** `git rev-list --count origin/gnhf/p22-nn-cellstate..HEAD` = 0; PR URL recorded here.
**Dependencies:** T1. **Scope:** XS.
- [ ] T2

### Checkpoint 1
- [ ] Gate PASS on integration branch; branch pushed

## Phase 2: Human review

### T3: Author review
**Acceptance:** author has read the professor update, draft and below-chance diagnosis; corrections listed.
**Verification:** corrections noted in `docs/nn_v2/v6/AUTHOR_REVIEW.md` (or "none").
**Dependencies:** T1. **Scope:** S.
- [ ] T3

### T4: Professor update decision
**Acceptance:** decision recorded: send now / after Phase 3.
**Dependencies:** T3. **Scope:** XS.
- [ ] T4

### Checkpoint 2
- [ ] Professor update approved by author

## Phase 3: Optional science extensions (each needs a named amendment BEFORE running)

### T5: chr21-forced representation sensitivity
**Description:** Default HVG keeps 31/538 chr21 genes. Rerun all arms with chr21 genes forced into the RNA view.
**Acceptance:** `configs/nn_protocol_v2_amendment_chr21forced.json` committed before the run; `ladder_v4_chr21forced` 450/450; `verify_ladder.py --run …` PASS; primary contrast reported as a sensitivity, primary endpoint unchanged.
**Dependencies:** T1. **Scope:** M (≈ 3–6 h CPU).
- [ ] T5

### T6: Per-fold primary contrast sensitivity
**Acceptance:** per-fold CA−TC contrast with donor-level uncertainty in `docs/nn_v2/v6/per_fold_contrast.json`; stated as prespecified sensitivity.
**Dependencies:** T1. **Scope:** S.
- [ ] T6

### T7: Detectability / power analysis
**Acceptance:** from planted runs, minimum detectable BA gain at 30 donors (80% of repeats CI excludes 0) in `docs/nn_v2/v6/detectability.json`; one paragraph for the paper.
**Dependencies:** T1. **Scope:** M.
- [ ] T7

### Checkpoint 3
- [ ] Extensions reported; results doc and paper updated; gate PASS

## Phase 4: Paper to submission

### T8: Venue and format
**Acceptance:** venue, page/word limits, template recorded in `paper/VENUE.md`.
**Dependencies:** T3. **Scope:** XS.
- [ ] T8

### T9: Revision pass
**Acceptance:** author + professor edits applied; `paper/check_paper.py` passes; figures regenerated; vault copy updated.
**Dependencies:** T4, T8 (and T5–T7 if run). **Scope:** M.
- [ ] T9

### T10: Preprint / submission
**Acceptance:** advisor approval recorded; submitted; link recorded here.
**Dependencies:** T9. **Scope:** S.
- [ ] T10

### Checkpoint 4
- [ ] Submitted

## Phase 5: Hygiene

### T11: Clean worktrees and branches
**Acceptance:** merged lane worktrees under `P22/.worktrees/` removed; `P22-gnhf-worktrees/p22-results-executio-debda8` kept until T10.
**Dependencies:** T2. **Scope:** XS.
- [ ] T11

### T12: Memory and vault summary
**Acceptance:** project memory and vault README reflect v5 verified results and this plan.
**Dependencies:** T1. **Scope:** XS.
- [ ] T12
