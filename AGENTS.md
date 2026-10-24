<!-- agents-constitution | v2.1.0 | 2026-10-24 | review-aware risk gate; ledger and changelog; workflow/ layout -->
# AGENTS.md — Operating Constitution

**Status:** Approved · **Owner:** Operator · **Consumer:** every coding agent, every session · **Normative for:** delivery unit, execution policy, prohibitions

This is the only instruction file every agent is guaranteed to read. Rules live here. Process, mechanisms and schemas are referenced in §10. If a rule is neither here nor in a referenced document, it is not a rule.

---

## 1. Delivery unit

- **One full work package per branch and PR.** Steps, commits and child changes are internal.
- Do not invent smaller packages to fit a turn, a context window or a session limit.
- Continue the same work package after interruption. A new session is not a new package.
- Partial delivery requires an explicit operator instruction. Absent it, an incomplete package is a **reported blocker**, not a delivery.
- Never present a child as the completed parent.

## 2. Completion

- Define completion **before** coding: WP, acceptance checklist, prerequisites, branch.
- Map delivered behaviour to that checklist. Preserve incomplete obligations; name concrete blockers.
- If the package boundary is impractical, flag it **before starting**.

## 3. Execution and resources

- Four budgets: context, reasoning, execution, usage. An estimate is not an authoritative limit.
- Do not reduce scope or skip verification because of a speculative budget.
- Do not change model, reasoning effort or validation depth mid-package.
- If a limit is genuinely reached: checkpoint, report, and state the remaining step. Do not fake completion.

## 4. Verification

- Untested implementation does not satisfy a package. **Evidence is command output, not assertion.**
- Tests may not hand-build state the production path is supposed to produce.
- Do not edit, delete, weaken, rename or skip an existing test without flagging it in the declaration and justifying it.
- Affected tests during development; one authoritative full run on the exact head before merge.

## 5. Test economics

- New verification needs a reason: a distinct behaviour, a regression, or a named failure.
- Shared invariants live in shared coverage. No quotas, no copied suites, no cumulative pass counts as a delivery target.

## 6. State and decisions

- Read the index at the top of `DECISIONS.md` before proposing an approach. `adopted` binds. `rejected` means do not re-propose it unless its **Revisit if** is now true. `superseded` is history — follow the row.
- Record a decision when it constrains work beyond this package, costs more than a day to reverse, or someone will ask "why" within six months. Otherwise it belongs in the checkpoint.
- Maintain `progress.md` and `state.json` per `workflow/STATE.md`. Record branch and last commit; on resume, compare them with the working tree before following the next step.

## 7. Reporting

- Lead with completed criteria and remaining blockers.
- Separate implementation | tests | fixtures | generated | docs; additions/deletions from net growth; new tests from cumulative passes; validation latency from implementation effort.
- Never present a child commit as progress on the parent, or a cumulative pass count as delivery evidence.

## 8. Review and delivery

- Machine gates first, fresh-context verifier second, risk-triggered human review third.
- Merge per `workflow/config.json` mode. A risk trigger requires an authorized human's approval of the exact head commit, recorded as the `risk-gate` status; a blocked gate is not mergeable.
- A skipped required lane is a failed lane.
- Write the changelog line and any decision entries at close. Do not start the next WP.

## 9. Prohibited

- Editing, disabling or weakening a test to obtain green.
- Adding a dependency without a stated reason.
- Inventing a service, database, queue or integration the spec does not define.
- Marking a WP complete when any acceptance criterion is unverified.
- Removing a human gate without replacing it with a check.
- Starting the next work package.
- Rewriting these rules. Propose an amendment in the PR.

## 10. Reference map

| Need | Document |
|---|---|
| Install, bootstrap, state machine | `workflow/START.md` |
| Phases, gates, roles, artifact authority | `workflow/WORKFLOW.md` |
| Verification mechanisms and CI guards | `workflow/VERIFICATION.md` |
| Checkpoint schemas and resume | `workflow/STATE.md` |
| Decisions of record | `DECISIONS.md` |
| What shipped | `CHANGELOG.md` |
| Review protocol | `workflow/REVIEW.md` |
| Telemetry, calibration, retro | `workflow/MEASUREMENT.md` |
| Phase prompts | `workflow/prompts/` |
| WP brief, declaration, digest, checkpoints | `workflow/templates/` |
| Commands and modes | `workflow/config.json` |

## Revision history

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-10-24 | Initial constitution. |
| 2.0.0 | 2026-10-25 | Enforcement is machine-checked or agent-verified; "human-gated" removed. Adds the decision ledger and changelog. Updates paths to `workflow/`. |
| 2.1.0 | 2026-10-24 | Risk-triggered review is a review-aware gate: an authorized approval of the exact head commit unblocks it, recorded as a commit status. |
