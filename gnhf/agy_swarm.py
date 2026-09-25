#!/usr/bin/env python3
"""P22-NN v3 driver: Gemini (agy) lanes in worktrees; the DRIVER runs every check and command.

Why a driver and not GNHF: GNHF has no agy agent, and its failure rollback (`reset --hard`)
erased the DeepSeek ladder runner five times. Here every agy call is committed, nothing is
reset, and DONE only counts after the driver's own check passes (tasks/nn/swarm/agy_lanes.json).
agy runs with --sandbox (no shell): it edits files and asks for runs via tasks/nn/run/<ID>.json.

Usage: python3 gnhf/agy_swarm.py [--from-stage S3] [--smoke]
Exit: 0 done, 5 unmergeable branch, 6 hard gate still failing after 3 rounds.
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess as sp
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import swarm as S  # noqa: E402  (reuse git/status/worktree helpers)

CFG = json.loads((S.MAIN / "tasks/nn/swarm/agy_lanes.json").read_text())
S.LOGDIR = S.MAIN / "reports/generated/nn_agy" / S.STAMP
MODELS = CFG["models"]
QUOTA = re.compile(r"RESOURCE_EXHAUSTED|quota|rate.?limit|\b429\b|exceeded your|try again later", re.I)
RUN_OK = re.compile(r"^(scripts|paper|gnhf)/[\w./-]+\.py$")
ENV = os.environ | {"PYTHONPATH": "src:scripts", "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "1"}
JOBS = {}  # (lane, task) -> (Popen, log path)
VAULT_PAPER = "/Users/anuragdani/Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/paper-nn"


def sh(cmd, cwd, timeout=3600):
    if cmd.startswith("PY "):
        cmd = f"{S.PY} {cmd[3:]}"
    try:
        r = sp.run(["bash", "-c", cmd], cwd=cwd, env=ENV, capture_output=True, text=True, timeout=timeout)
    except sp.TimeoutExpired:
        return 124, f"TIMEOUT after {timeout}s"
    return r.returncode, (r.stdout[-2500:] + ("\n" + r.stderr[-1500:] if r.stderr.strip() else ""))


def tail(path, n=2500):
    try:
        return Path(path).read_text(errors="replace")[-n:]
    except OSError:
        return "(no log)"


def commit(root, msg):
    with S.LOCK:
        if S.git("status", "--porcelain", cwd=root).stdout.strip():
            S.git("add", "-A", cwd=root)
            S.git("commit", "-q", "-m", msg, cwd=root)
            return True
    return False


def set_status(root, tid, text):
    (root / "tasks/nn/status" / tid).write_text(text + "\n")
    commit(root, f"agy-driver: {tid} -> {text[:40]}")


# --- per-lane verification (the driver decides DONE) ---------------------------------------

def check_task(wt, lane, tid):
    outs, ok = [], True
    for cmd in lane.get("checks", {}).get(tid, []):
        rc, out = sh(cmd, wt, 1800)
        outs.append(f"$ {cmd}\n[exit {rc}]\n{out.strip()[-1200:]}")
        ok = ok and rc == 0
    return ok, "\n".join(outs)


def verify(wt, lane, verified):
    report, open_tasks = [], []
    for t in lane["tasks"]:
        st = S.status(wt, t)
        if t in verified and st.startswith("DONE"):
            report.append(f"{t}: verified")
            continue
        if st.startswith("DONE"):
            ok, out = check_task(wt, lane, t)
            if ok:
                verified.add(t)
                report.append(f"{t}: DONE verified by driver")
            else:
                set_status(wt, t, "TODO")
                report.append(f"{t}: your DONE was REJECTED, the check failed. Fix it:\n{out}")
                open_tasks.append(t)
        elif st.startswith(("BLOCKED", "NOT_NEEDED")):
            if t in lane.get("critical", []):
                set_status(wt, t, "TODO")
                report.append(f"{t}: {st[:120]} is NOT accepted: {t} is on the critical path. "
                              "Use the decision-tree fallback and complete it.")
                open_tasks.append(t)
            else:
                report.append(f"{t}: accepted as {st[:100]}")
        else:
            report.append(f"{t}: {st[:100]}")
            open_tasks.append(t)
    return open_tasks, "\n".join(report)


# --- file guard and run requests ------------------------------------------------------------

def allowed(path, lane):
    pats = (lane["owns"] + [f"tasks/nn/status/{t}" for t in lane["tasks"]]
            + [f"tasks/nn/run/{t}.json" for t in lane["tasks"]] + [f"tasks/nn/lanes/{lane['name']}.md"])
    return any(path == p or (p.endswith("/") and path.startswith(p)) or fnmatch.fnmatch(path, p) for p in pats)


def revert_foreign(root, ok):
    tracked = S.git("diff", "--name-only", "HEAD", cwd=root).stdout.split("\n")
    untracked = S.git("ls-files", "--others", "--exclude-standard", cwd=root).stdout.split("\n")
    bad = [p for p in tracked + untracked if p and not ok(p)]
    for p in bad:
        if p in tracked:
            S.git("checkout", "HEAD", "--", p, cwd=root, check=False)
        else:
            (root / p).unlink(missing_ok=True)
    return bad


def handle_runs(wt, lane):
    notes = []
    for t in lane["tasks"]:
        req_path = wt / "tasks/nn/run" / f"{t}.json"
        if not req_path.exists():
            continue
        try:
            req = json.loads(req_path.read_text())
            argv = [str(a) for a in req["argv"]]
        except (ValueError, KeyError, TypeError) as exc:
            argv, req = [], {}
            notes.append(f"run request {t}: invalid JSON ({exc}); expected {{\"argv\": [...]}}")
        req_path.unlink()
        commit(wt, f"agy-driver: consumed run request {t}")
        if not argv:
            continue
        if not (RUN_OK.match(argv[0]) or argv[:2] == ["-m", "pytest"]):
            notes.append(f"run request {t}: REJECTED argv[0]={argv[0]!r} (must be scripts|paper|gnhf/*.py or -m pytest)")
            continue
        logp = S.SHARED_OUT / "runs" / f"{lane['name']}_{t}_{time.strftime('%Y%m%dT%H%M%S')}.log"
        logp.parent.mkdir(parents=True, exist_ok=True)
        cmd = [str(S.PY), *argv]
        if req.get("background"):
            fh = open(logp, "w")
            proc = sp.Popen(cmd, cwd=wt, env=ENV, stdout=fh, stderr=sp.STDOUT, start_new_session=True)
            JOBS[(lane["name"], t)] = (proc, logp)
            set_status(wt, t, f"RUNNING:{proc.pid}:{logp}")
            notes.append(f"run {t}: started in background, pid {proc.pid}, log {logp}")
            S.log(f"{lane['name']}: background {t} pid {proc.pid}: {' '.join(argv)[:160]}")
        else:
            minutes = min(int(req.get("timeout_min", 20)), 60)
            try:
                with open(logp, "w") as fh:
                    rc = sp.run(cmd, cwd=wt, env=ENV, stdout=fh, stderr=sp.STDOUT, timeout=minutes * 60).returncode
            except sp.TimeoutExpired:
                rc = "TIMEOUT"
            notes.append(f"run {t}: `{' '.join(argv)}` exit {rc}; log {logp}; tail:\n{tail(logp, 2000)}")
    return notes


# --- one lane --------------------------------------------------------------------------------

PREAMBLE = """Workspace root: {wt}
Every path below is relative to that root; give your file tools absolute paths.

You are the Gemini agent for lane `{name}` of the P22-NN study (stage {stage}). You have NO shell:
never try to run a command. You edit files; the DRIVER does everything else after each call:
it commits your edits, REVERTS edits to files you do not own, re-runs the acceptance check of
every task you mark DONE (a false DONE is rejected and set back to TODO), and executes your run
requests. Its output is at the end of this message: fix any failure there FIRST.

Run requests: to run code, write `tasks/nn/run/<TASK>.json` =
{{"argv": ["scripts/some_script.py", "--flag", "value"], "background": false, "timeout_min": 20}}
argv[0] must be a .py file under scripts/, paper/ or gnhf/, or argv may start with "-m", "pytest".
The driver runs it with the project Python (PYTHONPATH=src:scripts) in this worktree and shows
you the log tail next call. Use "background": true for anything longer than 20 minutes; the
driver waits for it and calls you when it ends. At most {workers} worker processes per run.

Status: exactly one line in `tasks/nn/status/<ID>`: TODO | DONE:<evidence> |
BLOCKED:<reason>:<evidence> | NOT_NEEDED:<evidence>. Append one line per call to
`tasks/nn/lanes/{name}.md`. Do ONE coherent step per call (write one module and its tests, OR
request one run, OR write one evidence file), then stop.
"""


def orphan_running(wt, lane):
    """A RUNNING:<pid> status from an earlier driver process whose job is still alive."""
    for t in lane["tasks"]:
        st = S.status(wt, t)
        if st.startswith("RUNNING:") and (lane["name"], t) not in JOBS:
            try:
                os.kill(int(st.split(":")[1]), 0)
                return True
            except (ValueError, ProcessLookupError, PermissionError):
                set_status(wt, t, "TODO")
    return False


def lane_prompt(stage, lane, wt, report, feedback, idle):
    owns = "\n".join(f"- {p}" for p in lane["owns"])
    checks = "\n".join(f"- {t}: {' && '.join(c)}" for t, c in lane.get("checks", {}).items())
    nudge = ("\nYou changed nothing in your last calls. Take the SMALLEST next step now (one file or one "
             "run request). If a task truly cannot be done, say why in its status with evidence.\n") if idle >= 2 else ""
    return (PREAMBLE.format(wt=wt, name=lane["name"], stage=stage["id"], workers=lane.get("workers", 2))
            + f"""
## Goal
{lane['goal']}

## Your tasks, in order: {', '.join(lane['tasks'])}
Specs: the `## <ID>:` sections of tasks/nn/todo.md; IF/ELSE rules: tasks/nn/decision_tree.md
section G plus each task's section (for N10a–N10d use section N10). Science, assumptions and
honesty rules: tasks/nn/plan.md §0–§4 and §7 (they override anything else). Earlier results:
docs/nn_v2/*, tasks/nn/status/*. Ignore GNHF-specific instructions in those files.

## Files you own (everything else is reverted)
{owns}
- tasks/nn/status/<your IDs>, tasks/nn/run/<your IDs>.json, tasks/nn/lanes/{lane['name']}.md

## Driver acceptance checks (must pass before a DONE counts)
{checks}

{lane.get('extra', '')}
{nudge}
## Driver report (current task states)
{report}

## Driver output from your last call
{feedback}
""")


def call_agy(wt, prompt, model, n, name):
    logp = S.LOGDIR / f"{name}_call{n:03d}.log"
    try:
        with open(logp, "w") as fh:
            rc = sp.run(["agy", "-p", prompt, "--add-dir", str(wt), "--model", model, "--mode", "accept-edits",
                         "--sandbox", "--print-timeout", "45m"], cwd=wt, stdout=fh, stderr=sp.STDOUT,
                        timeout=50 * 60).returncode
    except sp.TimeoutExpired:
        rc = "TIMEOUT"
    return rc, tail(logp, 4000)


def run_lane(stage, lane):
    try:
        return _run_lane(stage, lane)
    except Exception as exc:  # noqa: BLE001 - one lane must not kill the others
        S.log(f"{lane['name']}: CRASHED {exc!r}")
        return "crashed"


def _run_lane(stage, lane):
    name = lane["name"]
    wt, _ = S.ensure_worktree(lane)
    commit(wt, f"chore: preserve leftovers in {name} before agy lane")
    verified, calls, idle, model_i, feedback = set(), 0, 0, 0, "(first call of this round)"
    while True:
        mine = {k: v for k, v in JOBS.items() if k[0] == name}
        if any(p.poll() is None for p, _ in mine.values()) or orphan_running(wt, lane):
            time.sleep(120)
            continue
        for key, (proc, logp) in mine.items():
            del JOBS[key]
            if S.status(wt, key[1]).startswith("RUNNING"):
                set_status(wt, key[1], "TODO")
            feedback = f"Background run {key[1]} ended with exit {proc.returncode}. Log {logp}, tail:\n{tail(logp)}"
        open_tasks, report = verify(wt, lane, verified)
        S.STATE[name] = f"calls {calls}/{lane['max_calls']} open {open_tasks}"
        S.save_state()
        if not open_tasks:
            S.log(f"{name}: all tasks verified after {calls} calls")
            return "verified"
        if calls >= lane["max_calls"]:
            for t in open_tasks:
                if t not in lane.get("critical", []):
                    set_status(wt, t, f"BLOCKED:agy_call_cap:{calls} calls; see tasks/nn/lanes/{name}.md")
            S.log(f"{name}: call cap reached; open {open_tasks}")
            return "capped"
        prompt = lane_prompt(stage, lane, wt, report, feedback, idle)
        rc, out = call_agy(wt, prompt, MODELS[model_i], calls + 1, name)
        changed_files = S.git("status", "--porcelain", cwd=wt).stdout.strip()
        if QUOTA.search(out) and not changed_files:
            model_i = (model_i + 1) % len(MODELS)
            S.log(f"{name}: quota/rate limit; switching to {MODELS[model_i]}"
                  + ("" if model_i else " after a 15 min wait"))
            if model_i == 0:
                time.sleep(900)
            continue
        calls += 1
        bad = revert_foreign(wt, lambda p: allowed(p, lane))
        changed = commit(wt, f"agy {name}: call {calls}")
        notes = handle_runs(wt, lane)
        idle = 0 if (changed or notes) else idle + 1
        feedback = "\n\n".join(filter(None, [
            f"Reverted (not your files): {bad}" if bad else "",
            *notes,
            f"agy exit {rc}; last output:\n{out[-1500:]}",
        ]))
        S.log(f"{name}: call {calls} rc={rc} changed={changed} runs={len(notes)} idle={idle}")
        if idle >= 8:
            S.log(f"{name}: 8 idle calls in a row")
            calls = max(calls, lane["max_calls"])  # ends the round; hard gates decide what happens next


# --- integration ------------------------------------------------------------------------------

def agy_fix(instruction, files, tag, test_cmd):
    """Bounded agy repair in the main checkout; the driver re-runs `test_cmd` after every call."""
    for n in range(1, 6):
        rc, out = sh(test_cmd, S.MAIN, 1800)
        if rc == 0:
            return True
        prompt = (f"Workspace root: {S.MAIN}\nYou have NO shell. Edit only these files: {files}.\n\n"
                  f"{instruction}\n\nPreserve both sides' intent; never delete results, tests or evidence; never "
                  f"change a frozen protocol field.\n\n## Driver output\n$ {test_cmd}\n{out[-3000:]}")
        call_agy(S.MAIN, prompt, MODELS[0], n, f"fix_{tag}")
        revert_foreign(S.MAIN, lambda p: p in files)
        commit(S.MAIN, f"agy fix {tag}: call {n}")
    return sh(test_cmd, S.MAIN, 1800)[0] == 0


def integrate(stage):
    start = S.git("rev-parse", "HEAD").stdout.strip()
    for lane in stage["lanes"]:
        br = f"gnhf/p22-nn-{lane['name']}"
        if S.git("merge-base", "--is-ancestor", br, S.INTEG, check=False).returncode == 0:
            continue
        if S.git("merge", "--no-ff", "--no-edit", br, check=False).returncode:
            files = [f for f in S.git("diff", "--name-only", "--diff-filter=U").stdout.split() if f]
            fixed = agy_fix(f"Resolve the git conflict markers (<<<<<<< ======= >>>>>>>) in {files}; "
                            f"keep both branches' content where they do not contradict.",
                            files, f"merge_{lane['name']}", "! git grep -n '^<<<<<<< ' -- " + " ".join(files))
            if not fixed:
                S.git("merge", "--abort", check=False)
                S.log(f"FATAL: cannot merge {br}")
                sys.exit(5)
            S.git("add", *files)
            S.git("commit", "-q", "--no-edit")
        S.log(f"merged {br}")
    tests = "PY -m pytest -q -x " + " ".join(sorted(str(p.relative_to(S.MAIN)) for p in (S.MAIN / "tests").glob("test_nn_*.py")))
    if sh(tests, S.MAIN, 1800)[0]:
        changed = S.git("diff", "--name-only", start, "HEAD").stdout.split()
        agy_fix("The focused tests fail after merging this stage. Fix the code so they pass without "
                "changing any saved result.", [f for f in changed if f.endswith(".py")], f"tests_{stage['id']}", tests)
    for parent, kids in CFG.get("rollup", {}).items():
        if all(S.status(S.MAIN, k).startswith("DONE") for k in kids) and not S.status(S.MAIN, parent).startswith("DONE"):
            set_status(S.MAIN, parent, f"DONE:rolled up from {', '.join(kids)}")
    gate_ok, outs = True, []
    for cmd in stage.get("gate", []):
        rc, out = sh(cmd, S.MAIN, 1800)
        gate_ok = gate_ok and rc == 0
        outs.append(f"{cmd} -> {rc}")
    S.regen_todo_table()
    S.log(f"{stage['id']} gate {'PASS' if gate_ok else 'FAIL'}: {outs}")
    return gate_ok


def smoke():
    """One real agy call in a scratch worktree: proves permissions, sandbox writes and the model."""
    lane = {"name": "agysmoke", "owns": ["tasks/nn/lanes/agysmoke.md"], "tasks": []}
    wt, _ = S.ensure_worktree(lane)
    target = wt / "tasks/nn/lanes/agysmoke.md"
    target.unlink(missing_ok=True)
    rc, out = call_agy(wt, f"Workspace root: {wt}\nYou have NO shell. Read {wt}/docs/nn_v2/PROTOCOL_FREEZE.md and "
                           f"create {target} containing exactly one line: SMOKE <the protocol sha256 it lists>.",
                       MODELS[0], 1, "smoke")
    text = target.read_text() if target.exists() else ""
    ok = "80931bfc05c403804db47f53b02b29989204a6c04720476cb752dd62968b7161" in text
    print(("SMOKE PASS" if ok else "SMOKE FAIL") + f" (agy exit {rc}); file: {text.strip()[:120]!r}")
    target.unlink(missing_ok=True)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-stage")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    S.LOGDIR.mkdir(parents=True, exist_ok=True)
    latest = S.LOGDIR.parent / "latest"
    if latest.is_symlink() or latest.exists():
        latest.unlink()
    latest.symlink_to(S.LOGDIR)
    if S.git("branch", "--show-current").stdout.strip() != S.INTEG:
        sys.exit(f"main checkout must be on {S.INTEG}")
    if args.smoke:
        sys.exit(0 if smoke() else 1)
    commit(S.MAIN, "chore: preserve main-checkout leftovers before agy run")
    started = args.from_stage is None
    for stage in CFG["stages"]:
        started = started or stage["id"] == args.from_stage
        if not started:
            continue
        for rnd in range(1, 4):
            todo = [lane for lane in stage["lanes"] if not all(
                S.status(S.MAIN, t).startswith(("DONE", "NOT_NEEDED")) or
                (S.status(S.MAIN, t).startswith("BLOCKED") and t not in lane.get("critical", []))
                for t in lane["tasks"])]
            if not todo:
                break
            S.log(f"{stage['id']} round {rnd}: {[lane['name'] for lane in todo]} - {stage['goal']}")
            threads = [threading.Thread(target=run_lane, args=(stage, lane)) for lane in todo]
            for t in threads:
                t.start()
                time.sleep(20)
            for t in threads:
                t.join()
            if integrate(stage) or not stage.get("hard"):
                break
        else:
            if stage.get("hard"):
                S.log(f"STOP: {stage['id']} hard gate still failing after 3 rounds. See {S.LOGDIR}.")
                sys.exit(6)
    S.log("agy swarm finished")


if __name__ == "__main__":
    main()
