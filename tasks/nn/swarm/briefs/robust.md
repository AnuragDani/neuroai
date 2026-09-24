# P22-NN swarm lane `robust` (stage S3)

You are ONE of several DeepSeek agents working in parallel, each in its own git worktree.
This worktree: `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/robust` on branch `gnhf/p22-nn-robust`. The orchestrator merges your branch into
`gnhf/p22-nn-cellstate` after the stage; never merge, rebase, switch branches, push or edit another worktree.

**Goal:** Professor D13 + D9: chr21-excluded sensitivity and init/sampling-seed sensitivity with the same frozen estimand.
**Your tasks, in order:** N11, N12. Do nothing else.
**Owned files (create/edit only these):** scripts/run_nn_v2_comparison.py, docs/nn_v2/chr21_excluded.json, docs/nn_v2/seed_sensitivity.json, docs/nn_v2/ROBUSTNESS.md
plus `tasks/nn/status/<your task IDs>` and your log `tasks/nn/lanes/robust.md`.
**Lanes running at the same time (never touch their files):** faith (N13, N14), export (N15), geneact (N21), paper1 (N26).

Read once, then act: `tasks/nn/swarm/plan.md` section "Lane rules"; `tasks/nn/plan.md`
§0–§4 and §7; `tasks/nn/decision_tree.md` section G and your tasks' sections; your tasks'
sections in `tasks/nn/todo.md` (`sed -n '/^## N7:/,/^## N8:/p'`). New tasks P1/P2 are
specified in `tasks/nn/swarm/plan.md`.

Status (overrides every mention of the todo.md status table or Run log): write exactly one
line to `tasks/nn/status/<ID>`: `TODO` | `RUNNING:<pid>:<log>` | `DONE:<evidence>` |
`BLOCKED:<reason>:<evidence>` | `NOT_NEEDED:<evidence>`. Append one line per iteration to
`tasks/nn/lanes/robust.md`. Never edit `tasks/nn/todo.md`.

Compute: at most 5 worker processes, 1 torch thread each. Heavy outputs go
under `reports/generated/nn_20260923/` (a symlink shared by all lanes). Results from
earlier stages are already merged here: read `docs/nn_v2/*` and `tasks/nn/status/*`.
Python: `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with
`PYTHONPATH=src:scripts PYTHONDONTWRITEBYTECODE=1`.

Outputs under reports/generated/nn_20260923/chr21_excluded/ and .../seeds/. Write the reading into docs/nn_v2/ROBUSTNESS.md, not LADDER.md.

Finish: when every one of your tasks has a resolved status (DONE, BLOCKED or NOT_NEEDED),
return should_fully_stop=true. Null results are valid; never tune toward a win.
