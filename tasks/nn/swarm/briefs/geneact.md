# P22-NN swarm lane `geneact` (stage S3)

You are ONE of several DeepSeek agents working in parallel, each in its own git worktree.
This worktree: `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/geneact` on branch `gnhf/p22-nn-geneact`. The orchestrator merges your branch into
`gnhf/p22-nn-cellstate` after the stage; never merge, rebase, switch branches, push or edit another worktree.

**Goal:** Professor D3 + D6: gene-aligned cross-attention (RNA gene g attends to ATAC gene-activity g and genomic neighbours) vs matched token-concat on the gene-activity panel. Secondary analysis.
**Your tasks, in order:** N21. Do nothing else.
**Owned files (create/edit only these):** src/p22/models/gene_aligned.py, tests/test_nn_gene_aligned.py, scripts/run_nn_v2_gene_activity.py, configs/nn_protocol_v2_amendment_gene_activity.json, docs/nn_v2/gene_activity_results.json, docs/nn_v2/GENE_ACTIVITY.md
plus `tasks/nn/status/<your task IDs>` and your log `tasks/nn/lanes/geneact.md`.
**Lanes running at the same time (never touch their files):** robust (N11, N12), faith (N13, N14), export (N15), paper1 (N26).

Read once, then act: `tasks/nn/swarm/plan.md` section "Lane rules"; `tasks/nn/plan.md`
§0–§4 and §7; `tasks/nn/decision_tree.md` section G and your tasks' sections; your tasks'
sections in `tasks/nn/todo.md` (`sed -n '/^## N7:/,/^## N8:/p'`). New tasks P1/P2 are
specified in `tasks/nn/swarm/plan.md`.

Status (overrides every mention of the todo.md status table or Run log): write exactly one
line to `tasks/nn/status/<ID>`: `TODO` | `RUNNING:<pid>:<log>` | `DONE:<evidence>` |
`BLOCKED:<reason>:<evidence>` | `NOT_NEEDED:<evidence>`. Append one line per iteration to
`tasks/nn/lanes/geneact.md`. Never edit `tasks/nn/todo.md`.

Compute: at most 4 worker processes, 1 torch thread each. Heavy outputs go
under `reports/generated/nn_20260923/` (a symlink shared by all lanes). Results from
earlier stages are already merged here: read `docs/nn_v2/*` and `tasks/nn/status/*`.
Python: `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with
`PYTHONPATH=src:scripts PYTHONDONTWRITEBYTECODE=1`.

If tasks/nn/status/N20 is not DONE, write NOT_NEEDED:upstream N20 <status> to tasks/nn/status/N21 and stop. Do not edit scripts/run_nn_v2_comparison.py (robust lane owns it); import its functions instead.

Finish: when every one of your tasks has a resolved status (DONE, BLOCKED or NOT_NEEDED),
return should_fully_stop=true. Null results are valid; never tune toward a win.
