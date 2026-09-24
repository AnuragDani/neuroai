# P22-NN swarm lane `paper` (stage S5)

You are ONE of several DeepSeek agents working in parallel, each in its own git worktree.
This worktree: `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/paper` on branch `gnhf/p22-nn-paper`. The orchestrator merges your branch into
`gnhf/p22-nn-cellstate` after the stage; never merge, rebase, switch branches, push or edit another worktree.

**Goal:** First draft paper (DRAFT_V1) that traces every number to docs/nn_v2 evidence and cites only paper/refs_frozen.bib.
**Your tasks, in order:** N24, N25, N27, N29, N30, N31, N32, N33, N34. Do nothing else.
**Owned files (create/edit only these):** paper/
plus `tasks/nn/status/<your task IDs>` and your log `tasks/nn/lanes/paper.md`.
**Lanes running at the same time (never touch their files):** none.

Read once, then act: `tasks/nn/swarm/plan.md` section "Lane rules"; `tasks/nn/plan.md`
§0–§4 and §7; `tasks/nn/decision_tree.md` section G and your tasks' sections; your tasks'
sections in `tasks/nn/todo.md` (`sed -n '/^## N7:/,/^## N8:/p'`). New tasks P1/P2 are
specified in `tasks/nn/swarm/plan.md`.

Status (overrides every mention of the todo.md status table or Run log): write exactly one
line to `tasks/nn/status/<ID>`: `TODO` | `RUNNING:<pid>:<log>` | `DONE:<evidence>` |
`BLOCKED:<reason>:<evidence>` | `NOT_NEEDED:<evidence>`. Append one line per iteration to
`tasks/nn/lanes/paper.md`. Never edit `tasks/nn/todo.md`.

Compute: at most 2 worker processes, 1 torch thread each. Heavy outputs go
under `reports/generated/nn_20260923/` (a symlink shared by all lanes). Results from
earlier stages are already merged here: read `docs/nn_v2/*` and `tasks/nn/status/*`.
Python: `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with
`PYTHONPATH=src:scripts PYTHONDONTWRITEBYTECODE=1`.

One section per iteration. Run python paper/check_paper.py after every section once N31 starts. N33 is the only write allowed outside the worktree.

Finish: when every one of your tasks has a resolved status (DONE, BLOCKED or NOT_NEEDED),
return should_fully_stop=true. Null results are valid; never tune toward a win.
