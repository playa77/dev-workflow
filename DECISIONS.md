<!-- decision-ledger | v2.0.0 | 2026-10-25 | initial -->
# Decision ledger

Write an entry when **any** of these is true:

1. it constrains work beyond this package;
2. reversing it would cost more than a day, or need a migration;
3. someone will ask "why is it like this?" within six months.

Otherwise it belongs in the WP checkpoint, not here.

New entries go at the bottom. Corrections to an entry are allowed at any time
(typos, clarity, a stale fact, an added consequence). Changing **what was
decided** requires a new entry with `Supersedes`. The index below is generated
by `workflow/scripts/check-ledger.py --write`.

<!-- index:begin -->
| ID | Decision | Status | Date | WP |
|---|---|---|---|---|
| D-001 | Work packages are sized by reviewability, not token estimates | adopted | 2026-10-24 | intake |
| D-002 | Executability gates run before implementation, not only at review | adopted | 2026-10-24 | intake |
| D-003 | Shrinking packages to fit a context window or turn limit | rejected | 2026-10-24 | intake |
| D-004 | Accepting a green test run as evidence of test quality | rejected | 2026-10-24 | intake |
| D-005 | Model-generated delivery statistics | rejected | 2026-10-24 | intake |
| D-006 | Multi-agent orchestration beyond implementer and verifier | rejected | 2026-10-24 | intake |
| D-007 | Editing an existing test to make a change pass | rejected | 2026-10-24 | intake |
| D-008 | Allowing a required CI lane to be skipped | rejected | 2026-10-24 | intake |
| D-009 | Method files live under `workflow/`; generated artifacts under `docs/` | adopted | 2026-10-25 | WP-001 |
| D-010 | Work packages merge automatically when every gate is green, with risk triggers | adopted | 2026-10-25 | WP-001 |
| D-011 | The roadmap is generated with the spec, not on request | adopted | 2026-10-25 | WP-001 |
| D-012 | Review cadence is milestone-based, not per-package | adopted | 2026-10-25 | WP-001 |
| D-013 | No rollout repository designated before fixtures pass | adopted | 2026-10-25 | WP-001 |
| D-014 | The interview exits on a coverage map, not a confidence percentage | adopted | 2026-10-25 | WP-001 |
| D-015 | One append-only ledger file at the repo root, not per-file ADRs | adopted | 2026-10-25 | WP-001 |
| D-016 | The changelog is a method artifact, correlated with the ledger | adopted | 2026-10-25 | WP-001 |
| D-017 | Enforcement is machine-checked or agent-verified; human-gated is removed | adopted | 2026-10-25 | WP-001 |
| D-018 | Human input is limited to the interview, the digest and risk triggers | adopted | 2026-10-25 | WP-001 |
| D-019 | Commands are generated into `workflow/config.json`, not written in a table | adopted | 2026-10-25 | WP-001 |
| D-020 | Documents 1–3 are generated in one pass, with no per-document approvals | adopted | 2026-10-25 | WP-001 |
<!-- index:end -->

---

### D-001 — Work packages are sized by reviewability, not token estimates

- **Date:** 2026-10-24
- **Status:** adopted
- **WP:** intake
- **Changelog:** expected
- **Revisit if:** review consistently takes under ten minutes or over ninety

**Context.** Packages sized to fit a context window produced both un-reviewable
diffs and premature splitting; the binding constraint in practice is how fast a
human can verify a diff against a checklist.

**Decision.** A work package must be reviewable in one pass against its
acceptance checklist. Token consumption is not a sizing input.

**Alternatives considered.**
- *Size by context window* — rejected: it optimises the wrong budget and
  produces un-reviewable partial deliveries. Revisit if: the execution
  environment enforces a hard per-run cap that cannot be raised.
- *Size by file count* — rejected: unrelated to the reviewer's cost.

**Consequences.**
- Good: review cost is bounded by design rather than discovered later.
- Bad: some packages exceed a single context window and must be resumed.

---

### D-002 — Executability gates run before implementation, not only at review

- **Date:** 2026-10-24
- **Status:** adopted
- **WP:** intake
- **Changelog:** expected
- **Revisit if:** the structural checks miss a seam defect that the verifier then catches twice

**Context.** Coverage matrices and traceability tables pass for specifications
whose modules cannot reach each other.

**Decision.** Composition root, seam register, call traces, caller existence and
type closure are delivery gates. A gap is a `[CONFLICT]`, not a note.

**Alternatives considered.**
- *Check only at review* — rejected: the defect is cheapest to fix before code
  exists. Revisit if: the verifier consistently finds what the checks miss.
- *Rely on the coverage matrix alone* — rejected: internal consistency is not
  executability.

**Consequences.**
- Good: unreachable modules and undefined types are caught on paper.
- Bad: the specification takes longer to produce and can block a roadmap.

---

### D-003 — Shrinking packages to fit a context window or turn limit

- **Date:** 2026-10-24
- **Status:** rejected
- **WP:** intake
- **Changelog:** none (nothing shipped)
- **Revisit if:** a package cannot be checkpointed at any boundary, or the platform enforces a cap that cannot be raised

**Context.** The obvious response to a long package is to split it until it fits.
That produces coordination overhead and partial deliveries.

**Decision.** Not adopted. Checkpoints solve state hygiene; splitting is for
reviewability and uncertainty, not for token budgets.

**Alternatives considered.**
- *Checkpoint and continue* — chosen. State survives interruption; scope does not shrink.

**Consequences.**
- Good: packages stay whole and reviewable.
- Bad: a package can span more than one session.

---

### D-004 — Accepting a green test run as evidence of test quality

- **Date:** 2026-10-24
- **Status:** rejected
- **WP:** intake
- **Changelog:** none (nothing shipped)
- **Revisit if:** never. Use the mechanisms in `workflow/VERIFICATION.md`

**Context.** A weak test and a strong test both exit zero.

**Decision.** Not adopted. The test diff is the evidence, not the exit code.

**Alternatives considered.**
- *Test-integrity mechanisms* — chosen: hashing, deltas, no-assert lint,
  diff coverage, scoped mutation, stash-check.

**Consequences.**
- Good: a weakened test is visible.
- Bad: verification is slower than reading a green summary.

---

### D-005 — Model-generated delivery statistics

- **Date:** 2026-10-24
- **Status:** rejected
- **WP:** intake
- **Changelog:** none (nothing shipped)
- **Revisit if:** never. Statistics are machine-generated from git

**Context.** A model reporting its own additions and deletions is exactly the
claim the reporting rule exists to distrust.

**Decision.** Not adopted. `wp-stats.sh` generates the numbers.

**Alternatives considered.**
- *Agent-reported statistics* — rejected: unauditable.

**Consequences.**
- Good: numbers match the diff by construction.
- Bad: one more script to run at close.

---

### D-006 — Multi-agent orchestration beyond implementer and verifier

- **Date:** 2026-10-24
- **Status:** rejected
- **WP:** intake
- **Changelog:** none (nothing shipped)
- **Revisit if:** a package decomposes into genuinely independent units and review capacity exists to absorb the output

**Context.** Cost scales faster than output as agents are added; coordination
dominates the work.

**Decision.** Not adopted. Two roles: implementer and fresh-context verifier.

**Alternatives considered.**
- *Planner, reviewer, documenter and coordinator in addition* — rejected:
  reported cost multiplier without proportional output.

**Consequences.**
- Good: the pipeline stays debuggable.
- Bad: less parallelism on genuinely independent work.

---

### D-007 — Editing an existing test to make a change pass

- **Date:** 2026-10-24
- **Status:** rejected
- **WP:** intake
- **Changelog:** none (nothing shipped)
- **Revisit if:** an explicit operator instruction, recorded in this ledger, with the reason

**Context.** The cheapest way to green is to weaken the assertion.

**Decision.** Not adopted. A test change requires justification in the declaration.

**Alternatives considered.**
- *Add a new test, leave the old one failing until the behaviour is fixed* — chosen.

**Consequences.**
- Good: regressions cannot be edited away.
- Bad: some red runs stay red longer.

---

### D-008 — Allowing a required CI lane to be skipped

- **Date:** 2026-10-24
- **Status:** rejected
- **WP:** intake
- **Changelog:** none (nothing shipped)
- **Revisit if:** never

**Context.** A skipped lane is indistinguishable from a lane that would have failed.

**Decision.** Not adopted. A skipped required lane fails the gate.

**Alternatives considered.**
- *Warn and continue* — rejected: normalises the failure.

**Consequences.**
- Good: the gate means what it says.
- Bad: infrastructure failures block delivery until fixed.

---

### D-009 — Method files live under `workflow/`; generated artifacts under `docs/`

- **Date:** 2026-10-25
- **Status:** adopted
- **WP:** WP-001
- **Changelog:** expected
- **Revisit if:** agents repeatedly fail to find the method files, or a tool requires `docs/` for them

**Context.** The first version dropped six directories at the repository root and
overwrote `README.md` and `AGENTS.md` on install. Root should hold the project's
files, not the method's internals.

**Decision.** One method directory, `workflow/`. Generated project artifacts stay
in `docs/{design,spec,roadmap,wp,process}`. Root holds `README.md`, `AGENTS.md`,
`DECISIONS.md`, `CHANGELOG.md`, `workflow/`, `docs/` and `.github/`.

**Alternatives considered.**
- *Everything at root* — rejected: collides with the project's own files and
  makes install destructive. Revisit if: never.
- *Hidden `.workflow/`* — rejected: ripgrep and several agent file-search tools
  skip dot-directories, so the agent would not find the rules. Revisit if:
  the tooling changes.

**Consequences.**
- Good: install writes one directory plus two marker blocks.
- Bad: every path in every document changes once.

---

### D-010 — Work packages merge automatically when every gate is green, with risk triggers

- **Date:** 2026-10-25
- **Status:** adopted
- **WP:** WP-001
- **Changelog:** expected
- **Revisit if:** two post-merge defects escape the risk triggers within ten work packages

**Context.** Human merge review cost 30–60 minutes per package — the largest and
least replaceable cost in the method. Most packages touch no risk-bearing surface.

**Decision.** Merge automatically when every lane is green, the verifier returns
`pass`, and `risk-scan.py` reports no trigger. A human is still required for
auth/authz/crypto, migrations and data deletion, billing, secrets, dependency
manifests and lockfiles, CI configuration, public API changes, any modified or
deleted test, and any change to `AGENTS.md` or `workflow/`.

**Alternatives considered.**
- *Human merge gate on every package* — rejected: the cost above, and the
  trigger list covers the classes where review catches defects. Revisit if: a
  defect escapes the triggers twice.
- *Auto-merge with no triggers* — rejected: security and data-loss changes would
  reach main on a green test run, which is not evidence of safety. Revisit if: never.

**Consequences.**
- Good: the operator's time goes to the interview and the digest.
- Bad: detection latency replaces review latency for defects no test catches.

---

### D-011 — The roadmap is generated with the spec, not on request

- **Date:** 2026-10-25
- **Status:** adopted
- **WP:** WP-001
- **Changelog:** expected
- **Revisit if:** roadmap generation proves to be the dominant cost of the spec pass

**Context.** An optional roadmap produced only on request leaves the first
execution session inventing its own decomposition.

**Decision.** Documents 1, 2 and 3 are produced in one pass. The roadmap is the
execution plan, not a separate approval.

**Alternatives considered.**
- *Keep Doc 3 optional* — rejected: it defers the decomposition to the least
  informed moment. Revisit if: the cost above materialises.

**Consequences.**
- Good: the first work package starts from a complete plan.
- Bad: the spec pass is longer.

---

### D-012 — Review cadence is milestone-based, not per-package

- **Date:** 2026-10-25
- **Status:** adopted
- **WP:** WP-001
- **Changelog:** expected
- **Revisit if:** two milestones pass with no human reading a diff and defects accumulate

**Context.** Per-package human reading was the dominant recurring cost and the
research on review capacity shows it degrades into rubber-stamping.

**Decision.** Human review is risk-triggered per package and otherwise sampled at
milestones, using the one-page digest produced by `close-wp.py`.

**Alternatives considered.**
- *Per-package diff review* — rejected: 5–10 hours per ten packages, and the
  attention is not uniform. Revisit if: the trigger list proves too narrow.
- *No human review at all* — rejected: risk-bearing changes need judgement that
  no check provides. Revisit if: never.

**Consequences.**
- Good: review happens where it changes outcomes.
- Bad: some defects are found after merge rather than before.

---

### D-013 — No rollout repository designated before fixtures pass

- **Date:** 2026-10-25
- **Status:** adopted
- **WP:** WP-001
- **Changelog:** none (process decision)
- **Revisit if:** the fixture and scratch-install suites pass and a candidate project is chosen

**Context.** Installing v2 into a real repository before the clobber, gate and
migration tests pass would repeat the failure that prompted the rewrite.

**Decision.** Prove v2 on fixture repositories and a scratch install first. No
real project is designated yet.

**Alternatives considered.**
- *Pilot immediately on a live repo* — rejected: destructive install bugs would
  be discovered at the worst moment. Revisit if: the suite is green.

**Consequences.**
- Good: the first real install is tested.
- Bad: adoption is delayed by the test pass.

---

### D-014 — The interview exits on a coverage map, not a confidence percentage

- **Date:** 2026-10-25
- **Status:** adopted
- **WP:** WP-001
- **Changelog:** expected
- **Revisit if:** a project reaches `open == 0` and still produces a spec that misses a confirmed requirement twice

**Context.** Verbalized confidence is inflated, top-skewed and heavily
discretised on a 0–100 scale; prompting alone does not produce calibration. A
single judgement about understanding a future system has no answer key and
cannot be audited.

**Decision.** The interview tracks twelve topics with statuses
`answered | answered_by_repo | defaulted | deferred | open`. It exits when
`open == 0`, with `check-intake.py` enforcing the structure. No percentage.

**Alternatives considered.**
- *Keep ≥95% confidence* — rejected: unmeasurable and empirically inflated.
  Revisit if: never.
- *Unbounded questions until the agent is satisfied* — rejected: produces
  strategy meetings and under-asking in equal measure.

**Consequences.**
- Good: the exit condition is countable and checkable.
- Bad: the map can be complete while understanding is still shallow — hence the
  digest and the assumption register.

---

### D-015 — One append-only ledger file at the repo root, not per-file ADRs

- **Date:** 2026-10-25
- **Status:** adopted
- **WP:** WP-001
- **Changelog:** expected
- **Revisit if:** the ledger passes 150 entries and single-file retrieval measurably slows

**Context.** The ADR literature recommends one file per decision. For
agent-driven work the retrieval path is a search, and a directory of records
needs an index that drifts from the records.

**Decision.** One `DECISIONS.md` at the root, entries appended in ID order,
rejected options recorded inside the entry that rejected them, a generated index
at the top. Corrections are allowed; changing a decision requires a new entry
with `Supersedes`.

**Alternatives considered.**
- *`docs/adr/NNNN-*.md` per file* — rejected: needs an index, conflicts less but
  retrieves worse for an agent, and at tens of decisions the directory is pure
  overhead. Revisit if: the ledger outgrows a single file.

**Consequences.**
- Good: one search covers the whole decision history.
- Bad: parallel packages can conflict when both append.

---

### D-016 — The changelog is a method artifact, correlated with the ledger

- **Date:** 2026-10-25
- **Status:** adopted
- **WP:** WP-001
- **Changelog:** expected
- **Revisit if:** changelog upkeep becomes the step that is consistently skipped at close

**Context.** A changelog written after the fact is the step that falls off under
deadline. The ledger and the changelog answer different questions and drift
apart when neither cites the other.

**Decision.** Root `CHANGELOG.md`, Keep a Changelog 1.1.0, SemVer (milestone
headings allowed). Every line cites `(D-nnn, WP-nnn)`. The WP brief carries a
"user-visible effect" field, so the entry is written from data that already
exists.

**Alternatives considered.**
- *Generate from commit subjects* — rejected: commit messages are written for
  reviewers, not users, and the result is noise. Revisit if: never.
- *No changelog* — rejected: the operator cannot see what shipped.

**Consequences.**
- Good: the changelog is a by-product of close, not a separate task.
- Bad: one more field in the brief.

---

### D-017 — Enforcement is machine-checked or agent-verified; human-gated is removed

- **Date:** 2026-10-25
- **Status:** adopted
- **WP:** WP-001
- **Changelog:** expected
- **Revisit if:** a rule survives three packages with neither a check nor an agent verification

**Context.** The first version's principle — "machine-checked or human-gated with
named evidence" — made "a human looks at it" an acceptable enforcement
mechanism, which is why mechanical steps kept routing to the operator.

**Decision.** Every rule is enforced by a named machine check or by a named agent
check that produces named evidence. Human judgement is reserved for intent (the
interview), the constraint ledger (the digest) and risk acceptance (triggers).

**Alternatives considered.**
- *Keep human gates as an enforcement class* — rejected: the gate becomes the
  place where work accumulates. Revisit if: a gate cannot be mechanised and is
  load-bearing.

**Consequences.**
- Good: the human is asked only where judgement is irreplaceable.
- Bad: removing a gate without a check is now a defect, and must be caught in review.

---

### D-018 — Human input is limited to the interview, the digest and risk triggers

- **Date:** 2026-10-25
- **Status:** adopted
- **WP:** WP-001
- **Changelog:** expected
- **Revisit if:** the operator spends more than two hours per milestone on the method

**Context.** Nineteen human steps existed across install, phase gates, per-package
approvals, conflict resolution, exceptions, checklist signing and ledger upkeep.

**Decision.** Four approvals become one: the interview answers, the one-page spec
digest, risk-triggered PR review, and changes to the constraint ledger or the
method itself. Everything else is agent work or a script.

**Alternatives considered.**
- *Keep per-document and per-package approvals* — rejected: reading cost with no
  proportional defect detection. Revisit if: the digest misses a constraint.

**Consequences.**
- Good: the operator's attention is concentrated where it changes the outcome.
- Bad: errors that a human would have caught in a per-package read can reach main.

---

### D-019 — Commands are generated into `workflow/config.json`, not written in a table

- **Date:** 2026-10-25
- **Status:** adopted
- **WP:** WP-001
- **Changelog:** expected
- **Revisit if:** autodetection fails on more than one stack in a row

**Context.** The command table was a human step, and CI ignored it, hardcoding
`make test`.

**Decision.** The installer detects the stack and writes `workflow/config.json`;
`check-config.py` fails closed on an unresolved role. Documents refer to roles,
never literals.

**Alternatives considered.**
- *Keep the table* — rejected: a human step that the CI did not even read.
  Revisit if: detection cannot cover a required stack.

**Consequences.**
- Good: one source for commands, used by CI and scripts.
- Bad: a new adapter is needed for each unrecognised stack.

---

### D-020 — Documents 1–3 are generated in one pass, with no per-document approvals

- **Date:** 2026-10-25
- **Status:** adopted
- **WP:** WP-001
- **Changelog:** expected
- **Revisit if:** a spec produced in one pass is approved and then needs a constraint-level revision twice

**Context.** Three sequential approvals meant reading three long documents at
three times, with the reasoning split across them; the packaged successors of
this pipeline removed the intermediate gates in favour of front-loaded questions.

**Decision.** One spec pass produces `DESIGN.md`, `SPEC.md` and `ROADMAP.md`. The
human approves the one-page digest, not the documents.

**Alternatives considered.**
- *Keep Doc 1 and Doc 2 approvals* — rejected: reading load without a matching
  defect catch. Revisit if: a missed constraint reaches implementation twice.

**Consequences.**
- Good: one decision point instead of four.
- Bad: a wrong constraint propagates through three documents before review.

---
