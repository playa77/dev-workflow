#!/usr/bin/env python3
"""Append a decision entry to DECISIONS.md, then regenerate the index.

Usage:
    python3 workflow/scripts/new-decision.py \
        --title "Use Postgres for the registry" --wp WP-003 \
        --context "The registry needs transactional writes and joins." \
        --decision "Use the existing Postgres cluster; no new datastore." \
        --alternative "SQLite — rejected: single-writer and no network access. Revisit if: the tool ships offline." \
        --good "One datastore to operate." --bad "Couples the tool to the cluster's availability." \
        --revisit "write volume exceeds 5k/s or the cluster is decommissioned"

Rejected decisions: add --status rejected and --changelog "none (nothing shipped)".
Superseding: add --supersedes D-004; the old entry's Status line is updated (the
one permitted in-place edit).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ENTRY_RE = re.compile(r"^### (D-(\d{3,}))\s+—\s+", re.M)
STATUS_LINE_RE = re.compile(r"^- \*\*Status:\*\*.*$", re.M)


def next_id(text: str) -> str:
    nums = [int(m.group(2)) for m in ENTRY_RE.finditer(text)]
    return f"D-{max(nums, default=0) + 1:03d}"


def entry_block(a: argparse.Namespace, did: str) -> str:
    alts = a.alternative or []
    if a.mandated_by:
        alt_lines = [f"- *No alternative was available* — mandated by {a.mandated_by}."]
    elif alts:
        alt_lines = [f"- *{x}*" for x in alts]
    else:
        raise SystemExit("error: provide --alternative or --mandated-by")
    lines = [
        f"### {did} — {a.title}",
        "",
        f"- **Date:** {a.date}",
        f"- **Status:** {a.status}",
        f"- **WP:** {a.wp}",
        f"- **Changelog:** {a.changelog}",
        f"- **Revisit if:** {a.revisit}",
    ]
    if a.supersedes:
        lines.append(f"- **Supersedes:** {a.supersedes}")
    lines += [
        "",
        f"**Context.** {a.context}",
        "",
        f"**Decision.** {a.decision}",
        "",
        "**Alternatives considered.**",
        *alt_lines,
        "",
        "**Consequences.**",
        f"- Good: {a.good}",
        f"- Bad: {a.bad}",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default="DECISIONS.md")
    ap.add_argument("--title", required=True)
    ap.add_argument("--status", choices=["adopted", "rejected"], default="adopted")
    ap.add_argument("--wp", required=True)
    ap.add_argument("--changelog", default=None)
    ap.add_argument("--revisit", required=True)
    ap.add_argument("--context", required=True)
    ap.add_argument("--decision", required=True)
    ap.add_argument("--alternative", action="append", default=[])
    ap.add_argument("--mandated-by", default=None)
    ap.add_argument("--good", required=True)
    ap.add_argument("--bad", required=True)
    ap.add_argument("--supersedes", default=None)
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args(argv)

    if args.changelog is None:
        args.changelog = (
            "none (nothing shipped)" if args.status == "rejected" else "expected"
        )
    if args.status == "rejected" and not args.changelog.startswith("none"):
        print("error: a rejected decision cannot expect a changelog line")
        return 2

    path = Path(args.ledger)
    if not path.exists():
        print(f"error: {path} not found")
        return 2
    text = path.read_text(encoding="utf-8")
    did = next_id(text)

    if args.supersedes:
        m = re.search(
            rf"^### {re.escape(args.supersedes)}\s+—\s+.*?$.*?^- \*\*Status:\*\*.*$",
            text, re.M | re.S,
        )
        if not m:
            print(f"error: {args.supersedes} not found")
            return 2
        updated = STATUS_LINE_RE.sub(
            f"- **Status:** superseded by {did}", m.group(0), count=1
        )
        text = text[: m.start()] + updated + text[m.end():]

    if not text.endswith("\n"):
        text += "\n"
    text += "\n" + entry_block(args, did)
    path.write_text(text, encoding="utf-8")

    script = Path(__file__).with_name("check-ledger.py")
    subprocess.run([sys.executable, str(script), "--write", "--quiet"], check=False)
    print(did)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
