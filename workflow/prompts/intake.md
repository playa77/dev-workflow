<!-- intake-prompt | v2.0.0 | 2026-10-25 | coverage map; no confidence percentage -->
# Phase 0 — Intake

**Goal:** a complete coverage map of what is being built, with every unresolved topic closed by an answer, a default with a blast radius, or a deferral with a resolving work package. **No design.**

## Rules

- **Recon before questions.** Read the brief, the repository, its manifest, its CI and the last fifty commits. Any topic you can answer from evidence is `answered_by_repo` with a file path — do not spend a question on it.
- **At most twelve questions for a project**, in rounds of up to three, in one message.
- Every question is **answerable by a letter or one line**. Give 2–4 concrete options and mark the recommended one with one sentence of why.
- Every question states **what happens if the answer is wrong** — the cost, not the stakes in the abstract.
- Do not ask what you can defer. If a decision can wait for a named work package without rework, record `deferred` with its default and the resolving WP.
- Do not assume an answer because it is conventional. Default it, name the blast radius, and move on.
- If the brief already answers a topic, confirm it in one line.
- **No architecture, components, schemas or technology choices in this phase.** If you need options to elicit a requirement, present them as questions about intent.

## Coverage

Use `workflow/templates/intake.json`; the twelve topics are fixed:

`purpose, users, scope, data, integrations, security, infrastructure, performance, budget, technology, operations, non_goals`

Statuses:

| Status | Requires |
|---|---|
| `answered` | the answer, in the operator's words where possible |
| `answered_by_repo` | the file path that answers it |
| `defaulted` | `default`, `blast_radius` (`local` / `architectural`), `revisit_if` |
| `deferred` | the three above, plus `resolved_by: WP-nnn` |
| `open` | nothing — blocks the phase |

## Techniques

- **Inversion.** "What would make this fail?" "What would make us regret this in a year?"
- **Blast radius.** "If this is wrong, what else breaks?"
- **Boundary probing.** "Where does this system's responsibility end?" — test both sides.
- **Concreteness.** Replace adjectives with numbers: "fast" → "p95 under X ms at Y rps".
- **Silence hunting.** The topic the operator has not mentioned is usually the expensive one.

## Exit

When `open == 0` and `python3 workflow/scripts/check-intake.py` passes:

1. Write `workflow/state/intake.json`.
2. Write the one-page digest from `workflow/templates/digest.md` to `docs/process/DIGEST.md`: what is being built, the constraint ledger, non-goals, deferrals, the riskiest assumptions, and the decisions taken so far (as `D-nnn` entries in `DECISIONS.md`).
3. Present the digest and **stop**. Do not begin the spec pass in the same turn.

If the operator corrects the digest, update the topics and the digest, re-run the check, and present again. Do not proceed on silence.
