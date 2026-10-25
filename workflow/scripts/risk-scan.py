#!/usr/bin/env python3
"""Classify a diff against the risk triggers that inform review.

Usage:
    python3 workflow/scripts/risk-scan.py --base main [--head REV] [--json]
                                          [--fail-on-trigger]

`--head` selects the revision that is inspected (default `HEAD`). The gate uses
it to read a fetched pull request commit as data while its own checkout stays
on the protected default branch.

Every finding carries a severity:

    high, normal   material — a strict review policy (`mode.review:
                   risk-triggered`) requires an independent approval of the
                   exact head commit.
    info           bookkeeping — reported, never approval-triggering.

The default policy (`mode.review: advisory`) reports every finding and blocks
nothing. This script only classifies; `--fail-on-trigger` turns material
findings into a failing check when the script is used on its own.

Prints JSON:
    {"base": "main", "head": "HEAD", "files": 3,
     "triggers": [{"class": "...", "path": "...", "reason": "...",
                   "severity": "high|normal|info"}],
     "counts": {"high": 0, "normal": 0, "info": 0},
     "requires_human": true}

Exit 0 when the scan ran (regardless of triggers), 1 with --fail-on-trigger
when a material trigger exists, 2 on a git or usage error.
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
    # The mechanisms that enforce the method and the tests.
    "enforcement": ["workflow/scripts/**", "workflow/config.json",
                    "workflow/state/test-baseline.json"],
    # Ordinary method prose: rules, process, prompts and templates.
    "method": ["AGENTS.md", "workflow/**"],
    # Explicit API directories; package initialisers are handled by the
    # __all__ / public-definition heuristic in scan(), not by a blanket glob.
    "public_api": ["**/api/**", "**/public/**"],
    # Routine records: reported so they are visible, never approval-triggering.
    # Intake state is deliberately not here: changing recorded requirements is
    # method work, not bookkeeping.
    "bookkeeping": ["DECISIONS.md", "CHANGELOG.md",
                    "workflow/process/CALIBRATION.csv",
                    "workflow/state/install.json"],
}

SEVERITY = {
    "security": "high",
    "data": "high",
    "money": "high",
    "dependencies": "high",
    "ci": "high",
    "enforcement": "high",
    "data_deletion": "high",
    "test-change": "high",
    "test-skip": "high",
    "public_api": "normal",
    "method": "normal",
    "bookkeeping": "info",
}

# A path can match several classes (workflow/scripts/x.py matches enforcement
# and the broader method pattern). Classify it once, by the most specific
# class, so the report stays readable.
CLASS_PRECEDENCE = ["security", "data", "money", "dependencies", "ci",
                    "enforcement", "public_api", "bookkeeping", "method"]
PRECEDENCE_INDEX = {name: index for index, name in enumerate(CLASS_PRECEDENCE)}

TEST_PATTERNS = [r"(^|/)tests?/", r"(^|/)__tests__/", r"test_[^/]*\.py$",
                 r"_test\.go$", r"\.test\.[jt]sx?$", r"\.spec\.[jt]sx?$"]
SKIP_PATTERNS = [r"pytest\.mark\.skip", r"@unittest\.skip", r"\.skip\(",
                 r"\bxit\(", r"it\.skip", r"#\[ignore\]", r"t\.Skip\("]
DELETION_RE = re.compile(
    r"\b(DROP\s+(?:TABLE|DATABASE|SCHEMA)|TRUNCATE\s+TABLE|DELETE\s+FROM)\b"
    r"|rm\s+-rf|shutil\.rmtree\(|os\.remove\(|unlink\("
)
INIT_RE = re.compile(r"(^|/)__init__\.py$")
REMOVED_PUBLIC_DEF_RE = re.compile(
    r"^-(?:async\s+)?(?:def|class)\s+([A-Za-z][A-Za-z0-9_]*)"
)
# Destructive-operation heuristics belong to executable code, not to prose that
# documents them. A README line saying "never run rm -rf /" is not a finding.
CODE_SUFFIXES = {
    ".py", ".sh", ".bash", ".zsh", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".go", ".rs", ".sql", ".rb", ".php", ".pl", ".java", ".kt", ".cs",
    ".yml", ".yaml", ".toml",
}
CODE_NAMES = {"Makefile", "Dockerfile", "Justfile", "Taskfile"}
SELF_PATH = "workflow/scripts/risk-scan.py"


def is_code_path(path: str) -> bool:
    candidate = Path(path)
    return candidate.suffix in CODE_SUFFIXES or candidate.name in CODE_NAMES


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
            triggers = data.get("risk_triggers") if isinstance(data, dict) else None
            if isinstance(triggers, dict) and triggers:
                return {k: list(v) for k, v in triggers.items() if isinstance(v, list)}
        except json.JSONDecodeError:
            pass
    return DEFAULT_TRIGGERS


def is_test(path: str) -> bool:
    return any(re.search(p, path) for p in TEST_PATTERNS)


def trigger(cls: str, path: str, reason: str) -> dict:
    return {"class": cls, "path": path, "reason": reason,
            "severity": SEVERITY.get(cls, "normal")}


def diff_sections(diff: str) -> dict[str, list[str]]:
    """Map each changed path to its added and removed diff lines."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:].strip()
            sections.setdefault(current, [])
            continue
        if line.startswith("diff --git "):
            current = None
            continue
        if current is not None and (line.startswith("+") or line.startswith("-")) \
                and not line.startswith(("+++", "---")):
            sections[current].append(line)
    return sections


def init_public_api_changes(path: str, status: str,
                            changes: list[str]) -> list[tuple[str, str]]:
    """Return public-API findings for a changed package initialiser.

    An ordinary `__init__.py` edit (a docstring, an internal import, a version
    constant) is not an API change. What breaks callers is removing the module,
    changing `__all__`, or removing a public top-level definition.
    """
    findings: list[tuple[str, str]] = []
    if status[:1] in {"D", "R"}:
        findings.append((path, "package initialiser removed or renamed"))
        return findings
    if any(line[1:].strip().startswith("__all__") for line in changes):
        findings.append((path, "changes `__all__` in a package initialiser"))
    for line in changes:
        if not line.startswith("-"):
            continue
        match = REMOVED_PUBLIC_DEF_RE.match(line)
        if match and not match.group(1).startswith("_"):
            findings.append((path, f"removes public top-level definition `{match.group(1)}`"))
            break
    return findings


def scan(cwd: Path, base: str, head: str = "HEAD") -> dict:
    revision = f"{base}...{head}"
    name_status = git(["diff", "--name-status", revision], cwd)
    files: list[tuple[str, str]] = []
    for line in name_status.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            files.append((parts[0], parts[-1]))

    diff = git(["diff", revision, "-U0"], cwd)
    sections = diff_sections(diff)

    triggers: list[dict] = []
    compiled = {cls: [glob_to_regex(p) for p in pats] for cls, pats in load_triggers(cwd).items()}

    for status, path in files:
        matched = [cls for cls, patterns in compiled.items()
                   if any(rx.match(path) for rx in patterns)]
        if matched:
            matched.sort(key=lambda cls: PRECEDENCE_INDEX.get(cls, len(CLASS_PRECEDENCE)))
            cls = matched[0]
            triggers.append(trigger(cls, path, f"path matches a {cls} trigger"))

        if is_test(path) and status[0] in {"M", "D", "R"}:
            triggers.append(trigger(
                "test-change", path,
                f"test file {status} — a weakened test is a silent regression",
            ))

        if INIT_RE.search(path) and "public_api" in compiled:
            for changed_path, reason in init_public_api_changes(
                    path, status, sections.get(path, [])):
                triggers.append(trigger("public_api", changed_path, reason))

    for path, changes in sections.items():
        # The scanner's own source defines the patterns it searches for; that is
        # the one unavoidable false positive. Prose is excluded by suffix.
        if not is_code_path(path) or path == SELF_PATH:
            continue
        for line in changes:
            if line.startswith("+") and DELETION_RE.search(line[1:]):
                triggers.append(trigger("data_deletion", path, line[1:].strip()[:120]))
                break
    for path, changes in sections.items():
        if not is_test(path):
            continue
        for line in changes:
            if line.startswith("+") and any(
                    re.search(pattern, line[1:]) for pattern in SKIP_PATTERNS):
                triggers.append(trigger("test-skip", path, line[1:].strip()[:120]))
                break

    dedup = {(t["class"], t["path"], t["reason"]): t for t in triggers}
    unique = list(dedup.values())
    counts = {"high": 0, "normal": 0, "info": 0}
    for item in unique:
        counts[item["severity"]] = counts.get(item["severity"], 0) + 1
    result = {
        "base": base,
        "head": head,
        "files": len(files),
        "triggers": unique,
        "counts": counts,
        # A material finding is what a strict review policy gates on. Info
        # findings are bookkeeping and never require an approval.
        "requires_human": bool(counts["high"] or counts["normal"]),
    }
    return result


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="main")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true", help="accepted for symmetry; JSON is always printed")
    ap.add_argument("--fail-on-trigger", action="store_true",
                    help="exit 1 when a material finding exists (bookkeeping never fails)")
    args = ap.parse_args(argv)

    try:
        result = scan(Path(args.root), args.base, args.head)
    except RuntimeError as exc:
        print(f"risk-scan: error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    if args.fail_on_trigger and result["requires_human"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
