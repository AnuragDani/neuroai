# Professor-direction investigation — 2026-09-29

## Aim and present truth

Determine why the current cross-attention study has not produced a defensible advantage or a cell-state finding, and identify the smallest prospective study that can answer Professor Fang's remaining scientific question. A negative answer is complete if it is well supported. Do not search model, seed, threshold, dataset, or wording until a positive result appears.

This is a **new investigation**, not a continuation of the frozen NN-v2 primary or either S7 batch. The September 29 package was researcher-confirmed sent. No new professor reply is recorded. Original professor sources are the [July 2](../../../../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/MOM/2026-07-02/MOM_07-02-2026_Transcript_and_Meeting_Notes.md) and [July 21](../../../../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/MOM/2026-07-21/MOM_07-21-2026_Transcript_and_Meeting_Notes.md) meeting records. Worker plans, handoffs, and sent packets are not new professor instructions.

Current accepted primary: `ladder_v3`, 450/450 fits, verifier `PASS`, R3 cross-attention minus token-concat donor balanced accuracy 0.0267, 95% donor-bootstrap CI [-0.0250, 0.0768], `B_NULL`. This means advantage is **not demonstrated**, not that methods are equivalent. N13 did not show cross-attention pairing use; N16 found `SPECTRUM_NULL`; chromosome-21 dosage strongly separates this cohort. S7-v1 and S7-v2 are both `INVALID`. The v2 review found a pooled-versus-mean-fold null-check mismatch, failed pooled null controls, `PC_FAIL`, and no confirmation fits. Biological power is `POWER_UNESTABLISHED`. No external paired-cohort validation occurred.

Use the live [ladder verifier](../../../docs/nn_v2/ladder_verification.json), [faithfulness](../../../docs/nn_v2/faithfulness.json), [spectrum](../../../docs/nn_v2/spectrum.json), [v6 detectability](../../../docs/nn_v2/v6/detectability.json), the versioned S7-v2 result and [independent S7-v2 review](../../../.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202/docs/nn_v2/s7_v2/CODEX_REVIEW_20260929.md). Recompute from raw sidecars where a gate matters. If status text and a verifier conflict, use the verifier for scientific claims and record the conflict.

## Questions to settle

| Question | Required answer |
|---|---|
| Q1. Was the fair comparison implemented as declared? | Donor and cell identity, feature timing, labels, splits, paired arm budgets, parameter counts, aggregation, bootstrap, controls, and exact executed source. |
| Q2. Why did S7 fail? | Separate invalid control design/statistic, marginal leakage, model optimization, pairing sensitivity, small donor count, and orchestration faults. Do not infer one cause from a failed composite gate. |
| Q3. Can this architecture learn and use a *pairing-dependent* signal? | A prospective control with single-view and shuffled-pair checks, fixed primary statistic, matched non-attention arms, and predeclared failure rules. |
| Q4. Is another real-data question scientifically justified and feasible? | Cohort, donor counts, cell states, ATAC quality, chromosome-21/technical confounding, external paired data, effect size, precision and access. |
| Q5. What paper is justified now? | Claim-by-claim choice: bounded internal null paper, new method study only after valid method evidence, or biological study only after independent biological support. |

## Professor-direction coverage to audit

| July direction | Existing response | Remaining check |
|---|---|---|
| Mathematical refinement and non-clinical nuisance removal | MIL, conditional adversary, InfoNCE, and ablations were implemented. | Did each addition improve its declared objective? Did nuisance control remove signal or fail its probe? |
| Cell-state spectrum rather than cell-type label recovery | Donor-trained per-cell scores and cell-type analyses exist. | Are these scores a meaningful state measure, or only unstable inherited donor labels? Is an independent biological readout possible? |
| Granular programs/subfeatures rather than gene-as-token novelty | Program/module-token and gene-activity secondary analyses exist. | Which tokens represent independent biology? Which are only engineering variants? Confirm novelty against primary papers. |
| Fair, equally supervised comparisons | Same donor folds and simple baselines were used. | Recheck actual executed feature, tuning, cell, and parameter budgets. Record every exception. |
| Complex benchmark that differentiates models | N4 and S7 controls were attempted. | Why did simpler models match or beat CA? Was the scenario structurally attention-specific? |
| Donor-aware sampling and routing-faithfulness tests | Stable sampler, held-out folds, clamp/permutation/ablation, and seeds exist. | Did each intervention have a sensitive positive control? Did the fitted CA use the intended modality pair? |
| Paper-based customization and cautious claims | A frozen bibliography and paper claim ledger exist. | Trace each mathematical choice to the cited original work and report only supported adaptations. |
| Tasic as engineering check | Tasic was not used as disease evidence. | Make sure no future synthesis promotes it to independent-modality proof. |

## Evidence and claim rules

1. Keep original July professor records and September worker handoffs distinct. A user-reported approval for the existing public-data study exists, but no dated, independently archived professor approval or reply to the September 29 package exists. Do not invent one.
2. Freeze the finished NN-v2 protocol, outcomes, S7-v1, and S7-v2. Never repair an invalid historical batch by changing its gate, result label, or denominator. A new control requires a new protocol ID and output root.
3. Distinguish label-signal amplitude from the observed **between-model** contrast. A narrow CI in a synthetic selected cell is not power for the biological joint `A_ADVANTAGE` rule.
4. A future advantage claim needs its predeclared estimate threshold **and** CI rule, fair comparators, valid controls, robustness, and pairing-sensitive intervention. Cell-state or regulatory claims need donor-level inference, confound controls, and independent support. Report failures and uncertainty.
5. No lane may run model fits, download new data, change a scientific threshold, merge branches, push, edit the sent packet, or change canonical status. This first wave is investigation and protocol design. Researcher may later authorize a bounded fit from a reviewed frozen protocol.

## Parallel GNHF wave: three isolated lanes

Each lane uses `gnhf --worktree` from the same S7-v2 base commit (`808fa734`, confirm live before launch). Each writes only its own `tasks/nn/professor_direction_investigation_20260929/outputs/LANE_*.md` and a compact evidence table there. No lane edits shared code, source results, paper, MOM, status, or another lane's output. Each commits its own files locally and reports branch, SHA, commands, inspected artifacts, unresolved questions, and exact stop reason. The launch prompts are `LANE_A_PROMPT.md`, `LANE_B_PROMPT.md`, and `LANE_C_PROMPT.md` in this folder. No automatic merge.

### Lane A — executed-evidence and root-cause audit

**Task A1: inventory.** Map the exact versioned raw data, protocol, source commit, sidecars, summaries, gate scripts, and output hashes for ladder_v3, S7-v1, and S7-v2. Identify missing or mismatched evidence. Do not treat task checkboxes as results.

**Task A2: rerun arithmetic from saved outputs.** Independently recompute the primary CA–TC estimate/CI and donor coverage when raw files permit. For S7-v2, recompute pooled donor BA, mean-fold BA, seven-arm null and marginal controls, CA against every arm, PC coverage/statistic, and whether confirmation was correctly skipped. Explain any discrepancy with frozen spec or implementation.

**Task A3: trace executed path.** Inspect call graph from CLI through fold builder, label generation, transforms, fit, checkpoint reload, donor aggregation, bootstrap, gate and writer. Record only concrete faults with file/line and a counterexample. Include leakage, paired-cell identity, donor duplication, seed coupling, threshold/statistic mismatch, and source/protocol ID. Separate scientific faults from GNHF parsing or logging errors.

**Acceptance:** a table of each claim, raw source, recomputation, gate, and confidence level; a ranked cause tree; one minimal proposed repair per confirmed defect; explicit `KNOWN`, `LIKELY`, `UNKNOWN` labels. No source edit or fits.

### Lane B — prospective benchmark and model-design review

**Task B0: source and model taxonomy.** Revisit the original papers for the implemented loss terms, nuisance adversary, pairing objective, MIL pooling, and program tokens. Record each model's inputs, supervision, target and what was adapted. Use primary papers or source code for technical claims. Do not treat a planned architectural variant as a contribution without a fair test.

**Task B1: reconstruct professor's benchmark question.** Compare July wording with N4 S0–S6 and S7-v1/v2. Explain which scenario tests cross-view interaction, which tests pairing, which admits a single-view or concat shortcut, and whether cross-attention is structurally necessary. A benchmark that all competent arms solve does not establish a unique attention benefit.

**Task B2: propose at most two candidate controls on paper.** For each, specify donor/cell-level generative equation, what is held constant, label balance, noise, positive and negative controls, and why CA might differ from *every* fair comparator. State a falsifier. Do not claim that CA must win. Include representation and pooling limitations, train/test identity, and what a pair shuffle destroys while preserving donor marginals.

**Task B3: select one candidate before fitting.** Write a draft frozen protocol with primary estimand, exactly one primary statistic, fixed seeds/scenario, donor splits, same information and tuning budget for CA/TC/concat/gated/linear controls, parameter matching, checkpoints, intervention sensitivity, resource cap, output root, and `INVALID`/`NEGATIVE`/`POSITIVE` precedence. Resolve pooled-versus-mean-fold BA explicitly. Review whether the old `[0.35,0.65]` null interval at 30 donors is defensible; do not reuse or change it without a prospective rationale. Label the protocol **DRAFT / NO FITS**.

**Acceptance:** one selected protocol and a rejected-alternatives table; every gate computable before results; one fit-budget calculation; a testable implementation checklist; no changed old spec or fits. If no defensible attention-specific control exists, recommend stop and bounded paper.

### Lane C — cohort, power and biological-value audit

**Task C1: map the biological question.** Separate donor disease prediction from cell-state spectrum and regulatory mechanism discovery. Audit whether the current DS cohort can answer any beyond-dosage question with 15+15 donors, cell-type support, paired ATAC signal, and known batch/age/library structure. Do not treat chr21-forced secondary significance as primary attention evidence.

**Task C2: feasibility.** Inventory existing external paired-cohort candidates and file/access status from project records. For each: donor count per group, cell-state labels, real paired modality, comparable age/tissue/protocol, data license/access, leakage risk, expected transfer/compute, and unresolved preflight. Metadata inspection only. No acquisition or external validation.

**Task C3: design adequacy.** Define the exact joint success event for `A_ADVANTAGE`: estimate at least 0.07 and CI lower bound above zero. Sketch donor-level simulation/precision analysis with plausible **between-model** effects and uncertainty; report assumptions, design effect, target detection probability, and uncertainty across assumptions. If saved outputs cannot identify those inputs, mark `POWER_UNESTABLISHED`; do not output a spurious donor target. Also estimate feasibility for a separate biological estimand if justified.

**Acceptance:** cohort decision matrix, explicit available/blocked inputs, auditable power assumptions, and go/no-go recommendation for external validation versus bounded paper. No acquisition, fits, or new biological claim.

## Integration after parallel lanes

| Gate | Condition to pass | If it fails |
|---|---|---|
| I0 provenance | All three lanes use same base evidence and distinguish professor sources from worker material. | Correct factual record before deciding. |
| I1 reproducibility | Primary and S7-v2 gate numbers recompute; any mismatch has a concrete cause. | Repair evaluator **prospectively** and retain old result labels. |
| I2 control design | One candidate has a non-circular pairing-dependent estimand, fair controls, fixed statistic and falsifier. | Stop new method fits; retain internal null paper. |
| I3 design adequacy | Fit budget, donor-level uncertainty and sensitivity targets are declared; no synthetic CI is called biological power. | Keep power unresolved; do not promise a positive result. |
| I4 biology | A stated biological question has adequate measurements, confound plan and independent support path. | No mechanism or transportability claim. |
| I5 independent review | Reviewer checks protocol/gate/code paths before any fit and signs a dated decision record. | Revise protocol without seeing new fit outcomes. |

Integration output: `DECISION.md` with source-specific findings; `PROTOCOL_V3_DRAFT.md` and machine-readable spec only if I2 passes; exact fit/no-fit decision; expected compute/storage budget; reviewer objections and resolutions. A single integrator owns shared files after the lanes stop. Do not merge three branches blindly. Review branch diffs, then copy or cherry-pick lane-owned reports only.

## Conditional experimental phase, not part of parallel launch

1. **No-fit implementation check:** freeze a new protocol ID, versioned paths, inputs, hashes, donor split/label manifests, primary statistic, tests, and resource caps. Demonstrate that invalid controls prevent fits or confirmation as declared. Review source changes. No old S7 edits.
2. **Bounded synthetic pilot:** only after I0–I5 pass. Run one prespecified smoke, screen, pairing intervention and conditional confirmation. Count attempted fits, not only successful ones. Stop on an invalid control, missing checkpoint, coverage failure, cap breach, or protocol drift. Preserve `INVALID`, `NEGATIVE`, or `POSITIVE` result even when disappointing. No seed/threshold reroll.
3. **Method interpretation:** a valid positive synthetic control can show that this implementation can exploit a constructed signal. It does not turn the real DS primary positive or prove biological power. A valid negative rules out the *tested architecture/control pair* under the frozen budget, not all attention methods.
4. **Real-data follow-up:** only after a separate prospective real-label protocol and design-adequacy review. Choose one objective: method advantage versus fair arms, or biologically justified beyond-dosage cell-state signal. Do not reuse the finished primary as a fresh discovery test. Add donor-level CI, confound and intervention checks, multiplicity, and independent validation plan before fitting.
5. **External phase:** data access/preflight, cohort comparability, protocol freeze, then independent evaluation. Report transport failure. No broad biological or method-generalization claim from the internal cohort alone.

## Completion and stop rules

The investigation is complete when lanes A–C, integration gate I0–I5, and a dated decision exist. A new experiment is **optional and separately gated**. Valid outcomes include a bounded paper with no more model fitting, an invalid-control diagnosis with a new reviewed protocol, a feasible external-cohort plan, or a documented data/power blocker. Do not equate a successful GNHF iteration or a checked task box with scientific acceptance. Update `status.md` only after a material accepted gate or blocker. The next professor update must start from the September 29 sent package and must not claim a reply that is not recorded.
