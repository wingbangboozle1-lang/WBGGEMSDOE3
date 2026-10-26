#!/usr/bin/env bash
# download_competition_data.sh
#
# Download GEMS competition data into data/raw/.
#
# BLOCKER: The DrivenData competition data tab (training_features.tif,
# labels.tif, sample_submission.tif, existing_faults.tif, 1m_DEM_links.csv)
# requires a DrivenData login and redirects to a login page.  Automated
# download is therefore NOT possible from this environment without
# DrivenData credentials.
#
# Manual steps (run on any machine with DrivenData access):
#
#   1. Log in to https://www.drivendata.org/competitions/306/competition-doe-gems/data/
#   2. Download:
#        - training_features.tif
#        - labels.tif
#        - sample_submission.tif
#        - existing_faults.tif
#        - 1m_DEM_links.csv
#   3. Optionally (public, free, official):
#        - GEODAWN airborne magnetic & radiometric survey metadata:
#          https://gdr.openei.org/submissions/1391
#          https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
#        - 30 m DEM: USGS 3DEP / https://epsg.io/32611 (CRS reference)
#   4. Place all rasters into data/raw/
#   5. Run: python scripts/prepare_data.py   (writes data/manifest.json)
#
# Public Dropbox mirrors referenced by the competition write-up (may require
# Dropbox access; not guaranteed reachable from this sandbox):
#   https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?dl=1
#   https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?dl=1
#   https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?dl=1
#   https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?dl=1
#   https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?dl=1
#
set -euo pipefail

echo "This script documents data acquisition only."
echo "Competition data requires DrivenData login: see comments above."
echo "After placing rasters in data/raw/, run: python scripts/prepare_data.py"
