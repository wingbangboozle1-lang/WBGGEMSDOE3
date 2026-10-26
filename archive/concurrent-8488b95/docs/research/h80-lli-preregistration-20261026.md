# Preregistration: H80 LLI-UNIQUE HYDROTHERMAL-CONDUIT

- **Date:** 2026-10-26
- **Lane:** LLI-UNIQUE / HYDROTHERMAL-CONDUIT-EDGE-DETECTION
- **Hypothesis:** Multi-scale DEM curvature discontinuity + simulated thermal-gradient proxy detects hidden geothermal fault segments that do not surface in USGS/INGENIOUS catalogue.
- **Mechanism:** Curvature at 300m, 600m, 1200m triangular kernels → gradient magnitude maxima → confidence-weighted placement along anomaly edges → suppression within 500m of visible catalogue faults.
- **Prediction:** Will catch alteration-zone-adjacent hidden fault tips not captured by H19-5 dotted-ridge replication (current champion family).
- **Expected DTI improvement:** Uncertain; projection 0.230-0.255 < champion 0.285 due to small visible-fault feature stack. Requires real feature stack for improvement.
- **Unique feature:** No replication of registry point patterns; uses curvature discontinuity only.
- **Non-fault mimic:** Erosional scarps, fluvial terraces, glacial moraines. Filtered by stress-direction alignment, thermal-proxy correlation, and aspect-ratio exclusion.
- **Holdout:** Hide-and-recover (whole segments + buffer) using visible faults only. Score: DTI (alpha 0.2, beta 0.8, 300m triangular kernel).
- **Leakage check:** Each feature (curvature scale 1, scale 2, gradient proxy) tested individually; AUC < 0.90 required.
- **Budget:** 1/3 experiments used; stop at 3 or 2 hours.
- **Verdict criterion:** Promote only if holdout DTI + 95% CI exceeds current repo best (0.0992 proxy) AND projection ≥ champion under same LLI fit. Current status: NEGATIVE — do not submit as improvement; file is unique and format-valid for audit.
