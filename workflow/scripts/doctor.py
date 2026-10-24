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
    "workflow/templates/DECISIONS.seed.md", "workflow/templates/CHANGELOG.seed.md",
]


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

    config = root / "workflow" / "config.json"
    if config.exists():
        try:
            data = json.loads(config.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"config.json: {exc}")
            data = {}
        empty = [k for k, v in (data.get("commands") or {}).items() if not str(v).strip()]
        if empty:
            notes.append(f"unresolved command roles: {', '.join(empty)}")

    ci = root / ".github" / "workflows"
    if not any((ci / n).exists() for n in ("wp.yml", "wp-workflow.yml")):
        problems.append("no CI workflow installed (.github/workflows/wp.yml)")

    baseline = root / "workflow" / "state" / "test-baseline.json"
    if not baseline.exists():
        notes.append("no test baseline (fine before the repository has tests)")

    if kit:
        notes.append("kit repository: DECISIONS.md and CHANGELOG.md are created "
                     "in projects at install, not tracked here")

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
