# WBGGEMSDOE3 — auditable GEMS submission research

> **Project starting point:** Every session begins by reading this README and `docs/index.html`. Optimize for a scientifically defensible, validated competition result—not a submission-shaped artifact. Never claim a score, uniqueness, validation, or official confirmation without evidence. Never reuse a prior submission raster as the deliverable. A submission is eligible to download only after the project-specific holdout and exact format checks pass.

## Current state (2026-10-26)

This checkout contains only this README and Git metadata. It contains **no competition rasters, cached feature stack, labels, evaluator, submission writer, validation code, prior submission rasters, or training data**. Consequently this repository cannot presently run a holdout, calculate a DTI/CI, compare against registry rasters/dots, create a correctly georeferenced GeoTIFF, or establish that a new raster beats an existing score. No TIFF is provided; this is intentional rather than a failed/unchecked submission.

The prompt reports a GEMSDOE32 submission score of 0.2778, a leaderboard high of 0.3195, and elsewhere 0.4413. These are **user-provided figures, not independently verified**; their disagreement and the absence of dated leaderboard receipts must be resolved before using them as a baseline. All other historical scores below are likewise user-provided, not independently confirmed by this checkout.

## Non-negotiable process

1. **Read this file before each work session.** Follow the lane and experiment limits in the current task/run card. Do not promote or submit a candidate on the basis of an estimated score.
2. **Use shared template assets** (cached feature stack, common spatially blocked holdout evaluator, and submission writer) if/when they are present. Do not create a private fork of shared evaluation tooling. In a hide-and-recover test, withhold whole fault segments plus a buffer; derive catalogue-dependent features from visible faults only; mask visible fault pixels exactly; pool DTI with alpha 0.2, beta 0.8 and the specified 300 m triangular kernel. Record evaluator version, withheld positives and 95% CI.
3. **Leakage canary:** test each feature alone on the holdout. AUC > 0.90 is leakage until demonstrated otherwise.
4. **Novelty gate:** compare candidate surfaces and final dots against every available registry raster. Rank correlation > 0.90 or >70% of candidate dots within 3 px of one registry's dots means duplicate/lane drift: log it and stop. Never state uniqueness when the registry assets or a defined comparison are unavailable.
5. **File gate:** matching one-band GeoTIFF, CRS, shape and affine transform; finite predictions in [0,1] inside the footprint; explicit NaN/outside-footprint policy; writer/validator output; SHA-256. A failed or unrun gate means **NOT OK TO SUBMIT**.
6. **Competition integrity:** do not use hidden labels, leaderboard feedback as training labels, or other teams' private material. A score estimate is not an organizer-confirmed score. Only an actual submission-page receipt qualifies as ORGANIZER-CONFIRMED.
7. **Budget:** at most 3 experiments or 2 hours per run, whichever comes first. Promotion to a real slot is a separate selector decision subject to the competition's weekly cap.
8. **Run card:** record hypothesis; mechanism; named non-fault process that could mimic it; holdout DTI, evaluator, withheld positives and CI (or explicitly NOT RUN); novelty/correlation and overlap (or NOT TESTED); raster SHA-256 (or NOT CREATED); validator (or NOT RUN); proposed name and <=140-character note; verdict `promote` or `negative`. Do not put a projection in the score field.

## Site-by-site executive summary

This table transcribes the relevant scores as supplied in the request. It does **not** certify the scores, artifact existence, uniqueness, download availability, or suitability for a new submission. Exact duplicate comparison requires the actual rasters and registry dots; names alone are insufficient.

| Site | Highest user-reported result in the prompt | Reported score | Best evidenced option / uniqueness status |
|---|---|---:|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 | Highest listed here; user-reported only. Exact uniqueness **unknown**. |
| GEMSDOE25 | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | 0.2600 | Highest listed here; user-reported only. Exact uniqueness **unknown**. |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 | Highest scored listed; another entry has no score. Exact uniqueness **unknown**. |
| GEMSDOE28 | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | 0.2710 | Highest listed; user-reported only. Exact uniqueness **unknown**. |
| GEMSDOE30 | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 | Highest listed; user-reported only. Exact uniqueness **unknown**. |
| GEMSDOE31 | `h27-4-solo-d28-20261004-8acb75e1-nan` | 0.2708 | Only scored result listed; user-reported only. Exact uniqueness **unknown**. |
| GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | 0.2778 | Highest listed and highest among these nine by the supplied figures; user-reported only. Exact uniqueness **unknown**. |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 | Only result listed; user-reported only. Exact uniqueness **unknown**. |
| GEMSDOE36 | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 | Only result listed; user-reported only. Exact uniqueness **unknown**. |

**Download/submit recommendation:** none of these historical artifacts can be recommended as a *new unique submission* from the contents of this repository. No generated TIFF exists here and no candidate passes the prescribed holdout/novelty/format gates. Do not download/submit a candidate from this checkout yet. The reported 0.2778 is below both prompt-stated leaderboard figures (0.3195 and 0.4413), but comparisons are not reliable until the discrepancy and score provenance are resolved.

## Candidate hypotheses to test (not results)

Ranked by plausible incremental value versus effort, **not by measured DTI**. Relevant raster layers are not present in this checkout, and the existing implementation/feature inventory is unavailable, so distinctness from existing code cannot yet be confirmed. These are candidates for inspection against the shared template—not permission to implement outside it.

| Rank | Hypothesis and layer(s) | Target physical signature / rationale | Why it may find uncatalogued faults | Main confounder | Cost / key precondition |
|---|---|---|---|---|---|
| 1 | Multi-scale curvature-break concordance: DEM-derived profile/plan curvature plus slope, at scales matched to the DEM resolution | Persistent curvature sign transitions and aligned slope breaks | Structural breaks can continue beyond mapped traces; scale persistence may suppress isolated terrain edges | Lithologic contacts, erosional scarps, roads/terracing | Low–medium; DEM and exact footprint required. Check whether curvature transforms already exist. |
| 2 | Magnetic analytic-signal edge plus directional coherence: magnetic channels in the GeoDawn numerical-feature stack | Analytic-signal amplitude gradient / oriented edge continuity across scale | Magnetic contrasts can expose concealed basement discontinuities not represented by surface mapping | Intrusive/lithologic boundaries, cultural magnetic noise, acquisition seams | Medium; identify channels and nodata/line-correction behavior; verify these transforms are not already implemented. |
| 3 | Radiometric ratio-boundary consensus: K, eTh, eU (or verified equivalent channels) with local robust normalization | Coincident gradients or ratio breaks, downweighted where channels disagree | Alteration/weathering or structure-controlled drainage may create lineaments beyond known fault traces | Soil moisture, regolith, lithology, vegetation, survey striping | Medium; channel metadata and missingness required; no external data assumed. |
| 4 | DEM–magnetic cross-domain edge intersection | Spatially coherent edge intersections between topographic and magnetic gradients | Independent physical modalities agreeing away from mapped catalogue traces may highlight hidden structures | Contacts and non-tectonic landforms can align by chance | Medium; both layers and careful spatial null/holdout testing required. |
| 5 | Official mapped geology contact-distance negative control, not a primary predictor | Test whether apparent edge signal is merely a lithologic contact effect | Separates structural evidence from a major non-fault mimic; can improve calibration rather than directly add faults | Map scale/generalization and imperfect contact mapping | High if no geology layer already provided; needs official, freely obtainable mapped-geology data for the exact footprint before viable. Do not proceed until availability/licensing is verified. |

**Top candidate for the first test:** rank 1, only if DEM is in the shared cached stack and the template does not already contain the transforms. This is a *proposed test*, not a validated winner. Under the requested rule, do not touch a submission slot unless spatially blocked holdout DTI and uncertainty beat the current holdout best. Since neither evaluator nor holdout data exists here, validation is **NOT RUN** and no candidate can pass that gate.

## Submission checklist and limitations

To make a genuinely auditable download-ready submission, this checkout needs (with appropriate competition permissions): the official sample submission/template raster, training features, labels or permitted training labels, cached feature stack, shared evaluator and writer, plus registry prediction rasters/dots for novelty screening. The request itself notes DrivenData data access redirects to login; this repository has no authenticated access and must not fabricate or bypass it. Place authorized data in the project's documented `data/` location; keep large/private data out of Git. Then implement/run the shared protocol, test each feature alone, assess the candidate against the holdout best and registry, write to the exact official geospatial template, and independently validate the file before exposing a download button.

Competition entry is performed on DrivenData, not by this repository. Never expose a “ready” download link unless the artifact and every gate above are real and reproducible. A concise submission note should state the tested mechanism, not promise a leaderboard score.

## Primary references supplied for manual review

- [DrivenData competition overview and rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [About/resources](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [Competition data page (login may be required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Competition leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDawn airborne survey dataset](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [GBC current projects / INGENIOUS](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611](https://epsg.io/32611)
- [Submission guidance PDF supplied in request](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

These links were supplied by the user; their current contents and availability have not been independently fetched in this minimal checkout. Treat external claims as unverified until checked against the linked source.

## Current run card (honest status)

```json
{
  "hypothesis": "Multi-scale DEM curvature-break concordance; proposed, not tested",
  "mechanism": "Persistent profile/plan curvature transitions aligned with slope breaks may indicate structural lineaments beyond mapped traces",
  "named_non_fault_mimic": "Lithologic contacts and erosional scarps",
  "holdout_dti": "NOT RUN (evaluator, labels and cached feature stack absent); CI NOT AVAILABLE",
  "correlation_overlap_vs_registry": "NOT TESTED (registry rasters/dots absent)",
  "raster_sha256": "NOT CREATED",
  "validator_output": "NOT RUN; no TIFF exists to inspect for NaN, [0,1], CRS, shape or transform",
  "submission_name": "NONE",
  "submission_note": "No validated candidate artifact; do not submit",
  "verdict": "negative"
}
```
