#!/usr/bin/env python3
"""Plan guard for the synthetic-only implementation sequence.

Standard library only. This script must stay importable without NumPy, pandas,
scikit-learn, PyTorch, or anndata so that plan compliance can be checked in a
bare interpreter.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "plan" / "implementation_plan.json"
STATE_PATH = REPO_ROOT / "plan" / "state.json"
APPROVALS_PATH = REPO_ROOT / "plan" / "approvals.json"

PHASES = ("worktree", "staged", "committed")
SCANNED_SUFFIXES = (".py", ".ipynb")
DATA_DIR_ALLOWED = ("data/README.md",)
AGENT_TRAILER_PATTERN = re.compile(
    r"(?im)^\s*(co-authored-by|generated-by|assisted-by|signed-off-by-agent)\s*:",
)
AGENT_MENTION_PATTERN = re.compile(
    r"(?i)\b(cursor|claude|chatgpt|openai|copilot|codex|gemini)\b",
)


@dataclass
class Report:
    """Accumulated guard findings."""

    passed: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def ok(self, message: str) -> None:
        self.passed.append(message)

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def extend_failures(self, messages: list[str], ok_message: str) -> None:
        if messages:
            self.failures.extend(messages)
        else:
            self.passed.append(ok_message)

    @property
    def exit_code(self) -> int:
        return 1 if self.failures else 0


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def step_ids(plan: dict) -> list[str]:
    return [step["id"] for step in plan["steps"]]


def find_step(plan: dict, step_id: str) -> dict:
    for step in plan["steps"]:
        if step["id"] == step_id:
            return step
    raise KeyError(f"unknown step {step_id}")


def check_branch(actual: str, expected: str) -> list[str]:
    if actual != expected:
        return [f"branch is {actual!r}, plan requires {expected!r}"]
    return []


def check_step_order(plan: dict, state: dict, step_id: str, phase: str) -> list[str]:
    ids = step_ids(plan)
    if step_id not in ids:
        return [f"step {step_id} is not in the plan"]
    problems: list[str] = []
    states = state.get("steps", {})
    for earlier in ids[: ids.index(step_id)]:
        status = states.get(earlier, {}).get("status")
        if status != "complete":
            problems.append(f"step {earlier} is {status!r}; steps cannot be skipped")
    current = states.get(step_id, {}).get("status")
    if phase == "worktree":
        if current not in ("pending", "in_progress"):
            problems.append(f"step {step_id} is {current!r}; expected pending or in_progress")
    elif current != "complete":
        problems.append(f"step {step_id} is {current!r}; mark it complete before {phase} check")
    return problems


def check_paths(changed: list[str], allowed: list[str]) -> list[str]:
    allowed_set = set(allowed)
    return [
        f"path not allowlisted for this step: {path}" for path in changed if path not in allowed_set
    ]


def check_real_data_paths(changed: list[str], patterns: list[str]) -> list[str]:
    problems: list[str] = []
    for path in changed:
        if any(fnmatch.fnmatch(path, pattern) for pattern in patterns):
            problems.append(f"real-data-shaped file must not be tracked: {path}")
        if path.startswith("data/") and path not in DATA_DIR_ALLOWED:
            problems.append(f"dataset directory must stay untracked: {path}")
    return problems


def check_network_calls(sources: dict[str, str], patterns: list[str]) -> list[str]:
    problems = []
    for path, text in sorted(sources.items()):
        for pattern in patterns:
            if pattern in text:
                problems.append(f"network or remote-data call {pattern!r} found in {path}")
    return problems


def check_condition_terms(sources: dict[str, str], terms: list[str]) -> list[str]:
    problems = []
    for path, text in sorted(sources.items()):
        lowered = text.lower()
        for term in terms:
            if re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", lowered):
                problems.append(
                    f"condition-specific term {term!r} found in {path} while approval is blocked"
                )
    return problems


def check_data_mode(documents: dict[str, dict], allowed_modes: list[str]) -> list[str]:
    problems = []
    for path, document in sorted(documents.items()):
        mode = document.get("data_mode")
        if mode is not None and mode not in allowed_modes:
            problems.append(f"{path} declares data_mode {mode!r}; allowed: {allowed_modes}")
    return problems


def check_agent_trailers(message: str) -> list[str]:
    problems = []
    if AGENT_TRAILER_PATTERN.search(message):
        problems.append("commit message contains a disallowed agent trailer")
    if AGENT_MENTION_PATTERN.search(message):
        problems.append("commit message names an agent or model")
    return problems


def check_recorded_commits(state: dict, is_ancestor) -> list[str]:
    """Every commit hash recorded in plan/state.json must exist in current history.

    Hashes are back-filled one step later so that the working tree stays clean at
    commit time.
    """
    problems = []
    for step_id, record in sorted(state.get("steps", {}).items()):
        commit = record.get("commit")
        if not commit:
            continue
        if not is_ancestor(commit):
            problems.append(
                f"plan/state.json records commit {commit!r} for {step_id}, "
                "which is not an ancestor of HEAD"
            )
    return problems


def check_commit_subject(actual: str, expected: str) -> list[str]:
    if actual != expected:
        return [f"commit subject {actual!r} does not match plan subject {expected!r}"]
    return []


def git(*args: str, repo: Path = REPO_ROOT) -> str:
    """Run git and return stdout with trailing newlines removed.

    Leading whitespace is preserved because porcelain status codes are
    column-positional.
    """
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.rstrip("\n")


def git_succeeds(*args: str, repo: Path = REPO_ROOT) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def parse_status_paths(porcelain: str) -> list[str]:
    paths: list[str] = []
    for line in porcelain.splitlines():
        if not line.strip():
            continue
        entry = line[3:]
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        paths.append(entry.strip().strip('"'))
    return sorted(set(paths))


def changed_paths(phase: str, repo: Path = REPO_ROOT) -> list[str]:
    if phase == "worktree":
        return parse_status_paths(git("status", "--porcelain=v1", "-uall", repo=repo))
    if phase == "staged":
        output = git("diff", "--cached", "--name-only", repo=repo)
        return sorted({line.strip() for line in output.splitlines() if line.strip()})
    output = git("show", "--name-only", "--pretty=format:", "HEAD", repo=repo)
    return sorted({line.strip() for line in output.splitlines() if line.strip()})


def read_sources(paths: list[str], phase: str, repo: Path = REPO_ROOT) -> dict[str, str]:
    sources: dict[str, str] = {}
    for path in paths:
        if not path.endswith(SCANNED_SUFFIXES):
            continue
        if phase == "committed":
            try:
                sources[path] = git("show", f"HEAD:{path}", repo=repo)
            except subprocess.CalledProcessError:
                continue
            continue
        candidate = repo / path
        if candidate.is_file():
            sources[path] = candidate.read_text(encoding="utf-8", errors="replace")
    return sources


def read_json_documents(paths: list[str], repo: Path = REPO_ROOT) -> dict[str, dict]:
    documents: dict[str, dict] = {}
    for path in paths:
        if not path.endswith(".json"):
            continue
        candidate = repo / path
        if not candidate.is_file():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            documents[path] = payload
    return documents


def run_status(repo: Path = REPO_ROOT) -> int:
    plan = load_json(repo / "plan" / "implementation_plan.json")
    state = load_json(repo / "plan" / "state.json")
    approvals = load_json(repo / "plan" / "approvals.json")
    states = state.get("steps", {})
    complete = [sid for sid in step_ids(plan) if states.get(sid, {}).get("status") == "complete"]
    print(f"plan version: {plan['plan_version']}")
    print(f"branch: {state.get('branch')}")
    print(f"base commit: {state.get('base_commit')}")
    print(f"data mode: {state.get('data_mode')}")
    print(f"approval: {approvals.get('approval_state')} (approver: {approvals.get('approver')})")
    print(f"complete steps: {len(complete)}/{len(step_ids(plan))}")
    print(f"next action: {state.get('next_action')}")
    print("")
    print(f"{'step':<5} {'status':<12} {'gate':<13} commit    subject")
    for step in plan["steps"]:
        record = states.get(step["id"], {})
        commit = (record.get("commit") or "-")[:8]
        gate = record.get("notebook_gate") or "-"
        status = record.get("status", "unknown")
        print(f"{step['id']:<5} {status:<12} {gate:<13} {commit:<9} {step['subject']}")
    return 0


def run_check(step_id: str, phase: str, repo: Path = REPO_ROOT) -> int:
    plan = load_json(repo / "plan" / "implementation_plan.json")
    state = load_json(repo / "plan" / "state.json")
    approvals = load_json(repo / "plan" / "approvals.json")
    step = find_step(plan, step_id)
    report = Report()

    branch = git("branch", "--show-current", repo=repo).strip()
    report.extend_failures(check_branch(branch, plan["branch"]), f"branch {branch} matches plan")
    report.extend_failures(
        check_step_order(plan, state, step_id, phase), f"step order valid for {step_id} ({phase})"
    )

    paths = changed_paths(phase, repo=repo)
    report.extend_failures(
        check_paths(paths, step["allowed_paths"]), f"{len(paths)} changed path(s) allowlisted"
    )
    report.extend_failures(
        check_real_data_paths(paths, approvals["real_data_path_patterns"]),
        "no real-data files introduced",
    )

    sources = read_sources(paths, phase, repo=repo)
    report.extend_failures(
        check_network_calls(sources, approvals["network_call_patterns"]),
        f"no network calls in {len(sources)} scanned file(s)",
    )
    if approvals.get("approval_state") != "approved":
        report.extend_failures(
            check_condition_terms(sources, approvals["condition_terms"]),
            "no condition-specific execution while approval is blocked",
        )
    report.extend_failures(
        check_data_mode(read_json_documents(paths, repo=repo), approvals["allowed_data_modes"]),
        "declared data modes allowed",
    )

    if phase == "committed":
        message = git("log", "-1", "--format=%B", repo=repo)
        subject = message.splitlines()[0].strip() if message.strip() else ""
        report.extend_failures(
            check_commit_subject(subject, step["subject"]), "commit subject matches plan"
        )
        report.extend_failures(check_agent_trailers(message), "commit message has no agent trailer")
        dirty = parse_status_paths(git("status", "--porcelain=v1", "-uall", repo=repo))
        report.extend_failures(
            [f"working tree not clean after commit: {path}" for path in dirty],
            "working tree clean",
        )
        report.extend_failures(
            check_recorded_commits(
                state,
                lambda commit: git_succeeds(
                    "merge-base", "--is-ancestor", commit, "HEAD", repo=repo
                ),
            ),
            "recorded commit hashes are in current history",
        )

    for message in report.passed:
        print(f"ok: {message}")
    for message in report.failures:
        print(f"FAIL: {message}")
    verdict = "FAIL" if report.failures else "PASS"
    print(f"{verdict}: plan guard {step_id} {phase}")
    return report.exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan compliance guard")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="print plan status table")
    check = subparsers.add_parser("check", help="check one step in one phase")
    check.add_argument("--step", required=True)
    check.add_argument("--phase", required=True, choices=PHASES)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "status":
        return run_status()
    return run_check(args.step, args.phase)


if __name__ == "__main__":
    sys.exit(main())
