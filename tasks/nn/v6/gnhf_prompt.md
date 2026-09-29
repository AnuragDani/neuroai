# P22-NN v6 — sensitivity extensions, results and paper revision (GNHF prompt, Cursor auto)

2026-09-28. Branch `codex/p22-nn-finish-base`, worktree
`/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-base`. Execute code. **Completion =
`python3 gnhf/v6_gate.py` prints `V6_GATE PASS`.** Context: `tasks/nn/v6/plan.md` (verified state).

## 0. Fixed facts (do not change)

- Canonical ladder `reports/generated/nn_20260923/ladder_v3` (verified). Primary R3_ca − R3_tc donor
  BA +0.027, 95% CI [−0.025, +0.077] → `B_NULL`. It stays the PRIMARY result whatever v6 finds.
- Per-fold AUROC R3_ca 0.656, R3_tc 0.658, logreg_rna 0.534; chr21_dosage 1.0; default HVG keeps
  31/538 chr21 genes; forced-chr21 positive control AUROC 0.924.
- External validation is DEFERRED (T13). Do not access external data.

## 1. Rules

1. `tasks/nn/plan.md` §0–§4, §7 rules apply. Null results are valid; never tune toward a win.
2. Never edit `gnhf/`, `configs/nn_protocol_v2_2026-09-23.json`, `docs/nn_v2/chr21_sanity.json`,
   `docs/nn_v2/ladder_verification.json`, `docs/nn_v2/ladder_summary.json`,
   `docs/nn_v2/v5/CANONICAL_LADDER.txt`, or anything in `ladder`, `ladder_v2`, `ladder_v3` run dirs.
3. Never run `gnhf/verify_ladder.py` with `--write` (it would overwrite the canonical verification).
4. Status: one line in `tasks/nn/status/<ID>`; log one line per iteration in `tasks/nn/lanes/v6.md`.
5. Python `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python`, `PYTHONPATH=src:scripts`,
   `PYTHONDONTWRITEBYTECODE=1`. ≤ 14 worker processes, 1 torch thread each.
6. Runs > 10 min: `nohup … > <log> 2>&1 &`, status `RUNNING:<pid>:<log>`, end the iteration; check
   next iteration. Never start a duplicate (`pgrep -fl run_nn_v2`).
7. One coherent step per iteration; run the task's check before DONE; GNHF commits. New code gets
   `tests/test_nn_v6_*.py`. No new packages, no network, no messages. Merges and pushes ONLY in X7, exactly as written there.
8. Cite only `paper/refs_frozen.bib`; every number in prose from a JSON under `docs/nn_v2/`.

## 2. Tasks (IF/ELSE branches are mandatory)

### X1 — chr21-forced representation: pre-register, then run
1. BEFORE any run, write `configs/nn_protocol_v2_amendment_chr21forced.json`: time (UTC), reason
   ("default HVG keeps 31/538 chr21 genes; test whether forcing all chr21 genes changes the
   cross-attention contrast"), changed field `n_hvg` / feature rule (HVG ∪ all chr21 genes), and
   the statement that the primary endpoint is unchanged and this is a sensitivity. Commit it.
2. Add a runner flag (for example `--force-chr21`) reusing the V2 positive-control feature logic;
   test it in `tests/test_nn_v6_chr21forced.py` (feature set contains every chr21 gene; train-only fit).
3. Launch the full 18-arm, 5×5 ladder into `reports/generated/nn_20260923/ladder_v4_chr21forced`
   in the background.
- IF the run dies → rerun with `--resume` into the same directory (never delete finished folds).
- IF projected time > 12 h → amendment `cap512` for this sensitivity only, recorded before rerun.
**Check:** 450 fold files exist.

### X2 — Verify and summarize the chr21-forced run
Run `scripts/summarize_nn_v2.py --run reports/generated/nn_20260923/ladder_v4_chr21forced --out docs/nn_v2/v6`
so the summary lands at `docs/nn_v2/v6/ladder_v4_summary.json` (rename if the script writes
`ladder_summary.json` there). Then run
`python3 gnhf/verify_ladder.py --run reports/generated/nn_20260923/ladder_v4_chr21forced --summary docs/nn_v2/v6/ladder_v4_summary.json`.
- IF it fails only on parameter counts → check the amendment names the width field (`n_hvg`); fix
  the amendment text, never the verifier.
- IF it fails on summary agreement → fix the summarizer, rerun X2.
- ELSE IF it fails on chr21 AUROC or coverage → pipeline problem: diagnose, fix with a test, rerun X1.
Write `docs/nn_v2/v6/CHR21_FORCED.md` (≤ 40 lines): contrast, per-fold AUROC per arm vs ladder_v3,
reading. Label: `CHR21FORCED_B_NULL`, `CHR21FORCED_A_ADVANTAGE`, `CHR21FORCED_C_DISADVANTAGE`
(same rules as decision tree N10).

### X3 — Per-fold primary contrast (prespecified sensitivity)
Script `scripts/nn_v6_per_fold_contrast.py` (+ test): for each of the 25 folds, R3_ca − R3_tc donor
AUROC and BA; mean over folds; 95% CI by donor-cluster bootstrap over folds within repeats
(1,000 draws, seed 22). Write `docs/nn_v2/v6/per_fold_contrast.json` (`estimate`, `ci`, `per_fold`,
`metric`) for the canonical ladder_v3 (and also for ladder_v4_chr21forced if X2 is DONE).

### X4 — Detectability at 30 donors
Script `scripts/nn_v6_detectability.py` (+ test). From the planted-benchmark machinery, for effect
sizes δ ∈ {0.1, 0.25, 0.5, 0.75, 1.0} of an interaction signal (S4-type), run CA vs TC on the same
30-donor, 5×5 design (reuse existing planted code; ≤ 3 repeats if time > 6 h, recorded). Report per δ
the fraction of repeats whose CA−TC CI excludes 0 and the mean contrast; `min_detectable_delta` =
smallest δ with ≥ 80% detection, or `null` with the statement "not detectable up to δ = 1.0".
Write `docs/nn_v2/v6/detectability.json` and a ≤ 30-line reading `docs/nn_v2/v6/DETECTABILITY.md`.

### X5 — Results document and professor update
Add sections "chr21-forced sensitivity" (the phrase `chr21-forced` must appear), "Per-fold primary
contrast" and "Detectability" to `docs/nn_v2/NN_V2_RESULTS_2026-09-23.md`. Write
`docs/nn_v2/v6/PROFESSOR_UPDATE_v6.md` (≤ 500 words + the D1–D13 table carried from v5, updated):
plain-language result first; say external validation is deferred. Unsent.

### X6 — Paper revision to DRAFT_V3
Update `paper/draft.md`: Methods (chr21-forced sensitivity, per-fold contrast, detectability
design), Results (numbers from `docs/nn_v2/v6/*.json`), Limitations (detectability limit, external
validation deferred), Abstract. The words `chr21-forced` and `detectability` must appear. Header
label → `DRAFT_V3_COMPLETE`. Update `paper/claims.csv`, add a detectability figure via
`paper/make_figures.py`, update `paper/self_review.md`. Run `paper/check_paper.py` until it passes.
Copy draft, figures, claims, self-review to
`/Users/anuragdani/Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/paper-nn/` (overwrite
those files only).

### X7 — Integrate and push (T1/T2; author-authorized 2026-09-28)
Only after `python3 gnhf/v6_gate.py` passes every line except the X7 line:
1. Main checkout `/Users/anuragdani/Github/niw-eb1a/P22` must be on `gnhf/p22-nn-cellstate` with a
   clean `git status --porcelain`. IF not clean → set X7 `BLOCKED:main checkout dirty:<git status>`; stop.
2. `git -C /Users/anuragdani/Github/niw-eb1a/P22 merge --no-ff --no-edit codex/p22-nn-finish-base`.
   IF conflicts → `git merge --abort`, set X7 BLOCKED with the conflicted files; stop (never force).
3. In the main checkout run `python3 gnhf/v6_gate.py`; IF it fails → do NOT push; set X7 BLOCKED with output.
4. `git -C /Users/anuragdani/Github/niw-eb1a/P22 push origin gnhf/p22-nn-cellstate` (no `--force`).
   Also `git -C /Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-base push origin codex/p22-nn-finish-base`.
5. X7 DONE with both remote SHAs. Never push to `main`; never open or merge a PR.

## 3. Final verification

After X6 is DONE (and again after X7), every iteration: run `python3 gnhf/v6_gate.py`. IF `V6_GATE PASS` → stop
(`should_fully_stop=true`). ELSE fix the first FAIL line (never by editing `gnhf/` or protected
files). After 3 failed iterations on one line, set the owning task BLOCKED with evidence; science
checks (verification, paper checker, tests) must still pass for completion.
