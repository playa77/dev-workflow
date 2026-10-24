<!-- start-here | v2.1.0 | 2026-10-24 | single entrypoint; resume precedence; review-aware gate -->
# START — install, bootstrap, and the phase state machine

This is the only file an operator needs to point an agent at. It says what to do first, what to read next, and when to stop.

## 0. Which state are we in?

| Check | State | Go to |
|---|---|---|
| `docs/wp/WP-nnn.state.json` exists and is not `delivered` | **resuming — takes precedence over every row below** | `workflow/STATE.md` §3 |
| `workflow/config.json` missing or `workflow/state/install.json` missing | not installed | §1 |
| `workflow/state/intake.json` missing | installed, no intake | §3 |
| `intake.json` has `"open": 0` and a digest exists, no `docs/spec/SPEC.md` | intake done | §4 |
| `docs/spec/SPEC.md` exists and `docs/roadmap/ROADMAP.md` exists | ready to execute | §5 |

Check resume first: an interrupted package and a project that is ready to execute can both be true, and the interrupt wins. Do not start a new package while a checkpoint is open.

## 1. Install (agent, no operator commands)

1. Run the installer in dry-run first and read the plan:
   `python3 <kit>/workflow/scripts/install.py --target . --dry-run`, where `<kit>` is the path to the kit you were given (`.` when the kit is already this repository).
   - It lists every file and marker block it would write and writes nothing. If the plan would replace project content, stop and report it rather than proceeding.
2. Run the same command without `--dry-run`.
   - It copies the method into `workflow/`, installs the constitution as `workflow/CONSTITUTION.md` (and as `AGENTS.md` when the project has none), merges a marker block into an existing `AGENTS.md`, appends a pointer block to `README.md` (never replaces either), seeds `DECISIONS.md` and `CHANGELOG.md` only if absent, detects the stack, writes `workflow/config.json`, generates `.github/workflows/wp.yml`, writes the test baseline, and records `workflow/state/install.json`.
   - `--upgrade` updates kit-owned files and preserves `config.json` edits, `DECISIONS.md`, `CHANGELOG.md`, `state/` and `process/`; in the configuration it fills only command roles that are missing or unset. `--reset-config` is the explicit way to regenerate the file.
   - A new install writes `mode.merge: human`. Do not switch it to `auto` without the operator's approval; propose the change in the digest (§3).
3. Run `python3 workflow/scripts/doctor.py`.
   - Resolve every failure **inside `workflow/`**. If a command role cannot be detected, inspect the repository's Makefile, `package.json`, CI history and lockfiles, run the cheap candidates to confirm they work, and write the verified command into `workflow/config.json`. Do not hand this to the operator.
   - CI resolves `test_full` from `workflow/config.json` at run time (`run-role.py`); an unset role fails the suite. Correcting the file needs no CI regeneration — re-run `doctor.py`, which also checks that the workflow still enforces the risk policy.
4. Commit on `chore/workflow-init` with a Conventional Commit message. Open a PR and merge per `workflow/config.json` mode.
   - The install touches `AGENTS.md`, `README.md` and `.github/`, so the risk gate blocks until the operator approves the head commit. Merge this first PR after review.
   - **After it merges**, ask the operator to make the `risk-gate` commit status a required check in branch protection (a one-time repository setting). Configuring it before the workflow exists on the default branch would block this PR with no gate able to publish. Without the required check, later gates report but do not block.
5. Continue to §2 in the same session. Do not stop to ask whether to begin.

## 2. Read order

1. `AGENTS.md`, then `workflow/CONSTITUTION.md` — rules. They override every prompt.
2. `DECISIONS.md` — read the index; search for anything the brief touches.
3. `workflow/WORKFLOW.md` — phases and gates.
4. The phase prompt in `workflow/prompts/`.

Never load the whole repository "for context". Read what the phase points at.

## 3. Intake

Prompt: `workflow/prompts/intake.md`.

- Recon first: answer every topic you can from the repository, the brief and git history, with a file path as evidence.
- Ask at most twelve questions for a project, in rounds of up to three, each answerable by a letter or one line, each with a recommended answer and the cost of getting it wrong.
- Write `workflow/state/intake.json` (schema in `workflow/STATE.md` §1). The phase exits when `open == 0` and `check-intake.py` passes.
- Write the one-page digest to `docs/process/DIGEST.md`. **Stop here and wait for the operator.** That approval is the only approval before execution. It also carries one line of merge mode: `human` or `auto`. Propose `auto` only with the operator's explicit approval, then set it in `workflow/config.json`.

## 4. Spec pass

Prompt: `workflow/prompts/spec.md`. One pass, three files:

- `docs/design/DESIGN.md`
- `docs/spec/SPEC.md`
- `docs/roadmap/ROADMAP.md`

Run `check-spec.py` and `check-roadmap.py` before presenting the digest. A `[CONFLICT]` is recorded as a decision entry, not smoothed over. Present the digest; stop for approval.

## 5. Execution loop

For each package, in dependency order:

1. Create `docs/wp/WP-nnn.md` from `workflow/templates/WP.md` if the roadmap did not already.
2. Prompt: `workflow/prompts/execute.md`. Preflight is read-only; if the boundary is wrong, report before writing code.
3. Implement, test, checkpoint (`progress.md`, `state.json`).
4. Prompt: `workflow/prompts/verify.md` in a fresh context. The verifier does not fix code.
5. `python3 workflow/scripts/risk-gate.py --base main` — `pass` means no trigger; `blocked` means stop and request review. This local run cannot see approvals: CI re-decides on `pull_request` and `pull_request_review` and publishes the verdict as the `risk-gate` status on the head commit.
6. `python3 workflow/scripts/close-wp.py --wp WP-nnn --base main` — appends the changelog line, regenerates the ledger index, validates both, writes the declaration.
7. Merge per `workflow/config.json` mode, following `workflow/REVIEW.md` §1.1 — only when every required check is green and `risk-gate` is green on the head being merged. Nothing in the kit merges by itself. Do not start the next package in the same turn unless the operator asked for a batch.

## 6. When something blocks

- A missing requirement: stop, record the question in the digest, ask. Do not invent it.
- A spec gap: `[CONFLICT]` + decision entry; a versioned spec revision, never roadmap-local invention.
- A limit reached: checkpoint, report the exact remaining step. Do not claim completion.
- A risk trigger: stop and request review. Do not merge.
