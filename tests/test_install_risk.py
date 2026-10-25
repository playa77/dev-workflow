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
        (self.dir / "DECISIONS.md").write_text("# Decisions\n", encoding="utf-8")
        (self.dir / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
        (self.dir / "workflow" / "process").mkdir(parents=True)
        (self.dir / "workflow" / "process" / "CALIBRATION.csv").write_text(
            "wp\n", encoding="utf-8")
        (self.dir / "workflow" / "scripts").mkdir(parents=True)
        (self.dir / "workflow" / "scripts" / "check-x.py").write_text(
            "x = 1\n", encoding="utf-8")
        (self.dir / ".github" / "workflows").mkdir(parents=True)
        (self.dir / ".github" / "workflows" / "wp.yml").write_text(
            "name: x\n", encoding="utf-8")
        (self.dir / "pkg").mkdir()
        (self.dir / "pkg" / "__init__.py").write_text('"""pkg"""\n', encoding="utf-8")
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

    def test_documentation_mentioning_destructive_commands_is_not_a_finding(self):
        (self.dir / "docs").mkdir()
        (self.dir / "docs" / "operations.md").write_text(
            "Never run `rm -rf /` against production, and never `DROP TABLE users`.\n",
            encoding="utf-8")
        self.commit()
        result = self.scan()
        self.assertNotIn("data_deletion", {t["class"] for t in result["triggers"]})
        self.assertFalse(result["requires_human"])

    def test_skip_marker_in_a_test_file_triggers(self):
        marker = "@unittest." + "skip('later')"
        (self.dir / "tests" / "test_a.py").write_text(
            f"import unittest\n\n\n{marker}\ndef test_a():\n"
            "    assert True\n", encoding="utf-8")
        self.commit()
        result = self.scan()
        self.assertIn("test-skip", {t["class"] for t in result["triggers"]})
        self.assertTrue(result["requires_human"])

    def test_skip_marker_in_documentation_does_not_trigger(self):
        marker = "@unittest." + "skip"
        (self.dir / "docs").mkdir()
        (self.dir / "docs" / "testing.md").write_text(
            f"Do not add {marker} to hide a failing test.\n", encoding="utf-8")
        self.commit()
        result = self.scan()
        self.assertNotIn("test-skip", {t["class"] for t in result["triggers"]})
        self.assertFalse(result["requires_human"])

    def test_decision_ledger_update_is_bookkeeping_not_material(self):
        (self.dir / "DECISIONS.md").write_text(
            "# Decisions\n\n### D-001 — A decision\n", encoding="utf-8")
        self.commit()
        result = self.scan()
        classes = {(t["class"], t["severity"]) for t in result["triggers"]}
        self.assertEqual(classes, {("bookkeeping", "info")})
        self.assertFalse(result["requires_human"])

    def test_calibration_record_is_bookkeeping_not_material(self):
        (self.dir / "workflow" / "process" / "CALIBRATION.csv").write_text(
            "wp\nWP-001\n", encoding="utf-8")
        self.commit()
        result = self.scan()
        self.assertEqual({t["class"] for t in result["triggers"]}, {"bookkeeping"})
        self.assertFalse(result["requires_human"])

    def test_ordinary_package_initialiser_is_not_public_api(self):
        (self.dir / "pkg" / "__init__.py").write_text(
            '"""pkg"""\n\nVERSION = "1"\n', encoding="utf-8")
        self.commit()
        result = self.scan()
        self.assertNotIn("public_api", {t["class"] for t in result["triggers"]})
        self.assertFalse(result["requires_human"])

    def test_all_change_in_package_initialiser_is_public_api(self):
        (self.dir / "pkg" / "__init__.py").write_text(
            '"""pkg"""\n\n__all__ = ["a", "b"]\n', encoding="utf-8")
        self.commit()
        result = self.scan()
        self.assertIn("public_api", {t["class"] for t in result["triggers"]})
        self.assertTrue(result["requires_human"])

    def test_removing_a_public_definition_is_public_api(self):
        path = self.dir / "pkg" / "__init__.py"
        path.write_text('"""pkg"""\n\n\ndef public():\n    pass\n', encoding="utf-8")
        self.commit("add public definition")
        path.write_text('"""pkg"""\n', encoding="utf-8")
        self.commit("remove public definition")
        result = self.scan()
        reasons = {t["reason"] for t in result["triggers"] if t["class"] == "public_api"}
        self.assertTrue(any("removes public top-level definition" in r for r in reasons),
                        result)
        self.assertTrue(result["requires_human"])

    def test_ci_change_is_material(self):
        (self.dir / ".github" / "workflows" / "wp.yml").write_text(
            "name: y\n", encoding="utf-8")
        self.commit()
        result = self.scan()
        self.assertIn("ci", {t["class"] for t in result["triggers"]})
        self.assertTrue(result["requires_human"])

    def test_enforcement_script_change_is_material(self):
        (self.dir / "workflow" / "scripts" / "check-x.py").write_text(
            "x = 2\n", encoding="utf-8")
        self.commit()
        result = self.scan()
        self.assertIn("enforcement", {t["class"] for t in result["triggers"]})
        self.assertTrue(result["requires_human"])

    def test_fail_on_trigger_ignores_bookkeeping(self):
        (self.dir / "DECISIONS.md").write_text(
            "# Decisions\n\n### D-001 — A decision\n", encoding="utf-8")
        self.commit()
        proc = run([sys.executable, str(SCRIPTS / "risk-scan.py"),
                    "--base", "HEAD~1", "--root", str(self.dir), "--fail-on-trigger"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse(json.loads(proc.stdout)["requires_human"])

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
