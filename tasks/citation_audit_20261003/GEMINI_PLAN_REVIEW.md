# Gemini plan review — CLI

Route: AGy CLI, model `gemini-3.1-pro-high`, plan mode. Initial acpx/Gemini route failed with client-not-supported error; no substantive acpx review occurred. First AGy invocation ignored stdin; retry passed the complete prompt directly.

Here is the requested independent scientific-audit planning review.

### 1. Verdict
**PASS**

The plan is methodologically sound, strictly scoped, and correctly isolates literature verification (Gate C3) from experimental validation. The defined resource limits and failure rules ensure the agent will not fall into unbounded retrieval loops.

### 2. Necessary Corrections (Ranked by Importance)
While the plan is approved for execution, keep the following strict operational guidelines in mind:
1. **Unbundle Grouped Citations:** Ensure that any grouped citations (e.g., `[4, 7, 9]`) are evaluated individually against the sentence's claim. Do not allow a strong source to "cover" for a weak or irrelevant source within the same bracket. 
2. **Explicit Block on Unresolved:** Clarify in execution that an "unresolved" source (e.g., due to a paywall or missing text) must explicitly block the T4 handoff (`BLOCKED` status). A lack of evidence cannot be treated as a localized `PASS`.

### 3. Executable Acceptance Criteria and Definition of Done
**Definition of Done:** 
An exhaustive audit ledger (`AUDIT.md`) is completed, mapping every citation instance in `paper/submission_20261003/draft.md` (covering all 17 keys and repeated uses) to an exact primary source excerpt, paraphrase, or explicit "unresolved" state. The draft text is updated to reflect only verified source bounds.

**Executable Acceptance Criteria:**
- 100% of citation instances in the draft are cross-referenced with primary source text.
- No unsupported or extrapolated claim is retained in the manuscript.
- All automated scientific/source checks (`check_paper.py`, `verify_ladder.py`) pass identically without `--write` modifications.
- Protected files, frozen bibliographies (`refs_frozen.bib`), and experimental hashes remain strictly unchanged.
- Execution terminates within the defined resource limits (32 retrieval attempts, 32 MiB retained text), with accounting documented.
- `READINESS.md`, `status.md`, and the task ledger are accurately updated to reflect the final state (`READY_FOR_RESEARCHER_REVIEW` or `BLOCKED`).

### 4. Sufficiency to Close C3
**Yes, this scoped audit is sufficient to close C3 without redoing experiments.** 
Gate C3 is fundamentally a literature entailment and source-verification gate. By systematically verifying that the manuscript's text faithfully reflects the cited literature and surgically correcting any overstatements, the scientific integrity of the external claims is secured. This operates entirely independently of the local empirical findings.

### 5. Citation Support vs. Numerical Validation
The execution must strictly separate literature entailment from local experimental validation:
- **Citation Support:** Verifies that external literature says what the manuscript claims it says (e.g., "Paper X observed mechanism Y").
- **Numerical Validation:** This study's local cohort counts, pipeline performance, and measured outcomes are self-contained. External sources do not, and cannot, validate this study's specific numerical results.

### 6. Identified Risks in Specific Claim Areas
- **Atlas paired-cell claim:** There is a high risk of conflating the cited atlas's broad population statistics with the specific, processed local subset used in this study. Numerical similarities do not constitute primary-source support. Claims must explicitly match the exact cohort described in the source.
- **Attention disagreement:** Treating competing papers as a unified consensus is scientifically inaccurate. The wording must clearly represent the disagreement or theoretical fracture regarding attention-as-explanation in the cited works.
- **Donor-DE-to-classification extrapolation:** Citing Donor Differential Expression (DE) studies to justify the generalizability of machine learning classification models is a category error. Citations must be restricted strictly to supporting DE findings, not ML performance.
- **Mixed grouped citations:** There is a risk of "citation laundering," where an irrelevant or weak paper is hidden within a group of valid citations. Every individual key within a group must independently support the claim it is attached to.


## Disposition

Accepted: unbundle every grouped reference; any unresolved retained source claim blocks readiness. Clarified that our donor-inference design is a methodological choice motivated by DE replicate reasoning, not validated by that paper. Numerical/source gates remain separate.
