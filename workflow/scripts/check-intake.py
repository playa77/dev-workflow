#!/usr/bin/env python3
"""Validate workflow/state/intake.json — the interview exit condition.

Usage:
    python3 workflow/scripts/check-intake.py [--path workflow/state/intake.json]
                                             [--digest docs/process/DIGEST.md]

Exit 0 only when every topic is closed and `open` is 0.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TOPICS = [
    "purpose", "users", "scope", "data", "integrations", "security",
    "infrastructure", "performance", "budget", "technology", "operations", "non_goals",
]
STATUSES = {"answered", "answered_by_repo", "defaulted", "deferred", "open"}
BLAST = {"local", "architectural"}
WP_RE = re.compile(r"^WP-\d{3,}$")
MAX_QUESTIONS = 12


def check(data: dict, root: Path) -> list[str]:
    problems: list[str] = []
    topics = data.get("topics")
    if not isinstance(topics, dict):
        return ["topics must be an object"]

    missing = [t for t in TOPICS if t not in topics]
    extra = [t for t in topics if t not in TOPICS]
    if missing:
        problems.append(f"missing topics: {', '.join(missing)}")
    if extra:
        problems.append(f"unknown topics: {', '.join(extra)}")

    open_count = 0
    for name in TOPICS:
        t = topics.get(name)
        if not isinstance(t, dict):
            problems.append(f"{name}: missing entry")
            continue
        status = t.get("status")
        if status not in STATUSES:
            problems.append(f"{name}: invalid status {status!r}")
            continue
        if status == "open":
            open_count += 1
        elif status == "answered":
            if not str(t.get("answer", "")).strip():
                problems.append(f"{name}: answered without an answer")
        elif status == "answered_by_repo":
            ev = str(t.get("evidence", "")).strip()
            if not ev:
                problems.append(f"{name}: answered_by_repo without evidence")
            else:
                path = ev.rsplit(":", 1)[0] if re.search(r":\d+$", ev) else ev
                if not (root / path).exists():
                    problems.append(f"{name}: evidence path not found: {path}")
        else:
            if not str(t.get("default", "")).strip():
                problems.append(f"{name}: {status} without a default")
            if t.get("blast_radius") not in BLAST:
                problems.append(f"{name}: {status} needs blast_radius local|architectural")
            if not str(t.get("revisit_if", "")).strip():
                problems.append(f"{name}: {status} without revisit_if")
            if status == "deferred" and not WP_RE.match(str(t.get("resolved_by", ""))):
                problems.append(f"{name}: deferred needs resolved_by WP-nnn")

    declared = data.get("open")
    if declared != open_count:
        problems.append(f"open is {declared}, computed {open_count}")
    if open_count:
        problems.append(f"{open_count} topic(s) still open")

    asked = data.get("questions_asked", 0)
    if not isinstance(asked, int) or asked < 0:
        problems.append("questions_asked must be a non-negative integer")
    elif asked > MAX_QUESTIONS:
        problems.append(f"questions_asked {asked} exceeds the budget of {MAX_QUESTIONS}")
    return problems


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", default="workflow/state/intake.json")
    ap.add_argument("--digest", default="docs/process/DIGEST.md")
    ap.add_argument("--root", default=".")
    ap.add_argument("--quiet", action="store_true")
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

    problems = check(data, Path(args.root))
    digest = Path(args.digest)
    if digest.exists():
        text = digest.read_text(encoding="utf-8").lower()
        for needle in ("constraint ledger", "non-goals", "approve"):
            if needle not in text:
                problems.append(f"digest missing section: {needle}")
    elif data.get("open") == 0:
        problems.append(f"digest not found at {digest}")

    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1
    print(f"intake: ok — {len(TOPICS)} topics closed, {data.get('questions_asked', 0)} questions asked")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
