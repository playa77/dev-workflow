<!-- verification-spec | v2.0.0 | 2026-10-25 | transitions delegated; risk triggers; structural gates -->
# Verification — mechanisms, gates and proof

**Status:** Approved · **Owner:** Operator · **Consumer:** executor, verifier, CI · **Normative for:** how verification is performed and what counts as evidence

`AGENTS.md` §4–5 states the rules. This document states the mechanisms. A rule with no mechanism is a preference.

---

## 1. What counts as evidence

| Claim | Not evidence | Evidence |
|---|---|---|
| "Tests pass" | a sentence in the report | command, timestamp, runner summary line, exit code |
| "The feature works" | "implemented as specified" | an acceptance criterion mapped to a test or a recorded check |
| "No regressions" | "ran the suite" | baseline count vs current count, plus failing-before/passing-after |
| "Tests are meaningful" | coverage percentage | mutation result or stash-check on changed lines |
| "Scope was respected" | the file list in the description | machine diff stats by category |
| "The package is complete" | every child commit merged | every criterion with its own evidence row |

A verification report is generated, not narrated. The verifier reads it; the operator reads the diff when a trigger fires.

## 2. Test integrity

**A test may not hand-build the state the code under test is supposed to produce.** Pre-existing state is established by calling the production path.

| # | Mechanism | Catches | Runs |
|---|---|---|---|
| 1 | Test-file hash baseline | a test quietly weakened or deleted | every PR |
| 2 | Test-count and skip delta | a test removed, renamed away or newly skipped | every PR |
| 3 | No-assert lint | a test that calls the function and checks nothing | every PR |
| 4 | Diff coverage | changed lines no test executes | every PR |
| 5 | Scoped mutation | assertions that cannot fail | pre-merge |
| 6 | Stash-check (bug fixes) | a regression test that passes without the fix | pre-merge |
| 7 | Clean-checkout run | a test depending on `conftest`, runner config or local state | pre-merge |

1–4 and 7 are fail-closed. 5 and 6 are fail-closed for bug fixes and advisory for features: a mutation score is a policy number, not a proof.

### 2.1 Red for the right reason

- **Syntactic red** — the test failed to execute. Not evidence.
- **Semantic red** — the test executed and the assertion failed. Evidence.

When a test is written for a new behaviour, record the expected failure message. A red run whose failure text does not match is syntactic red.

### 2.2 Stash-check

1. Stash the fix, keeping the new tests. 2. Run: it must fail, for the expected reason. 3. Restore. 4. Run: it must pass.

Green in both states means the test proves nothing. Refactors invert: keep the tests, stash the refactor, and the tests must pass on the old code.

**Bytecode and build caches must be cleared first.** CPython validates a `.pyc` by source mtime *and* size; a one-character fix restored within the same second leaves a stale `.pyc` that looks valid. The script deletes `__pycache__` and runs with `PYTHONDONTWRITEBYTECODE=1`.

### 2.3 Mutation scope

Scope mutations to changed lines covered by tests, with a fixed time budget; full set nightly. A timed-out scoped run is **inconclusive**, not passing.

## 3. Declaration guards

`workflow/templates/PR.md` is the delivery declaration. CI checks it mechanically:

| Guard | Failure |
|---|---|
| Declaration present and parseable | missing section = fail |
| Every acceptance criterion has an evidence row | unmapped criterion = fail |
| Evidence is fresh (this branch, after the last code commit) | stale evidence = fail |
| Required lanes ran on the exact candidate revision | skipped lane = fail |
| Category stats were generated, not written by hand | hand-written stats = fail |
| Test count did not decrease | decrease = fail unless justified |
| Every cited decision exists | unknown `D-nnn` = fail |

These establish that the declaration is complete and the execution happened. They cannot establish semantic completeness; that is the verifier's job.

## 4. Risk triggers

`workflow/scripts/risk-scan.py --base <ref>` classifies the diff and exits `requires_human: true` for:

- auth, authz, crypto paths;
- migrations, schema changes, data deletion;
- billing, payments, money;
- secrets and `.env` files;
- dependency manifests and lockfiles;
- CI configuration;
- public API surface changes;
- any modified, renamed, deleted or newly skipped test;
- any change to `AGENTS.md`, `DECISIONS.md` or `workflow/`.

A trigger blocks automatic merge and requests review under `workflow/REVIEW.md`. A trigger list that fires constantly means the repository should set `mode.merge: human` by evidence, not by policy.

## 5. Proportional validation

| Stage | What runs |
|---|---|
| Development | `TEST_AFFECTED`, `LINT`, integrity 1–4 |
| Pre-merge candidate | one authoritative `TEST_FULL` on the exact head, integrity 5–7, declaration guards, risk scan |
| Main, routine push | `TEST_SMOKE` (bounded) |
| Documentation-only change | link and heading check |
| Release | full manual checks, exact candidate evidence, fail-closed status |

Independent lanes run on separate runners. A required but unconfigured lane fails.

## 6. Exceptions

An exception requires: a named mechanism, a reason, a compensating control, and a ledger entry when it changes a decision.

Valid: "Mutation is skipped for the generated client (`src/gen/**`), compensated by pinning the generator version and diffing its output."
Invalid: "Mutation is slow on this repo."

The **agent** may grant an exception that names all three and records it in the declaration. Only exceptions on a risk-triggered surface (security, money, data deletion, migrations) require the operator. This is the delegation that makes the rest of the method run without a human queue.

## 7. Adapters

`check-test-integrity.sh` autodetects the runner from `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml` and `Makefile`. Recognised:

| Stack | Test paths | Summary parsed |
|---|---|---|
| Python | `tests/**`, `test_*.py`, `*_test.py` | `N passed` |
| JS/TS | `**/*.test.*`, `**/*.spec.*`, `__tests__/**` | `Tests N passed` |
| Go | `*_test.go` | count of `--- PASS` |
| Rust | `tests/**`, `#[cfg(test)]` | `N passed` |

Overrides: `TEST_COUNT_CMD`, `TEST_PATHS`, `TEST_CMD`. An unrecognised stack reports **not configured** and fails closed at pre-merge. `scripts/`, `workflow/`, `docs/`, `.github/`, `vendor/` and `node_modules/` are never treated as test locations.

## 8. Structural gates

| Script | Checks | Limits |
|---|---|---|
| `check-intake.py` | coverage statuses, defaults with blast radius, deferrals with a resolving WP, `open == 0` | cannot judge whether an answer is true |
| `check-wp.py` | brief fields, 3–8 criteria, verification rows, decisions, user-visible effect | cannot judge whether a criterion is testable in substance |
| `check-spec.py` | required sections, seam table, every module in a call trace, no placeholders | structural only; not semantics |
| `check-roadmap.py` | DAG acyclic, dependencies resolve, coverage matrix complete | cannot judge WP sizing |
| `check-ledger.py` | IDs, fields, supersession consistency, changelog correlation, index freshness | cannot judge whether a decision was wise |
| `check-changelog.py` | structure, citations, version agreement | cannot judge whether an entry is meaningful |

The residual risk — a well-formed artifact that is wrong — is the verifier's and, at milestones, the operator's.

## Revision history

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-10-24 | Initial. |
| 2.0.0 | 2026-10-25 | Exceptions delegated to the agent except on risk-triggered surfaces; adds risk triggers and structural gates; paths updated. |
