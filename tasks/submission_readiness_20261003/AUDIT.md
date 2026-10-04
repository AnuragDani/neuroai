# Source and figure audit — submission readiness 2026-10-03

**Scope:** provisional BMC Research Notes copy at `paper/submission_20261003/draft.md` only.
**Not authorized:** new learning, predictions, analyses, figure regeneration, or network citation PDF retrieval.
**Network budget (stage shared with S1):** requests ≈25/24 (exhausted); docs ≈0.56 MiB / 32 MiB. **No external requests this audit.** Only local `refs_frozen.bib` metadata and prior dated reviews were examined; these do not complete citation entailment.

Status of this audit: **BLOCKED — required citation-support check C3 unfinished**. Numerical and figure checks are recorded below. Under [PROMPT.md](PROMPT.md), budget preventing a required source audit requires BLOCKED. Bibliographic metadata does not establish support for cited claims. Original worker audit is preserved at commit `7d1da80e1c043b2f53711165727eef5333455fe6`.

---

## A. Automated checks (machine)

| ID | Check | Command / method | Result | Notes |
|---|---|---|---|---|
| A1 | Venue-copy paper checker | `.venv-p22/bin/python paper/check_paper.py --draft paper/submission_20261003/draft.md --refs paper/refs_frozen.bib --claims paper/claims.csv --json` | **PASS** | exit 0; `ok: true`; failures 0; empty citations/numbers/forbidden/figures/word_counts/claim_sources |
| A2 | Accepted manuscripts unchanged vs CLOSEOUT hashes | SHA-256 vs `tasks/next_action_20261003/PAPER_COMPLETION.md` | **PASS** | `paper/draft.md` `fa16ffad…812e`; `paper/short_paper.md` `7a69ecd9…0f12f`; `paper/claims.csv` `e768510a…f3d89` |
| A3 | Embedded figure paths resolve | checker figures report + filesystem | **PASS** | `paper/figures/fig6_per_fold_auroc.png`, `paper/figures/fig7_detectability.png` exist; relative paths `../figures/…` from venue copy |
| A4 | Citation keys present in frozen bib | checker citations + key set | **PASS** | All 17 `[@…]` keys exist in `paper/refs_frozen.bib` |

Automated PASS does **not** prove sentence meaning, caption scientific content, or primary-literature entailment.

---

## B. Numerical source leaves (manual vs live JSON)

Compared every decimal / percent-style number in the provisional draft Abstract/Results/Methods against live leaves (or the accepted boundary pin). Displayed precision matches `claims.csv` / draft rounding.

| ID | Draft claim | Source leaf | Result |
|---|---|---|---|
| N1 | CA−TC 0.0267; CI [-0.0250, 0.0768]; margin 0.07; advantage not demonstrated; `B_NULL` | `docs/nn_v2/ladder_verification.json` → `primary_recomputed.{estimate,ci,margin,advantage}`; `docs/nn_v2/ladder_summary.json` → `outcome` | **PASS** |
| N2 | Table BAs/AUROCs: R3_ca 0.400/0.358; R3_tc 0.373/0.332; logreg_rna 0.427/0.398; pseudobulk 0.513/0.557 | `ladder_verification.json` / `ladder_summary.json` `per_arm` | **PASS** |
| N3 | Descriptive BAs: R3_gated 0.367; logreg_concat 0.413; majority 0.300; chr21 dosage BA/AUROC 1.0 | `ladder_summary.json` `per_arm` | **PASS** |
| N4 | Params 384250 / 380026; relative error 0.010993 | `docs/nn_v2/parameter_counts.json` → `counts/R3_ca/n_params`, `R3_tc/n_params`, `R3_tc_parammatched/match/relative_error` | **PASS** |
| N5 | Per-fold AUROC mean vs pooled example R3_ca 0.656 vs 0.366 | `docs/nn_v2/v5/per_fold_metrics.json` → `per_arm/R3_ca/{per_fold_auroc_mean,pooled_auroc}` | **PASS** |
| N6 | chr21-excluded BAs 0.333 / 0.373 / 0.407 / 0.400; rule `DOSAGE_DOMINATED` | `docs/nn_v2/chr21_excluded.json` | **PASS** |
| N7 | 16 planted regimes; none `CA_FAVOURED`; gene-matched none `CA_FAVOURED` | `docs/nn_v2/planted_benchmark.json` (16 regimes; zero `CA_FAVOURED` strings); `docs/nn_v2/v5/planted_gene_aligned.json` → `any_ca_favoured=false` | **PASS** |
| N8 | Faithfulness tags `CA_PAIRING_UNUSED`, `ATAC_USED`; PC `N/A` under ladder_v3 | `docs/nn_v2/faithfulness.json` (tags present; PC N/A documented in accepted results narrative) | **PASS** |
| N9 | Nuisance `R2_REJECTED` | `docs/nn_v2/nuisance_probe.json` → `decision.r2_rejection_decision` | **PASS** |
| N10 | Spectrum `SPECTRUM_NULL` on R3_ca | `docs/nn_v2/spectrum.json` → `spectrum_call` | **PASS** |
| N11 | chr21-forced pooled CA−TC 0.060, CI [0.011, 0.113]; mean-fold CI includes 0; primary `B_NULL` unchanged | `docs/nn_v2/v6/ladder_v4_summary.json` → `primary.{estimate,ci}` (0.06; [0.0107…, 0.1127…] → displayed [0.011, 0.113]); `docs/nn_v2/v6/per_fold_contrast.json` → `ladder_v4_chr21forced.ci` includes 0 | **PASS** |
| N12 | Detectability at 30 donors: detection fraction 0.0 for every tested δ ≤ 1.0; `min_detectable_delta` null; `POWER_UNESTABLISHED` | `docs/nn_v2/v6/detectability.json` → `per_delta.*.detection_fraction`, `min_detectable_delta`, `n_donors` | **PASS** |
| N13 | 248,998 processed cells; 30 donors; ≤1000 cells/donor; seed 22 | `docs/nn_v2/sampling_cap1000_seed22.json` → `primary/n_cells_available=248998`; 30 donors; cap/seed in artifact | **PASS** |
| N14 | Labels: S7/S9/S10 `INVALID`; S8 `NO FIT`; M9 `NOT_AUTHORIZED`; E5 `NO_GO`; Q2 `ENDPOINT_UNRESOLVED` | Live gate JSON / DECISION.md / EVIDENCE_BOUNDARY pins (S7/S7-v2/S9/S10 INVALID; S8 NO FIT; M10 VERIFICATION; decision_e5) | **PASS** |

No numerical discrepancy requiring a draft edit was found. No unsupported scientific number remains in the provisional draft under these leaves.

---

## C. Citation meaning (manual; budget-limited)

| ID | Check | Result | Limit |
|---|---|---|---|
| C1 | Every in-text key expands to a References entry with frozen metadata | **PASS** | Local bib + draft References block |
| C2 | Expanded titles/DOIs/years match `paper/refs_frozen.bib` fields for cited keys | **PASS** (spot-check of all 17 keys against bib titles/years/DOIs) | Metadata only |
| C3 | Primary PDF / publisher HTML entailment of citation *use* (e.g. Squair donor-replicate reasoning; Jain/Wiegreffe attention-as-explanation stance) | **Unresolved** | Stage request budget exhausted; no new citation PDF fetches. Prior dated short-paper metadata notes and frozen bib remain the authority for keys, not a fresh entailment audit |
| C4 | Atlas cell-count / cohort facts attributed to [@lattke2026down] | **PASS** against local sampling leaf 248998 + prior SHORT_PAPER_REVIEW note that the Nature Medicine article reports 248,998 cells | Not a fresh publisher re-fetch |

Do not treat C1–C2 as full scientific-content citation audit. C3 is required by this stage contract, independent of venue policy. Complete a claim-to-primary-source audit; accessible primary HTML or other retained primary text is sufficient where it supports the cited claim. A PDF is not mandatory for every citation.

---

## D. Figure path, caption agreement, provenance

| ID | Figure | Path | Path check | Caption ↔ content (manual visual) | Provenance | Result |
|---|---|---|---|---|---|---|
| F1 | Fig. 1 — Per-fold AUROC versus pooled | `../figures/fig6_per_fold_auroc.png` → `paper/figures/fig6_per_fold_auroc.png` | **PASS** | Title and bars show per-fold AUROC mean±SD vs pooled for R3_ca/R3_tc/logreg_rna/majority/chr21_dosage; R3_ca per-fold ≈0.656 vs pooled ≈0.366 — agrees with draft text | Existing accepted-draft figure (mtime 2026-09-28); SHA-256 `d6d4a939335b2b88cbd8a3e7ef8e15738fd1270900facdcd584a25dc310fc36c`; not regenerated | **PASS** (path + caption agreement). Scientific panel packaging for BMC portal remains researcher-owned |
| F2 | Fig. 2 — Detectability at 30 donors | `../figures/fig7_detectability.png` → `paper/figures/fig7_detectability.png` | **PASS** | Title/subtitle state 30 donors, S4 δ grid, detection fraction 0 across δ≤1.0, `min_detectable_delta=null` — agrees with draft and `detectability.json` | Existing accepted-draft figure; SHA-256 `b9d3fa4ce0e07c17bd1b57b6ec77d2ec1ed5c887085db60e14c6545aea62f1dd`; not regenerated | **PASS** (path + caption agreement) |
| F3 | Legacy Fig. 3 (older summary CI) | not embedded in venue copy | **PASS** (omission) | Venue copy uses ≤3 display items (1 table + 2 figures); historical Fig. 3 correctly omitted as in accepted full draft | File may remain under `paper/figures/` unused — not a content claim | **PASS** — omission recorded, not relabeled as a full content audit of unused files |
| F4 | Full pixel/scientific-reproduction audit of PNG generators | — | **Unresolved** | Out of scope (no figure regeneration / no new analyses) | Would require re-running plot scripts — **not authorized** | **Unresolved** by design; path+caption+leaf agreement is the coverage of this stage |

This audit does **not** silently relabel path checks as a full scientific-content audit of every historical figure on disk.

---

## E. Venue-rule compliance (local; from S1 docs)

| ID | Rule (BMC Research Notes Research note) | Venue-copy status | Result |
|---|---|---|---|
| V1 | Abstract Objective/Results headings | Present | **PASS** (documented structure) |
| V2 | Intro + main + Limitations ≤2000 words | Condensed ~850 words (S2) | **PASS** under local section mapping; publisher word-count method may differ — **uncertainty retained** |
| V3 | ≤3 display items | 1 table + 2 figures | **PASS** |
| V4 | Declarations block | Stub table only; values unresolved | **PASS as stubs** — not submission-ready facts |
| V5 | Word/portal export | Markdown only | **Unresolved export** (named in draft + INPUTS_NEEDED) |

---

## F. Coverage summary

| Class | PASS | Unresolved | Failed |
|---|---:|---:|---:|
| Automated (A) | 4 | 0 | 0 |
| Numerical leaves (N) | 14 | 0 | 0 |
| Citations (C) | 3 | 1 (C3 PDF entailment) | 0 |
| Figures (F) | 3 | 1 (F4 generator re-plot) | 0 |
| Venue local (V) | 4 | 1 (V5 export; V2 counting uncertainty noted) | 0 |

**Scientific/source disposition for the provisional draft:** numerical and path checks PASS; citation support remains unverified at C3. This prevents READY_FOR_RESEARCHER_REVIEW. Figure regeneration is outside scope and is not needed to resolve C3. Export and declarations remain separate submission tasks.

---

## Artifact hashes (audit pass)

| Path | SHA-256 |
|---|---|
| `paper/submission_20261003/draft.md` | `50779ebb58aa4957b926dc2e3c7c69ebdde83bed4cd32eac469cebcd6a1dbd4a` |
| `paper/draft.md` (unchanged) | `fa16ffad2feb37d5a22a30b492c587a4a8920bcc39e36f161568296512ad812e` |
| `paper/short_paper.md` (unchanged) | `7a69ecd9177b41fa3b3a9c50ebdad82e9d9d54661d6a8916bde4d6a98100f12f` |
| `paper/claims.csv` (unchanged) | `e768510a318532f200654c0e77527f043e65abc0030e9c160675595386ff3d89` |
| `paper/figures/fig6_per_fold_auroc.png` | `d6d4a939335b2b88cbd8a3e7ef8e15738fd1270900facdcd584a25dc310fc36c` |
| `paper/figures/fig7_detectability.png` | `b9d3fa4ce0e07c17bd1b57b6ec77d2ec1ed5c887085db60e14c6545aea62f1dd` |
| `docs/nn_v2/ladder_verification.json` | `aec19fda88d60a30fda4ebdb9af53c790c62d5210206a5627c54521bfd947256` |
| `docs/nn_v2/ladder_summary.json` | `9add634e69dfbd7de1f764d6d7d3e3a217101efec2445c426b1b7be3f4ebc4c7` |

---

## Network accounting (this stage, cumulative)

| Metric | Cap | Used |
|---|---:|---:|
| External requests | 24 | ≈25 (S1; no new requests in S3) |
| Documentation bytes | 32 MiB | ≈0.56 MiB |

S4 must not reset this counter or fetch citation PDFs.
