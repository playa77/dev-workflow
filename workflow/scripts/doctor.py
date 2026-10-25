#!/usr/bin/env python3
"""Check that the installation is complete and internally consistent.

Usage:
    python3 workflow/scripts/doctor.py [--root .] [--quiet]

Exit 0 only when every required file is present, the configuration resolves,
the ledger and changelog validate (in an installed project), and CI is installed.

Two layouts are recognised:
  * an installed project — root AGENTS.md carries only a workflow block and the
    project owns DECISIONS.md and CHANGELOG.md;
  * the kit repository itself — `workflow/state/install.json` records
    `"kit": true`; it ships the installer and the artifact templates instead of
    a ledger and changelog of its own.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

COMMON = [
    "AGENTS.md",
    "workflow/START.md", "workflow/WORKFLOW.md", "workflow/VERIFICATION.md",
    "workflow/STATE.md", "workflow/REVIEW.md", "workflow/MEASUREMENT.md",
    "workflow/config.json", "workflow/VERSION",
]

PROJECT_ONLY = [
    "DECISIONS.md", "CHANGELOG.md", "workflow/CONSTITUTION.md",
]

KIT_ONLY = [
    "workflow/scripts/install.py", "workflow/scripts/risk-scan.py",
    "workflow/scripts/risk-gate.py", "workflow/scripts/run-role.py",
    "workflow/templates/DECISIONS.seed.md", "workflow/templates/CHANGELOG.seed.md",
]

# The CI file must implement the review-aware gate, not merely exist. The
# installer preserves a hand-edited workflow, so this is the only check that
# the preserved file still enforces the policy.
CI_POLICY = [
    ("pull_request_review",
     "no pull_request_review trigger: a strict-mode approval would not re-evaluate the gate"),
    ("risk-gate.py",
     "no risk-gate.py lane: the risk decision is not recorded"),
    ("--publish",
     "risk-gate.py does not publish its verdict as a commit status"),
    ("statuses: write",
     "no `statuses: write` permission: the gate cannot publish its verdict"),
    ("run-role.py test_full",
     "the full-suite lane does not resolve `test_full` from workflow/config.json"),
    ("ref: ${{ github.event.repository.default_branch }}",
     "the risk job does not check out the protected default branch: it would "
     "execute pull request code in the job that publishes the verdict"),
    ("refs/pull/",
     "the risk job does not fetch the pull request head as data"),
    ("persist-credentials: false",
     "the test job leaves checkout credentials in .git/config for pull request code"),
]


def review_mode_notes(root: Path) -> list[str]:
    """Explain the active review policy and what it requires of the operator."""
    try:
        data = json.loads((root / "workflow" / "config.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    mode_value = data.get("mode")
    mode = mode_value if isinstance(mode_value, dict) else {}
    review = str(mode.get("review") or "").strip().lower()
    if review == "advisory":
        return ["review mode: advisory (solo default) — risk findings are reported; "
                "the owner accepts them by merging the pull request"]
    if review == "risk-triggered":
        return ["review mode: risk-triggered (opt-in) — material risk findings require "
                "an independent approval on the exact head commit; a second GitHub "
                "identity is needed"]
    if review == "human":
        return ["review mode: human (opt-in) — every pull request requires an "
                "independent approval on the exact head commit; a second GitHub "
                "identity is needed"]
    return []


def workflow_level_status_write(text: str) -> bool:
    """True when `statuses: write` is granted workflow-wide instead of per job."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("permissions:"):
            continue
        inline = line.split(":", 1)[1].strip()
        if inline in {"statuses: write", "write-all"}:
            return True
        for following in lines[index + 1:]:
            stripped = following.strip()
            if stripped and not following[:1].isspace():
                break
            if stripped in {"statuses: write", "write-all"}:
                return True
    return False


def ci_policy_problems(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path.name}: {exc}"]
    problems = [f"{path.name}: {message}" for token, message in CI_POLICY if token not in text]
    if workflow_level_status_write(text):
        problems.append(f"{path.name}: `statuses: write` is granted to every job; "
                        "only the trusted risk job may publish a status")
    return problems


def is_kit(root: Path) -> bool:
    state = root / "workflow" / "state" / "install.json"
    if state.exists():
        try:
            return json.loads(state.read_text(encoding="utf-8")).get("kit") is True
        except json.JSONDecodeError:
            return False
    return False


def run(script: Path, cwd: Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(script), *args],
                          cwd=cwd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    problems: list[str] = []
    notes: list[str] = []
    kit = is_kit(root)

    required = COMMON + (KIT_ONLY if kit else PROJECT_ONLY)
    for rel in required:
        if not (root / rel).exists():
            hint = " (run install.py --upgrade)" if rel == "workflow/CONSTITUTION.md" else ""
            problems.append(f"missing {rel}{hint}")

    agents = root / "AGENTS.md"
    if agents.exists() and "workflow/START.md" not in agents.read_text(encoding="utf-8"):
        problems.append("AGENTS.md does not point at workflow/START.md")

    scripts = root / "workflow" / "scripts"
    checks = ["check-config.py"]
    if not kit:
        checks += ["check-ledger.py", "check-changelog.py"]
    for name in checks:
        script = scripts / name
        if not script.exists():
            problems.append(f"missing workflow/scripts/{name}")
            continue
        code, out = run(script, root)
        if code != 0:
            problems.append(out.replace("\n", "; "))

    ci = root / ".github" / "workflows"
    ci_files = [p for p in (ci / "wp.yml", ci / "wp-workflow.yml") if p.exists()]
    if not ci_files:
        problems.append("no CI workflow installed (.github/workflows/wp.yml)")
    if len(ci_files) > 1:
        problems.append("both wp.yml and wp-workflow.yml exist: two workflows would "
                        "race to publish the risk-gate status; remove one")
    for path in ci_files:
        problems.extend(ci_policy_problems(path))

    baseline = root / "workflow" / "state" / "test-baseline.json"
    if not baseline.exists():
        notes.append("no test baseline (fine before the repository has tests)")

    if kit:
        notes.append("kit repository: DECISIONS.md and CHANGELOG.md are created "
                     "in projects at install, not tracked here")

    notes.extend(review_mode_notes(root))

    state = root / "workflow" / "state" / "install.json"
    if state.exists():
        try:
            installed = json.loads(state.read_text(encoding="utf-8")).get("version")
            current = (root / "workflow" / "VERSION").read_text(encoding="utf-8").strip()
            if installed != current:
                notes.append(f"install recorded {installed}, files are {current}; run install.py --upgrade")
        except (json.JSONDecodeError, OSError):
            pass

    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1
    print("doctor: ok — installation complete and consistent")
    for n in notes:
        print(f"note: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
