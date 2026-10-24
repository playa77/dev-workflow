#!/usr/bin/env python3
"""Test-integrity gate. See workflow/VERIFICATION.md section 2.

Modes:
  --snapshot          record hashes, static test counts and skip markers
  --verify            compare against the snapshot; fail on weakening
  --stash-check SEL   prove a regression test fails without the fix

Exit codes: 0 ok, 1 violation, 2 configuration/setup error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASELINE_DIR = "workflow/state"
BASELINE_FILE = "test-baseline.json"

PATTERNS = {
    "python": [r"(^|/)tests?/", r"(^|/)test_[^/]*\.py$", r"[^/]*_test\.py$"],
    "js": [r"\.(test|spec)\.[cm]?[jt]sx?$", r"(^|/)__tests__/"],
    "go": [r"_test\.go$"],
    "rust": [r"(^|/)tests/.*\.rs$"],
}

COUNT_RE = {
    "python": re.compile(r"^\s*(?:async\s+)?def\s+(test\w*)\s*\(", re.M),
    "js": re.compile(r"\b(?:it|test)(?:\.(?:only|concurrent|todo|skip))?\s*\(", re.M),
    "go": re.compile(r"^func\s+(Test\w+)\s*\(", re.M),
    "rust": re.compile(r"#\[(?:tokio::)?test\]", re.M),
}

SKIP_RE = {
    "python": re.compile(
        r"@pytest\.mark\.skip|@unittest\.skip|pytest\.skip\(|unittest\.skip|@skip\b", re.M
    ),
    "js": re.compile(r"\b(?:it|test|describe)\.skip\s*\(|\bx(?:it|describe)\s*\(", re.M),
    "go": re.compile(r"\bt\.Skip(?:f|Now)?\s*\(", re.M),
    "rust": re.compile(r"#\[ignore(?:\([^)]*\))?\]", re.M),
}

SKIP_EXT = {".py": "python", ".js": "js", ".jsx": "js", ".ts": "js", ".tsx": "js",
            ".mjs": "js", ".cjs": "js", ".go": "go", ".rs": "rust"}

# Directories that are never test locations, even if a filename looks like one.
# Without this, a production module named test_integrity.py (or a harness under
# scripts/) is snapshotted as a test file, and editing it later fails the gate.
EXCLUDE_PREFIXES = ("scripts/", "docs/", "prompts/", "templates/", ".github/",
                    "vendor/", "node_modules/", ".wp/", "workflow/")

# Generated state that must never be stashed or trusted across a comparison.
CACHE_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules",
               ".venv", "venv", "target", "dist", "build", ".next", ".turbo"} 
CACHE_SUFFIXES = {".pyc", ".pyo", ".class", ".o", ".so"}


def is_cache_path(rel: str) -> bool:
    parts = set(Path(rel).parts)
    if parts & CACHE_PARTS:
        return True
    return Path(rel).suffix in CACHE_SUFFIXES


def clear_bytecode_caches(root: Path) -> int:
    """Remove Python bytecode under root.

    Necessary because CPython validates .pyc by source mtime *and* size. A fix
    that changes one character, restored within the same second, can leave a
    valid-looking stale .pyc and make the stash-check pass vacuously. This was
    observed in testing, not theorised.
    """
    removed = 0
    for p in root.rglob("__pycache__"):
        if ".git" in p.parts:
            continue
        for f in p.glob("*.py[co]"):
            try:
                f.unlink()
                removed += 1
            except OSError:
                pass
    return removed


def run(cmd: list[str], cwd: Path, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=check)


def repo_root() -> Path:
    p = run(["git", "rev-parse", "--show-toplevel"], Path.cwd())
    if p.returncode != 0:
        die("not inside a git repository")
    return Path(p.stdout.strip())


def die(msg: str) -> None:
    print(f"integrity: {msg}", file=sys.stderr)
    raise SystemExit(2)


def detect_stack(root: Path) -> str:
    forced = os.environ.get("TEST_STACK", "").strip().lower()
    if forced:
        if forced not in PATTERNS:
            die(f"TEST_STACK={forced!r} is not one of {sorted(PATTERNS)}")
        return forced
    if (root / "pyproject.toml").exists() or (root / "pytest.ini").exists():
        return "python"
    if (root / "package.json").exists():
        return "js"
    if (root / "go.mod").exists():
        return "go"
    if (root / "Cargo.toml").exists():
        return "rust"
    die("cannot detect stack (no pyproject.toml, package.json, go.mod or Cargo.toml); "
        "set TEST_STACK")


def is_test_file(path: str, stack: str) -> bool:
    if path.startswith(EXCLUDE_PREFIXES):
        return False
    return any(re.search(p, path) for p in PATTERNS[stack])


def list_test_files(root: Path, stack: str) -> list[str]:
    override = os.environ.get("TEST_PATHS", "").strip()
    if not override:
        cfg = root / "workflow" / "config.json"
        if cfg.exists():
            try:
                paths = json.loads(cfg.read_text(encoding="utf-8")).get("integrity", {}).get("test_paths") or []
                override = ",".join(paths)
            except json.JSONDecodeError:
                pass
    p = run(["git", "ls-files"], root)
    files = [f for f in p.stdout.splitlines() if f.strip()]
    if override:
        import glob
        out: list[str] = []
        for pat in override.split(","):
            out.extend(sorted({str(Path(m)) for m in glob.glob(pat.strip(), root_dir=root,
                                                             recursive=True)}))
        return sorted(set(out))
    return sorted(f for f in files if is_test_file(f, stack))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def static_stats(root: Path, files: list[str], stack: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for rel in files:
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        out[rel] = {
            "sha256": digest(root / rel),
            "tests": len(COUNT_RE[stack].findall(text)),
            "skips": len(SKIP_RE[stack].findall(text)),
        }
    return out


def baseline_path(root: Path, override: str | None) -> Path:
    if override:
        p = Path(override)
        return p if p.is_absolute() else root / p
    return root / BASELINE_DIR / BASELINE_FILE


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"no baseline at {path}; run --snapshot at branch creation")
    except json.JSONDecodeError as exc:
        die(f"baseline {path} is not valid JSON: {exc}")


def cmd_snapshot(root: Path, stack: str, args) -> int:
    files = list_test_files(root, stack)
    if args.require_tests and not files:
        die(f"no test files found for stack {stack!r}")
    rev = run(["git", "rev-parse", "--short", "HEAD"], root).stdout.strip()
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root).stdout.strip()
    data = {
        "version": 1,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "branch": branch,
        "revision": rev,
        "stack": stack,
        "files": static_stats(root, files, stack),
    }
    path = baseline_path(root, args.baseline)
    save_json(path, data)
    total = sum(v["tests"] for v in data["files"].values())
    print(f"integrity: snapshot {path.relative_to(root)} "
          f"({len(files)} test files, {total} test definitions, rev {rev})")
    return 0


def run_lint(root: Path, files: list[str], warn: bool) -> int:
    lint = Path(__file__).with_name("no_assert_lint.py")
    if not files:
        return 0
    cmd = [sys.executable, str(lint)]
    if warn:
        cmd.append("--warn")
    cmd.extend(files)
    p = subprocess.run(cmd, cwd=str(root), text=True, capture_output=True)
    sys.stdout.write(p.stdout)
    sys.stderr.write(p.stderr)
    return p.returncode


def cmd_verify(root: Path, stack: str, args) -> int:
    base = load_json(baseline_path(root, args.baseline))
    if base.get("stack") and base["stack"] != stack:
        print(f"integrity: WARN baseline stack {base['stack']} != detected {stack}")
    files = list_test_files(root, stack)
    current = static_stats(root, files, stack)
    old = base.get("files", {})

    failures: list[str] = []
    warnings: list[str] = []
    details: list[dict] = []

    removed = sorted(set(old) - set(current))
    for f in removed:
        failures.append(f"removed test file: {f}")

    changed = sorted(f for f in set(old) & set(current) if old[f]["sha256"] != current[f]["sha256"])
    for f in changed:
        msg = f"modified test file: {f}"
        (warnings if args.allow_test_changes else failures).append(msg)

    added = sorted(set(current) - set(old))
    for f in added:
        warnings.append(f"new test file: {f}")

    old_total = sum(v["tests"] for v in old.values())
    new_total = sum(v["tests"] for v in current.values())
    if new_total < old_total:
        failures.append(f"test definitions decreased: {old_total} -> {new_total}")

    old_skips = sum(v["skips"] for v in old.values())
    new_skips = sum(v["skips"] for v in current.values())
    if new_skips > old_skips:
        failures.append(f"skip markers increased: {old_skips} -> {new_skips}")

    touched = changed + added
    if touched and not args.no_lint:
        rc = run_lint(root, touched, warn=args.lint_warn)
        if rc != 0 and not args.lint_warn:
            failures.append(f"no-assert lint failed on {len(touched)} file(s)")

    details = [
        {"check": "removed", "count": len(removed), "items": removed},
        {"check": "modified", "count": len(changed), "items": changed},
        {"check": "added", "count": len(added), "items": added},
        {"check": "test_definitions", "before": old_total, "after": new_total},
        {"check": "skips", "before": old_skips, "after": new_skips},
    ]

    if args.json:
        print(json.dumps({"ok": not failures, "failures": failures, "warnings": warnings,
                          "details": details}, indent=2))
    else:
        print(f"integrity: {len(files)} test files, {new_total} test definitions "
              f"(baseline {old_total}, rev {base.get('revision', '?')})")
        for w in warnings:
            print(f"  note: {w}")
        for f in failures:
            print(f"  FAIL: {f}")
        if not failures:
            print("integrity: ok")
    return 1 if failures else 0


def cmd_stash_check(root: Path, args) -> int:
    """Prove a regression test fails without the fix. See VERIFICATION.md 2.2."""
    if not args.stash_check:
        die("--stash-check needs a test selector")
    status = run(["git", "status", "--porcelain"], root).stdout.splitlines()
    if not status:
        die("working tree is clean: nothing to stash, nothing to prove")

    stack = detect_stack(root)
    non_test: list[str] = []
    for line in status:
        path = line[3:].strip().strip('"')
        if not path or path.startswith((".wp/", "workflow/state/")) or is_cache_path(path):
            continue
        if not is_test_file(path, stack):
            non_test.append(path)
    if not non_test:
        die("no non-test changes to stash; the fix is not in the working tree")

    test_cmd = os.environ.get("TEST_CMD", "").strip()
    if not test_cmd:
        die("TEST_CMD is not set (example: 'python3 -m unittest discover -s tests -q')")

    def run_test() -> int:
        clear_bytecode_caches(root)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(f"{test_cmd} {args.stash_check}", shell=True, cwd=str(root),
                              text=True, capture_output=True, env=env).returncode

    clear_bytecode_caches(root)

    print(f"integrity: fix present, running test (expect PASS)")
    if run_test() != 0:
        print("integrity: FAIL the test does not pass with the fix applied")
        return 1

    print(f"integrity: stashing {len(non_test)} non-test path(s) (expect FAIL)")
    for p in non_test:
        print(f"  - {p}")
    stash = run(["git", "stash", "push", "--include-untracked", "-m",
                 f"wp-stash-check {args.stash_check}", "--", *non_test], root)
    if stash.returncode != 0:
        die(f"git stash failed: {stash.stderr.strip()}")
    try:
        rc = run_test()
    finally:
        pop = run(["git", "stash", "pop"], root)
        if pop.returncode != 0:
            print("integrity: ERROR could not restore the stash. Run `git stash pop` manually.",
                  file=sys.stderr)
            print(pop.stderr, file=sys.stderr)

    if rc == 0:
        print("integrity: FAIL the test passes without the fix: it proves nothing")
        return 1
    print("integrity: ok the test fails without the fix and passes with it")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Test-integrity gate (workflow/VERIFICATION.md)")
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--stash-check", metavar="SELECTOR")
    ap.add_argument("--baseline", help="baseline path (default workflow/state/test-baseline.json)")
    ap.add_argument("--allow-test-changes", action="store_true",
                    help="downgrade modified test files to notes (declaration must justify)")
    ap.add_argument("--no-lint", action="store_true")
    ap.add_argument("--lint-warn", action="store_true")
    ap.add_argument("--require-tests", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = repo_root()
    if args.snapshot:
        return cmd_snapshot(root, detect_stack(root), args)
    if args.stash_check:
        return cmd_stash_check(root, args)
    if args.verify:
        return cmd_verify(root, detect_stack(root), args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
