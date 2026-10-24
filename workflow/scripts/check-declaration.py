#!/usr/bin/env python3
"""Validate a delivery declaration (workflow/templates/PR.md) as submitted in a PR body.

Textual guards only. Freshness and lane checks need CI metadata and live in the
pipeline. See workflow/VERIFICATION.md section 3.

Exit codes: 0 ok, 1 violation, 2 usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED = [
    (r"^##\s*1\.\s*Status", "status"),
    (r"^##\s*2\.\s*Acceptance", "acceptance"),
    (r"^##\s*3\.\s*Delivery statistics", "statistics"),
    (r"^##\s*4\.\s*Test integrity", "integrity"),
    (r"^##\s*5\.\s*Verification runs", "verification"),
    (r"^##\s*7\.\s*Decisions", "decisions"),
    (r"^##\s*10\.\s*Verifier verdict", "verdict"),
    (r"^##\s*11\.\s*Risk scan", "risk"),
]

PLACEHOLDER = re.compile(r"<[A-Za-z][^<>\n]{0,80}>")
STATUS_OK = ("complete", "partial", "blocked")
VERDICT_OK = ("pass", "fail", "needs-evidence")


def section(text: str, start_pat: str) -> str:
    m = re.search(start_pat, text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"^##\s", rest, re.M)
    return rest[:nxt.start()] if nxt else rest


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a delivery declaration")
    ap.add_argument("path", nargs="?", help="file containing the declaration (default: stdin)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    raw = Path(args.path).read_text(encoding="utf-8") if args.path else sys.stdin.read()
    text = raw.replace("\r\n", "\n")

    problems: list[str] = []

    for pat, name in REQUIRED:
        if not re.search(pat, text, re.M):
            problems.append(f"missing section: {name}")

    # Unfilled placeholders outside HTML comments and fenced code.
    scan_lines = []
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or line.strip().startswith("<!--"):
            continue
        scan_lines.append(line)
    hits = PLACEHOLDER.findall("\n".join(scan_lines))
    if hits:
        problems.append(f"unfilled placeholders: {', '.join(sorted(set(hits))[:6])}")

    status_sec = section(text, r"^##\s*1\.\s*Status")
    first_line = next((l.strip() for l in status_sec.splitlines() if l.strip()), "")
    m = re.search(r"\b(complete|partial|blocked)\b", first_line, re.I)
    status = m.group(1).lower() if m else None
    if not status:
        problems.append("status is not one of complete | partial | blocked")
    if status == "partial" and "instruction" not in status_sec.lower():
        problems.append("partial delivery without a quoted operator instruction")

    stats_sec = section(text, r"^##\s*3\.\s*Delivery statistics")
    if not re.search(r"\|\s*Category\s*\|", stats_sec) and "stats:" not in stats_sec:
        problems.append("statistics section has no generated table")

    acc_sec = section(text, r"^##\s*2\.\s*Acceptance")
    rows = [l for l in acc_sec.splitlines() if l.strip().startswith("|") and "---" not in l]
    if len(rows) < 2:
        problems.append("acceptance table has no criteria rows")

    ver_sec = section(text, r"^##\s*10\.\s*Verifier verdict")
    verdict = next((w for w in VERDICT_OK if re.search(rf"\b{w}\b", ver_sec, re.I)), None)
    if not verdict:
        problems.append("verifier verdict missing or not one of pass | fail | needs-evidence")

    dec_sec = section(text, r"^##\s*7\.\s*Decisions")
    if "none" not in dec_sec.lower() and not re.search(r"\bD-\d{3,}\b", dec_sec):
        problems.append("decisions section names no D-nnn and does not say 'none'")

    if args.json:
        print(json.dumps({"ok": not problems, "status": status, "verdict": verdict,
                          "problems": problems}, indent=2))
    else:
        print(f"declaration: status={status or '?'} verifier={verdict or '?'}")
        for p in problems:
            print(f"  FAIL: {p}")
        if not problems:
            print("declaration: ok")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
