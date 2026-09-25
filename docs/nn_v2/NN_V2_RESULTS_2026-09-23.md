# NN-v2 results — 2026-09-23

**Final label: `NN_ASSIGNMENT_PARTIAL_BLOCKED`.**

Upstream blocker (first lines): **N10 (the real-data refinement ladder) is
`BLOCKED:lane_stalled`; no real-DS-label model was ever fit.** Every task that needs a
fitted model — N11 (chr21-excluded arm), N12 (seeds), N13 (faithfulness), N14 (nuisance
probe), N15/N16/N17 (cell-state spectrum and routing/attention) — is therefore
`BLOCKED:upstream`, and N21 is blocked as well. Consequence: the study has **no real-data
primary contrast, no chr21-exclusion result, no cell-type spectrum, and no faithfulness
result**. What is below is foundation, benchmark and measurement work only. No claim of
mechanism, causality, clinical use, novelty or external validity is made anywhere.

## 1. Plain-language conclusion

The engineering foundation is complete and frozen: a repaired donor-aware sampler
(30 donors, cap 1000, 30,000 cells), a leak-checked fold-prep pipeline (24 fit / 6
holdout donors), a parameter-counted 18-arm ladder, and a planted-signal benchmark. The
planted benchmark answers the professor's question about when cross-attention should win:
**in none of the tested regimes did cross-attention beat the best simpler model.** At
δ = 1.0 the additive regimes were solved by a linear concat baseline (balanced accuracy
1.0), and the pairing-only regime S5 favoured the MLP/gated fusion (best non-attention
1.0 vs cross-attention 0.9667). Cross-attention was never better than the best
non-attention model in any of the 16 scenario×δ cells (max advantage 0.0). The real-data
question the professor actually cares about — does cross-attention beat matched
token-concat on DS donors — is **unanswered**, because the ladder never ran. The ATAC
gene-activity upgrade reached its acquisition gate (548/548 regions, ACCEPTED) but its
downstream rerun (N21) could not run without the ladder. So this is an honest partial:
infrastructure and a negative planted-benchmark answer, no real-data result.

## 2. Professor-direction coverage (plan §1, D1–D13)

| ID | Direction | Status | Evidence path |
|---|---|---|---|
| D1 | Math nuance: MIL loss, nuisance adversary, InfoNCE | PARTIAL | `docs/nn_v2/parameter_counts.json`; `docs/nn_v2/PROTOCOL_FREEZE.md` (arms, λ grid); no fits → no ablation result (N10 BLOCKED) |
| D2 | Cell-state spectrum | BLOCKED | `docs/nn_v2/spectrum.json` = NOT_ESTIMABLE(input_missing); `docs/nn_v2/ROUTING_ATTENTION.md` |
| D3 | Program/module tokens and gene-aligned tokens | PARTIAL | N8 DONE (program tokens); N21 BLOCKED; `docs/nn_v2/gene_activity_measurement.json` (panel built) |
| D4 | No saturated subtype classification | DONE | `docs/nn_v2/sampling_cap1000_seed22.json` (strata = donor×cell-type×library; cell type is never a label) |
| D5 | Apple-to-apple, equal supervision | PARTIAL | `docs/nn_v2/PROTOCOL_FREEZE.md`; `docs/nn_v2/parameter_counts.json` (18 arms; parammatch rel. err 1.10%); no runs |
| D6 | Benchmark differentiating attention from simple models | DONE | `docs/nn_v2/planted_benchmark.json` |
| D7 | Concatenation fusion baseline | DONE | `docs/nn_v2/planted_benchmark.json` (`logreg_concat`, `rna_atac_concat`, `token_concat`) |
| D8 | Stratified, donor-aware downsampling | DONE | `docs/nn_v2/sampling_cap1000_seed22.json` |
| D9 | Faithfulness interventions | BLOCKED | `docs/nn_v2/faithfulness.json` (all I1–I6/NC/PC = N/A) |
| D10 | Customize from papers, name precedent | PARTIAL | `docs/nn_v2/PROTOCOL_FREEZE.md` maps rungs to §6 precedents; no refinement result |
| D11 | Lead with clear conclusions, no Tasic rerun | DONE | this document §1; no Tasic artifact exists |
| D12 | Verify GenAI claims; no new citations | DONE | this document cites only plan §6 ([B1]–[B14]); no novelty claims |
| D13 | DS vs control feasibility, chr21 dosage | BLOCKED | `docs/nn_v2/nuisance_probe.json`; N11 BLOCKED:upstream N10 |

## 3. Planted benchmark: which scenario favours cross-attention?

Answer from `docs/nn_v2/planted_benchmark.json` (5 models × 5 folds, δ = 1.0, cap 1000):
**no tested regime favoured cross-attention.** All additive regimes S1–S4 were labelled
LINEAR_SUFFICIENT; S5 (pairing-only) was labelled MLP_FAVOURED.

| scenario @ δ=1.0 | regime | CA | best non-attention | CA − best |
|---|---|---|---|---|
| S1 RNA-additive | LINEAR_SUFFICIENT | 1.0 | 1.0 (four-arm tie) | 0.0 |
| S2 ATAC-additive | LINEAR_SUFFICIENT | 1.0 | 1.0 (four-arm tie) | 0.0 |
| S3 both-additive | LINEAR_SUFFICIENT | 1.0 | 1.0 (four-arm tie) | 0.0 |
| S4 context interaction | LINEAR_SUFFICIENT | 0.8667 | 0.9 (`gated_fusion` / `logreg_concat`) | −0.0333 |
| S5 pairing-only | MLP_FAVOURED | 0.9667 | 1.0 (`gated_fusion`) | −0.0333 |

Reading (≤10 lines): a linear concat baseline is sufficient whenever the signal is an
additive shift in either modality, and it still edges the neural arms at S4. In the
pairing-only regime S5 — the one designed to require the RNA–ATAC joint — gated fusion
(1.0) and the concat MLP/token-concat (0.9333 each) both beat cross-attention (0.9667).
Sanity gates held:
S0 within 0.35–0.65 and S1 δ=1.0 all models ≥ 0.9. The S5 δ=1.0 deviation check
(`s5_delta1_within_0p05_of_chance`) is **False**, i.e. fusion did *not* collapse to chance;
the current capacity *can* detect pairing-only signal, it just is not best detected by
cross-attention. These are synthetic planted labels, independent of DS, with no
biological or clinical meaning.

## 4. Refinement ladder and parameter counts

The frozen ladder has 18 arms (`docs/nn_v2/PROTOCOL_FREEZE.md`; counts in
`docs/nn_v2/parameter_counts.json`): R0 v2 representation, R1 + gated MIL, R2 + nuisance
adversary, R3 + InfoNCE pairing, R4 program tokens, each with CA and TC twins, plus
`R3_tc_parammatched`, `R3_gated`, `latent_pca_lsi_head` and five controls.

| arm | params (CA / TC) |
|---|---|
| R0 | 359,426 / 355,202 |
| R1 | 367,876 / 363,652 |
| R2 | 384,250 / 380,026 |
| R3 | 384,250 / 380,026 |
| R4 | 29,970 / 25,746 |
| R3_tc_parammatched | 380,026 (rel. err 1.10% vs R3_ca 384,250) |
| R3_gated | 314,044 |
| latent_pca_lsi_head | 16,836 |

**Rung decisions: none can be decided.** Every rung's rejection rule (plan §4.2) requires a
held-out fit; the ladder did not run, so R1–R4 are neither accepted nor rejected. The
primary contrast remains fixed at R3_ca − R3_tc (margin 0.07), unmeasured. The protocol
also fixes the grid (R2 λ_adv ∈ {0.1, 1.0}; R3 λ_adv × λ_nce ∈ {0.1, 1.0}²) and the
rung/§6 precedent mapping ([B1] MIL, [B2] adversary, [B3]/[B4] InfoNCE, [B5]/[B9]
program tokens), but adaptation quality could not be evaluated.

## 5. Data foundation and ATAC measurement

Sampler (`docs/nn_v2/sampling_cap1000_seed22.json`): 30 donors, 248,998 cells available,
30,000 selected at cap 1000, seed 22, donor×cell-type×library strata; reproduction
reference is the historical 256-cap sample (7,680 cells, 30 donors). Fold prep
(`docs/nn_v2/fold_prep_smoke.json`): fold 0, 24 fit / 6 holdout donors, 24,000 train and
6,000 holdout rows, 2,000 HVG, 256 ATAC regions (465 union), exclude_chr21 = False, load
7.03 s, prep 1.52 s, peak RSS 4.153 GiB.

ATAC gene-activity upgrade (`docs/nn_v2/gene_activity_measurement.json`): a label-free
548-region panel (chr21 genes with ≥1% RNA detection plus dispersion selection), fragment
counts, budget 3,500,000,000 bytes with 2,066,087,936 fetched at window 131,072 (the
planned 262,144 window was abandoned for headroom; counts are window-invariant), 548/548
complete joins, 0 truncated, 0 unknown; acceptance checker
`scripts/check_real_paired_acceptance.py` → **ACCEPTED, 11/11 checks,
scientific_claim_allowed = true**. The panel is descriptive measurement only; no
deconvolution and no result (N21 BLOCKED).

## 6. Limitations

- 30 donors only; internal cohort only; same-cohort annotations are not independent
  validation (plan §6 [B14]).
- The gene-activity panel is measurement-level and not a regulatory/functional panel.
- No external validation, no clinical or regulatory claim.
- Attention and gate weights are **not** explanations [B11]; with N13 blocked, no
  intervention shows any readout is used, so all routing/attention readouts are
  `NOT_SHOWN_USED` (`docs/nn_v2/routing_attention.json`).
- The planted benchmark is semi-synthetic; its labels are independent of disease.
- No real-data result exists for the primary contrast; the professor's core question is
  open, not answered negatively.

## 7. Replay commands, hashes, runtime

Replay (from repo root, `.venv-p22` active, `PYTHONPATH=src:scripts`):

```
PY -m pytest -q tests/test_nn_spectrum.py
PY scripts/analyze_nn_v2_spectrum.py          # -> NOT_ESTIMABLE (input_missing)
PY -m pytest -q -x                            # full suite, N23
ruff check src tests scripts
```

Hashes and provenance: current git HEAD `2ab4b92c9176a93d0fe14f7ba3213f64b577ac8b`
(recorded at N22). Protocol canonical sha256
`80931bfc05c403804db47f53b02b29989204a6c04720476cb752dd62968b7161` (canonical JSON,
sha256 field excluded; file sha256 `98b169f68710d66e34d44728d72c2aadd01c60cfe351c2924e7660cc8a249154`);
inputs `configs/nn_inputs_2026-09-23.json` sha256
`45d9b540d2a1c906879867003a488e7a54a9e4818a82f776b91643f77ae9f766`; sampling artifact
sha256 `e515b2eee03804b3836256ba3e8b7604fa6a8043e50c06c36b24988250423b2f`; planted
protocol sha256 `d6760c33e472ac4d0bcd88aec00b0abd18f4566f9f28d6da15dcae18110d2bf4`.
Per-artifact git heads: sampling `e1d12af185f537ad6e57ba36fed45ab827553517`,
parameter counts `1306bc508f19bb519e74cde25fad7bf12e284148`.

Runtime: no ladder runtime exists (never ran). Recorded foundation runtimes: fold-prep
load 7.03 s + prep 1.52 s, peak RSS 4.153 GiB; gene-activity acquisition 2,066,087,936
bytes. N22 authoring and N23 verification are the only new work in this document.

## 8. Number provenance (every number → JSON)

| claim | JSON path |
|---|---|
| sampler 30 donors, 30,000/248,998, cap 1000, seed 22, reproduction 7,680 | `docs/nn_v2/sampling_cap1000_seed22.json` |
| fold prep 24/6 donors, 24,000/6,000 rows, 2,000 HVG, 256/465 regions, runtimes/RSS | `docs/nn_v2/fold_prep_smoke.json` |
| all planted balanced accuracies, regimes, gate checks | `docs/nn_v2/planted_benchmark.json` |
| all parameter counts and parammatch 1.10% | `docs/nn_v2/parameter_counts.json` |
| gene-activity panel 548, budget/bytes/window, 11/11 ACCEPTED | `docs/nn_v2/gene_activity_measurement.json` |
| nuisance probe BLOCKED, R2_UNEVALUATED | `docs/nn_v2/nuisance_probe.json` |
| faithfulness all N/A, tag rule | `docs/nn_v2/faithfulness.json` |
| spectrum NOT_ESTIMABLE | `docs/nn_v2/spectrum.json` |
| routing/attention all NOT_SHOWN_USED | `docs/nn_v2/routing_attention.json` |

Citations use only plan §6 keys ([B1]–[B14]); no citation was added.
