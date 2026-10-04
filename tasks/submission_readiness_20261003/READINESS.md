# Submission readiness handoff — 2026-10-03

**Status: `READY_FOR_RESEARCHER_REVIEW`** after the separately authorized citation audit. Submission remains pending human facts and export.

## Evidence and decision
Original GNHF run stopped after 4 successful iterations / 4 commits, but its READY claim was premature: required citation-support C3 was unverified. Worker handoff remains in commit `7d1da80e1c043b2f53711165727eef5333455fe6`; corrective BLOCKED handoff remains in `d0f043c`. The later user explicitly authorized consolidation/push, a Gemini plan review and audit execution.

Gemini `gemini-3.1-pro-high` reviewed the plan through AGy CLI and returned **PASS**. acpx/Gemini failed because its Code Assist client was unsupported; AGy was the successful CLI fallback. [Plan](../citation_audit_20261003/PLAN.md), [exact Gemini review](../citation_audit_20261003/GEMINI_PLAN_REVIEW.md).

**C3 PASS after surgical wording corrections:** [citation audit](../citation_audit_20261003/AUDIT.md), [claim/source inventory](../citation_audit_20261003/CITATION_SUPPORT.json). All **17 references / 22 revised key uses / 21 citation groups** have source-specific support. Broad component motivations use primary abstracts; atlas population and Signac window attribution use primary results/methods. Grouped references are checked individually. No unsupported retained claim or unresolved required source check remains in this scope.

## Outputs
- [Provisional venue draft](../../paper/submission_20261003/draft.md): three paragraphs revised (Introduction, Related Work, Methods). The atlas available-cell count is distinguished from capped analysis; donor-DE motivation is separated from classifier design; attention disagreement is attributed; method adaptations and the distinct gene window are explicit.
- [Venue comparison](VENUES.md): provisional BMC Research Notes Research note. Venue selection remains researcher-owned; no new venue/APC verification.
- [Historical S3 numerical/figure audit](AUDIT.md): original snapshot preserved with current C3 pointer.
- [Researcher inputs H1–H12](INPUTS_NEEDED.md): authors, contributions, funding, conflicts, ethics/consent, release links, venue/budget/license and export remain unresolved.
- [Task list](todo.md): original audit blocker closed by this later authorized stage.

## Fresh verification (repo root, no --write)
| Check | Command | Exit / result |
|---|---|---|
| Accepted paper checker | `.venv-p22/bin/python paper/check_paper.py --json` | 0; ok=true; failures=0 |
| Venue-copy checker | `.venv-p22/bin/python paper/check_paper.py --draft paper/submission_20261003/draft.md --refs paper/refs_frozen.bib --claims paper/claims.csv --json` | 0; ok=true; failures=0 |
| Saved-prediction replay | `.venv-p22/bin/python gnhf/verify_ladder.py --run reports/generated/nn_20260923/ladder_v3` | 0; PASS; advantage=false; estimate 0.0266667; CI [-0.0250, 0.0767857] |
| Protected hashes | [PROTECTED_HASHES.json](../citation_audit_20261003/PROTECTED_HASHES.json) | 12/12 match |
| Citation coverage | Inventory vs draft extraction | 17/17 keys; 22/22 revised key uses |

Accepted full/short papers, frozen bibliography, claims, original MOM and scientific gate artifacts remain unchanged. Abstract/Results, accepted numerical results and existing figures in the provisional copy are unchanged. No new fits, predictions, plot generation or data acquisition.

## Coverage and limits
- Numerical/path/figure checks from the original audit remain accepted; unchanged protected hashes rematch.
- C3 is completed at the level of each retained citation claim; this does not certify every cited paper’s full methods or independently reproduce those publications.
- Full regeneration of historical PNGs is outside scope; original path/caption/content checks and figure hashes remain preserved.
- Markdown-to-Word/portal export, final venue confirmation and human declarations remain open. This is not submission-ready certification.

## Resource accounting
Original submission-preparation ledger: approximately 25 requests against cap 24, approximately 0.56 MiB. That overrun remains recorded; the counter was not reset or re-certified.

Separate citation stage: **28 source acquisition/discovery attempts**, **28 cached-page navigation operations**, **280,195 bytes of returned response representations**. [Detailed ledger](../citation_audit_20261003/NETWORK.md), [batch records](../citation_audit_20261003/NETWORK.json). The 32-attempt acquisition cap is not a 32-total-web-operation or physical HTTP cap: all 56 initiated acquisition/navigation operations are disclosed. Internal HTTP/redirect/cache counts and web download-byte totals are unavailable; strict physical-cap compliance is not established. Source verification is complete despite those accounting limits; no further acquisition is needed.

## Definition of Done
| Criterion | Evidence | Verdict |
|---|---|---|
| Provisional venue comparison and copy exist | VENUES + draft; known export limits stated | PASS |
| Every retained scientific citation claim has primary support | Citation audit + 17-key / 22-use inventory | PASS after wording corrections |
| Required automated scientific checks pass | Fresh commands above | PASS |
| Protected accepted work unchanged | 12/12 hashes | PASS |
| Manual coverage and limits explicit | Original + new audits; resource limits disclosed | PASS for stated scope |
| Human facts not invented; owners named | INPUTS_NEEDED H1–H12 | PASS as unresolved inputs |
| Task marks and current handoff agree | Stage task list + this file | PASS |

## Scientific labels preserved
Primary R3_ca−R3_tc **B_NULL**; power **POWER_UNESTABLISHED**; M9 **NOT_AUTHORIZED**; M10 diagnostic-only; S7/S9/S10 **INVALID**; S8 **NO FIT**; E5 **NO_GO**; Q2 **ENDPOINT_UNRESOLVED**. No superiority, equivalence, validated cell-state biology or new professor endorsement.

## Current artifact hashes
Paths relative to repo root. Plan/task/status/index/current handoff are excluded from this register to avoid closure/self-reference churn; original snapshots remain in Git.

| Artifact | SHA-256 |
|---|---|
| `paper/submission_20261003/draft.md` | `fa80103f2ea220102372605b067bafb14b3c26ecc8915949e17ee6ce914ef0fc` |
| `paper/draft.md` | `fa16ffad2feb37d5a22a30b492c587a4a8920bcc39e36f161568296512ad812e` |
| `paper/short_paper.md` | `7a69ecd9177b41fa3b3a9c50ebdad82e9d9d54661d6a8916bde4d6a98100f12f` |
| `paper/claims.csv` | `e768510a318532f200654c0e77527f043e65abc0030e9c160675595386ff3d89` |
| `paper/refs_frozen.bib` | `9d5432d7faf3ad28eb159945f239b1eb1fd67e1f76174ffca691f5c2f11a3da4` |
| `paper/figures/fig6_per_fold_auroc.png` | `d6d4a939335b2b88cbd8a3e7ef8e15738fd1270900facdcd584a25dc310fc36c` |
| `paper/figures/fig7_detectability.png` | `b9d3fa4ce0e07c17bd1b57b6ec77d2ec1ed5c887085db60e14c6545aea62f1dd` |
| `tasks/submission_readiness_20261003/VENUES.md` | `588889e73a664ef7461415b0c92b88b8678eb130020ceb61fe3f5d5119a3d441` |
| `tasks/submission_readiness_20261003/AUDIT.md` | `97923ee0e45bb665c74fc2ee2bb22b25706dea48175854c5cee9b489d85e046e` |
| `tasks/submission_readiness_20261003/INPUTS_NEEDED.md` | `e0a8be39dea8feb1b5376ede694fc50e3c16fb3e8eaebda4e8196b1468b702a1` |
| `docs/nn_v2/ladder_verification.json` | `aec19fda88d60a30fda4ebdb9af53c790c62d5210206a5627c54521bfd947256` |
| `docs/nn_v2/ladder_summary.json` | `9add634e69dfbd7de1f764d6d7d3e3a217101efec2445c426b1b7be3f4ebc4c7` |
| `MOM/README.md` | `18e8c8ade62a075097a09e1da7565c5a6c33566d5298f0f319e5d9fb2ed6a4c9` |
| `MOM/2026-07-02/README.md` | `d411701b09dc34cfaf0674ea82733341ff8cd3355d9dd1823666242845212fa0` |
| `MOM/2026-07-21/README.md` | `cf732e339e5348d260c121b10f5b0f4dcb15d276cdf3bdaf5aadb3c7ee25e0e6` |
| `tasks/next_action_20261003/CLOSEOUT.md` | `db21d4855654ceb4262945b436238032517bab1a343aa20fc77eb49cbfa59b71` |
| `tasks/citation_audit_20261003/AUDIT.md` | `e29f6643456d91deddf1cae5ecdaa24f8245fe0f49c0a0e7df66cd3524ef0c5a` |
| `tasks/citation_audit_20261003/CITATION_SUPPORT.json` | `61fb68e43a7b0d3dfa5877ed7edb36429787bb2c06046112ab61839943362185` |
| `tasks/citation_audit_20261003/NETWORK.json` | `2a70d9fff9a9767d41f653630e73f8de0977f9992fef6f8e0824f814df7240c9` |
| `tasks/citation_audit_20261003/GEMINI_PLAN_REVIEW.md` | `26e7f4d2755e8ffbc9a40281dc472c2ebe8c200b3475dfc13a8007876086f9bd` |
| `tasks/citation_audit_20261003/PROTECTED_HASHES.json` | `3b821a93fd98f947a20a6968fd482e5a843fa158ff2e75d6ac319478409d3d53` |

## Next action and stop
Researcher reviews the audited provisional copy and closes H1–H12; then prepare the required export. Further source audit is needed only for newly introduced claims or challenged evidence. No automatic training or dataset search. Submission/contact require the researcher’s explicit instruction.
