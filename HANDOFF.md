# Handoff

**Date:** 2026-07-27
**Branch:** `develop`
**Next action:** `awaiting_professor_approval`
**Approver:** Professor Fang
**Data mode:** synthetic
**Condition-specific data added:** none

## Resume here

1. Read `README.md`, `DATA_CARD.md`, `MODEL_CARD.md`, and
   `docs/interim_methods_protocol.md`
2. Run `make plan-status` and `make verify`
3. Do not start real-data work without a dated entry in `docs/decision_log.md`

## What C01–C13 delivered

| Area | Location |
|---|---|
| Plan guard and package scaffold | `scripts/plan_guard.py`, `src/p22/` |
| Tasic evidence boundary | `legacy/tasic_proxy_view/` |
| Synthetic fixtures | `src/p22/testing/synthetic.py` |
| Donor splits | `src/p22/data/splits.py` |
| Train-only transforms | `src/p22/data/transforms.py` |
| Metadata preflight | `src/p22/data/preflight.py` |
| Models | `src/p22/models/` |
| Metrics and donor bootstrap | `src/p22/eval/` |
| Run registry and reports | `src/p22/runs/`, `src/p22/reports/` |
| Five-seed runner | `src/p22/training/`, `scripts/run_toy_pilot.py` |
| Faithfulness interventions | `src/p22/eval/faithfulness.py` |
| Local + CI verification | `scripts/verify_repository.py`, `.github/workflows/ci.yml` |
| Meeting notebooks | `notebooks/implementation/00`–`10` |

## Limitations (carry forward)

- Synthetic results do not transfer to real cohorts
- Legacy Tasic work is single-matrix proxy views with cell-level splits
- Routing weights are not explanations without interventions
- MPS unavailable in the recorded local environment; CPU remains required
- Generated evidence under `reports/generated/` must be re-built after clone

## Explicit approval blocker

Condition-specific dataset selection, download, training, and biological
interpretation stay blocked until Professor Fang records approval. The
post-approval checklist is in `docs/interim_methods_protocol.md` and section 8
of the implementation handoff.

## Commands for the next person

```bash
source .venv-p22/bin/activate
make plan-status
make verify
python scripts/verify_repository.py --json
```

If notebooks need re-execution on a cold machine:

```bash
python scripts/verify_repository.py --execute-notebooks
```
