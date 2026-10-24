#!/usr/bin/env bash
# Entry point used by docs/WORKFLOW.md and CI. See docs/VERIFICATION.md section 2.
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$here/test_integrity.py" "$@"
