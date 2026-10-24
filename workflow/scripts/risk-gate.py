#!/usr/bin/env python3
"""Decide whether a pull request may merge, given risk triggers and reviews.

Usage:
    python3 workflow/scripts/risk-gate.py --base origin/main [--head SHA]
                                         [--pr N] [--repo owner/name]
                                         [--author LOGIN] [--publish] [--json]

Verdicts:
    pass      no risk trigger; merge may proceed
    approved  risk triggers, and an authorized human approved the head commit
    blocked   risk triggers, and no valid approval on the head commit
    error     the scan or the GitHub API failed

Exit codes: 0 pass/approved, 1 blocked, 2 error.

A valid approval is the reviewer's latest review on the pull request, is
APPROVED, carries `commit_id` equal to the head commit, comes from someone
other than the PR author and not a bot, and comes from either
`review.approvers` in workflow/config.json or, when that list is empty, a
collaborator with write, maintain or admin permission.

With --publish the verdict is also written as a commit status on the head
commit, context `review.status_context` (default `risk-gate`). CI runs this on
pull_request and pull_request_review events, so an approval re-evaluates
without a new commit; branch protection must require that status.

Trust boundary: run this script from the repository's protected default branch,
never from the pull request. `--head` names the commit to inspect; the scan
reads it as a git diff and no pull request file is imported or executed. The
workflow that publishes the status therefore runs only trusted code.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "workflow-kit/2.1 risk-gate"
BOT_RE = re.compile(r"\[bot\]$", re.I)
REVIEW_STATES = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}
WRITE_PERMISSIONS = {"admin", "maintain", "write"}


def load_settings(root: Path) -> tuple[list[str], str]:
    path = root / "workflow" / "config.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    review = data.get("review") if isinstance(data.get("review"), dict) else {}
    approvers = [str(a).strip() for a in (review.get("approvers") or []) if str(a).strip()]
    context = str(review.get("status_context") or "risk-gate").strip() or "risk-gate"
    return approvers, context


def scan(root: Path, base: str, head: str) -> dict:
    script = Path(__file__).with_name("risk-scan.py")
    proc = subprocess.run(
        [sys.executable, str(script), "--base", base, "--head", head,
         "--root", str(root), "--fail-on-trigger"],
        capture_output=True, text=True,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr.strip() or f"risk scan exited {proc.returncode}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"risk scan output is not JSON: {exc}") from exc


def valid_approvals(reviews: list[dict], head: str, author: str,
                    authorized) -> list[dict]:
    """Return approvals that are valid for the exact head commit."""
    latest: dict[str, dict] = {}
    for review in reviews:
        state = str(review.get("state") or "").upper()
        if state not in REVIEW_STATES:
            continue
        login = str(((review.get("user") or {}).get("login")) or "")
        if not login:
            continue
        previous = latest.get(login)
        if previous is not None and str(review.get("submitted_at") or "") < str(
                previous.get("submitted_at") or ""):
            continue
        latest[login] = review

    valid: list[dict] = []
    for login, review in latest.items():
        if str(review.get("state")).upper() != "APPROVED":
            continue
        if login.lower() == author.lower():
            continue
        if (review.get("user") or {}).get("type") == "Bot" or BOT_RE.search(login):
            continue
        if review.get("commit_id") != head:
            continue
        if not authorized(login):
            continue
        valid.append({
            "user": login,
            "commit_id": review.get("commit_id"),
            "submitted_at": review.get("submitted_at"),
        })
    return sorted(valid, key=lambda item: item["user"].lower())


def decide(result: dict, reviews: list[dict] | None, head: str, author: str,
           authorized) -> dict:
    triggers = result.get("triggers") or []
    requires_human = bool(result.get("requires_human") or triggers)
    decision = {
        "verdict": "pass",
        "head": head,
        "requires_human": requires_human,
        "triggers": triggers,
        "approvals": [],
        "reasons": ["no risk trigger"],
    }
    if not requires_human:
        return decision

    approvals = valid_approvals(reviews or [], head, author, authorized) if reviews is not None else []
    if approvals:
        decision.update(verdict="approved", approvals=approvals,
                        reasons=[f"approved by {', '.join(a['user'] for a in approvals)}"])
        return decision

    if reviews is None:
        reason = "risk detected; no pull-request context to resolve reviews"
    else:
        reason = f"risk detected; no valid approval on {head[:12]}"
    decision.update(verdict="blocked", reasons=[reason])
    return decision


def api_base() -> str:
    return os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")


def token() -> str:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


def _request(url: str, tok: str, method: str = "GET", payload: dict | None = None):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {tok}",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        return urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"{method} {url} -> {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc.reason}") from exc


def api_get(path: str, tok: str, pages: int = 5):
    url = api_base() + path
    collected: list[dict] = []
    for _ in range(pages):
        with _request(url, tok) as response:
            body = response.read().decode("utf-8")
            link = response.headers.get("Link", "")
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"GET {url} returned non-JSON: {exc}") from exc
        if isinstance(data, list):
            collected.extend(data)
        else:
            return data
        match = re.search(r'<([^>]+)>;\s*rel="next"', link)
        if not match:
            break
        url = match.group(1)
    return collected


def fetch_reviews(repo: str, pr: str, tok: str) -> list[dict]:
    data = api_get(f"/repos/{repo}/pulls/{urllib.parse.quote(str(pr))}/reviews?per_page=100", tok)
    return data if isinstance(data, list) else []


def permission(repo: str, login: str, tok: str) -> str:
    data = api_get(f"/repos/{repo}/collaborators/{urllib.parse.quote(login)}/permission", tok)
    if not isinstance(data, dict):
        return ""
    return str(data.get("permission") or "").lower()


def authorizer(approvers: list[str], repo: str, tok: str):
    allowed = {name.lower() for name in approvers}
    cache: dict[str, str] = {}

    def authorized(login: str) -> bool:
        if allowed:
            return login.lower() in allowed
        if login not in cache:
            cache[login] = permission(repo, login, tok) if repo and tok else ""
        return cache[login] in WRITE_PERMISSIONS

    return authorized


def publish(repo: str, sha: str, decision: dict, context: str, tok: str) -> None:
    state = "success" if decision["verdict"] in {"pass", "approved"} else "failure"
    if decision["verdict"] == "pass":
        description = "no risk trigger"
    elif decision["verdict"] == "approved":
        description = "approved by " + ", ".join(a["user"] for a in decision["approvals"])
    else:
        description = (f"{len(decision['triggers'])} risk trigger(s); "
                       f"approval required for {sha[:12]}")
    payload = {"state": state, "context": context, "description": description[:140]}
    target = os.environ.get("RUN_URL", "").strip()
    if target:
        payload["target_url"] = target
    with _request(f"{api_base()}/repos/{repo}/statuses/{sha}", tok,
                  method="POST", payload=payload) as response:
        response.read()


def git_head(root: Path) -> str:
    proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git rev-parse HEAD failed")
    return proc.stdout.strip()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--head", default="")
    ap.add_argument("--pr", default="")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    ap.add_argument("--author", default="")
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--json", action="store_true",
                    help="accepted for symmetry; JSON is always printed")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    try:
        head = args.head.strip() or git_head(root)
        approvers, context = load_settings(root)
        result = scan(root, args.base, head)
        tok = token()
        reviews = None
        if args.pr and args.repo and tok:
            reviews = fetch_reviews(args.repo, args.pr, tok)
        decision = decide(result, reviews, head, args.author, authorizer(approvers, args.repo, tok))

        if args.publish:
            if not (args.repo and tok and head):
                raise RuntimeError("--publish needs a repository, a token and a head commit")
            publish(args.repo, head, decision, context, tok)
    except RuntimeError as exc:
        print(f"risk-gate: error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(decision, indent=2))
    if decision["verdict"] == "blocked":
        print(f"risk-gate: blocked — {decision['reasons'][0]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
