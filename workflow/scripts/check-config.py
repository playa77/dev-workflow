#!/usr/bin/env python3
"""Validate workflow/config.json and resolve every command role.

Usage:
    python3 workflow/scripts/check-config.py [--verify-commands]

Exit 0 when every required role is present and, with --verify-commands, the
first token of each command resolves.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROLES = ["test_affected", "test_full", "test_smoke", "lint", "build",
         "integrity", "callers", "stats"]
MODES = {
    "merge": {"auto", "human"},
    # advisory is the solo default; the other two are explicit opt-ins that
    # require an independent approval of the exact head commit.
    "review": {"advisory", "risk-triggered", "human"},
}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", default="workflow/config.json")
    ap.add_argument("--verify-commands", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        print(f"FAIL: {path} not found")
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL: {path}: {exc}")
        return 2

    problems: list[str] = []
    notes: list[str] = []
    commands = data.get("commands")
    if not isinstance(commands, dict):
        problems.append("commands must be an object")
        commands = {}
    for role in ROLES:
        value = commands.get(role)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"command role '{role}' is unset")
            continue
        if args.verify_commands:
            first = value.split()[0]
            if "/" in first or first.startswith("."):
                if not Path(first).exists():
                    problems.append(f"'{role}': {first} does not exist")
            elif shutil.which(first) is None:
                problems.append(f"'{role}': '{first}' not on PATH")

    mode = data.get("mode", {})
    review_mode = None
    merge_mode = None
    if not isinstance(mode, dict):
        problems.append("mode must be an object")
        mode = {}
    else:
        for key, allowed in MODES.items():
            if mode.get(key) not in allowed:
                problems.append(f"mode.{key} must be one of {sorted(allowed)}")
        review_mode = mode.get("review")
        merge_mode = mode.get("merge")
    if merge_mode == "auto":
        notes.append("mode.merge=auto is opt-in: the executing agent may merge once every "
                     "required check and the risk-gate status are green")
    if review_mode == "advisory":
        notes.append("mode.review=advisory is the solo default: risk findings are reported "
                     "and never fail a required check; the owner accepts them by merging")
    elif review_mode in {"risk-triggered", "human"}:
        notes.append(f"mode.review={review_mode} is opt-in: an independent approval of the "
                     "exact head commit is required, so a second GitHub identity is needed")

    triggers = data.get("risk_triggers")
    if triggers is not None and not (
        isinstance(triggers, dict) and all(isinstance(v, list) for v in triggers.values())
    ):
        problems.append("risk_triggers must be an object of lists")

    review = data.get("review")
    approvers: list[str] = []
    if review is not None:
        if not isinstance(review, dict):
            problems.append("review must be an object")
        else:
            approvers = review.get("approvers") or []
            if approvers is not None and not (
                isinstance(approvers, list)
                and all(isinstance(a, str) and a.strip() for a in approvers)
            ):
                problems.append("review.approvers must be a list of logins")
                approvers = []
            context = review.get("status_context")
            if context is not None and not (isinstance(context, str) and context.strip()):
                problems.append("review.status_context must be a non-empty string")

    if review_mode == "advisory" and approvers:
        notes.append("review.approvers is unused in advisory mode; it applies only to "
                     "risk-triggered and human review")
    if review_mode in {"risk-triggered", "human"} and not approvers:
        notes.append("review.approvers is empty: approvals fall back to collaborators with "
                     "write permission; name the independent reviewers to pin them")

    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1
    print("config: ok — roles resolved")
    for note in notes:
        print(f"note: {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
