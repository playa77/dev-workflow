<!-- execute-prompt | v2.2.0 | 2026-10-25 | ledger first; close writes changelog; risk report in the declaration -->
# Executor prompt — one work package

You are implementing exactly one work package. You have full authority inside its scope and none outside it.

## Read order

1. `AGENTS.md` — the rules. They override this prompt and the brief.
2. The index at the top of `DECISIONS.md`, then search it for the modules and paths you will touch.
3. The WP brief at `docs/wp/WP-nnn.md`.
4. The Doc 1 and Doc 2 sections the brief cites. Read them; do not reconstruct them from the code.
5. The existing code you will touch, and its neighbours.

Do not read the whole repository "for context".

## 1. Preflight (read-only)

Fill §11 of the brief: modules touched and why; unresolved dependencies; the verification path, confirmed by running the cheap commands; obstacles; whether the brief matches reality.

If the boundary is wrong — larger than it looked, depends on something unfinished, needs an architectural decision — **stop and report before writing code**. Flagging an impractical boundary is a successful outcome.

## 2. Implement

- Stay inside §3. §4 stays untouched, even if it is one line away.
- Follow the contracts in §5 and Doc 2 §8. A deviation is recorded and reported.
- Write the tests the package needs. A test may not hand-build the state the production path produces.
- Run `TEST_AFFECTED` continuously. Fix regressions this package introduced; record unrelated failures, do not fix them.
- Commit in coherent steps with Conventional Commit messages that say why.

## 3. Decisions

- If you make a choice that constrains future work, costs more than a day to reverse, or will be asked about in six months, append a `D-nnn` entry to `DECISIONS.md` **in this branch**, with context, alternatives and a revisit condition.
- Do not rewrite an earlier entry to mean something else. Use `Supersedes`.
- Local, reversible choices stay in `progress.md`.

## 4. Checkpoint

At each meaningful milestone and before any interruption, update `docs/wp/WP-nnn.progress.md` and `WP-nnn.state.json`. Evidence is a command and its result, never "works". `Next step` is one action. Record what you ruled out.

## 5. Under pressure

Do not reduce scope. Do not skip verification. Checkpoint, then continue. If a limit is genuinely reached, stop, checkpoint, report the exact remaining work. Never change model, reasoning effort or validation depth mid-package.

## 6. Close

Before declaring completion:

1. Every criterion has evidence on this head.
2. `TEST_FULL` ran on the exact head.
3. `check-test-integrity.sh --verify` passes, or every exception is recorded.
4. `check-caller-existence.py --base <base>` passes for new definitions.
5. `check-state.py` passes.
6. `python3 workflow/scripts/risk-gate.py --base <base>` has run and its mode, verdict and findings are recorded in §11 of the declaration. Advisory findings are reported and the owner accepts them by merging; a strict review mode needs an independent approval on this exact head.
7. `python3 workflow/scripts/close-wp.py --wp WP-nnn --base <base>` has run. It appends the changelog line if `user_visible`, regenerates the ledger index, validates both artifacts, and writes the declaration statistics.
8. `workflow/templates/PR.md` is filled completely.

## 7. Report

Lead with **complete** or **blocked**, and the criteria met vs outstanding. Then: what changed by category; verification commands and results; decisions and deviations with reasons; what was ruled out; known limitations; the single next action if blocked.

Do not describe the process. Do not narrate tool calls. Do not begin the next work package.
