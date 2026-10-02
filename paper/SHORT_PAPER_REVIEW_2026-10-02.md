# Bounded short-paper consolidation — 2026-10-02

## Scope
Revised `paper/short_paper.md` from accepted ladder_v3 evidence. The complete original `paper/draft.md` remains a separate older draft. This is a scoped evidence revision, not a full academic-paper pipeline certification or submission-ready designation. No new fits, professor packet, messages, vault/MOM changes or push.

## Changes
- Include donor-level pseudobulk RNA logistic baseline: BA 0.513, AUROC 0.557. Point estimates alone do not establish statistical superiority.
- Add a four-model result table with pooled out-of-fold AUROC limitations.
- Preserve primary CA−TC BA 0.0267, CI [-0.0250, 0.0768], margin 0.07 and advantage-not-demonstrated framing. No equivalence claim.
- Distinguish constructed-signal detectability from established power of the real-data comparison.
- Record later invalid S9/S10 controls without promoting them to method/pairing validation.
- Exclude unauthorized masked-ATAC pilot numbers from accepted results. Record its review gap as an internal provenance note.

## Evidence checks
Fresh `.venv-p22/bin/python gnhf/verify_ladder.py --run reports/generated/nn_20260923/ladder_v3` exits 0 / PASS. It reads saved folds and runs no fits. Four result-table rows match verifier values rounded to three decimals. Primary CI matches fresh bootstrap rounded to four decimals. `git diff --check` passes. Source/manuscript hashes and table keys: [evidence JSON](short_paper_evidence_2026-10-02.json).

## Reference existence and metadata
Six cited works have matching primary article/publication records. This check is not a comprehensive retraction or citation-entailment audit. DOI direct access failed for three records; PubMed/primary full text supplied alternate metadata.

1. Lattke et al., 2026: [Nature Medicine article](https://www.nature.com/articles/s41591-026-04211-1). Article reports 15 DS/15 control cortices and 248,998 cells after QC.
2. Hao et al., 2021: [PubMed publication record](https://pubmed.ncbi.nlm.nih.gov/34062119/). Title and DOI 10.1016/j.cell.2021.04.048 match.
3. Ashuach et al., 2023: [PubMed publication record](https://pubmed.ncbi.nlm.nih.gov/37386189/). Title and DOI 10.1038/s41592-023-01909-9 match.
4. Ilse et al., 2018: [PMLR proceedings](https://proceedings.mlr.press/v80/ilse18a.html).
5. Squair et al., 2021: [Primary full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC8479118/). Title/DOI match. It motivates biological-replicate handling in differential expression, not a guarantee of predictive generalization.
6. Jain and Wallace, 2019: [ACL Anthology](https://aclanthology.org/N19-1357/).

## Remaining scope
Reconcile the original full draft and its claim ledger before treating it as current. Select venue/length only when needed for formatting. Independent scoped evidence review returned PASS. The reviewer requested S9 marginal-gate context and a selected-arm table label; both were added. No claim of new biological state, causal mechanism, external transport or model superiority.
