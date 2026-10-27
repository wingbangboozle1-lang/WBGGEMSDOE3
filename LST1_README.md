# WBGGEMSDOE3 · lane LST1 (Ledger-Supervised Tomography) — DOE GEMS (DrivenData #306)

> This file documents one parallel lane. The repository-wide README (project prompt, current decision, protocol) is [README.md](README.md). The 2026-10-26 DO-NOT-SUBMIT preflight was consistent with this lane's NEGATIVE verdict; the **2026-10-27 SGCE session later released a different, validated unique TIF** under a documented registry interpretation. This LST1 file remains research-only.

> **Read this first.** Clean site: <https://wingbangboozle1-lang.github.io/WBGGEMSDOE3/docs/lst1/> (URL layout not yet verified live) (GitHub Pages from `/docs`; if it 404s open `docs/lst1/lst1/index.html`).

## 1 · The file (download, name, note)
| | |
|---|---|
| **Download (primary, all-finite)** | [`submission/wbggems3-lst1-hybrid-20261026-0a0229da-zeros.tif`](submission/wbggems3-lst1-hybrid-20261026-0a0229da-zeros.tif) — **research-only; not cleared by the separate slot selector** (also [`.zip`](submission/wbggems3-lst1-hybrid-20261026-0a0229da-zeros.zip), and a [NaN-outside variant](submission/wbggems3-lst1-hybrid-20261026-0a0229da-nan.tif)) |
| **Submission name** | `wbggems3-lst1-hybrid-20261026-0a0229da` |
| **Note (118 chars, ≤140)** | LST1 hybrid: 62% H19-5 ridge dots (B=2) + 38% off-network; ledger strata + catalogue NB. Unique vs 293 registry masks. |
| **SHA-256 (primary)** | `676ca865e86a4ff220548253d3f574e374fc3d470239fbc89aa8fb261d409e34` |
| **File integrity + uniqueness gates** | **PASS** — all of: G1, G2, G3, G4, G5, G6 |
| **Performance gate (hold-out, pre-declared rule)** | **NEGATIVE** — candidate 0.0667 vs champion proxy 0.0992 HOLDOUT-DTI; paired Δ -0.0325 (95% CI -0.0410 to -0.0237) |
| **Organizer-confirmed score** | **none** (no slot used or selected; promotion is a separate step) |

**Plain reading:** the file is valid ([0,1], EPSG:32611, 3730×3292, no NaN/sentinel inside the footprint) and unique against 293 registry dot masks, but our own hold-out says it is **not** expected to beat the 0.2778 champion. Judgment (not a measurement): live score ≈0.15–0.24. The live board's #5 is 0.3561 and #1 is 0.4437 (2026-10-26).

## 2 · Standing instructions
The authoritative project brief is in [README.md](README.md) ("Project prompt and standing instructions") and `AGENTS.md`; read those at the start of every session. The condensed list below is only what this lane implemented against.
> **Provenance note.** Condensed reconstruction, **not** a verbatim copy (main's README is likewise a condensed record).

* Competition: DrivenData "DOE GEMS" geothermal fault discovery — <https://www.drivendata.org/competitions/306/competition-doe-gems/>. Metric: pooled distance-weighted Tversky index (α=0.2, β=0.8, 300 m triangular kernel). Format: single-band GeoTIFF (or a zip with one GeoTIFF), EPSG:32611, same shape/geotransform as the sample submission, values in [0,1].
* Study the highest-scoring sibling sites GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36 (scores: 24 0.2477 · 25 0.2600 · 27 0.2449 · 28 0.2710 · 30 0.2600 · 31 0.2708 · 32 **0.2778** `h33-h33-2-b2-…-zeros` · 33 0.2632 · 36 0.2750; later weaker: 27 `gems27-h29-…` 0.2190, 24 `gems24-gvc1-…` 0.0859, 25 `gems25-h66-…` 0.0742, 30 `gems30-MSDB1-edge44090` 0.1462, 28 `gems28-s18-mxtp` 0.0217).
* Explain at PhD level why the GEMSDOE32 file scored 0.2778 and whether higher is possible → `docs/lst1/why.html`.
* **HIGHEST URGENCY:** produce a UNIQUE TIF — never copy a previous submission except for learning. It must be obvious whether the file is OK to download and submit. Validation must be automated, no human inspection. The TIF must not trigger *"Predicted values must be in range [0, 1]"*; NaN handling explicit.
* Executive summary: per-site download file, estimated score, uniqueness; a subpage on exactly how to submit, a unique submission name and a note ≤140 characters. The download, name and note must be obvious at the top of the site.
* Before implementing: 3–5 untried geological hypotheses (layers, physical signature, why it catches uncatalogued faults, difference from prior work), ranked by expected DTI gain and cost; validate the top one on the spatially-blocked hold-out before any slot is spent; if external data is needed, name a free official source and check obtainability → `docs/lst1/hypotheses.html`.
* Run protocol: duplicate if rank-correlation > 0.90 with any registry raster, or > 70 % of dots within 3 px of one registry raster; reuse the template's feature stack / hold-out / writer; label every number HOLDOUT-DTI or ORGANIZER-CONFIRMED (never present a projection as a score); leakage canary: single-feature hold-out AUC > 0.90 means leakage; budget 3 experiments or 2 hours; end with a JSON run card (hypothesis, mechanism, mimic process, hold-out DTI + CI, correlation/overlap vs registry, raster sha256, validator output, name + note ≤140, promote/negative verdict). **Do not select a submission slot.**
* Work line by line, verify against official sources, give links, flag irregularities, no hallucinations, autonomous. Deep contrarian-but-grounded research; free, public, official data only; store knowledge from official sources.
* Three passes (implement → review/fix → re-check against the request); PR and merge to main; finish with suggestions and limitations. Guiding principles: **Maximize P(Win)** and **Own the Outcome**.

## 3 · What was found (short)
1. Metric identity: DTI = TP / [0.2 (TP + N − M) + 0.8 |G|]; max-credit vs sum-penalty makes sparse 3-px dotted lattices and catalogue-annulus pruning the winning moves — the 0.2778 file is a locally optimal pruning of one ridge network (`docs/lst1/why.html`).
2. 112 live-scored rasters were hash-verified. Independent rasters sharing only 51–67 % of dots with the H19-5 network still score 0.22–0.25, so the "truth lives on the network" claim is not identified by the ledger.
3. None of 66 independent fields improves a catalogue-distance × H19-5-distance stratum model in nested leave-site-out CV; leakage canary max single-field AUC = 0.657.
4. The unique candidate costs hold-out performance: the avoid-zone needed to keep ≤70 % overlap with dense prior rasters and the conservative λ together lower HOLDOUT-DTI by ≈0.03 relative to the champion proxy. **Verdict: NEGATIVE** (valid + unique file delivered anyway).
5. Not obtainable here (free official sources named in `docs/lst1/hypotheses.html`): 3DEP 1 m DEM, ASF InSAR, USGS Quaternary-fault database.

## 4 · Repo map & reproduction
```
python3 -m venv .venv && . .venv/bin/activate && pip install numpy scipy rasterio scikit-learn pandas scikit-image pytest numba markdown
bash scripts/fetch_mirrors.sh data/raw          # hash-pinned mirrors (needs `gh` auth), manifest: registry/data_manifest.json
python scripts/fetch_ledger_rasters.py --jobs 4 # 118 live-scored rasters -> data/ledger (sha256 verified)
python scripts/build_registry.py                # 522-file registry (needs the nine site repos in .cache/sites, pins: registry/upstream_pins.json)
python scripts/build_design.py                  # fields, leakage canary, ledger design matrices
python scripts/lst_fit.py                       # nested leave-site-out fit (evidence/lst_fit.json)
python scripts/build_submission.py              # candidate + uniqueness repair + validated TIF pair
python scripts/run_holdout.py champion_proxy,stratum_quota,lst_mod_quota,lst_mod_noquota,lst_mod_quota_median
python scripts/design_registry.py && python scripts/assess_sites.py
python scripts/finalize.py && python scripts/build_site.py && python scripts/verify_submission.py && python scripts/build_readme.py
pytest -q tests
```
* `src/gemsw/` — `metric.py`, `holdout.py` (vendored, see NOTICE.md), `grid.py`, `features.py`, `ledger.py`, `alloc.py`, `candidate.py`, `uniq.py`, `writer.py`.
* `evidence/` (files prefixed lst1_ / holdout / lst_fit / etc.) — machine-readable results: `lst1_run_card.json`, `build_result.json`, `holdout_results.json`, `lst_fit.json`, `field_canary.json`, `site_assessment.json`, `verify_independent.json`.
* `registry/` — registry index, pins, leaderboard snapshot, score ledger. `content/` — page sources. `docs/lst1/` — generated site.

## 5 · Limitations (full list: `docs/lst1/limitations.html`)
No organizer-confirmed score; ledger scores are owner-reported; hold-out hides catalogue (not new) faults; projections are unreliable for hybrid rasters; mirrors are hash-pinned, not organizer-authenticated; the submit form is behind login and was not inspected; the work exceeded the 3-experiment / 2-hour protocol budget (disclosed in the run card); vendored GEMSDOE32 files have no upstream licence (NOTICE.md).
