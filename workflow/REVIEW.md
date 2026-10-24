<!-- review-spec | v2.1.0 | 2026-10-24 | review-aware gate; CI-enforced; merge procedure -->
# Review — what the human actually reads

**Status:** Approved · **Owner:** Operator · **Consumer:** operator, verifier · **Normative for:** the human review gate

Everything else in this method automates evidence. This page is about the part that cannot be automated without turning review into rubber-stamping — and about how little of it there is by design.

The failure it prevents: generation becomes faster than reading, and the operator starts approving declarations instead of diffs. At that point the gates still pass and the quality signal is gone.

---

## 1. When a human is required

A human reads a diff when any of these is true — `risk-scan.py` computes it from the diff, the CI risk gate blocks, and the gate records `risk-gate` on the head commit:

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

### 1.1 The gate: no risk, or an approval for the exact revision

`workflow/scripts/risk-gate.py` decides, and publishes the decision as a commit status:

| Risk trigger | Valid approval on the head commit | Verdict | `risk-gate` |
|---|---|---|---|
| none | irrelevant | `pass` | success |
| any | no | `blocked` | failure |
| any | yes | `approved` | success |

A valid approval is a review that:

1. is the reviewer's **latest** review on the pull request — a later `CHANGES_REQUESTED` or a dismissal voids it, a later plain comment does not;
2. is `APPROVED`;
3. carries `commit_id` equal to the head commit. A new push needs a new approval; an approval of an earlier revision never carries forward;
4. comes from someone other than the pull request author, and not from a bot;
5. comes from a login in `review.approvers`, or, when that list is empty, from a collaborator with `write`, `maintain` or `admin` permission.

One valid approval satisfies the risk gate. Branch protection's separate "require approvals" rules, if enabled, still apply on top.

CI runs the gate on two triggers: `pull_request` (opened, synchronize, reopened, ready_for_review) and `pull_request_review` (submitted, dismissed). A review approval therefore re-evaluates the gate **without a new commit** and flips the status. The status context is `review.status_context` (default `risk-gate`).

**Branch protection must require that status, and the `workflow gates` check.** The two lanes are independent: a green risk decision does not compensate for failed tests, and a green test run does not satisfy a risk trigger. The risk job's own check is not the gate: on a review event the run is attached to the pull request merge commit, and its check cannot clear a failure recorded against the head. The commit status is the only object that carries the decision for the revision under review. This is a one-time repository setting, listed in the install steps.

The gate executes only trusted code. CI checks out the repository's **protected default branch** and runs `risk-gate.py` and `risk-scan.py` from there, with `workflow/config.json` from the same checkout; the head is fetched as a git object and inspected as a diff against the pull request's target branch. The gate imports and executes nothing from the head, so a change to the gate scripts or to the risk triggers cannot alter its own verdict. Permissions are granted per job: the test lane runs pull request code with `contents: read` and without persisted checkout credentials.

The workflow definition is a separate surface. GitHub runs `pull_request` and `pull_request_review` workflow files from the merged pull request, so a change to `.github/workflows/**` still alters the job that publishes the status — it is a `ci` trigger and must be read as a privileged change. The outer trust boundary is write access to the repository: the gate enforces process against actors who are not attacking the CI system, and cannot police a writer who is.

Three consequences worth stating plainly:

- **Fork pull requests get a read-only `GITHUB_TOKEN`**, so the gate cannot publish a status there. The required status never appears and the PR stays blocked rather than merging unreviewed. The kit assumes branches in the same repository, which is how the agent workflow operates.
- **A dismissed or superseded approval blocks again on the next evaluation.** There is no "approved forever" state.
- **Authorization is as strong as the permission model.** A machine account with write access is indistinguishable from a human; name the humans in `review.approvers` when that distinction matters.

The kit ships no merge runner. `mode.merge: auto` is a permission for the executing agent, not a daemon. The agent merges only when all of these hold:

1. every required CI check is green on the exact head being merged;
2. the verifier returned `pass` with evidence for each acceptance criterion;
3. `gh pr checks` shows `risk-gate` passing on that head (or the statuses API reports `success` for the context);
4. `check-declaration.py` passes on the PR body.

Then merge with `gh pr merge --squash --delete-branch`. A condition that cannot be checked is not met. `mode.merge: human` stops after condition 4 and waits for the operator. A blocked gate under either mode stops before the merge.

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
| 2.1.0 | 2026-10-24 | The gate is review-aware: an authorized approval of the exact head commit flips the `risk-gate` status; branch protection must require it. |
