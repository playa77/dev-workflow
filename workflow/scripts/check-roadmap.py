#!/usr/bin/env python3
"""Structural checks on ROADMAP.md: DAG, dependencies, coverage.

Usage:
    python3 workflow/scripts/check-roadmap.py [--path docs/roadmap/ROADMAP.md]
                                              [--spec docs/spec/SPEC.md]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

WP_RE = re.compile(r"^###\s+(WP-(\d{3,}))\b", re.M)
DEP_RE = re.compile(r"(?i)depends[- ]on\s*:?\s*(.*)$")
ID_RE = re.compile(r"WP-\d{3,}")


def numbered(text: str, n: int) -> str | None:
    m = re.search(rf"^##\s*{n}\.\s.*?$(.*?)(?=^##\s*\d+\.|\Z)", text, re.M | re.S)
    return m.group(1) if m else None


def wp_blocks(text: str) -> dict[str, str]:
    matches = list(WP_RE.finditer(text))
    blocks: dict[str, str] = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks[m.group(1)] = text[m.end():end]
    return blocks


def check(text: str, spec: str | None) -> list[str]:
    problems: list[str] = []
    for n in range(1, 8):
        if numbered(text, n) is None:
            problems.append(f"missing section {n}")

    blocks = wp_blocks(text)
    if not blocks:
        problems.append("no '### WP-nnn' entries")
        return problems

    deps: dict[str, list[str]] = {}
    for wp, body in blocks.items():
        line = next((l for l in body.splitlines() if DEP_RE.search(l)), "")
        m = DEP_RE.search(line) if line else None
        if not m:
            problems.append(f"{wp}: no depends-on line")
            deps[wp] = []
            continue
        ids = ID_RE.findall(m.group(1))
        deps[wp] = ids
        for d in ids:
            if d not in blocks:
                problems.append(f"{wp}: depends on unknown {d}")
            elif int(d.split("-")[1]) >= int(wp.split("-")[1]):
                problems.append(f"{wp}: depends on {d}, which is not earlier")

    # cycle detection (defensive; the ordering rule already implies acyclicity)
    colour: dict[str, int] = {}

    def visit(node: str, stack: list[str]) -> None:
        if colour.get(node) == 1:
            problems.append(f"dependency cycle: {' -> '.join(stack + [node])}")
            return
        if colour.get(node) == 2:
            return
        colour[node] = 1
        for d in deps.get(node, []):
            if d in blocks:
                visit(d, stack + [node])
        colour[node] = 2

    for wp in blocks:
        visit(wp, [])

    coverage = numbered(text, 6) or ""
    cov_rows = [l for l in coverage.splitlines() if l.strip().startswith("|")]
    cov_rows = [l for l in cov_rows if not re.match(r"^\|[\s:|-]+\|$", l.strip())][1:]
    if len(cov_rows) < len(blocks):
        problems.append(f"coverage matrix has {len(cov_rows)} rows for {len(blocks)} packages")
    for wp in blocks:
        if wp not in coverage:
            problems.append(f"{wp}: missing from the coverage matrix")

    if spec:
        sec8 = numbered(spec, 8) or ""
        modules = [m.group(1).strip().strip("`") for m in re.finditer(r"^###\s+(.+?)\s*$", sec8, re.M)]
        for mod in modules:
            short = mod.split("—")[0].strip()
            if short and short.lower() not in coverage.lower():
                problems.append(f"module '{short}' missing from the coverage matrix")

    for p in ("TBD", "TODO", "and so on"):
        if p.lower() in text.lower():
            problems.append(f"placeholder '{p}'")
    return problems


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", default="docs/roadmap/ROADMAP.md")
    ap.add_argument("--spec", default=None)
    args = ap.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        print(f"FAIL: {path} not found")
        return 2
    spec_text = None
    if args.spec and Path(args.spec).exists():
        spec_text = Path(args.spec).read_text(encoding="utf-8")
    problems = check(path.read_text(encoding="utf-8"), spec_text)
    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1
    print("roadmap: ok — DAG, dependencies and coverage")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
