# P22-NN: professor-aligned neural-network study on paired RNA+ATAC (GNHF prompt)

Prepared 2026-09-23. This file is the GNHF prompt. The executable checklist is the sibling
file `tasks/nn/todo.md` (tasks N0–N23). **Execute code. A proposal, literature summary or
re-planning pass is not progress.** Status at handoff: PLANNED / NOT STARTED.

---

## 0. Assumptions (decided by the user's instruction "make assumptions and move on")

The user instructed: focus on the neural-network code, make assumptions, do not ask for
permission, and do not get blocked. Every assumption below is binding for this run. If an
assumption proves false, record `ASSUMPTION_FAILED:<id>:<evidence>` in `todo.md`, apply the
stated fallback, and continue. **Never stop to ask the user.**

| ID | Assumption | Fallback if false |
|---|---|---|
| A1 | Professor approval for continuing the public Down syndrome (DS) paired RNA/ATAC study is already recorded (`plan/real_data_attestation_2026-09-08.json`). This NN study is a continuation inside that scope. Do not request approval again. | None needed. Do not fabricate a new approval or date. |
| A2 | The user's instruction of 2026-09-23 grants execution scope for this plan: local code, local model fitting on already-saved data, and ONE bounded ATAC range acquisition (N20, ≤3.5 GB transfer). It supersedes the read-only boundary in `docs/P22_SESSION_HANDOFF_2026-09-23.md` for these items only. | — |
| A3 | Development-cohort measured ATAC is available through the CELLxGENE indexed fragment route (465- and 480-region matrices already measured). The `.rda`/Seurat/HEAD route in the 2026-09-23 handoff is **parked**; it is not on this plan's critical path. The handoff was written against main-repo HEAD `8217719` and does not see the GNHF branch results; the worktree evidence supersedes its "no common ATAC space" framing for the development cohort. | If the saved matrices fail hash checks in N0, stop Phase 3+ and record BLOCKED; Phases 1–2 still run on the H5AD RNA plus any matrix that verifies. |
| A4 | External cohort (NeMO/Vuong) is **out of scope**. Every result is internal, donor-held-out, development-cohort only. | — |
| A5 | CPU is the primary device (`torch.set_num_threads(2)` per worker process, up to 8 worker processes via `concurrent.futures.ProcessPoolExecutor`). MPS is not used for any reported number (nondeterminism). | If total wall time for a phase exceeds 6 h, halve `cell_cap` to 512 (predeclared) and record it. |
| A6 | New primary cell cap is **1,000 cells per donor** (≈30,000 cells), drawn by the repaired stable donor×cell-type×library stratified sampler (N1). The historical 256-cap sample remains the reproduction reference. | A5 fallback (512). |
| A7 | RNA representation v2: `log1p(1e4 · raw_count / cell_total_raw_count)` on `raw/X` with `raw/var` axis; per-fold, training-cells-only, label-free highly-variable-gene selection (top 2,000 by normalized dispersion, computed on training cells); per-gene standard scaling fit on training cells. | If memory > 32 GB, use top 1,000 genes and record. |
| A8 | ATAC representation v2: existing unique-fragment-overlap counts → per-cell TF-IDF `log1p(tf · idf)` with `tf = count / cell_total_panel_count` and IDF fit on training cells only; all regions of the per-fold training-only region set (256) are kept. A zero-total cell keeps an all-zero row (recorded count). | — |
| A9 | Chromosome coordinates for genes come from the H5AD `raw/var` columns `seqnames`, `start`, `end` (GRCh38; no strand). Strand-agnostic gene-activity windows = gene body ± 2,000 bp, canonical chromosomes only. No external annotation download. | — |
| A10 | Technical (non-clinical) nuisance factors to residualize: `library`, `batch_seq`, `log1p(nCount_RNA)`, `log1p(nCount_ATAC)`, `TSS.enrichment`, `percent.mt`, `nucleosome_signal`. **Biological factors kept, not removed:** disease, `dev_PCW`, `sex`, cell type. Batches E23 and E27 contain DS donors only; an unconditional batch adversary would erase disease signal, so the adversary is **conditional on the disease label** (N6). | — |
| A11 | Primary endpoint for the new NN-v2 study (declared prospectively in N9, before any real-label fit): donor-level balanced accuracy of `cross_attention` minus matched `token_concat`, both at the final ladder rung R3 (MIL + conditional adversary + contrastive), averaged over 5×5 repeated donor folds (split seed 0), 1,000-draw donor-cluster bootstrap CI. Practical margin 0.07 (unchanged). Secondary: donor AUROC, donor log-loss, Brier. | — |
| A12 | Model selection uses inner-validation **donor log-loss** (smoother than balanced accuracy at 5–6 validation donors). Declared in N9 before fitting. | — |
| A13 | Hyperparameter search is a predeclared tiny grid, identical for every architecture at a rung (N9). No other tuning. Learning rate 1e-3, Adam, max 30 epochs, patience 6, embed 32, hidden 128, dropout 0.2, 8 latent tokens, 4 heads unless the rung declares otherwise. | — |
| A14 | Packages: only what is in `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22` (torch 2.8.0, scikit-learn 1.7.2, scipy, numpy 1.26.4, pandas, anndata 0.12.6, h5py). `statsmodels`, `scanpy`, `pyarrow`, `joblib`, `scvi-tools`, `mofapy2` are **absent and must not be installed**. Use NumPy/SciPy/scikit-learn; write tables as `.csv.gz`/`.npz`/`.json`. MultiVI/MOFA+ baselines are replaced by the matched PCA(RNA)+LSI(ATAC)+head latent baseline (N10) and recorded `NOT_NEEDED:package_absent_by_assumption_A14`. | — |
| A15 | OpenRouter/DeepSeek allowance is whatever the existing key has. On credit/auth failure, save work and stop cleanly (GNHF resumes later). Never change limits, keys or models. | — |
| A16 | A null result is a valid result. The goal is a trustworthy NN comparison and a cell-state spectrum readout, not a cross-attention win. Never tune toward a win. | — |

## 1. What the professor asked, and how this plan answers it

Sources: `VAULT/MOM/2026-07-02/MOM_07-02-2026_Transcript_and_Meeting_Notes.md`,
`VAULT/MOM/2026-07-21/MOM_07-21-2026_Transcript_and_Meeting_Notes.md`,
`VAULT/Professor_Direction_Redline_2026-07-05.md` (a proposed response, not an approval).
`VAULT = /Users/anuragdani/Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22`.

| ID | Professor direction (anchor) | NN response in this plan | Tasks |
|---|---|---|---|
| D1 | Add mathematical nuance: loss functions, residualize non-clinical factors (Jul 2 [00:00]) | Attention-MIL donor loss; conditional gradient-reversal adversary for technical nuisance; cross-modal InfoNCE pairing loss. Each is an ablation rung with a rejection rule. | N5–N7, N10, N14 |
| D2 | Person-level/coarse categorical output is too coarse; study cell-state spectrum (Jul 2 [00:36], [20:51]) | Per-cell DS-state score and MIL attention mass, read out per cell type on held-out donors = condition-by-state spectrum. Donor classification stays only as the training signal and feasibility benchmark. | N15–N17 |
| D3 | Gene-as-token is crowded; use more granular latent/token definitions, programs/sub-features (Jul 2 [01:10], [17:10]) | Program/module tokens: training-only NMF gene programs (RNA) and region modules (ATAC) become attention tokens; gene-aligned RNA↔ATAC gene-activity tokens in Phase 5. | N8, N21 |
| D4 | No saturated subtype classification (Jul 2 [19:30]) | Author cell types are strata/annotation only. Never a prediction target. | all |
| D5 | Compare apple-to-apple; equal supervision (Jul 2 [14:12]) | Every arm: same donors, splits, cells, features, head, selection budget. Parameter counts recorded; parameter-matched token-concat sensitivity. | N9, N10 |
| D6 | Find a benchmark where cross-attention and simpler models should differ (Jul 21 [14:02], [17:39]) | Semi-synthetic planted-signal benchmark on real features: additive vs interaction vs pairing-only signals; answers "which scenario favours cross-attention, which favours MLP/linear". | N3, N4 |
| D7 | Concatenation is the required simple fusion baseline (Jul 21 To-Do 6) | Plain feature concat (logistic + MLP) and matched token-concat in every table. | N4, N10 |
| D8 | Stratified, donor-aware downsampling (Jul 21 [03:40]) | Repaired stable donor×cell-type×library sampler. | N1 |
| D9 | Faithfulness: clamp, permutation, ablation, seeds, held-out donors (Jul 21 To-Do 10) | Held-out interventions incl. within-donor×cell-type ATAC permutation (breaks pairing, keeps marginals), attention knockout, MIL uniform pooling; positive control on planted model. 5 init seeds + 3 sampling seeds. | N12, N13 |
| D10 | Customize from papers: loss, reward, hyperparameters (Jul 21 [25:26]) | Frozen bibliography (§6) → each refinement names its precedent and what was adapted. | N5–N9, N22 |
| D11 | Tasic = engineering check only; write conclusions clearly (Jul 21 [13:39]) | Results doc leads with a plain-language conclusion; no Tasic rerun. | N22 |
| D12 | Verify GenAI claims (Jul 2 [12:09]) | No new citations beyond §6. Novelty claims limited to "adapted combination, not claimed novel". | N22 |
| D13 | DS vs control feasibility, maybe marker panel (Jul 21 [24:15]) | chr21-dosage baseline and chr21-excluded sensitivity test whether DS signal exceeds dosage. | N10, N11 |

## 2. Settled facts — do not redo or contradict

- Historical corrected internal comparison (480-region panel): cross-attention − token-concat
  = +0.0066667, 95% CI [−0.025, +0.0350074]. Tie-break 465-region panel: −0.0200,
  [−0.0533333, +0.0113165]. Margin 0.07 not met. RNA logistic 0.62; cross-attention 0.5133;
  token-concat 0.5333. Seeds 0–4 on tie-break: {−0.02, 0.0, +0.04, −0.0133, +0.0067}.
- Held-out interventions: prediction depends on the RNA view (clamp/ablate drops
  ~0.09–0.16); near-zero ATAC dependence.
- RNA external replication INCONCLUSIVE; donor-influence closed. Do not rerun.
- `X` is processed (non-integer); only `raw/X` is counts. ATAC matrices count unique
  fragment overlaps (not read support). Region sets were chosen by training-library
  prevalence; they are an unbiased-order panel, **not** a regulatory panel (1/13 candidate
  genes overlapped).
- 7 of 30 donors span two libraries/batches. Batches E23, E27 are DS-only.
- Software tests are engineering evidence only.

## 3. Locations

| Alias | Path |
|---|---|
| `WT` (the main P22 checkout, branch `gnhf/p22-nn-cellstate`, base `ec562f4`; ALL code development happens here) | `/Users/anuragdani/Github/niw-eb1a/P22` |
| `SRC_WT` (read-only inputs; ignored data lives here) | `/Users/anuragdani/Github/niw-eb1a/P22-gnhf-worktrees/p22-results-executio-debda8` |
| `PY` | `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with `PYTHONPATH=src:scripts`, `PYTHONDONTWRITEBYTECODE=1` |
| H5AD | `/Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad` (sha256 `08d6eff265db6e6a2e1c4a259153588f3dba3c51f5f754736dc63c28795fcdbb`) |
| ATAC tie-break matrix (465 × 248,998, regions × cells) | `SRC_WT/reports/generated/atac_tiebreak_measured_20260921/counts/counts.npz` (sha256 `5f13c089c0b598c45323d0afc874f96bdf7d4074307c3c01dc40129862d9f969`) |
| Its region sets / union BED | `SRC_WT/reports/generated/atac_tiebreak_sensitivity_20260921/region_sets_sha256.json`, `.../union_sha256.bed`; tracked copy `WT/configs/atac_tiebreak_union_2026-09-21.bed` |
| ATAC historical corrected matrix (480 regions) | `SRC_WT/reports/generated/repeated_comparison_corrected_20260921/counts/counts.npz` (sha256 `81dfdf7c615dd2252792103a4917d87d949ffb46d3affe3aa0f20d3dd31ecf3f`) |
| Local tabix index | `SRC_WT/reports/generated/development_region_set_20260921/fragment.tbi` (sha256 `fd656ed4b287276d102a3aaf800d75678c081afee6fd8c580c747eb76dae306f`) |
| Remote fragment (only for N20) | `https://datasets.cellxgene.cziscience.com/46b43994-2af5-4359-bf75-3314a0d3a7a5-fragment.tsv.bgz` |
| New ignored outputs | `WT/reports/generated/nn_20260923/<task>/` |
| New tracked evidence | `WT/docs/nn_v2/` (compact JSON/MD only, each < 200 KB) |
| Checklist to update | `WT/tasks/nn/todo.md` |

All new code, tests, configs and docs go under `WT` = `/Users/anuragdani/Github/niw-eb1a/P22`.
Never write into `SRC_WT` (other GNHF worktree, read-only inputs) or the vault. Do not
`git add` any path outside the files your task lists; 17 preserved untracked `docs/`
drafts are excluded via `.git/info/exclude` and must stay untouched. Never modify `WT/tasks/plan.md`, `WT/tasks/todo.md` (historical plans) or this
prompt file. Never delete or regenerate historical artifacts.

## 4. Scientific design (fixed; tasks implement it)

### 4.1 Questions

- **Q1 (benchmark validity, D6).** On real feature distributions with a *planted* donor
  signal, which signal structures let cross-attention/gated fusion beat plain
  concatenation and linear models, and does the current implementation detect them?
- **Q2 (primary, D1/D5).** With nuisance-residualized, MIL-trained encoders on the v2
  representation, does cross-attention beat matched token-concatenation for donor-held-out
  DS prediction by ≥ 0.07 balanced accuracy? (A11)
- **Q3 (cell-state spectrum, D2).** In held-out donors, which author cell types carry
  the model's DS signal (out-of-fold per-cell scores, MIL attention mass), and does that
  signal exceed chromosome-21 dosage and technical depth?

### 4.2 Model ladder (each rung = one added refinement; CA and TC always paired)

| Rung | Change | Precedent (§6) | Rejection rule |
|---|---|---|---|
| R0 | v2 representation, cell-level CE with inherited donor labels (current training style) | — | reference |
| R1 | + gated-attention MIL donor loss (bags of 64 cells from one donor) | [B1] | rejected if donor log-loss not lower than R0 for both CA and TC (mean over repeats) |
| R2 | + conditional gradient-reversal nuisance adversary (A10) | [B2] | rejected if held-out nuisance-probe accuracy (within disease) does not drop ≥ 5 points vs R1, OR donor BA drops > 0.05 vs R1 |
| R3 | + symmetric InfoNCE RNA↔ATAC pairing loss | [B3],[B4] | rejected if held-out pairing retrieval top-1 ≤ 2× chance, OR donor log-loss worse than R2 |
| R4 | program/module tokens replace learned latent tokens (on top of R2) | [B5],[B9] | descriptive; rejected if donor BA < R2 − 0.05 |

A rejected rung is still reported; rejection only means it is not carried as evidence for
that refinement. The primary contrast is fixed at R3 regardless of rejection (A11).

### 4.3 Key equations (implement exactly)

- MIL gated attention [B1]: for cell embeddings `h_i` in bag `b`,
  `a_i = softmax_i( w^T ( tanh(V h_i) ⊙ sigmoid(U h_i) ) )`, `H_b = Σ_i a_i h_i`,
  `p_b = sigmoid(f(H_b))`, loss `BCE(p_b, y_donor)`. Inference for a held-out donor: one
  bag = all its sampled cells (≤ 1,000); per-cell score `s_i = f(h_i)` (logit) is exported.
- Conditional adversary [B2]: `L = L_task + λ_adv · Σ_k L_k( g_k( GRL(h) ⊕ onehot(y) ) )`,
  `k ∈ {library (CE), batch_seq (CE), QC vector (MSE on 5 standardized columns)}`;
  GRL forward identity, backward `−γ(p)` with `γ(p) = 2/(1+exp(−10p)) − 1`, `p` = training
  progress in [0,1]. Adversary heads: 1 hidden layer (64).
- InfoNCE [B3]: projections `u_i = norm(P_R z_i^R)`, `v_i = norm(P_A z_i^A)`,
  `L_nce = ½[CE(u Vᵀ/τ, I) + CE(v Uᵀ/τ, I)]`, τ = 0.1 fixed, within minibatch.
- Total: `L = L_MIL + λ_adv·L_adv + λ_nce·L_nce`.

### 4.4 Evaluation contract

- Splits: `iter_repeated_stratified_group_folds(donor, label, 5, 5, 0)` (identical donor
  folds to the historical study); inner 3-fold donor split on training donors for
  validation (same helper, as in `scripts/run_real_paired_comparison.py::_indices`).
- Every fitted transform (HVG, scaler, IDF, NMF, region set) is fit on outer-training
  cells only. Outer-test donors never influence selection, epoch choice or grid choice.
- Donor aggregation: MIL arms use the donor bag; cell-level arms use
  `aggregate_donor_probabilities` (existing).
- Uncertainty: `p22.eval.repeated_comparison.repeated_primary_contrast` (existing donor
  bootstrap) for every contrast. Secondary contrasts are descriptive.
- Spectrum tests (Q3): donor is the unit; per cell type eligible if ≥ 20 cells in ≥ 8
  donors per group; donor-bootstrap CI + 10,000 donor-label permutation p; Holm across
  eligible cell types.

## 5. Execution order

Dependency graph (`→` = must finish first; BLOCKED counts as finished for scheduling):

```
N0 → N1 → N2 → {N3 → N4}
N2 → {N5, N6, N7, N8} → N9 → N10 → {N11, N12, N13, N14} → N15 → {N16, N17}
N0 → N18 → N19 → N20 → N21   (Phase 5, independent; N21 also needs N9 and N10)
all → N22 → N23
```

| Phase | Tasks | Checkpoint (must hold before next phase) |
|---|---|---|
| 0 Foundation | N0 inputs; N1 sampler; N2 data module | inputs hash-verified; sampler counterexample passes; fold prep leak test passes |
| 1 Positive control | N3 planted generator; N4 benchmark run | S1 sanity passes (all models ≥ 0.9 at δ=1.0) else debug before Phase 3 |
| 2 Refinements | N5 MIL; N6 adversary; N7 InfoNCE; N8 program tokens; N9 frozen protocol | unit tests green; protocol JSON committed **before** any real-label fit |
| 3 Real DS runs | N10 ladder; N11 chr21-excluded; N12 seeds; N13 faithfulness; N14 nuisance probe | primary contrast + CI saved; reproduction of historical −0.0200 within 1e-9 |
| 4 Spectrum | N15 export; N16 analysis; N17 routing/attention description | per-cell-type table with Holm-adjusted p |
| 5 ATAC upgrade | N18 budget fix; N19 gene-activity BED; N20 bounded quantification; N21 rerun | acquisition ACCEPTED or BLOCKED with reason |
| 6 Deliver | N22 results + professor note; N23 verification | every task DONE / BLOCKED / NOT_NEEDED with evidence |

Parallelism: one GNHF worker. Inside a task, fold-level fits may run in up to 8 processes.
Phase 5 may be interleaved whenever a Phase 3 run is executing in the background.

## 6. Frozen bibliography (the ONLY citations allowed; do not add, do not invent DOIs)

- [B1] Ilse, Tomczak, Welling. Attention-based Deep Multiple Instance Learning. ICML 2018.
- [B2] Ganin, Lempitsky. Unsupervised Domain Adaptation by Backpropagation. ICML 2015; Ganin et al. Domain-Adversarial Training of Neural Networks. JMLR 2016.
- [B3] van den Oord, Li, Vinyals. Representation Learning with Contrastive Predictive Coding. arXiv 2018.
- [B4] Radford et al. Learning Transferable Visual Models From Natural Language Supervision (CLIP). ICML 2021.
- [B5] Vaswani et al. Attention Is All You Need. NeurIPS 2017.
- [B6] Tsai et al. Multimodal Transformer for Unaligned Multimodal Language Sequences. ACL 2019.
- [B7] Nagrani et al. Attention Bottlenecks for Multimodal Fusion. NeurIPS 2021.
- [B8] Hao et al. Integrated analysis of multimodal single-cell data (Seurat v4, weighted nearest neighbours: per-cell modality weights). Cell 2021.
- [B9] Lee, Seung. Learning the parts of objects by non-negative matrix factorization. Nature 1999.
- [B10] Ashuach et al. MultiVI. Nature Methods 2023; Argelaguet et al. MOFA+. Genome Biology 2020 (named only as excluded baselines under A14).
- [B11] Jain, Wallace. Attention is not Explanation. NAACL 2019; Wiegreffe, Pinter. Attention is not not Explanation. EMNLP 2019.
- [B12] Squair et al. Confronting false discoveries in single-cell differential expression. Nature Communications 2021 (donor as unit of inference).
- [B13] Stuart et al. Single-cell chromatin state analysis with Signac. Nature Methods 2021 (gene-activity = gene body + upstream window; TF-IDF).
- [B14] Lattke et al. Nature Medicine 2026, https://www.nature.com/articles/s41591-026-04211-1 (source cohort; same-cohort annotation, not independent validation).

Novelty language: "adapted combination of known techniques"; never "novel", "first", or
"mechanism". [B8] is a known precedent for per-cell modality weighting; say so.

## 7. Operating rules for the GNHF worker

1. **Start of every iteration:** `git status --short`, `git log --oneline -3`, then read
   `tasks/nn/todo.md` status table (top of file) only. Pick the first task whose status is
   `TODO` and whose dependencies are finished. Read only that task's section
   (`sed -n '/^## N7:/,/^## N8:/p' tasks/nn/todo.md`).
2. **One task per iteration** (two only if both are XS). Finish with focused tests, `ruff`
   on touched files, a status update in `todo.md`, and an evidence line (output path +
   sha256 or test count). GNHF commits.
3. **Never block.** If a step fails after one materially different retry: write
   `BLOCKED:<one-line reason>:<evidence path>` for that task, mark every dependent task
   that genuinely cannot run as `BLOCKED:upstream <id>`, and continue with the next
   runnable task. A task whose inputs are partially available runs on what exists and says so.
4. **Never ask the user anything.** Resolve ambiguity with §0 assumptions; record any
   new assumption as `A-NEW-<n>` in the todo "Run log" section with rationale.
5. **Context hygiene (65k context):** never `cat` files > 200 lines; use `sed -n`/`grep -n`.
   Never print arrays, matrices, JSON > 50 lines or full logs; use `tail -20`. Code files
   ≤ 300 lines each; split modules instead. Each file write ≤ ~250 lines; append in parts.
6. **Long runs:** launch any run expected to exceed 5 minutes with
   `nohup <cmd> > reports/generated/nn_20260923/<task>/run.log 2>&1 &`, record the PID in
   `todo.md`, and finish the iteration after verifying the first fold completes. The next
   iteration checks `tail -5 run.log` and the output files. Never kill another process you
   did not start. Before starting a run, check `pgrep -fl run_nn_` to avoid duplicates.
7. **Resource guards (check before every run):** `df -g /` free ≥ 11 GiB (10 GiB reserve
   + 1 GiB); process RSS ≤ 32 GB (record `resource.getrusage` high-water); no run writes
   > 2 GB. If free disk < 11 GiB: do not start; mark BLOCKED:disk.
8. **Determinism:** `set_all_seeds`, `torch.set_num_threads(2)` per process,
   `torch.use_deterministic_algorithms(True)` in NN runners; every output JSON records
   seeds, git HEAD, protocol sha256, input sha256s, elapsed seconds, and RSS.
9. **Leakage rules:** outer-test donors never touch any `fit`. Add an assertion in every
   runner that the set of donors used in each fitted transform is ⊆ outer-train donors.
10. **Honesty rules:** no claim of mechanism, causality, clinical use, novelty, external
    validity or regulatory function. Attention/gate weights are not explanations [B11]
    unless the matching N13 intervention changes predictions. Report nulls plainly. Never
    change a frozen field in `configs/nn_protocol_v2_2026-09-23.json` after N10 starts;
    any change is a new, separately named amendment file with timestamp and reason.
11. **No:** new packages, network access except N20, pushes, merges, PRs, messages,
    notebook re-execution that refits models, edits outside `WT`, deletion of any file you
    did not create in this run.
12. **Tests:** `PY -m pytest -q tests/test_nn_*.py` after each task; full
    `PY -m pytest -q -x` once at N23 only. Lint: `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/ruff check <files>`.

13. **Reuse before writing (ponytail).** Before adding any function, `grep -rn` `src/`
    and `scripts/` for an existing one and reuse it: `set_all_seeds`, `train_model`,
    `_train_epoch`, `predict`, `aggregate_donor_probabilities`,
    `iter_repeated_stratified_group_folds`, `fit_train_only`, `load_cell_matrix`,
    `repeated_primary_contrast`, `initialization_primary_sensitivity`,
    `measure_stage`, the `real_interventions` pattern, the existing model classes.
    Stdlib or installed packages before custom code. No base classes/registries/config
    layers with one user; a plain dict of arm → builder is enough. Fewest files that meet the
    task's acceptance list. Mark each deliberate corner with `# ponytail: <ceiling>, <upgrade path>`.
    Each task leaves one runnable check (its listed test), not a suite.

## 8. Completion

Stop (`should_fully_stop=true`) only when every task N0–N23 in `tasks/nn/todo.md` is
`DONE`, `BLOCKED:<reason>` or `NOT_NEEDED:<evidence>`, `docs/nn_v2/NN_V2_RESULTS_2026-09-23.md`
exists with the primary contrast, and N23 passed. A BLOCKED Phase 5 does not prevent
completion. Final label must be one of `NN_ASSIGNMENT_COMPLETE` or
`NN_ASSIGNMENT_PARTIAL_BLOCKED`; the study label stays `STUDY_PARTIAL` (no external
validation). Return GNHF's required JSON result every iteration; `success=true` after a
coherent saved increment; `should_fully_stop=false` while runnable tasks remain.
