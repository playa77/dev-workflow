#!/usr/bin/env python3
"""Validate CHANGELOG.md and its correlation with DECISIONS.md.

Usage:
    python3 workflow/scripts/check-changelog.py [--quiet]
    python3 workflow/scripts/check-changelog.py --ledger DECISIONS.md --version-file workflow/VERSION

Checks structure (Keep a Changelog), citation resolution, version agreement and
WP coverage. It does not judge whether an entry is meaningful.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

HEAD_RE = re.compile(r"^## \[([^\]]+)\](?:\s*-\s*(\d{4}-\d{2}-\d{2}))?\s*$")
CATEGORY_RE = re.compile(r"^### (Added|Changed|Deprecated|Removed|Fixed|Security)\s*$")
ENTRY_RE = re.compile(r"^- (.+)$")
CITE_RE = re.compile(r"\((D-\d{3,}),\s*(WP-\d{3,})\)\s*$")
HASH_RE = re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{7,40}\b")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
MILESTONE_RE = re.compile(r"^M\d+$")

LEDGER_ENTRY_RE = re.compile(r"^### (D-\d{3,})\s+—\s+.+$")
LEDGER_STATUS_RE = re.compile(r"^- \*\*Status:\*\*\s*(.+?)\s*$")


@dataclass
class Section:
    name: str
    date: str | None
    line: int
    categories: dict[str, list[tuple[str, int]]] = field(default_factory=dict)
    invalid: list[tuple[str, int]] = field(default_factory=list)


def parse(text: str) -> list[Section]:
    sections: list[Section] = []
    current: Section | None = None
    category: str | None = None
    for lineno, line in enumerate(text.splitlines(), start=1):
        hm = HEAD_RE.match(line)
        if hm:
            current = Section(name=hm.group(1), date=hm.group(2), line=lineno)
            sections.append(current)
            category = None
            continue
        if current is None:
            continue
        cm = CATEGORY_RE.match(line)
        if cm:
            category = cm.group(1)
            current.categories.setdefault(category, [])
            continue
        if line.startswith("### "):
            current.invalid.append((line.strip(), lineno))
            category = None
            continue
        em = ENTRY_RE.match(line)
        if em and category is not None:
            current.categories[category].append((em.group(1), lineno))
    return sections


def ledger_statuses(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    statuses: dict[str, str] = {}
    current: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = LEDGER_ENTRY_RE.match(line)
        if m:
            current = m.group(1)
            statuses[current] = ""
            continue
        if current is None:
            continue
        sm = LEDGER_STATUS_RE.match(line)
        if sm:
            statuses[current] = sm.group(1)
    return statuses


def check(text: str, sections: list[Section], ledger: dict[str, str] | None,
          version_file: Path, wp_dir: Path) -> list[str]:
    problems: list[str] = []
    if not sections:
        return ["no '## [version]' headings found"]
    if sections[0].name != "Unreleased":
        problems.append("first heading must be '## [Unreleased]'")
    if sections[0].date is not None:
        problems.append("Unreleased must not carry a date")

    wps_cited: set[str] = set()
    dated: list[tuple[str, date]] = []
    for sec in sections:
        if sec.name == "Unreleased":
            limit_adopted = True
        else:
            limit_adopted = False
            if not sec.date:
                problems.append(f"[{sec.name}]: version heading needs an ISO date")
            else:
                try:
                    dated.append((sec.name, date.fromisoformat(sec.date)))
                except ValueError:
                    problems.append(f"[{sec.name}]: date is not ISO")
            if not (SEMVER_RE.match(sec.name) or MILESTONE_RE.match(sec.name)):
                problems.append(f"[{sec.name}]: not a semver or milestone heading (M1, M2, ...)")
        for title, lineno in sec.invalid:
            problems.append(f"[{sec.name}] line {lineno}: invalid heading {title!r}")
        for cat, entries in sec.categories.items():
            if cat not in ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"):
                problems.append(f"[{sec.name}] {cat}: invalid category")
            for body, lineno in entries:
                if HASH_RE.search(body):
                    problems.append(f"line {lineno}: commit-hash-shaped token in entry")
                m = CITE_RE.search(body)
                if not m:
                    problems.append(f"line {lineno}: entry must end with (D-nnn, WP-nnn)")
                    continue
                did, wp = m.group(1), m.group(2)
                wps_cited.add(wp)
                if ledger is None:
                    problems.append(f"line {lineno}: ledger not found, cannot resolve {did}")
                    continue
                if did not in ledger:
                    problems.append(f"line {lineno}: {did} does not exist in the ledger")
                elif limit_adopted and ledger[did] != "adopted":
                    problems.append(
                        f"line {lineno}: {did} is '{ledger[did]}', not adopted; cite the live decision"
                    )

    dates = [d for _, d in dated]
    if dates != sorted(dates, reverse=True):
        problems.append("version headings must be reverse chronological")

    if version_file.exists() and dated:
        want = version_file.read_text(encoding="utf-8").strip()
        newest = dated[0][0]
        if want and want != newest:
            problems.append(f"VERSION says {want}, newest changelog heading is {newest}")

    if wp_dir.exists() and ledger is not None:
        for path in sorted(wp_dir.glob("*.state.json")):
            try:
                state = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                problems.append(f"{path.name}: invalid JSON")
                continue
            if state.get("status") in ("delivered", "merged") and state.get("user_visible"):
                wp = state.get("wp")
                if wp and wp not in wps_cited:
                    problems.append(f"{wp}: user_visible is true but no changelog line cites it")
    return problems


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", default="CHANGELOG.md")
    ap.add_argument("--ledger", default="DECISIONS.md")
    ap.add_argument("--version-file", default="workflow/VERSION")
    ap.add_argument("--wp-dir", default="docs/wp")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        print(f"FAIL: {path} not found")
        return 2
    text = path.read_text(encoding="utf-8")
    sections = parse(text)
    ledger = ledger_statuses(Path(args.ledger))
    problems = check(text, sections, ledger, Path(args.version_file), Path(args.wp_dir))

    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1
    entries = sum(len(v) for s in sections for v in s.categories.values())
    print(f"changelog: ok — {len(sections)} sections, {entries} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
