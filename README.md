# WB-GEMS-DOE-3 — DOE GEMS Prize fault-discovery submission system

**Goal:** place top of the [DOE GEMS Prize Challenge](https://www.drivendata.org/competitions/306/competition-doe-gems/)
leaderboard by generating a unique, valid, high-scoring single-band GeoTIFF submission of geothermal fault
probability, validated automatically (no human inspection) and ready to download and submit.

> Read this README at the start of every work session. It is the project's starting point and the statement of
> what we are building: a system that produces an easy-to-download submission TIF, estimates its score, proves
> uniqueness vs prior GEMSDOE submissions, and makes submission obvious.

---

## Competition facts (official, verified)

- **Task:** predict geological faults as pixel-wise probabilities in [0, 1]; submit one single-band GeoTIFF.
- **Metric:** distance-weighted Tversky Index, `alpha=0.2`, `beta=0.8`, triangular kernel `R = 300 m` (3 px at 100 m).
  [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- **Format:** EPSG:32611 (UTM 11N), 100 m, same bounds as training data, single-band float32, values in [0,1],
  data outside bounds null/NaN. Grid: **3730 × 3292**, origin `(243350, 4508550)`.
  [Submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format)
- **Data (login-gated):** `training_features.tif`, `labels.tif`, `sample_submission.tif`, `1m_DEM_links.csv` from
  [DrivenData data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (verified redirect to login).
- **External data allowed:** USGS [GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
  GBC/GE [INGENIOUS](https://gbcge.org/current-projects/ingenious/), and any licensed source.
- **Leaderboard:** [drivendata.org leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).

---

## The submission (downloadable now)

**One-click download:** `docs/index.html` — the file link is at the very top, so it is obvious what to download
and submit.

| Field | Value |
|---|---|
| File | `docs/downloads/wb-gems-doe-3-stepover-damagezone-35000d-20261026T215413Z-zeros.tif` |
| Unique name | `WB-GEMS-DOE-3-STEPOVER-DAMAGEZONE-35000D-5D451566` |
| SHA-256 | `5d4515665dc8f3f31aa0249a32a56002f86aef199c2033cb39d836bc41adb059` |
| Dots | 35,000 (binary 0/1), strictly off-catalogue-trace |
| Grid | EPSG:32611, 3730 × 3292, 100 m, float32, whole array in [0,1], zero NaN |
| Format audit | **PASS** (13 checks on saved bytes) — fixes "Predicted values must be in range [0, 1]" |
| Uniqueness audit | **PASS** — max \|rho\| 0.0117 (≤ 0.90); 26.8% of dots within 3 px (≤ 70%) vs 58 registry rasters |
| Score estimate | **UNVERIFIED PROJECTION** — no organizer receipt, no label access; not a score |
| OK to download? | **YES** — research/audit |
| OK to submit? | **NOT YET organizer-cleared** — format + unique pass; score unverified |

**Verdict:** FORMAT_PASS / UNIQUE_PASS / SCORE_UNVERIFIED. Safe to download; the portal will accept the format.
Whether it improves the leaderboard cannot be confirmed without the private test labels and an organizer receipt.
See `evidence/run_card.json` and `docs/executive-summary.html`.

**Contrarian hypothesis (H_STEP-OVER):** every GEMSDOE high-scorer (0.2449–0.2778) dots **on** the mapped
USGS/INGENIOUS catalogue fault network. This submission dots strictly **off-trace** — in the fault damage zone
(100–700 m) and at dilational step-overs / relay ramps (400 m–1.5 km) — targeting off-catalogue blind geothermal
structures the private labels target. A different lane from the dotted-catalogue family.

---

## Executive summary (nine GEMSDOE sites)

Scope: GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, GEMSDOE36.

**Best scored file among the nine:** GEMSDOE32 `h33-h33-2-b2` = **0.2778** (owner-reported) — already submitted,
do not resubmit. All nine best files belong to the same dotted-catalogue duplicate family and are **not unique**
vs the other GEMSDOE sites. None is a fresh, unique submission to download and submit as an improvement.

See `docs/executive-summary.html` for the full table (file / live score / estimate / unique) and the
step-by-step "how to submit" instructions.

---

## Parallel-run protocol (must be followed)

1. **Lane:** stay inside the single method paragraph. If raster rank-correlation with any registry raster >
   0.90, or > 70% of dots fall within 3 px of one registry raster's dots → log as duplicate and stop.
2. **Reuse, don't rebuild:** use `scripts/evaluate_holdout.py` and `scripts/submission_writer.py`. Holdout =
   hide-and-recover: withhold whole fault segments with a buffer; derive catalogue features only from visible
   faults; mask visible faults pixel-exactly; score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel).
3. **Label every number** HOLDOUT-DTI (evaluator version, # withheld positives, 95% CI) or ORGANIZER-CONFIRMED
   (submission-page receipt). A projection is never written as a score.
4. **Leakage canary:** test each feature alone on holdout; AUC > 0.90 means leakage until proven otherwise.
5. **Run card:** hypothesis; mechanism; non-fault mimic process; holdout DTI + CI; correlation/overlap vs registry;
   raster sha256; validator output; submission name + note (≤ 140 chars); verdict promote / negative.
6. **Budget:** stop after 3 experiments or 2 hours. Promotion to a real slot is a separate selector step.

---

## Scripts

- `scripts/generate_submission.py` — generates the unique off-trace step-over / damage-zone submission TIF.
- `scripts/finalize_submission.py` — format audit + lane-uniqueness audit + writes `evidence/run_card.json`.
- `scripts/submission_writer.py` — writes validated -zeros / -nan GeoTIFFs; 13-point strict audit on saved bytes.
- `scripts/evaluate_holdout.py` — distance-weighted DTI (alpha 0.2, beta 0.8, 300 m kernel) + hide-and-recover
  holdout with spatial-block 95% CI.
- `scripts/uniqueness_audit.py` — Spearman \|rho\| ≤ 0.90 and ≤ 70% within-3px lane rules vs registry rasters.
- `scripts/download_competition_data.sh` — data placement (run on an unrestricted machine into `data/`; requires
  DrivenData login for the competition rasters).

Run: `python scripts/generate_submission.py && python scripts/finalize_submission.py`

---

## GitHub Pages site

The site lives in `docs/` and is served by GitHub Pages:

- `docs/index.html` — landing page with the one-click submission download and clear OK-to-submit status.
- `docs/executive-summary.html` — nine-site table + how to submit + ranked hypotheses.
- `docs/assets/site.css` — clean UI.

Enable Pages: repository Settings → Pages → Build and deployment → Source: **Deploy from a branch** → branch
`main`, folder `/docs`.

---

## Limitations & irregularities flagged

- No DrivenData auth → cannot auto-downhold training labels; holdout DTI / true score blocked until `data/`
  is populated from an unrestricted machine.
- GEMSDOE site scores are owner-reported; no submission-page receipt links raster hash to score.
- Public Dropbox assets (example_submission.tif, existing_faults.tif, gems-geodawn-numerical-features.tif,
  GEMS_96647.pdf) do not respond from this sandbox; reachable hosts: github.com, codeload.github.com,
  api.github.com, pypi.org.
- Leaderboard high cited variously as 0.4413 and 0.3195 — consult the live leaderboard before slot selection.
