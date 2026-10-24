import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workflow" / "scripts" / "check-ledger.py"
INDEX = "<!-- index:begin -->\n<!-- index:end -->"


def entry(
    id="D-001",
    title="Use X",
    status="adopted",
    wp="intake",
    changelog="expected",
    revisit="never",
    supersedes=None,
    alternatives="- *Y* — rejected: slower. Revisit if: never.",
    consequences=("- Good: simpler", "- Bad: one more moving part"),
):
    lines = [
        f"### {id} — {title}",
        "",
        "- **Date:** 2026-10-25",
        f"- **Status:** {status}",
        f"- **WP:** {wp}",
        f"- **Changelog:** {changelog}",
        f"- **Revisit if:** {revisit}",
    ]
    if supersedes:
        lines.append(f"- **Supersedes:** {supersedes}")
    lines += [
        "",
        "**Context.** a constraint",
        "",
        "**Decision.** do the thing",
        "",
        "**Alternatives considered.**",
        alternatives,
        "",
        "**Consequences.**",
        *consequences,
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def ledger(*entries):
    return "# Decision ledger\n\n" + INDEX + "\n\n" + "\n".join(entries)


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, entries, lines=("- change. (D-001, WP-001)",)):
        led = self.dir / "DECISIONS.md"
        cha = self.dir / "CHANGELOG.md"
        led.write_text(ledger(*entries), encoding="utf-8")
        cha.write_text(
            "# Changelog\n\n## [Unreleased]\n\n### Changed\n" + "\n".join(lines) + "\n",
            encoding="utf-8",
        )
        return led, cha

    def invoke(self, led, cha, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--path", str(led), "--changelog", str(cha), *args],
            capture_output=True, text=True,
        )

    def test_valid_ledger_passes(self):
        led, cha = self.write([entry()])
        self.assertEqual(self.invoke(led, cha, "--write").returncode, 0)
        proc = self.invoke(led, cha)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("ok", proc.stdout)

    def test_duplicate_id_fails(self):
        led, cha = self.write([entry(), entry()])
        self.invoke(led, cha, "--write")
        proc = self.invoke(led, cha)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("duplicate", proc.stdout)

    def test_missing_field_fails(self):
        text = entry().replace("- **Revisit if:** never\n", "")
        led = self.dir / "DECISIONS.md"
        cha = self.dir / "CHANGELOG.md"
        led.write_text(ledger(text), encoding="utf-8")
        cha.write_text("## [Unreleased]\n\n- x. (D-001, WP-001)\n", encoding="utf-8")
        self.invoke(led, cha, "--write")
        proc = self.invoke(led, cha)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Revisit if", proc.stdout)

    def test_stale_index_fails(self):
        led, cha = self.write([entry()])
        proc = self.invoke(led, cha)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("stale", proc.stdout)

    def test_supersede_consistent_passes(self):
        old = entry(id="D-001", status="superseded by D-002")
        new = entry(id="D-002", title="Use Z", supersedes="D-001", changelog="expected")
        led, cha = self.write([old, new], lines=("- change. (D-002, WP-001)",))
        self.invoke(led, cha, "--write")
        proc = self.invoke(led, cha)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_supersede_without_status_fails(self):
        new = entry(id="D-002", supersedes="D-001")
        led, cha = self.write([entry(), new], lines=("- change. (D-002, WP-001)",))
        self.invoke(led, cha, "--write")
        proc = self.invoke(led, cha)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("status must read", proc.stdout)

    def test_expected_changelog_missing_fails(self):
        led, cha = self.write([entry(wp="WP-001")], lines=())
        self.invoke(led, cha, "--write")
        proc = self.invoke(led, cha)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no line", proc.stdout)

    def test_rejected_with_expected_fails(self):
        led, cha = self.write([entry(status="rejected", changelog="expected")])
        self.invoke(led, cha, "--write")
        proc = self.invoke(led, cha)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("rejected", proc.stdout)

    def test_missing_bad_consequence_fails(self):
        led, cha = self.write([entry(consequences=("- Good: simpler",))])
        self.invoke(led, cha, "--write")
        proc = self.invoke(led, cha)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Good and a Bad", proc.stdout)

    def test_decreasing_ids_fail(self):
        led, cha = self.write([entry(id="D-002"), entry(id="D-001")])
        self.invoke(led, cha, "--write")
        proc = self.invoke(led, cha)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("increasing", proc.stdout)


if __name__ == "__main__":
    unittest.main()
