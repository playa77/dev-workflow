<!-- spec-sections | v2.0.0 | 2026-10-25 | loaded on demand by the spec prompt -->
# Spec sections — Doc 1, Doc 2, Doc 3

Load this file when writing the spec pass. It is deliberately separate from the prompt: a prompt carrying every section at once gets worse compliance, so the prompt carries the gates and this file carries the shape.

## Document 1 — Design Document

`docs/design/DESIGN.md`

1. **Overview and Goals** — what this is, what success means, what it is not.
2. **Requirements Summary** — the constraint ledger. Functional, non-functional, and hard constraints as testable propositions. Every later section is bound by this one.
3. **System Architecture** — components, responsibilities, data flow, trust boundaries. A diagram plus prose that stands alone.
4. **Component Responsibilities** — per component: owns, does not own, depends on, is depended on by.
5. **Data Model** — entities, relationships, invariants, lifecycle, retention.
6. **API and Interface Design** — surfaces, contracts, error semantics. Signatures and schemas, not implementations.
7. **Security Architecture** — trust boundaries, authN/authZ, secrets, sensitive data, threat model.
8. **Infrastructure and Deployment** — environments, topology, configuration surface, rollout and rollback.
9. **Operational Model** — observability, alerting, failure modes, runbook-level expectations, capacity.
10. **Key Design Decisions** — each with alternatives, reason, cost accepted, and the `D-nnn` ID.
11. **Open Questions and Assumptions** — tagged, with risk and the WP that resolves each.

Before delivering: re-read §2 against §§3–10 and name the section that honours each constraint. A section that designs against a constraint is a defect: fix it or record `[CONFLICT]`.

## Document 2 — Technical Specification

`docs/spec/SPEC.md`

1. **Implementation Scope** — what is built, and explicitly what is not.
2. **Project Structure** — directory layout with the purpose of each path.
3. **Dependencies** — runtime and development, with the reason for each.
4. **Configuration** — every setting, type, default, secrecy, source.
5. **Data Layer** — DDL, migrations, indexes, transaction boundaries, access patterns.
6. **API Specification** — endpoints, methods, request/response schemas, status codes, error bodies.
7. **AuthN/AuthZ** — identity, session or token lifecycle, permission model, enforcement points.
8. **Module Specifications** — per module: responsibility, public interface, dependencies, invariants, failure behaviour.
9. **Background Jobs** — trigger, schedule, idempotency, retry, dead-letter, observability.
10. **Observability** — logs, metrics, traces, the question each answers, alert thresholds.
11. **Error Handling** — taxonomy, boundary behaviour, retry vs fail, user-visible messages.
12. **Testing Strategy** — levels, fixture policy, the test-construction rule, how a regression test is proven.
13. **Build/Run/Deploy** — exact commands, environments, artefacts, promotion.
14. **Acceptance Criteria** — project-level, objective, testable.
15. **Seam Register and Call Traces** — mandatory; see below.
16. **Final Consistency Checklist** — completed, not left as a template.

### §12 test-construction rule (verbatim)

> A test may not hand-build the state the code under test is supposed to produce. Pre-existing state is established by calling the production path, never by direct fixture writes. A test that pre-builds its inputs verifies arithmetic while proving nothing about whether the pipeline can produce them.

### §15 executability record

Three parts, all required:

**Composition root.** The single module that constructs components. No other module instantiates infrastructure. Two modules building the database client means there are two roots and therefore none.

**Seam register**, built from the call traces below, not from the module list:

| From | To | Constructor or invoker | Data crossing | State residence |
|---|---|---|---|---|

**Call traces.** For each primary runtime path: entry point → every call → committed state. Note where state resides at every process boundary (memory, request scope, database, queue, cache, file). A trace ending at "returns a response" without naming the committed state is incomplete.

### §16 checklist

| Check | Result |
|---|---|
| Every Doc 1 §2 constraint is honoured by a named section here | |
| Every module in §8 appears in at least one call trace | |
| Every type named in a signature is defined in this document | |
| Every specified module, function and type has a named caller or constructor | |
| Every contract consumed by a work package exists here or in an earlier package | |
| No section assumes a capability excluded by a Doc 1 constraint | |
| No placeholders remain | |

Three rules that catch most real defects: caller existence, type closure, constraint honouring. **Internal consistency is not executability** — run the traces.

## Document 3 — Implementation Roadmap

`docs/roadmap/ROADMAP.md`

1. **Roadmap Overview** — strategy, phase sequence, consumption model (one WP per session, dependency order).
2. **Global Conventions** — bootstrap order, branch/commit conventions, versioning, definition of done.
3. **Dependency Graph** — full WP index with `depends-on`; acyclic; parallelisable WPs marked with what makes them independent.
4. **Work Packages** — per WP: ID, title, phase, depends-on, type, objective, rationale, scope (paths per Doc 2 §2), out of scope, spec references, task list, contracts consumed/produced, acceptance criteria (3–8), verification commands, review cost, sizing.
5. **Milestones and Integration Checkpoints** — where the system must build and run end to end, with the smoke procedure.
6. **Coverage and Traceability Matrix** — every Doc 2 §1 scope item and §8 module mapped to at least one WP; union equals 100% of scope, nothing beyond.
7. **Completion Criteria** — project definition of done; mirrors Doc 2 §14.

Gates: the DAG is acyclic; no WP consumes a contract not produced earlier or defined in Doc 2; the coverage matrix is complete; each WP is self-contained given Docs 1 and 2; the roadmap never silently extends the spec — a gap triggers a versioned Doc 2 revision.

## Voice

Prefer tables for repeated structure. Sections are self-contained. No "and so on", no "the rest". A reader who reads one section must not need another to understand it.
