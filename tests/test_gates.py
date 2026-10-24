import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "workflow" / "scripts"
TOPICS = ["purpose", "users", "scope", "data", "integrations", "security",
          "infrastructure", "performance", "budget", "technology", "operations", "non_goals"]


def run(script, *args):
    return subprocess.run([sys.executable, str(S / script), *args],
                          capture_output=True, text=True)


class IntakeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "README.md").write_text("# x\n", encoding="utf-8")
        self.digest = self.dir / "DIGEST.md"
        self.digest.write_text("Constraint ledger\nNon-goals\nApprove\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, topics, questions=7, open_=None):
        data = {"project": "x", "updated": None, "questions_asked": questions,
                "topics": topics,
                "open": open_ if open_ is not None else sum(
                    1 for t in topics.values() if t.get("status") == "open")}
        p = self.dir / "intake.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def invoke(self, p):
        return run("check-intake.py", "--path", str(p), "--root", str(self.dir),
                   "--digest", str(self.digest))

    def all_answered(self):
        t = {name: {"status": "answered", "answer": "x"} for name in TOPICS}
        t["users"] = {"status": "answered_by_repo", "evidence": "README.md"}
        return t

    def test_valid(self):
        p = self.write(self.all_answered())
        proc = self.invoke(p)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_open_topic_fails(self):
        t = self.all_answered()
        t["security"] = {"status": "open"}
        p = self.write(t, open_=1)
        proc = self.invoke(p)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("open", proc.stdout)

    def test_bad_evidence_path_fails(self):
        t = self.all_answered()
        t["users"] = {"status": "answered_by_repo", "evidence": "NOPE.md"}
        p = self.write(t)
        self.assertEqual(self.invoke(p).returncode, 1)

    def test_deferred_needs_resolved_by(self):
        t = self.all_answered()
        t["data"] = {"status": "deferred", "default": "x", "blast_radius": "local",
                     "revisit_if": "later"}
        p = self.write(t)
        proc = self.invoke(p)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("resolved_by", proc.stdout)

    def test_question_budget(self):
        p = self.write(self.all_answered(), questions=13)
        proc = self.invoke(p)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("budget", proc.stdout)


WP_HEAD = """# WP-001 — Add resolver

| Field | Value |
|---|---|
| Type | `deterministic` |
| Phase | 1 |
| Depends on | none |
| Branch | `feat/wp-001-resolver` |
| Base | `main` |
| Spec refs | `Doc 1 v1 §2` |
| Review cost | `one pass` |
| User-visible effect | Adds a resolver. |
| Decisions expected | `D-001` |
| Status | `proposed` |
"""


def wp(criteria=3, with_uv=True):
    lines = [WP_HEAD if with_uv else WP_HEAD.replace("| User-visible effect | Adds a resolver. |\n", "")]
    for n, title in [(1, "Objective"), (2, "Rationale"), (3, "Scope"), (4, "Out of scope"),
                     (5, "Contracts"), (8, "Prohibited"), (9, "Recovery"), (10, "Completion")]:
        lines.append(f"## {n}. {title}\n\ntext\n")
    lines.append("## 6. Acceptance criteria\n\n")
    lines += [f"{i}. criterion {i}\n" for i in range(1, criteria + 1)]
    lines.append("\n## 7. Verification\n\n| # | Command | Expected |\n|---|---|---|\n| 1 | `true` | 0 |\n")
    lines.append("\n## 11. Preflight\n\n- ok\n")
    return "\n".join(lines)


class WpTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def invoke(self, text):
        p = self.dir / "WP-001.md"
        p.write_text(text, encoding="utf-8")
        return run("check-wp.py", str(p))

    def test_valid(self):
        proc = self.invoke(wp())
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_two_criteria_fail(self):
        proc = self.invoke(wp(criteria=2))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("3–8", proc.stdout)

    def test_missing_user_visible_fails(self):
        proc = self.invoke(wp(with_uv=False))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("User-visible", proc.stdout)


def design():
    parts = ["# Design"]
    for n in range(1, 12):
        parts.append(f"## {n}. Section {n}\n")
        if n == 2:
            parts.append("| # | Constraint |\n|---|---|\n| C-1 | a |\n| C-2 | b |\n| C-3 | c |\n")
    return "\n".join(parts)


def spec(module_in_trace=True):
    parts = ["# Spec"]
    for n in range(1, 17):
        parts.append(f"## {n}. Section {n}\n")
        if n == 8:
            parts.append("### Resolver\n\nResponsibility.\n")
        if n == 15:
            parts.append("Composition root: main.\nSeam register below.\nCall traces below.\n")
            parts.append("| From | To | Ctor | Data | State |\n|---|---|---|---|---|\n"
                         "| a | b | c | d | e |\n")
            if module_in_trace:
                parts.append("Resolver is invoked by main.\n")
        if n == 16:
            parts.append("| Check | Result |\n|---|---|\n| every module in a trace | ok |\n")
    return "\n".join(parts)


class SpecTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.d = self.dir / "DESIGN.md"
        self.s = self.dir / "SPEC.md"

    def tearDown(self):
        self.tmp.cleanup()

    def invoke(self, spec_text=None):
        self.d.write_text(design(), encoding="utf-8")
        self.s.write_text(spec_text or spec(), encoding="utf-8")
        return run("check-spec.py", "--design", str(self.d), "--spec", str(self.s))

    def test_valid(self):
        proc = self.invoke()
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_module_not_in_trace_fails(self):
        proc = self.invoke(spec(module_in_trace=False))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Resolver", proc.stdout)

    def test_placeholder_fails(self):
        proc = self.invoke(spec().replace("Section 4", "TBD"))
        self.assertEqual(proc.returncode, 1)


def roadmap(forward=False):
    dep = "WP-002" if forward else "WP-001"
    parts = [f"## {n}. Section {n}\n" for n in (1, 2, 3, 5, 7)]
    parts.insert(0, "# Roadmap")
    parts.append("## 4. Work packages\n\n### WP-001 — A\n\nDepends on: "
                 + ("WP-002" if forward else "none") + "\n\n### WP-002 — B\n\nDepends on: "
                 + dep + "\n")
    parts.append("## 6. Coverage\n\n| Item | WP |\n|---|---|\n| WP-001 | WP-001 |\n"
                 "| WP-002 | WP-002 |\n")
    return "\n".join(parts)


class RoadmapTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def invoke(self, text):
        p = self.dir / "ROADMAP.md"
        p.write_text(text, encoding="utf-8")
        return run("check-roadmap.py", "--path", str(p))

    def test_valid(self):
        proc = self.invoke(roadmap())
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_forward_dependency_fails(self):
        proc = self.invoke(roadmap(forward=True))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("not earlier", proc.stdout)

    def test_missing_coverage_fails(self):
        proc = self.invoke(roadmap().replace("| WP-002 | WP-002 |\n", ""))
        self.assertEqual(proc.returncode, 1)


if __name__ == "__main__":
    unittest.main()
