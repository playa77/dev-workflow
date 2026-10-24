#!/usr/bin/env python3
"""Validate DECISIONS.md and keep its generated index current.

Usage:
    python3 workflow/scripts/check-ledger.py [--check | --write] [--quiet]
    python3 workflow/scripts/check-ledger.py --path DECISIONS.md --changelog CHANGELOG.md

Checks structure and cross-consistency only. It does not diff entry bodies:
corrections are allowed, and review of the git diff is the human/verifier job.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

INDEX_BEGIN = "<!-- index:begin -->"
INDEX_END = "<!-- index:end -->"

ENTRY_RE = re.compile(r"^### (D-(\d{3,}))\s+—\s+(.+?)\s*$")
FIELD_RE = re.compile(
    r"^- \*\*(Date|Status|WP|Changelog|Revisit if|Supersedes):\*\*\s*(.*?)\s*$"
)
STATUS_RE = re.compile(r"^(adopted|rejected|superseded by (D-\d{3,}))$")
CHANGELOG_RE = re.compile(r"^(expected|none\s*\(.+\))$")
WP_RE = re.compile(r"^(WP-\d{3,}|intake|spec)$")
CITE_RE = re.compile(r"\((D-\d{3,}),\s*(WP-\d{3,})\)")

REQUIRED_FIELDS = ["Date", "Status", "WP", "Changelog", "Revisit if"]
REQUIRED_SECTIONS = [
    "**Context.**",
    "**Decision.**",
    "**Alternatives considered.**",
    "**Consequences.**",
]
CATEGORIES = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]


@dataclass
class Entry:
    id: str
    number: int
    title: str
    fields: dict[str, str] = field(default_factory=dict)
    body: list[str] = field(default_factory=list)
    line: int = 0


def parse(text: str) -> list[Entry]:
    entries: list[Entry] = []
    current: Entry | None = None
    for lineno, line in enumerate(text.splitlines(), start=1):
        m = ENTRY_RE.match(line)
        if m:
            current = Entry(id=m.group(1), number=int(m.group(2)), title=m.group(3), line=lineno)
            entries.append(current)
            continue
        if current is None:
            continue
        fm = FIELD_RE.match(line)
        if fm:
            current.fields[fm.group(1)] = fm.group(2).strip()
        else:
            current.body.append(line)
    return entries


def index_block(text: str) -> tuple[int, int] | None:
    lines = text.splitlines()
    try:
        begin = lines.index(INDEX_BEGIN)
        end = lines.index(INDEX_END)
    except ValueError:
        return None
    if end <= begin:
        return None
    return begin, end


def render_index(entries: list[Entry]) -> list[str]:
    rows = ["| ID | Decision | Status | Date | WP |", "|---|---|---|---|---|"]
    for e in sorted(entries, key=lambda x: x.number):
        title = e.title.replace("|", "\\|")
        status = e.fields.get("Status", "?")
        dt = e.fields.get("Date", "?")
        wp = e.fields.get("WP", "?")
        rows.append(f"| {e.id} | {title} | {status} | {dt} | {wp} |")
    return rows


def with_index(text: str, entries: list[Entry]) -> str:
    block = index_block(text)
    if block is None:
        raise SystemExit("FAIL: DECISIONS.md has no index markers")
    begin, end = block
    lines = text.splitlines()
    new = lines[: begin + 1] + render_index(entries) + lines[end:]
    return "\n".join(new) + ("\n" if text.endswith("\n") else "")


def changelog_citations(path: Path) -> set[str] | None:
    if not path.exists():
        return None
    return {m.group(1) for m in CITE_RE.finditer(path.read_text(encoding="utf-8"))}


def check(text: str, entries: list[Entry], changelog: Path) -> list[str]:
    problems: list[str] = []
    if index_block(text) is None:
        problems.append("index markers missing (<!-- index:begin --> / <!-- index:end -->)")
    if not entries:
        # An empty ledger is valid at install; the first decision creates the first entry.
        return problems

    seen: dict[str, Entry] = {}
    last = 0
    for e in entries:
        if e.id in seen:
            problems.append(f"{e.id}: duplicate id (first at line {seen[e.id].line})")
        seen[e.id] = e
        if e.number <= last:
            problems.append(f"{e.id}: ids must be strictly increasing")
        last = max(last, e.number)

        for name in REQUIRED_FIELDS:
            if not e.fields.get(name):
                problems.append(f"{e.id}: missing field '{name}'")
        if e.fields.get("Date"):
            try:
                date.fromisoformat(e.fields["Date"])
            except ValueError:
                problems.append(f"{e.id}: date is not ISO (YYYY-MM-DD)")
        status = e.fields.get("Status", "")
        if status and not STATUS_RE.match(status):
            problems.append(f"{e.id}: invalid status '{status}'")
        wp = e.fields.get("WP", "")
        if wp and not WP_RE.match(wp):
            problems.append(f"{e.id}: WP must be WP-nnn, intake or spec, got '{wp}'")
        ch = e.fields.get("Changelog", "")
        if ch and not CHANGELOG_RE.match(ch):
            problems.append(f"{e.id}: Changelog must be 'expected' or 'none (reason)'")

        body = "\n".join(e.body)
        for marker in REQUIRED_SECTIONS:
            if marker not in body:
                problems.append(f"{e.id}: missing section {marker}")
        if "**Alternatives considered.**" in body:
            tail = body.split("**Alternatives considered.**", 1)[1]
            tail = tail.split("**Consequences.**", 1)[0]
            has_bullet = any(line.strip().startswith("- ") for line in tail.splitlines())
            if not has_bullet and "none" not in tail.lower():
                problems.append(f"{e.id}: no alternatives recorded")
        if "**Consequences.**" in body:
            tail = body.split("**Consequences.**", 1)[1]
            if "Good" not in tail or "Bad" not in tail:
                problems.append(f"{e.id}: consequences need a Good and a Bad line")

    # Supersession consistency, both directions.
    for e in entries:
        sup = e.fields.get("Supersedes")
        if sup:
            target = seen.get(sup)
            if target is None:
                problems.append(f"{e.id}: Supersedes {sup} does not exist")
            else:
                if target.number >= e.number:
                    problems.append(f"{e.id}: Supersedes must point to an earlier id")
                expect = f"superseded by {e.id}"
                if target.fields.get("Status") != expect:
                    problems.append(
                        f"{target.id}: status must read '{expect}' (it supersedes via {e.id})"
                    )
        status = e.fields.get("Status", "")
        m = STATUS_RE.match(status)
        if m and m.group(2):
            successor = seen.get(m.group(2))
            if successor is None:
                problems.append(f"{e.id}: superseded by unknown {m.group(2)}")
            else:
                if successor.number <= e.number:
                    problems.append(f"{e.id}: successor {successor.id} must be later")
                if successor.fields.get("Supersedes") != e.id:
                    problems.append(f"{successor.id}: must declare Supersedes: {e.id}")

    citations = changelog_citations(changelog)
    if citations is None:
        if any(e.fields.get("Changelog") == "expected" for e in entries):
            problems.append(f"changelog not found at {changelog}")
    else:
        for e in entries:
            pending = e.fields.get("WP") in {"intake", "spec"}
            if (e.fields.get("Changelog") == "expected"
                    and e.fields.get("Status") == "adopted"
                    and not pending
                    and e.id not in citations):
                problems.append(f"{e.id}: Changelog is 'expected' but no line in {changelog.name} cites it")
            if e.fields.get("Status") == "rejected" and e.fields.get("Changelog", "").startswith("expected"):
                problems.append(f"{e.id}: a rejected decision cannot expect a changelog line")

    block = index_block(text)
    if block:
        begin, end = block
        lines = text.splitlines()
        current = lines[begin + 1 : end]
        if current != render_index(entries):
            problems.append("index is stale (run --write)")
    return problems


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", default="DECISIONS.md")
    ap.add_argument("--changelog", default="CHANGELOG.md")
    ap.add_argument("--write", action="store_true", help="regenerate the index block")
    ap.add_argument("--check", action="store_true", help="fail if the index is stale (default)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        print(f"FAIL: {path} not found")
        return 2
    text = path.read_text(encoding="utf-8")
    entries = parse(text)

    if args.write:
        path.write_text(with_index(text, entries), encoding="utf-8")
        text = path.read_text(encoding="utf-8")

    problems = check(text, entries, Path(args.changelog))
    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1

    adopted = sum(1 for e in entries if e.fields.get("Status") == "adopted")
    rejected = sum(1 for e in entries if e.fields.get("Status") == "rejected")
    superseded = sum(1 for e in entries if e.fields.get("Status", "").startswith("superseded"))
    if args.quiet:
        print(f"ledger: ok ({len(entries)} entries: {adopted} adopted, {rejected} rejected, {superseded} superseded)")
    else:
        print(f"ledger: ok — {len(entries)} entries ({adopted} adopted, {rejected} rejected, {superseded} superseded)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
