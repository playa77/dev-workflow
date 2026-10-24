<!-- decision-ledger | v2.0.0 | template -->
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
<!-- index:end -->

---

### D-001 — <decision, stated as an imperative>

- **Date:** <YYYY-MM-DD>
- **Status:** adopted
- **WP:** <WP-nnn | intake | spec>
- **Changelog:** expected
- **Revisit if:** <falsifiable condition>

**Context.** <the forcing constraint>

**Decision.** <one imperative sentence>

**Alternatives considered.**
- *<option>* — rejected: <reason>. Revisit if: <condition>.

**Consequences.**
- Good: <what improves>
- Bad: <what gets worse>

---
