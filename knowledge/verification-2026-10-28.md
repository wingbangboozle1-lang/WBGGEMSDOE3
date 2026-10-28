# Verification log — 2026-10-28 session (arena/05d1dfa0-wbggemsdoe3)

Scope: check the current submission decision line by line against official sources and independent
recomputation, fix what is wrong, and state plainly what is still unproven. Every line below is either a
quoted official fact (with its URL) or a number reproduced by a command listed in the last column.
Nothing here is an organizer-confirmed score. No competition upload was made and no weekly slot was used.

## 1. Official rules (quoted; verified by fetch on 2026-10-28)

| # | Claim | Source (verified) | Result |
|---|---|---|---|
| R1 | One GeoTIFF; single layer; `float32`; values **between 0 and 1** | DrivenData problem page, “Submission format”: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | Confirmed |
| R2 | Same CRS (EPSG 32611), resolution (100 m) and bounds as training data | same page | Confirmed |
| R3 | “data outside the bounds is **null or nan**” | same page | Confirmed. This allows NaN outside the bounds, so the project's zeros-outside choice is a *stricter* policy, not a rule. |
| R4 | Submissions “will be automatically evaluated”; expert panel revises labels *after* the initial round | NLR Official Rules §3.5 and §1 “Executive Summary”: https://docs.nlr.gov/docs/fy26osti/96647.pdf | Confirmed. No human inspector gates an upload. |
| R5 | Three submissions per week; one final submission per entity | NLR §3.2 (“three submissions per week”), §3.4 | Confirmed. The live weekly quota on the portal was not visible (login-gated). |
| R6 | Narrative must disclose generative-AI use | NLR §3.2 “Indication of use of generative artificial intelligence (AI) technology” | Confirmed. Added to the how-to page. |
| R7 | Portal submission page | https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/ | Exists; redirects to **login** (not reachable without the user's account). |
| R8 | Metric: distance-weighted Tversky, α=0.2, β=0.8, triangular kernel R=300 m | DrivenData problem page “Performance metric” | Confirmed; the shared evaluator in `src/gemsw/exact.py` uses R=3 px = 300 m at 100 m. |

## 2. Live public leaderboard (read 2026-10-28)

Source: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/

- #1 xiaofanhu **0.4544** (33 submissions) · #2 cfld__ **0.3916** · #3 Batik Shirt Brothers **0.3911** ·
  #4 BrandenKMurray **0.3724** · #5 No Fault of Our Own **0.3570**.
- The brief's figures **0.4413** and **0.3195** are **not** the current top. They are stale or unverifiable.
- Public scores are *public-test* scores. The private test set decides Phase 1.

## 3. Primary file (`docs/downloads/wbggems3-invdesign-anchor-20k-zeros.tif`)

| Item | Value | Command |
|---|---|---|
| sha256 | `283209b977bc1c4885b6e9936494575d324a3460f289312aeeef760528909dda` | `sha256sum` |
| bytes | 263,882 | `stat` |
| grid | 3730 × 3292, EPSG:32611, transform (100, 0, 243350, 0, −100, 4508550) | rasterio |
| dtype / bands | float32 / 1 | rasterio |
| NaN / non-finite | 0 / 0 | `scripts/validate_submission.py` |
| min / max | 0.0 / 1.0 | same |
| positive cells | 20,000 | same |
| verdict (format + uniqueness) | **PASS** | `docs/data/submission_validation_2026-10-28.json` |

The format gate reuses the shared preflight `gems_project.format_preflight.raster_report`. The
template grid `data/template_grid.tif` (all zeros, same grid) is the reference. Its provenance is the
mirror bytes listed in `registry/data_manifest.json`; the official `sample_submission.tif` could not be
downloaded here (login-gated), so the grid match is proven against the mirror, not the organizer's file.

## 4. Uniqueness (independent recomputation)

Rule (user protocol §1): a file is a duplicate if >70 % of its dots lie within 3 px of one registry raster's
dots, or if |Spearman| > 0.90 against one registry raster; an exact byte copy is also a duplicate.

- Comparators: the nine focus-site rasters, fetched by pinned commit through the GitHub API
  (`scripts/fetch_focus_rasters.sh`, `registry/focus_rasters_manifest.json`, each hash-verified), plus the two
  GEMSDOE3 `pindrop` rasters, plus every other GeoTIFF in this repository. Byte-identical copies are merged.
- Compared: 27 unique comparators. Skipped: 3 (different grid, or no positive cells). Skips are reported, not passed.
- Exact SHA-256 duplicates: **none**.
- Maximum share of our dots within 3 px of one comparator: **0.6874** (`pindrop-v4-discovery`, 155,021 dots),
  against the 0.70 limit. This passes, but the margin is only 1.3 points. See IR-09.
- Maximum |Spearman|: **0.0320** (limit 0.90).
- Against the nine focus sites: max directed overlap **0.3948** (GEMSDOE27), well under 0.70.

### Nine-site pairwise check (confirms the README “Unique: No” column)

Share of the ROW site's dots within 3 px of the COLUMN site's dots (independent run, same kernel):

| row \ col | 24 | 25 | 27 | 28 | 30 | 31 | 32 | 33 | 36 |
|---|---|---|---|---|---|---|---|---|---|
| 24 | 1.000 | 1.000 | 1.000 | 0.927 | 1.000 | 0.934 | 0.878 | 0.958 | 0.879 |
| 25 | 1.000 | 1.000 | 1.000 | 0.922 | 1.000 | 0.925 | 0.869 | 0.953 | 0.870 |
| 27 | 0.979 | 0.980 | 1.000 | 0.908 | 0.980 | 0.915 | 0.860 | 0.938 | 0.861 |
| 28 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.997 | 0.950 | 0.998 | 0.950 |
| 30 | 1.000 | 1.000 | 1.000 | 0.922 | 1.000 | 0.925 | 0.869 | 0.953 | 0.870 |
| 31 | 1.000 | 1.000 | 1.000 | 0.995 | 1.000 | 1.000 | 0.947 | 0.999 | 0.947 |
| 32 | 1.000 | 1.000 | 1.000 | 0.999 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| 33 | 0.997 | 0.997 | 0.997 | 0.965 | 0.997 | 0.970 | 0.918 | 1.000 | 0.919 |
| 36 | 0.974 | 0.973 | 0.974 | 0.971 | 0.973 | 0.972 | 0.972 | 0.973 | 1.000 |

Reading: the nine focus “champions” are one dot family (24, 25, 27, 28, 30, 31, 32, 33 and 36 all overlap at
≥0.87 directed). None of them is independent of the others. This is why the README marks every row
“Unique: No”. The candidate's maximum against these nine is 0.39, so it is a different family.

## 5. Score estimate (what is and is not known)

- The 0.47 figure is `ESTIMATE`, from `evidence/design_calibration.json`: an OLS fit of implied hidden-truth
  mass on 41 **owner-reported** scores (slope 0.735, R² 0.385, MAE 842 cells, Spearman 0.61).
- It assumes hidden truth mass M = 15,200 cells (`evidence/design_estimate.json`, `hypothesis`). That is an assumption,
  not a measurement.
- The 95 % interval (0.32–0.62) is a prediction interval of the fit, not a confidence interval of the score.
- No organizer receipt exists for this file. **The score is unknown.** Only the portal's receipt can give one.

## 6. Irregularities (flagged for review; corrected where noted)

- **IR-01 — Paraphrase labelled “verbatim”.** README's “Standing brief — verbatim” section was a
  condensed paraphrase. **Corrected:** the full user prompt is now in README (see the verbatim section);
  the paraphrase is kept, relabelled as a summary.
- **IR-02 — Wrong claim on the how-to page.** It said every scored sibling file is a `-zeros` file. The
  user's own public-leaderboard list includes positive `-nan` files (GEMSDOE24 0.2477, GEMSDOE28 0.2710,
  GEMSDOE25 0.2600). **Corrected** in `scripts/build_site_v3.py`.
- **IR-03 — False “ORGANIZER-CONFIRMED” label.** The zeros encoding was labelled organizer-confirmed with no
  receipt. **Corrected:** labelled unproven until a receipt arrives.
- **IR-04 — Stale note.** Run card, estimate evidence and `design_inv.py` said “14k dots; DTI est 0.31”. The
  file has 20,000 dots and the model estimate is 0.47. **Corrected** in all three places and in the gate.
- **IR-05 — CI reproducibility step was a no-op.** `checks.yml` ran `scripts/build_site.py`, a retired stub
  that prints a message, then diffed `docs/`. **Corrected** to `build_site_v3.py` + `build_release_gate_v2.py`.
- **IR-06 — Broken link out of the site contract.** A new link to `evidence/` failed `check_site.py`.
  **Corrected** by writing the validator record to `docs/data/`.
- **IR-07 — “Predicted values must be in range [0, 1]” root cause unproven.** The rules allow NaN outside the
  bounds, so NaN is not proven to be the cause. The zeros encoding is stricter and avoids the question, but
  acceptance is unconfirmed until a receipt.
- **IR-08 — Sample grid provenance.** The official `sample_submission.tif` is login-gated; the grid used
  here is the mirror-derived `data/template_grid.tif`. The rules fix CRS, resolution and bounds, not the
  shape 3730 × 3292; the shape comes from the mirror.
- **IR-09 — Near-threshold overlap.** The candidate is 0.6874 against GEMSDOE3 `pindrop-v4-discovery`
  (limit 0.70). It passes, but a small change in the dot set could flip it. It is also a dense comparator
  (155,021 dots), which makes overlap high by chance.
- **IR-10 — Estimate lineage is weak.** R² 0.385 on 41 owner-reported targets, with an assumed M. Treat 0.47
  as a hypothesis to test with one slot, not as a finding.
- **IR-11 — Holdout is not a reliable ranker.** The release gate records that the catalogue holdout is
  anti-correlated with live scores. Do not use it to promote or reject files.
- **IR-12 — Leaderboard figures disagree.** The brief quotes 0.4413 and 0.3195; registry and the live
  leaderboard show 0.4544. Use the live page.
- **IR-13 — Owner-reported sibling scores cannot be reconciled with the public board.** Sibling claims of
  0.24–0.28 sit well below the public top ten (0.33–0.39), and none has a receipt here. They are used
  only as a reference point.
- **IR-14 — Access limits.** `raw.githubusercontent.com` is not an allowed host here, so raw links fail; the
  GitHub API works. The DrivenData data page and the portal require login. The competition training data
  is not in this sandbox (`data/raw/` absent), so no holdout or training run was repeated this session.
- **IR-15 — Legacy page makes an unverified claim.** `docs/thcs/` (legacy THCS lane, built by
  `scripts/build_site_thcs.py`, which `build_site_v3.py` does not invoke) says its file “will **not** trigger the portal validation error”. That is not
  verified. The page is superseded and not regenerated by CI. Treat it as historical only.
- **IR-16 — Stored Spearman figure not reproducible here.** The index quotes max |ρ| 0.047 against 58 sibling
  rasters (from `evidence/uniqueness_gate.json`, built from `/tmp` inputs that are no longer present). The
  independent run here gives 0.032 against 27 unique comparators. Both are far below 0.90; the discrepancy
  reflects the different comparator sets.
- **IR-17 — Catalogue figure not re-run.** “0.0 % of our dots within 3 px of the public catalogue” comes from the
  design run. The USGS/INGENIOUS label raster is not in this sandbox, so this session did not re-test it.
- **IR-18 — Local “PASS” labels.** Format rows were labelled PASS, which reads like portal acceptance. They are
  now labelled LOCAL PASS. Only the portal's response is acceptance evidence.

## 7. What this session did not do (honest limits)

- No new holdout experiment and no new model. The three-experiment budget was not used. Re-running the
  holdout needs the login-gated training data, which is not in the sandbox.
- No competition upload. The user should upload, if they choose, after reading `docs/how-to-submit.html`.
- The three hypotheses required before implementation were written in earlier sessions
  (`knowledge/hypotheses-2026-10-28-invdesign.md`, `knowledge/preregistration-2026-10-28-*.md`). This session
  did not add new ones.

## 8. Reproduce

```
bash scripts/fetch_focus_rasters.sh                       # 11 pinned comparators, hash-verified
.venv/bin/python scripts/validate_submission.py docs/downloads/wbggems3-invdesign-anchor-20k-zeros.tif \
   --registry-dir data/external/focus --include-repo-tifs --out docs/data/submission_validation_2026-10-28.json
.venv/bin/python scripts/build_site_v3.py && .venv/bin/python scripts/build_release_gate_v2.py
.venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q
```
