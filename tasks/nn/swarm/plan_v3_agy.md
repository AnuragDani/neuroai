# Implementation Plan v3: P22-NN finish with Gemini (agy), self-verifying

2026-09-25. Replaces the DeepSeek/GNHF execution layer for the remaining work. Science,
assumptions A1–A16, protocol (frozen in N9) and decision tree are unchanged.

## Why v3

The v2 swarm finished every stage, but its critical task N10 (the real-data ladder) never ran:
DeepSeek reported "no final answer" or unparseable output on 10 of its 11 ladder iterations, and
GNHF's rollback (`reset --hard`) erased the unsaved runner each time. The v2 S2 gate failed, but
the swarm continued, so the paper was written without the main result.

## Architecture (`gnhf/agy_swarm.py`, config `tasks/nn/swarm/agy_lanes.json`)

- **Gemini 3.1 Pro (High) via `agy`**, `--sandbox --mode accept-edits`: it edits files only; no shell.
  Fallback model on quota errors: Gemini 3.8 Flash (High). Quota/rate limits → wait 15 min, retry, forever.
- **The driver executes everything.** Gemini writes `tasks/nn/run/<ID>.json`; the driver validates
  argv (`scripts|paper|gnhf/*.py` or `-m pytest`), runs it with the project Python, and feeds the log
  tail into the next call. Runs longer than 20 min go to the background; the driver waits.
- **Nothing is reset.** Every call is committed. Edits outside the lane's owned files are reverted.
- **Driver-verified DONE.** Each task has acceptance commands. A DONE whose check fails is set back
  to TODO with the failure output. BLOCKED/NOT_NEEDED is refused for critical-path tasks.
- **Hard gates.** S2, S4 and S5 do not pass without their evidence files; a failing hard gate reruns
  the stage (3 rounds), then the driver stops with exit 6 instead of writing on missing evidence.
- **Worktrees** under `P22/.worktrees/<lane>`; merges into `gnhf/p22-nn-cellstate`; merge conflicts
  and post-merge test failures are repaired by bounded agy calls, re-checked by the driver.

## Stages, goals, tasks, verification

### S2 — Primary ladder (hard gate). Critical: N10a–N10d.
| Task | Deliverable | Driver check |
|---|---|---|
| N10a | runner + summarizer + synthetic end-to-end test | `pytest tests/test_nn_runner.py tests/test_nn_factory.py` |
| N10b | smoke fold, historical reproduction, timing | `ladder_timing.json` has projected_hours, reproduction, cap |
| N10c | full 5×5 ladder (background, 14 workers) | `ladder_run.json` folds_done == folds_expected |
| N10d | summary, primary contrast, outcome label | `ladder_summary.json` primary.estimate/ci, outcome, rung_decisions, per_arm |
Gate: `ladder_summary.json` primary.estimate, primary.ci, outcome. Roll-up: N10 = DONE.

### S3 — Robustness, faithfulness, export, gene-aligned (soft gate, parallel)
| Lane | Tasks | Driver check |
|---|---|---|
| robust | N11, N12 | `chr21_excluded.json`, `seed_sensitivity.json` |
| faith | N13, N14 | `pytest test_nn_faithfulness.py`, `faithfulness.json`, `nuisance_probe.json` |
| export | N15 | `cell_scores.csv.gz`, `donor_celltype_scores.csv.gz` |
| geneact | N21 | `pytest test_nn_gene_aligned.py`, `gene_activity_results.json` |

### S4 — Interpretation (hard gate). Critical: N22, N23.
N16 spectrum (`spectrum.json`, `pytest test_nn_spectrum.py`), N17 attention (`routing_attention.json`),
N22 results doc (contains the primary contrast) + unsent professor note, N23 full `pytest -q`.

### S5 — Draft paper rebuilt on real results (hard gate). Critical: N24, N27, N30, N31, N34.
Framing by rule (N24), figures incl. `fig3_ladder.png` (N25), Results + claims ledger (N27),
Discussion/Limitations (N29), Abstract/title (N30), `paper/check_paper.py` passes (N31),
self-review (N32), vault copy performed by the driver's N33 check, final label (N34).
Gate: `check_paper.py` passes and `DRAFT_V1_COMPLETE|PARTIAL` present.

## Pre-launch verification (done 2026-09-25)
- [x] `agy` smoke: Gemini read `PROTOCOL_FREEZE.md` and wrote the exact sha256 into a worktree file (SMOKE PASS).
- [x] Driver offline checks: run request executed and consumed; bad argv rejected; false DONE → TODO;
      critical BLOCKED refused; foreign edit reverted, owned edit kept.
- [x] agy settings: read/write allow rules for `/Users/anuragdani/Github/niw-eb1a/P22`
      (backup `~/.gemini/antigravity-cli/settings.json.bak-p22-2026-09-25`).
- [x] Statuses reset: N10–N17, N21–N34 TODO; N10a–N10d added. Kept: N0–N9, N18–N20, N26, N28, P1, P2.

## Risks
| Risk | Mitigation |
|---|---|
| Antigravity quota exhaustion | model fallback, then 15-min waits indefinitely |
| Gemini cannot run code | driver-run requests with log tails each call |
| Long ladder run (hours) | background job; driver polls; `--resume` on crash |
| Real result stays null | valid; paper framing chosen by rule; never tune toward a win |
| Hard gate never passes | exit 6 after 3 rounds with logs; nothing written on missing evidence |

## Monitor
`tail -f reports/generated/nn_agy/latest/swarm.log`;
per-task: `grep -H . tasks/nn/status/*`; per-call logs in `reports/generated/nn_agy/latest/`.
