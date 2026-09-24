# P22-NN decision tree (IF / ELSE rules for an unattended run)

Companion to `tasks/nn/plan.md` and `tasks/nn/todo.md`. Before starting any task, read
section `G` once per iteration and that task's section here:
`sed -n '/^## N7:/,/^## N8:/p' tasks/nn/decision_tree.md`.
Rules here override anything in `todo.md` when they conflict. They never override plan §0
assumptions A1–A16 or plan §7 honesty/leakage rules.

Notation: `→` = do this. `ELSE` applies when the preceding IF is false. "Record" means
write one line in the todo Run log with evidence path. "Amendment" means a new file
`configs/nn_amendment_<n>_<slug>.json` with UTC time, reason, and the exact changed
field, committed **before** the run it affects.

---

## G: Global rules (every iteration)

G1 Iteration start
- IF `git status --porcelain` is non-empty → these are your own leftovers from a crashed
  iteration. IF they belong to the task marked `RUNNING` or the first TODO task → run
  that task's focused tests. IF tests pass → continue the task from there. ELSE fix
  (≤ 2 attempts) → IF still failing → `git checkout -- <tracked files>` and delete only
  the untracked files listed in that task's "Files" list; restart the task cleanly.
- IF a background run is recorded as `RUNNING:<pid>` → `ps -p <pid>`.
  IF alive → do an independent runnable task this iteration (or, if none, check
  `tail -5 run.log` and end the iteration with success=true, summary "waiting on <task>").
  ELSE IF output files complete → mark the task's run step done and continue.
  ELSE (dead, incomplete) → rerun once with `--resume`; IF it dies again → BLOCKED:crash.

G2 Task choice
- Take the first TODO task whose dependencies are all DONE / BLOCKED / NOT_NEEDED.
- IF a dependency is BLOCKED → run the task anyway if the task's section below gives a
  fallback; ELSE mark `BLOCKED:upstream <id>`.
- IF the next task is M-sized → split its work across iterations: per iteration do ONE of
  (a) write code + unit tests, (b) run the experiment, (c) summarize + evidence JSON.
  Record which sub-step finished in the Run log so the next iteration resumes there.

G3 Step budget (100 tool steps per iteration)
- IF you have used ~70 steps → stop editing, run the focused tests, record the sub-step
  reached, return success=true with should_fully_stop=false. Never end an iteration
  mid-file-write.

G4 Retry budget per task
- IF a task has consumed 3 iterations without DONE → reduce scope to its acceptance list
  only (drop optional extras) and record it.
- IF 5 iterations → mark `BLOCKED:iteration_budget:<what is missing>`, move on.

G5 Test failures
- IF focused tests fail → fix (≤ 2 attempts per failure). IF a pre-existing, unrelated
  test fails → record it, do not fix it, continue. IF your own test still fails after 2
  attempts → BLOCKED with the failing test name.

G6 Resources
- IF free disk < 11 GiB → do not start runs that write > 100 MB and skip N20.
  IF < 10 GiB → start no runs at all; do code/writing tasks only; record.
- IF a run's RSS > 32 GB → rerun with half the worker processes; IF still > 32 GB →
  apply cap 512 amendment.
- IF a single fit takes > 10 min → reduce `max_epochs` is NOT allowed; instead use
  `cell_cap` 512 amendment for all arms equally.

G7 Provider / tooling errors
- IF OpenRouter reports credit/auth/key-limit errors → save work, return success=false,
  should_fully_stop=true. Never change keys or limits.
- IF a Python package is missing → do not install it. Use NumPy/SciPy/sklearn/matplotlib
  equivalents. IF impossible → BLOCKED:package.

G8 Result honesty
- IF a result looks "too good" (donor BA ≥ 0.95 on real DS, or planted S0 ≥ 0.7) →
  assume leakage first: run the leak check (shuffle donor labels across donors, rerun one
  fold). IF shuffled BA stays high → leakage bug; fix before anything else.
- IF a result contradicts the settled facts (plan §2) → re-check inputs/hashes before
  reporting; report both, never overwrite historical evidence.

G9 Scope
- IF you think a new experiment would help → do NOT run it. Add one line to
  `docs/nn_v2/FUTURE_WORK.md` instead.

---

## N3:
- IF S5 per-donor mean invariance fails by > 1e-5 → compute re-centering in float64, cast
  back to float32 after. ELSE continue.
- IF hash-based fake labels are not balanced within a DS group (odd count) → allow a
  difference of 1 donor; record exact table.

## N4:
- IF S0 (null) mean donor BA for any model outside [0.35, 0.65] → G8 leak check.
  IF leak found → fix, rerun N4. ELSE record "S0 variance at 30 donors" and continue.
- IF S1 at δ=1.0: all models ≥ 0.9 → sane. ELSE IF only neural models < 0.9 → amendment
  `max_epochs=60` **for planted runs only**, rerun S1. IF still < 0.9 → record
  `NEURAL_UNDERFIT` (feeds paper Limitations) and continue. ELSE IF linear also < 0.9 →
  fold-prep bug; debug (≤ 2 iterations) → IF unresolved BLOCKED and Phase 3 still runs
  flagged.
- IF S5 at δ=1.0: every fusion model within 0.05 of chance → run S5 once more at
  δ=2.0 (amendment) to find a detection threshold. Record result either way.
- Classify each scenario: `CA_FAVOURED` (CA − best non-attention model ≥ 0.07 in mean BA),
  `LINEAR_SUFFICIENT` (logreg within 0.03 of best), `MLP_FAVOURED`, `NONE_DETECT`.
  Write the classification into `docs/nn_v2/planted_benchmark.json` (`regime_labels`).

## N5:
- IF synthetic MIL AUROC < 0.9 → try lr 3e-4 once; IF still < 0.9 → try bag size 32.
  IF still → BLOCKED; the ladder becomes R0 → R2' (cell-level loss + adversary) → R3'
  (+NCE); rename arms with `'` and record in N9.
- IF training is non-deterministic across two identical CPU runs → set
  `torch.use_deterministic_algorithms(True)` and single-thread the test; record.

## N6:
- IF synthetic probe drop < 10 points → try λ_adv 3.0 in the test only. IF passes → keep
  grid {0.1, 1.0, 3.0} for R2/R3 (declare in N9). ELSE BLOCKED; rungs R2/R3 run without
  adversary (arms renamed `R2_na`, `R3_na`).
- IF adversary loss diverges (NaN) → clip grad norm 5.0 for all arms (declare in N9).

## N7:
- IF retrieval test fails → check L2 normalisation and temperature; IF still → BLOCKED;
  R3 = R2 (record; primary contrast then falls back to R2, declared in N9).

## N8:
- IF NMF fit > 10 min per fold → fit on a stable-hash subsample of 20,000 training cells
  (declare in N9). IF NMF non-convergence warnings → max_iter 800; record.
- IF program tokens BLOCKED → R4 NOT_NEEDED:blocked_N8; paper omits token claim.

## N9:
- IF any of N5–N8 BLOCKED → the protocol must list the actual arm set, the renamed
  ladder and the primary contrast actually used. The primary contrast is the
  highest available rung among R3 → R2 → R1 → R0, chosen by this rule only.
- IF parameter-matched token-concat cannot reach ±5% → accept ±10%; record.
- Freeze. No real-DS-label NN-v2 fit may exist before this commit (check
  `ls reports/generated/nn_20260923/ladder` is absent).

## N10:
Before full run:
- IF reproduction check differs from −0.0200000 by < 0.01 → record nondeterminism note;
  ELSE spend ≤ 1 iteration diagnosing; then continue regardless (record).
- IF timing probe projects > 6 h → cap 512 amendment. IF > 12 h even at 512 → drop R4 and
  `latent_pca_lsi_head` from the full run (amendment); keep primary arms.
During/after:
- IF an arm fails in > 5 of 25 folds → mark that arm BLOCKED, keep others.
- Outcome classification (write `outcome` into `ladder_summary.json`):
  - `A_ADVANTAGE`: primary estimate ≥ 0.07 AND CI lower bound > 0.
  - `B_NULL`: CI includes 0.
  - `C_DISADVANTAGE`: CI upper bound < 0.
  - `D_SMALL_POSITIVE`: CI lower > 0 but estimate < 0.07.
- Secondary label `LINEAR_SUFFICIENT` IF logreg_rna or logreg_concat mean BA ≥ best NN
  arm mean BA − 0.02.
- Rung decisions per plan §4.2 → `rung_decisions` object.

## N11:
- IF all arms' BA without chr21 ≤ 0.55 → label `DOSAGE_DOMINATED`.
- ELSE IF any arm keeps ≥ 0.60 → label `BEYOND_DOSAGE` for that arm.
- ELSE → `PARTIAL_DOSAGE`.

## N12:
- IF outcome A → require ≥ 4/5 init seeds with estimate ≥ 0.07; ELSE relabel
  `A_FRAGILE`.
- IF outcome B/C/D → report spread only.
- IF sampling-seed spread > 0.07 → label `SAMPLING_SENSITIVE`.

## N13:
- IF NC (identity) Δ ≠ 0 exactly → bug in intervention harness; fix before any other row.
- IF I3 (pairing permutation) Δ log-loss CI excludes 0 for CA → `CA_USES_PAIRING`; ELSE
  `CA_PAIRING_UNUSED`.
- IF I1 (ATAC ablation) Δ CI includes 0 for all fusion arms → `ATAC_UNUSED` (matches
  historical); ELSE `ATAC_USED`.
- IF PC (planted S4/S5 model) fails to show I3 effect while its task BA ≥ 0.8 → the
  permutation test is insensitive; record `I3_INSENSITIVE` and do not interpret real I3.

## N14:
- IF R2 probe drop < 5 points → R2 rejected (plan §4.2). IF DS BA drop > 0.05 →
  `ADVERSARY_ERASES_SIGNAL`; record, keep reporting.

## N15:
- IF a cell appears ≠ 5 times per arm → export bug; fix. Do not average partial repeats.

## N16:
- IF no cell type eligible (support floor) → spectrum `NOT_ESTIMABLE`; report support.
- IF ≥ 1 cell type significant after Holm → `SPECTRUM_LOCALIZED:<types>`.
  Also check: IF the same types are significant for chr21 dosage alone → append
  `(dosage-aligned)`.
- ELSE → `SPECTRUM_NULL` with effect sizes and CIs.
- IF residualized (dev_PCW + depth) test loses significance that the raw test had →
  label that type `CONFOUND_SENSITIVE`.

## N17:
- IF N13 tags missing (N13 BLOCKED) → every readout `NOT_SHOWN_USED`.

## N18:
- IF existing tests break after the fix → the fix changed behaviour beyond budgeting;
  revert to minimal composition change and retest.

## N19:
- IF estimator validation error > 1% → do not trust it; BLOCKED:estimator; N20/N21
  BLOCKED:upstream.
- IF chr21 + 13 candidates alone exceed 3.5e9 → reduce to the 13 candidates + chr21
  genes with ≥ 5% detection; IF still over → BLOCKED:budget.

## N20:
- IF transport error → one retry after 30 min (sleep via `nohup` background run, not a
  blocking wait); ELSE BLOCKED. IF any refusal (truncated/unknown/budget) → BLOCKED with
  the refusal text. Never raise the budget.

## N21:
- IF gene-aligned CA does not fit in memory (1,500 tokens × cells) → restrict tokens to
  the 500 genes with highest label-free dispersion (amendment).
- Outcome labels as in N10, prefixed `GA_`. Secondary only.

## N22 / N23:
- IF any upstream task BLOCKED → results doc states it in the first 10 lines with its
  consequence for the claims.

---

## Paper phase (N24–N34). Framing is chosen by rule, not by preference.

## N24:
Framing decision → `paper/framing.md` (≤ 60 lines). Evaluate in order; the first TRUE row
decides the title and the headline claim:

| # | IF | Framing | Headline claim allowed |
|---|---|---|---|
| F1 | N10 outcome `A_ADVANTAGE` (not `A_FRAGILE`) AND N13 `CA_USES_PAIRING` | Method paper: nuisance-residualized MIL cross-attention for paired multiome disease-state modelling | "internal donor-held-out advantage; pairing is used" |
| F2 | N4 has ≥ 1 `CA_FAVOURED` regime AND N10 outcome B/C/D | Benchmark + negative result: when does cross-modal attention help in paired single-cell data? | "cross-attention helps in planted pairing-dependent regimes; no real-data advantage on DS" |
| F3 | N16 `SPECTRUM_LOCALIZED` (any N10 outcome) | Cell-state spectrum paper: where DS signal lives across developing cortex cell types | "model DS signal localizes to <types>, (not) beyond dosage" |
| F4 | none of the above | Rigorous negative-result/benchmark paper: paired RNA+ATAC gives no donor-level gain over RNA-linear baselines at 30 donors; planted-signal detectability limits | "RNA-linear sufficient; stated detectability limits" |

- IF F1 and F3 both hold → F1 headline, F3 as second contribution. IF F2 and F3 hold →
  F2 headline + F3 section. Record the evaluated truth table.
- Title must not contain "novel", "first", "mechanism", "biomarker".

## N25:
Figures (matplotlib, PNG 300 dpi + PDF, under `paper/figures/`; each from a JSON under
`docs/nn_v2/` via `paper/make_figures.py`):
- Fig 1 architecture/ladder schematic (matplotlib boxes and arrows; no external tools).
- Fig 2 planted benchmark: scenario × model heatmap (δ=1.0) + BA vs δ lines for S4/S5.
- Fig 3 ladder forest plot: CA−TC per rung with CIs; logreg reference line.
- Fig 4 faithfulness: Δ log-loss per intervention with CIs.
- Fig 5 spectrum: per-cell-type DS−CON donor effect with CIs, Holm markers.
- IF a source JSON is missing (BLOCKED task) → skip that figure, record, renumber.

## N26:
Methods section `paper/draft.md` §Methods (≤ 1,400 words). Numbers only from
`configs/nn_protocol_v2_2026-09-23.json`, `configs/nn_inputs_2026-09-23.json`,
amendments. Cite only keys in `paper/refs_frozen.bib` as `[@key]`.

## N27:
Results section (≤ 1,500 words). Every number must come from a `docs/nn_v2/*.json` field;
add each to `paper/claims.csv` (`sentence_id,value,json_path,json_key`). IF a number
cannot be traced → delete the sentence.

## N28:
Introduction + Related work (≤ 900 words). Only frozen keys. IF you want to cite
something not in the frozen bib → write the claim without a citation or drop it. Never
add a bib entry. Precedents to acknowledge: WNN per-cell modality weights
[@hao2021integrated], MultiVI [@ashuach2023multivi], MOFA+ [@argelaguet2020mofa],
cross-modal attention [@tsai2019multimodal; @nagrani2021attention], attention as
explanation debate [@jain2019attention; @wiegreffe2019attention], pseudobulk donor unit
[@squair2021confronting].

## N29:
Discussion + Limitations (≤ 700 words). Mandatory limitations: 30 donors; internal
development cohort only (no external validation); same-cohort annotations
[@lattke2026down]; region panel is not a regulatory panel (unless N21 DONE); attention
is not explanation; any BLOCKED task.

## N30:
Abstract (≤ 200 words) and title, written last, from framing.md + claims.csv.

## N31:
`paper/check_paper.py` (stdlib only): (1) every `[@key]` ∈ refs_frozen.bib; (2) every
number with a decimal point or % in Results/Abstract appears in claims.csv; (3)
forbidden words absent (novel, first, mechanism, causal, biomarker, clinically,
state-of-the-art); (4) figure paths exist; (5) word counts per section within limits;
total ≤ 5,000 words excluding references. IF any check fails → fix the draft (≤ 2
iterations) → IF still failing → record the failing check in the draft header.

## N32:
Adversarial self-review → `paper/self_review.md`: write 8 reviewer objections (leakage,
confounding by age/batch, 30-donor power, planted-signal realism, parameter mismatch,
attention interpretation, region-panel adequacy, lack of external cohort). For each:
IF already answered by an existing result → cite the section. ELSE add the sentence to
Limitations. Never run a new experiment here (G9).

## N33:
Copy the finished draft for the author: create
`/Users/anuragdani/Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/paper-nn/`
and copy `paper/draft.md`, `paper/figures/`, `paper/refs_frozen.bib`,
`paper/claims.csv`, `paper/self_review.md` there. This is the ONLY write allowed outside
the repo. Never edit any other vault file. IF the path is not writable → BLOCKED; the repo
copy is the deliverable.

## N34:
Final: full test suite once, `python paper/check_paper.py` passes, status table complete.
Final label in `paper/draft.md` header comment: `DRAFT_V1_COMPLETE` or
`DRAFT_V1_PARTIAL:<missing>`.
