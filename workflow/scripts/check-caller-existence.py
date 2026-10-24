#!/usr/bin/env python3
"""Caller-existence check: a new definition with no reference anywhere is dead code.

Checks the implementation side of the rule in Doc 2 section 15 ("every specified
module, function and type must have at least one specified caller"). It cannot
read the specification; it answers the narrower question a diff can answer:
did this branch add a symbol that nothing refers to?

Exit codes: 0 ok, 1 violations, 2 configuration error.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

DEF_PATTERNS = {
    "python": [
        re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\("),
        re.compile(r"^\s*class\s+([A-Za-z_]\w*)\s*[\(:]"),
    ],
    "js": [
        re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"),
        re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\("),
        re.compile(r"^\s*(?:export\s+)?(?:interface|type|class|enum)\s+([A-Za-z_$][\w$]*)"),
    ],
    "go": [
        re.compile(r"^func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\("),
        re.compile(r"^type\s+([A-Za-z_]\w*)\s+"),
    ],
    "rust": [
        re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)"),
        re.compile(r"^\s*(?:pub\s+)?(?:struct|enum|trait)\s+([A-Za-z_]\w*)"),
    ],
}

EXT_LANG = {".py": "python", ".js": "js", ".jsx": "js", ".ts": "js", ".tsx": "js",
            ".mjs": "js", ".cjs": "js", ".go": "go", ".rs": "rust"}

TEST_PATH = re.compile(r"(^|/)(tests?|__tests__)/|_test\.\w+$|\.(test|spec)\.\w+$|(^|/)test_[^/]*$")
SKIP_NAMES = {"main", "init", "__init__", "setUp", "tearDown", "setUpClass",
              "tearDownClass", "constructor", "render"}
MAX_BYTES = 2_000_000
MAX_FILES = 20_000
ALLOW_RE = re.compile(r"caller-existence:\s*allow", re.I)


def run(cmd: list[str], cwd: Path) -> str:
    p = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    if p.returncode != 0:
        print(f"callers: {' '.join(cmd)} failed: {p.stderr.strip()}", file=sys.stderr)
        raise SystemExit(2)
    return p.stdout


def repo_root() -> Path:
    p = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, capture_output=True)
    if p.returncode != 0:
        print("callers: not inside a git repository", file=sys.stderr)
        raise SystemExit(2)
    return Path(p.stdout.strip())


def default_base(root: Path) -> str:
    for cand in ("origin/main", "main", "origin/master", "master"):
        p = subprocess.run(["git", "rev-parse", "--verify", "--quiet", cand],
                           cwd=str(root), capture_output=True)
        if p.returncode == 0:
            return cand
    return "HEAD~1"


def added_definitions(root: Path, base: str, committed: bool = False) -> list[dict]:
    rng = f"{base}...HEAD" if committed else base
    diff = run(["git", "diff", "--unified=0", "--no-color", rng], root)
    found: list[dict] = []
    current: str | None = None
    lineno = 0
    recent: list[str] = []
    for raw in diff.splitlines():
        if raw.startswith("+++ b/"):
            current = raw[6:].strip()
            recent = []
            continue
        if raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            lineno = int(m.group(1)) if m else 0
            continue
        if not current:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            line = raw[1:]
            lang = EXT_LANG.get(Path(current).suffix)
            if lang and not TEST_PATH.search(current):
                for pat in DEF_PATTERNS[lang]:
                    m = pat.match(line)
                    if m:
                        found.append({"name": m.group(1), "file": current, "line": lineno,
                                      "lang": lang, "allow": any(ALLOW_RE.search(x) for x in recent)})
                        break
            recent = (recent + [line])[-3:]
            lineno += 1
        elif raw.startswith(" "):
            recent = (recent + [raw[1:]])[-3:]
            lineno += 1
    return found


def load_allowlist(root: Path) -> set[str]:
    path = root / "workflow" / "state" / "callers-allow.txt"
    if not path.exists():
        return set()
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(line)
    return out


def corpus(root: Path) -> dict[str, str]:
    files = run(["git", "ls-files"], root).splitlines()
    texts: dict[str, str] = {}
    for rel in files[:MAX_FILES]:
        p = root / rel
        if not p.is_file():
            continue
        try:
            if p.stat().st_size > MAX_BYTES:
                continue
            data = p.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:4096]:
            continue
        texts[rel] = data.decode("utf-8", errors="replace")
    return texts


def main() -> int:
    ap = argparse.ArgumentParser(description="Flag newly added symbols with no reference")
    ap.add_argument("--base", help="git revision to diff against (default: origin/main)")
    ap.add_argument("--committed", action="store_true",
                    help="diff base...HEAD instead of base...working tree")
    ap.add_argument("--strict", action="store_true",
                    help="require a reference outside the defining file")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = repo_root()
    base = args.base or default_base(root)
    defs = added_definitions(root, base, committed=args.committed)
    allow = load_allowlist(root)
    texts = corpus(root)

    results = []
    for d in defs:
        name = d["name"]
        if d["allow"] or name in allow or name in SKIP_NAMES:
            results.append({**d, "refs": None, "status": "allowed"})
            continue
        if name.startswith("_") and d["lang"] in {"python", "go", "rust"}:
            results.append({**d, "refs": None, "status": "private"})
            continue
        word = re.compile(rf"\b{re.escape(name)}\b")
        total = 0
        other = 0
        for rel, text in texts.items():
            n = len(word.findall(text))
            if n:
                total += n
                if rel != d["file"]:
                    other += n
        if d["lang"] == "python" and name.startswith("__") and name.endswith("__"):
            status = "dunder"
        elif total <= 1:
            status = "unused"
        elif args.strict and other == 0:
            status = "no-external-caller"
        else:
            status = "ok"
        results.append({**d, "refs": total, "external": other, "status": status})

    bad = [r for r in results if r["status"] in {"unused", "no-external-caller"}]
    if args.json:
        print(json.dumps({"base": base, "checked": len(results), "violations": len(bad),
                          "results": results}, indent=2))
    else:
        print(f"callers: {len(results)} new definition(s) vs {base}")
        for r in results:
            if r["status"] == "ok":
                continue
            refs = "-" if r.get("refs") is None else r["refs"]
            print(f"  {r['status']:<18} {r['name']:<32} {r['file']}:{r['line']} refs={refs}")
        if bad:
            print("callers: FAIL definitions with no caller. Add a caller, or record an "
                  "intentional scaffold with a `caller-existence: allow <reason>` comment "
                  "or an entry in workflow/state/callers-allow.txt")
        else:
            print("callers: ok")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
