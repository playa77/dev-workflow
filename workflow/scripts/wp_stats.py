#!/usr/bin/env python3
"""Machine-generated delivery statistics.

Produces the category split required by AGENTS.md section 7:
handwritten implementation | tests and helpers | fixture data | generated files |
documentation, plus additions/deletions versus net growth. Never hand-written.

Exit codes: 0 ok, 2 configuration error.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_CATEGORIES: list[tuple[str, list[str]]] = [
    ("generated", ["**/generated/**", "**/*_pb2.py", "**/*.pb.go", "**/*.g.dart",
                   "**/*.min.js", "**/*.min.css", "**/*.lock", "package-lock.json",
                   "uv.lock", "poetry.lock", "yarn.lock", "pnpm-lock.yaml"]),
    ("fixtures", ["**/fixtures/**", "**/testdata/**", "**/__snapshots__/**",
                  "**/golden/**", "**/*.snap"]),
    ("tests", ["tests/**", "test/**", "**/__tests__/**", "**/*_test.*", "**/test_*.*",
               "**/*.test.*", "**/*.spec.*"]),
    ("docs", ["docs/**", "**/*.md", "**/*.mdx", "**/*.rst", "**/*.txt"]),
    ("handwritten", ["**"]),
]

CATEGORY_ORDER = [c for c, _ in DEFAULT_CATEGORIES]


def run(cmd: list[str], cwd: Path) -> str:
    p = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    if p.returncode != 0:
        print(f"stats: {' '.join(cmd)} failed: {p.stderr.strip()}", file=sys.stderr)
        raise SystemExit(2)
    return p.stdout


def repo_root() -> Path:
    p = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, capture_output=True)
    if p.returncode != 0:
        print("stats: not inside a git repository", file=sys.stderr)
        raise SystemExit(2)
    return Path(p.stdout.strip())


def default_base(root: Path) -> str:
    for cand in ("origin/main", "main", "origin/master", "master"):
        p = subprocess.run(["git", "rev-parse", "--verify", "--quiet", cand],
                           cwd=str(root), capture_output=True)
        if p.returncode == 0:
            return cand
    return "HEAD~1"


def glob_to_regex(pattern: str) -> re.Pattern:
    out = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


CATEGORY_RES = [(name, [glob_to_regex(p) for p in pats]) for name, pats in DEFAULT_CATEGORIES]


def categorize(path: str) -> str:
    for name, regexes in CATEGORY_RES:
        if any(r.match(path) for r in regexes):
            return name
    return "handwritten"


def load_config(root: Path) -> None:
    """Optional workflow/state/stats.conf: JSON {"categories": {"name": ["glob", ...]}}."""
    path = root / "workflow" / "state" / "stats.conf"
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"stats: workflow/state/stats.conf is not valid JSON: {exc}", file=sys.stderr)
        raise SystemExit(2)
    global CATEGORY_RES, CATEGORY_ORDER
    cats = data.get("categories")
    if isinstance(cats, dict) and cats:
        CATEGORY_RES = [(name, [glob_to_regex(p) for p in pats]) for name, pats in cats.items()]
        CATEGORY_ORDER = [name for name, _ in CATEGORY_RES]


def main() -> int:
    ap = argparse.ArgumentParser(description="Delivery statistics by category")
    ap.add_argument("--base", help="git revision to diff against (default: origin/main)")
    ap.add_argument("--committed", action="store_true",
                    help="compare base...HEAD instead of base...working tree")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = repo_root()
    load_config(root)
    base = args.base or default_base(root)
    mb = run(["git", "merge-base", base, "HEAD"], root).strip()
    rng = f"{mb}..HEAD" if args.committed else mb

    numstat = run(["git", "diff", "--numstat", rng], root)
    names = run(["git", "diff", "--name-status", rng], root)

    added_files = set()
    for line in names.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].startswith("A"):
            added_files.add(parts[-1])

    totals = {c: {"files": 0, "added": 0, "deleted": 0, "net": 0, "new_files": 0}
              for c in CATEGORY_ORDER}
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        add, dele, path = parts
        if path.startswith((".wp/", "workflow/state/")):
            continue
        if add == "-" or dele == "-":  # binary
            add_i = dele_i = 0
        else:
            add_i, dele_i = int(add), int(dele)
        cat = categorize(path)
        bucket = totals.setdefault(cat, {"files": 0, "added": 0, "deleted": 0,
                                         "net": 0, "new_files": 0})
        bucket["files"] += 1
        bucket["added"] += add_i
        bucket["deleted"] += dele_i
        bucket["net"] += add_i - dele_i
        if path in added_files:
            bucket["new_files"] += 1

    total = {k: sum(v[k] for v in totals.values()) for k in
             ("files", "added", "deleted", "net", "new_files")}
    tests = totals.get("tests", {"files": 0, "new_files": 0})

    if args.json:
        print(json.dumps({"base": base, "range": rng, "categories": totals, "total": total,
                          "test_files_new": tests["new_files"],
                          "test_files_touched": tests["files"]}, indent=2))
        return 0

    print(f"stats: {rng} (base {base})")
    print()
    print("| Category | Files | Added | Deleted | Net | New files |")
    print("|---|---:|---:|---:|---:|---:|")
    for name in CATEGORY_ORDER:
        v = totals.get(name)
        if not v or v["files"] == 0:
            continue
        print(f"| {name} | {v['files']} | {v['added']} | {v['deleted']} | {v['net']:+d} | "
              f"{v['new_files']} |")
    print(f"| **total** | {total['files']} | {total['added']} | {total['deleted']} | "
          f"{total['net']:+d} | {total['new_files']} |")
    print()
    print(f"tests: {tests['new_files']} new test file(s), {tests['files']} test file(s) touched")
    print(f"net growth: {total['net']:+d} lines "
          f"({total['added']} added, {total['deleted']} deleted)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
