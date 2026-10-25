<!-- digest | <YYYY-MM-DD> | v<spec version> -->
# Spec digest — <project>

The one page the operator approves. Everything else in Docs 1–3 exists for the agent.

## What is being built

<One paragraph a stranger could act on.>

## Constraint ledger (Doc 1 §2)

| # | Constraint | Testable as |
|---|---|---|
| C-1 | <constraint> | <check or measurement> |

## Non-goals

- <what this explicitly will not do>

## Deferred

| Question | Default used now | Resolved by |
|---|---|---|
| <question> | <default> | `WP-<nnn>` |

## Assumptions at risk

| Assumption | If wrong | Blast radius |
|---|---|---|
| <assumption> | <consequence> | `local` \| `architectural` |

## Decisions taken

| ID | Decision |
|---|---|
| `D-<nnn>` | <one line> |

## Operating mode

| Setting | Value | Effect |
|---|---|---|
| `mode.merge` | `human` (default) | The agent opens the PR; the owner reviews and merges it. `auto` is an explicit opt-in. |
| `mode.review` | `advisory` (default) | CI reports risk findings; the owner's merge accepts them. `risk-triggered` or `human` requires an independent approval on the exact head and is an explicit opt-in. |

Changing either value is an operator decision; state it here before execution.

## Approve

Reply with `approve`, or list corrections. Silence is not approval.
