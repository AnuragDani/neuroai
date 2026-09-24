#!/usr/bin/env python3
"""P22-NN GNHF swarm: parallel DeepSeek lanes in separate worktrees, merged stage by stage.

Stages and lanes come from tasks/nn/swarm/lanes.json; the rationale is in
tasks/nn/swarm/plan.md. Each lane runs gnhf/run_nn_cellstate.sh in its own worktree under
P22/.worktrees/<lane> (GNHF's failure rollback is `reset --hard` + `clean -fd`, so agents
must never share a checkout). Rerunning this script resumes from tasks/nn/status/*.

Usage: python3 gnhf/swarm.py [--dry-run] [--from-stage S3]
Exit: 0 done, 4 provider key/credit limit, 5 unmergeable lane branch.
"""
import argparse
import json
import os
import re
import signal
import subprocess as sp
import sys
import threading
import time
from pathlib import Path

MAIN = Path(os.environ.get("P22_MAIN", "/Users/anuragdani/Github/niw-eb1a/P22"))
CFG = json.loads((MAIN / "tasks/nn/swarm/lanes.json").read_text())
INTEG = CFG["integration_branch"]
LAUNCHER = MAIN / "gnhf/run_nn_cellstate.sh"
PY = MAIN / ".venv-p22/bin/python"
SHARED_OUT = MAIN / "reports/generated/nn_20260923"
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
LOGDIR = MAIN / "reports/generated/nn_swarm" / STAMP
RESOLVED = re.compile(r"^(DONE|BLOCKED|NOT_NEEDED)")
KEY_LIMIT = re.compile(r"key limit exceeded|insufficient credits|requires more credits|payment required", re.I)
KEY_OUT = threading.Event()
LOCK = threading.Lock()  # serializes git commands that touch the shared object store refs
STATE = {}


def log(msg):
    line = f"{time.strftime('%H:%M:%SZ', time.gmtime())} {msg}"
    print(line, flush=True)
    with open(LOGDIR / "swarm.log", "a") as fh:
        fh.write(line + "\n")


def git(*args, cwd=MAIN, check=True):
    r = sp.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed in {cwd}: {r.stderr.strip()}")
    return r


def status(root, tid):
    p = root / "tasks/nn/status" / tid
    return p.read_text().strip().splitlines()[0] if p.exists() else "TODO"


def resolved(root, tasks):
    return all(RESOLVED.match(status(root, t)) for t in tasks)


def wip_commit(root, why):
    with LOCK:
        if git("status", "--porcelain", cwd=root).stdout.strip():
            git("add", "-A", cwd=root)
            git("commit", "-q", "-m", f"chore: preserve interrupted {why} work as WIP", cwd=root)
            log(f"WIP commit in {root.name} ({why})")


def write_status(root, tasks, text, why):
    for t in tasks:
        if not RESOLVED.match(status(root, t)):
            (root / "tasks/nn/status" / t).write_text(text + "\n")
    with LOCK:
        git("add", "tasks/nn/status", cwd=root)
        git("commit", "-q", "-m", f"swarm: {why}", cwd=root, check=False)


def save_state():
    (LOGDIR / "status.json").write_text(json.dumps(STATE, indent=2))


# --- takeover of the old single-agent batch -------------------------------------------

def takeover(dry):
    if sp.run(["tmux", "has-session", "-t", "p22nn"], capture_output=True).returncode:
        return
    if dry:
        log("DRY: would wait for p22nn's next iteration end, then stop it")
        return
    runs = sorted((MAIN / ".gnhf/runs").glob("*/gnhf.log"), key=lambda p: p.stat().st_mtime)
    count = lambda: runs[-1].read_text().count('"event":"iteration:end"') if runs else 0
    base, deadline = count(), time.time() + 45 * 60
    log("old batch p22nn running; waiting for its next iteration end (max 45 min)")
    while time.time() < deadline and count() == base:
        time.sleep(20)
    table = sp.run(["ps", "-A", "-o", "pid=,ppid=,command="], capture_output=True, text=True).stdout
    procs = [(int(a), int(b), c) for a, b, c in (l.split(None, 2) for l in table.splitlines() if l.strip())]
    panes = sp.run(["tmux", "list-panes", "-s", "-t", "p22nn", "-F", "#{pane_pid}"],
                   capture_output=True, text=True).stdout.split()
    tree, frontier = set(), {int(p) for p in panes}
    while frontier:
        tree |= frontier
        frontier = {pid for pid, ppid, _ in procs if ppid in frontier} - tree
    sp.run(["tmux", "kill-session", "-t", "p22nn"])
    time.sleep(3)
    for pid, _, cmd in procs:
        # ponytail: keeps any experiment the agent started; it finishes and the lane picks it up.
        if pid in tree and "scripts/run_nn_" not in cmd:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    wip_commit(MAIN, "single-agent batch")
    log("old batch stopped")


def sync_from_todo():
    """One-way: a non-TODO row in todo.md wins over a TODO status file (old batch progress)."""
    rows = re.findall(r"^\|\s*([NP]\d+)\s*\|.*\|\s*([^|]+?)\s*\|[ \t]*$",
                      (MAIN / "tasks/nn/todo.md").read_text(), re.M)
    changed = [t for t, st in rows if st != "TODO" and status(MAIN, t) == "TODO"]
    for t, st in rows:
        if t in changed:
            (MAIN / "tasks/nn/status" / t).write_text(st + "\n")
    if changed:
        write_status(MAIN, [], "", f"sync status files from todo.md ({', '.join(changed)})")


def regen_todo_table():
    path = MAIN / "tasks/nn/todo.md"
    def cell(m):
        text = status(MAIN, m.group(1)).replace("|", "/")[:160]
        return f"{m.group(0)[: m.group(0).rindex('|', 0, -1)]}| {text} |"
    new = re.sub(r"^\|\s*([NP]\d+)\s*\|.*\|\s*[^|]*\|[ \t]*$", cell, path.read_text(), flags=re.M)
    path.write_text(new)
    with LOCK:
        if git("status", "--porcelain", "tasks/nn/todo.md").stdout.strip():
            git("commit", "-q", "-m", "chore: sync todo status table from status files", "--", "tasks/nn/todo.md")


# --- lanes ------------------------------------------------------------------------------

def ensure_worktree(lane):
    br, wt = f"gnhf/p22-nn-{lane['name']}", MAIN / ".worktrees" / lane["name"]
    with LOCK:
        if not (wt / ".git").exists():
            exists = git("rev-parse", "--verify", "--quiet", br, check=False).returncode == 0
            if exists and git("merge-base", "--is-ancestor", br, INTEG, check=False).returncode == 0:
                git("branch", "-f", br, INTEG)
            if exists:
                git("worktree", "add", str(wt), br)
            else:
                git("worktree", "add", "-b", br, str(wt), INTEG)
        if git("merge-base", "--is-ancestor", INTEG, "HEAD", cwd=wt, check=False).returncode:
            if git("merge", "--no-edit", INTEG, cwd=wt, check=False).returncode:
                git("merge", "--abort", cwd=wt, check=False)
                log(f"{lane['name']}: could not catch up with {INTEG}; continuing on its own base")
    link = wt / "reports/generated/nn_20260923"
    if not link.exists() and not link.is_symlink():
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(SHARED_OUT)
    return wt, br


def lane_brief(stage, lane, others, wt, br):
    tasks = ", ".join(lane["tasks"])
    return f"""# P22-NN swarm lane `{lane['name']}` (stage {stage['id']})

You are ONE of several DeepSeek agents working in parallel, each in its own git worktree.
This worktree: `{wt}` on branch `{br}`. The orchestrator merges your branch into
`{INTEG}` after the stage; never merge, rebase, switch branches, push or edit another worktree.

**Goal:** {lane['goal']}
**Your tasks, in order:** {tasks}. Do nothing else.
**Owned files (create/edit only these):** {', '.join(lane['owns'])}
plus `tasks/nn/status/<your task IDs>` and your log `tasks/nn/lanes/{lane['name']}.md`.
**Lanes running at the same time (never touch their files):** {others or 'none'}.

Read once, then act: `tasks/nn/swarm/plan.md` section "Lane rules"; `tasks/nn/plan.md`
§0–§4 and §7; `tasks/nn/decision_tree.md` section G and your tasks' sections; your tasks'
sections in `tasks/nn/todo.md` (`sed -n '/^## N7:/,/^## N8:/p'`). New tasks P1/P2 are
specified in `tasks/nn/swarm/plan.md`.

Status (overrides every mention of the todo.md status table or Run log): write exactly one
line to `tasks/nn/status/<ID>`: `TODO` | `RUNNING:<pid>:<log>` | `DONE:<evidence>` |
`BLOCKED:<reason>:<evidence>` | `NOT_NEEDED:<evidence>`. Append one line per iteration to
`tasks/nn/lanes/{lane['name']}.md`. Never edit `tasks/nn/todo.md`.

Compute: at most {lane['workers']} worker processes, 1 torch thread each. Heavy outputs go
under `reports/generated/nn_20260923/` (a symlink shared by all lanes). Results from
earlier stages are already merged here: read `docs/nn_v2/*` and `tasks/nn/status/*`.
Python: `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` with
`PYTHONPATH=src:scripts PYTHONDONTWRITEBYTECODE=1`.

{lane.get('extra', '')}

Finish: when every one of your tasks has a resolved status (DONE, BLOCKED or NOT_NEEDED),
return should_fully_stop=true. Null results are valid; never tune toward a win.
"""


def run_lane(stage, lane, others, dry):
    try:
        _run_lane(stage, lane, others, dry)
    except Exception as exc:  # noqa: BLE001 - a lane crash must not kill the swarm
        STATE[lane["name"]] = f"crashed: {exc}"
        log(f"{lane['name']}: CRASHED {exc!r}")


def _run_lane(stage, lane, others, dry):
    name = lane["name"]
    wt, br = ensure_worktree(lane)
    brief = LOGDIR / "prompts" / f"{name}.md"
    brief.write_text(lane_brief(stage, lane, others, wt, br))
    ids = " ".join(lane["tasks"])
    env = os.environ | {
        "P22_NN_WORKTREE": str(wt), "NN_BRANCH": br, "NN_PROMPT": str(brief),
        "NN_MAX_ITER": "30",
        "NN_AGENT_TASK": (f"You are swarm lane {name}. Execute the lane brief given as the objective: "
                          f"tasks {ids} only. Each iteration: read tasks/nn/status/<ID> for your tasks, pick the "
                          "first unresolved one, read its sections in tasks/nn/todo.md and tasks/nn/decision_tree.md "
                          "with sed, do ONE numbered step, run focused pytest and ruff, update tasks/nn/status/<ID> "
                          f"and append to tasks/nn/lanes/{name}.md. Never edit tasks/nn/todo.md. Never ask the user; "
                          "on failure record BLOCKED with evidence. Never cat files over 200 lines or print arrays. "
                          "Use no subagents."),
        "NN_STOP_WHEN": (f"Every task in [{ids}] has a file tasks/nn/status/<ID> whose line starts with DONE, "
                         "BLOCKED or NOT_NEEDED. Null results are valid; never tune toward a win."),
    }
    if dry:
        r = sp.run(["bash", str(LAUNCHER), "--check"], env=env, capture_output=True, text=True)
        STATE[name] = "dry-ok" if r.returncode == 0 else f"dry-FAIL: {r.stderr.strip()[-300:]}"
        return
    prev, stalls = int(git("rev-list", "--count", "HEAD", cwd=wt).stdout), 0
    for attempt in range(1, lane["attempts"] + 1):
        if resolved(wt, lane["tasks"]) or KEY_OUT.is_set():
            break
        wip_commit(wt, name)
        STATE[name] = f"attempt {attempt}/{lane['attempts']}"
        save_state()
        out = LOGDIR / f"{name}_attempt{attempt}.log"
        with open(out, "w") as fh:
            rc = sp.run(["bash", str(LAUNCHER)], env=env, stdout=fh, stderr=sp.STDOUT).returncode
        wip_commit(wt, name)
        text = out.read_text(errors="replace")
        runs = sorted((wt / ".gnhf/runs").glob("*/gnhf.log"), key=lambda p: p.stat().st_mtime)
        if KEY_LIMIT.search(text) or (runs and KEY_LIMIT.search(runs[-1].read_text(errors="replace")[-20000:])):
            KEY_OUT.set()
            log(f"{name}: provider key/credit limit detected; stopping the swarm")
            break
        now = int(git("rev-list", "--count", "HEAD", cwd=wt).stdout)
        stalls = stalls + 1 if now <= prev else 0
        prev = now
        log(f"{name}: attempt {attempt} rc={rc} commits={now} stalls={stalls} "
            f"status={[status(wt, t)[:12] for t in lane['tasks']]}")
        if stalls >= 3:
            write_status(wt, lane["tasks"], "BLOCKED:lane_stalled:no commit in 3 attempts", f"{name} stalled")
            break
    else:
        write_status(wt, lane["tasks"], "BLOCKED:lane_attempts_exhausted", f"{name} out of attempts")
    STATE[name] = "key_out" if KEY_OUT.is_set() else "finished"
    save_state()


# --- integration --------------------------------------------------------------------------

def fixer(instruction, stop_when, tag):
    brief = LOGDIR / "prompts" / f"fixer_{tag}.md"
    brief.write_text(f"# P22-NN integration fixer ({tag})\n\nWork in `{MAIN}` on `{INTEG}`.\n\n{instruction}\n\n"
                     "Preserve both sides' intent; never delete results, evidence or tests to make them pass; "
                     "never change a frozen protocol field. Run `PY -m pytest -q -x tests/test_nn_*.py`. Commit.\n")
    env = os.environ | {"NN_PROMPT": str(brief), "NN_MAX_ITER": "8", "NN_STOP_WHEN": stop_when,
                        "NN_AGENT_TASK": instruction + " Never ask the user. Use no subagents."}
    with open(LOGDIR / f"fixer_{tag}.log", "w") as fh:
        sp.run(["bash", str(LAUNCHER)], env=env, stdout=fh, stderr=sp.STDOUT)
    wip_commit(MAIN, f"fixer {tag}")


def tests_pass():
    files = sorted(str(p.relative_to(MAIN)) for p in (MAIN / "tests").glob("test_nn_*.py"))
    files += ["tests/test_paper_tools.py"] if (MAIN / "tests/test_paper_tools.py").exists() else []
    env = os.environ | {"PYTHONPATH": "src:scripts", "PYTHONDONTWRITEBYTECODE": "1"}
    r = sp.run([str(PY), "-m", "pytest", "-q", "-x", *files], cwd=MAIN, env=env, capture_output=True, text=True)
    (LOGDIR / "pytest_last.log").write_text(r.stdout[-8000:] + r.stderr[-4000:])
    return r.returncode == 0


def integrate(stage):
    for lane in stage["lanes"]:
        br = f"gnhf/p22-nn-{lane['name']}"
        if git("rev-parse", "--verify", "--quiet", br, check=False).returncode:
            continue
        if git("merge-base", "--is-ancestor", br, INTEG, check=False).returncode == 0:
            continue
        if git("merge", "--no-ff", "--no-edit", br, check=False).returncode:
            git("merge", "--abort", check=False)
            log(f"merge conflict on {br}; launching fixer")
            fixer(f"Run `git merge --no-ff {br}` and resolve every conflict, then commit the merge.",
                  f"Branch {br} is an ancestor of HEAD and tests/test_nn_*.py pass.", f"merge_{lane['name']}")
            if git("merge-base", "--is-ancestor", br, "HEAD", check=False).returncode:
                log(f"FATAL: {br} still unmerged after fixer")
                sys.exit(5)
        log(f"merged {br}")
    ok = tests_pass()
    if not ok:
        log(f"{stage['id']}: focused tests fail after merge; launching fixer")
        fixer("The focused tests fail on the integration branch after merging this stage's lanes. "
              "See reports/generated/nn_swarm/latest/pytest_last.log. Fix the code so they pass "
              "without changing any saved result.", "tests/test_nn_*.py pass.", f"tests_{stage['id']}")
        ok = tests_pass()
    gates = {f: (MAIN / f).exists() for f in stage["gate_files"]}
    tasks = [t for lane in stage["lanes"] for t in lane["tasks"]]
    record = {"stage": stage["id"], "tests_pass": ok, "gate_files": gates,
              "status": {t: status(MAIN, t)[:80] for t in tasks},
              "verdict": "PASS" if ok and all(gates.values()) else "FAIL"}
    path = LOGDIR / "gates.json"
    old = json.loads(path.read_text()) if path.exists() else []
    path.write_text(json.dumps(old + [record], indent=2))
    regen_todo_table()
    log(f"{stage['id']} gate {record['verdict']}: tests={ok} files={gates}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--from-stage", default=None)
    args = ap.parse_args()
    (LOGDIR / "prompts").mkdir(parents=True, exist_ok=True)
    latest = LOGDIR.parent / "latest"
    if latest.is_symlink() or latest.exists():
        latest.unlink()
    latest.symlink_to(LOGDIR)
    if git("branch", "--show-current").stdout.strip() != INTEG:
        sys.exit(f"main checkout must be on {INTEG}")
    takeover(args.dry_run)
    if not args.dry_run:
        sync_from_todo()
    started = args.from_stage is None
    for stage in CFG["stages"]:
        started = started or stage["id"] == args.from_stage
        todo = [lane for lane in stage["lanes"] if not resolved(MAIN, lane["tasks"])]
        if not started or not todo:
            log(f"{stage['id']}: skipped ({'before --from-stage' if not started else 'already resolved'})")
            continue
        log(f"{stage['id']} start: {[lane['name'] for lane in todo]} — {stage['goal']}")
        threads = []
        for lane in todo:
            others = ", ".join(f"{o['name']} ({', '.join(o['tasks'])})" for o in todo if o is not lane)
            t = threading.Thread(target=run_lane, args=(stage, lane, others, args.dry_run))
            t.start()
            threads.append(t)
            time.sleep(0 if args.dry_run else 30)  # stagger OpenCode server start-up
        for t in threads:
            t.join()
        save_state()
        if args.dry_run:
            log(f"DRY {stage['id']}: {json.dumps({l['name']: STATE.get(l['name']) for l in todo})}")
            continue
        if KEY_OUT.is_set():
            integrate(stage)
            log("stopped: provider key/credit limit. Top up, then rerun gnhf/swarm.py to resume.")
            sys.exit(4)
        integrate(stage)
    log("swarm finished" if not args.dry_run else "dry run finished")


if __name__ == "__main__":
    main()
