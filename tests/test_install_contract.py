"""Contract tests for install/upgrade behaviour and the CI risk gate.

Companion to test_install_risk.py: these cover what the installer transfers
(constitution, configuration, CI rendering) and what doctor.py accepts.
"""

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


class InstallContractTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "README.md").write_text("# Project\n\nKeep me.\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def install(self, *args):
        return run([sys.executable, str(SCRIPTS / "install.py"),
                    "--target", str(self.dir), "--source", str(ROOT), *args])

    def config(self):
        return json.loads((self.dir / "workflow" / "config.json").read_text(encoding="utf-8"))

    def test_agents_md_is_created_from_the_full_constitution(self):
        proc = self.install()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        agents = (self.dir / "AGENTS.md").read_text(encoding="utf-8")
        constitution = (self.dir / "workflow" / "CONSTITUTION.md").read_text(encoding="utf-8")
        self.assertIn("<!-- workflow:constitution -->", agents)
        self.assertIn("## 1. Delivery unit", agents)
        self.assertIn("## 9. Prohibited", agents)
        self.assertEqual(constitution, (ROOT / "AGENTS.md").read_text(encoding="utf-8").strip() + "\n")

    def test_upgrade_keeps_the_installed_constitution_in_agents_md(self):
        self.install()
        proc = self.install("--upgrade")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        agents = (self.dir / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("## 1. Delivery unit", agents)
        self.assertIn("<!-- workflow:constitution -->", agents)

    def test_existing_agents_md_is_preserved_and_points_at_the_constitution(self):
        (self.dir / "AGENTS.md").write_text("# House rules\n\nKeep me.\n", encoding="utf-8")
        proc = self.install()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        agents = (self.dir / "AGENTS.md").read_text(encoding="utf-8")
        self.assertTrue(agents.startswith("# House rules"))
        self.assertIn("Keep me.", agents)
        self.assertIn("workflow/CONSTITUTION.md", agents)
        self.assertIn("Delivery unit", agents)
        self.assertNotIn("<!-- workflow:constitution -->", agents)

    def test_new_install_defaults_to_human_merge_and_can_opt_in(self):
        self.install()
        self.assertEqual(self.config()["mode"]["merge"], "human")
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        proc = run([sys.executable, str(SCRIPTS / "install.py"),
                    "--target", other.name, "--source", str(ROOT), "--merge-mode", "auto"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        cfg = json.loads((Path(other.name) / "workflow" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["mode"]["merge"], "auto")

    def test_dry_run_writes_nothing(self):
        proc = self.install("--dry-run")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse((self.dir / "workflow").exists())
        self.assertFalse((self.dir / "AGENTS.md").exists())
        self.assertFalse((self.dir / ".github").exists())
        self.assertIn("dry-run: nothing written", proc.stdout)

    def test_upgrade_preserves_edited_config_and_fills_only_missing_roles(self):
        self.install()
        path = self.dir / "workflow" / "config.json"
        cfg = self.config()
        cfg["commands"]["test_full"] = "make verify"
        cfg["mode"]["merge"] = "auto"
        cfg["risk_triggers"] = {"custom": ["**/ledger/**"]}
        cfg["stack"] = ["python"]
        del cfg["commands"]["lint"]
        path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

        proc = self.install("--upgrade")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        after = self.config()
        self.assertEqual(after["commands"]["test_full"], "make verify")
        self.assertEqual(after["mode"]["merge"], "auto")
        self.assertEqual(after["risk_triggers"], {"custom": ["**/ledger/**"]})
        self.assertEqual(after["stack"], ["python"])
        self.assertIn("lint", after["commands"])
        ci = (self.dir / ".github" / "workflows" / "wp.yml").read_text(encoding="utf-8")
        self.assertIn("run: make verify", ci)

    def test_generated_ci_enforces_the_risk_gate(self):
        proc = self.install()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        ci = (self.dir / ".github" / "workflows" / "wp.yml").read_text(encoding="utf-8")
        risk_lines = [l for l in ci.splitlines() if "risk-scan.py" in l]
        self.assertEqual(len(risk_lines), 1, ci)
        self.assertIn("--fail-on-trigger", risk_lines[0])
        self.assertIn("needs-human", ci)
        self.assertIn("pull-requests: write", ci)
        self.assertIn("check-ledger.py", ci)
        self.assertIn("check-changelog.py", ci)

    def test_upgrade_does_not_overwrite_a_ci_file_it_did_not_generate(self):
        self.install()
        ci = self.dir / ".github" / "workflows" / "wp.yml"
        ci.write_text("# custom workflow\n" + ci.read_text(encoding="utf-8"), encoding="utf-8")
        proc = self.install("--upgrade")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = ci.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# custom workflow"))
        self.assertIn("kept (hand-edited)", proc.stdout)


class DoctorKitTest(unittest.TestCase):
    def test_doctor_accepts_the_kit_layout_without_a_ledger_or_changelog(self):
        self.assertFalse((ROOT / "DECISIONS.md").exists())
        self.assertFalse((ROOT / "CHANGELOG.md").exists())
        proc = run([sys.executable, str(SCRIPTS / "doctor.py"), "--root", str(ROOT)])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("doctor: ok", proc.stdout)


class RiskGateExitCodeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        run(["git", "init", "-q"], cwd=self.dir)
        run(["git", "config", "user.email", "t@example.com"], cwd=self.dir)
        run(["git", "config", "user.name", "t"], cwd=self.dir)
        (self.dir / "src" / "auth").mkdir(parents=True)
        (self.dir / "src" / "auth" / "login.py").write_text("x = 1\n", encoding="utf-8")
        run(["git", "add", "-A"], cwd=self.dir)
        run(["git", "commit", "-qm", "base"], cwd=self.dir)
        (self.dir / "src" / "auth" / "login.py").write_text("x = 2\n", encoding="utf-8")
        run(["git", "add", "-A"], cwd=self.dir)
        run(["git", "commit", "-qm", "change"], cwd=self.dir)

    def tearDown(self):
        self.tmp.cleanup()

    def test_fail_on_trigger_turns_a_trigger_into_a_failing_check(self):
        proc = run([sys.executable, str(SCRIPTS / "risk-scan.py"),
                    "--base", "HEAD~1", "--root", str(self.dir), "--fail-on-trigger"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["requires_human"])


if __name__ == "__main__":
    unittest.main()
