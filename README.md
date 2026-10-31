# GEMS DOE review — current decision (2026-10-31)

## Read this first at every session

**Project decision: DO NOT DOWNLOAD OR SUBMIT any TIFF.** No current candidate is cleared or safe to download for submission. Historical TIFFs remain in the repository only as quarantined research artifacts. This review generated **no TIFF**, ran **no geological experiment or holdout**, selected **no slot**, and made **no upload**.

Why we stopped:

1. The reconstructed brief refers to a single assigned method-lane paragraph, but that paragraph is absent. Do not infer the lane.
2. The committed literal-registry audit records a hash-pinned owner-mirrored raster positive on all 5,167,373 cells of the mirrored sample footprint. Under the current finite-and-positive support rule, any nonempty in-footprint candidate would have 100% directed overlap, above the user's 70%/3-px stop. The evidence is conditional on owner mirrors; it does not authenticate the organizer's complete registry. The stop remains binding unless corrected through a documented, evidence-based protocol change.
3. The shared cached feature stack is absent, and the shared evaluator/writer runtime has not been restored or verified for an assigned lane. Historical copies in the repository are not a substitute.

The run card is [`evidence/session_2026-10-31_run_card.json`](evidence/session_2026-10-31_run_card.json). The generated site is [`docs/index.html`](docs/index.html); the status page has no direct TIFF links. See [`docs/downloads/LEGACY-DO-NOT-SUBMIT.txt`](docs/downloads/LEGACY-DO-NOT-SUBMIT.txt) for the exact inventory of historical TIFF/ZIP artifacts under `docs/downloads/`.

## Requested focus sites — executive comparison

The table's scores are **OWNER-REPORTED / UNVERIFIED**, not organizer receipts. `NOT ESTIMABLE` is deliberate: the repository has no validated leaderboard-calibrated estimate for these bytes. The filenames below identify historical artifacts; **none is a file to download for submission**. The overlap column is the maximum directed 3-px overlap with another pinned file in this nine-site set. It is not a full portal-registry audit; the separate literal witness stop blocks any new nonempty candidate.

| Site | Highest pinned historical file (research reference only) | Owner report | Score estimate | Unique in focus set? / status |
|---|---|---:|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | 0.2477 | NOT ESTIMABLE | No — 100.0% overlap with GEMSDOE25; DO NOT SUBMIT |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` | 0.2600 | NOT ESTIMABLE | No — 100.0% overlap with GEMSDOE30; DO NOT SUBMIT |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` | 0.2449 | NOT ESTIMABLE | No — 98.0% overlap with GEMSDOE24; DO NOT SUBMIT |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` | 0.2710 | NOT ESTIMABLE | No — 100.0% overlap with GEMSDOE25; DO NOT SUBMIT |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | 0.2600 | NOT ESTIMABLE | No — 100.0% overlap with GEMSDOE25; DO NOT SUBMIT |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` | 0.2708 | NOT ESTIMABLE | No — 100.0% overlap with GEMSDOE25; DO NOT SUBMIT |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | 0.2778 | NOT ESTIMABLE | No — 100.0% overlap with GEMSDOE36; DO NOT SUBMIT |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 0.2632 | NOT ESTIMABLE | No — 99.7% overlap with GEMSDOE27; DO NOT SUBMIT |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 0.2750 | NOT ESTIMABLE | No — 97.6% overlap with GEMSDOE27; DO NOT SUBMIT |

Evidence: [`evidence/focus_audit.json`](evidence/focus_audit.json), [`evidence/focus_files_verification_2026-10-29.json`](evidence/focus_files_verification_2026-10-29.json), and the generated [executive summary](docs/executive-summary.html). The byte comparisons use pinned public owner mirrors, not authenticated organizer files.

## GEMSDOE32 — reported 0.2778: what is and is not known

The **reported** 0.2778 is the highest of the nine owner-reported focus-site values, but it is not an organizer-confirmed score. A saved byte/mask audit says the 37,654-positive-cell B2 file is an exact subset of a 40,199-cell H27-4 base; 2,545 cells were removed near a mirrored fault catalogue. The most plausible metric mechanism is that pruning low-credit predictions can reduce false-positive mass while nearby predictions retain some distance-kernel credit. That is a hypothesis—not a verified causal explanation—because the hidden labels and a receipt linking the value to the exact bytes are unavailable.

The official metric uses α=0.2, β=0.8 and a 300 m triangular kernel. Known-fault pixels are reportedly masked from scoring, but this does not mean all neighboring pixels are masked. A previous related pruning experiment was only a scoped proxy: `HOLDOUT-DTI`, evaluator `gems57-pooled-hide-v2`, 11,321 withheld positives; proximity pruning changed 0.13520 [0.11846, 0.15306] to 0.13526 [0.11849, 0.15310], with paired Δ +0.000054 [ +0.000027, +0.000089 ]. Its holdout excluded the near-catalogue new-fault regime and did not score GEMSDOE32. It neither confirms nor disproves the reported 0.2778.

Full evidence-bounded explanation: [`content/why-0.2778.md`](content/why-0.2778.md). Official metric description: [DrivenData problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).

## New hypotheses — ranked by qualitative gain vs cost

These are research priorities, **not DTI estimates or submission choices**. A prior-art screen found that active THCS/FCHD code already uses GDR #1391 shallow 2 m probes, sinter/tufa, well/spring temperatures, silica/cation geothermometry, and volcanic-vent proximity. Those layers alone are not new. Existing earthquake-density, strain, radiometric-ratio/gradient, and raster-destriping features are also not new by themselves. Previously proposed Landsat, ECOSTRESS, simple focal-mechanism strike clustering, and raw GeoDAWN crossover ideas are not relabeled as new here.

1. **Positive well heat-flow residual corridors — medium-high potential / medium cost.** Use the point residual in the USGS Great Basin heat-flow release—not only its broad background map—after quality and sampling-density controls. A localized convective departure may indicate a concealed permeable conduit. Mimics: shallow groundwater circulation, lithologic thermal conductivity, exploration-well bias, depth/quality artifacts. The official USGS ScienceBase page is reachable and lists a 124.12 MB archive; no file/schema/license/AOI inspection has been done. **Top research candidate, not ready to implement.**
2. **Conservative-ion hydrothermal mixing residuals — medium potential / medium-high cost.** If suitable analytes exist in DOE GDR #1391 aqueous-geochemistry tables, test multivariate mixing residuals rather than another temperature or silica/cation geothermometer. Mimics: evaporation, lithology, well-screen mixing, contamination, sampling bias. The official GDR page is reachable and states CC BY 4.0; the archive/schema and AOI fields were not checked. **Conditional, not viable until fields are confirmed.**
3. **Focal-mechanism stress inversion projected onto blind geophysical lineaments — low-to-moderate potential / medium-high cost.** Infer stress from USGS ComCat focal-mechanism products and evaluate independent lineament orientations, rather than earthquake density alone. Mimics: quarry/induced events, sparse mechanisms, nodal-plane ambiguity, lithologic contacts. The official API docs support `producttype=focal-mechanism`, but the regional query did not return and coverage is unknown. **Not viable until a coverage screen succeeds.**

No candidate is currently eligible for a holdout. The assigned lane is missing, the literal registry stop is active, and the shared cache/runtime is unavailable. Details and source checks: [`knowledge/preregistration-2026-10-31.md`](knowledge/preregistration-2026-10-31.md), [`evidence/preregistration_2026-10-31.json`](evidence/preregistration_2026-10-31.json), and [`evidence/official_source_check_2026-10-31.json`](evidence/official_source_check_2026-10-31.json).

## Current official public leaderboard feed

The official leaderboard was fetched in three page chunks on **2026-10-31** (exact fetch time not exposed). Captured values: rank 1 **0.4544**, rank 2 **0.3925**, rank 25 **0.3396**, rank 26 **0.3396**, and rank 50 **0.3195**. Thus 0.3195 is rank 50 in this observation, not the leader. These are public scores for other entries—not project-file scores, receipts, or private/final results. The automated HTMX refresh was not run in this session; the dated manual observation and feed record are [`evidence/leaderboard_observation_2026-10-31.json`](evidence/leaderboard_observation_2026-10-31.json) and [`registry/leaderboard.json`](registry/leaderboard.json). Separately, the official GitHub API identity monitor fetched all nine focus repositories; all nine `main` HEADs differ from the 2026-10-26 audit baseline. That indicates commit movement only—it does not show that a pinned TIFF or score changed. See [`evidence/latest-upstream-check.json`](evidence/latest-upstream-check.json).

## Submission and download status

**There is no TIFF from this review and no safe download. Do not submit any historical TIFF.** The `docs/downloads/` and other repository TIFFs are legacy research artifacts; the generated site intentionally provides no direct TIFF or ZIP links. A local format check, owner report, projection, or public leaderboard score is not a submission receipt.

The [submission guide](docs/how-to-submit.html) describes the required future checks. Before any future experiment: confirm the exact lane, resolve the registry stop through a documented protocol correction, restore the shared feature cache and evaluator/writer, verify source provenance, then run the preregistered spatially blocked holdout and leakage canaries. Any later slot decision belongs to a separate selector; no slot has been used here.

## Historical lane records

The [AMDC lane dossier](docs/amdc/index.html), [LBCAL lane archive](docs/lbcal/index.html), and all other lane pages under `docs/` are research-only historical records. They inherit the project-wide **DO NOT SUBMIT** decision and provide no approved TIFF download.

## Standing safeguards and values

Keep **Maximize P(Win)** and **Own the Outcome** central. Negative findings are deliverables. Preserve these constraints in every session:

- Stay inside one explicitly assigned method lane. Do not infer a missing paragraph.
- Check absolute surface rank correlation before placement; stop if it exceeds 0.90. Stop if more than 70% of final dots are within 3 px of any registry raster. Do not silently exempt dense/lattice comparators.
- Reuse the shared cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`; do not fork. Hold out whole fault segments with a buffer; derive catalogue features only from visible faults; pixel-exactly mask visible faults; use pooled DTI (α=0.2, β=0.8, 300 m triangular kernel).
- Test each feature alone. AUC >0.90 is leakage until explained.
- Label an actual score only `HOLDOUT-DTI` with evaluator version, withheld-positive count, and 95% CI, or `ORGANIZER-CONFIRMED` from an actual receipt. A projection is never a score.
- Stop after three experiments or two hours. No real slot selection in this lane; promotion is a separate selector step. Keep slot usage at zero unless that selector explicitly approves.
- End an eligible experiment with one JSON run card: hypothesis/mechanism/mimic, holdout and CI, registry correlation/overlap, raster SHA-256, validator results, submission name/note ≤140 characters, and promote/negative verdict.
- Never copy a previous submission. Never call a TIFF safe unless it is distinct, holdout-validated, unique, format-valid, and selector-approved. If a gate fails, clearly say no file is safe to download/submit.
- Use verified official sources, record exact access limits, and do not imply geothermal-vent labels when the official competition target is faults.

## Three review passes and next work

This review: (1) audited the nine focus files, existing feature code, lane/uniqueness constraints, and candidate novelty; (2) corrected the active builder/checker so stale candidate downloads cannot be published and made the current decision fail closed; (3) refreshed the dated public-board evidence, tested the site and repository, and rechecked the prompt and claims. Details and any remaining limitations are in [`knowledge/review-2026-10-31.md`](knowledge/review-2026-10-31.md).

Next: obtain the missing lane assignment and resolve the protocol definition with evidence; verify the shared runtime/cache; inspect only the official datasets needed for the eligible lane; then rerun gates before any experiment. Recheck the official deadline, account quota, and source product terms before a separate selector action.

## Standing task prompt — preserved for every session

The original chat prompt is not independently recoverable as an authenticated verbatim transcript. This is the complete operational brief preserved from the available session instructions; see [`PROJECT_PROMPT.md`](PROJECT_PROMPT.md) for the fuller reconstruction. Read this section and the current negative decision at the start of each session.

> Review the repository, focusing on GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36. Give an executive summary for each with the historical file, score estimate, and uniqueness status. Explain the reported GEMSDOE32 0.2778 and whether a better result can be demonstrated. Rank 3–5 distinct geological hypotheses by expected gain and cost; name the specific layers, physical signature, why each may detect faults missing from the USGS/INGENIOUS catalogue, how it differs from existing implementation, and a named non-fault mimic. Validate the top eligible candidate on the shared spatially blocked holdout before any slot decision.
>
> Produce a unique, format-valid TIFF only when every gate passes; make its download/submission status unambiguous. Include a practical submission guide, official-source citations, a current public feed, and three review passes. Preserve this prompt in README and prepare a PR/merge when requested.
>
> **Parallel-run protocol:** remain in one assigned method lane. Before placement, test surface rank correlation; stop if |Spearman| >0.90. Stop if >70% of final dots lie within 3 px of any registry raster. Reuse the shared cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`—never fork. Hold out whole fault segments with a buffer, derive catalogue features only from visible faults, pixel-exactly mask visible faults, and score pooled DTI (α=0.2, β=0.8, 300 m triangular kernel). Test each feature alone; AUC >0.90 is leakage until explained.
>
> Label scores only as `HOLDOUT-DTI` with evaluator version, withheld-positive count, and 95% CI, or `ORGANIZER-CONFIRMED` from an actual receipt. A projection is never a score. End an eligible experiment with a JSON run card containing hypothesis, mechanism, named mimic, holdout/CI, registry correlation/overlap, raster SHA-256, validator output, submission name and ≤140-character note, and promote/negative verdict. Stop after three experiments or two hours. No real slot selection in this research lane; promotion is separate. Treat negative results as deliverables.
>
> Keep **Maximize P(Win)** and **Own the Outcome** central. Do not copy an old submission. Cite verified official sources, flag irregularities, do not hallucinate, and never state that a TIFF is safe to download/submit unless the exact bytes clear all gates.

## Key official sources

- [DrivenData competition description, metric, and raster format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [USGS Great Basin heat-flow residual data release](https://doi.org/10.5066/P9BZPVUC)
- [DOE GDR #1391 INGENIOUS compilation](https://gdr.openei.org/submissions/1391)
- [USGS GeoDAWN data release](https://doi.org/10.5066/P93LGLVQ)
- [USGS ComCat FDSN event API](https://earthquake.usgs.gov/fdsnws/event/1/)
- [USGS Landsat Collection 2](https://www.usgs.gov/landsat-missions/landsat-collection-2)
- [NASA/JPL ECOSTRESS data products](https://ecostress.jpl.nasa.gov/data)

## Build and checks

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build_site.py
.venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q
```

Checks establish repository/site consistency, not scientific performance or organizer acceptance.
