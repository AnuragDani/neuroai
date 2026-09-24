# P22-NN swarm lane `ladder` (stage S2)

You are ONE of several DeepSeek agents working in parallel, each in its own git worktree.
This worktree: `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/ladder` on branch `gnhf/p22-nn-ladder`. The orchestrator merges your branch into
`gnhf/p22-nn-cellstate` after the stage; never merge, rebase, switch branches, push or edit another worktree.

**Goal:** Professor D1 + D5: frozen, apple-to-apple ladder R0-R4 of cross-attention vs matched token-concat, plus linear, pseudobulk, chr21, latent and majority controls; primary contrast with donor-bootstrap CI.
**Your tasks, in order:** N9, N10. Do nothing else.
**Owned files (create/edit only these):** src/p22/eval/nn_factory.py, configs/nn_protocol_v2_2026-09-23.json, configs/nn_protocol_v2_amendment_*.json, configs/nn_amendment_*.json, docs/nn_v2/PROTOCOL_FREEZE.md, docs/nn_v2/parameter_counts.json, scripts/run_nn_v2_comparison.py, scripts/summarize_nn_v2.py, tests/test_nn_factory.py, tests/test_nn_runner.py, docs/nn_v2/ladder_summary.json, docs/nn_v2/LADDER.md
plus `tasks/nn/status/<your task IDs>` and your log `tasks/nn/lanes/ladder.md`.
**Lanes running at the same time (never touch their files):** none.

Read once, then act: `tasks/nn/swarm/plan.md` section "Lane rules"; `tasks/nn/plan.md`
§0–§4 and §7; `tasks/nn/decision_tree.md` section G and your tasks' sections; your tasks'
sections in `tasks/nn/todo.md` (`sed -n '/^## N7:/,/^## N8:/p'`). New tasks P1/P2 are
specified in `tasks/nn/swarm/plan.md`.

Status (overrides every mention of the todo.md status table or Run log): write exactly one
line to `tasks/nn/status/<ID>`: `TODO` | `RUNNING:<pid>:<log>` | `DONE:<evidence>` |
`BLOCKED:<reason>:<evidence>` | `NOT_NEEDED:<evidence>`. Append one line per iteration to
`tasks/nn/lanes/ladder.md`. Never edit `tasks/nn/todo.md`.

Compute: at most 14 worker processes, 1 torch thread each. Heavy outputs go
under `reports/generated/nn_20260923/` (a symlink shared by all lanes). Results from
earlier stages are already merged here: read `docs/nn_v2/*` and `tasks/nn/status/*`.
Python: `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with
`PYTHONPATH=src:scripts PYTHONDONTWRITEBYTECODE=1`.

Save every fold model state_dict plus its fold preprocessing evidence (selected genes, regions, scaler/IDF/NMF parameters, grid point) under reports/generated/nn_20260923/ladder/models/<arm>/r<rep>_f<fold>.pt and .json; N13 and N15 in stage S3 reload them instead of refitting. Runner flags --arms, --repeats, --resume, --workers, --exclude-chr21, --model-seed, --sampling-seed must exist (S3 lanes use them). Use at most 14 worker processes, 1 torch thread each.

Finish: when every one of your tasks has a resolved status (DONE, BLOCKED or NOT_NEEDED),
return should_fully_stop=true. Null results are valid; never tune toward a win.
