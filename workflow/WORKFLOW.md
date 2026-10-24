<!-- workflow-spec | v2.1.0 | 2026-10-24 | human gates collapsed; review-aware risk gate; workflow/ layout -->
# The Workflow — normative process specification

**Status:** Approved · **Owner:** Operator · **Consumer:** operator, architect, executor, verifier · **Normative for:** phases, gates, roles, artifact authority, WP lifecycle

Rules live in `AGENTS.md`. This document defines the process: who does what, in what order, what evidence moves it forward, and which artifact is authoritative for what. Where the two disagree, `AGENTS.md` wins and this document is corrected.

---

## 1. Purpose

A zero-context coding agent can implement a work package correctly, and a human can verify that it did, without either re-deriving the architecture. Documents are not deliverables; they are the compression format.

## 2. Roles

| Role | Who | May decide | May not decide |
|---|---|---|---|
| **Operator** | Dan | Answer the intake; approve the digest; accept risk on a trigger; amend this method | Delegate the digest approval |
| **Architect** | agent, spec prompt | Wording, structure, proposed options | Buy a requirement nobody confirmed |
| **Executor** | coding agent | Implementation, tests, refactors inside scope | Change scope, weaken tests, change model or effort |
| **Verifier** | fresh-context agent | Whether evidence supports each criterion | Fix the code it verifies |
| **CI** | scripts | Pass/fail on declarations and mechanical guards | Semantic completeness |

Human-only decisions: the intake answers, the digest approval, risk acceptance on a trigger, and changes to `AGENTS.md`, this document, or `DECISIONS.md` entries that were adopted by the operator. Everything else is agent work or a script.

The verifier's separation is real only if the context is: no script can create one. The host agent starts a subagent or a new session and hands it the brief, the diff and the command output — not this conversation.

## 3. Terminology

| Term | Meaning |
|---|---|
| **WP** | Work package. One independently testable outcome, one branch, one PR. |
| **Seam** | A cross-module handoff with a named constructor or invoker. |
| **Composition root** | The single module that constructs components. |
| **Contract** | Any runtime capability a WP's verification requires: a reachable module, populated data, cross-process state, a credential, an interface. |
| **Delivery declaration** | The PR body produced from `workflow/templates/PR.md`. |
| **Evidence** | Command output, run timestamps, diffs, measurements. Not assertions. |
| **Decision** | An entry in `DECISIONS.md` with context, options, outcome and a revisit condition. |
| **Digest** | The one-page summary the operator approves: constraint ledger, non-goals, deferrals, top risks. |
| **Checkpoint** | The `progress.md` + `state.json` pair at a milestone. |

## 4. Artifacts and authority

| Artifact | Path | Authority | Versioned |
|---|---|---|---|
| Constitution | `AGENTS.md` | Delivery unit, execution policy, prohibitions; installed verbatim as `workflow/CONSTITUTION.md` | yes |
| Process | `workflow/WORKFLOW.md` | Phases, gates, roles, lifecycle | yes |
| Decisions | `DECISIONS.md` | Irreversible choices, rejected options, revisit conditions | append-only |
| Changelog | `CHANGELOG.md` | User-visible changes, one line per change | per release |
| Intake state | `workflow/state/intake.json` | Topic coverage, defaults, deferrals | machine |
| Design document | `docs/design/DESIGN.md` | Requirements, constraints (§2), architecture | semver |
| Technical spec | `docs/spec/SPEC.md` | Implementation contract, seams, call traces | semver |
| Roadmap | `docs/roadmap/ROADMAP.md` | WP index, DAG, coverage | semver |
| WP brief | `docs/wp/WP-nnn.md` | Scope, acceptance, verification for one package | per WP |
| Checkpoint (human) | `docs/wp/WP-nnn.progress.md` | Narrative state | per milestone |
| Checkpoint (machine) | `docs/wp/WP-nnn.state.json` | Acceptance `passes`, evidence, status | per transition |
| Digest | `docs/process/DIGEST.md` | The approved constraint ledger and deferrals | per spec revision |
| Calibration ledger | `workflow/process/CALIBRATION.csv` | Per-WP actuals | append-only |

Doc 1 §2 is the **constraint ledger**. No later section of any document may assume a capability §2 excludes. A conflict is recorded as a decision entry and a `[CONFLICT]`, never smoothed over.

## 5. Phases and gates

Every gate names the evidence that moves the phase forward. A gate without its evidence is not passed, regardless of how complete the artifact looks.

### Phase 0 — Intake

**Goal:** a complete coverage map, not a confidence figure. Twelve topics, statuses `answered | answered_by_repo | defaulted | deferred | open`. At most twelve questions for a project, in rounds of up to three, each with a recommended answer.

Answer from the repository first. A question the agent could have answered by reading is a defect.

**Gate:** `check-intake.py` passes (`open == 0`, every default names its blast radius, every deferral names the resolving WP) and the operator approves `docs/process/DIGEST.md`. Silence is not approval.

### Phase 1 — Spec pass (Docs 1–3)

One pass, three files. No approval between them. Sections and checks: `workflow/prompts/spec.md` and `workflow/references/spec-sections.md`.

**Gate:** `check-spec.py` and `check-roadmap.py` pass, the executability trace is present, and the digest is approved. A gap is `[CONFLICT]`, not a note.

### Phase 2 — Execution

One WP per branch and PR. Prompt: `workflow/prompts/execute.md`. Brief: `workflow/templates/WP.md`.

**Gate:** every acceptance criterion has evidence on the delivered head; checkpoint written; `check-wp.py`, `check-state.py`, `check-declaration.py` pass.

### Phase 3 — Review

Order is fixed:

1. machine gates (`workflow/VERIFICATION.md`, CI);
2. fresh-context verifier (`workflow/prompts/verify.md`);
3. risk gate (`workflow/scripts/risk-gate.py`; CI publishes its verdict as the `risk-gate` status on the head commit and re-runs on review events);
4. human review **only if the scan triggers**, otherwise at the milestone audit (`workflow/REVIEW.md`);
5. merge per `workflow/config.json` mode, under the procedure in `workflow/REVIEW.md` §1.1 — `auto` is a permission for the executing agent, not a runner.

**Gate:** verification clean or every exception recorded; verifier `pass`; no unresolved risk trigger.

### Phase 4 — Close and measure

`close-wp.py` appends the changelog line, regenerates the ledger index, validates both artifacts, and appends the calibration row.

**Gate:** `check-ledger.py` and `check-changelog.py` pass; the calibration row exists.

## 6. Work package lifecycle

```
proposed → approved → claimed → in-progress → verified → delivered → merged → measured
                │                                    │
                └──────────── returned on rejection ─┘
```

| Transition | Evidence required |
|---|---|
| proposed → approved | brief complete: objective, scope, acceptance, verification, type, review cost, user-visible effect, decisions expected |
| approved → claimed | branch from the roadmap's declared base; prerequisites confirmed |
| claimed → in-progress | preflight report: modules touched, unresolved dependencies, verification path |
| in-progress → verified | every criterion has evidence; integrity checks pass |
| verified → delivered | declaration complete; exceptions justified |
| delivered → merged | gates green; no unresolved risk trigger |
| merged → measured | changelog line and calibration row written |

## 7. Types and complexity

| Type | Characteristic | Gate |
|---|---|---|
| **Deterministic** | Architecture settled, interfaces defined, tests clear | Standard acceptance |
| **Exploratory** | Requirements clear, implementation uncertain | Investigation boundary and time-boxed preflight |
| **Architectural** | Competing designs | Spike first; do not implement under unresolved architecture |
| **Spike** | Deliverable is a decision | Decision entry in `DECISIONS.md`; no production code merged |

Complexity has five dimensions: context, uncertainty, dependencies, verification, **review**. A WP low on the first four but high on review is split by reviewable behaviour, never by file and never to reduce token consumption.

## 8. Conflict and escalation

1. A conflict between documents, or between a document and reality, is recorded as `[CONFLICT]` with both sides quoted.
2. The executor resolves it under constraint supremacy and records a decision entry. It does not choose the convenient side.
3. It escalates to the operator only when the **constraint ledger itself** must change, or when the resolution reverses an adopted decision.
4. A resolution that changes a decision is a new ledger entry with `Supersedes`; the owning document gets a version bump.

Silent deviation is the failure this section exists to prevent.

## 9. Versioning and change control

- Every normative document carries a title, semver, date, status and revision history.
- A revision bumps the version and states what changed.
- Cross-document references cite document + version + section; a reference without a version is a defect.
- `AGENTS.md` and this document change only by operator decision, recorded as a ledger entry.

## 10. Commands

Commands live in `workflow/config.json`, generated at install and verified by `check-config.py`. The workflow refers to roles, never literals:

`TEST_AFFECTED`, `TEST_FULL`, `TEST_SMOKE`, `LINT`, `BUILD`, `INTEGRITY`, `CALLERS`, `STATS`.

An unresolved role fails closed at the pre-merge gate. It never silently skips.

## 11. What this workflow refuses to do

- Advance a phase without its gate evidence.
- Deliver part of a package without an explicit instruction.
- Call a package complete on the strength of a summary.
- Split a package because context is running out.
- Accept a green run as proof that a test proves anything.
- Resolve a contradiction silently.
- Treat a token estimate as an authorized limit.
- Remove a human gate without replacing it with a check.

## Revision history

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-10-24 | Initial process specification. |
| 2.0.0 | 2026-10-25 | Human gates collapsed to intake, digest and risk triggers; all other gates are checks. Adds close/measure, ledger and changelog authority, and command roles. |
| 2.0.1 | 2026-10-24 | Risk scan is fail-closed; merge is a documented agent procedure, not a runner. |
| 2.1.0 | 2026-10-24 | The risk gate is review-aware: blocked until an authorized approval on the exact head commit, re-evaluated on review events. |
