# Lane B — prospective benchmark and model-design review

**Status:** Lane B acceptance met (DRAFT / NO FITS).  
**Lane owner outputs only.** No fits, downloads, source edits, scientific-JSON edits, status/MOM/paper/packet edits, or other-lane writes.  
**Base evidence commit:** `808fa734a8dc2d89d34853204251bd9decea2a06` (`gnhf/read-users-anuragdan-caf4c8`).  
**Written:** 2026-09-30T00:27:57Z (UTC).  
**Stop reason:** selected one prospective protocol draft with gates/falsifier/fit budget; rejected one alternative; S7-v1/v2 labels untouched.

All protocol text below is **DRAFT / NO FITS**. Old S7-v1 (`INVALID`) and S7-v2 (`INVALID`) remain immutable; never relabel.

---

## Provenance and inspected artifacts

| Artifact | Role |
|---|---|
| Vault July 2 MOM | Fair/equal-supervision direction (apple-to-apple) |
| Vault July 21 MOM | Complex differentiating benchmark; concat baseline; independent modalities |
| `tasks/nn/plan.md` §1 D1–D13, §6 B1–B14 | Direction map + frozen bibliography only |
| `docs/nn_v2/PLANTED_BENCHMARK.md`, `planted_benchmark.json` | Frozen N4 S0–S5 outcomes |
| `docs/nn_v2/v5/planted_gene_aligned.json` | Gene-aligned S6 secondary (no CA_FAVOURED) |
| `docs/nn_v2/s7/S7_RESULT.md` | S7-v1 `INVALID` (split-class blocker) |
| `docs/nn_v2/s7_v2/S7_V2_RESULT.md`, `CODEX_REVIEW_20260929.md` | S7-v2 `INVALID`; pooled vs mean-fold mismatch |
| `tasks/nn/s7_v2/BENCHMARK_SPEC.json` | Frozen v2 generative equation and intended pooled null |
| `src/p22/eval/planted_signal.py` | S0–S5 / `plant_covariance` / within-donor ATAC shuffle |
| `src/p22/eval/s7_screen.py` | Implemented null gate uses mean-fold BA (mismatch) |
| `docs/nn_v2/FAITHFULNESS.md` | Real-label R3_ca `CA_PAIRING_UNUSED`; PC N/A on ladder |

Commands used (read-only): `git rev-parse HEAD`; `rg` on July MOM; inspect JSON/MD/source paths above. No model fits.

---

## B0. Source and model taxonomy (adapted, not novel)

Cite only the frozen bibliography in `tasks/nn/plan.md` §6. No invented novelty.

| Component | Primary source | Implemented adaptation | Supervision / target |
|---|---|---|---|
| Cross-attention fusion | Vaswani et al. 2017 [B5]; multimodal use Tsai et al. 2019 [B6], Nagrani et al. 2021 [B7] | Paired RNA/ATAC token encoders + multi-head cross-attention; matched token-concat control | Donor fake or real binary label; cell then donor aggregation |
| Token / feature concat | Engineering baseline (Jul 21 To-Do 6); not a paper claim | Same encoders, concat fused tokens or raw views | Same labels/splits/budget |
| Gated fusion | Related to modality weighting precedent Hao et al. 2021 [B8] (WNN-style weighting cited as known precedent, not claimed novel) | Learned gate between views | Same |
| Linear controls | Standard logistic regression | `logreg_rna`, `logreg_atac`, `logreg_concat` | Same |
| Attention MIL pooling | Ilse, Tomczak, Welling 2018 [B1] | Gated attention pool over donor bags (ladder rungs; not required for S7 screen path) | Donor bag loss |
| Conditional nuisance adversary | Ganin & Lempitsky 2015 / Ganin et al. 2016 [B2] | GRL adversary conditioned on disease label (ladder) | Technical library/batch/QC; label protected |
| Pairing / contrastive aux | van den Oord et al. 2018 [B3]; Radford et al. 2021 [B4] CLIP-style framing | Cross-modal InfoNCE on ladder rungs | Pairing of views within cell |
| Program / module tokens | Lee & Seung 1999 NMF [B9] | Train-only NMF programs as tokens (ladder); gene-activity secondary Stuart/Signac-style windows [B13] | Same donor task |
| Faithfulness caveat | Jain & Wallace 2019; Wiegreffe & Pinter 2019 [B11] | Intervention Δ must exclude 0 before “used” language | — |

**What was adapted vs contribution:** each term is an adapted combination under equal budgets. A planned architectural variant is not a contribution without a fair prospective test. MultiVI/MOFA+ remain excluded baselines under plan A14.

---

## B1. Professor benchmark question vs N4 / S7

### July wording (professor sources only)

- **Jul 2 [14:12]:** comparisons must be apple-to-apple on supervision and task setup.
- **Jul 21 [14:02]:** cell-type Tasic scenarios are unfair for differentiating models; ask which scenario would make cross-attention better and which would make MLP better — benchmark verification.
- **Jul 21 [15:04]–[17:39]:** cross-attention combines two different data types so one can look at the other; use concatenation as the simple fusion baseline; find a **complex** case that compares concat vs cross-attention.
- **Jul 21 To-Dos:** identify one complex multimodal benchmark; treat concatenation as required simple fusion baseline; do not claim CA superiority from Tasic.

Worker plans/packets are not new professor instructions.

### Scenario map (what each test actually stresses)

| Scenario | Generative idea | Tests interaction? | Tests pairing? | Single-view / concat shortcut? | CA structurally necessary? |
|---|---|---|---|---|---|
| N4 S0 | Null (identity) | No | No | Chance only | No |
| N4 S1 | Additive RNA mean shift on fake+ | No | No | RNA-only / concat | No — linear sufficient |
| N4 S2 | Additive ATAC mean shift | No | No | ATAC-only / concat | No |
| N4 S3 | Split additive both views | Weak | No | Concat / either view | No |
| N4 S4 | RNA shift when ATAC context high | Yes (threshold) | Partial | Concat can read joint features | No |
| N4 S5 | Pairing-only RNA shift by ATAC sign; donor RNA mean restored | Yes | Yes (marginals matched) | Concat+MLP learns products; linear fails | **No** — N4 label `MLP_FAVOURED` (gated_fusion), never `CA_FAVOURED` |
| S6 gene-aligned | Per-gene RNA×ATAC interaction | Yes | Partial | Concat/MLP | No — prior gene-aligned run not CA_FAVOURED |
| S7 covariance | `RNA=z`, `ATAC=(2y−1)ρz + √(1−ρ²)w` | Yes (signed covariance) | Yes (shuffle destroys cov) | Concat MLP can learn channel products; single-view marginals matched by design | **No guarantee** — S7-v2 rho=1 pooled CA 0.321 < best non-attention `rna_atac_concat` 0.393 |

### Frozen outcomes (evidence, not redesign)

- **N4:** 16/16 cells scored; **zero** `CA_FAVOURED`; S0–S4 `LINEAR_SUFFICIENT`; S5 `MLP_FAVOURED` (gated_fusion BA 1.0 vs CA 0.967 at δ=1.0).
- **S7-v1:** `INVALID` — frozen split put fold-0 test all one fake class; smoke 14/14 `single_class`.
- **S7-v2:** split repaired (55/55); screen 105/105; rho-0 null FAIL; rho-1 `NONE_DETECT` / not CA_FAVOURED; pairing PC `PC_FAIL` (CA ll-drop CI lower ≤ 0); confirmation skipped; cumulative 119 fits. Independent review: **pooled** TC/gated rho-0 BA fail `[0.35,0.65]`; GNHF/T7 cited **mean-fold** TC 0.341667 from `s7_screen.null_check` — protocol/implementation mismatch; both statistics fail; do not promote the run.

**Reading for Q3 (pairing-dependent learning):** a benchmark all competent fusion arms solve does not establish unique attention benefit (Jul 21 + N4 S5). S7 asked whether CA shows finite-budget advantage on covariance vs fair arms; the valid scientific answer under that freeze is not available (`INVALID`), and the available rho-1 numbers do not favor CA.

---

## B2. Two candidate controls (paper only)

### Candidate 1 — CA-advantage remake on covariance / pairing products (**rejected**)

- **Equation:** reuse S7 `plant_covariance` (same latent construction). Hold donor roster, cell IDs, feature selection, train-only transforms, and equal neural budgets constant. Fake labels balanced 16/14; ρ grid {0, 0.5, 1}; positive control = high ρ detectable by some fusion arm; negative = ρ=0 null + within-donor ATAC shuffle.
- **Why CA might differ:** only if attention routing exploited signed cross-view structure better than every fair comparator.
- **Falsifier:** CA − best non-attention < 0.07 or CI rule fails; or any fair concat/gated arm matches CA.
- **Why rejected prospectively:** N4 S5 already shows concat/gated MLP solve pairing-product signals; S7-v2 rho=1 pooled gap CA−best = −0.071. Selecting another “CA must win” batch on the same signal class is circular search after two failures. No new generative claim invented to force CA uniqueness.

### Candidate 2 — Pairing-**use** diagnostic on known covariance plant (**selected**)

- **Equation:** identical S7 generative process (not a new biology claim): for each donor/channel, independent `z,w`; `RNA=z`; `ATAC=(2y_d−1)ρ z + √(1−ρ²) w`; other columns unchanged; generation order by stable `cell_id` (`tasks/nn/s7_v2/BENCHMARK_SPEC.json` generation block; `plant_covariance`).
- **Held constant:** 30 donors, cap/policy from existing NN inputs config, S7-v2 class-quota donor splits, seven arms, matched seeds/budgets, CA/TC parameter gap ≤10% pre-fit check.
- **Label balance:** full-cohort fake 16/14; every outer test fold both classes (v2 quotas).
- **Noise:** ρ=0 null plant; ρ=1 decision cell; ρ=0.5 descriptive only.
- **Positive / negative controls:** (neg) ρ=0 pooled null band; (neg) ρ=1 single-view BA ≤ 0.60; (pos for *pairing use*) within-donor ATAC shuffle raises CA donor log-loss with CI lower > 0 while identity reload matches.
- **Why CA might differ from fair comparators:** secondary only — report CA vs each arm; **primary is not advantage**. Primary asks whether *this CA implementation* uses pairing under a plant where pairing is the planted dependence (Jul 21 faithfulness intent + plan D9).
- **Falsifier (primary):** after valid screen, CA mean donor log-loss drop under 32 within-donor ATAC shuffles has 95% donor-bootstrap CI lower ≤ 0 → `PAIRING_NEGATIVE` (architecture/control pair did not use pairing under budget). Also falsifies any later “CA used cross-view pairing” claim for this protocol ID.

---

## B3. Selection and DRAFT protocol summary

**Selected:** Candidate 2 — protocol ID draft `S8_pairing_use_DRAFT_20260929` (see sibling `DRAFT_PROTOCOL_S8.md`).  
**Rejected:** Candidate 1 (CA-advantage remake).  
**Not selected:** stop-all. Method-**advantage** fits are not justified from Lane B alone; a pairing-use diagnostic remains the smallest non-circular prospective control answering PLAN Q3. Integration I2 may still choose bounded paper over any fit.

### Exact estimand (primary)

Donor-level **pairing sensitivity** of the frozen CA screen checkpoints at ρ=1:  
Δ = mean over held-out donors of [log-loss(shuffle_k) − log-loss(identity)], averaged over predeclared shuffle seeds, then donor-bootstrap CI.

### Exact primary statistic

One statistic only: **mean donor log-loss drop**, 1000-draw donor-cluster bootstrap, seed 22, paired shared draws; success iff estimate > 0 **and** 95% CI lower > 0. BA drop is descriptive only.

### Fair arms (equal information / tuning)

`cross_attention`, `token_concat`, `rna_atac_concat`, `gated_fusion`, `logreg_concat`, `logreg_rna`, `logreg_atac`. Same folds, cells, features, fake labels, inner val rule (donor log-loss), epoch/patience/LR/batch/token/embed/hidden/heads/dropout as N4/S7 neural defaults; no hyperparameter sweep; CA/TC param count within 10% or refuse.

### Sensitivity tests (predeclared)

1. ρ=0 pooled null band (all complete arms).  
2. ρ=1 single-view marginal BA ≤ 0.60.  
3. Checkpoint reload identity `max_abs_diff ≤ 1e-6`.  
4. 32 within-donor ATAC shuffles (seeds 3001–3032); marginal row multiset preserved.  
5. Report mean-fold BA **and** pooled BA side-by-side; **gates use pooled only**.

### Pooled-versus-mean-fold resolution (prospective; do not patch S7)

| Item | Decision for S8 draft |
|---|---|
| Gate statistic | **Pooled donor BA** across the five disjoint outer-test donor sets (30 donors), `balanced_accuracy_score` on pooled labels/preds |
| Descriptive | Mean-fold BA/AUROC reported to expose fold imbalance; **never** used for PASS/FAIL |
| S7-v2 | Leave `INVALID`; documented mismatch (`BENCHMARK_SPEC` said pooled; `s7_screen.null_check` used mean-fold) |
| Null interval `[0.35,0.65]` | **Not reused as-is.** At n=30 the band is historically conventional (N4 S0) but failed on S7-v2 under both statistics without proving leakage vs chance variance. S8 requires a **pre-fit chance calibration**: Monte Carlo of chance donor predictions under the frozen fake-label split (constant-0.5 and/or Bernoulli-0.5, ≥10k draws, no neural fit); gate = each arm’s pooled BA inside the predeclared central 95% of that calibration. If calibration artifacts are missing at freeze time → `INVALID` / no fits |

### Gate order and result precedence

1. Split/preflight class quotas + coverage complete → else `INVALID`.  
2. Smoke identity/reload → else `INVALID`.  
3. Screen coverage 105/105 scoreable → else `INVALID`.  
4. ρ=0 pooled null (calibrated band) → else `INVALID` (not a method win).  
5. ρ=1 marginal single-view → else `INVALID` (shortcut; refuse pairing-only interpretation).  
6. Pairing PC on CA checkpoints → `PAIRING_POSITIVE` / `PAIRING_NEGATIVE`.  
7. Descriptive CA−arm gaps **never** override (1)–(6); no `CA_FAVOURED` promotion path in S8; no confirmation fits for advantage.

Precedence: `INVALID` > (`PAIRING_POSITIVE` | `PAIRING_NEGATIVE`). Missing checkpoints → `INVALID`. Never rewrite S7 labels.

### Fit budget (attempted fits, not only successes)

| Stage | Planned attempted fits | Notes |
|---|---:|---|
| Smoke | 14 | fold 0 × 7 arms × {ρ=0,1} |
| Screen | 105 | 3 ρ × 5 folds × 7 arms |
| Confirmation / advantage | **0** | Not in scope |
| Pairing interventions | 0 new fits | Evaluate saved CA checkpoints |
| **Planned total** | **119** | |
| **Hard cap** | **150** | Stop on breach; count attempts |

### Falsifier (one line)

If screen is valid and CA pairing ll-drop 95% CI lower ≤ 0, conclude `PAIRING_NEGATIVE`: under this budget and plant, the CA implementation did not use within-cell RNA↔ATAC pairing.

---

## Rejected-alternatives table

| Alternative | Decision | Reason |
|---|---|---|
| Candidate 1 CA-advantage covariance remake | Rejected | Same signal class already MLP/concat-solvable (N4 S5) and S7-v2 rho=1 not CA-favoured; would be outcome-driven redesign |
| Reuse S7-v2 with patched mean-fold→pooled evaluator | Forbidden | Never repair invalid historical batch by changing gate after outcomes |
| Reuse `[0.35,0.65]` without calibration | Rejected | Independent review asked for prospective rationale at 30 donors; S8 uses chance calibration instead |
| New exotic CA-only generative story | Rejected | Would invent novelty; no primary paper warrant beyond adapted S7 equation |
| Stop all prospective controls | Not selected as Lane B output | Pairing-use diagnostic still answers Q3; integrator may still choose no-fit paper at I2/I5 |

---

## Implementation checklist (testable before any fit)

- [ ] New protocol ID + output root; no writes under S7-v1/v2 ledgers  
- [ ] Evaluator unit tests: pooled BA gate ≠ mean-fold; both logged  
- [ ] Chance-calibration artifact written and hashed **before** neural fits  
- [ ] Split manifest: 16/14, quotas, both classes every partition  
- [ ] Param-count CA/TC preflight ≤10%  
- [ ] Smoke refuses single-class test folds  
- [ ] Pairing shuffle preserves within-donor ATAC marginal multiset  
- [ ] Result writer encodes precedence above; cannot emit advantage PASS  

---

## Unresolved questions (out of Lane B / for integrator)

1. Whether I2 accepts any fit vs bounded internal null paper after Lanes A/C.  
2. Whether chance-calibrated null bands are wide enough that ρ=0 plants with residual background features still pass — needs the calibration artifact, not a threshold guess.  
3. Real-label power / external cohort (Lane C); not decided here.

---

## Lane B acceptance self-check

| Required | Met? |
|---|---|
| ≤2 candidates examined; one selected or stop | Yes — 2 examined; Candidate 2 selected |
| Estimand, statistic, fair arms, sensitivities, gate order, precedence, fit budget, falsifier | Yes |
| Pooled vs mean-fold resolved prospectively; S7 not relabeled | Yes |
| DRAFT / NO FITS marking | Yes |
| Primary literature for technical claims | Yes (frozen B1–B14 + July MOM) |
| Compact draft protocol under same folder | Yes — `DRAFT_PROTOCOL_S8.md` |

**Exact stop:** Lane B report complete with evidence citations; no fits run; no push/merge.
