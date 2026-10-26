# Repository review and scientific decision — 2026-10-26

## Decision first

**Verdict: negative / no submission.** This checkout does not contain the competition inputs or the shared evaluation/writing tools required by the stated protocol. No experiment was run, no new raster was built, and no TIF is approved for download or upload. This is deliberately fail-closed: a made-up TIFF or a copied prior TIFF would not be a valid completion.

The best historic result in the nine focus sites is GEMSDOE32's `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`, with **OWNER-REPORTED score 0.2778**. The reviewed public records did not provide a receipt that binds that file's bytes to an organizer score. The result is historical, belongs to the H19-5/D2.8 family, and is not unique under the owner-maintained cross-site audit. **Do not submit it again.** A new candidate's score estimate is **not computed**.

## What was inspected

### This checkout

- Branch: `arena/bc1cafda-wbggemsdoe3`; starting commit: `891b84e8ed7771a98bffc2041bd291dfedf9e15e`.
- `git ls-files` returned only `README.md`.
- There are no local competition rasters, `data/` cache, sample submission, registry, tests, scripts, evaluator, submission writer, or project template.
- `rasterio` is not installed in the current environment.
- The user's described scripts `scripts/download_competition_data.sh`, `scripts/prepare_data.py`, `scripts/evaluate_holdout.py`, and `scripts/submission_writer.py` do not exist in this checkout.

### Public references

- Cloned and inspected the official [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) at commit `aebe92f7c8a990f0e3443451b7a825d9afd6336b`. Its README directs users to download competition data from the competition website; its notebook demonstrates a U-Net baseline. It is not the shared fault-segment holdout / submission-writing template required by this run protocol.
- Read the public owner-maintained nine-site summaries and audits in [GEMSDOE27](https://github.com/buffedlizard55-lab/GEMSDOE27/blob/bef7ae8e8f63b69d299c9214c75988c8f5055f9c/knowledge/24_focus_sites_executive_summary_2026-10-26.md) and [GEMSDOE32](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/07806249f4ed3efe70b4fbf866183c32392b7853/evidence/nine_site_executive_audit_20261026.json), plus the [GEMSDOE32 focus-site analysis](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/07806249f4ed3efe70b4fbf866183c32392b7853/docs/research/focus-sites-executive-summary.md) and the H33 artifact audit.
- Downloaded the GEMSDOE32 H33 TIFF **only for byte-level review**. Its local SHA-256 is `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`, matching the public owner audit. I did not copy it into this repo or use it as a submission. Because `rasterio` is unavailable here, its metadata and pixel values were not independently re-read; the CRS/grid/range details below are owner-audit claims, not a validation performed by this checkout.

The focus-site data are normalized in [`reports/focus-sites-2026-10-26.json`](../reports/focus-sites-2026-10-26.json). This report uses conservative `OWNER-REPORTED (unverified)` labels for historical leaderboard numbers. Some older GEMSDOE32 records use stronger receipt language; a later GEMSDOE32 review says no byte-linked receipt is available. No receipt was accessible in this checkout, so the stronger label is not adopted.

## Focus-site executive table

Every historical score in this table is **OWNER-REPORTED (unverified here; no byte-linked organizer receipt was reviewed)**. These are not new estimates, not HOLDOUT-DTI results, and not proof of generalization. The `New-file estimate` is intentionally `N/A`: there is no new candidate or local evaluator. “Unique: no” reflects the owner-maintained audit and lineage; this checkout did not recompute pixel overlap.

| Site | Highest historic file stem (reference only; do not submit) | Historic result | New-file score estimate | Unique vs the other focus sites? | Decision |
|---|---|---:|---|---|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | **OWNER-REPORTED 0.2477** | Not computed | **No** — H19-5/D1.5 family; owner audit reports high overlap | Do not submit |
| GEMSDOE25 | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | **OWNER-REPORTED 0.2600** | Not computed | **No** — pixel-identical dot set to GEMSDOE30 D2.8 | Do not submit |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | **OWNER-REPORTED 0.2449** | Not computed | **No** — gap-closure addition on shared H19-5/D1.5 base; not a new independent field | Do not submit |
| GEMSDOE28 | `h36-1-rung30-blind-r1-20261003-b531dae0a36f` | **OWNER-REPORTED 0.2710** | Not computed | **No** — same dense H19-5/D2.8 pruning family; site files have `-nan` and all-finite variants | Do not submit |
| GEMSDOE30 | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | **OWNER-REPORTED 0.2600** | Not computed | **No** — pixel-identical to GEMSDOE25 D2.8 | Do not submit |
| GEMSDOE31 | `h27-4-solo-d28-20261004-8acb75e1` | **OWNER-REPORTED 0.2708** | Not computed | **No** — same positive-pixel mask as GEMSDOE28 H27-4 solo | Do not submit |
| GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | **OWNER-REPORTED 0.2778** | Not computed | **No** — nested H19-5/B2 prune; GEMSDOE36 is a near-superset | Historical reference only; do not submit |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | **OWNER-REPORTED 0.2632** | Not computed | **No** — tip/step-over additions to the same dominant family; not independently unique in the owner audit | Do not submit |
| GEMSDOE36 | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | **OWNER-REPORTED 0.2750** | Not computed | **No** — owner audit says it contains all H33-B2 dots plus 1,200 additions; Jaccard 0.969 (owner-audit measurement) | Do not submit |

**The one file to treat as the historical benchmark is H33-B2, not a file to submit.** There is no current replacement that passes the required gates. The most obvious download button on the site is therefore deliberately disabled and says **NO APPROVED TIFF — DO NOT SUBMIT**.

## Why H33-B2 is the historic focus-site high — and what that does not prove

### What the evidence supports

The owner-maintained audit describes a nested thinning/pruning sequence built from the H19-5 lineament field:

- The D2.8 parent is recorded at **OWNER-REPORTED 0.2600**.
- The H27-4/B1 solo rung is recorded at **OWNER-REPORTED 0.2708**.
- H33-B2 removes a further catalogue-proximal annulus from that base and is recorded at **OWNER-REPORTED 0.2778**.
- GEMSDOE36 adds dots to H33-B2 and is recorded at **OWNER-REPORTED 0.2750**.

In the H33 audit, the named B2 operation is removal of predictions within **200 m** of known catalogue faults; the resulting raster has **37,654** positive pixels. The owner audit lists `EPSG:32611`, a **3730 × 3292** grid, and values from **0 to 1** for its `-zeros` version. These are published audit facts, not a metadata check run in this checkout.

### Scientific interpretation

For the stated Tversky-style index, a prediction contributes through a **300 m triangular kernel**; nearby dots have overlapping credit fields. The pooled objective penalizes false-positive mass as well as missed hidden fault mass. A useful **MODEL identity (not a score)** makes the pruning logic explicit. If one unit of emitted prediction has kernel-integrated true credit `q`, it adds `q` to `TP`, `1-q` to `FP`, and removes `q` from `FN`. With the user-specified `alpha=0.2` and `beta=0.8` (so `alpha + beta = 1`), the denominator increases by `alpha` per unit. The index rises only if `q > alpha × current_DTI`. Thus, once a lineament family identifies the broad corridor, thinning dense adjacent predictions and removing dots whose *marginal hidden-fault credit* is below that break-even can improve the score without discovering any new structure.

This is a plausible explanation of the observed nesting, not a causal proof. A leaderboard result alone cannot separate better marginal precision from public/private split variation, parameter search, or catalogue-specific structure. The key generalization test is the user's stipulated hide-and-recover design: hold out whole segments with a buffer, derive all catalogue features from visible segments only, mask visible pixels exactly, and compare pooled DTI with spatial uncertainty. That computation was not possible here.

**Answer to “can we beat 0.2778?”** It is scientifically possible, but there is no defensible score projection for a new file from this checkout. No new TIF was generated, and no candidate beat the local holdout incumbent because there was no compliant local holdout run. The H33 number is a historical owner-reported score, not a target or a promise. A score higher than it must be demonstrated by an authorized, unique, leakage-screened candidate and an organizer receipt.

### Upstream holdout results are context, not this session's result

The GEMSDOE32 site publishes a later experimental comparison. For context only, its run cards report:

- **HOLDOUT-DTI 0.11696 [0.10053, 0.13204]** — evaluator `GEMSDOE32-HIDE-RECOVER-v3.0`, **22,232** withheld positives, `95% CI`; the published H38 arm.
- **HOLDOUT-DTI 0.0784 [0.0662, 0.0909]** — evaluator `GEMSDOE32-HIDE-RECOVER-v3.0`, **22,232** withheld positives, `95% CI`; the published H47 unique-allocation arm.

These are **published external run-card results, not rerun or reproduced in WBGGEMSDOE3**. The H47 run card marks its outcome negative. The GEMSDOE32 site also gives an LLI **PROJECTION** of **0.240–0.248** for H47; this is explicitly not a score and is not used as an estimate here. None of these artifacts is copied or offered for download.

## Four hypotheses for future review (proposal only; no experiment run)

The ranks below are qualitative research priorities, **not DTI values or forecasts**. “Not found” means not found in the owner-maintained summaries and run-card indexes inspected; it is not proof that no team has ever tried the idea. Before any experiment, the single authorized lane must be stated explicitly, and the shared registry/tooling must be available.

| Rank | Hypothesis and layers | Physical signature and why it could reveal uncatalogued faults | Difference / novelty check | Main non-fault mimic | Expected DTI impact (qualitative) | Cost and source/access check |
|---|---|---|---|---|---|---|
| 1 | **Depth-consistent basement step plus kinematic support.** Cached-stack candidates: `depth_to_base_surf`, `geod_2ndinv`, `tmi_vg`, `iso_grav_anom_vg`, `geod_shearrate`, `geod_dilaterate`, and `rtp` (band names listed in the public GEMSDOE32 prepared manifest). | Look for a laterally coherent step in magnetic/gravity source-depth or gradient features that is accompanied by a spatially aligned shear/dilation signal. A buried offset plus strain localization could mark a concealed fault outside mapped traces. | Different from simple lineament thresholding or re-spacing: require signed cross-domain depth/kinematic concordance and suppress isolated single-sensor edges. The exact composite was not found in the reviewed nine-site summary, but related Euler/depth, geophysics, and geodetic work exists; novelty is **unconfirmed**. | Lithologic contacts, basin margins, and airborne survey leveling/flight-line seams. | **Medium, conditional**; most feasible of these ideas because it could use the cached stack, but no numerical gain is justified. | **Medium.** No new external source if the shared cache contains these bands; this checkout does not contain that cache. The owner manifest is a secondary inventory, not proof that the data exist locally or are official inputs. **Not validated; do not implement yet.** |
| 2 | **Multi-epoch InSAR deformation-gradient persistence.** Sentinel-1 line-of-sight displacement and coherence time series (NASA/JPL OPERA DISP-S1 or an equivalent official Sentinel-1 archive). | Search for persistent, spatially localized shear/extension gradients and fault-tip deformation over repeat acquisitions; active blind structures can deform without a mapped surface trace. | The focus-site summaries reviewed do not show a time-series InSAR displacement layer. This is distinct from static magnetic/radiometric lineaments and point temperature data; global novelty is unverified. | Groundwater withdrawal/subsidence, landslides, geothermal reservoir compaction, atmospheric delay, and decorrelation. | **Medium–high if active structures are present; low for dormant faults.** No score forecast. | **High.** Named free official source: NASA/JPL OPERA DISP-S1 / NASA Earthdata. These hosts cannot be fetched in this sandbox; data coverage/terms/availability for the footprint were **not checked**. **Blocked, not viable until access is checked.** |
| 3 | **Geochemical mixing and geothermometry at springs/wells.** DOE GDR / USGS-NWIS or NGDS fluid chemistry, if spatially adequate: silica, chloride/boron, alkali ratios, and stable-isotope measurements. | Look for coherent fluid-composition gradients or mixing fronts along off-catalogue structural corridors; deep geothermal fluids can ascend along permeable faults. | The reviewed owner records describe probe temperatures and mapped geothermal manifestations, but do not establish a complete chemistry layer. This would test fluid composition rather than reuse temperature-point locations. | Bedrock lithology, evaporation, mixing of shallow waters, well sampling bias, and anthropogenic contamination. | **Medium, potentially specific but sparse.** | **High.** User-provided official starting link: [DOE GDR submission 1391](https://gdr.openei.org/submissions/1391); [USGS NWIS](https://waterdata.usgs.gov/nwis/). The source pages and chemistry coverage were **not fetched or checked** here. **Blocked, not viable until availability and licensing are verified.** |
| 4 | **Seasonally normalized land-surface thermal residuals.** Multiyear Landsat Collection 2 surface temperature plus vegetation/land-cover covariates (USGS Landsat Collection 2). | Estimate persistent warm/cool anomalies after season, elevation, aspect, and land-cover adjustment; fault-fed geothermal discharge can create repeated thermal/vegetation anomalies near concealed conduits. | Distinct from static airborne radiometrics and point temperature probes. The reviewed records do not verify that a multitemporal satellite-temperature anomaly was tested; the exact novelty remains unconfirmed. | Solar exposure, irrigation, urban/road heat, wildfire scars, emissivity differences, and seasonal soil moisture. | **Low–medium** because surface expressions are intermittent and confounded; no score forecast. | **High.** Named free official source: USGS Landsat Collection 2. The USGS host and local footprint coverage were **not checked** in this sandbox. **Blocked, not viable until access is checked.** |

### Top candidate and stop decision

The highest-feasibility proposal is the **depth-consistent basement-step plus kinematic-support** hypothesis, but it is only a proposal. This prompt does not identify a single scientific lane paragraph, and the current checkout has neither the cached features nor the shared evaluator. Therefore it was **not selected or run**. No weekly slot was touched. The exact next action is to restore the canonical cache/tools and supply an explicit, pre-registered lane; only then can a fold-local, spatially blocked holdout and single-feature leakage canary be run.

## Protocol and provenance irregularities

1. **Lane missing:** the user-supplied protocol says to stay in “the single method paragraph below,” but the prompt does not identify a specific lane/method paragraph. A GEMSDOE32 owner README independently notes that the lane paragraph was absent in the recorded prompt. We did not infer one from another site.
2. **No shared template in this repo:** the required evaluator/writer/cache do not exist here. Copying them from a sibling repository would violate “reuse, don't rebuild.”
3. **Score-provenance conflict:** older GEMSDOE32 evidence calls the H33 score organizer-confirmed; later GEMSDOE32 and GEMSDOE27 reviews state there is no receipt linking the bytes to a score. This report uses `OWNER-REPORTED` pending a visible receipt.
4. **Leaderboard conflict:** the prompt lists claimed current leaders `0.3195` and `0.4413`. A GEMSDOE32 owner-maintained snapshot records `0.4437` at `2026-10-26T21:20:39Z`; the DrivenData host was not fetched directly, so that snapshot is not independently confirmed here.
5. **Uniqueness registry ambiguity:** a GEMSDOE32 review says its literal overlap threshold can be triggered by space-filling calibration lattices and describes a null-calibrated diagnostic. The supplied protocol says to stop when any registry raster crosses the threshold and gives no exception. No exemption is applied here; a future lane must use the literal rule unless the user revises it.
6. **File variant ambiguity:** some historical site entries have `-nan` and all-finite/`-zeros` variants. The submission portal error quoted by the user is a range failure. Without the sample template, it is unsafe to choose a variant by filename; a future validator must check the whole required footprint for NaN/Inf and values in `[0,1]`, then compare CRS, shape, and transform against the actual sample.
7. **External access:** the official competition, USGS, DOE, NLR, and other non-GitHub hosts were not accessible under this sandbox's outbound-host allowlist. The links are provided for review, not described as fetched or verified.
8. **No portal authority:** no DrivenData login, receipt, or live weekly-cap/selector state is available here. No portal submission was attempted.

## Three-pass review record

- **Pass 1 — inventory and source inspection:** confirmed the local repository is a one-file stub; inspected the official reference repository and public focus-site audits; extracted the historical bests with provenance labels.
- **Pass 2 — challenge assumptions and edge cases:** compared GEMSDOE27 and GEMSDOE32 summaries; found the score-receipt conflict, leaderboard conflict, H28 TIFF-variant ambiguity, literal uniqueness-lattice ambiguity, and missing lane/tools/data. Corrected the conclusion to avoid treating historic scores or projections as current predictions.
- **Pass 3 — fail-closed acceptance check:** verified that no candidate is offered, no experiment or weekly slot was used, the run card records `NOT RUN`/`negative`, and the site visibly says **DO NOT SUBMIT**. The JSON report parses and the site links are checked locally; external official pages and raster-grid validation remain unverified because the inputs/hosts are unavailable.

## Remaining work / exact unblock list

1. Provide the required competition rasters through an authorized source: training features, labels, existing-faults/catalogue raster, and `sample_submission.tif`; do not store credentials in this repository.
2. Restore the canonical shared cache, `evaluate_holdout.py`, `submission_writer.py`, registry manifest/rasters, and validator into the shared template (or provide the path to that template). Do not copy a private version into this repo.
3. State the single lane/method paragraph explicitly and freeze its pre-registration. Resolve whether the uniqueness rule is literal for calibration lattices; this project will not silently exempt a registry raster.
4. Run the mandated hide-and-recover holdout and every-feature-alone leakage canary; record pooled `HOLDOUT-DTI`, evaluator version, withheld positives, and spatial-bootstrap `95% CI`.
5. Compare the continuous surface against every registry raster before placement, then compare final dots using the stated correlation/overlap rule. A duplicate is a stop, not a near-miss.
6. Use the canonical writer and automatically validate the final GeoTIFF against the actual sample grid and `[0,1]` range. Store the file hash and short note in the run card.
7. Only a separate selector may mark a candidate `promote`, after checking current quota and competition rules. Until then, the answer remains **no file to download or submit**.

## Source links for review

### Competition and official research sources

- [DrivenData competition](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem statement](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [About page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [Competition data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b)
- [NLR GEMS submission guidance PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE GDR submission 1391](https://gdr.openei.org/submissions/1391)
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611](https://epsg.io/32611)
- [Tversky index](https://en.wikipedia.org/wiki/Tversky_index)
- [USGS FDSN event service](https://earthquake.usgs.gov/fdsnws/event/1/) — named in the owner-site research; not fetched in this sandbox.

### Owner-maintained evidence (use for learning/audit, not as official contest receipts)

- [GEMSDOE24 site](https://buffedlizard55-lab.github.io/GEMSDOE24/)
- [GEMSDOE25 site](https://buffedlizard55-lab.github.io/GEMSDOE25/)
- [GEMSDOE27 site](https://buffedlizard55-lab.github.io/GEMSDOE27/)
- [GEMSDOE28 site](https://buffedlizard55-lab.github.io/GEMSDOE28/)
- [GEMSDOE30 site](https://buffedlizard55-lab.github.io/GEMSDOE30/)
- [GEMSDOE31 site](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/)
- [GEMSDOE32 site](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)
- [GEMSDOE33 site](https://buffedlizard55-lab.github.io/GEMSDOE33/)
- [GEMSDOE36 site](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/)
- [GEMSDOE32 H33 artifact audit](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/07806249f4ed3efe70b4fbf866183c32392b7853/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json)
- [GEMSDOE32 nine-site audit](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/07806249f4ed3efe70b4fbf866183c32392b7853/evidence/nine_site_executive_audit_20261026.json)
- [GEMSDOE32 H47 run card](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/07806249f4ed3efe70b4fbf866183c32392b7853/evidence/h47_run_card.json)
