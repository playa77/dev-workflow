<!-- workflow-kit | v2.1.0 | 2026-10-24 | review-aware risk gate; install/CI conformance -->
# Workflow kit — architecture-first agentic delivery

A self-contained method for turning an interview into agent-executed work packages that a human can verify without reading everything. The agent reads `AGENTS.md`; the method lives under `workflow/`; the scripts enforce what prose cannot.

**Provenance.** The operational form of a Delivery Contract, a multi-phase architect prompt, a budget analysis, and the practice research behind the 2.0 rewrite. Version 2 removes the human-gated steps, replaces the confidence threshold with a coverage map, and adds a decision ledger and changelog as first-class project artifacts.

---

## The loop

```
Intake → Spec (Docs 1–3) → WP → verify → merge → measure
 ≤12 Qs    one pass, one digest  execute  gates   auto*   ledger
```

\* Automatic when the operator has set `mode.merge: auto`, every gate is green and the `risk-gate` status is green — either no risk trigger, or an authorized human approved the exact head commit. The kit ships no merger. Risk-bearing changes still require a human; see `workflow/REVIEW.md` §1.1.

Two properties make it work:

1. **Docs 1+2+3 are sufficient for a zero-context agent.** Nothing important lives in a conversation.
2. **Every rule is machine-checked or agent-verified with named evidence.** "A human looked at it" is not enforcement; the human supplies intent, approves the digest, and accepts risk.

## Install

Point an agent at this kit and give it this prompt:

```
Use the development workflow kit from:
https://github.com/playa77/dev-workflow

Clone the kit outside the current project directory.

Read workflow/START.md in the kit and follow its installation
instructions for the current project.

First run the installer in dry-run mode and inspect its proposed
changes. Then install the workflow, run doctor.py, and resolve
installation issues.

Do not overwrite existing project instructions or documentation.
Do not enable automatic merging without my approval.

Once installed, begin the workflow's intake phase.
```

The installer runs `python3 <kit>/workflow/scripts/install.py --target . --dry-run` first and prints the plan without writing. A real install then:

- copies the method into `workflow/`;
- installs the full constitution as `workflow/CONSTITUTION.md`, and uses it as `AGENTS.md` when the project has none;
- merges a marker block into an existing `AGENTS.md` and appends a pointer block to `README.md` — it never replaces either;
- writes `DECISIONS.md` and `CHANGELOG.md` from the seeds only when absent;
- detects the stack and writes `workflow/config.json`;
- generates the CI workflow. Its full-suite lane resolves `test_full` from `workflow/config.json` at run time, so an unset role fails instead of passing silently;
- snapshots the test baseline.

Install is idempotent. It never overwrites `README.md`, `AGENTS.md`, `DECISIONS.md` or `CHANGELOG.md`. A CI file that does not carry the generated marker is left untouched; a generated one is re-rendered on upgrade.

`--upgrade` updates kit-owned files while **preserving** project edits in `workflow/config.json`: it fills only command roles that are missing or unset, and keeps `mode`, `review`, `risk_triggers` and `integrity` as the project set them. Use `--reset-config` to deliberately regenerate the file.

A new install writes `mode.merge: human`. Automatic merging is enabled with `--merge-mode auto`, or by editing `workflow/config.json` later with the operator's approval.

The CI workflow publishes a `risk-gate` commit status on the head of every pull request. **Make it a required status check in branch protection** — that is the one-time setting that turns the gate into an enforcement point. A PR with no risk trigger gets a green status automatically; a PR with a trigger stays red until an authorized human approves that exact head commit, and CI re-evaluates on the review event without needing a new push. Authorization is `review.approvers` in `workflow/config.json`, or any collaborator with write permission when that list is empty.

**This repository is the kit source.** It carries no `DECISIONS.md` or `CHANGELOG.md` of its own: those are created in a project when the kit is installed, and `doctor.py` distinguishes the two layouts (`workflow/state/install.json` records `"kit": true` here).

## File map

| Path | What it is |
|---|---|
| `AGENTS.md` | The constitution: delivery unit, execution policy, prohibitions. Installs as `workflow/CONSTITUTION.md` and, on a project with no `AGENTS.md`, as that file. |
| `workflow/START.md` | The single entrypoint: install, bootstrap, phase state machine |
| `workflow/WORKFLOW.md` | Phases, gates, roles, artifact authority, WP lifecycle |
| `workflow/VERIFICATION.md` | Test-integrity mechanisms, declaration guards, validation matrix |
| `workflow/STATE.md` | `intake.json`, `progress.md`, `state.json`, resume protocol |
| `workflow/REVIEW.md` | Risk triggers, the merge procedure, the small non-delegable list, milestone audit |
| `workflow/MEASUREMENT.md` | Telemetry, calibration ledger, retro |
| `workflow/config.json` | Commands and modes, generated at install |
| `workflow/prompts/` | `intake`, `spec`, `execute`, `verify` |
| `workflow/references/` | Section templates loaded on demand |
| `workflow/templates/` | WP brief, delivery declaration, digest, checkpoints, and the seeded `DECISIONS.md` / `CHANGELOG.md` |
| `workflow/scripts/` | Installer, doctor, gates, ledger and changelog checks, risk scan and review-aware gate, role runner, stats |
| `.github/workflows/wp.yml` | CI lanes for the kit itself; the template written into projects is in `workflow/scripts/install.py` |

Project artifacts created at install: `DECISIONS.md` (one append-only ledger with a generated index) and `CHANGELOG.md` (curated, user-visible changes, every line citing a decision and a work package).

## Design rules

1. **One normative home per rule.** `AGENTS.md` owns rules; `WORKFLOW.md` process; `VERIFICATION.md` mechanisms; `STATE.md` schemas; `DECISIONS.md` why. Everything else is a pointer.
2. **Machine-checked or agent-verified, or deleted.** A rule without a check and without a named verification is decoration.
3. **JSON where a model edits, Markdown where a human reads.** Models rewrite prose; they edit fields.
4. **Length caps.** `AGENTS.md` under 100 lines; prompts under 120. A long instruction file causes the instructions that matter to be ignored.
5. **Review is the constraint, not context.** A package that cannot be reviewed in one pass is too large.
6. **Decisions are load-bearing.** The ledger is read before any approach is proposed; an entry exists when a choice constrains future work.

## What changed in 2.1.0

- **The risk gate is review-aware.** `risk-gate.py` decides `pass` / `blocked` / `approved`: no trigger passes, a trigger blocks until an authorized human approves the exact head commit, and CI re-evaluates on `pull_request_review` so an approval flips the gate without a new push. The verdict is published as a commit status on the head, named by `review.status_context` (default `risk-gate`).
- **Branch protection must require that status.** The workflow job's own check carries the event SHA and cannot clear a failure recorded on the head; the status is the object that carries the decision.
- **The full-suite lane resolves `test_full` from configuration at run time** (`run-role.py test_full`). The installer no longer writes `run: true` for an undetected project, and correcting `workflow/config.json` no longer requires regenerating CI.
- **`doctor.py` checks the CI policy, not just the file's existence**: the review trigger, the gate call, its publishing permission and the config-resolved suite.
- **`START.md` resume takes precedence** over the ready-to-execute row; an open checkpoint always wins.
- `workflow/config.json` gains `review.approvers` and `review.status_context`; `check-config.py` validates them.

## What changed in 2.0.1

- The installer transfers the full constitution (`workflow/CONSTITUTION.md`, and `AGENTS.md` itself on a project that has none) instead of only a short instruction block.
- CI began running `risk-scan.py --fail-on-trigger` so a trigger could not pass quietly; 2.1.0 replaces that report-only lane with the review-aware gate below.
- `--upgrade` preserves `workflow/config.json`; `--reset-config` is the explicit way to discard project edits.
- New installs default to `mode.merge: human`; `--merge-mode auto` is an explicit opt-in.
- `doctor.py` distinguishes the kit repository from an installed project. The kit no longer carries a ledger or changelog of its own.
- A generated CI file is re-rendered on upgrade; a hand-edited one is left alone and reported.

## What changed in 2.0

- Install, command setup, baseline and bootstrap are agent steps. One entrypoint, no human shell.
- The interview exits on a countable coverage map, not a confidence percentage.
- Docs 1–3 are generated in one pass; the human approves a one-page digest.
- Human input is limited to the interview, the digest and risk-triggered review.
- Merge is automatic on green with risk triggers; the full-suite lane is rendered from `workflow/config.json` at install.
- `DECISIONS.md` and `CHANGELOG.md` are method artifacts, correlated by ID and checked in CI.
- `HUMAN-REVIEW.md`, the per-document approvals, the operator checklist and the manual command table are gone.

## Known limits

- **Stack adapters.** Python, JS/TS, Go and Rust are recognised. Anything else fails closed until adapted.
- **Structural checks are not semantics.** `check-spec.py` verifies seams, types, callers and coverage structurally; a spec can pass and still be wrong.
- **Mutation testing** is specified but not implemented; `workflow/VERIFICATION.md` §2.3 states the scope policy and hook point.
- **Review quality is not mechanisable.** Risk triggers and milestone sampling are the defence; they depend on the operator actually looking.
- **No merge runner.** `mode.merge: auto` is a permission, not a daemon. The executing agent performs the merge sequence in `workflow/REVIEW.md` §1.1 after CI is green; nothing in the kit can merge a pull request by itself.
- **Branch protection is external.** The gate publishes a `risk-gate` commit status; requiring it is a repository setting the installer cannot make. Without it the gate reports but does not block.
- **Fork pull requests cannot publish the status.** GitHub gives workflows triggered by fork PRs a read-only `GITHUB_TOKEN`, so the gate cannot record its verdict and the required status never appears. The kit assumes branches in the same repository, which is how the agent workflow operates.
- **Verifier separation is host-provided.** The method requires a fresh-context verifier but cannot spawn one. The host agent must start a new context (a subagent or a new session) and give it only the brief, the diff and the command output.
- **The ledger assumes tens of decisions per project.** Past ~150 entries, the single-file ledger design needs revisiting.
