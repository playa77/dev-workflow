#!/usr/bin/env python3
"""Check that the installation is complete and internally consistent.

Usage:
    python3 workflow/scripts/doctor.py [--root .] [--quiet]

Exit 0 only when every required file is present, the configuration resolves,
the ledger and changelog validate, and CI is installed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REQUIRED = [
    "AGENTS.md", "DECISIONS.md", "CHANGELOG.md",
    "workflow/START.md", "workflow/WORKFLOW.md", "workflow/VERIFICATION.md",
    "workflow/STATE.md", "workflow/REVIEW.md", "workflow/MEASUREMENT.md",
    "workflow/config.json", "workflow/VERSION",
]


def run(script: Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(script), *args],
                          capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    problems: list[str] = []
    notes: list[str] = []

    for rel in REQUIRED:
        if not (root / rel).exists():
            problems.append(f"missing {rel}")

    agents = root / "AGENTS.md"
    if agents.exists() and "workflow/START.md" not in agents.read_text(encoding="utf-8"):
        problems.append("AGENTS.md does not point at workflow/START.md")

    scripts = root / "workflow" / "scripts"
    for name in ("check-config.py", "check-ledger.py", "check-changelog.py"):
        script = scripts / name
        if not script.exists():
            problems.append(f"missing workflow/scripts/{name}")
            continue
        code, out = run(script)
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
