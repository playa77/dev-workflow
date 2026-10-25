"""Acceptance tests for the solo-developer default lifecycle.

One repository, one GitHub identity: the agent implements, tests and opens a
PR; CI validates and reports risks; the owner reviews and merges. No second
identity participates. Strict review remains available as an explicit opt-in.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workflow" / "scripts"


def run(cmd, cwd=None):
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )


class SoloLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        run(["git", "init", "-q"], cwd=self.dir)
        run(["git", "checkout", "-q", "-b", "main"], cwd=self.dir)
        run(["git", "config", "user.email", "solo@example.com"], cwd=self.dir)
        run(["git", "config", "user.name", "Solo Owner"], cwd=self.dir)
        (self.dir / "pyproject.toml").write_text(
            '[project]\nname = "solo"\nversion = "0.1.0"\n', encoding="utf-8")
        (self.dir / "src").mkdir()
        (self.dir / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
        (self.dir / "tests").mkdir()
        (self.dir / "tests" / "test_app.py").write_text(
            "import unittest\n\n\nclass T(unittest.TestCase):\n"
            "    def test_ok(self):\n        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        run(["git", "add", "-A"], cwd=self.dir)
        run(["git", "commit", "-qm", "base"], cwd=self.dir)

        proc = run([sys.executable, str(SCRIPTS / "install.py"),
                    "--target", str(self.dir), "--source", str(ROOT)], cwd=self.dir)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.commit("install workflow kit")

        self.config_path = self.dir / "workflow" / "config.json"
        self.scripts = self.dir / "workflow" / "scripts"

    def tearDown(self):
        self.tmp.cleanup()

    def config(self):
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def write_config(self, **mode):
        cfg = self.config()
        cfg["mode"].update(mode)
        self.config_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

    def commit(self, message):
        run(["git", "add", "-A"], cwd=self.dir)
        run(["git", "commit", "-qm", message], cwd=self.dir)

    def risk_branch(self):
        run(["git", "checkout", "-q", "-b", "feat/risk-change"], cwd=self.dir)
        (self.dir / "src" / "auth").mkdir(parents=True)
        (self.dir / "src" / "auth" / "login.py").write_text("x = 1\n", encoding="utf-8")
        self.commit("add authentication code")

    def gate(self):
        return run([sys.executable, str(self.scripts / "risk-gate.py"),
                    "--base", "main", "--head", "HEAD", "--root", str(self.dir)],
                   cwd=self.dir)

    def doctor(self):
        return run([sys.executable, str(self.scripts / "doctor.py"),
                    "--root", str(self.dir)], cwd=self.dir)

    def test_a_single_owner_can_complete_the_lifecycle_without_a_second_identity(self):
        cfg = self.config()
        self.assertEqual(cfg["mode"]["merge"], "human")
        self.assertEqual(cfg["mode"]["review"], "advisory")

        doctor = self.doctor()
        self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
        self.assertIn("review mode: advisory (solo default)", doctor.stdout)

        self.risk_branch()
        proc = self.gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        decision = json.loads(proc.stdout)
        self.assertEqual(decision["verdict"], "advisory")
        self.assertTrue(decision["risk_detected"])
        self.assertFalse(decision["requires_approval"])
        self.assertIn("accepts them by merging", proc.stderr)

    def test_a_verification_failure_still_blocks_in_advisory_mode(self):
        self.risk_branch()
        self.assertEqual(self.gate().returncode, 0)

        cfg = self.config()
        cfg["commands"]["test_full"] = "python3 -c 'import sys; sys.exit(9)'"
        self.config_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        proc = run([sys.executable, str(self.scripts / "run-role.py"), "test_full"],
                   cwd=self.dir)
        self.assertEqual(proc.returncode, 9, proc.stdout + proc.stderr)

    def test_strict_review_is_opt_in_and_blocks_without_an_approver(self):
        self.write_config(review="risk-triggered")
        self.risk_branch()
        proc = self.gate()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        decision = json.loads(proc.stdout)
        self.assertEqual(decision["verdict"], "blocked")
        self.assertTrue(decision["requires_approval"])
        self.assertEqual(decision["mode"], "risk-triggered")

    def test_human_review_mode_requires_an_approval_on_every_pr(self):
        self.write_config(review="human")
        self.commit("adopt human review")
        run(["git", "checkout", "-q", "-b", "feat/safe-change"], cwd=self.dir)
        (self.dir / "src" / "app.py").write_text("x = 2\n", encoding="utf-8")
        self.commit("change application code")
        proc = self.gate()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        decision = json.loads(proc.stdout)
        self.assertEqual(decision["verdict"], "blocked")
        self.assertEqual(decision["triggers"], [])
        self.assertTrue(decision["requires_approval"])

    def test_upgrade_preserves_strict_policy_and_migrates_only_when_asked(self):
        cfg = self.config()
        cfg["mode"]["merge"] = "auto"
        cfg["mode"]["review"] = "risk-triggered"
        cfg["review"]["approvers"] = ["reviewer"]
        self.config_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        self.commit("adopt strict review")

        upgraded = run([sys.executable, str(SCRIPTS / "install.py"),
                        "--target", str(self.dir), "--source", str(ROOT), "--upgrade"],
                       cwd=self.dir)
        self.assertEqual(upgraded.returncode, 0, upgraded.stdout + upgraded.stderr)
        preserved = self.config()
        self.assertEqual(preserved["mode"]["merge"], "auto")
        self.assertEqual(preserved["mode"]["review"], "risk-triggered")
        self.assertEqual(preserved["review"]["approvers"], ["reviewer"])

        migrated = run([sys.executable, str(SCRIPTS / "install.py"),
                        "--target", str(self.dir), "--source", str(ROOT),
                        "--upgrade", "--review-mode", "advisory"], cwd=self.dir)
        self.assertEqual(migrated.returncode, 0, migrated.stdout + migrated.stderr)
        final = self.config()
        self.assertEqual(final["mode"]["merge"], "auto")
        self.assertEqual(final["mode"]["review"], "advisory")
        self.assertEqual(final["review"]["approvers"], ["reviewer"])

    def test_upgrade_fills_a_missing_review_mode_with_the_solo_default(self):
        cfg = self.config()
        del cfg["mode"]["review"]
        self.config_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        self.commit("drop review mode")
        proc = run([sys.executable, str(SCRIPTS / "install.py"),
                    "--target", str(self.dir), "--source", str(ROOT), "--upgrade"],
                   cwd=self.dir)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.config()["mode"]["review"], "advisory")


if __name__ == "__main__":
    unittest.main()
