#!/usr/bin/env python3
"""Flag test functions that contain no assertion.

A test that calls the code and checks nothing passes forever. This lint is
deliberately shallow: it answers one question — does this test body contain
anything that could fail? See workflow/VERIFICATION.md section 2.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PY_DEF = re.compile(r"^(\s*)(?:async\s+)?def\s+(test\w*)\s*\(")
JS_CALL = re.compile(r"\b(?:it|test)(?:\.(?:only|concurrent))?\s*\(")
GO_FUNC = re.compile(r"^func\s+(Test\w+)\s*\(")
RS_TEST = re.compile(r"^\s*#\[(?:tokio::)?test\]")

PY_ASSERT = re.compile(r"\bassert\b|pytest\.raises|assertRaises|assertEqual|assertTrue|"
                       r"assertIn|assertIs|assertGreater|assertLess|assertAlmost|"
                       r"assertRaisesRegex|assertWarns|pytest\.fail|self\.fail\(")
JS_ASSERT = re.compile(r"\bexpect\s*\(|\bassert\b|\.should\b|\bt\.(?:is|deepEqual|throws)\b")
GO_ASSERT = re.compile(r"\bt\.(?:Error|Errorf|Fatal|Fatalf|Fail|FailNow)\b|\b(?:require|assert)\.")
RS_ASSERT = re.compile(r"\bassert(?:_eq|_ne)?!|\bdebug_assert|\bpanic!|unwrap_err|"
                       r"should_panic|expect_err")


def block_by_indent(lines: list[str], start: int) -> list[str]:
    base = len(lines[start]) - len(lines[start].lstrip())
    out = [lines[start]]
    for line in lines[start + 1:]:
        if not line.strip():
            out.append(line)
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= base:
            break
        out.append(line)
    return out


def block_by_braces(text: str, open_index: int) -> str:
    depth = 0
    started = False
    for i in range(open_index, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
            started = True
        elif ch == "}":
            depth -= 1
            if started and depth == 0:
                return text[open_index:i + 1]
    return text[open_index:]


def check_python(path: Path, warn: bool) -> list[str]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    bad = []
    for i, line in enumerate(lines):
        m = PY_DEF.match(line)
        if not m:
            continue
        body = "\n".join(block_by_indent(lines, i))
        body = body.split("\n", 1)[1] if "\n" in body else ""
        if not PY_ASSERT.search(body):
            bad.append(f"{path}:{i + 1}: {m.group(2)} has no assertion")
    return bad


def check_js(path: Path, warn: bool) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    bad = []
    for m in JS_CALL.finditer(text):
        open_paren = m.end() - 1
        brace = text.find("{", open_paren)
        if brace == -1:
            continue
        body = block_by_braces(text, brace)
        if not JS_ASSERT.search(body):
            line_no = text[:m.start()].count("\n") + 1
            bad.append(f"{path}:{line_no}: test callback has no assertion")
    return bad


def check_go(path: Path, warn: bool) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    bad = []
    for i, line in enumerate(lines):
        m = GO_FUNC.match(line)
        if not m:
            continue
        brace = text.find("{", text.find(line) + len(line))
        if brace == -1:
            continue
        body = block_by_braces(text, brace)
        if not GO_ASSERT.search(body):
            bad.append(f"{path}:{i + 1}: {m.group(1)} has no failure path")
    return bad


def check_rust(path: Path, warn: bool) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    bad = []
    for i, line in enumerate(lines):
        if not RS_TEST.match(line):
            continue
        fn = None
        for j in range(i, min(i + 4, len(lines))):
            m = re.match(r"\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)", lines[j])
            if m:
                fn = (m.group(1), j)
                break
        if not fn:
            continue
        brace = text.find("{", sum(len(x) + 1 for x in lines[:fn[1]]) + len(lines[fn[1]]))
        if brace == -1:
            continue
        body = block_by_braces(text, brace)
        if not RS_ASSERT.search(body):
            bad.append(f"{path}:{fn[1] + 1}: {fn[0]} has no assertion")
    return bad


CHECKERS = {".py": check_python, ".js": check_js, ".jsx": check_js, ".ts": check_js,
            ".tsx": check_js, ".mjs": check_js, ".cjs": check_js, ".go": check_go,
            ".rs": check_rust}


def main() -> int:
    ap = argparse.ArgumentParser(description="Flag tests with no assertion")
    ap.add_argument("--warn", action="store_true", help="report but exit 0")
    ap.add_argument("files", nargs="+")
    args = ap.parse_args()

    findings: list[str] = []
    unsupported: set[str] = set()
    for name in args.files:
        path = Path(name)
        if not path.exists():
            continue
        checker = CHECKERS.get(path.suffix)
        if not checker:
            unsupported.add(path.suffix or "(no extension)")
            continue
        findings.extend(checker(path, args.warn))

    for ext in sorted(unsupported):
        print(f"no-assert: skipped {ext} (no checker for this extension)", file=sys.stderr)
    for f in findings:
        print(f"no-assert: {f}")
    if findings:
        print(f"no-assert: {len(findings)} test(s) without an assertion")
    return 0 if (args.warn or not findings) else 1


if __name__ == "__main__":
    raise SystemExit(main())
