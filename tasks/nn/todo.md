# P22-NN task checklist (N0–N23)

Companion to `tasks/nn/plan.md` (read its §0 assumptions, §4 design, §7 rules first).
Paths `WT`, `SRC_WT`, `PY`, H5AD are defined in plan §3. Output root for ignored files:
`reports/generated/nn_20260923/`. Tracked evidence: `docs/nn_v2/`.

**Every task also has IF/ELSE rules in `tasks/nn/decision_tree.md` (section G + the task's
section). Read them before starting the task; they override this file on conflict.**

Status values: `TODO`, `RUNNING:<pid>:<log>`, `DONE:<evidence>`, `BLOCKED:<reason>:<evidence>`,
`NOT_NEEDED:<evidence>`. Update only the status table and the Run log; never rewrite task text.

## Status table

| Task | Title | Deps | Size | Status |
|---|---|---|---|---|
| N0 | Startup snapshot + input manifest | — | XS | DONE:configs/nn_inputs_2026-09-23.json; all 4 sha256 inputs match; free=15GiB |
| N1 | Stable donor×cell-type×library sampler | N0 | S | DONE:src/p22/data/nn_sampling.py + tests/test_nn_sampling.py (7 passed) + docs/nn_v2/sampling_cap1000_seed22.json |
| N2 | NN v2 data module + fold preprocessing | N1 | M | DONE:src/p22/data/nn_inputs.py + src/p22/data/nn_fold.py + tests/test_nn_inputs.py (4 passed) + docs/nn_v2/fold_prep_smoke.json (RSS 4.15GiB, region sha256 matc |
| N3 | Planted-signal generator | N2 | S | DONE:src/p22/eval/planted_signal.py + tests/test_nn_planted.py (5 passed) + real-fold check (S5 donor rna-mean |Δ| =4.6e-8, S1/S5 atac untouched) |
| N4 | Planted-signal benchmark run | N3 | M | DONE:reports/generated/nn_20260923/planted/results.csv.gz (sha256 3c00bc865ebad7bc…, 400 records = 16 cells×5 models×5 folds, 0 non-ok) + docs/nn_v2/planted_ben |
| N5 | Gated-attention MIL head + bag training loop | N2 | M | DONE:src/p22/models/mil.py + src/p22/training/bags.py + src/p22/training/mil_loop.py + tests/test_nn_mil.py (10 passed); synthetic 12-donor 10%-signal val donor |
| N6 | Conditional GRL nuisance adversary | N5 | S | DONE:src/p22/models/nuisance.py + tests/test_nn_nuisance.py (9 passed); `mil_loop._train_mil_epoch` meta["index"] added; synthetic planted-batch probe drop 0.23 |
| N7 | Cross-modal InfoNCE pairing loss | N5 | S | DONE:src/p22/models/contrastive.py + tests/test_nn_contrastive.py (10 passed) + mil.py forward_bag_full branch exposure + mil_loop aux-head optimizer; paired lo |
| N8 | Program/module-token fusion models | N2 | M | DONE:src/p22/models/program_tokens.py + tests/test_nn_program_tokens.py (14 passed; ruff clean); NMF train-only isolation, ProgramTokenCrossAttention attention  |
| N9 | Model factory + frozen protocol v2 | N4,N5,N6,N7,N8 | S | DONE:docs/nn_v2/PROTOCOL_FREEZE.md + configs/nn_protocol_v2_2026-09-23.json (protocol_sha256=80931bfc05c403804db47f53b02b29989204a6c04720476cb752dd62968b7161) + |
| N10 | Real DS ladder run (R0–R4 + controls) | N9 | M | DONE:rolled up from N10a, N10b, N10c, N10d |
| N11 | chr21-excluded sensitivity | N10 | S | DONE:docs/nn_v2/chr21_excluded.json |
| N12 | Init-seed and sampling-seed sensitivity | N10 | S | DONE:docs/nn_v2/seed_sensitivity.json |
| N13 | Held-out faithfulness interventions | N10 | M | BLOCKED:agy_call_cap:30 calls; see tasks/nn/lanes/faith.md |
| N14 | Nuisance-probe diagnostics | N10 | S | BLOCKED:agy_call_cap:30 calls; see tasks/nn/lanes/faith.md |
| N15 | Out-of-fold per-cell score export | N10 | S | DONE:reports/generated/nn_20260923/spectrum/cell_scores.csv.gz |
| N16 | Cell-state spectrum analysis | N15,N11 | M | TODO |
| N17 | Routing/attention description by cell type | N15,N13 | S | TODO |
| N18 | Fix retry-budget accounting defect | N0 | XS | DONE:Retry(Budget(raw)) composition; 15 passed tests/test_quantify_development_atac.py; ruff clean |
| N19 | Gene-activity BED + transfer estimate | N18 | S | DONE:configs/nn_gene_activity_2026-09-23.bed+.json; 548 genes, estimate 3493593088<=3.5e9, estimator validation rel_err 0.0<=1%; 30 tests pass, ruff clean |
| N20 | Bounded gene-activity quantification | N19 | S | DONE:quantify.json 548/548 join_complete, 0 truncated, n_unknown=0, bytes_fetched=2066087936<=3.5e9 (window=131072); counts.npz 548x248998 nnz=18722983 cells_sh |
| N21 | Gene-aligned rerun on gene-activity ATAC | N20,N10 | M | BLOCKED:agy_call_cap:30 calls; see tasks/nn/lanes/geneact.md |
| N22 | Results doc + unsent professor note | N10–N21 | M | TODO |
| N23 | Final verification | N22 | XS | TODO |
| N24 | Paper framing decision (rule-based) | N22 | XS | TODO |
| N25 | Paper figures from evidence JSON | N24 | S | TODO |
| N26 | Draft Methods | N24 | S | DONE:paper/draft.md Methods (856 words <=1400, six bold-led blocks: data/cohort, sampling, representation, ladder, architecture+training, evaluation, controls); |
| N27 | Draft Results + claims ledger | N25,N26 | M | TODO |
| N28 | Draft Introduction + Related work | N24 | S | DONE:paper/draft.md Introduction+Related Work (254+237=491 words <=900); 17 frozen citekeys used; check_paper.py 5/5 PASS; 15 tests pass; ruff clean |
| N29 | Draft Discussion + Limitations | N27 | S | TODO |
| N30 | Abstract + title | N29,N28 | XS | TODO |
| N31 | Paper checker + fixes | N30 | S | TODO |
| N32 | Adversarial self-review | N31 | S | TODO |
| N33 | Copy draft to vault | N32 | XS | TODO |
| N34 | Final paper verification | N33 | XS | TODO |

## Run log

- 2026-09-24T19:50Z N4: batch session was killed by the user mid-iteration. Full benchmark `scripts/run_nn_planted_benchmark.py --cap 1000 --workers 5` left running as PID 37613 (log reports/generated/nn_20260923/planted/run.log). Current docs/nn_v2/PLANTED_BENCHMARK.md + planted_benchmark.json are a 1-fold SMOKE (SD=nan), not the result. Next: per decision_tree G1, if PID alive do N5; when it exits, verify outputs cover 16 scenario×delta cells × 5 models × 5 folds, regenerate the docs, run tests, mark N4 DONE. Do not start a second benchmark.

(append one line per iteration: date-time UTC, task, outcome, evidence path; record any
`A-NEW-<n>` assumption here with a one-line rationale)

- 2026-09-23T00:00Z N0 DONE. Manifest `configs/nn_inputs_2026-09-23.json`; H5AD, tie-break 465, historical 480, fragment.tbi all sha256 match plan §3; free disk 15 GiB, RAM 128 GiB; H5AD raw shape 248998×35477, all 13 required obs columns present, raw/var has seqnames/start/end. Next: N1.
- 2026-09-23T18:58Z N1 DONE. New `src/p22/data/nn_sampling.py::sample_donor_stratified_cells(obs, cap, seed, strata=("author_cell_type","library"))` (hierarchical largest-remainder allocation, ≥1 per joint stratum when cap allows, sha256 tie-break, label-free). `tests/test_nn_sampling.py` 7 passed incl. real-obs check on all 7 two-library donors. Evidence `docs/nn_v2/sampling_cap1000_seed22.json` (cap1000 seed22: 30000 cells, 0 proportionality violations; cap256 reproduction block included). ruff clean. Next: N2.
- 2026-09-23T19:40Z N2 DONE. `src/p22/data/nn_inputs.py` (265 lines: loader, `NNInputs`/`FoldArrays`, gene/region tables, chr21 masks, `region_indices`, lazy `prepare_nn_fold` re-export) + `src/p22/data/nn_fold.py` (184 lines: `_rna_lognorm` A7, `_hvg_indices`, `_atac_tfidf` A8, `_qc_matrix`, `prepare_nn_fold`). `tests/test_nn_inputs.py` 4 passed (train-only fit invariance incl. IDF sha256 + rna/atac unchanged, chr21 exclusion, region-id mapping, train/holdout donor-overlap refusal); ruff clean. Real-data smoke repeat 0/fold 0 cap1000 seed22: 30000 cells, rna [30000,2000], atac [30000,256], qc [30000,5], 15000 positives, `region_set_sha256` matches union JSON, load 7.03s, prep 1.52s, peak RSS 4.153 GiB. Evidence `docs/nn_v2/fold_prep_smoke.json`. Next: N3.
- 2026-09-24T00:00Z N3 DONE. `src/p22/eval/planted_signal.py` (`fake_donor_labels` sha256-rank alternating within disease group; `select_features` 20 RNA HVG cols + 20 ATAC region cols by hash rank; `plant` S0/S1/S2/S3/S4/S5, train-only median, S5 per-donor RNA re-centering, non-mutating). `tests/test_nn_planted.py` 5 passed (fake table [[2,2],[2,2]] balanced/independent, S0 identity, S5 donor marginal |Δ|<1e-5, S1 only positive-donor RNA cols, feature determinism); ruff clean. Real-fold check repeat0/fold0 cap1000 seed22: 30000 cells, 14000 fake-positive, S5 worst donor rna-mean |Δ|=4.6e-8, atac untouched, S1 rna diff 1.0. Next: N4.
- 2026-09-24T01:10Z N4 step (a)/3 done: wrote `scripts/run_nn_planted_benchmark.py` (16-cell grid: S0 δ0 + S1–S5 × {0.25,0.5,1.0}; 5 models; 5 outer folds; plants signal post train-only prep; fake-label-stratified outer+inner folds; writes results.csv.gz + planted_benchmark.json + PLANTED_BENCHMARK.md) and `tests/test_nn_planted_benchmark.py` (unit-tests `delta_grid`/`fold_positions`/`donor_scores`/`regime_labels`/`acceptance_checks`). ruff clean; `pytest -q tests/test_nn_planted_benchmark.py` 4 passed. N4 stays TODO; next step is the real run.
- 2026-09-24T02:10Z N5 step 1/3 done: wrote `src/p22/models/mil.py` (`GatedAttentionPool(dim, attn_dim=64)`, `MILWrapper(encoder_model, dim)` dispatch over fusion `.fused_embedding` / single-view `.embed`; `forward_bag(views)->(logit_bag[1], attention[n_cells] sum=1, cell_logits[n_cells])`) and `src/p22/training/bags.py` (`make_bags(donor_ids, bag_size=64, seed, epoch)`, per-donor seeded shuffle, purity, last partial kept iff ≥16 cells). `tests/test_nn_mil.py` 7 passed (attention sum, permutation invariance, both encoder paths, bag purity/determinism/partial rule, input validation); ruff clean. N4 PID 37613 still alive (04:14 elapsed). N5 stays TODO; next: mil_loop.py + synthetic 12-donor AUROC≥0.9 test.
- 2026-09-24T03:05Z N5 step 2/3 done: wrote `src/p22/training/mil_loop.py` (`train_mil` Adam + BCE per donor bag, equal-donor weighting, val = one-bag-per-donor log-loss, patience 6, best-state restore, returns `TrainedModel(selection_metric="negative_donor_log_loss", selection_unit="donor", training_weighting="equal_donor_bags")`; `predict_mil` -> donor probs/logits + per-cell logits + attention; `aux_losses` callables `(batch_out, batch_meta)->(name,tensor)` for N6/N7). Not yet validated. N4 PID 37613 still alive. N5 stays TODO; next: synthetic AUROC + signature tests.
- 2026-09-24T03:30Z N5 step 3/3 done (N5 DONE): added to `tests/test_nn_mil.py` a 12-train+12-val-donor partial-signal generator (10% of positive-donor cells shifted ±4), `test_synthetic_partial_signal_reaches_donor_auroc` (val donor AUROC=1.0 across seeds 0/1/2, 30 epochs), `test_predict_mil_shapes_and_per_donor_attention` (per-donor attention sums to 1), and `test_train_mil_signature_has_no_test_arrays`. `PY -m pytest -q tests/test_nn_mil.py` 10 passed in 2.79s; ruff clean on all four N5 files. N4 PID 37613 still alive (run.log still 0 bytes). Next: N6 (GRL nuisance adversary).
- 2026-09-24T04:00Z N6 step 1/2 done: wrote `src/p22/models/nuisance.py` (`_GradReverse`/`grl` (forward identity, backward -gamma), `gamma_schedule(p)=2/(1+exp(-10p))-1`, `ConditionalNuisanceAdversary(dim,n_library,n_batch,n_qc=5,hidden=64)` with 3 heads reading `cat(grl(h),onehot(y))` so the label is protected, `adversary_losses` (library CE + batch CE + QC MSE + total), and `adversary_aux_loss` factory returning `(batch_out,batch_meta)->("adversary",lambda*total)` keyed on `batch_meta["index"]`). `tests/test_nn_nuisance.py` 8 passed (grad == -gamma*w, gamma 0 no grad, schedule endpoints+monotone, head shapes, label-conditioning, finite losses+backprop, factory index/scale/validation); ruff clean. N4 PID 37613 still alive. Next: step 2/2 = set `meta["index"]`/progress in `mil_loop._train_mil_epoch`, synthetic probe-drop test, then mark N6 DONE.
- 2026-09-24T20:20Z N4 DONE. Background PID 37613 had exited; run.log "status: 400 ok / 0 non-ok of 400". Verified results.csv.gz 400 records over exactly 16 scenario×δ cells × 5 models × 5 folds; regenerated docs/nn_v2/PLANTED_BENCHMARK.md + planted_benchmark.json already carry mean±SD tables, acceptance_checks and per-cell `regime_labels`. Decision-tree N4: S0 range [0.50,0.5417] within [0.35,0.65] (no leak); S1 δ=1.0 all models =1.0 (sane); S5 δ=1.0 every fusion model is far above chance (max dev 0.5) so the δ=2.0 amendment is NOT triggered — recorded finding "current fusion capacity detects pairing-only signal at cap 1000". Classification: no cell is CA_FAVOURED (CA−best non-attention ≤ 0 everywhere; best is −0.1); S0/S1/S2/S3/S4 = LINEAR_SUFFICIENT, S5 = MLP_FAVOURED (gated_fusion 0.97–1.0 vs logreg 0.54). `pytest -q tests/test_nn_planted.py tests/test_nn_planted_benchmark.py` 9 passed. Next: N6 step 2/2.
- 2026-09-24T21:05Z N6 DONE. Step 2/2: `mil_loop._train_mil_epoch` now sets `meta["index"]` (bag row positions) alongside `progress`; added `test_adversary_strips_planted_batch_signal` to `tests/test_nn_nuisance.py` (synthetic 400 cells, label in feature 0, batch in feature 1; `ViewEncoder(6,embed_dim=4)`+`Linear(4,2)`, 1500 epochs, gamma_schedule ramp, λ=0 vs λ=3.0, seeds 0/1, within-label LogisticRegression batch probe). Result: control probe [1.0,0.998] mean 0.999, regularised [0.735,0.8] mean 0.768, drop 0.231 ≥ 0.10; label probe [1.0,1.0]. `PY -m pytest -q tests/test_nn_nuisance.py` 9 passed in 5.8s; ruff check clean on both N6 files. Direct gradient probe confirmed GRL flows (gamma=0 → enc grad 0.0; gamma=1 → 0.0566) and the earlier no-drop was insufficient epochs, not registration. A-NEW-1: `train_mil`'s Adam optimises only `model.parameters()`, so at N9/N10 the adversary must be attached as a model submodule (e.g. `model.adversary = adversary`) or its params added explicitly, otherwise the nuisance heads never train. Next: N7 (cross-modal InfoNCE pairing loss).
- 2026-09-24T21:35Z N7 DONE. `src/p22/models/contrastive.py` (`PairingHead(dim,proj=32)` two linear projections; `info_nce(u,v,tau=0.1)` symmetric CE over arange labels; `branch_embeddings(model,views)` unwraps encoder/MILWrapper, requires `has_gate`; `pairing_aux_loss(head,lambda_nce=1.0)` factory returning `(batch_out,batch_meta)->("pairing",λ·loss)` keyed on `branch_embeddings`, exposes `.head`; `pairing_retrieval_top1(model,arrays,chunk_size=256)` chunked). `mil.py` gained `MILWrapper.forward_bag_full` (single encoder pass returns logit/attention/cell_logits/embeddings/branch_embeddings; `forward_bag` delegates). `mil_loop._bag_batch` now surfaces `branch_embeddings`; optimizer collects aux `.head` params deduped by id; `best_aux_state` saved/restored alongside model best state (addresses A-NEW-1 for N7). `tests/test_nn_contrastive.py` 10 passed (paired 5.88→1.2-ish < shuffled; retrieval 1.0 identical / <0.02 shifted, chance 1/256; MILWrapper branch shapes; train_mil moves `head.proj_r.weight`); `pytest -q tests/test_nn_contrastive.py tests/test_nn_mil.py tests/test_nn_nuisance.py` 29 passed; ruff clean on all four touched files. Next: N8 (program/module-token fusion models).

---

## N0: Startup snapshot + input manifest

**Description:** Verify the workspace and freeze input identities so every later result
binds to exact bytes.

**Steps:**
1. `git status --short`; `git log --oneline -3`; confirm branch `gnhf/p22-nn-cellstate`.
2. `df -g /` and `sysctl -n hw.memsize`; record free GiB and RAM.
3. sha256 every input in plan §3 (H5AD, both counts.npz, fragment.tbi, region-set JSONs,
   union BEDs). Compare to the hashes listed in plan §3.
4. Write `configs/nn_inputs_2026-09-23.json`: absolute paths, sha256, shapes (read npz
   shape only via `scipy.sparse.load_npz(...).shape`), expected-vs-observed match flags,
   free disk, RAM, git HEAD, python/torch/sklearn versions.
5. Record H5AD obs columns needed later exist: `donor_id, disease, library, batch_seq,
   sex, dev_PCW, author_cell_type, cell_class, nCount_RNA, nCount_ATAC, TSS.enrichment,
   percent.mt, nucleosome_signal`.

**Acceptance criteria:**
- [ ] Manifest JSON exists; every listed hash matches, or mismatch recorded.
- [ ] Free disk ≥ 11 GiB recorded (else later runs BLOCKED:disk).

**Verification:** `PY -c "import json;d=json.load(open('configs/nn_inputs_2026-09-23.json'));print(all(v['match'] for v in d['inputs'].values()))"` prints True.

**On failure:** hash mismatch on an ATAC matrix → mark tasks that need that matrix
BLOCKED; the other matrix may still be used (tie-break 465 is primary; historical 480 is
only for reproduction checks). H5AD mismatch → BLOCKED all real-data tasks; N3–N8 still
run on synthetic fixtures.

**Files:** `configs/nn_inputs_2026-09-23.json`.

---

## N1: Stable donor×cell-type×library sampler (repairs 09-21 review defect 2)

**Description:** The proposed stratified sampler took lowest row indices, dropping whole
libraries for 5 of 7 two-library donors. Build a deterministic sampler that allocates the
per-donor cap across (author_cell_type × library) strata proportionally
(largest remainder, ≥1 per present stratum when cap allows) and picks cells inside each
stratum by stable hash rank: `sha256(f"{seed}\n{cell_id}")`.

**Implementation:**
- Add `sample_donor_stratified_cells(obs: DataFrame, cap: int, seed: int,
  strata=("author_cell_type","library")) -> np.ndarray` (sorted row indices) in new
  `src/p22/data/nn_sampling.py`. Pure pandas/numpy/hashlib. Donors with ≤ cap cells keep
  all cells.
- Do not modify `sample_nested_capped_cells` (historical).

**Acceptance criteria:**
- [ ] Every two-library donor keeps both libraries; each library share within ±2 cells of
      proportional allocation (test on the real obs + a synthetic fixture).
- [ ] Deterministic: same seed → identical indices; shuffled obs row order → identical
      selected cell IDs.
- [ ] No disease/label column is read (assert signature/columns used).

**Verification:** `PY -m pytest -q tests/test_nn_sampling.py`; plus a script
`scripts/nn_sampling_report.py` writing `docs/nn_v2/sampling_cap1000_seed22.json`
(per-donor library and cell-type counts, cap 1000, seed 22; and cap 256 for comparison).

**Files:** `src/p22/data/nn_sampling.py`, `tests/test_nn_sampling.py`,
`scripts/nn_sampling_report.py`, `docs/nn_v2/sampling_cap1000_seed22.json`.

---

## N2: NN v2 data module + fold preprocessing

**Description:** One loader and one fold-preprocessing function used by every NN run.

**Implementation (`src/p22/data/nn_inputs.py`, ≤ 300 lines; split if needed):**
- `load_nn_inputs(h5ad, atac_npz, cap, seed) -> NNInputs` dataclass: sampled row
  indices (N1), metadata frame (cell_id, donor_id, label = disease=="complete trisomy 21",
  author_cell_type, cell_class, library, batch_seq, sex, dev_PCW, qc columns per A10),
  RNA raw counts CSR from `raw/X` for sampled rows (reuse
  `p22.data.real_cohort.load_cell_matrix(..., matrix_key=DEFAULT_RNA_MATRIX_KEY)`),
  per-cell raw totals computed over **all** genes, gene table from `raw/var`
  (gene id, gene_name, seqnames, start, end), ATAC CSR (cells × regions, transpose of the
  saved regions × cells matrix), region list from the union BED in matrix row order
  (verify order via the region-sets JSON / manifest used in 09-21), chr21 masks for genes
  and regions.
- `prepare_nn_fold(inputs, train_rows, holdout_rows, region_rows, cfg) -> FoldArrays`:
  RNA log-normalize (A7), HVG on train rows only (dispersion = var/mean of normalized
  values, binned by mean into 20 bins, z-scored within bin; top `n_hvg`), scaler fit on
  train; ATAC restricted to `region_rows` (the fold's training-only region set from
  `region_sets_sha256.json`), TF-IDF with train-only IDF (A8), scaler fit on train;
  QC matrix standardized on train; categorical nuisance codes. Option
  `exclude_chr21: bool` drops chr21 genes/regions **before** HVG selection.
- Returns float32 dense arrays (≈30k × 2,256 floats ≈ 270 MB; fine) plus an evidence
  dict (selected gene ids, region ids, donors used per fit).
- Leakage assertion: donors behind every fit ⊆ train donors.

**Acceptance criteria:**
- [ ] Synthetic-fixture test: changing only holdout rows' values leaves HVG choice,
      scaler and IDF unchanged.
- [ ] Real smoke: repeat 0 / fold 0 at cap 1000 loads in < 5 min, RSS < 16 GB;
      shapes recorded in `docs/nn_v2/fold_prep_smoke.json`.
- [ ] `exclude_chr21=True` yields zero chr21 features (test).

**Verification:** `PY -m pytest -q tests/test_nn_inputs.py`.

**Files:** `src/p22/data/nn_inputs.py`, `tests/test_nn_inputs.py`,
`docs/nn_v2/fold_prep_smoke.json`.

---

## N3: Planted-signal generator (professor Jul 21 [14:02])

**Description:** Semi-synthetic labels and signal on real features so we know when
cross-attention *should* win. Label is fake and independent of DS.

**Design (`src/p22/eval/planted_signal.py`):**
- Fake donor label: within each true disease group, assign donors to fake 0/1 by
  `sha256(f"planted-v1\n{donor}")` rank, alternating → balanced, independent of DS.
- Fixed feature sets chosen without labels: RNA set G = 20 HVGs picked by hash rank from
  the fold's HVG list; ATAC module M = 20 regions by hash rank. `r_i` = mean of G,
  `m_i` = mean of M (after scaling), per cell.
- Scenarios, applied only to fake-positive donors' cells, effect δ ∈ {0.25, 0.5, 1.0} (SD):
  - S1 RNA-additive: G += δ.
  - S2 ATAC-additive: M += δ.
  - S3 both-additive: G += δ/2, M += δ/2.
  - S4 context interaction: G += δ only where `m_i > median_train(m)` (cell-context dependent).
  - S5 pairing-only: G += δ·sign(m_i − median_train(m)) and then re-center G per donor so
    donor-level marginal means of G and M are unchanged; only the RNA–ATAC joint differs.
  - S0 null: no change (all models must be ≈ 0.5).
- Planting happens **after** fold preprocessing on the scaled arrays, using train-only
  medians; pure function `plant(fold_arrays, scenario, delta, seed) -> (arrays, fake_labels)`.

**Acceptance criteria:**
- [ ] Tests: S5 leaves each donor's G and M means unchanged (|Δ| < 1e-5); S0 is identity;
      fake labels balanced within each DS group and independent of disease (exact table).

**Verification:** `PY -m pytest -q tests/test_nn_planted.py`.

**Files:** `src/p22/eval/planted_signal.py`, `tests/test_nn_planted.py`.

---

## N4: Planted-signal benchmark run

**Description:** Run existing families on planted data: `logreg_concat` (sklearn
LogisticRegression C=1, lbfgs, max_iter 1000, donor-weighted as in
`scripts/run_real_paired_linear_controls.py`), `rna_atac_concat` MLP, `gated_fusion`,
`token_concat`, `cross_attention` (existing classes, embed 32 / hidden 128 / 8 tokens / 4
heads / dropout 0.2), existing cell-level training loop with donor weights.
Design: 1 repeat × 5 outer folds, 6 scenarios × 3 δ (S0 only δ=0), cap 1000.

**Script:** `scripts/run_nn_planted_benchmark.py --cap 1000 --out reports/generated/nn_20260923/planted/`
(parallel over folds via ProcessPoolExecutor, 8 workers, 2 threads each).

**Outputs:** `results.csv.gz` (scenario, δ, fold, model, donor BA, donor AUROC, log-loss),
`docs/nn_v2/planted_benchmark.json` + `docs/nn_v2/PLANTED_BENCHMARK.md` (table
scenario × δ × model, mean ± SD over folds, and a 5-line plain-language reading).

**Predeclared interpretation:**
- S0 all models 0.35–0.65 → pipeline sane; else leakage bug → BLOCK Phase 3 until fixed.
- S1 at δ=1.0 all models ≥ 0.9 → sane; else debug fold prep.
- S5: linear expected ≈ chance; if every neural fusion is also ≈ chance at δ=1.0, record
  "current fusion capacity cannot detect pairing-only signal at this sample size" — this
  is a finding, not a failure; continue.
- S4/S5: record whether CA or gated beats `rna_atac_concat` MLP by ≥ 0.07. This answers
  the professor's "which scenario favours which model".

**Acceptance criteria:**
- [ ] All 16 scenario×δ cells × 5 models × 5 folds present (or listed failures).
- [ ] Markdown table + reading committed.

**Verification:** `PY -m pytest -q tests/test_nn_planted.py`; check row count in CSV.

**Files:** `scripts/run_nn_planted_benchmark.py`, `docs/nn_v2/PLANTED_BENCHMARK.md`,
`docs/nn_v2/planted_benchmark.json`.

---

## N5: Gated-attention MIL head + bag training loop

**Description:** Donor labels are bag labels; stop pretending every cell is DS-positive.
Implement plan §4.3 MIL.

**Implementation:**
- `src/p22/models/mil.py`: `GatedAttentionPool(dim, attn_dim=64)` returning `(H, a)`;
  `MILWrapper(encoder_model, dim)` where `encoder_model` is any existing fusion/baseline
  model exposing a fused/embedding tensor (use `FusionOutput.fused_embedding` or
  `BaselineMLP.embed`); head `Linear(dim, 1)`; `forward_bag(views) -> (logit_bag, a, cell_logits)`.
- `src/p22/training/bags.py`: `make_bags(donor_ids, bag_size=64, seed, epoch)` → list of
  index arrays, each from one donor, deterministic per (seed, epoch); last partial bag kept
  if ≥ 16 cells.
- `src/p22/training/mil_loop.py`: `train_mil(model, train_arrays, donors, labels,
  val_arrays, val_donors, val_labels, cfg, aux_losses=()) -> TrainedModel-like record`:
  Adam, BCE per bag, each donor weighted equally per epoch (bags per donor normalized),
  validation = donor log-loss with one bag per val donor (all its cells), early stopping
  patience 6, best-state restore. `aux_losses` = callables `(batch_out, batch_meta) ->
  (name, tensor)` used by N6/N7. `predict_mil(model, arrays, donors)` → donor probs +
  per-cell logits + attention.

**Acceptance criteria:**
- [ ] Attention sums to 1 per bag; pooled output invariant to cell permutation (test).
- [ ] Synthetic: 12 donors where only 10% of cells in positive donors carry signal → MIL
      reaches val donor AUROC ≥ 0.9 in ≤ 30 epochs (fixed seed) (test).
- [ ] No test arrays passed to `train_mil` (signature has none).

**Verification:** `PY -m pytest -q tests/test_nn_mil.py`.

**Files:** `src/p22/models/mil.py`, `src/p22/training/bags.py`,
`src/p22/training/mil_loop.py`, `tests/test_nn_mil.py`.

---

## N6: Conditional GRL nuisance adversary

**Description:** Residualize technical factors (A10) without erasing disease (E23/E27 are
DS-only, so condition on label).

**Implementation (`src/p22/models/nuisance.py`):**
- `GradReverse` autograd Function; `grl(x, gamma)`.
- `ConditionalNuisanceAdversary(dim, n_library, n_batch, n_qc=5, hidden=64)`: input
  `cat(grl(h), onehot(y))`; heads: library CE, batch CE, QC MSE.
- `gamma_schedule(progress) = 2/(1+exp(-10p)) - 1`.
- `adversary_aux_loss(lambda_adv)` factory returning an aux loss callable for
  `train_mil` (applied to per-cell embeddings `h_i` of the bag).
- Library codes: fit mapping on train cells; unseen library in holdout is fine (adversary
  unused at inference).

**Acceptance criteria:**
- [ ] Gradient through `grl` equals `-gamma ×` identity gradient (test with autograd).
- [ ] Synthetic: planted batch signal in embeddings → post-training linear probe
      accuracy for batch (within label) drops by ≥ 10 points vs λ=0 (test, fixed seed).

**Verification:** `PY -m pytest -q tests/test_nn_nuisance.py`.

**Files:** `src/p22/models/nuisance.py`, `tests/test_nn_nuisance.py`.

---

## N7: Cross-modal InfoNCE pairing loss

**Description:** Label-free signal from RNA↔ATAC pairing (plan §4.3). Exposes branch
embeddings `z_R`, `z_A` (existing `FusionOutput.branch_embeddings`).

**Implementation (`src/p22/models/contrastive.py`):** `PairingHead(dim, proj=32)` with
two linear projections; `info_nce(u, v, tau=0.1)` symmetric; `pairing_aux_loss(lambda_nce)`
factory for `train_mil`; `pairing_retrieval_top1(model, arrays)` metric (held-out, chunks
of 256 cells, chance = 1/256).

**Acceptance criteria:**
- [ ] Loss on correctly paired synthetic data < loss after shuffling pairs (test).
- [ ] Retrieval metric = 1.0 on identical embeddings and ≈ 1/256 on shuffled (test).

**Verification:** `PY -m pytest -q tests/test_nn_contrastive.py`.

**Files:** `src/p22/models/contrastive.py`, `tests/test_nn_contrastive.py`.

---

## N8: Program/module-token fusion models (professor D3)

**Description:** Tokens with identities instead of anonymous latent tokens.

**Implementation (`src/p22/models/program_tokens.py`):**
- `fit_programs(train_matrix_nonneg, k, seed)`: sklearn `NMF(n_components=k,
  init="nndsvda", max_iter=400, random_state=seed)` on **training cells only**; RNA input =
  log-normalized HVG matrix before scaling (non-negative), k_R = 16; ATAC input = TF-IDF
  matrix before scaling, k_A = 8. Returns fitted NMF; `transform` for holdout.
- `ProgramTokenCrossAttention(k_R, k_A, dim=32, heads=4)`: token_k = activity_k · E_k +
  b_k (learned `E`, `b`); RNA program tokens (queries) attend to ATAC module tokens
  (keys/values) via `nn.MultiheadAttention(batch_first=True)`; fused = cat(mean RNA tokens,
  mean ATAC tokens + mean context); exposes `attention_weights` (cells × k_R × k_A) when
  `need_weights=True`; returns `FusionOutput`.
- `ProgramTokenConcat` matched control: same token construction, mean-pool + concat, no
  attention. Record parameter counts for both.
- Program annotation helper: top-10 genes per RNA program, top-10 regions per ATAC module
  (from NMF components) → saved per fold for N17.

**Acceptance criteria:**
- [ ] NMF fit sees only training rows (test with holdout perturbation).
- [ ] Output shapes and attention rows summing to 1 (test); both models work inside
      `MILWrapper`.

**Verification:** `PY -m pytest -q tests/test_nn_program_tokens.py`.

**Files:** `src/p22/models/program_tokens.py`, `tests/test_nn_program_tokens.py`.

---

## Checkpoint A (after N0–N8)

- [ ] `PY -m pytest -q tests/test_nn_*.py` all pass; ruff clean on new files.
- [ ] N4 sanity rules passed (S0, S1), or the leak/debug fix is committed and N4 rerun.
- [ ] Nothing in `SRC_WT`, main repo or vault modified (`git -C SRC_WT status --short` unchanged).

---

## N9: Model factory + frozen protocol v2

**Description:** Freeze every choice **before** any real-DS-label fit (A11–A13).

**Implementation:**
- `src/p22/eval/nn_factory.py`: `build_arm(arm_name, widths, cfg) -> (model, aux_losses,
  trainer)` for arms:
  `R0_{ca,tc}` (existing CrossAttentionModel / TokenConcatFusionModel, cell-level loop),
  `R1_{ca,tc}` (+MIL), `R2_{ca,tc}` (+MIL+adv), `R3_{ca,tc}` (+MIL+adv+nce),
  `R4_{ca,tc}` (program tokens + MIL + adv), `R3_tc_parammatched` (token-concat hidden
  widened until parameter count within ±5% of `R3_ca`), `R3_gated`,
  `latent_pca_lsi_head` (train-only PCA 32 on RNA + TruncatedSVD 32 on TF-IDF ATAC →
  MLP head, MIL), controls `logreg_rna`, `logreg_concat` (cell-level, donor weights),
  `pseudobulk_rna_logistic`, `chr21_dosage`, `majority`.
- `configs/nn_protocol_v2_2026-09-23.json`: cap 1000, sampling seed 22, split seed 0,
  5×5 folds, inner 3-fold val, representation (A7/A8), n_hvg 2000, region set
  = tie-break 465 per-fold sets, architecture defaults (A13), bag size 64, grid:
  `R2: lambda_adv ∈ {0.1, 1.0}`, `R3: lambda_adv best-of-R2 rule is NOT used; grid
  lambda_adv ∈ {0.1,1.0} × lambda_nce ∈ {0.1,1.0}` (same for ca/tc), others no grid;
  selection = inner-val donor log-loss; primary contrast `R3_ca − R3_tc` donor BA; margin
  0.07; bootstrap 1000, seed 22; model seed 0; rung rejection rules (plan §4.2).
  Include `protocol_sha256` of the canonical JSON dump.
- `docs/nn_v2/PROTOCOL_FREEZE.md`: ≤ 40 lines, time of freeze (UTC), git HEAD, statement
  that no real-label NN-v2 fit has run yet (evidence: `ls reports/generated/nn_20260923/`).

**Acceptance criteria:**
- [ ] Factory builds every arm on synthetic widths; parameter counts table saved
      `docs/nn_v2/parameter_counts.json`.
- [ ] Protocol committed in the same commit as the freeze note, before N10.

**Verification:** `PY -m pytest -q tests/test_nn_factory.py`.

**Files:** `src/p22/eval/nn_factory.py`, `configs/nn_protocol_v2_2026-09-23.json`,
`docs/nn_v2/PROTOCOL_FREEZE.md`, `docs/nn_v2/parameter_counts.json`,
`tests/test_nn_factory.py`.

---

## N10: Real DS ladder run

**Description:** Execute the frozen protocol on real development data.

**Script:** `scripts/run_nn_v2_comparison.py --protocol configs/nn_protocol_v2_2026-09-23.json
--out reports/generated/nn_20260923/ladder/` (+ `--arms`, `--repeats`, `--resume` to skip
finished fold×arm files). One JSON per (repeat, fold, arm) under `folds/`, containing donor
predictions, best grid point, inner-val log-loss per grid point, epochs, parameter count,
elapsed, RSS, fit-donor sets. Parallel over (repeat, fold) with 8 processes.

**Before the full run:**
1. Reproduction check: run the **historical** protocol (`configs/paired_multiome.json`
   protocol values, cap 256, sampling via `sample_nested_capped_cells`, tie-break matrix,
   raw-count standard scaling as in `scripts/run_real_paired_comparison.py`) for
   `cross_attention` and `token_concat` via the existing script into
   `reports/generated/nn_20260923/reproduction/`; primary contrast must equal −0.0200000
   (|diff| < 1e-9). If not identical, record the difference and continue (A-NEW note).
2. Timing probe: repeat 0 fold 0, all arms; if projected total > 6 h, apply A5 fallback
   (cap 512) — write the amendment file `configs/nn_protocol_v2_amendment_cap512.json`
   **before** running further folds.

**Summary:** `scripts/summarize_nn_v2.py` → `docs/nn_v2/ladder_summary.json` and
`docs/nn_v2/LADDER.md`: per-arm mean donor BA/AUROC/log-loss; primary contrast with
`repeated_primary_contrast(repeats, model="R3_ca", reference="R3_tc")` (adapt the
record shape: each repeat dict holds per-arm donor prediction tables as the function
expects — read its `_prepare_repeats` first); secondary contrasts (each rung CA−TC; R3_ca
vs logreg_rna; R3_ca vs R3_tc_parammatched); rung rejection outcomes per plan §4.2.

**Acceptance criteria:**
- [ ] 25 fold files per arm (or failures listed with error text).
- [ ] Primary estimate, CI, margin decision in `ladder_summary.json`.
- [ ] Leakage assertions passed in every fold file.

**Verification:** focused tests for runner helpers `tests/test_nn_runner.py` (tiny synthetic
end-to-end with 6 donors, 2 folds); file count check.

**Files:** `scripts/run_nn_v2_comparison.py`, `scripts/summarize_nn_v2.py`,
`tests/test_nn_runner.py`, `docs/nn_v2/ladder_summary.json`, `docs/nn_v2/LADDER.md`.

---

## N11: chr21-excluded sensitivity (D13)

**Description:** Is DS prediction more than chromosome-21 dosage? Rerun `R3_ca`, `R3_tc`,
`logreg_rna`, `logreg_concat` with `exclude_chr21=True` (same folds, same grid).

**Acceptance criteria:**
- [ ] `docs/nn_v2/chr21_excluded.json`: per-arm BA with and without chr21, paired
      difference with donor bootstrap CI.
- [ ] One-paragraph reading in `LADDER.md` (no mechanism language).

**Verification:** fold-file count; `tests/test_nn_inputs.py` chr21 test still passes.

**Files:** runner flag only (`--exclude-chr21`), `docs/nn_v2/chr21_excluded.json`.

---

## N12: Init-seed and sampling-seed sensitivity (D9)

**Description:** Model seeds 0–4 for `R3_ca`, `R3_tc` (fixed grid choice from seed 0 per
fold, no re-search); sampling seeds {22, 23, 24} at seed 0.
Use the same pooled-donor estimand (existing `initialization_primary_sensitivity` pattern).

**Acceptance criteria:**
- [ ] `docs/nn_v2/seed_sensitivity.json`: per-seed primary contrast + CI; spread vs margin.

**Verification:** fold-file count.

**Files:** runner flags `--model-seed`, `--sampling-seed`; `docs/nn_v2/seed_sensitivity.json`.

---

## N13: Held-out faithfulness interventions (D9, [B11])

**Description:** Test whether routing/attention/MIL actually drive predictions. Apply to
outer-test donors only, using the saved fold models (save state_dicts in N10 under
`reports/generated/nn_20260923/ladder/models/`; if absent, refit fold models with the
recorded grid point — deterministic).

**Interventions (each vs unmodified prediction on same donors):**
| ID | Applies to | Manipulation | Reference value |
|---|---|---|---|
| I1 | all fusion | ablate ATAC branch: replace `z_A` by train mean of `z_A` | outer-train mean |
| I2 | all fusion | ablate RNA branch similarly | outer-train mean |
| I3 | CA, gated, program-CA | within donor × author_cell_type, permute ATAC rows (breaks pairing, keeps marginals) | 20 permutation draws |
| I4 | CA, program-CA | attention knockout: replace attention context with its outer-train mean | outer-train mean |
| I5 | MIL arms | replace attention pooling with uniform mean pooling | — |
| I6 | gated | clamp routing to [1,0], [0,1], [0.5,0.5] (existing `route_override`) | — |
| NC | all | identity permutation (no-op) must give Δ = 0 exactly | — |
| PC | N4 S5/S4 models at δ=1.0 | I3 must reduce planted-task BA if the model used pairing | — |

Metrics: Δ donor BA, Δ donor log-loss, fraction of held-out cells whose cell-level
prediction flips; donor-bootstrap CI for Δ.

**Script:** `scripts/run_nn_v2_faithfulness.py`. Output `docs/nn_v2/faithfulness.json` +
table in `docs/nn_v2/FAITHFULNESS.md` with the rule: an attention/gate readout may be
described as "used by the model" only if its intervention Δ log-loss CI excludes 0.

**Acceptance criteria:**
- [ ] NC exact zero; all applicable cells of the table filled or marked N/A with reason.

**Verification:** `PY -m pytest -q tests/test_nn_faithfulness.py` (synthetic model where
ATAC is unused → I1 Δ ≈ 0; I2 large).

**Files:** `scripts/run_nn_v2_faithfulness.py`, `tests/test_nn_faithfulness.py`,
`docs/nn_v2/faithfulness.json`, `docs/nn_v2/FAITHFULNESS.md`.

---

## N14: Nuisance-probe diagnostics (R2 rejection rule)

**Description:** Held-out embedding probes: for R1 vs R2 vs R3 (CA and TC), fit
`LogisticRegression` on outer-train cell embeddings predicting `batch_seq` and `library`
**within each disease group**, score on outer-test cells (batches seen in train only);
also linear R² for QC columns. Report DS-signal retention (donor BA of the same fold).

**Acceptance criteria:**
- [ ] `docs/nn_v2/nuisance_probe.json`; R2 rejection decision recorded per plan §4.2.

**Verification:** `tests/test_nn_nuisance.py` probe helper test.

**Files:** `scripts/run_nn_v2_nuisance_probe.py`, `docs/nn_v2/nuisance_probe.json`.

---

## Checkpoint B (after N10–N14)

- [ ] Primary contrast + CI + margin decision saved; reproduction check recorded.
- [ ] Faithfulness NC = 0; rung decisions recorded; all tests pass.

---

## N15: Out-of-fold per-cell score export

**Description:** For `R3_ca`, `R3_tc`, `R4_ca` (and `R1_ca` for comparison): for every
outer-test cell, per-cell logit `s_i`, MIL attention `a_i` (normalized within donor bag),
gated weights if any; average across the 5 repeats (each cell is test once per repeat).
Also per-cell chr21 dosage = mean scaled log-normalized expression of chr21 genes
(train-fit scaler), `log1p(nCount_RNA)`, `log1p(nCount_ATAC)`.

**Output:** `reports/generated/nn_20260923/spectrum/cell_scores.csv.gz` (cell_id, donor,
label, author_cell_type, cell_class, dev_PCW, arm, s_mean, s_sd, a_mean, chr21_dosage,
depth cols); compact donor×cell-type means to `docs/nn_v2/donor_celltype_scores.csv.gz`.

**Acceptance criteria:**
- [ ] Every sampled cell appears exactly 5 times per arm before averaging (assert).

**Files:** `scripts/export_nn_v2_cell_scores.py`.

---

## N16: Cell-state spectrum analysis (D2)

**Description:** Donor-unit readout of where DS signal lives.

**Analyses (`scripts/analyze_nn_v2_spectrum.py`, NumPy/SciPy only):**
1. Per author cell type (eligible: ≥ 20 cells in ≥ 8 donors per group): donor mean `s`;
   DS − CON difference; 2,000-draw donor bootstrap CI; 10,000 donor-label permutation
   p (permute labels among donors, stratified by `stage` column PCW11_12/13_16/17_20);
   Holm across eligible types.
2. Same for MIL attention mass share per cell type (DS vs CON).
3. Confound checks per cell type: Spearman of donor mean `s` with donor mean chr21
   dosage, with `dev_PCW`, with mean `log nCount_RNA`/`log nCount_ATAC`; partial
   residual: regress donor mean `s` on dev_PCW + depth (OLS via numpy lstsq, within cell
   type, donor rows) and repeat test 1 on residuals (label: sensitivity).
4. Compare to chr21-excluded model (N11) scores if exported (repeat N15 for that arm;
   if skipped, NOT_NEEDED with reason).
5. Composition context: donor-level cell-type fractions DS vs CON (descriptive only).

**Output:** `docs/nn_v2/spectrum.json`, `docs/nn_v2/SPECTRUM.md` (one table + ≤ 10-line
reading; words allowed: "associated", "carries model signal"; forbidden: "causes",
"mechanism", "biomarker").

**Acceptance criteria:**
- [ ] Table covers all eligible types with Holm-adjusted p; exclusions listed.

**Verification:** `tests/test_nn_spectrum.py` (synthetic donors with a planted shift in
one cell type → only that type significant after Holm).

**Files:** `scripts/analyze_nn_v2_spectrum.py`, `tests/test_nn_spectrum.py`,
`docs/nn_v2/spectrum.json`, `docs/nn_v2/SPECTRUM.md`.

---

## N17: Routing/attention description by cell type

**Description:** Descriptive only, gated by N13. Per cell type: mean gated routing weight
(RNA vs ATAC) for `R3_gated`; CA attention entropy; for `R4_ca` the mean k_R × k_A
program-module attention matrix per cell type with top genes/regions per token (from N8
annotation). Each readout tagged `USED_BY_MODEL` or `NOT_SHOWN_USED` using N13 results.

**Output:** `docs/nn_v2/ROUTING_ATTENTION.md` + `routing_attention.json`.

**Acceptance criteria:**
- [ ] Every readout carries its N13 tag; no biological interpretation of untagged readouts.

**Files:** `scripts/describe_nn_v2_attention.py`.

---

## N18: Fix retry-budget accounting defect (09-21 review defect 1)

**Description:** CLI composes `Budget(Retry(raw))`, so a failed attempt plus its retry is
charged once. Change composition to `Retry(Budget(raw))` semantics: every network attempt
charged against one shared budget; budget exhaustion raises a non-retryable error.

**Acceptance criteria:**
- [ ] Regression test: two 100-byte attempts (first fails) under a 100-byte budget → second
      attempt refused, charged total 200 recorded or refusal raised before transfer.
- [ ] Existing `tests/test_quantify_development_atac.py` passes.

**Verification:** `PY -m pytest -q tests/test_quantify_development_atac.py`.

**Files:** `scripts/quantify_development_atac.py`, `tests/test_quantify_development_atac.py`.

---

## N19: Gene-activity BED + transfer estimate

**Description:** Build a gene-aligned ATAC panel (A9, [B13]) chosen without outcomes.

**Gene list rule (deterministic, label-free):**
1. All chr21 genes with RNA detection in ≥ 1% of cells (computed on the full H5AD raw/X
   via column nnz — read CSR `indices` in chunks; do not densify).
2. The 13 candidate genes: RORB, FOXP1, TLE4, BCL11B, CUX2, NEUROD2, NEUROD6, SOX9, PAX6,
   EOMES, FEZF2, TCF7L2, RORA.
3. Then genes in descending label-free normalized dispersion over all cells (same formula
   as N2) until the transfer estimate reaches 3.5e9 bytes or 1,500 genes.
Window: `[start − 2000, end + 2000]` clipped at 0, canonical chr1–22, X only; BED
zero-based half-open (subtract 1 from 1-based start if `raw/var` starts are 1-based —
decide from a known gene, e.g. compare a gene's start with the union BED convention used by
`scripts/query_fragment_regions.py`; record the decision).

**Transfer estimate:** reuse the estimator that produced the 3,171,155,968-byte estimate in
`configs/atac_tiebreak_measurement_contract_2026-09-21.json` (`grep -rn "estimat" scripts
src | head`). If no reusable function exists, implement
`scripts/estimate_fragment_transfer.py`: merged BGZF chunk spans from the local `.tbi`
(reuse the index parser in `scripts/query_fragment_regions.py`), each rounded up to the
reader's window size, summed. Validate: estimator on the tie-break union BED must be within
1% of 3,171,155,968.

**Output:** `configs/nn_gene_activity_2026-09-23.bed`, `.json` (rule, gene list, estimate,
validation).

**Acceptance criteria:**
- [ ] Estimator validation within 1%; estimate ≤ 3.5e9 bytes.

**Files:** `scripts/build_gene_activity_bed.py`, optional
`scripts/estimate_fragment_transfer.py`, `tests/test_nn_gene_activity.py`.

---

## N20: Bounded gene-activity quantification (only network step)

**Preconditions:** N18 DONE, N19 DONE, free disk ≥ 11 GiB, `pgrep -fl quantify` empty.

**Command (background, record PID):**
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts nohup $PY scripts/quantify_development_atac.py \
  --regions-file configs/nn_gene_activity_2026-09-23.bed \
  --index-path SRC_WT/reports/generated/development_region_set_20260921/fragment.tbi \
  --obs-h5ad <H5AD> --count-mode fragment --unknown-policy error --workers 8 \
  --transport-retries 6 --total-max-bytes 3500000000 \
  --counts-out reports/generated/nn_20260923/gene_activity/counts \
  --out reports/generated/nn_20260923/gene_activity/quantify.json \
  > reports/generated/nn_20260923/gene_activity/run.log 2>&1 &
```
(substitute absolute paths; check `--help` for the exact retry flag name first.)

**Acceptance criteria:**
- [ ] quantify.json: all regions complete joins, 0 truncated, 0 unknown barcodes, total
      charged bytes ≤ 3.5e9; ordered-cells sha256 equals H5AD obs order.
- [ ] Build manifest + acceptance with existing `scripts/build_real_paired_input_manifest.py`
      and `scripts/check_real_paired_acceptance.py` (new requirements JSON
      `configs/nn_gene_activity_acceptance_requirements_2026-09-23.json`) → ACCEPTED.

**On failure:** one retry after 30 min for transport errors only; then
`BLOCKED:acquisition:<log>`; N21 becomes BLOCKED:upstream N20. Never download the whole
fragment file; never raise the budget.

**Files:** configs + `docs/nn_v2/gene_activity_measurement.json`.

---

## N21: Gene-aligned rerun on gene-activity ATAC

**Description:** With RNA gene g and ATAC gene-activity g sharing identity, build
`GeneAlignedCrossAttention` (tokens = the ≤1,500 panel genes; RNA token value = scaled
expression of g, ATAC token value = TF-IDF of g's window; token embedding = value · E_mod
+ gene identity embedding shared across modalities; RNA tokens attend to ATAC tokens with
a band restricted to the same gene ± k nearest genes by genomic position, k=5, via an
attention mask) and a matched token-concat. Train under R3 settings (MIL+adv+nce) with the
frozen grid. Also rerun `R3_ca`, `R3_tc`, `logreg_concat` with view B = gene-activity
matrix (all features, train-only scaling). Separate amendment config
`configs/nn_protocol_v2_amendment_gene_activity.json` written before fitting; results are
**secondary** (primary stays N10).

**Acceptance criteria:**
- [ ] `docs/nn_v2/gene_activity_results.json` + section in `LADDER.md`; N13 I1/I3/I4 run for
      the new CA arm.

**Verification:** `tests/test_nn_gene_aligned.py` (mask correctness, shapes).

**Files:** `src/p22/models/gene_aligned.py`, runner flag `--atac-matrix/--atac-bed`,
`tests/test_nn_gene_aligned.py`.

---

## N22: Results doc + unsent professor note

**Description:** `docs/nn_v2/NN_V2_RESULTS_2026-09-23.md` (≤ 2,500 words):
1. Plain-language conclusion first (5–8 lines): what the NN study found; primary contrast
   with CI and margin decision; whether DS signal survives chr21 exclusion; which cell
   types carry model signal; what faithfulness showed.
2. Professor-direction coverage table D1–D13 (plan §1): status DONE/PARTIAL/BLOCKED +
   evidence path.
3. Planted benchmark answer to "which scenario favours cross-attention vs MLP".
4. Refinement ladder with rung decisions; parameter counts.
5. Limitations: 30 donors, internal only, same-cohort annotations, panel not regulatory
   (unless N21 ran), no external validation, attention ≠ explanation.
6. Exact replay commands, input/protocol hashes, git HEAD, runtime.
Also `docs/nn_v2/PROFESSOR_NOTE_UNSENT.md` (≤ 350 words, no immigration language, no
claims beyond results). Do not send anything.

**Acceptance criteria:**
- [ ] Every number in the doc traceable to a JSON under `docs/nn_v2/`.
- [ ] Only §6 citations used.

---

## N23: Final verification

- [ ] `PY -m pytest -q -x` full suite once; record pass count.
- [ ] `ruff check src tests scripts` on new/changed files clean.
- [ ] `git status --short` shows no stray large files (tracked additions < 200 KB each).
- [ ] Status table complete; final label `NN_ASSIGNMENT_COMPLETE` or
      `NN_ASSIGNMENT_PARTIAL_BLOCKED` written at the top of `NN_V2_RESULTS_2026-09-23.md`.

---

## Paper phase N24–N34

Full IF/ELSE, word limits and acceptance rules: `tasks/nn/decision_tree.md`, sections
`N24:`–`N34:`. Shared constraints:
- Draft source: `paper/draft.md` (markdown, pandoc citations `[@key]`), figures in
  `paper/figures/`, ledger `paper/claims.csv`, checker `paper/check_paper.py`,
  figure script `paper/make_figures.py`.
- Cite ONLY keys in `paper/refs_frozen.bib` (18 verified entries). Never edit that file.
- Numbers ONLY from `docs/nn_v2/*.json` and `configs/nn_*.json`; every number traced in
  `paper/claims.csv`.
- One section per iteration. Each iteration ends with `python paper/check_paper.py`
  once it exists (N31 onward).
- No new experiments in the paper phase (decision_tree G9).
- Audience: advisor and reviewers. No immigration, career or funding language.

**Acceptance (phase):** `paper/draft.md` complete with all sections; checker passes;
`paper/self_review.md` exists; vault copy made (or BLOCKED with reason).

---

## N10 split (v3, agy driver). N10 is DONE when N10a–N10d are all DONE (driver roll-up).

The GNHF/DeepSeek attempt at N10 lost its unsaved runner five times. In v3 the driver runs every
command; you write code and request runs via `tasks/nn/run/<ID>.json` (see the lane preamble).

## N10a: Ladder runner + summarizer code, synthetic end-to-end test

**Files:** `scripts/run_nn_v2_comparison.py`, `scripts/summarize_nn_v2.py`, `tests/test_nn_runner.py`.
Build on `src/p22/eval/nn_factory.py` (N9), `src/p22/data/nn_inputs.py` / `nn_fold.py`, the frozen
`configs/nn_protocol_v2_2026-09-23.json`, and reuse `scripts/run_real_paired_comparison.py::_indices`
fold logic. Runner flags: `--protocol`, `--out`, `--arms`, `--repeats`, `--folds`, `--resume`,
`--workers`, `--exclude-chr21`, `--model-seed`, `--sampling-seed`, `--synthetic` (tiny generated
inputs for tests). One JSON per (repeat, fold, arm) under `<out>/folds/`; state_dict + fold
preprocessing evidence under `<out>/models/<arm>/r<rep>_f<fold>.pt|.json`; `<out>/run.json` with
`folds_expected`, `folds_done`, `failures`. Summarizer writes `ladder_summary.json` (fields below)
from any `<out>` directory.
**Acceptance (driver-run):** `PY -m pytest -q tests/test_nn_runner.py tests/test_nn_factory.py`
passes; the test runs the runner with `--synthetic` on 6 donors × 2 folds for every arm, checks
leakage assertions, `--resume` skipping, and the summarizer output keys.

## N10b: Smoke fold, reproduction check, timing probe

Request one real run: repeat 0, fold 0, all arms, `--out reports/generated/nn_20260923/ladder_smoke`,
`--workers 4`. Then request the historical reproduction (plan N10 "Before the full run" step 1).
Write `docs/nn_v2/ladder_timing.json` with `smoke_seconds`, `projected_hours` (full 5×5 at 14
workers), `reproduction` (`{"estimate": ..., "expected": -0.02, "abs_diff": ...}`), `cap` used.
If `projected_hours` > 6, write `configs/nn_protocol_v2_amendment_cap512.json` first (decision tree N10).
**Acceptance:** `check_evidence.py docs/nn_v2/ladder_timing.json projected_hours reproduction cap`.

## N10c: Full ladder run (background)

Request the full run in the background: `--out reports/generated/nn_20260923/ladder --workers 14
--resume`. The driver starts it, waits, and reports its log. If it dies, request it again with
`--resume` (never delete finished folds). When it ends, copy `<out>/run.json` to
`docs/nn_v2/ladder_run.json`.
**Acceptance:** `check_evidence.py docs/nn_v2/ladder_run.json folds_expected folds_done --eq folds_expected folds_done`.

## N10d: Summary, primary contrast, outcome label

Request `scripts/summarize_nn_v2.py --run reports/generated/nn_20260923/ladder --out docs/nn_v2`.
`docs/nn_v2/ladder_summary.json` must contain `primary` (`model`, `reference`, `estimate`, `ci`,
`margin`, `advantage`), `outcome` (decision tree N10 labels), `secondary`, `rung_decisions`,
`per_arm`. Write `docs/nn_v2/LADDER.md` (≤ 60 lines, plain-language reading first).
**Acceptance:** `check_evidence.py docs/nn_v2/ladder_summary.json primary.estimate primary.ci outcome rung_decisions per_arm`.
