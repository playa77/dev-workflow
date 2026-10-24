<!-- workflow-kit | v2.0.0 | 2026-10-25 -->
# Workflow kit — architecture-first agentic delivery

A self-contained method for turning an interview into agent-executed work packages that a human can verify without reading everything. The agent reads `AGENTS.md`; the method lives under `workflow/`; the scripts enforce what prose cannot.

**Provenance.** The operational form of a Delivery Contract, a multi-phase architect prompt, a budget analysis, and the practice research behind the 2.0 rewrite. Version 2 removes the human-gated steps, replaces the confidence threshold with a coverage map, and adds a decision ledger and changelog as first-class artifacts.

---

## The loop

```
Intake → Spec (Docs 1–3) → WP → verify → merge → measure
 ≤12 Qs    one pass, one digest  execute  gates   auto*   ledger
```

\* Automatic when every gate is green and no risk trigger fires. Risk-bearing changes still require a human; see `workflow/REVIEW.md`.

Two properties make it work:

1. **Docs 1+2+3 are sufficient for a zero-context agent.** Nothing important lives in a conversation.
2. **Every rule is machine-checked or agent-verified with named evidence.** "A human looked at it" is not enforcement; the human supplies intent, approves the digest, and accepts risk.

## Install

You do not run commands. Point the agent at this kit and say:

> Read `workflow/START.md` in this kit, then install the workflow into this repository.

The agent runs `workflow/scripts/install.py`, resolves anything `doctor.py` reports, commits the result, and begins the intake interview in the same session. Install is idempotent and never overwrites `README.md`, `AGENTS.md`, `DECISIONS.md` or `CHANGELOG.md`.

If you are working on the kit itself rather than installing it, `workflow/START.md` still applies.

## File map

| Path | What it is |
|---|---|
| `AGENTS.md` | Constitution: delivery unit, execution policy, prohibitions |
| `DECISIONS.md` | Decision ledger with a generated index; rejected options live inside the entry that rejected them |
| `CHANGELOG.md` | Curated, user-visible changes; every line cites a decision and a work package |
| `workflow/START.md` | The single entrypoint: install, bootstrap, phase state machine |
| `workflow/WORKFLOW.md` | Phases, gates, roles, artifact authority, WP lifecycle |
| `workflow/VERIFICATION.md` | Test-integrity mechanisms, declaration guards, validation matrix |
| `workflow/STATE.md` | `intake.json`, `progress.md`, `state.json`, resume protocol |
| `workflow/REVIEW.md` | Risk triggers, the small non-delegable list, milestone audit |
| `workflow/MEASUREMENT.md` | Telemetry, calibration ledger, retro |
| `workflow/config.json` | Commands and modes, generated at install |
| `workflow/prompts/` | `intake`, `spec`, `execute`, `verify` |
| `workflow/references/` | Section templates loaded on demand |
| `workflow/templates/` | WP brief, delivery declaration, digest, checkpoints |
| `workflow/scripts/` | Installer, doctor, gates, ledger and changelog checks, stats |
| `.github/workflows/wp.yml` | CI lanes, fail-closed |

## Design rules

1. **One normative home per rule.** `AGENTS.md` owns rules; `WORKFLOW.md` process; `VERIFICATION.md` mechanisms; `STATE.md` schemas; `DECISIONS.md` why. Everything else is a pointer.
2. **Machine-checked or agent-verified, or deleted.** A rule without a check and without a named verification is decoration.
3. **JSON where a model edits, Markdown where a human reads.** Models rewrite prose; they edit fields.
4. **Length caps.** `AGENTS.md` under 100 lines; prompts under 120. A long instruction file causes the instructions that matter to be ignored.
5. **Review is the constraint, not context.** A package that cannot be reviewed in one pass is too large.
6. **Decisions are load-bearing.** The ledger is read before any approach is proposed; an entry exists when a choice constrains future work.

## What changed in 2.0

- Install, command setup, baseline and bootstrap are agent steps. One entrypoint, no human shell.
- The interview exits on a countable coverage map, not a confidence percentage.
- Docs 1–3 are generated in one pass; the human approves a one-page digest.
- Human input is limited to the interview, the digest and risk-triggered review.
- Merge is automatic on green with risk triggers; CI lanes are generated from `workflow/config.json`.
- `DECISIONS.md` and `CHANGELOG.md` are method artifacts, correlated by ID and checked in CI.
- `HUMAN-REVIEW.md`, the per-document approvals, the operator checklist and the manual command table are gone.

## Known limits

- **Stack adapters.** Python, JS/TS, Go and Rust are recognised. Anything else fails closed until adapted.
- **Structural checks are not semantics.** `check-spec.py` verifies seams, types, callers and coverage structurally; a spec can pass and still be wrong.
- **Mutation testing** is specified but not implemented; `workflow/VERIFICATION.md` §2.3 states the scope policy and hook point.
- **Review quality is not mechanisable.** Risk triggers and milestone sampling are the defence; they depend on the operator actually looking.
- **The ledger assumes tens of decisions per project.** Past ~150 entries, revisit D-015.
