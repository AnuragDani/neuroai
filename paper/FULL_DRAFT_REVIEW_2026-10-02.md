# Full draft and claim-ledger reconciliation — 2026-10-02

## Accepted revision

[Full draft](draft.md) and [numeric ledger](claims.csv) now agree with accepted evidence and current scientific dispositions. This completes the reconciliation left open in the earlier [short-paper review](SHORT_PAPER_REVIEW_2026-10-02.md). This is a scoped evidence revision, not submission certification.

| Issue | Resolution | Evidence |
|---|---|---|
| Primary confidence interval | Use saved-fold replay: 0.0267, 95% CI [-0.0250, 0.0768], margin 0.07 | `docs/nn_v2/ladder_verification.json` |
| Missing donor RNA baseline | Include pseudobulk BA 0.513, AUROC 0.557; descriptive, without superiority claim | Same verifier, `pseudobulk_rna_logistic` |
| Two pooled AUROC definitions | Canonical table averages within-repeat AUROCs; diagnostic Fig. 6 pools all 150 donor-repeat rows | `gnhf/verify_ladder.py`; `scripts/nn_v5_per_fold_metrics.py` |
| Historical Fig. 3 interval | Remove its embedding; preserve original figure and summary | Current primary paragraph and result table |
| False numerical provenance | Remove Boolean policy checks from numeric ledger; fix signed gaps and source pointers | Source-leaf checker; existing policy remains in Methods |
| Detectability versus power | Synthetic exercise does not establish real-data primary power | `docs/nn_v2/v6/DETECTABILITY.md`; failure-audit handoff |
| Later controls | S7/S9/S10 INVALID; S8 NO FIT; no method validation or dataset-defect conclusion | Original control handoffs |
| Unauthorized pilot | Exclude accepted quantitative claims; historical NOT_AUTHORIZED remains | M10 handoff; E5 NO_GO |
| Professor direction | Preserve pending objective endorsement and independent cell-state endpoint limits | Original July 2/21 MOM; guidance audit |
| R0 versus MIL selection | Disclose R0 donor BA selection and MIL donor log-loss selection | Frozen protocol selection note |

## Verification

- Fresh saved-fold replay: PASS; zero training fits.
- `python paper/check_paper.py --json`: PASS, including each numerical CSV value against its signed JSON source leaf at displayed precision.
- Paper-tool tests excluding figure generation: 13 PASS, 8 deselected. The added test rejects sign errors, Boolean sources, missing pointers and incorrect rounding; it accepts bracket/list pointers and percent scaling.
- Independent scoped reviewer `paper_evidence_review`: PASS. No unsupported superiority, equivalence, statistical-power, biological-endpoint or professor-endorsement claims found.
- [Evidence manifest](full_draft_evidence_2026-10-02.json) pins manuscript, ledger, checker and source hashes. Original MOM and dated scientific records were not edited.

Run the numerical/source checks from the repository root:

```sh
.venv-p22/bin/python paper/check_paper.py --json
.venv-p22/bin/python gnhf/verify_ladder.py --run reports/generated/nn_20260923/ladder_v3
```

## Limits and next action

The checker validates numerical source leaves, citation keys, number presence, image paths and word limits. It does not prove sentence-to-source meaning or manuscript signs. Independent review covered the revised scientific claims. This pass does not certify all reference contents, figure contents or submission readiness; the full draft still uses frozen bibliography keys and awaits publication formatting/declarations.

Next action: prepare a separate, dated, unsent professor update from the last packet actually sent, following the vault packet guide. No packet, outbound message, push or new experiment was performed here. Research acceptance remains B_NULL / POWER_UNESTABLISHED; automatic pilot remains NO_GO.
