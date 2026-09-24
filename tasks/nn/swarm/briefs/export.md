# P22-NN swarm lane `export` (stage S3)

You are ONE of several DeepSeek agents working in parallel, each in its own git worktree.
This worktree: `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/export` on branch `gnhf/p22-nn-export`. The orchestrator merges your branch into
`gnhf/p22-nn-cellstate` after the stage; never merge, rebase, switch branches, push or edit another worktree.

**Goal:** Professor D2 input: out-of-fold per-cell DS-state scores and MIL attention for every sampled cell.
**Your tasks, in order:** N15. Do nothing else.
**Owned files (create/edit only these):** scripts/export_nn_v2_cell_scores.py, tests/test_nn_export.py, docs/nn_v2/donor_celltype_scores.csv.gz
plus `tasks/nn/status/<your task IDs>` and your log `tasks/nn/lanes/export.md`.
**Lanes running at the same time (never touch their files):** robust (N11, N12), faith (N13, N14), geneact (N21), paper1 (N26).

Read once, then act: `tasks/nn/swarm/plan.md` section "Lane rules"; `tasks/nn/plan.md`
§0–§4 and §7; `tasks/nn/decision_tree.md` section G and your tasks' sections; your tasks'
sections in `tasks/nn/todo.md` (`sed -n '/^## N7:/,/^## N8:/p'`). New tasks P1/P2 are
specified in `tasks/nn/swarm/plan.md`.

Status (overrides every mention of the todo.md status table or Run log): write exactly one
line to `tasks/nn/status/<ID>`: `TODO` | `RUNNING:<pid>:<log>` | `DONE:<evidence>` |
`BLOCKED:<reason>:<evidence>` | `NOT_NEEDED:<evidence>`. Append one line per iteration to
`tasks/nn/lanes/export.md`. Never edit `tasks/nn/todo.md`.

Compute: at most 2 worker processes, 1 torch thread each. Heavy outputs go
under `reports/generated/nn_20260923/` (a symlink shared by all lanes). Results from
earlier stages are already merged here: read `docs/nn_v2/*` and `tasks/nn/status/*`.
Python: `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with
`PYTHONPATH=src:scripts PYTHONDONTWRITEBYTECODE=1`.

Write the full table to reports/generated/nn_20260923/spectrum/cell_scores.csv.gz. Also export the same table for the chr21-excluded arms if their models exist; otherwise record NOT_NEEDED for that part.

Finish: when every one of your tasks has a resolved status (DONE, BLOCKED or NOT_NEEDED),
return should_fully_stop=true. Null results are valid; never tune toward a win.
