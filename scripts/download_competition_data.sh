#!/usr/bin/env bash
# Restore the publicly mirrored inputs; these are not organizer-authenticated.
# The official data page and DEM links still require separate access.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 scripts/restore_data.py "$@"
