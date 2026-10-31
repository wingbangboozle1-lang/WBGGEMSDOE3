# Protocol — new-fault lane, 2026-10-31

This lane answers one question: can a map built only from the organizer's **published** catalogue and
published telemetry score on the **privately withheld** fault subset? Everything below is fixed before
the final holdout run and is implemented once in shared code (`src/newfaults/`, `src/gemsw/metric.py`).

## 1. Data and definitions

| Item | Value |
|---|---|
| Telemetry | 19 bands, EPSG:32611, 100 m, 3730 × 3292, origin 243350 / 4508550 |
| Catalogue | `data/official/labels.tif`, SHA-256 `7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093` |
| Label meaning | 1 = mapped fault, 0 = mapped absence, NaN = outside the sample footprint |
| Footprint | 5,167,373 cells (`labels >= 0`) |
| Metric | `gemsw.metric.dti_binary`, α = 0.2, β = 0.8, R = 3 px (triangular kernel), visible catalogue masked as known |

## 2. Holdout design (hide-and-recover)

1. The catalogue is split into 8-connected **segments** (3,199 components).
2. Each fold hides 20 % of catalogue **pixels**, drawn segment-by-segment and stratified over four
   map quadrants, so the hidden set is interleaved rather than one corner of the map.
3. Hidden segments are dilated by 2 px to form the hide zone. Nothing in the hide zone is used for
   training: it supplies neither positives nor negatives.
4. **All fold-local features are rebuilt from the fold's visible catalogue only** — including the
   distance-to-catalogue channel and the corridor density. No hidden pixel can reach the prediction.
5. Scoring masks the visible catalogue (dilated 1 px) as known, exactly as the organizer masks known
   faults.

Three folds are used (seeds 0/1/2 → `seed + 1000·fold`), with 12,368 / 12,250 / 12,331 withheld
pixels.

## 3. Uncertainty

* 300-rep **block bootstrap**, 256-px blocks, on the decomposable per-truth-pixel TP credit and
  per-dot FP penalty. Blocks are drawn with replacement over the block grid, so spatial
  autocorrelation is respected.
* **Paired deltas** reuse the identical block draws for the candidate and the baseline
  (`holdout.paired_bootstrap_delta`), so block-to-block variance cancels and the interval answers the
  question "is this better than that, on the same ground?".

## 4. Emission geometry

`prior = Gaussian(distance-free density of visible catalogue, σ = 24 px)`; keep the band
`3 ≤ d_vis < 12 px`; accept candidate pixels in descending prior order with a hard **4 px minimum
separation** (greedy thinning). Dots are never placed on a known fault or outside the footprint.
The shipped file applies this to the full published catalogue; the holdout applies it to each fold's
visible catalogue.

## 5. Gates

| Gate | Threshold | Where |
|---|---|---|
| HOLDOUT-DTI vs matched random | strictly greater on every fold | `holdout_final.json` |
| HOLDOUT-DTI vs best registry file | strictly greater on every fold | same |
| Paired Δ 95 % CI lower bound | > 0 on every fold | same |
| Leakage canary | every channel tested, max \|AUC−0.5\|+0.5 ≤ 0.90, positive control > 0.90 | `leakage_canary.json` |
| Uniqueness | 3-px dot overlap ≤ 70 %, \|Spearman\| ≤ 0.90, no byte duplicate | `uniqueness_*.json` |
| Format | saved bytes re-read: single band, float32, CRS/shape/transform, values in [0,1], no NaN/Inf, positives inside footprint | `build_newfaults_submission.validate` |

The release gate (`src/gems_project/site_gate.py`) recomputes all of these from disk. If any input is
missing or fails, the decision becomes `DO-NOT-SUBMIT` and the site removes the download button.

## 6. What this protocol cannot do

* It cannot audit registry entries that are not present locally. The registry index lists 522
  entries / 296 unique dot masks; 28 were available. This is disclosed as a scope limit rather than
  claimed as completeness.
* It cannot produce a leaderboard estimate. `HOLDOUT-DTI` is a local proxy, and the nine focus
  rasters all score ≤ 0.105 here while their owners report 0.24–0.28 on the platform.
* It cannot prove the organizer's withheld subset looks like the holdout's withheld segments. That
  remains an assumption, stated as a residual risk.
