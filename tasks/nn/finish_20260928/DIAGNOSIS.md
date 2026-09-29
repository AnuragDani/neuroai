# Prospective path — saved-evidence diagnosis (2026-09-28)

Planning only. No new fits, gate changes, downloads, external validation, email, or push.
Raw runs under `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/` were read, not modified.
Finished E/W/C closeout stays closed (`B_NULL`, study `STUDY_PARTIAL`).

## Question

From saved controls and gates: is the constructed interaction learnable, do both comparators learn it, and do labels/representation/pooling hide a measurable CA−TC contrast? Separate (A) benchmark learnability, (B) model behavior, (C) donor uncertainty. Do not equate primary non-detection with failure to learn disease or with low donor power alone.

## Evidence used (verified summaries + raw presence)

| Claim area | Summary artifact | Raw check |
|---|---|---|
| Planted S0–S5 | `docs/nn_v2/planted_benchmark.json` | `reports/generated/nn_20260923/planted/results.csv.gz` present |
| Gene-matched S6 | `docs/nn_v2/v5/planted_gene_aligned.json` | `.../planted_gene_aligned/results.csv.gz` present |
| Forced-chr21 disease PC | `docs/nn_v2/v5/positive_control.json` | run_dir `.../v5_positive_control` (summary donor AUROC 0.924) |
| Primary ladder | `docs/nn_v2/ladder_summary.json`, `ladder_verification.json` (`PASS`) | `.../ladder_v3/` `folds_done=450`, `failures=[]` |
| CA−TC detectability | `docs/nn_v2/v6/detectability.json` (`min_detectable_delta=null`) | raw JSON statement matches docs |
| Pairing / faithfulness | `docs/nn_v2/faithfulness.json` | PC `N/A`; tags `CA_PAIRING_UNUSED`, `ATAC_USED` |
| Chr21-forced sensitivity | `docs/nn_v2/v6/CHR21_FORCED.md` / `ladder_v4_summary.json` | secondary only; not primary |

## A. Benchmark learnability (planted / control labels)

1. **Null and strong additive signals behave as designed.** S0 BA stays in [0.50, 0.54]; S1@δ=1.0 all five models reach BA 1.0 (`acceptance_checks` pass). Constructed additive labels are learnable by CA and by simple concat / gated arms.
2. **Context interaction (S4) is learnable but not CA-unique.** At δ=1.0 every scored arm is high (CA 0.867; best non-attention gated/logreg 0.9) → regime `LINEAR_SUFFICIENT`, CA−best = −0.033. Simple models solve the planted interaction under this representation/pooling.
3. **Pairing-only (S5) is learnable by the fusion family, not by linear concat, and not uniquely by CA.** At δ=1.0: gated_fusion 1.0, CA 0.967, token/feature concat ~0.933, logreg_concat ~0.542 → `MLP_FAVOURED`. Pairing signal exists and is recovered; CA is slightly worse than gated fusion.
4. **Gene-matched interaction (S6) is jointly learnable by CA and feature-concat MLP.** At δ=0.5/1.0: `gene_aligned_ca` and `rna_atac_concat` both BA 1.0; `gene_aligned_tc` weaker (0.70 / 0.867). `any_ca_favoured=false` because the CA_FAVOURED rule requires beating the best non-attention baseline.
5. **Across the entire planted grid there is zero `CA_FAVOURED` regime** (N4 S0–S5 + P2 S6). There is therefore **no saved planted support** that the current architecture/protocol yields a cross-attention-specific advantage on the interaction designs already tried.
6. **Disease/dosage learnability on real labels is not the bottleneck for cohort discrimination.** Forced-chr21 positive control logreg donor AUROC **0.924**; model-free `chr21_dosage` on ladder_v3 has BA/AUROC **1.0**. Non-detection of CA−TC advantage is not “the cohort has no learnable DS signal.”

## B. Model behavior (comparators and interventions)

1. **Primary real-data contrast is a verified null, not equivalence.** Verifier `primary_recomputed`: estimate **0.0267**, CI **[−0.0250, 0.0768]**, margin 0.07, `advantage=false` → `B_NULL`. Absolute R3_ca BA **0.40** is below RNA logreg **0.427** (secondary `LINEAR_SUFFICIENT`).
2. **Both CA and TC underperform dosage / strong linear controls on real DS labels.** Chr21 dosage remains perfect; chr21-excluded ladder is `DOSAGE_DOMINATED`. Complex fusion is not carrying a beyond-dosage disease claim under the finished protocol.
3. **CA does not show pairing use on real-data interventions; pairing PC was never saved.** N13: I3 on R3_ca `used_by_model=false` → `CA_PAIRING_UNUSED`. `pc_status=N/A` because no planted S4/S5 δ=1.0 fold models were kept under ladder_v3. Pairing-advantage claims stay provisional.
4. **Matched TC can use ATAC under I1 while CA does not meet the same “used” bar on I1.** Tag set includes `ATAC_USED` from R3_tc I1 log-loss CI excluding 0; R3_ca I1 does not. This is comparator behavior evidence, not a planted CA win.
5. **Chr21-forced representation (ladder_v4) moves the primary contrast to a small positive that still misses A_ADVANTAGE.** Estimate **0.060**, CI **[0.011, 0.113]** → `CHR21FORCED_D_SMALL_POSITIVE` only. Linear arms gain more AUROC than R3 when chr21 is forced. Representation helps disease discrimination broadly; it does not deliver a finished CA method win.

## C. Donor uncertainty (power / precision at n=30)

1. **X4 planted S4 CA−TC detectability at 30 donors: detection fraction 0 at every δ ∈ {0.1, 0.25, 0.5, 0.75, 1.0}; `min_detectable_delta=null`.** Raw and docs statements match. Even when a planted context interaction exists, the **CA−TC donor-BA CI rarely excludes 0** under the finished widths/repeats.
2. **Therefore donor n needed for a reliable CA−TC contrast is not established by the current planted grid.** Non-detection at δ=1.0 mixes: (i) small true CA−TC gaps when both arms learn the label (see S4 LINEAR_SUFFICIENT), and (ii) wide donor-bootstrap uncertainty at n=30.
3. **Primary real-data CI already spans below zero and past the 0.07 margin upper edge of the estimate gap.** Estimate is 0.043 below margin; CI includes 0. This is compatible with a true near-null or a small underpowered positive — the finished study correctly reports advantage not demonstrated.
4. **Planted non-detection alone does not isolate “low donor power” from “benchmark/model does not create a CA-unique gap.”** S4/S6 show both comparators (or concatenative MLP) can solve the label; X4 then asks a harder question (CA−TC contrast) that stays undetectable.

## Integrated diagnosis

| Factor | Verdict from saved evidence | Implication for next path |
|---|---|---|
| Benchmark learnability of constructed signal | **Yes** for additive, pairing-only (fusion), and gene-matched interaction | Failure is not “labels are unlearnable.” |
| Benchmark learnability of **CA-unique** advantage | **No** (`CA_FAVOURED` count = 0) | Method-advantage path lacks a demonstrated pairing-sensitive CA-favoured control under current designs. |
| Real-label disease discrimination | **Yes** for dosage / forced-chr21 logreg; **no** beyond-dosage CA claim | Do not narrate B_NULL as inability to learn DS. |
| Comparator behavior (CA vs TC/simple) | CA ≈ or ≤ fair baselines on planted and primary real; pairing unused on CA | Prefer redesign of estimand/control over searching variants of the finished primary. |
| Donor uncertainty | CA−TC contrast not detectable at n=30 up to δ=1.0; n required unknown | Power/precision design is mandatory before any new real-label fit; current grid does not set n. |

**Bottom line.** The finished internal null is coherent: constructed interactions are learnable, but not in a way that isolates cross-attention; both CA and strong non-attention arms often solve the same planted labels; real DS signal is dosage-dominated and learnable by simple controls; donor-level CA−TC precision at n=30 is insufficient to detect even large planted contrasts. The binding gap for a **method-advantage** continuation is the missing **pairing-sensitive, CA-favoured learnable control** (plus PC sensitivity), not raw disease learnability. A **beyond-dosage biological** continuation is a different estimand and also lacks a positive internal beyond-dosage result today.

## Explicit nulls / gaps (honest)

- No `CA_FAVOURED` planted regime (null for method-support claim).
- Pairing intervention PC = `N/A` (null evidence for pairing-use sensitivity).
- Detectability `min_detectable_delta = null` (no established δ or donor n for CA−TC).
- External paired validation not performed (`STUDY_PARTIAL`).
- No authorization in this document to run new experiments.

## Status of planning deliverables

| Deliverable | Status |
|---|---|
| Evidence-linked diagnosis | **This file — COMPLETE** |
| One proposed hypothesis + estimand | Pending next iteration |
| Frozen comparison / positive-result criteria | Pending (reuse finished A_ADVANTAGE rule until explicitly re-declared for a new protocol) |
| Feasibility + ordered execution tasks | Pending |

Finished primary endpoint and gates remain unchanged.
