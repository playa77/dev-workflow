import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workflow" / "scripts" / "close-wp.py"
SEED = ROOT / "workflow" / "templates" / "CHANGELOG.seed.md"

LEDGER = """# Decision ledger

<!-- index:begin -->
<!-- index:end -->

### D-001 — Use the resolver

- **Date:** 2026-10-25
- **Status:** adopted
- **WP:** WP-001
- **Changelog:** expected
- **Revisit if:** never

**Context.** c

**Decision.** d

**Alternatives considered.**
- *Other* — rejected: reason.

**Consequences.**
- Good: g
- Bad: b

---
"""


class CloseWpTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "docs" / "wp").mkdir(parents=True)
        (self.dir / "DECISIONS.md").write_text(LEDGER, encoding="utf-8")
        (self.dir / "CHANGELOG.md").write_text(SEED.read_text(encoding="utf-8"), encoding="utf-8")
        (self.dir / "docs" / "wp" / "WP-001.md").write_text(
            "# WP-001 — Resolver\n\n## 1. Objective\n\nAdd the resolver.\n\n"
            "## 6. Acceptance criteria\n\n1. a\n2. b\n3. c\n", encoding="utf-8")
        (self.dir / "docs" / "wp" / "WP-001.state.json").write_text(json.dumps({
            "wp": "WP-001", "status": "in-progress", "user_visible": True,
            "decisions": ["D-001"], "criteria": [],
        }), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def invoke(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--wp", "WP-001", "--base", "main",
             "--decision", "D-001"],
            cwd=self.dir, capture_output=True, text=True,
        )

    def test_close_appends_and_marks_delivered(self):
        proc = self.invoke()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = (self.dir / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("- Add the resolver. (D-001, WP-001)", text)
        state = json.loads((self.dir / "docs/wp/WP-001.state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "delivered")

    def test_close_is_idempotent(self):
        self.invoke()
        first = (self.dir / "CHANGELOG.md").read_text(encoding="utf-8")
        proc = self.invoke()
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(first, (self.dir / "CHANGELOG.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
