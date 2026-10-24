#!/usr/bin/env bash
# Entry point used by docs/WORKFLOW.md section 10 and templates/PR.md.
set -euo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$here/wp_stats.py" "$@"
