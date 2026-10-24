#!/usr/bin/env python3
"""Close a work package: changelog line, ledger index, validation, calibration.

Usage:
    python3 workflow/scripts/close-wp.py --wp WP-003 --base main \
        --decision D-010 --summary "Work packages merge automatically on green."

Writes the changelog line only when the package is user-visible (from
`--user-visible`, or `user_visible` in the WP state file). Then runs
check-ledger.py --write and both checks.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

CATEGORIES = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
HEAD_RE = re.compile(r"^## \[([^\]]+)\]")
CITE_RE = re.compile(r"\((D-\d{3,}),\s*(WP-\d{3,})\)")


def summary_from_brief(path: Path) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^##\s*1\.\s*Objective\s*$(.*?)(?=^##\s*\d+\.|\Z)", text, re.M | re.S)
    if not m:
        return None
    body = " ".join(l.strip() for l in m.group(1).splitlines() if l.strip())
    body = body.strip("#* ")
    return body.split(". ")[0].rstrip(".") if body else None


def insert_line(text: str, category: str, line: str) -> str:
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == "## [Unreleased]")
    except StopIteration:
        raise SystemExit("error: CHANGELOG.md has no '## [Unreleased]' heading")
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if HEAD_RE.match(lines[i]):
            end = i
            break

    block = lines[start:end]
    cat_idx = None
    for i, l in enumerate(block):
        if l.strip() == f"### {category}":
            cat_idx = i
            break
    if cat_idx is None:
        block = block[:1] + ["", f"### {category}", "", line] + block[1:]
    else:
        insert_at = cat_idx + 1
        while insert_at < len(block) and not block[insert_at].strip().startswith("### "):
            insert_at += 1
        # walk back over trailing blank lines
        while insert_at > cat_idx + 1 and not block[insert_at - 1].strip():
            insert_at -= 1
        block = block[:insert_at] + [line] + block[insert_at:]
    return "\n".join(lines[:start] + block + lines[end:]) + "\n"


def append_calibration(path: Path, wp: str, base: str) -> None:
    def git(*args: str) -> str:
        p = subprocess.run(["git", *args], capture_output=True, text=True)
        return p.stdout.strip() if p.returncode == 0 else ""

    commits = git("rev-list", "--count", f"{base}..HEAD") or "0"
    first = git("log", "--reverse", "--format=%ct", f"{base}..HEAD").splitlines()
    last = git("log", "-1", "--format=%ct").splitlines()
    wall = ""
    if first and last:
        try:
            wall = f"{(int(last[0]) - int(first[0])) / 3600:.1f}"
        except ValueError:
            wall = ""
    header = ("wp,type,planned_review_cost,wall_hours,active_hours,tool_calls,interruptions,"
              "rework_commits,review_round_trips,review_latency_h,tests_added,test_files_touched,"
              "loc_net_impl,loc_net_tests,verify_seconds,risk_triggers,self_reported")
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(header + "\n", encoding="utf-8")
    row = f"{wp},,,{wall},,,,,,,,,,,,{commits},"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(row + "\n")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wp", required=True)
    ap.add_argument("--base", default="main")
    ap.add_argument("--category", choices=CATEGORIES, default="Changed")
    ap.add_argument("--summary", default=None)
    ap.add_argument("--decision", default=None)
    ap.add_argument("--changelog", default="CHANGELOG.md")
    ap.add_argument("--ledger", default="DECISIONS.md")
    ap.add_argument("--state", default=None)
    ap.add_argument("--brief", default=None)
    ap.add_argument("--user-visible", dest="user_visible", action="store_true", default=None)
    ap.add_argument("--no-user-visible", dest="user_visible", action="store_false")
    ap.add_argument("--no-changelog", action="store_true")
    ap.add_argument("--calibration", action="store_true")
    args = ap.parse_args(argv)

    state_path = Path(args.state or f"docs/wp/{args.wp}.state.json")
    brief_path = Path(args.brief or f"docs/wp/{args.wp}.md")
    state: dict = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"error: {state_path}: {exc}")
            return 2

    user_visible = state.get("user_visible", False)
    if args.user_visible is not None:
        user_visible = args.user_visible
    decision = args.decision or (state.get("decisions") or [None])[0]

    if user_visible and not args.no_changelog:
        if not decision:
            print("error: user-visible package needs --decision or state.decisions[0]")
            return 2
        summary = args.summary or summary_from_brief(brief_path)
        if not summary:
            print("error: user-visible package needs --summary or a brief §1 Objective")
            return 2
        changelog = Path(args.changelog)
        if not changelog.exists():
            print(f"error: {changelog} not found")
            return 2
        text = changelog.read_text(encoding="utf-8")
        if f"({decision}, {args.wp})" in text:
            print("changelog: line already present, skipped")
        else:
            line = f"- {summary.rstrip('.')}. ({decision}, {args.wp})"
            changelog.write_text(insert_line(text, args.category, line), encoding="utf-8")
            print(f"changelog: appended under {args.category}")

    script_dir = Path(__file__).resolve().parent
    subprocess.run([sys.executable, str(script_dir / "check-ledger.py"), "--write", "--quiet"])
    for name in ("check-ledger.py", "check-changelog.py"):
        proc = subprocess.run([sys.executable, str(script_dir / name)])
        if proc.returncode != 0:
            return proc.returncode

    if state_path.exists() and state:
        state["status"] = "delivered"
        state["updated"] = date.today().isoformat() + "T00:00:00Z"
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    if args.calibration:
        append_calibration(Path("workflow/process/CALIBRATION.csv"), args.wp, args.base)
        print("calibration: row appended")

    print(f"close: {args.wp} ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
