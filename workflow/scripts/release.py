#!/usr/bin/env python3
"""Cut a release: propose a version, move Unreleased, update VERSION, check.

Usage:
    python3 workflow/scripts/release.py [--version 2.0.0] [--date YYYY-MM-DD] [--tag] [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

HEAD_RE = re.compile(r"^## \[([^\]]+)\](?:\s*-\s*(\d{4}-\d{2}-\d{2}))?\s*$")


def git(*args: str) -> str:
    p = subprocess.run(["git", *args], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else ""


def propose_bump() -> str:
    last = git("describe", "--tags", "--abbrev=0")
    rng = f"{last}..HEAD" if last else "HEAD"
    subjects = git("log", rng, "--format=%s").splitlines()
    if any("!:" in s or "BREAKING CHANGE" in s for s in subjects):
        return "major"
    if any(s.startswith("feat") for s in subjects):
        return "minor"
    return "patch"


def next_version(current: str, bump: str) -> str:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", current)
    major, minor, patch = (int(x) for x in m.groups()) if m else (0, 0, 0)
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--changelog", default="CHANGELOG.md")
    ap.add_argument("--version-file", default="workflow/VERSION")
    ap.add_argument("--version", default=None)
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--tag", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    changelog = Path(args.changelog)
    version_file = Path(args.version_file)
    if not changelog.exists():
        print(f"error: {changelog} not found")
        return 2

    text = changelog.read_text(encoding="utf-8")
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == "## [Unreleased]")
    except StopIteration:
        print("error: no '## [Unreleased]' heading")
        return 2
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if HEAD_RE.match(lines[i]):
            end = i
            break
    block = [l for l in lines[start + 1:end] if l.strip()]
    if not block:
        print("error: Unreleased has no entries")
        return 2

    current = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else "0.0.0"
    version = args.version or next_version(current, propose_bump())
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        print(f"error: version '{version}' is not semver")
        return 2

    new_block = ["## [Unreleased]", "", f"## [{version}] - {args.date}", ""] + block
    new_text = "\n".join(lines[:start] + new_block + lines[end:]) + "\n"

    if args.dry_run:
        print(f"would release {version} on {args.date} ({len(block)} lines)")
        return 0

    changelog.write_text(new_text, encoding="utf-8")
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(version + "\n", encoding="utf-8")

    script_dir = Path(__file__).resolve().parent
    for name in ("check-ledger.py", "check-changelog.py"):
        proc = subprocess.run([sys.executable, str(script_dir / name)])
        if proc.returncode != 0:
            return proc.returncode

    if args.tag:
        proc = subprocess.run(["git", "tag", "-a", f"v{version}", "-m", f"v{version}"])
        if proc.returncode != 0:
            return proc.returncode
        print(f"tagged v{version}")
    print(f"released {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
