<!-- review-spec | v2.0.1 | 2026-10-24 | risk-triggered; CI-enforced; merge procedure -->
# Review — what the human actually reads

**Status:** Approved · **Owner:** Operator · **Consumer:** operator, verifier · **Normative for:** the human review gate

Everything else in this method automates evidence. This page is about the part that cannot be automated without turning review into rubber-stamping — and about how little of it there is by design.

The failure it prevents: generation becomes faster than reading, and the operator starts approving declarations instead of diffs. At that point the gates still pass and the quality signal is gone.

---

## 1. When a human is required

A human reads a diff when any of these is true — `risk-scan.py` computes it from the diff, CI fails the pull request, and the PR is labelled `needs-human`:

| Trigger | Why |
|---|---|
| Auth, authz, crypto | irreversible in a way tests rarely capture |
| Migrations, schema changes, data deletion | data loss is not recoverable by revert |
| Billing, payments, money | arithmetic bugs are expensive and quiet |
| Secrets, `.env` | a leaked credential cannot be un-leaked |
| Dependency manifests, lockfiles | supply-chain surface |
| CI configuration | the gate itself must not be weakened |
| Public API surface | breaks callers outside the repository |
| Any modified, renamed, deleted or newly skipped test | a weakened test is a silent reduction in the guarantee |
| `AGENTS.md`, `DECISIONS.md`, `workflow/` | the method must not be edited by the thing it governs |

Everything else merges on green.

### 1.1 How the trigger is enforced, and what "merge" means

`workflow/scripts/risk-scan.py --base <base> --fail-on-trigger` exits non-zero when any trigger fires. CI runs exactly that command on every pull request — `install.py` renders the lane — so a triggered PR cannot be green. The job also adds the `needs-human` label; the label is a convenience, the failing check is the enforcement. Labelling needs `pull-requests: write`, so it is best-effort on pull requests opened from forks.

The kit ships no merge runner. `mode.merge: auto` is a permission for the executing agent, not a daemon. The agent merges only when all of these hold:

1. every CI lane is green on the exact head being merged;
2. the verifier returned `pass` with evidence for each acceptance criterion;
3. `python3 workflow/scripts/risk-scan.py --base <base> --fail-on-trigger` exits 0 on that head;
4. `check-declaration.py` passes on the PR body.

Then merge with `gh pr merge --squash --delete-branch`. A condition that cannot be checked is not met. `mode.merge: human` stops after condition 4 and waits for the operator. A trigger under either mode stops before the merge.

## 2. What to read when triggered

1. **The diff first**, before the declaration. The declaration is a claim about the diff; reading it first anchors you to the claim.
2. **The acceptance table**, then find each piece of evidence in the diff. A criterion whose evidence you cannot locate is unverified.
3. **The test diff before the implementation diff.** What was weakened or removed is more informative than what was added.
4. **The risk-bearing hunks only.** Not every hunk; the ones that made the trigger fire.
5. **The declaration's numbers against `wp-stats.sh`.** If they were typed by hand, the declaration is invalid.
6. **One question you do not know the answer to.** If the answer is not in the diff or the docs, the package is under-documented.

## 3. Milestone audit

At each milestone the agent produces the one-page digest in `workflow/MEASUREMENT.md` §4. The operator:

- reads the page;
- samples two merged PRs — one with the largest diff, one chosen at random;
- checks the changelog lines against the decisions they cite;
- confirms the next milestone's scope.

Sampling is deliberate. Uniform per-package review was the cost this method removed; the trigger list is where attention is spent instead.

## 4. Never delegated

| Item | Why you |
|---|---|
| A change to the constraint ledger (Doc 1 §2) | It is the contract with the operator |
| A decision that reverses an adopted entry | Intent, not implementation |
| Security, money, data deletion, migration paths | Irreversible in a way tests rarely capture |
| A modified or deleted test, when it is not a pure rename | A weakened test is a silent reduction in the guarantee |
| A risk trigger you do not understand | If it is unclear, it is not approved |

## 5. Red flags

- A criterion marked passing whose evidence is a summary ("tests pass", "verified manually").
- A test file in the diff with no justification in §4 of the declaration.
- New interfaces with no caller.
- Scope items in the diff absent from §6 deviations.
- Statistics that do not match the diff.
- A verifier verdict of `pass` with an empty evidence column.
- The implementer's description used as the only source for what it did.
- A ledger entry edited to say something different from what was decided, with no `Supersedes`.

## 6. Time budget

Triggered review: 15–30 minutes, focused on the trigger. Milestone audit: 20–30 minutes. If triggered review routinely exceeds an hour, the trigger is too broad or the package too large — record it as a decision, do not silently absorb it.

## 7. What accepting means

Accepting means you can explain this change to someone else without asking an agent. If you cannot, read more, ask for a walkthrough in the PR, or reject — do not merge and hope.

## Revision history

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-10-24 | Initial human-review protocol (all diffs). |
| 2.0.0 | 2026-10-25 | Review is risk-triggered plus milestone sampling; non-delegable list narrowed; time budget scaled to triggers. |
| 2.0.1 | 2026-10-24 | States how CI enforces the trigger (`--fail-on-trigger`) and what `mode.merge: auto` authorises, since no merge runner ships. |
