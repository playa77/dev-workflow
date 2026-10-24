#!/usr/bin/env python3
"""Structural checks on DESIGN.md and SPEC.md.

Usage:
    python3 workflow/scripts/check-spec.py [--design docs/design/DESIGN.md]
                                           [--spec docs/spec/SPEC.md]

Structural only: sections, seams, module traces, placeholders. It cannot judge
whether the architecture is right; that is the executability trace and the verifier.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DESIGN_SECTIONS = 11
SPEC_SECTIONS = 16
PLACEHOLDERS = ["TBD", "TODO", "to be determined", "FIXME"]


def numbered(text: str, n: int) -> str | None:
    m = re.search(rf"^##\s*{n}\.\s.*?$(.*?)(?=^##\s*\d+\.|\Z)", text, re.M | re.S)
    return m.group(1) if m else None


def headings(body: str) -> list[str]:
    return [m.group(1).strip().strip("`") for m in re.finditer(r"^###\s+(.+?)\s*$", body, re.M)]


def table_rows(body: str) -> list[str]:
    rows = []
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            continue
        if re.match(r"^\|[\s:|-]+\|$", line.strip()):
            continue
        rows.append(line)
    return rows


def check_design(text: str) -> list[str]:
    problems = []
    for n in range(1, DESIGN_SECTIONS + 1):
        if numbered(text, n) is None:
            problems.append(f"design: missing section {n}")
    sec2 = numbered(text, 2) or ""
    if len(table_rows(sec2)) + len([l for l in sec2.splitlines() if l.strip().startswith("- ")]) < 3:
        problems.append("design: §2 constraint ledger has fewer than three entries")
    for p in PLACEHOLDERS:
        if p.lower() in text.lower():
            problems.append(f"design: placeholder '{p}'")
    return problems


def check_spec(text: str) -> list[str]:
    problems = []
    for n in range(1, SPEC_SECTIONS + 1):
        if numbered(text, n) is None:
            problems.append(f"spec: missing section {n}")
    for p in PLACEHOLDERS:
        if p.lower() in text.lower():
            problems.append(f"spec: placeholder '{p}'")

    sec15 = numbered(text, 15) or ""
    low = sec15.lower()
    for needle in ("composition root", "seam register", "call trace"):
        if needle not in low:
            problems.append(f"spec: §15 missing '{needle}'")
    seam_rows = [r for r in table_rows(sec15) if r.count("|") >= 5]
    if len(seam_rows) < 2:  # header + at least one seam
        problems.append("spec: §15 seam table has no data rows")

    sec8 = numbered(text, 8) or ""
    modules = headings(sec8)
    if not modules:
        problems.append("spec: §8 has no module subsections")
    for mod in modules:
        short = mod.split("—")[0].strip()
        if short and short.lower() not in low:
            problems.append(f"spec: module '{short}' does not appear in §15 call traces")

    sec16 = numbered(text, 16) or ""
    for row in table_rows(sec16)[1:]:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) >= 2 and not cells[-1]:
            problems.append(f"spec: §16 checklist row not completed: {cells[0][:60]}")
    return problems


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--design", default="docs/design/DESIGN.md")
    ap.add_argument("--spec", default="docs/spec/SPEC.md")
    args = ap.parse_args(argv)

    problems: list[str] = []
    for path, fn in ((Path(args.design), check_design), (Path(args.spec), check_spec)):
        if not path.exists():
            problems.append(f"{path} not found")
            continue
        problems.extend(fn(path.read_text(encoding="utf-8")))

    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1
    print("spec: ok — sections, seams, module traces and checklist")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
