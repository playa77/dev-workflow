import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workflow" / "scripts"


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "README.md").write_text("# My project\n\nKeep me.\n", encoding="utf-8")
        (self.dir / "AGENTS.md").write_text("# My rules\n\nDo not lose this.\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def install(self, *args):
        return run([sys.executable, str(SCRIPTS / "install.py"),
                    "--target", str(self.dir), "--source", str(ROOT), *args])

    def test_does_not_clobber_and_is_idempotent(self):
        proc = self.install()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        readme = (self.dir / "README.md").read_text(encoding="utf-8")
        agents = (self.dir / "AGENTS.md").read_text(encoding="utf-8")
        self.assertTrue(readme.startswith("# My project"))
        self.assertIn("Keep me.", readme)
        self.assertIn("workflow-kit:begin", readme)
        self.assertIn("Do not lose this.", agents)
        self.assertIn("workflow:begin", agents)
        self.assertTrue((self.dir / "workflow" / "START.md").exists())
        self.assertTrue((self.dir / "workflow" / "config.json").exists())
        cfg = json.loads((self.dir / "workflow" / "config.json").read_text())
        # The kit's own config must not be copied into the target; a target with
        # no manifest is detected as unknown.
        self.assertEqual(cfg["stack"], ["unknown"])
        self.assertTrue((self.dir / ".github" / "workflows" / "wp.yml").exists())
        self.assertTrue((self.dir / "DECISIONS.md").exists())
        self.assertTrue((self.dir / "CHANGELOG.md").exists())
        mode = (self.dir / "workflow" / "scripts" / "check-ledger.py").stat().st_mode
        self.assertTrue(mode & 0o111)

        before = {p.relative_to(self.dir): p.read_bytes()
                  for p in self.dir.rglob("*") if p.is_file()}
        second = self.install()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        after = {p.relative_to(self.dir): p.read_bytes()
                 for p in self.dir.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


class RiskScanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        run(["git", "init", "-q"], cwd=self.dir)
        run(["git", "config", "user.email", "t@example.com"], cwd=self.dir)
        run(["git", "config", "user.name", "t"], cwd=self.dir)
        (self.dir / "src").mkdir()
        (self.dir / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
        (self.dir / "tests").mkdir()
        (self.dir / "tests" / "test_a.py").write_text(
            "def test_a():\n    assert True\n", encoding="utf-8")
        run(["git", "add", "-A"], cwd=self.dir)
        run(["git", "commit", "-qm", "base"], cwd=self.dir)

    def tearDown(self):
        self.tmp.cleanup()

    def scan(self):
        proc = run([sys.executable, str(SCRIPTS / "risk-scan.py"),
                    "--base", "HEAD~1", "--root", str(self.dir)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def commit(self, message="change"):
        run(["git", "add", "-A"], cwd=self.dir)
        run(["git", "commit", "-qm", message], cwd=self.dir)

    def test_security_and_test_change_trigger(self):
        (self.dir / "src" / "auth").mkdir()
        (self.dir / "src" / "auth" / "x.py").write_text("y = 2\n", encoding="utf-8")
        (self.dir / "tests" / "test_a.py").write_text(
            "def test_a():\n    assert True\n\ndef test_b():\n    assert True\n",
            encoding="utf-8")
        self.commit()
        result = self.scan()
        classes = {t["class"] for t in result["triggers"]}
        self.assertIn("security", classes)
        self.assertIn("test-change", classes)
        self.assertTrue(result["requires_human"])

    def test_benign_change_does_not_trigger(self):
        (self.dir / "src" / "app.py").write_text("x = 2\n", encoding="utf-8")
        self.commit()
        result = self.scan()
        self.assertFalse(result["requires_human"], result)

    def test_deletion_sql_triggers(self):
        (self.dir / "src" / "app.py").write_text(
            "x = 2\nQUERY = 'DROP TABLE users'\n", encoding="utf-8")
        self.commit()
        classes = {t["class"] for t in self.scan()["triggers"]}
        self.assertIn("data_deletion", classes)

    def test_head_scans_a_revision_that_is_not_checked_out(self):
        base = run(["git", "rev-parse", "HEAD"], cwd=self.dir).stdout.strip()
        (self.dir / "src" / "auth").mkdir()
        (self.dir / "src" / "auth" / "x.py").write_text("y = 2\n", encoding="utf-8")
        self.commit()
        head = run(["git", "rev-parse", "HEAD"], cwd=self.dir).stdout.strip()
        # The gate's own checkout stays on the base commit; the head is data.
        run(["git", "reset", "-q", "--hard", base], cwd=self.dir)
        proc = run([sys.executable, str(SCRIPTS / "risk-scan.py"),
                    "--base", base, "--head", head, "--root", str(self.dir)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertTrue(result["requires_human"], result)
        self.assertIn("security", {t["class"] for t in result["triggers"]})


if __name__ == "__main__":
    unittest.main()
