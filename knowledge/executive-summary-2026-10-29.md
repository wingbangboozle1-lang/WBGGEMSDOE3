# Nine-site executive summary — 2026-10-29

> **DECISION: DO NOT DOWNLOAD OR SUBMIT ANY FILE FROM THIS TABLE.** No file is cleared.
> No new TIFF was generated in this session. Reasons, in order of weight:
> 1. **Not unique.** Every nine-site file overlaps another focus file at ≥97.6% within 3 px
>    (`unique_vs_focus_set = false` for all nine). The user's rule requires a unique file.
> 2. **No holdout.** Competition labels are not in this sandbox (DrivenData and Dropbox are
>    unreachable), so no HOLDOUT-DTI can be computed and no candidate score exists.
> 3. **Open repo stop.** The 2026-10-28 review records a literal dense-witness stop that
>    blocks new candidate construction (see `README.md`, `AGENTS.md`).
> 4. **Unverified portal format.** The `Predicted values must be in range [0, 1]` error is
>    not reproduced or explained by any local check (see irregularities).

## Best owner-reported file (highest score in the nine sites)

**GEMSDOE32** — `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` — owner-reported **0.2778**. This is an owner report, not an organizer receipt. It is **not unique** and is **not cleared**.

Why it scored high (explained in full in [content/why-0.2778.md](../content/why-0.2778.md)): its positive support is an exact subset of the GEMSDOE28 base with 2,545 cells removed near the catalogue. That is a plausible mechanism for a distance-weighted Tversky score, not a proven one.

## Table — file, estimate, uniqueness

`Ledger projection` is a **model projection, not a score** (ledger-inversion, site-grouped CV MAE 0.037 per `docs/data/nine_site_table.json`). `Holdout-DTI` is `not run` for every row.

| Site | File to download? | Owner-reported score | Ledger projection (NOT a score) | Holdout-DTI | Unique vs the nine? | Max 3-px overlap with another nine-site file | Decision |
|---|---|---|---|---|---|---|---|
| GEMSDOE24 | [gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE24/raw/5cfab74597cd1d0a271e4640b4cc34511e56ca59/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) (research archive only) | 0.2477 | 0.3292 (projection) | not run | **No** | 100.00% vs GEMSDOE25 | **DO NOT SUBMIT** |
| GEMSDOE25 | [gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE25/raw/bfb2dfdbdf1b87d67afc6facd422180f56ebc455/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) (research archive only) | 0.2600 | 0.3460 (projection) | not run | **No** | 100.00% vs GEMSDOE24 | **DO NOT SUBMIT** |
| GEMSDOE27 | [gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE27/raw/f1e32af867d9cf0081af20866c8241ec8678a432/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) (research archive only) | 0.2449 | 0.3271 (projection) | not run | **No** | 98.02% vs GEMSDOE24 | **DO NOT SUBMIT** |
| GEMSDOE28 | [gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE28/raw/9c1be21e8f1be707347f737e42abf62ea669c819/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) (research archive only) | 0.2710 | 0.3475 (projection) | not run | **No** | 100.00% vs GEMSDOE24 | **DO NOT SUBMIT** |
| GEMSDOE30 | [gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif](https://github.com/buffedlizard55-lab/GEMSDOE30/raw/35ce8911e2c3287eed973eacd12c252e8cb3f34c/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) (research archive only) | 0.2600 | 0.3460 (projection) | not run | **No** | 100.00% vs GEMSDOE24 | **DO NOT SUBMIT** |
| GEMSDOE31 | [gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE31/raw/78f9bf3ae82e5c78ca348aa37c0660c339e72f0e/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) (research archive only) | 0.2708 | 0.3545 (projection) | not run | **No** | 100.00% vs GEMSDOE24 | **DO NOT SUBMIT** |
| GEMSDOE32 | [gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE32/raw/8953b986b2ce6eb5ee8b7eda23fe3ad529720986/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) (research archive only) | 0.2778 | 0.3599 (projection) | not run | **No** | 100.00% vs GEMSDOE24 | **DO NOT SUBMIT** |
| GEMSDOE33 | [GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif](https://github.com/buffedlizard55-lab/GEMSDOE33/raw/a24fb7c5031ee08b12440af4593057858fecef8e/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) (research archive only) | 0.2632 | 0.3469 (projection) | not run | **No** | 99.71% vs GEMSDOE27 | **DO NOT SUBMIT** |
| GEMSDOE36 | [gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE36/raw/b90418f852615aa0974cf9a53b92fa569ed133fc/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) (research archive only) | 0.2750 | 0.3588 (projection) | not run | **No** | 97.58% vs GEMSDOE27 | **DO NOT SUBMIT** |

Links point to the pinned upstream commit recorded in `README.md`, for reproducibility only.

## Why nothing here can be promoted yet

- Competition labels and the official sample footprint are not available here; DrivenData and Dropbox were unreachable from this sandbox on 2026-10-29 (HTTP 000); earlier sessions recorded a DrivenData login redirect.
- The only sample/labels bytes reachable from this sandbox are a third-party public mirror. Its `labels.tif` is identical to `existing_faults.tif`, which is a red flag, and its license and organizer origin are unverified. They are not used.

## Irregularities for manual review

1. **Template is not the official footprint.** `data/template_grid.tif` has 12,279,160 finite cells, all zero, versus the writer's claimed 5,167,373. Grid CRS/shape/origin/resolution match the writer constants: **True**. Recorded as IR-28-12.

2. **Leaderboard figures disagree.** Your message gives 0.4413 and 0.3195 as the top. The repo capture (`docs/data/leaderboard_observation_2026-10-28.json`) has rank 1 = 0.4544, and 0.3195 at rank 26. Contains 0.4544: True; 0.3195: True.

3. **Portal format error unexplained.** `Predicted values must be in range [0, 1]`. Local checks can confirm values in [0,1] and CRS/shape/transform, but not the portal's own parser or nodata rules.

4. **Deadline conflict.** The competition homepage and the rules PDF Appendix A give different end-of-competition times (see `knowledge/source-notes-2026-10-27.md`). The earlier time is assumed.

5. **Owner-repo mirror label anomaly** (see the archive note above).

6. **Projections are not scores.** The ledger estimates (0.33–0.36) above are model outputs and must not be read as expected leaderboard results.

## What is needed to generate a unique, cleared TIFF

1. Log in to DrivenData with your own account and download the competition data and sample submission to `data/` (the existing `scripts/download_competition_data.sh` and `scripts/prepare_data.py` do the placement). This sandbox cannot reach DrivenData.
2. Run the existing holdout protocol (`evaluate_holdout.py`, shared template) to get a HOLDOUT-DTI with withheld-positive count and 95% CI.
3. Resolve the dense-witness stop with a documented correction. Do not waive it.
4. Generate one candidate and run the format and uniqueness validators (float32, one band, EPSG:32611, 100 m, values in [0,1], NaN outside footprint, ≤70% within 3 px of any registry raster).
5. Only then a human selector chooses a slot (3 per week; 1 final across both rounds).

## Sources (official, for manual review)

- [DrivenData competition](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [Staff: known-fault masking](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516)
- [Official source check, 2026-10-28](../evidence/official_source_check_2026-10-28.json)

## Not in this summary

- No slot selection, no upload, and no organizer receipt. Owner scores are labelled as owner reports.

---
*Generated by `scripts/build_executive_summary_2026_10_29.py`. Verification record: `evidence/verification_2026_10_29.json`.*
