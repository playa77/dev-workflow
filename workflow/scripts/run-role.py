#!/usr/bin/env python3
"""Resolve and run a command role from workflow/config.json.

Usage:
    python3 workflow/scripts/run-role.py <role> [--config PATH] [--print]

Exit codes:
    0  the command ran and succeeded
    1  the role is missing or empty, or the command failed
    2  the configuration could not be read

The CI template calls this instead of embedding a command, so correcting
`workflow/config.json` takes effect on the next run without regenerating CI.
An unset role fails; it never falls through to a no-op.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ZERO_TESTS_RE = re.compile(r"\bNO TESTS RAN\b|\bRan 0 tests\b", re.I)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("role")
    ap.add_argument("--config", default="workflow/config.json")
    ap.add_argument("--print", action="store_true", dest="print_only")
    args = ap.parse_args(argv)

    path = Path(args.config)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"run-role: {path} not found", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"run-role: {path} is not valid JSON: {exc}", file=sys.stderr)
        return 2

    commands = data.get("commands")
    command = commands.get(args.role) if isinstance(commands, dict) else None
    if not isinstance(command, str) or not command.strip():
        print(f"run-role: no command configured for role '{args.role}' in {path}; "
              "set it and re-run doctor.py", file=sys.stderr)
        return 1

    if args.print_only:
        print(command)
        return 0

    print(f"run-role: {args.role}: {command}", file=sys.stderr)
    proc = subprocess.run(command, shell=True, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        return proc.returncode
    if args.role == "test_full" and ZERO_TESTS_RE.search(proc.stdout + proc.stderr):
        # unittest exits 0 when it collects nothing; that is a passing lane
        # that proves nothing, which the method refuses.
        print(f"run-role: test_full ran zero tests", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
