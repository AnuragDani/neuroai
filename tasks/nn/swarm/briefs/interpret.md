# P22-NN swarm lane `interpret` (stage S4)

You are ONE of several DeepSeek agents working in parallel, each in its own git worktree.
This worktree: `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/interpret` on branch `gnhf/p22-nn-interpret`. The orchestrator merges your branch into
`gnhf/p22-nn-cellstate` after the stage; never merge, rebase, switch branches, push or edit another worktree.

**Goal:** Professor D2 (cell-state spectrum), D9 (attention only where interventions show use), D11 (clear written conclusion); results doc and unsent professor note.
**Your tasks, in order:** N16, N17, N22, N23. Do nothing else.
**Owned files (create/edit only these):** scripts/analyze_nn_v2_spectrum.py, scripts/describe_nn_v2_attention.py, tests/test_nn_spectrum.py, docs/nn_v2/spectrum.json, docs/nn_v2/SPECTRUM.md, docs/nn_v2/routing_attention.json, docs/nn_v2/ROUTING_ATTENTION.md, docs/nn_v2/NN_V2_RESULTS_2026-09-23.md, docs/nn_v2/PROFESSOR_NOTE_UNSENT.md, docs/nn_v2/FUTURE_WORK.md
plus `tasks/nn/status/<your task IDs>` and your log `tasks/nn/lanes/interpret.md`.
**Lanes running at the same time (never touch their files):** none.

Read once, then act: `tasks/nn/swarm/plan.md` section "Lane rules"; `tasks/nn/plan.md`
§0–§4 and §7; `tasks/nn/decision_tree.md` section G and your tasks' sections; your tasks'
sections in `tasks/nn/todo.md` (`sed -n '/^## N7:/,/^## N8:/p'`). New tasks P1/P2 are
specified in `tasks/nn/swarm/plan.md`.

Status (overrides every mention of the todo.md status table or Run log): write exactly one
line to `tasks/nn/status/<ID>`: `TODO` | `RUNNING:<pid>:<log>` | `DONE:<evidence>` |
`BLOCKED:<reason>:<evidence>` | `NOT_NEEDED:<evidence>`. Append one line per iteration to
`tasks/nn/lanes/interpret.md`. Never edit `tasks/nn/todo.md`.

Compute: at most 8 worker processes, 1 torch thread each. Heavy outputs go
under `reports/generated/nn_20260923/` (a symlink shared by all lanes). Results from
earlier stages are already merged here: read `docs/nn_v2/*` and `tasks/nn/status/*`.
Python: `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with
`PYTHONPATH=src:scripts PYTHONDONTWRITEBYTECODE=1`.



Finish: when every one of your tasks has a resolved status (DONE, BLOCKED or NOT_NEEDED),
return should_fully_stop=true. Null results are valid; never tune toward a win.
