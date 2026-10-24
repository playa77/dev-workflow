#!/usr/bin/env python3
"""Validate a work-package brief.

Usage:
    python3 workflow/scripts/check-wp.py docs/wp/WP-001.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FIELDS = ["Type", "Depends on", "Branch", "Base", "Spec refs", "Review cost",
          "User-visible effect", "Decisions expected", "Status"]
TYPES = {"deterministic", "exploratory", "architectural", "spike"}
REVIEW = {"one pass", "spans sessions"}
DEC_RE = re.compile(r"^D-\d{3,}$")


def table_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*$", line)
        if m:
            fields[m.group(1).strip().lower()] = m.group(2).strip().strip("`")
    return fields


def section(text: str, n: int) -> str:
    m = re.search(rf"^##\s*{n}\.\s.*?$(.*?)(?=^##\s*\d+\.|\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def check(text: str, path: Path) -> list[str]:
    problems: list[str] = []
    fields = table_fields(text)
    for name in FIELDS:
        if name.lower() not in fields or not fields[name.lower()]:
            problems.append(f"missing field: {name}")
    typ = fields.get("type", "")
    if typ and typ not in TYPES:
        problems.append(f"Type must be one of {sorted(TYPES)}")
    review = fields.get("review cost", "")
    if review and review not in REVIEW:
        problems.append("Review cost must be 'one pass' or 'spans sessions'")
    status = fields.get("status", "")
    if status and status not in {"proposed", "approved", "claimed", "in-progress",
                                 "verified", "delivered", "merged", "blocked"}:
        problems.append(f"invalid Status: {status}")
    uv = fields.get("user-visible effect", "")
    if uv and uv.lower() not in {"none"} and len(uv) < 8:
        problems.append("User-visible effect must be a sentence or 'none'")
    dec = fields.get("decisions expected", "")
    if dec and dec.lower() != "none":
        for d in [x.strip().strip("`") for x in dec.split(",") if x.strip()]:
            if not DEC_RE.match(d):
                problems.append(f"Decisions expected: invalid id {d}")

    for n in range(1, 11):
        if not section(text, n):
            problems.append(f"missing section {n}")

    crit = section(text, 6)
    crits = [line for line in crit.splitlines() if re.match(r"^\d+\.\s+\S", line)]
    if not 3 <= len(crits) <= 8:
        problems.append(f"acceptance criteria must number 3–8, found {len(crits)}")

    ver = section(text, 7)
    rows = [line for line in ver.splitlines()
            if line.startswith("|") and not re.match(r"^\|[\s:|-]+\|$", line)]
    if len(rows) < 2:
        problems.append("verification needs at least one command row")

    if "TBD" in text or "TODO" in text:
        problems.append("contains TBD/TODO")
    return problems


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("brief", nargs="?", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    paths = [Path(args.brief)] if args.brief else sorted(Path("docs/wp").glob("WP-*.md"))
    paths = [p for p in paths if p.name != "WP.md"]
    if not paths:
        print("FAIL: no briefs found")
        return 2
    failed = False
    for path in paths:
        if not path.exists():
            print(f"FAIL: {path} not found")
            failed = True
            continue
        problems = check(path.read_text(encoding="utf-8"), path)
        if problems:
            failed = True
            for p in problems:
                print(f"FAIL: {path}: {p}")
    if not failed:
        print(f"wp: ok — {len(paths)} brief(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
