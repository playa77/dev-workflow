<!-- state-spec | v2.2.0 | 2026-10-25 | intake state; ledger on resume; risk verdict includes advisory -->
# State — intake, checkpoints, resume

**Status:** Approved · **Owner:** Operator · **Consumer:** executor writes, verifier and operator read · **Normative for:** `intake.json`, `progress.md`, `state.json`

The checkpoint exists so an interrupted package can be resumed by a session with no conversation history. It is not a status report and not a changelog.

| File | Format | Edited by | Holds |
|---|---|---|---|
| `workflow/state/intake.json` | JSON | agent, during intake | topic coverage, defaults, deferrals |
| `WP-nnn.progress.md` | Markdown | agent, at milestones | narrative: why, ruled out, next step |
| `WP-nnn.state.json` | JSON | agent, on transitions | status, per-criterion passes, evidence, decisions |
| `DECISIONS.md` | Markdown | agent, at decision time | binding decisions and rejected options |
| `CHANGELOG.md` | Markdown | `close-wp.py` | user-visible changes |

Markdown invites rewriting; JSON invites editing one field. Put each kind of information where it is least likely to be corrupted.

---

## 1. `intake.json`

```json
{
  "project": "entity-resolution",
  "updated": "2026-10-25T10:12:00Z",
  "questions_asked": 7,
  "topics": {
    "purpose":     {"status": "answered", "answer": "Resolve supplier records across systems", "evidence": "brief"},
    "users":       {"status": "answered_by_repo", "evidence": "README.md:12"},
    "scope":       {"status": "answered", "answer": "SMB suppliers only"},
    "data":        {"status": "defaulted", "default": "Postgres, 30-day retention",
                    "blast_radius": "local", "revisit_if": "retention becomes a compliance requirement"},
    "integrations":{"status": "answered", "answer": "SAP export, nightly"},
    "security":    {"status": "answered", "answer": "Internal only, SSO"},
    "infrastructure": {"status": "answered_by_repo", "evidence": "Dockerfile"},
    "performance": {"status": "defaulted", "default": "p95 < 300 ms at 50 rps",
                    "blast_radius": "architectural", "revisit_if": "load test fails"},
    "budget":      {"status": "answered", "answer": "None"},
    "technology":  {"status": "answered", "answer": "Python, Postgres"},
    "operations":  {"status": "answered", "answer": "Team runs it, Grafana"},
    "non_goals":   {"status": "answered", "answer": "No fuzzy matching"}
  },
  "open": 0
}
```

Statuses: `answered`, `answered_by_repo`, `defaulted`, `deferred`, `open`.

Rules:

- `answered_by_repo` requires an `evidence` path; the agent must have read it.
- `defaulted` requires `default`, `blast_radius` (`local` or `architectural`) and `revisit_if`.
- `deferred` requires `resolved_by` (a WP id) and the same three fields.
- `open` blocks the spec pass. `check-intake.py` enforces all of the above.
- Questions asked beyond twelve fail the check; if a genuine gap remains, record it as `deferred` with the WP that resolves it.

## 2. `progress.md`

| Field | Rule |
|---|---|
| WP id and title | Must match the brief |
| Branch | Exact branch name |
| Last commit | Short SHA |
| Working tree | `clean`, or the uncommitted paths and why they matter |
| Status | `in-progress` \| `blocked` \| `complete` |
| Acceptance | One line per criterion, with the evidence command and its result |
| Verification | Two fields: **command** and **last run** (timestamp, result) |
| Decisions | Decisions taken in this package, with their reasons; link the ledger ID if one was added |
| Ruled out | Options rejected here and why. Moves to the ledger when the package closes if it meets the entry threshold |
| Failures | Known failures with the exact error |
| Next step | One concrete action |

Rules: update at milestones and before an interruption; a criterion is checked only when its evidence line is filled; `Next step` is singular; no unfilled placeholders.

## 3. `state.json`

```json
{
  "wp": "WP-012",
  "branch": "feat/wp-012-entity-resolution",
  "base": "main",
  "status": "in-progress",
  "updated": "2026-10-25T14:02:00Z",
  "revision": "a1b2c3d",
  "user_visible": true,
  "decisions": ["D-021"],
  "criteria": [
    {"id": 1, "passes": true, "evidence": "pytest tests/resolve_test.py::test_identical -q (41 passed)"},
    {"id": 2, "passes": false, "evidence": null}
  ],
  "verification": {"command": "make test-affected", "last_run": "2026-10-25T14:02:00Z", "result": "pass"},
  "integrity": {"snapshot": "workflow/state/test-baseline.json", "verify": "pass", "stash_check": "not-applicable"},
  "risk": {"mode": "advisory", "verdict": "pass", "requires_human": false, "triggers": []},
  "blockers": []
}
```

| Field | Rule |
|---|---|
| `status` | `in-progress` \| `blocked` \| `verified` \| `delivered` |
| `user_visible` | Drives the changelog requirement; `true` means a line is mandatory |
| `decisions` | IDs added or relied on by this package; `check-changelog.py` resolves them |
| `criteria[].passes` | True only with non-null `evidence` |
| `verification.result` | `pass` \| `fail` \| `not-run` |
| `risk` | Output of `risk-gate.py` at close: `mode`, `verdict` (`pass` / `advisory` / `approved` / `blocked`) and the reported findings |
| `blockers` | Each names the blocker and what would unblock it |

Invariants: every brief criterion appears with the same id; no `passes: true` with null evidence; `verified` implies all pass and verification `pass`; `revision` reachable from `branch`; `user_visible` is a boolean and `decisions` is a list of valid ids; `user_visible` true implies a changelog line exists after close. `check-state.py` enforces these.

## 4. Resume protocol

1. `git status` and `git log --oneline -5` — establish the actual tree.
2. Read the index at the top of `DECISIONS.md`. Status is authoritative there; do not infer it from an entry.
3. Read `progress.md`. Compare its branch and last commit with step 1. **If they disagree, stop and reconcile.**
4. Read `state.json`. Criteria with `passes: true` and evidence are presumed verified; re-run the evidence command only if the tree differs from the recorded revision.
5. Read `Ruled out` before proposing an approach.
6. Continue from `Next step`. Do not restate the plan, re-derive the architecture, or begin another package.

## 5. What never goes in a checkpoint

- Decisions of record — `DECISIONS.md`.
- Specification text — cite Doc 2 by section.
- Delivery statistics — generated at close by `wp-stats.sh`.
- Conversation summaries. If a fact matters, write the fact.

## Revision history

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-10-24 | Initial. |
| 2.0.0 | 2026-10-25 | Adds `intake.json`, `user_visible`, `decisions`, risk block; resume reads the ledger index. |
| 2.2.0 | 2026-10-25 | The risk block records the review mode and the advisory verdict. |
