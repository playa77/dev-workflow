#!/usr/bin/env python3
"""Classify a diff against the risk triggers that force human review.

Usage:
    python3 workflow/scripts/risk-scan.py --base main [--json] [--fail-on-trigger]

Prints JSON:
    {"base": "main", "files": 3, "triggers": [{"class": "...", "path": "...", "reason": "..."}],
     "requires_human": true}

Exit 0 when the scan ran (regardless of triggers), 1 with --fail-on-trigger,
2 on a git or usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_TRIGGERS = {
    "security": ["**/auth/**", "**/authn/**", "**/authz/**", "**/crypto/**",
                 "**/*secret*", "**/.env", "**/*.pem", "**/*.key"],
    "data": ["**/migrations/**", "**/migrate/**", "**/schema/**"],
    "money": ["**/billing/**", "**/payments/**", "**/money/**"],
    "dependencies": ["**/pyproject.toml", "**/package.json", "**/requirements*.txt",
                     "**/go.mod", "**/Cargo.toml", "**/*.lock", "**/poetry.lock",
                     "**/package-lock.json", "**/yarn.lock"],
    "ci": [".github/**"],
    "method": ["AGENTS.md", "DECISIONS.md", "workflow/**"],
    "public_api": ["**/__init__.py"],
}

TEST_PATTERNS = [r"(^|/)tests?/", r"(^|/)__tests__/", r"test_[^/]*\.py$",
                 r"_test\.go$", r"\.test\.[jt]sx?$", r"\.spec\.[jt]sx?$"]
SKIP_PATTERNS = [r"pytest\.mark\.skip", r"@unittest\.skip", r"\.skip\(",
                 r"\bxit\(", r"it\.skip", r"#\[ignore\]", r"t\.Skip\("]
DELETION_RE = re.compile(r"\b(DROP\s+TABLE|TRUNCATE\s+TABLE|DELETE\s+FROM)\b|rm\s+-rf|os\.remove\(|unlink\(")


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    out = ["^"]
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if pattern[i:i + 2] == "**":
                if pattern[i:i + 3] == "**/":
                    out.append("(?:.*/)?")
                    i += 3
                    continue
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(c))
        i += 1
    out.append("$")
    return re.compile("".join(out))


def git(args: list[str], cwd: Path) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def load_triggers(cwd: Path) -> dict[str, list[str]]:
    config = cwd / "workflow" / "config.json"
    if config.exists():
        try:
            data = json.loads(config.read_text(encoding="utf-8"))
            triggers = data.get("risk_triggers")
            if isinstance(triggers, dict) and triggers:
                return {k: list(v) for k, v in triggers.items() if isinstance(v, list)}
        except json.JSONDecodeError:
            pass
    return DEFAULT_TRIGGERS


def is_test(path: str) -> bool:
    return any(re.search(p, path) for p in TEST_PATTERNS)


def scan(cwd: Path, base: str) -> dict:
    name_status = git(["diff", "--name-status", f"{base}...HEAD"], cwd)
    files: list[tuple[str, str]] = []
    for line in name_status.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            files.append((parts[0], parts[-1]))

    diff = git(["diff", f"{base}...HEAD", "-U0"], cwd)
    added = [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]

    triggers: list[dict] = []
    compiled = {cls: [glob_to_regex(p) for p in pats] for cls, pats in load_triggers(cwd).items()}

    for status, path in files:
        for cls, patterns in compiled.items():
            if any(rx.match(path) for rx in patterns):
                triggers.append({"class": cls, "path": path,
                                 "reason": f"path matches a {cls} trigger"})
        if is_test(path) and status[0] in {"M", "D", "R"}:
            triggers.append({"class": "test-change", "path": path,
                             "reason": f"test file {status} — a weakened test is a silent regression"})

    for line in added:
        if DELETION_RE.search(line):
            triggers.append({"class": "data_deletion", "path": "diff",
                             "reason": line.strip()[:120]})
            break
    for line in added:
        if any(re.search(p, line) for p in SKIP_PATTERNS):
            triggers.append({"class": "test-skip", "path": "diff",
                             "reason": line.strip()[:120]})
            break

    dedup = {(t["class"], t["path"], t["reason"]): t for t in triggers}
    result = {
        "base": base,
        "files": len(files),
        "triggers": list(dedup.values()),
        "requires_human": bool(triggers),
    }
    return result


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="main")
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true", help="accepted for symmetry; JSON is always printed")
    ap.add_argument("--fail-on-trigger", action="store_true")
    args = ap.parse_args(argv)

    try:
        result = scan(Path(args.root), args.base)
    except RuntimeError as exc:
        print(f"risk-scan: error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    if args.fail_on_trigger and result["requires_human"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
