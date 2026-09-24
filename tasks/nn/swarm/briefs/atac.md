# P22-NN swarm lane `atac` (stage S1)

You are ONE of several DeepSeek agents working in parallel, each in its own git worktree.
This worktree: `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/atac` on branch `gnhf/p22-nn-atac`. The orchestrator merges your branch into
`gnhf/p22-nn-cellstate` after the stage; never merge, rebase, switch branches, push or edit another worktree.

**Goal:** Gene-activity ATAC panel (gene body +/- 2 kb) for gene-aligned cross-attention (Professor D3, D6). The only network step of the study, capped at 3.5e9 bytes.
**Your tasks, in order:** N18, N19, N20. Do nothing else.
**Owned files (create/edit only these):** scripts/quantify_development_atac.py, tests/test_quantify_development_atac.py, scripts/build_gene_activity_bed.py, scripts/estimate_fragment_transfer.py, tests/test_nn_gene_activity.py, configs/nn_gene_activity_2026-09-23.bed, configs/nn_gene_activity_2026-09-23.json, configs/nn_gene_activity_acceptance_requirements_2026-09-23.json, configs/nn_gene_activity_input_manifest_2026-09-23.json, docs/nn_v2/gene_activity_measurement.json
plus `tasks/nn/status/<your task IDs>` and your log `tasks/nn/lanes/atac.md`.
**Lanes running at the same time (never touch their files):** mil (N6, N7), tokens (N8), paper0 (P1, P2, N28).

Read once, then act: `tasks/nn/swarm/plan.md` section "Lane rules"; `tasks/nn/plan.md`
§0–§4 and §7; `tasks/nn/decision_tree.md` section G and your tasks' sections; your tasks'
sections in `tasks/nn/todo.md` (`sed -n '/^## N7:/,/^## N8:/p'`). New tasks P1/P2 are
specified in `tasks/nn/swarm/plan.md`.

Status (overrides every mention of the todo.md status table or Run log): write exactly one
line to `tasks/nn/status/<ID>`: `TODO` | `RUNNING:<pid>:<log>` | `DONE:<evidence>` |
`BLOCKED:<reason>:<evidence>` | `NOT_NEEDED:<evidence>`. Append one line per iteration to
`tasks/nn/lanes/atac.md`. Never edit `tasks/nn/todo.md`.

Compute: at most 4 worker processes, 1 torch thread each. Heavy outputs go
under `reports/generated/nn_20260923/` (a symlink shared by all lanes). Results from
earlier stages are already merged here: read `docs/nn_v2/*` and `tasks/nn/status/*`.
Python: `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with
`PYTHONPATH=src:scripts PYTHONDONTWRITEBYTECODE=1`.

N20 quantification uses --workers 8 (network threads, light CPU). Write counts to reports/generated/nn_20260923/gene_activity/. Never raise the 3.5e9 byte budget.

Finish: when every one of your tasks has a resolved status (DONE, BLOCKED or NOT_NEEDED),
return should_fully_stop=true. Null results are valid; never tune toward a win.
