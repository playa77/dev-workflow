<!-- changelog | keep-a-changelog 1.1.0 | semver -->
# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Every line cites its decision and work package: `(D-nnn, WP-nnn)`.

## [Unreleased]

### Added
- `workflow/` holds the whole method; `docs/` holds generated artifacts. (D-009, WP-001)
- Root `DECISIONS.md`: one append-only ledger with a generated index and rejected options recorded inline. (D-015, WP-001)
- Root `CHANGELOG.md`, correlated with the ledger and checked in CI. (D-016, WP-001)
- `workflow/START.md`: single entrypoint for install, bootstrap and phase routing. (D-009, WP-001)
- Structural gates: `check-ledger.py`, `check-changelog.py`, `check-intake.py`, `check-wp.py`, `check-spec.py`, `check-roadmap.py`, `risk-scan.py`, `close-wp.py`. (D-002, WP-001)
- `install.py` and `doctor.py`: idempotent, non-destructive install with stack detection. (D-019, WP-001)

### Changed
- The interview exits on a twelve-topic coverage map with `open == 0`; no confidence percentage. (D-014, WP-001)
- Documents 1–3 are generated in one pass; the operator approves a one-page digest. (D-020, WP-001)
- Human input is limited to the interview, the digest and risk-triggered review. (D-018, WP-001)
- Enforcement is machine-checked or agent-verified; "human-gated" is removed. (D-017, WP-001)
- Work packages merge automatically when every gate is green; risk triggers force review. (D-010, WP-001)
- Review cadence is milestone-based, with risk-triggered per-package review. (D-012, WP-001)
- The roadmap is always generated with the spec. (D-011, WP-001)
- Work packages remain sized by reviewability, not token estimates. (D-001, WP-001)
- Commands are generated into `workflow/config.json`; CI lanes are generated from it. (D-019, WP-001)
- Test-integrity and executability gates are wired into CI. (D-002, WP-001)

### Removed
- `docs/HUMAN-REVIEW.md`, the per-document approvals, the operator checklist, the manual command table, the prompt preamble and the `cat` prompt assembly. (D-018, WP-001)
