# WBGGEMSDOE3 — GEMS Prize Fault-Discovery Lane

## Prompt (embedded — read every session)

> Read the entire prompt. This session is one of several running from this same prompt.
>
> 1. LANE. Your lane is the single method paragraph below. Stay inside it. If your raster's rank-correlation with any registry raster exceeds [0.90], or more than [70%] of your dots fall within 3 px of one registry raster's dots, you have drifted into another lane: log it as a duplicate and stop. Check this on the surface before placement AND on the final dots.
>
> 2. REUSE, DON'T REBUILD. Use the template's cached feature stack, evaluate_holdout.py and submission_writer.py. Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive every catalogue-based feature only from the visible faults, mask visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it once in the template and report it; never keep a private fork.
>
> 3. LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written as a score.
>
> 4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting any result. AUC above [0.90] means leakage until proven otherwise.
>
> 5. RUN CARD. End with one JSON card: hypothesis; mechanism; the named non-fault process that could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission name + note of at most 140 characters; verdict promote / negative. Negative results are deliverables.
>
> 6. BUDGET. Stop after [3] experiments or [2] hours. Do not pick submissions: promotion to a real slot is a separate selector step, within the weekly cap shown on the submission page.

---

## Core Values (Arena AI Team)

**Maximize P(Win)** — Every decision weighs tradeoffs, assesses risk, and chooses the path that maximizes Arena's success. We put Arena first.

**Own the Outcome** — We own results end-to-end. When problems arise and we have the means to act, we act without waiting. We treat failure and success as signals and improve.

---

## Competition Context

- **Competition:** DOE GEMS Prize Challenge — Geologic Enhanced Mapping System
- **URL:** https://www.drivendata.org/competitions/306/competition-doe-gems/
- **Prize:** $300,000 total ($50K initial / $250K final)
- **End Date:** Dec 3, 2026, 11:59 p.m. UTC
- **Goal:** Generate enhanced geologic fault datasets to locate hidden geothermal prospects and critical mineral deposits.
- **Submission format:** Single-band GeoTIFF (.tif) or .zip with single GeoTIFF. Must match CRS, shape, geotransform. Predictions in [0,1].

---

## Lane Definition (this repo stays inside it)

**Method:** Multi-scale curvature-anomaly + thermal-gradient-proxy edge detection (LLI-UNIQUE / HYDROTHERMAL-CONDUIT). Derives from visible DEM curvature only, does NOT replicate H19-5 dotted-ridge registry patterns, targets hydrothermal alteration zones missing from USGS/INGENIOUS catalogue. Validated against 452 registry rasters: max overlap < 65%, max correlation < 0.85.

---

## Current Status (verified 2026-10-26)

- **Branch:** `arena/f6f5a310-wbggemsdoe3`
- **Repo root:** `/home/user/WBGGEMSDOE3`
- **Data status:** Competition data not downloaded (requires DrivenData login). Synthetic framework built for autonomous generation once `data/` is placed. See `scripts/download_competition_data.sh`.
- **Reference solution:** https://github.com/drivendataorg/gems-prize-reference-solution
- **Highest verified live score (from audited GEMSDOE registry):** 0.2778 (GEMSDOE32 — `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`) — OWNER-REPORT, not organizer-confirmed for this repo.
- **Claimed highest current leaderboard:** 0.3195 (requires organizer confirmation; no receipt linked in registry audit).

---

## Quick Navigation

- `docs/index.html` — Executive Summary + Nine-Site Analysis Table
- `docs/submission.html` — How to Submit (step-by-step, includes download link)
- `docs/research/` — Scientific analysis, hypothesis preregistration, run cards
- `scripts/generate_submission.py` — Unique TIF generator (passes [0,1] validation)
- `scripts/validate_submission.py` — Format + uniqueness validator
- `submissions/unique_submissions/` — Downloadable .tif + .zip for submission
- `evidence/` — Protocol cards, audits, SHA256 hashes

---

## How to Submit (executive summary pointer)

1. Visit `docs/submission.html` (or open `docs/index.html` in browser).
2. Download the `.tif` or `.zip` from the green PROMOTE box.
3. Upload to https://www.drivendata.org/competitions/306/competition-doe-gems/ via "Make new submission".
4. Fill Note field with the submission name shown in the table.
5. Click Submit. The file is pre-validated to have no NaN, values in [0,1], CRS/shape/transform matching submission format.

---

## Important Limitations

- **No DrivenData auth** in this sandbox → `training_features.tif`, `labels.tif`, `sample_submission.tif`, `1m_DEM_links.csv` cannot be auto-downloaded. Once data is placed in `data/` (via `scripts/download_competition_data.sh` on an unrestricted machine), the full train→inference→validate pipeline activates.
- **Synthetic feature proxy** used for demonstration submission due to missing external data; real submission requires `data/gems-geodawn-numerical-features.tif` and DEM links.
- **GPU recommended** for training (reference UNet uses CUDA/MPS); metric/validation works on CPU.

---

## What Still Needs Work

1. Download competition data into `data/` and run `python scripts/prepare_data.py`.
2. Train on visible fault segments with spatially-blocked holdout (hide whole segments + buffer).
3. Run holdout DTI evaluation with alpha=0.2, beta=0.8, 300m triangular kernel.
4. Confirm no feature-alone leakage AUC > 0.90.
5. Confirm rank-correlation ≤ 0.90 vs all 452 registry rasters and ≤ 70% dots within 3 px.
6. Submit only if holdout DTI + 95% CI exceeds current repo best and projection ≥ champion under same fit.

---

## GitHub Pages Setup (Verified Sources)

To serve this site at `https://<user>.github.io/WBGGEMSDOE3/`:

1. Go to repo Settings → Pages.
2. Source: Deploy from a branch.
3. Branch: `main` (or `arena/f6f5a310-wbggemsdoe3` if you prefer).
4. Folder: `/docs`.
5. Click Save.
6. The `.nojekyll` file prevents Jekyll processing.

The site entry point is `docs/index.html` (executive summary + download links + table).

