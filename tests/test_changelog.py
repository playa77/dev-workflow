import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workflow" / "scripts" / "check-changelog.py"

LEDGER = """# Decision ledger

<!-- index:begin -->
<!-- index:end -->

### D-001 — Use X

- **Date:** 2026-10-25
- **Status:** adopted
- **WP:** intake
- **Changelog:** expected
- **Revisit if:** never

**Context.** c

**Decision.** d

**Alternatives considered.**
- *Y* — rejected: reason.

**Consequences.**
- Good: g
- Bad: b

---
"""


class ChangelogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.led = self.dir / "DECISIONS.md"
        self.led.write_text(LEDGER, encoding="utf-8")
        self.cha = self.dir / "CHANGELOG.md"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, text):
        self.cha.write_text(text, encoding="utf-8")

    def invoke(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--path", str(self.cha), "--ledger", str(self.led),
             "--version-file", str(self.dir / "NOFILE"), "--wp-dir", str(self.dir / "nowp")],
            capture_output=True, text=True,
        )

    def test_valid(self):
        self.write("""# Changelog

## [Unreleased]

### Added
- A thing. (D-001, WP-001)

## [1.0.0] - 2026-10-20

### Fixed
- An older thing. (D-001, WP-001)
""")
        proc = self.invoke()
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_missing_citation(self):
        self.write("## [Unreleased]\n\n### Added\n- A thing.\n")
        self.assertEqual(self.invoke().returncode, 1)

    def test_unknown_decision(self):
        self.write("## [Unreleased]\n\n### Added\n- A thing. (D-999, WP-001)\n")
        proc = self.invoke()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("does not exist", proc.stdout)

    def test_invalid_category(self):
        self.write("## [Unreleased]\n\n### Misc\n- A thing. (D-001, WP-001)\n")
        proc = self.invoke()
        self.assertEqual(proc.returncode, 1)

    def test_unreleased_must_be_first(self):
        self.write("## [1.0.0] - 2026-10-20\n\n### Added\n- A thing. (D-001, WP-001)\n")
        proc = self.invoke()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Unreleased", proc.stdout)

    def test_commit_hash_rejected(self):
        self.write("## [Unreleased]\n\n### Added\n- Change abc1234 here. (D-001, WP-001)\n")
        proc = self.invoke()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("hash", proc.stdout)

    def test_reverse_chronological(self):
        good = ("## [Unreleased]\n\n## [2.0.0] - 2026-10-20\n\n### Added\n- x. (D-001, WP-001)\n\n"
                "## [1.0.0] - 2026-10-01\n\n### Added\n- y. (D-001, WP-001)\n")
        self.write(good)
        self.assertEqual(self.invoke().returncode, 0)
        bad = ("## [Unreleased]\n\n## [1.0.0] - 2026-10-01\n\n### Added\n- y. (D-001, WP-001)\n\n"
               "## [2.0.0] - 2026-10-20\n\n### Added\n- x. (D-001, WP-001)\n")
        self.write(bad)
        self.assertEqual(self.invoke().returncode, 1)


if __name__ == "__main__":
    unittest.main()
