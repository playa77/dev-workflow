<!-- start-here | v2.0.0 | 2026-10-25 | single entrypoint -->
# START — install, bootstrap, and the phase state machine

This is the only file an operator needs to point an agent at. It says what to do first, what to read next, and when to stop.

## 0. Which state are we in?

| Check | State | Go to |
|---|---|---|
| `workflow/config.json` missing or `workflow/state/install.json` missing | not installed | §1 |
| `workflow/state/intake.json` missing | installed, no intake | §3 |
| `intake.json` has `"open": 0` and a digest exists, no `docs/spec/SPEC.md` | intake done | §4 |
| `docs/spec/SPEC.md` exists and `docs/roadmap/ROADMAP.md` exists | ready to execute | §5 |
| `docs/wp/WP-nnn.state.json` exists and is not `delivered` | resuming | `workflow/STATE.md` §3 |

## 1. Install (agent, no operator commands)

1. Run `python3 <kit>/workflow/scripts/install.py --target .`, where `<kit>` is the path to the kit you were given (`.` when the kit is already this repository).
   - It copies the method into `workflow/`, merges a marker block into `AGENTS.md`, appends a pointer block to `README.md` (never replaces either), detects the stack, writes `workflow/config.json`, generates `.github/workflows/wp.yml`, writes the test baseline, and records `workflow/state/install.json`.
   - `--dry-run` prints the plan; `--upgrade` updates kit-owned files while preserving `config.json`, `DECISIONS.md`, `CHANGELOG.md`, `state/` and `process/`.
2. Run `python3 workflow/scripts/doctor.py`.
   - Resolve every failure **inside `workflow/`**. If a command role cannot be detected, inspect the repository's Makefile, `package.json`, CI history and lockfiles, run the cheap candidates to confirm they work, and write the verified command into `workflow/config.json`. Do not hand this to the operator.
3. Commit on `chore/workflow-init` with a Conventional Commit message. Open a PR and merge per `workflow/config.json` mode. The install touches `AGENTS.md`, `README.md` and `.github/`, so a risk trigger may apply — if it does, request review and wait.
4. Continue to §2 in the same session. Do not stop to ask whether to begin.

## 2. Read order

1. `AGENTS.md` — rules. They override every prompt.
2. `DECISIONS.md` — read the index; search for anything the brief touches.
3. `workflow/WORKFLOW.md` — phases and gates.
4. The phase prompt in `workflow/prompts/`.

Never load the whole repository "for context". Read what the phase points at.

## 3. Intake

Prompt: `workflow/prompts/intake.md`.

- Recon first: answer every topic you can from the repository, the brief and git history, with a file path as evidence.
- Ask at most twelve questions for a project, in rounds of up to three, each answerable by a letter or one line, each with a recommended answer and the cost of getting it wrong.
- Write `workflow/state/intake.json` (schema in `workflow/STATE.md` §1). The phase exits when `open == 0` and `check-intake.py` passes.
- Write the one-page digest to `docs/process/DIGEST.md`. **Stop here and wait for the operator.** That approval is the only approval before execution.

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
5. `python3 workflow/scripts/risk-scan.py --base main` — if `requires_human`, stop and request review.
6. `python3 workflow/scripts/close-wp.py --wp WP-nnn --base main` — appends the changelog line, regenerates the ledger index, validates both, writes the declaration.
7. Merge per config. Do not start the next package in the same turn unless the operator asked for a batch.

## 6. When something blocks

- A missing requirement: stop, record the question in the digest, ask. Do not invent it.
- A spec gap: `[CONFLICT]` + decision entry; a versioned spec revision, never roadmap-local invention.
- A limit reached: checkpoint, report the exact remaining step. Do not claim completion.
- A risk trigger: stop and request review. Do not merge.
