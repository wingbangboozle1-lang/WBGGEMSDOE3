#!/usr/bin/env bash
# Restore the unmodified shared template and its SHA-verified public bridge.
# This is not an authenticated official data download.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -n "${PYTHON:-}" ]]; then
  exec "$PYTHON" scripts/restore_shared_data.py "$@"
fi
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
exec .venv/bin/python scripts/restore_shared_data.py "$@"
