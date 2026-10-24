<!-- measurement-spec | v2.0.0 | 2026-10-25 | agent-generated ledger; no operator memory -->
# Measurement — calibration, digest, retro

**Status:** Approved · **Owner:** Operator · **Consumer:** agent writes, operator reads at milestones · **Normative for:** per-WP telemetry, calibration, retro

The roadmap's sizing is a hypothesis. This document is how it gets corrected and how process decay is detected.

---

## 1. What is measured

| Field | Source | Answers |
|---|---|---|
| `wp`, `type` | brief | which kinds of package misbehave |
| `planned_review_cost` | brief | one pass or spanning sessions |
| `wall_hours` | first commit → close | elapsed effort |
| `active_hours` | agent-reported, marked | effort vs elapsed |
| `tool_calls` | agent-reported, marked | exploration cost |
| `interruptions` | checkpoint count | how often state was rebuilt |
| `rework_commits` | commits after the first red full run | how much was redone |
| `review_round_trips` | PR comments requesting change | friction |
| `review_latency_h` | close → merge | the real bottleneck |
| `tests_added` | `wp-stats.sh` | verification growth |
| `test_files_touched` | `wp-stats.sh` | churn in the suite |
| `loc_net_impl`, `loc_net_tests` | `wp-stats.sh` | growth by category |
| `verify_seconds` | `TEST_FULL` duration | whether validation is affordable |
| `risk_triggers` | `risk-scan.py` | how often human review is demanded |

Self-reported fields are marked in the ledger. Machine fields are generated. Never mix them without the marker. **No field depends on the operator's memory.**

## 2. Ledger

`workflow/process/CALIBRATION.csv`, one row per merged WP:

```csv
wp,type,planned_review_cost,wall_hours,active_hours,tool_calls,interruptions,rework_commits,review_round_trips,review_latency_h,tests_added,test_files_touched,loc_net_impl,loc_net_tests,verify_seconds,risk_triggers,self_reported
WP-001,deterministic,one-pass,6.5,4.2,140,1,0,1,18,9,1,420,180,95,none,active_hours;tool_calls
```

`close-wp.py --calibration` appends the row from git, CI and the checkpoint. Append-only; a missing value is an unanswered question, not a zero.

## 3. Reading it

| Signal | Threshold | Investigate |
|---|---|---|
| Review latency exceeding implementation time | 2 consecutive WPs | package too large, or review deferred |
| Rework commits | > 20% of commits | brief or verification path wrong |
| Interruptions | > 1 per WP | checkpoints too late, or package too big |
| Tests added per WP falling while scope holds | 3 WPs | verification traded away |
| `verify_seconds` doubling | once | suite becoming something people avoid |
| Review rounds | > 2 | acceptance criteria not testable enough |
| Risk triggers on most WPs | 3 in 10 | the trigger list is too broad, or the repo is high-risk and should merge by review |
| Same correction twice | any | a rule belongs in `AGENTS.md` or a hook |

A signal is a prompt to look, not a verdict.

## 4. Milestone digest

At each milestone (three merged WPs, then every milestone in the roadmap), the agent produces one page in the PR or `docs/process/MILESTONE-nn.md`:

1. **Are complete packages shipping?** Count with every criterion verified. Partial deliveries exceeding complete ones means sizing is wrong or gates are bypassed.
2. **Where did the time go?** Implementation, validation, review latency. The largest is where the next change goes.
3. **What did we stop doing?** Any step performed mechanically for three WPs with no decision riding on it. Retire it or say why it stays.
4. **Did the ledger stay useful?** Entries added, entries read (by citation), entries superseded. A ledger nobody cites is not load-bearing.

The operator reads this page at the milestone. That is the review cadence in D-012.

## 5. What this process refuses to measure

- Token estimates as a sizing input.
- Lines of code as productivity.
- Cumulative pass counts.
- Test count as a target.

## 6. Cadence

| When | What |
|---|---|
| Every merged WP | calibration row, changelog line |
| Every third WP | milestone digest |
| Any repeated correction | rule or hook, recorded as a decision |
| Release | version bump, changelog heading, tag |

## Revision history

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-10-24 | Initial. |
| 2.0.0 | 2026-10-25 | Agent-generated rows; risk-trigger field; milestone digest replaces the operator-answered retro. |
