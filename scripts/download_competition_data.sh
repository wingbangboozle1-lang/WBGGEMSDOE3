#!/usr/bin/env bash
# download_competition_data.sh — place the competition rasters into data/raw/.
#
# 2026-10-27: the previous version of this script only PRINTED instructions and
# could never succeed ("single remaining blocker to training is data placement").
# It now performs the placement autonomously through the only channel available
# to this environment: the SHA-256-pinned public GitHub mirror listed in
# registry/data_manifest.json.  `gh` authentication for github.com is already
# configured in this workspace; no DrivenData credential is used or stored.
#
# PROVENANCE WARNING (no hallucinations): these bytes are an OWNER-SUPPLIED
# MIRROR of the login-walled competition files, not an authenticated download
# from https://www.drivendata.org/competitions/306/competition-doe-gems/data/.
# The hashes prove that the mirror is internally consistent and that we fetched
# exactly the bytes studied by the sibling projects.  They do NOT prove the
# organizer's origin, band semantics, licence, or that the hidden test labels
# match.  See knowledge/review-and-irregularities-2026-10-26.md (IR-06).
#
# Official sources for manual verification:
#   https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
#   https://www.drivendata.org/competitions/306/competition-doe-gems/data/
#   https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
#   https://gdr.openei.org/submissions/1391
#   https://docs.nlr.gov/docs/fy26osti/96647.pdf
#
# Usage:  bash scripts/download_competition_data.sh [DEST]   (default data/raw)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DEST="${1:-$ROOT/data/raw}"

echo "[1/4] Fetching 26 hash-pinned mirror files into ${DEST} ..."
bash scripts/fetch_mirrors.sh "$DEST"

if [[ -x .venv/bin/python ]]; then PY=.venv/bin/python; else PY=python3; fi
echo "[2/4] Fetching 4 hash-pinned 3DEP 10 m / fluvial-chi / BLM external rasters ..."
"$PY" scripts/fetch_fchd_external.py

echo "[3/4] Running scripts/prepare_data.py ..."
"$PY" scripts/prepare_data.py

echo "[4/4] Data placement complete. Pins: registry/data_manifest.json + registry/fchd_external_manifest.json; grid: data/manifest.json."
echo "REMINDER: mirror bytes are NOT organizer-authenticated; verify provenance before a real upload."
