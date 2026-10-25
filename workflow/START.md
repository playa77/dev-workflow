<!-- start-here | v2.2.0 | 2026-10-25 | single entrypoint; solo default; advisory risk report -->
# START — install, bootstrap, and the phase state machine

This is the only file an operator needs to point an agent at. It says what to do first, what to read next, and when to stop.

## 0. Which state are we in?

| Check | State | Go to |
|---|---|---|
| `docs/wp/WP-nnn.state.json` exists and is not `delivered` | **resuming — takes precedence over every row below** | `workflow/STATE.md` §3 |
| `workflow/config.json` missing or `workflow/state/install.json` missing | not installed | §1 step 1 |
| `workflow/state/install.json` exists but the installation is not committed and pushed on the default branch | **bootstrap unfinished — finish §1 before anything else** | §1 step 2 |
| `workflow/state/intake.json` missing | installed, no intake | §3 |
| `intake.json` has `"open": 0` and a digest exists, no `docs/spec/SPEC.md` | intake done | §4 |
| `docs/spec/SPEC.md` exists and `docs/roadmap/ROADMAP.md` exists | ready to execute | §5 |

Check resume first: an interrupted package and a project that is ready to execute can both be true, and the interrupt wins. Do not start a new package while a checkpoint is open. An unfinished bootstrap also precedes every phase: the method is not installed until its commit is on the default branch.

## 1. Install and bootstrap (agent; one operator approval)

Bootstrap is not a work package. It is the one change that creates the method, so it commits to the default branch after the operator approves the diff instead of travelling through a branch, a pull request and the risk gate. The ordinary lifecycle — `AGENTS.md` §1 and §8: one branch and PR per package, the risk gate, merge mode — is mandatory from intake (§3) onward, once the bootstrap commit is on `main`.

1. **Create the workflow files.** Run the installer in dry-run first and read the plan:
   `python3 <kit>/workflow/scripts/install.py --target . --dry-run`, where `<kit>` is the path to the kit you were given (`.` when the kit is already this repository).
   - It lists every file and marker block it would write and writes nothing. If the plan would replace project content, or the working tree is not clean, stop and report it rather than proceeding: the bootstrap commit must contain the installation and nothing else.
   - Run the same command without `--dry-run`.
     - It copies the method into `workflow/`, installs the constitution as `workflow/CONSTITUTION.md` (and as `AGENTS.md` when the project has none), merges a marker block into an existing `AGENTS.md`, appends a pointer block to `README.md` (never replaces either), seeds `DECISIONS.md` and `CHANGELOG.md` only if absent, detects the stack, writes `workflow/config.json`, generates `.github/workflows/wp.yml`, writes the test baseline, and records `workflow/state/install.json`.
     - `--upgrade` updates kit-owned files and preserves `config.json` edits, `DECISIONS.md`, `CHANGELOG.md`, `state/` and `process/`; in the configuration it fills only command roles that are missing or unset. `--reset-config` is the explicit way to regenerate the file. An explicit `--review-mode advisory` on `--upgrade` migrates an existing strict installation to the solo default.
     - A new install writes `mode.merge: human` and `mode.review: advisory` (the solo default: the owner merges and accepts reported risks). `--review-mode risk-triggered` or `human` opts into independent review; `--merge-mode auto` opts into agent merging. Do not change either without the operator's approval; propose it in the digest (§3).

2. **Run every local check the installation provides.** No pull request or risk gate reviews this commit, so run them all and report every result.
   - `python3 workflow/scripts/doctor.py` — required files, configuration, ledger and changelog, and the CI policy. Resolve every failure **inside `workflow/`** and re-run it until it exits 0.
   - `python3 workflow/scripts/check-config.py --verify-commands` — every command role resolves. If a role cannot be detected, inspect the repository's Makefile, `package.json`, CI history and lockfiles, run the cheap candidates to confirm they work, and write the verified command into `workflow/config.json`. Do not hand this to the operator. CI resolves `test_full` from `workflow/config.json` at run time (`run-role.py`); an unset role fails the suite. Correcting the file needs no CI regeneration — re-run `doctor.py`, which also checks that the workflow still enforces the risk policy.
   - `bash workflow/scripts/check-test-integrity.sh --verify` when the installer wrote `workflow/state/test-baseline.json`.
   - `python3 workflow/scripts/run-role.py <role>` for each configured role the repository can run before the commit — `lint`, `build`, `test_full`, `test_affected` — cheapest first, so the command CI will run is the one you exercised. Report each command, its exit code and its summary line. An unset role or a zero-test run is reported as such, never counted as passing.

3. **Present the changes and stop.** Stage the bootstrap paths (staging is not committing), then give the operator, in one message: the dry-run plan, `git status --short`, `git diff --cached --stat`, the full staged diff, every check with its command, exit code and summary line, anything the installer skipped (preserved CI file, absent baseline, unset role), and the exact commit message and branch. Then wait. Do not pass `--commit` to the installer: it stages everything and commits without the approval this step requires. If the operator asks for a change, apply it, re-run step 2 and present again. Do not commit, push or start intake before the operator approves.

4. **Commit directly to the default branch and push.** This is the only commit the method makes without a pull request.
   - Commit only the staged bootstrap set — `workflow/`, `.github/workflows/`, `AGENTS.md`, `README.md`, `DECISIONS.md`, `CHANGELOG.md` — never unrelated work. The message is `chore: install workflow kit v<version>`. On a repository with no commits, create `main` and make this its initial commit.
   - Push, then verify `git rev-parse HEAD` equals `git rev-parse origin/main` and the tree is clean.
   - If the push is rejected — branch protection already requires a pull request, no write access, non-fast-forward — stop and report the exact output. Never force-push, and never open a pull request to route around it without the operator's decision.
   - The risk gate never sees this diff: the commit creates the gate and touches `AGENTS.md`, `.github/` and `workflow/`, which are all triggers. The approval in step 3 is the review that stands in for it.

5. **Close the one-time settings.** Now that the CI file is on the default branch, ask the operator to require the `workflow gates` check and the `risk-gate` commit status in branch protection. Requiring either before the bootstrap commit exists would block the installation with no gate able to report. Without both, later gates report but do not block — and a green risk decision must never stand in for failed tests.
   - In the default advisory policy the `risk-gate` status is green even when findings are reported, so the owner can merge and that merge accepts them. In a strict policy it stays red until an independent approval of the exact head exists.
   - The push triggers the `workflow gates` job on the default branch. In a repository with no tests yet the full-suite lane fails by design — a zero-test run is not a pass. Report that as the known bootstrap state; do not add a placeholder test or weaken the lane.

6. **Continue with intake** (§2 → §3) in the same session. Bootstrap is complete; do not stop to ask whether to begin.

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
- Write the one-page digest to `docs/process/DIGEST.md`. **Stop here and wait for the operator.** That approval is the only approval before execution. It also carries one line each of merge mode (`human` or `auto`) and review mode (`advisory`, `risk-triggered` or `human`). Propose `auto` or a strict review mode only with the operator's explicit approval, then set it in `workflow/config.json`.

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
5. `python3 workflow/scripts/risk-gate.py --base main` — `pass` or `advisory` means merge may proceed: advisory findings are reported and the owner accepts them by merging. `blocked` means a strict review mode is configured and needs an independent approval of the exact head. This local run cannot see approvals; CI re-decides on `pull_request` and `pull_request_review` and publishes the verdict as the `risk-gate` status on the head commit.
6. `python3 workflow/scripts/close-wp.py --wp WP-nnn --base main` — appends the changelog line, regenerates the ledger index, validates both, writes the declaration.
7. Merge per `workflow/config.json` mode, following `workflow/REVIEW.md` §1.1. In `mode.merge: human` the owner reviews and merges the PR; in `auto` the agent merges only when every required check and the `risk-gate` status are green on the head being merged. Nothing in the kit merges by itself. Do not start the next package in the same turn unless the operator asked for a batch.

## 6. When something blocks

- A missing requirement: stop, record the question in the digest, ask. Do not invent it.
- A spec gap: `[CONFLICT]` + decision entry; a versioned spec revision, never roadmap-local invention.
- A limit reached: checkpoint, report the exact remaining step. Do not claim completion.
- A material risk finding: in the default advisory mode report it and continue to the owner's merge decision; in a strict review mode stop and request an independent approval. A verification failure always blocks; a risk report never excuses one.
