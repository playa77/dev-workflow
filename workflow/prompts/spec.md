<!-- spec-prompt | v2.0.0 | 2026-10-25 | one pass, three files, no approvals between -->
# Phase 1 — Spec pass (Documents 1–3)

Input: an approved digest and `workflow/state/intake.json`. Output: `docs/design/DESIGN.md`, `docs/spec/SPEC.md`, `docs/roadmap/ROADMAP.md`.

Produce all three in one pass. There is no approval between them. Section lists, templates and examples: `workflow/references/spec-sections.md` — read it before writing.

## Non-negotiables

1. **Traceability.** Every detail traces to an operator requirement, a confirmed answer, `[ASSUMPTION]` or `[PROPOSED DESIGN DECISION]`. Untagged invention is a defect.
2. **Constraint supremacy.** Doc 1 §2 is the constraint ledger. Every later section of every document honours it. A capability the platform lacks does not become available because a later section needs it.
3. **Executability over internal consistency.** Traces, caller existence, type closure. A coverage table passes for a system whose modules cannot reach each other.
4. **No placeholders.** No TBD, no empty section. Unknown → `[ASSUMPTION]` with a risk, or a deferred question with a resolving WP.
5. **No invented services.** Anything not specified is `[PROPOSED DESIGN DECISION]` with a reason and an alternative.
6. **Minimal architecture.** Every complexity carries a `[COMPLEXITY JUSTIFICATION]` tied to a requirement.

## Order of work

1. Doc 1 from the digest and the intake state. §2 is the constraint ledger; write it first and re-read it before each later section.
2. Doc 2 from Doc 1. Produce §15 (composition root, seam register, call traces) **before** §16 and before the checklist.
3. Doc 3 from Doc 2. Build the WP index from the seam register and call traces, not from the module list.

## Decisions

- Every `[PROPOSED DESIGN DECISION]` that constrains future work, and every resolved `[CONFLICT]`, becomes a `D-nnn` entry in `DECISIONS.md`. Doc 1 §10 references the ID instead of repeating the prose.
- Corrections to an earlier entry are allowed; a changed decision is a new entry with `Supersedes`.
- If a requirement cannot be honoured, record `[CONFLICT]` with both sides quoted and the decision needed. Do not choose the convenient side.

## Before delivering

Run, and fix what they find:

```
python3 workflow/scripts/check-spec.py
python3 workflow/scripts/check-roadmap.py
python3 workflow/scripts/check-ledger.py --check
```

The checks are structural. They do not replace the executability trace: for each primary runtime path, walk entry point → every call → committed state, and confirm every callee has a named module, a named caller, defined types, and state that survives its process boundary.

## Exit

1. Write all three documents.
2. Update the digest with the constraint ledger, the deferrals and the riskiest assumptions.
3. Present the digest and **stop**. Do not begin execution without approval.
