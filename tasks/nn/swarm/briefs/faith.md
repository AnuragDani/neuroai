# P22-NN swarm lane `faith` (stage S3)

You are ONE of several DeepSeek agents working in parallel, each in its own git worktree.
This worktree: `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/faith` on branch `gnhf/p22-nn-faith`. The orchestrator merges your branch into
`gnhf/p22-nn-cellstate` after the stage; never merge, rebase, switch branches, push or edit another worktree.

**Goal:** Professor D9 + D1: held-out interventions (branch ablation, within donor x cell-type ATAC permutation, attention knockout, uniform MIL pooling, gate clamp, no-op and planted positive control) and nuisance probes.
**Your tasks, in order:** N13, N14. Do nothing else.
**Owned files (create/edit only these):** scripts/run_nn_v2_faithfulness.py, scripts/run_nn_v2_nuisance_probe.py, tests/test_nn_faithfulness.py, docs/nn_v2/faithfulness.json, docs/nn_v2/FAITHFULNESS.md, docs/nn_v2/nuisance_probe.json
plus `tasks/nn/status/<your task IDs>` and your log `tasks/nn/lanes/faith.md`.
**Lanes running at the same time (never touch their files):** robust (N11, N12), export (N15), geneact (N21), paper1 (N26).

Read once, then act: `tasks/nn/swarm/plan.md` section "Lane rules"; `tasks/nn/plan.md`
§0–§4 and §7; `tasks/nn/decision_tree.md` section G and your tasks' sections; your tasks'
sections in `tasks/nn/todo.md` (`sed -n '/^## N7:/,/^## N8:/p'`). New tasks P1/P2 are
specified in `tasks/nn/swarm/plan.md`.

Status (overrides every mention of the todo.md status table or Run log): write exactly one
line to `tasks/nn/status/<ID>`: `TODO` | `RUNNING:<pid>:<log>` | `DONE:<evidence>` |
`BLOCKED:<reason>:<evidence>` | `NOT_NEEDED:<evidence>`. Append one line per iteration to
`tasks/nn/lanes/faith.md`. Never edit `tasks/nn/todo.md`.

Compute: at most 5 worker processes, 1 torch thread each. Heavy outputs go
under `reports/generated/nn_20260923/` (a symlink shared by all lanes). Results from
earlier stages are already merged here: read `docs/nn_v2/*` and `tasks/nn/status/*`.
Python: `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with
`PYTHONPATH=src:scripts PYTHONDONTWRITEBYTECODE=1`.

Reload fold models from reports/generated/nn_20260923/ladder/models/; refit only if a model file is missing (deterministic, recorded grid point).

Finish: when every one of your tasks has a resolved status (DONE, BLOCKED or NOT_NEEDED),
return should_fully_stop=true. Null results are valid; never tune toward a win.
