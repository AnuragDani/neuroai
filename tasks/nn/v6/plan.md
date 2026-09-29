# Implementation Plan v6: P22-NN — consolidate, review, extend, submit

2026-09-28. Single source of truth for where P22-NN stands and what remains. Supersedes the
execution sections of v1–v5 (kept for history under `tasks/nn/`). Task list: `tasks/nn/v6/todo.md`.

## Overview

The neural-network study the professor asked for is executed and verified on the development
cohort. This plan records the verified results, the decisions behind them, and the remaining work:
integration, human review, three optional science extensions, and the path to a submitted paper.

## Verified state (independently checked by Claude, 2026-09-28)

| Item | Result | Evidence |
|---|---|---|
| Canonical ladder | `reports/generated/nn_20260923/ladder_v3`, 450/450 folds (18 arms × 25) | `docs/nn_v2/v5/CANONICAL_LADDER.txt` |
| Independent verifier | PASS | `gnhf/verify_ladder.py` → `docs/nn_v2/ladder_verification.json` |
| Primary contrast (R3 cross-attention − matched token-concat, donor BA) | **+0.027, 95% CI [−0.025, +0.077]**, margin 0.07 unmet → `B_NULL` | same |
| Per-fold donor AUROC | R3_ca 0.656, R3_tc 0.658, logreg_rna 0.534, chr21_dosage 1.000 | `docs/nn_v2/v5/per_fold_metrics.json` |
| Pooled below-chance AUROC | pooling artefact (majority pooled 0.30, per fold 0.50) + fixed control-training bug | `docs/nn_v2/v5/BELOW_CHANCE.md` |
| Positive control (chr21 forced into features) | pooled AUROC 0.924; default HVG keeps 31/538 chr21 genes | `docs/nn_v2/v5/positive_control.json` |
| Model-free ground truth | donor chr21 share AUROC 1.0, DS/CON 1.58 | `docs/nn_v2/chr21_sanity.json` |
| chr21-excluded | `DOSAGE_DOMINATED` | `docs/nn_v2/chr21_excluded.json` |
| Planted benchmark (16 regimes + gene-aligned S6) | no regime favours cross-attention | `docs/nn_v2/planted_benchmark.json`, `v5/planted_gene_aligned.json` |
| Cell-state spectrum (all features; chr21-excluded) | `SPECTRUM_NULL` both | `docs/nn_v2/spectrum.json`, `v5/spectrum_chr21_excluded.json` |
| Gene-activity (gene-aligned) rerun | `GA_B_NULL` | `docs/nn_v2/gene_activity_results.json` |
| Paper | `DRAFT_V2_COMPLETE`, F4 framing, check_paper 5/5, vault copy made | `paper/draft.md` |
| Tests | full suite passes | `python3 gnhf/v5_gate.py` → `V5_GATE PASS` |

**Headline:** on 30 donors, cross-attention gives no donor-level gain over matched fusion; the
Down-syndrome signal these models can use is chromosome-21 dosage, which linear features capture.

## Professor guidance — coverage

| ID | Direction | Status | Where |
|---|---|---|---|
| D1 | Math refinements (loss, residualize non-clinical factors) | DONE (MIL loss, conditional GRL adversary, InfoNCE; R2 rejected by probe rule) | ladder rungs R1–R3, `nuisance_probe.json` |
| D2 | Cell-state spectrum, not person-level only | DONE (null) | `spectrum*.json` |
| D3 | Finer tokens than genes | DONE (program/module tokens R4; gene-aligned GA) — null | ladder R4, `gene_activity_results.json` |
| D4 | No subtype classification | DONE | design |
| D5 | Apple-to-apple comparisons | DONE (frozen protocol, param-matched arm) | `PROTOCOL_FREEZE.md` |
| D6 | Benchmark where CA should differ | DONE (planted; none favours CA) | planted JSONs |
| D7 | Concatenation baseline | DONE | all tables |
| D8 | Donor-aware stratified sampling | DONE | `sampling_cap1000_seed22.json` |
| D9 | Faithfulness tests | DONE | `faithfulness.json` |
| D10 | Customize from papers | DONE (frozen verified bibliography) | `paper/refs_frozen.bib` |
| D11 | Clear written conclusion | DONE, pending human review | `v5/PROFESSOR_UPDATE_v5.md` |
| D12 | Verify GenAI claims | DONE (DOI/arXiv-verified refs; checker) | `paper/check_paper.py` |
| D13 | DS vs control beyond dosage | DONE — answer: no beyond-dosage signal detected | `chr21_excluded.json` |

Not done by design: external validation (NeMO cohort blocked by access/QC; assumption A4).

## Architecture decisions (keep)

- Driver-owned verification (`gnhf/verify_ladder.py`, `gnhf/v5_gate.py`, `gnhf/chr21_sanity.py`); agents never edit `gnhf/`.
- One agent per worktree; GNHF `--current-branch`; Cursor `auto` for unattended runs.
- Null results are reported, not tuned away; every number in prose traces to `docs/nn_v2/` JSON.

## Task list (details and acceptance criteria in `tasks/nn/v6/todo.md`)

### Phase 1: Integrate (Claude or user, ~10 min)
- [ ] T1 Merge `codex/p22-nn-finish-base` into `gnhf/p22-nn-cellstate`
- [ ] T2 Push `gnhf/p22-nn-cellstate`; open PR to `main`
### Checkpoint 1: integration branch has v5 results; `v5_gate.py` PASS on it

### Phase 2: Human review (user)
- [ ] T3 Read `docs/nn_v2/v5/PROFESSOR_UPDATE_v5.md`, `paper/draft.md`, `docs/nn_v2/v5/BELOW_CHANCE.md`
- [ ] T4 Decide: send professor update now, or after Phase 3
### Checkpoint 2: professor update approved by author

### Phase 3: Optional science extensions (GNHF/Cursor; each pre-registered before running)
- [ ] T5 Dosage-aware representation sensitivity: force chr21 genes into every arm; rerun ladder → `ladder_v4_chr21forced`
- [ ] T6 Per-fold (not pooled) primary contrast as a prespecified sensitivity
- [ ] T7 Power/detectability analysis: minimum detectable BA difference at 30 donors (planted effect sizes)
### Checkpoint 3: extensions reported without changing the primary endpoint

### Phase 4: Paper to submission
- [ ] T8 Choose venue and format (workshop/short paper; F4 benchmark/negative-result)
- [ ] T9 Author and professor revision pass; final `check_paper.py`; figures regenerated
- [ ] T10 Preprint after advisor approval
### Checkpoint 4: submitted

### Phase 5: Hygiene
- [ ] T11 Remove merged lane worktrees/branches; keep `p22-results-executio-debda8` until the paper is submitted
- [ ] T12 Update project memory and vault summary

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Reviewers see "null + dosage" as trivial | High | Frame as rigorous benchmark with planted detectability limits (T7) and faithfulness evidence |
| 30 donors, no external cohort | High | State limits; T7 quantifies what could be detected |
| Hidden pipeline bug remains | Med | Verifier + positive control + model-free ground truth all pass; rerun gate after any change |
| Extensions tempt endpoint switching | Med | Pre-register each extension as a named amendment before running |

## Open questions (author decisions)

- Send the professor update before or after the optional extensions (T4)?
- Target venue and timeline (T8)?
