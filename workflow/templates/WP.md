<!-- wp-brief | WP-<nnn> | <YYYY-MM-DD> | proposed -->
# WP-<nnn> — <title>

| Field | Value |
|---|---|
| Type | `<deterministic \| exploratory \| architectural \| spike>` |
| Phase | `<roadmap phase>` |
| Depends on | `WP-<nnn> (completed), ...` |
| Branch | `feat/wp-<nnn>-<slug>` |
| Base | `<main> @ <sha>` |
| Spec refs | `Doc 1 v<x.y> §<n>` · `Doc 2 v<x.y> §§<n>,<n>` |
| Review cost | `<one pass \| spans sessions>` |
| User-visible effect | `<one sentence, or "none">` |
| Decisions expected | `<D-nnn, ...>` or `none` |
| Status | `proposed` |

## 1. Objective

<One sentence. What is true after this package that was not true before.>

## 2. Rationale

<Which requirement in Doc 1 §2 this serves, and why the package exists as a unit.>

## 3. Scope

Files and modules created or modified, using paths from Doc 2 §2:

- `<path>` — <what changes>

## 4. Out of scope

- <explicitly excluded behaviour>

Out-of-scope items are not "later". If one is required for the objective, the boundary is wrong: flag it before starting.

## 5. Contracts

**Consumed** (must exist from a prior WP or Doc 2):

| Contract | Provided by | Runtime requirement |
|---|---|---|
| `<interface / table / credential / module>` | `WP-<nnn>` | `<reachable module, populated data, ...>` |

**Produced** (available to later WPs):

| Contract | Defined in | Consumed by |
|---|---|---|
| `<interface>` | `<path>` | `WP-<nnn>` |

## 6. Acceptance criteria

Objective and testable. Three to eight. Each maps to evidence in §7.

1. <condition>

## 7. Verification

| # | Command or check | Expected result |
|---|---|---|
| 1 | `<command>` | `<exit 0, N passed>` |
| 2 | `python3 workflow/scripts/check-caller-existence.py --base <base>` | `ok` |
| 3 | `bash workflow/scripts/check-test-integrity.sh --verify` | `ok` |

The pre-merge run is authoritative: `TEST_FULL` on this exact revision.

## 8. Prohibited in this package

- Editing, deleting, weakening or skipping an existing test without flagging it in the declaration.
- Building state in a test that the production path is supposed to produce.
- Adding a dependency not listed in Doc 2 §3.
- Changing model, reasoning effort or validation depth mid-package.
- Fixing an unrelated defect "while here". Report it; do not absorb it.
- Starting the next work package.

## 9. Recovery

Maintain `docs/wp/WP-<nnn>.progress.md` and `WP-<nnn>.state.json` (schemas in `workflow/STATE.md`).

If interrupted: preserve the working tree, record verified and unverified criteria with their evidence, record the last test run, state the single next step.

## 10. Completion

Complete when every criterion in §6 has evidence in §7, the changelog line is written (or `user-visible effect: none`), and the declaration from `workflow/templates/PR.md` is complete.

Do not begin the next work package.

---

## 11. Preflight

*Completed by the executor before the first code change. Read-only.*

- **Modules that will be touched:** <list, with why>
- **Unresolved dependencies:** <none | list>
- **Verification path:** <commands actually available, confirmed by running the cheap ones>
- **Obstacles or boundary concerns:** <none | flag before starting>
- **Assessment against the brief:** <consistent | differs because ...>
