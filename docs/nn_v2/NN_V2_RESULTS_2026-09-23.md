# NN-v2 results — 2026-09-23

**Final label: `NN_ASSIGNMENT_COMPLETE`.** Mandatory N10–N17 accepted; optional N21 secondary `GA_B_NULL`; N23 verification passed; N34 final paper verification passed. **v5 validity (V1–V4) + P1–P6 DONE** against canonical `ladder_v3` after a shared-path control-fit fix; primary outcome remains `B_NULL`. **v6 sensitivities (X1–X4)** add chr21-forced representation, per-fold primary contrast, and detectability without changing the primary endpoint; external validation remains deferred (T13). Claim limits below remain in force. Study label stays `STUDY_PARTIAL` (no external validation). P4 results refresh (this doc + unsent note); P5 coverage table in `v5/PROFESSOR_UPDATE_v5.md`; v6 unsent note in `v6/PROFESSOR_UPDATE_v6.md`; P6/X6 paper `DRAFT_V3_COMPLETE` (`check_paper` 5/5; vault `paper-nn/` synced; engineering suite check pending).

**Claim limits (first lines).** (1) Planted pairing positive control (PC) is `N/A` — no saved S4/S5 δ=1.0 models under `ladder_v3`; I3 `CA_PAIRING_UNUSED` is reported but pairing-use claims stay provisional without PC sensitivity (`docs/nn_v2/faithfulness.json`). (2) N15 chr21-excluded cell-score export is **EXPORTED** (60k rows); N16 chr21-score compare is `COMPARED` and also `SPECTRUM_NULL`; P3 primary on those scores is `SPECTRUM_NULL` (`docs/nn_v2/spectrum.json`, `docs/nn_v2/v5/spectrum_chr21_excluded.json`). (3) N21 gene-activity is **secondary only**; never independent external validation (`docs/nn_v2/gene_activity_results.json`). (4) Planted benchmark has **zero** `CA_FAVOURED` regimes (N4 S0–S5 and v5 P2 gene-matched S6) — no F2 planted support for a cross-attention-favoured headline (`docs/nn_v2/planted_benchmark.json`, `docs/nn_v2/v5/planted_gene_aligned.json`). (5) Attention/routing readouts are all `NOT_SHOWN_USED` (I4/I6 CIs include 0); do not treat attention as explanation [B11].

## 1. Plain-language conclusion

On the accepted real-data ladder (`ladder_v3`, 450/450 folds, verifier `PASS`), cross-attention does **not** beat matched token-concat at the primary rung: R3_ca − R3_tc donor balanced-accuracy estimate **0.0267**, 95% CI **[−0.0267, 0.0770]** (summary) / recomputed **[−0.0250, 0.0768]** (verifier `primary_recomputed.ci`), practical margin 0.07 not met → outcome **`B_NULL`**. Secondary label **`LINEAR_SUFFICIENT`**: RNA logistic pooled BA 0.427 exceeds R3_ca 0.400. Model-free chr21 dosage remains perfect (AUROC **1.0**, BA 1.0). After dropping chr21 features, every scored arm stays ≤ 0.55 BA → **`DOSAGE_DOMINATED`**. No eligible cell type shows a Holm-significant DS−CON difference in donor-mean R3_ca scores → **`SPECTRUM_NULL`** (9 eligible types; same call on chr21-excluded scores). Faithfulness: NC Δ = 0 exact; tags **`CA_PAIRING_UNUSED`**, **`ATAC_USED`** (I1 log-loss CI excludes 0 on R3_tc; R3_gated I1 includes 0 on v3). Seed spreads are modest (`SPREAD_ONLY`; model 0.073, sampling 0.033). No complex-model superiority claim; majority / learned-arm **pooled** BA/AUROC caveats retained — report **per-fold AUROC** alongside pooled metrics (see §5).

## 2. Professor-direction coverage (plan §1, D1–D13)

| ID | Direction | Status | Evidence |
|---|---|---|---|
| D1 | MIL / adversary / InfoNCE rungs | DONE | `ladder_summary.json` rung_decisions; `nuisance_probe.json` (`R2_REJECTED`) |
| D2 | Cell-state spectrum | DONE | `spectrum.json` (`SPECTRUM_NULL`); `v5/spectrum_chr21_excluded.json` (`SPECTRUM_NULL`); `routing_attention.json` |
| D3 | Program tokens + gene-aligned | DONE (secondary GA + P2) | `parameter_counts.json`; `gene_activity_results.json` (`GA_B_NULL`); `v5/planted_gene_aligned.json` (no `CA_FAVOURED`) |
| D4 | No subtype classification target | DONE | `sampling_cap1000_seed22.json` |
| D5 | Equal supervision / param match | DONE | `parameter_counts.json` (R3_tc_parammatched rel. err 1.10%) |
| D6 | Planted CA vs simple models | DONE | `planted_benchmark.json` + `v5/planted_gene_aligned.json` (no `CA_FAVOURED`) |
| D7 | Concat baselines | DONE | `ladder_summary.json` `logreg_concat`; planted concat arms |
| D8 | Donor-aware sampling | DONE | `sampling_cap1000_seed22.json` |
| D9 | Faithfulness + seeds | DONE (PC N/A) | `faithfulness.json`; `seed_sensitivity.json` |
| D10 | Named paper precedents | DONE | `PROTOCOL_FREEZE.md`; this doc §9 cites only [B1]–[B14] |
| D11 | Clear written conclusion | DONE | §1; no Tasic rerun |
| D12 | No unverified GenAI citations | DONE | §9 keys only; no novelty claim |
| D13 | Dosage / beyond-dosage | DONE | `chr21_excluded.json` + ROBUSTNESS (`DOSAGE_DOMINATED`); dosage arm in ladder; P3 spectrum |

## 3. Planted benchmark: which scenario favours cross-attention?

From `docs/nn_v2/planted_benchmark.json` (400 records; 5 models × 5 folds; synthetic labels only): **no regime is `CA_FAVOURED`**. At δ=1.0:

| scenario | regime | CA BA | best non-attention | CA − best |
|---|---|---|---|---|
| S1 RNA-additive | LINEAR_SUFFICIENT | 1.0 | 1.0 | 0.0 |
| S2 ATAC-additive | LINEAR_SUFFICIENT | 1.0 | 1.0 | 0.0 |
| S3 both-additive | LINEAR_SUFFICIENT | 1.0 | 1.0 | 0.0 |
| S4 context interaction | LINEAR_SUFFICIENT | 0.8667 | 0.9 | −0.0333 |
| S5 pairing-only | MLP_FAVOURED | 0.9667 | 1.0 (`gated_fusion`) | −0.0333 |

S0 stayed in [0.35, 0.65]; S1 δ=1.0 all models ≥ 0.9. S5 did not collapse to chance (`s5_delta1_within_0p05_of_chance` = false). Reading: linear concat solves additive planted shifts; pairing-only favours gated/MLP fusion, not cross-attention. No biological claim. Gene-matched interaction (P2 / §6) likewise yields no `CA_FAVOURED`.

## 4. Refinement ladder and parameter counts

Canonical run: `reports/generated/nn_20260923/ladder_v3` (`folds_done=450`, `failures=[]`; named in `docs/nn_v2/v5/CANONICAL_LADDER.txt`). Summary rebuilt by `scripts/summarize_nn_v2.py`; gate `docs/nn_v2/ladder_verification.json` **PASS**, `problems=[]`. (`ladder_v2` retained on disk; not canonical after the v5 control-fit fix.)

| Field | Value | JSON |
|---|---|---|
| Outcome | `B_NULL` | `ladder_summary.json` `outcome` |
| Primary | R3_ca−R3_tc = 0.0267; CI [−0.0267, 0.0770]; margin 0.07; advantage false | `primary` |
| Secondary | `LINEAR_SUFFICIENT` (R3_ca vs logreg_rna) | `secondary`, `secondary_contrasts` |
| Rung decisions | R1/R2/R3 accepted; R4 descriptive | `rung_decisions` |
| chr21 dosage | BA 1.0; AUROC 1.0 | `per_arm.chr21_dosage` |

Selected pooled BAs (`ladder_summary.json` `per_arm`): R3_ca 0.400, R3_tc 0.373, R3_gated 0.367, logreg_rna 0.427, logreg_concat 0.413, majority 0.300 (pooled-BA artefact; use `mean_per_fold_ba` / per-fold AUROC — verifier note + §5).

Parameter counts (`parameter_counts.json`): R0_ca/tc 359426/355202; R1 367876/363652; R2/R3 384250/380026; R4 29970/25746; R3_tc_parammatched 380026 (within 5%); R3_gated 314044; latent_pca_lsi_head 16836.

Downstream (all bound to `ladder_v3`):

| Task | Call | Evidence |
|---|---|---|
| N11 | `DOSAGE_DOMINATED` (no-chr21 BA: R3_ca 0.333, R3_tc 0.373, logreg_rna 0.407, logreg_concat 0.400) | `chr21_excluded.json`, `ROBUSTNESS.md` |
| N12 | `SPREAD_ONLY` (model spread 0.073; sampling 0.033; not `SAMPLING_SENSITIVE`) | `seed_sensitivity.json` |
| N13 | `CA_PAIRING_UNUSED`, `ATAC_USED`; NC exact zero; PC N/A | `faithfulness.json` |
| N14 | `R2_REJECTED` / `PROBE_DROP_INSUFFICIENT` | `nuisance_probe.json` |
| N15 | 120000 OOF rows; chr21-excluded 60000 EXPORTED; 5 appearances/arm asserted | `cell_scores_export.json` |
| N16 | `SPECTRUM_NULL` (9 eligible; 0 Holm-sig); chr21 compare `COMPARED`/`SPECTRUM_NULL` | `spectrum.json` |
| N17 | all readouts `NOT_SHOWN_USED` | `routing_attention.json` |
| N21 | secondary `GA_B_NULL` (GA_ca−GA_tc 0.0533, CI [−0.0527, 0.1572]); tags GA_ATAC_UNUSED_OR_NULL, GA_CA_PAIRING_UNUSED, GA_ATTENTION_NOT_SHOWN_USED | `gene_activity_results.json` |

## 5. Per-fold metrics and validity (v5 V1–V4)

**V1 — Per-fold metrics.** From every fold file in the canonical run (`docs/nn_v2/v5/per_fold_metrics.json`, 18 arms): majority per-fold BA is exactly **0.5** in all 25 folds (constant predictor check). On `ladder_v3`, learned arms show a pooling gap — per-fold AUROC means above or near chance while pooled AUROC stays below chance:

| Arm | Per-fold AUROC mean | Per-fold AUROC SD | Pooled AUROC |
|---|---:|---:|---:|
| R3_ca | 0.656 | 0.293 | 0.366 |
| R3_tc | 0.658 | 0.236 | 0.302 |
| logreg_rna | 0.534 | 0.244 | 0.390 |
| majority | 0.500 | 0.000 | 0.300 |
| chr21_dosage | 1.000 | 0.000 | 1.000 |

**V2 — Positive control.** Forced-chr21 union with HVGs, same fold prep/train/aggregate path (`docs/nn_v2/v5/positive_control.json`): logreg pooled donor AUROC **0.924** (≥ 0.9); orientation Spearman (pred DS prob vs donor chr21 share) **0.648**; default HVG kept ~31/538 chr21 genes. Shared-path fix: sklearn controls now fit on the full outer-train split (previously only the inner-train third).

**V3 — Below-chance diagnosis.** Verdict **`PIPELINE_BUG_FIXED`** (`docs/nn_v2/v5/below_chance_diagnosis.json`, `docs/nn_v2/v5/BELOW_CHANCE.md`): V2 required a shared-path fix, so the pre-fix ladder could not remain canonical. Separately, pooling fold-specific scores across stratified folds still depresses pooled AUROC relative to per-fold means; report both. Predictions were never flipped to look better.

**V4 — Canonical rebuild.** Full ladder into `reports/generated/nn_20260923/ladder_v3` (450/450); `verify_ladder` **PASS**; primary still `B_NULL` (estimate +0.0267, CI includes 0). `CANONICAL_LADDER.txt` points at `ladder_v3`; V1 per-fold metrics regenerated on v3. Downstream N11–N17 refreshed under P1 (`*_v3` paths).

## 6. P2 — gene-aligned planted interaction (D3)

Added planted regime S6: gene-level RNA×ATAC interaction on matched genes (`docs/nn_v2/v5/planted_gene_aligned.json`; 30/30 ok; δ = 0.5 and 1.0; 5 folds). Models: gene-aligned CA, gene-aligned token-concat, feature-concat MLP.

| cell | regime | gene_aligned_ca | gene_aligned_tc | rna_atac_concat | CA − best non-CA |
|---|---|---:|---:|---:|---:|
| S6@0.5 | `LINEAR_SUFFICIENT` | 1.0 | 0.70 | 1.0 | 0.0 |
| S6@1.0 | `LINEAR_SUFFICIENT` | 1.0 | 0.8667 | 1.0 | 0.0 |

**`any_ca_favoured` = false** (N4 `CA_FAVOURED` rule). Null is acceptable; no biological claim. Gene-aligned token-concat is weaker than CA and feature-concat MLP on this planted interaction.

## 7. P3 — dosage-aware spectrum on chr21-excluded scores (D2)

Repeated N16 spectrum analysis on per-cell scores from chr21-excluded models (`docs/nn_v2/v5/spectrum_chr21_excluded.json`; arm R3_ca; donor unit; Holm across eligible types). Prerequisite N11 label `DOSAGE_DOMINATED`. Label **`SPECTRUM_NULL`** (9 eligible author cell types; 0 Holm-significant DS−CON differences). Reading ≤ 40 lines: `docs/nn_v2/v5/SPECTRUM_CHR21_EXCLUDED.md`. No mechanism language.

## 8. chr21-forced sensitivity

Prespecified sensitivity only (`configs/nn_protocol_v2_amendment_chr21forced.json`): default HVG keeps 31/538 chr21 genes; test whether forcing **HVG ∪ all chr21 genes** changes the R3_ca − R3_tc contrast. Primary endpoint stays `ladder_v3` `B_NULL`. Full 18-arm × 5×5 ladder into `reports/generated/nn_20260923/ladder_v4_chr21forced` (450/450); summary `docs/nn_v2/v6/ladder_v4_summary.json`; verifier **PASS** (no `--write`).

From `docs/nn_v2/v6/ladder_v4_summary.json` / `docs/nn_v2/v6/chr21_forced_compare.json`: pooled R3_ca − R3_tc donor BA estimate **0.060**, 95% CI **[0.011, 0.113]**, margin 0.07 unmet → label **`CHR21FORCED_D_SMALL_POSITIVE`**. Per-fold AUROC means (v3 → chr21-forced): R3_ca 0.656 → 0.780; R3_tc 0.658 → 0.816; logreg_rna 0.534 → 0.983; chr21_dosage 1.0 → 1.0. Linear arms gain most; CA−TC gap stays below the 0.07 advantage margin. Reading: `docs/nn_v2/v6/CHR21_FORCED.md`.

## 9. Per-fold primary contrast

Prespecified sensitivity (`docs/nn_v2/v6/per_fold_contrast.json`): for each of 25 folds, R3_ca − R3_tc donor BA (and AUROC); mean over folds; 95% CI by donor-cluster bootstrap over folds within repeats (1,000 draws, seed 22).

| Ladder | Metric | Mean-fold estimate | 95% CI |
|---|---|---:|---|
| `ladder_v3` (canonical) | donor_ba | 0.0160 | [−0.0158, 0.0447] |
| `ladder_v3` | donor_auroc | −0.0021 | [−0.0922, 0.1021] |
| chr21-forced (`ladder_v4`) | donor_ba | 0.0340 | [−0.0176, 0.0699] |
| chr21-forced (`ladder_v4`) | donor_auroc | −0.0359 | [−0.1076, 0.0476] |

Mean-of-per-fold BA on `ladder_v3` is smaller than the pooled primary (0.027) and both CIs include 0 → agrees with `B_NULL`. On chr21-forced, the pooled primary was `D_SMALL_POSITIVE` but the per-fold BA CI still includes 0.

## 10. Detectability

Planted S4-type interaction at 30 donors, 5×5, CA vs TC (`docs/nn_v2/v6/detectability.json`; 125/125 ok). Effect sizes δ ∈ {0.1, 0.25, 0.5, 0.75, 1.0}; detection = fraction of repeats whose donor-bootstrap CA−TC BA CI excludes 0 (threshold 80%).

| δ | detection fraction | mean contrast |
|---:|---:|---:|
| 0.1 | 0.00 | +0.0277 |
| 0.25 | 0.00 | −0.0089 |
| 0.5 | 0.00 | +0.0000 |
| 0.75 | 0.00 | +0.0339 |
| 1.0 | 0.00 | +0.0259 |

**`min_detectable_delta` = null** (not detectable up to δ = 1.0). Reading: `docs/nn_v2/v6/DETECTABILITY.md`. Primary real-data endpoint unchanged.

## 11. Limitations

- 30 donors; internal development cohort only; no external validation (deferred, T13).
- Same-cohort annotations are not independent validation [B14].
- ATAC region panel is prevalence/tie-break ordered, **not** a regulatory panel; N21 gene-activity (500-gene amendment of 548) remains secondary measurement, not external validation [B13].
- Attention is not explanation [B11]; N17 tags follow N13 I4/I6 only.
- R2 adversary fails the held-out probe-drop rule; do not claim technical nuisance erasure.
- Majority / some pooled BA and AUROC values are depressed by pooling fold-specific scores across stratified folds; prefer per-fold AUROC / `mean_per_fold_ba` (§5).
- Detectability: at 30 donors, S4 CA−TC CIs never exclude 0 up to δ = 1.0 (§10); null is the valid outcome.
- Separate from August same-cap and September paired corrected studies (plan §2).

## 12. Citations used

Only plan §6 keys: [B1] Ilse et al.; [B2] Ganin et al.; [B3] van den Oord et al.; [B4] Radford et al.; [B5] Vaswani et al.; [B6] Tsai et al.; [B7] Nagrani et al.; [B8] Hao et al.; [B9] Lee & Seung; [B10] Ashuach / Argelaguet (named exclusions); [B11] Jain / Wiegreffe; [B12] Squair et al.; [B13] Stuart et al.; [B14] Lattke et al. Novelty language: adapted combination of known techniques — not claimed novel.

## 13. Replay commands, hashes, runtime

```bash
export PY=/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python
export PYTHONPATH=src:scripts PYTHONDONTWRITEBYTECODE=1
# Rebuild summary + gate (do not hand-edit JSON)
$PY scripts/summarize_nn_v2.py --run $(cat docs/nn_v2/v5/CANONICAL_LADDER.txt) --out docs/nn_v2
$PY gnhf/verify_ladder.py --run $(cat docs/nn_v2/v5/CANONICAL_LADDER.txt) --summary docs/nn_v2/ladder_summary.json --write
$PY gnhf/check_evidence.py docs/nn_v2/ladder_verification.json verdict
```

| Item | Value |
|---|---|
| Canonical ladder | `reports/generated/nn_20260923/ladder_v3` (`docs/nn_v2/v5/CANONICAL_LADDER.txt`) |
| Protocol file | `configs/nn_protocol_v2_2026-09-23.json` |
| Protocol sha256 (file bytes) | `98b169f68710d66e34d44728d72c2aadd01c60cfe351c2924e7660cc8a249154` |
| Protocol freeze canonical sha256 | `80931bfc05c403804db47f53b02b29989204a6c04720476cb752dd62968b7161` (`PROTOCOL_FREEZE.md`) |
| Inputs manifest sha256 | `45d9b540d2a1c906879867003a488e7a54a9e4818a82f776b91643f77ae9f766` |
| GA amendment sha256 | `5604131134339dadf4000ec8b4cf59543ce5e7737bfcc8f928730c1ab84d610c` |
| Ladder run | 450/450; failures `[]` (`ladder_v3/run.json`) |
| Smoke timing | 77.7 s; historical reproduction −0.0200 abs_diff ≈ 0 (`ladder_timing.json`) |
| Cell scores sha256 (ladder_v3 export) | `9e1302a9c032b40b63e3db14d88ca5ee9550b26a6046b2db3cff95a7e2e2428f` |
| GA counts / bed sha256 | `8cce7bd7…` / `946fd000…` (`gene_activity_results.json`) |

Full wall-clock for the 450-fold ladder was not stored in `run.json` (keys: folds_expected/done/failures only).
