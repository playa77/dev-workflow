<!-- delivery-declaration | WP-<nnn> | <YYYY-MM-DD> -->
# Delivery declaration — WP-<nnn>: <title>

> Numbers in §3 and evidence in §4 are **generated**, not typed. If a number here was written by hand, the declaration is invalid.

## 1. Status

`complete` | `partial` — instruction: "<quoted operator instruction>" | `blocked`

Branch: `<branch>` · Head: `<sha>` · Base: `<base> @ <sha>`

## 2. Acceptance

| # | Criterion | Evidence (command and result) | Pass |
|---|---|---|---|
| 1 | <from WP §6> | `<command>` → `<result>` | yes |

Every criterion appears here, with the same numbering as the brief. No criterion passes on a summary.

## 3. Delivery statistics (generated)

Paste the output of `workflow/scripts/wp-stats.sh --base <base> --committed`, unedited.

```
<generated table>
```

## 4. Test integrity

| Mechanism | Result | Note |
|---|---|---|
| Baseline snapshot | `<pass / not run>` | `workflow/state/test-baseline.json` at `<sha>` |
| Modified test files | `<none \| list>` | each with justification below |
| Test definition delta | `<before → after>` | |
| Skip markers | `<before → after>` | |
| No-assert lint | `<pass \| findings>` | |
| Diff coverage | `<percent>` | |
| Mutation, changed lines | `<score \| inconclusive \| skipped>` | budget: `<n>`s |
| Stash-check | `<proof \| not-applicable \| FAILED>` | selector: `<sel>` |

Any test added, modified, renamed or removed is listed here. A change without a justification is a failed declaration.

## 5. Verification runs

| Stage | Command | Revision | Result | Duration |
|---|---|---|---|---|
| affected | `<command>` | `<sha>` | `<pass/fail>` | `<n>s` |
| full (candidate) | `<command>` | `<sha>` | `<pass/fail>` | `<n>s` |
| lint | `<command>` | `<sha>` | `<pass/fail>` | `<n>s` |

The candidate revision in the full run must equal the head being delivered.

## 6. Deviations and exceptions

<None, or what deviated, why, and the compensating control. An agent-granted exception names mechanism, reason and control; a risk-triggered exception names the operator approval.>

## 7. Decisions

| Decision | New or relied on | Reason |
|---|---|---|
| `D-<nnn>` | `<new \| relied on>` | `<why>` |

## 8. Ruled out

| Option | Why rejected | Reopen if |
|---|---|---|
| `<option>` | `<reason>` | `<condition>` |

## 9. Known limitations

<What this package does not do, stated plainly. "None" is valid only if true.>

## 10. Verifier verdict

Filled by the fresh-context verifier (`workflow/prompts/verify.md`), not by the implementer.

| Criterion | Evidence supports it? | Gap |
|---|---|---|
| 1 | `<yes / no / insufficient>` | `<none \| what is missing>` |

Verdict: `<pass | fail | needs-evidence>`

## 11. Risk scan

Output of `python3 workflow/scripts/risk-scan.py --base <base> --fail-on-trigger`:

```
<triggers: none | list>
requires_human: <true | false>
exit: <0 | 1>
```

If `requires_human` is true, the CI risk lane fails, the PR is labelled `needs-human`, and it is not merged automatically.
