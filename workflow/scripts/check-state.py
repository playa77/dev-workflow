#!/usr/bin/env python3
"""Validate a WP checkpoint against its brief. See workflow/STATE.md section 3.

Invariants:
  1. every brief criterion appears in state.criteria with the same id
  2. no criterion has passes=true with evidence=null
  3. status=verified implies all criteria pass and verification.result=pass
  4. revision is reachable from branch

Exit codes: 0 ok, 1 violation, 2 configuration error.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

CRITERION_RE = re.compile(r"^\s*(\d+)\.\s+(.*\S)\s*$")


def repo_root() -> Path:
    p = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, capture_output=True)
    if p.returncode != 0:
        print("state: not inside a git repository", file=sys.stderr)
        raise SystemExit(2)
    return Path(p.stdout.strip())


def brief_criteria(path: Path) -> dict[int, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^##\s*6\.\s*Acceptance criteria", line, re.I):
            start = i + 1
            break
    if start is None:
        print(f"state: {path} has no '## 6. Acceptance criteria' section", file=sys.stderr)
        raise SystemExit(2)
    out: dict[int, str] = {}
    for line in lines[start:]:
        if line.startswith("## "):
            break
        m = CRITERION_RE.match(line)
        if m:
            out[int(m.group(1))] = m.group(2)
    if not out:
        print(f"state: no numbered criteria found in {path}", file=sys.stderr)
        raise SystemExit(2)
    return out


def reachable(root: Path, revision: str, branch: str) -> bool:
    p = subprocess.run(["git", "merge-base", "--is-ancestor", revision, branch],
                       cwd=str(root), capture_output=True)
    return p.returncode == 0


def revision_shape_ok(rev: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{7,40}", rev or ""))


def branch_exists(root: Path, branch: str) -> bool:
    p = subprocess.run(["git", "rev-parse", "--verify", "--quiet", branch],
                       cwd=str(root), capture_output=True)
    return p.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a WP state checkpoint")
    ap.add_argument("state", nargs="?", help="path to state.json (default: the only docs/wp/*.state.json)")
    ap.add_argument("--wp", help="WP id, e.g. WP-012")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = repo_root()
    if args.state:
        state_path = Path(args.state)
    elif args.wp:
        state_path = root / "docs" / "wp" / f"{args.wp}.state.json"
    else:
        found = sorted((root / "docs" / "wp").glob("*.state.json"))
        if len(found) != 1:
            print(f"state: expected exactly one docs/wp/*.state.json, found {len(found)}; "
                  "pass a path or --wp", file=sys.stderr)
            raise SystemExit(2)
        state_path = found[0]

    if not state_path.exists():
        print(f"state: {state_path} does not exist", file=sys.stderr)
        raise SystemExit(2)
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"state: {state_path} is not valid JSON: {exc}", file=sys.stderr)
        raise SystemExit(2)

    wp = data.get("wp", "")
    brief_path = root / "docs" / "wp" / f"{wp}.md"
    if not brief_path.exists():
        print(f"state: brief {brief_path} not found", file=sys.stderr)
        raise SystemExit(2)

    expected = brief_criteria(brief_path)
    got = {c.get("id"): c for c in data.get("criteria", []) if isinstance(c, dict)}

    failures: list[str] = []
    missing = sorted(set(expected) - set(got))
    extra = sorted(set(got) - set(expected))
    if missing:
        failures.append(f"criteria in brief but not in state: {missing}")
    if extra:
        failures.append(f"criteria in state but not in brief: {extra}")

    for cid, c in sorted(got.items()):
        if c.get("passes") is True and not c.get("evidence"):
            failures.append(f"criterion {cid} passes without evidence")

    status = data.get("status")
    verification = data.get("verification") or {}
    if status == "verified":
        if not all(c.get("passes") is True for c in got.values()):
            failures.append("status=verified but not all criteria pass")
        if verification.get("result") != "pass":
            failures.append("status=verified but verification.result is not 'pass'")

    rev, branch = data.get("revision"), data.get("branch")
    if "user_visible" in data and not isinstance(data["user_visible"], bool):
        failures.append("user_visible must be a boolean")
    decisions = data.get("decisions", [])
    if decisions and not isinstance(decisions, list):
        failures.append("decisions must be a list")
    elif isinstance(decisions, list):
        for d in decisions:
            if not re.fullmatch(r"D-\d{3,}", str(d)):
                failures.append(f"decisions: invalid id {d!r}")
    if rev and not revision_shape_ok(rev):
        failures.append(f"revision must be a commit SHA, got {rev!r}")
    elif rev and branch and not branch_exists(root, branch):
        failures.append(f"branch {branch} does not exist")
    elif rev and branch and not reachable(root, rev, branch):
        failures.append(f"revision {rev} is not reachable from branch {branch}")

    if args.json:
        print(json.dumps({"ok": not failures, "wp": wp, "failures": failures}, indent=2))
    else:
        print(f"state: {wp} status={status} criteria={len(got)}/{len(expected)}")
        for f in failures:
            print(f"  FAIL: {f}")
        if not failures:
            print("state: ok")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
