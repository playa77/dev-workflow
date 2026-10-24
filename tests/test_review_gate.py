"""Tests for the review-aware risk gate, role resolution and CI policy checks."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workflow" / "scripts"
HEAD = "a" * 40
OLD = "b" * 40


def load_gate():
    spec = importlib.util.spec_from_file_location("risk_gate", SCRIPTS / "risk-gate.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = load_gate()


def review(login, state="APPROVED", commit=HEAD, at="2026-10-24T10:00:00Z",
           user_type="User"):
    return {
        "user": {"login": login, "type": user_type},
        "state": state,
        "commit_id": commit,
        "submitted_at": at,
    }


RISK = {"requires_human": True, "triggers": [{"class": "security", "path": "src/auth/x.py",
                                              "reason": "path matches a security trigger"}]}
SAFE = {"requires_human": False, "triggers": []}


class DecisionTest(unittest.TestCase):
    def decide(self, result, reviews, author="agent", allowed=("alice",)):
        return GATE.decide(result, reviews, HEAD, author, lambda user: user in allowed)

    def test_no_risk_passes_without_an_approval(self):
        decision = self.decide(SAFE, None)
        self.assertEqual(decision["verdict"], "pass")

    def test_risk_without_reviews_blocks(self):
        decision = self.decide(RISK, [])
        self.assertEqual(decision["verdict"], "blocked")
        self.assertEqual(decision["approvals"], [])

    def test_risk_without_pr_context_blocks(self):
        decision = self.decide(RISK, None)
        self.assertEqual(decision["verdict"], "blocked")

    def test_approval_on_head_passes(self):
        decision = self.decide(RISK, [review("alice")])
        self.assertEqual(decision["verdict"], "approved")
        self.assertEqual([a["user"] for a in decision["approvals"]], ["alice"])

    def test_approval_on_an_earlier_commit_blocks(self):
        decision = self.decide(RISK, [review("alice", commit=OLD)])
        self.assertEqual(decision["verdict"], "blocked")

    def test_author_cannot_approve_their_own_pr(self):
        decision = self.decide(RISK, [review("agent")], author="agent", allowed=("agent", "alice"))
        self.assertEqual(decision["verdict"], "blocked")

    def test_unauthorized_reviewer_blocks(self):
        decision = self.decide(RISK, [review("mallory")])
        self.assertEqual(decision["verdict"], "blocked")

    def test_changes_requested_after_approval_blocks(self):
        reviews = [review("alice", at="2026-10-24T10:00:00Z"),
                   review("alice", state="CHANGES_REQUESTED", at="2026-10-24T11:00:00Z")]
        decision = self.decide(RISK, reviews)
        self.assertEqual(decision["verdict"], "blocked")

    def test_dismissed_approval_blocks(self):
        reviews = [review("alice", at="2026-10-24T10:00:00Z"),
                   review("alice", state="DISMISSED", at="2026-10-24T11:00:00Z")]
        decision = self.decide(RISK, reviews)
        self.assertEqual(decision["verdict"], "blocked")

    def test_comment_after_approval_does_not_revoke_it(self):
        reviews = [review("alice", at="2026-10-24T10:00:00Z"),
                   review("alice", state="COMMENTED", at="2026-10-24T11:00:00Z")]
        decision = self.decide(RISK, reviews)
        self.assertEqual(decision["verdict"], "approved")

    def test_bot_approval_blocks(self):
        decision = self.decide(RISK, [review("dependabot[bot]", user_type="Bot")],
                               allowed=("dependabot[bot]",))
        self.assertEqual(decision["verdict"], "blocked")

    def test_two_approvers_yield_two_entries(self):
        decision = self.decide(RISK, [review("alice"), review("bob")],
                               allowed=("alice", "bob"))
        self.assertEqual([a["user"] for a in decision["approvals"]], ["alice", "bob"])


class FakeGitHub(BaseHTTPRequestHandler):
    reviews: list = []
    permission = "admin"
    requests: list = []
    head = HEAD

    def do_GET(self):  # noqa: N802 - http.server API
        FakeGitHub.requests.append(("GET", self.path, dict(self.headers)))
        if "/reviews" in self.path:
            payload = FakeGitHub.reviews
        elif "/permission" in self.path:
            payload = {"permission": FakeGitHub.permission}
        else:
            self.send_error(404)
            return
        self.reply(200, payload)

    def do_POST(self):  # noqa: N802 - http.server API
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        FakeGitHub.requests.append(("POST", self.path, dict(self.headers), body))
        self.reply(201, {"state": body.get("state")})

    def reply(self, code, payload):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):  # noqa: A002 - http.server API
        pass


class RiskGateHttpTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.dir, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=self.dir, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.dir, check=True)
        (self.dir / "src" / "auth").mkdir(parents=True)
        (self.dir / "src" / "auth" / "login.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.dir, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=self.dir, check=True)
        self.base_ref = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=self.dir,
                                       capture_output=True, text=True, check=True).stdout.strip()
        subprocess.run(["git", "checkout", "-q", "-b", "pr"], cwd=self.dir, check=True)
        (self.dir / "src" / "auth" / "login.py").write_text("x = 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.dir, check=True)
        subprocess.run(["git", "commit", "-qm", "change"], cwd=self.dir, check=True)
        self.head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.dir,
                                   capture_output=True, text=True, check=True).stdout.strip()
        # The gate runs from the base commit; the pull request head is data.
        subprocess.run(["git", "checkout", "-q", self.base_ref], cwd=self.dir, check=True)

        FakeGitHub.requests = []
        FakeGitHub.head = self.head
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeGitHub)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def run_gate(self):
        env = dict(os.environ, GITHUB_TOKEN="test-token", GITHUB_API_URL=self.base,
                   PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "risk-gate.py"), "--base", self.base_ref,
             "--root", str(self.dir), "--head", self.head, "--pr", "7",
             "--repo", "owner/repo", "--author", "agent", "--publish", "--json"],
            capture_output=True, text=True, env=env,
        )

    def status_post(self):
        return [r for r in FakeGitHub.requests if r[0] == "POST"]

    def test_approval_on_head_publishes_a_success_status(self):
        FakeGitHub.reviews = [review("alice", commit=self.head)]
        proc = self.run_gate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        decision = json.loads(proc.stdout)
        self.assertEqual(decision["verdict"], "approved")
        posts = self.status_post()
        self.assertEqual(len(posts), 1, FakeGitHub.requests)
        self.assertEqual(posts[0][1], f"/repos/owner/repo/statuses/{self.head}")
        self.assertEqual(posts[0][3]["state"], "success")
        self.assertEqual(posts[0][3]["context"], "risk-gate")
        gets = [r for r in FakeGitHub.requests if r[0] == "GET"]
        self.assertTrue(all(r[2].get("User-Agent") == "workflow-kit/2.1 risk-gate" for r in gets),
                        [r[2].get("User-Agent") for r in gets])

    def test_no_approval_publishes_a_failure_status(self):
        FakeGitHub.reviews = []
        proc = self.run_gate()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "blocked")
        posts = self.status_post()
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0][3]["state"], "failure")

    def test_read_only_collaborator_is_not_authorized(self):
        FakeGitHub.permission = "read"
        FakeGitHub.reviews = [review("alice", commit=self.head)]
        proc = self.run_gate()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["verdict"], "blocked")


class RunRoleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.config = self.dir / "config.json"
        self.config.write_text(json.dumps({"commands": {
            "ok": "python3 -c 'import sys; sys.exit(0)'",
            "bad": "python3 -c 'import sys; sys.exit(3)'",
            "empty": "   ",
        }}), encoding="utf-8")
        self.zero = self.dir / "zero.json"
        self.zero.write_text(json.dumps({"commands": {
            "test_full": "python3 -c \"print('NO TESTS RAN')\"",
        }}), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_role(self, role, config=None):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "run-role.py"), role,
             "--config", str(config or self.config)],
            capture_output=True, text=True, cwd=self.dir,
        )

    def test_configured_role_runs(self):
        self.assertEqual(self.run_role("ok").returncode, 0)

    def test_failing_command_propagates_its_exit_code(self):
        self.assertEqual(self.run_role("bad").returncode, 3)

    def test_empty_role_fails_instead_of_skipping(self):
        proc = self.run_role("empty")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no command configured", proc.stderr)

    def test_missing_role_fails_instead_of_skipping(self):
        self.assertEqual(self.run_role("test_full").returncode, 1)

    def test_full_suite_running_zero_tests_fails(self):
        proc = self.run_role("test_full", config=self.zero)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("ran zero tests", proc.stderr)


class DoctorCiPolicyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.dir, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=self.dir, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.dir, check=True)
        (self.dir / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
        (self.dir / "tests").mkdir()
        (self.dir / "tests" / "test_x.py").write_text(
            "def test_x():\n    assert True\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.dir, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.dir, check=True)
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "install.py"), "--target", str(self.dir),
             "--source", str(ROOT)], capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def tearDown(self):
        self.tmp.cleanup()

    def doctor(self):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "doctor.py"), "--root", str(self.dir)],
            capture_output=True, text=True,
        )

    def test_fresh_install_passes(self):
        proc = self.doctor()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_workflow_without_the_gate_fails_doctor(self):
        ci = self.dir / ".github" / "workflows" / "wp.yml"
        ci.write_text(ci.read_text(encoding="utf-8").replace("risk-gate.py", "risk-scan.py"),
                      encoding="utf-8")
        proc = self.doctor()
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("risk-gate.py", proc.stdout)

    def test_two_workflow_files_fail_doctor(self):
        ci = self.dir / ".github" / "workflows" / "wp.yml"
        (ci.parent / "wp-workflow.yml").write_text(ci.read_text(encoding="utf-8"),
                                                   encoding="utf-8")
        proc = self.doctor()
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("race", proc.stdout)

    def test_pr_head_checkout_fails_doctor(self):
        ci = self.dir / ".github" / "workflows" / "wp.yml"
        text = ci.read_text(encoding="utf-8")
        mutated = text.replace("ref: ${{ github.event.repository.default_branch }}",
                               "ref: ${{ github.event.pull_request.head.sha }}")
        self.assertNotEqual(mutated, text)
        ci.write_text(mutated, encoding="utf-8")
        proc = self.doctor()
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("default branch", proc.stdout)

    def test_workflow_level_status_write_fails_doctor(self):
        ci = self.dir / ".github" / "workflows" / "wp.yml"
        ci.write_text("permissions:\n  statuses: write\n" + ci.read_text(encoding="utf-8"),
                      encoding="utf-8")
        proc = self.doctor()
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("every job", proc.stdout)


if __name__ == "__main__":
    unittest.main()
