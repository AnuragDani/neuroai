# P22-NN swarm lane `paper0` (stage S1)

You are ONE of several DeepSeek agents working in parallel, each in its own git worktree.
This worktree: `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/paper0` on branch `gnhf/p22-nn-paper0`. The orchestrator merges your branch into
`gnhf/p22-nn-cellstate` after the stage; never merge, rebase, switch branches, push or edit another worktree.

**Goal:** Paper tooling and the result-independent sections: checker (P1), figure script with the planted-benchmark figure (P2), Introduction + Related work (N28).
**Your tasks, in order:** P1, P2, N28. Do nothing else.
**Owned files (create/edit only these):** paper/check_paper.py, paper/make_figures.py, paper/draft.md, paper/figures/, tests/test_paper_tools.py
plus `tasks/nn/status/<your task IDs>` and your log `tasks/nn/lanes/paper0.md`.
**Lanes running at the same time (never touch their files):** mil (N6, N7), tokens (N8), atac (N18, N19, N20).

Read once, then act: `tasks/nn/swarm/plan.md` section "Lane rules"; `tasks/nn/plan.md`
§0–§4 and §7; `tasks/nn/decision_tree.md` section G and your tasks' sections; your tasks'
sections in `tasks/nn/todo.md` (`sed -n '/^## N7:/,/^## N8:/p'`). New tasks P1/P2 are
specified in `tasks/nn/swarm/plan.md`.

Status (overrides every mention of the todo.md status table or Run log): write exactly one
line to `tasks/nn/status/<ID>`: `TODO` | `RUNNING:<pid>:<log>` | `DONE:<evidence>` |
`BLOCKED:<reason>:<evidence>` | `NOT_NEEDED:<evidence>`. Append one line per iteration to
`tasks/nn/lanes/paper0.md`. Never edit `tasks/nn/todo.md`.

Compute: at most 1 worker processes, 1 torch thread each. Heavy outputs go
under `reports/generated/nn_20260923/` (a symlink shared by all lanes). Results from
earlier stages are already merged here: read `docs/nn_v2/*` and `tasks/nn/status/*`.
Python: `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with
`PYTHONPATH=src:scripts PYTHONDONTWRITEBYTECODE=1`.

P1 = decision_tree N31 checker features (1)-(5), stdlib only, parse citekeys from paper/refs_frozen.bib with regex @\w+\{([^,]+), (entries may be on one line). P2 = paper/make_figures.py with a --only planted mode that builds Fig 2 from docs/nn_v2/planted_benchmark.json (matplotlib Agg backend). N28: create paper/draft.md with a header comment, section headings (Abstract, Introduction, Related Work, Methods, Results, Discussion, Limitations, References) and write ONLY Introduction and Related Work. Framing must stay neutral (the question 'when does cross-modal attention help on paired single-cell RNA+ATAC?'); no result claims.

Finish: when every one of your tasks has a resolved status (DONE, BLOCKED or NOT_NEEDED),
return should_fully_stop=true. Null results are valid; never tune toward a win.
