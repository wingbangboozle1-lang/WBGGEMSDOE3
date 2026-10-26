# WBGGEMSDOE3 — GEMS Geothermal Discovery Submission Pipeline

**Branch:** `arena/9d03eeec-wbggemsdoe3`
**Competition:** [DrivenData GEMS (Geothermal Exploration Machine Learning)](https://www.drivendata.org/competitions/306/competition-doe-gems/)
**Leaderboard high score (as reported):** 0.4413 / 0.3195 (two figures appear in the brief; neither independently verified by us)
**Goal:** Place top of the GEMS leaderboard with a unique, validated, downloadable GeoTIFF submission.

> Read this README at the start of every work session. It is the project's
> single source of truth: hypothesis, method, validation gates, run card, and
> submission instructions.

---

## 1. One-line status

The pipeline is implemented and verified end-to-end on synthetic stand-in data.

| Item | Status |
|------|--------|
| Scripts (`scripts/`, `src/`) | Implemented & tested |
| Validation gates | Implemented (single band, [0,1], no NaN, CRS/shape/transform) |
| Generated stand-in TIF | `submission/gems-hnew01-stepper-dblind-unique.tif` |
| OK to download (format-valid) | **Yes** |
| OK to submit to real competition | **No** — stand-in built on synthetic test data; geometry does not match the real grid |
| Real competition data | **Not available** (DrivenData login required; see blocker below) |

---

## 2. Data blocker (must be resolved before a real submission)

The competition rasters (`training_features.tif`, `labels.tif`,
`sample_submission.tif`, `existing_faults.tif`, `1m_DEM_links.csv`) live on the
DrivenData [data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
and redirect to a login page. Automated download is blocked in this sandbox.

**What you need to do (one-time, on a machine with DrivenData access):**

```
1. Log in to https://www.drivendata.org/competitions/306/competition-doe-gems/data/
2. Download training_features.tif, labels.tif, sample_submission.tif,
   existing_faults.tif, 1m_DEM_links.csv
3. Place them in data/raw/
4. Create data/raw/REAL_COMPETITION_DATA_CONFIRMED   (marks data as genuine)
5. python scripts/prepare_data.py        # writes data/manifest.json
6. python scripts/generate_submission.py # builds + validates + writes submission/*.tif
7. Upload submission/*.tif to the DrivenData submission page
```

See `scripts/download_competition_data.sh` for the full documented source list
(including the public GEODAWN survey at USGS GDR #1391 and EPSG:32611).

Free, official, obtainable external sources:
- GEODAWN airborne magnetic & radiometric survey: https://gdr.openei.org/submissions/1391
- USGS GEODAWN data page: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- 30 m DEM / CRS: https://epsg.io/32611
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution

---

## 3. Executive summary — focus sites (GEMSDOE 24, 25, 27, 28, 30, 31, 32, 33, 36)

Scores below are **as reported on each team's site** — not independently re-scored by us and not organiser-confirmed.

| Site | Best submission (file to download) | Est. score | Unique vs other focus sites? | Notes |
|------|------------------------------------|------------|------------------------------|-------|
| GEMSDOE32 | h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros | **0.2778** | **No** — "-zeros" pattern reused across GEMSDOE36, 37, 39-44 | Highest reported among focus sites; "-zeros" suggests degenerate raster |
| GEMSDOE36 | anderson-geothermal-pinn-38854-...-9b9ea4e6-zeros | 0.2750 | **No** — "-zeros" pattern | Second-highest; also zero-filled |
| GEMSDOE28 | h36-1-rung30-blind-r1-...-b531dae0a36f-nan | 0.2710 | Yes | "-nan" flag (fails [0,1] gate) |
| GEMSDOE31 | h27-4-solo-d28-20261004-8acb75e1-nan | 0.2708 | **No** — duplicate family of GEMSDOE28 h27-4 | Same score/family |
| GEMSDOE28 | h27-4-r1-solo-d2-8-...-8acb75e1f2cc-nan | 0.2708 | **No** — duplicate family of GEMSDOE31 | "-nan" flag |
| GEMSDOE28 | h38-1-hf-euler-r30-r1-...-56a9f473edc7-nan | 0.2707 | Yes | "-nan" flag |
| GEMSDOE33 | h33d-analog-tip-stepover-r30-...-cb490425926e | 0.2632 | Yes | Tip/stepover family — conceptually closest to our H-NEW-01 |
| GEMSDOE25 | dotted-h19-5-d2-8-...-e56ea318af89-nan | 0.2600 | Yes | "-nan" flag; same score as GEMSDOE30 |
| GEMSDOE30 | d28-poisson300m-offcat-44090-...-91eae1ca | 0.2600 | Yes | Same score as GEMSDOE25 |
| GEMSDOE24 | h25-1-dotted-h19-5-d1-5-...-989f59505db1-nan | 0.2477 | Yes | "-nan" flag |
| GEMSDOE27 | topo-gap-closure-t-v2-on-d1-5-...-5512495c6bd1-nan | 0.2449 | Yes | "-nan" flag |

**Best submission to build on:** GEMSDOE32 (0.2778) is the highest-reported score,
but it is **not safe to copy**: it is flagged "-zeros" (degenerate) and is not
unique vs the "-zeros" pattern used across many sites. Copying it = duplicate
submission.

**Our approach:** target the same high-scoring neighbourhood (stepover / tip /
relay-ramp density — cf. GEMSDOE33's 0.2632 tip-stepover) via a **unique**
method (H-NEW-01 below) that is not a copy of any GEMSDOE focus-site submission.

Full site: `site/executive-summary.html`.

---

## 4. Our generated submission

**File:** `submission/gems-hnew01-stepper-dblind-unique.tif` (stand-in; also served from `site/assets/downloads/`)

- Single-band GeoTIFF, values in [0, 1], no NaN
- CRS EPSG:32611
- Method: H-NEW-01 blind stepover / relay-ramp pull-apart density
  (DEM curvature texture + local lineament density around visible faults)
- Unique vs all GEMSDOE focus sites
- Validation: passes all format gates (see run card JSON next to the TIF)

**NOT OK to submit to the real competition as-is** — it is a format-valid
stand-in produced on synthetic test data. Its geometry does not match the real
competition grid. Follow the data blocker steps above to generate a scorable
submission.

Run card (written next to the TIF): `submission/gems-hnew01-stepper-dblind-unique.run_card.json`

---

## 5. Hypotheses (ranked, untested on real grid)

| Rank | ID | Hypothesis | Expected DTI | Cost | Data needed | Obtainable? | Status |
|------|-----|------------|--------------|------|-------------|-------------|--------|
| 1 | H-NEW-01 | Blind stepover / relay-ramp pull-apart density (curvature + lineament density) | Moderate (+0.03 to +0.08) | Low | 30 m DEM (USGS 3DEP) | Yes | **Selected** |
| 2 | H-NEW-02 | Radiometric K/Th hydrothermal alteration halo (GEODAWN) | Moderate-to-high (+0.05 to +0.12) | Low-medium | GEODAWN K/Th/eU raster | Partly (needs DrivenData login) | Blocked |
| 3 | H-NEW-03 | Magnetic lineament gradient + Curie-point depth proxy | Moderate (+0.04 to +0.10) | Low-medium | GEODAWN magnetic raster | Partly (needs DrivenData login) | Blocked |
| 4 | H-NEW-04 | Thermal-inertia / nighttime LST anomaly over piedmont | Low-to-moderate (+0.02 to +0.06) | Low-medium | Landsat/Sentinel-3 LST | Yes | Proposed |
| 5 | H-NEW-05 | Dilation / stepover stress proxy from catalogue fault geometry | Low (+0.01 to +0.04) | Low | existing_faults.tif | Yes (needs login) | Proposed |

Source: `src/hypotheses.py` (programmatic list + ranking).

---

## 6. Validation gates (automated — no human inspection)

A generated TIF is OK to submit only if ALL pass:

1. Single-band GeoTIFF
2. No NaN / inf inside the footprint
3. All values in [0, 1]  (fixes the "Predicted values must be in range [0, 1]" error)
4. CRS / shape / geotransform match `sample_submission.tif`

Any failure = hard block (flagged NOT OK to submit). This replaces manual
human inspection with project-level automated validation.

See `src/validate.py` and `scripts/submission_writer.py`.

---

## 7. How to generate + submit a TIF

```
# 0. (One-time) Get real competition data — see section 2 blocker
# 1. Prepare
python scripts/prepare_data.py
# 2. Generate + validate + write
python scripts/generate_submission.py
# 3. Inspect output
cat submission/*.run_card.json
# 4. If ok_to_submit_to_competition == true, upload submission/*.tif to
#    https://www.drivendata.org/competitions/306/competition-doe-gems/
#    with a unique name and a note (<= 140 chars).
```

Submission note proposal (<=140 chars):
> Unique blind stepover/relay-ramp density (H-NEW-01); not a copy of any GEMSDOE 24-36 submission.

---

## 8. Run card (per experiment)

Every run ends with one JSON run card:
- hypothesis; mechanism; named non-fault process that could mimic it
- holdout DTI + 95% CI (labelled HOLDOUT-DTI; never a projection)
- correlation/overlap vs registry
- raster sha256
- validator output (no NaN inside footprint, values in [0,1], CRS/shape/transform match)
- submission name + note (<=140 chars)
- verdict: promote / negative

See `scripts/evaluate_holdout.py`, `scripts/generate_submission.py`.

---

## 9. GitHub Pages site

Clean UI at `site/`:
- `site/index.html` — landing page with obvious download link + how to submit
- `site/executive-summary.html` — full comparison table + submission instructions
- `site/assets/downloads/gems-hnew01-stepper-dblind-unique.tif` — downloadable stand-in TIF

Deployed via `.github/workflows/pages.yml` on push to `main` / `arena/9d03eeec-wbggemsdoe3`.

---

## 10. Limitations

- **No real competition data:** labels/features require DrivenData login (blocked here). All scores above are historical/as-reported, not organiser-confirmed.
- **DTI metric is an interpretation:** the official closed-form competition metric is not public; our `pooled_dti` (alpha 0.2, beta 0.8, 300 m triangular kernel) is a documented approximation for holdout self-evaluation only.
- **Stand-in TIF is not scorable:** built on synthetic test data; geometry won't match the real grid. Regenerate against real data before submitting.
- **Hypotheses untested on real grid:** H-NEW-01 through H-NEW-05 are proposed; none has been validated on real competition labels.

---

## 11. Official / verified sources (for manual review)

- Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/
- Overview: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- About: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- Data (login): https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- GEODAWN survey (USGS GDR #1391): https://gdr.openei.org/submissions/1391
- GEODAWN USGS page: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- INGENIOUS: https://gbcge.org/current-projects/ingenious/
- EPSG:32611: https://epsg.io/32611
- Tversky index: https://en.wikipedia.org/wiki/Tversky_index
- Submission rules PDF: https://docs.nlr.gov/docs/fy26osti/96647.pdf

---

*WBGGEMSDOE3 — Core values: Maximize P(Win), Own the Outcome. No hallucinations; every number labelled HOLDOUT-DTI or organiser-confirmed.*
