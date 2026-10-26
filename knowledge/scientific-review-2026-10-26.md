# Geological and metric review — 2026-10-26

**Status: desk research and analytical reasoning, not an experiment, a new score or a
resource discovery.** The actual competition target is surface faults; a proxy for
permeability or geothermal potential is not ground truth for that target. Frozen
hypotheses and named mimics are in [the preregistration](preregistration-2026-10-26.md).

## Geology: what is plausible and what is not established

The Basin and Range provides a plausible physical basis for examining structural
continuity and disruption, because deformation can create connected fracture networks.
A USGS-hosted study of [stress concentrations at discontinuities at Salt Wells and Bradys](https://pubs.usgs.gov/publication/70196066)
models stress transfer and compares it with proxies for modern fluid circulation; it
also explains how mineralization can seal pathways. A separate [USGS-hosted Great Basin
structural review](https://www.usgs.gov/publications/structural-discontinuities-and-their-control-hydrothermal-systems-great-basin-usa)
finds strong, localized modeled effects at stepovers and terminations. These examples
justify *testing* spatial discontinuity hypotheses, not assuming every magnetic edge,
mapped intersection or predicted fault conveys active flow. Fault slip, age, lithology,
stress, sealing, recharge and sufficient temperature also matter.

The [southern Gabbs Valley play-fairway study](https://www.usgs.gov/publications/discovery-a-blind-geothermal-system-southern-gabbs-valley-western-nevada-through)
describes a displacement-transfer setting and intersecting structures supported by
multiple geophysical measurements, a shallow temperature anomaly, and warm
temperature-gradient wells; the system lacked obvious surface manifestations. That is
a historical field example, **not** independent validation of this repository's model
or evidence that a particular competition dot identifies a vent. The [INGENIOUS
project](https://gbcge.org/current-projects/ingenious/) describes regional-to-prospect
integration and lists data sources, but importing its products requires confirming
coverage, license, temporal availability, independence from the labels, and resolution.

## Data interpretation and confounders

- [USGS GeoDAWN metadata](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7)
  describes magnetic and radiometric products and variable terrain clearance. Its two
  survey areas use different flight specifications: nominal flight-line spacing is
  200 m in Area 1 versus 400 m in Area 2. Acquisition blocks, flight direction, altitude,
  leveling and regridding may produce lineaments. Directional features should be tested
  against acquisition geometry, not merely rewarded for being linear.
- Magnetics respond to contrasts in rock magnetization and radiometrics to near-surface
  composition; they are **not measurements of fault presence or of subsurface heat**.
  Gravity may identify density boundaries but is also sensitive to lithology and basin
  geometry. Paired gradients can be concordant at a geological contact without faulting.
  Spatial support and source resolution must be inspected before combining a coarse
  field with a 100 m prediction grid.
- [USGS Great Basin detrended elevation maps](https://www.usgs.gov/data/maps-elevation-trend-and-detrended-elevation-great-basin-usa)
  explicitly highlight basin-and-range structure, using a 30 m DEM and alternative
  smoothness choices (CC0 1.0). Detrending is therefore a sensible regional-context
  feature, but a scarp, stream incision, road cut, alluvial-fan edge or survey artifact
  can yield similar morphology. Upsampling adds pixels, not new geological information.
- No extra external product was ingested in this session. The 19-band owner mirror has
  verified hashes but ambiguous band meanings, particularly `tc`; authenticate the
  official file and descriptions before interpreting a band or asserting data license.

## Metric mechanics and the H33 question

The official [distance-weighted Tversky formula](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
uses a triangular 300 m kernel, truth-side nearest-prediction coverage, and
prediction-side nearest-truth penalty, with α=.2, β=.8. For binary predictions, write
`T = TPw`, `F = FPw`, `G = number of truth pixels`, and
`D = T + αF + β(G − T) + ε`. Adding a new positive at a currently zero pixel changes
truth credit by `c ≥ 0` and adds false-positive penalty `f = 1 − max_g k(distance)`.
Its exact one-step effect improves the score iff

```
c * D > T * ((1 − β) * c + α * f)
```

The marginal truth gain can exceed one because one predicted pixel can add partial
coverage to several truth pixels. Redundant dots have reduced `c`, while nearby dots
can also reduce the penalty `f`. At the default parameters, this clarifies why sparse,
spatially distributed candidates and catalogue-distance masks might help a local proxy;
it does **not** identify an optimal dot count or prove the original 0.2778 claim.

The independently decoded H33 B2 raster has 37,654 positive pixels and is the exact
subset of a 40,199-dot H27-4 base obtained by deleting 2,545 near-catalogue pixels.
This is a concrete difference in output, not a causal estimate: no authenticated upload
receipt, hidden test truth or controlled paired leaderboard experiment was available.
The H33 project's DTI/buffer explanation remains an informed hypothesis. It is therefore
not defensible to assign a new score to our unbuilt CSPES idea or claim it beats B2.

## Future evaluation design, conditional on resolving the blocking rule

1. Freeze one method lane, available data, source hashes, split seed and registry set.
   Construct spatial folds by hiding **whole segments with buffers**, not random cells.
   A buffer cannot by itself guarantee independent geology, survey blocks or catchments;
   report segment/block distribution and dependence explicitly.
2. For each fold, regenerate all catalogue-derived features from *visible* faults only,
   apply the pixel-exact visible-fault mask, and ensure transformations and thresholds
   are fit without withheld labels. Test each feature alone for AUC > .90 leakage; repeat
   using visible-only features. Probe acquisition-stripe and lithology-contact mimics.
3. Score with the shared evaluator, α=.2, β=.8, 300 m kernel, pooling the same folds
   and geography for candidate and incumbent. Report **HOLDOUT-DTI**, version,
   withheld positives, paired spatial-block 95% CI, and subgroup diagnostics. Confidence
   intervals quantify variation under the resampling design; they do not correct for
   shared mapping omissions, geographic shift, label uncertainty or unobserved truth.
4. The mapped catalogue is incomplete: an unlabelled pixel is not automatically a known
   non-fault. Discovery claims require independent confirmation. Positive-only selection
   and repeatedly tuning to the same folds can overfit local proxies even with a CI.
5. Apply the actual pre-placement and final-dot uniqueness gates, then serialize with a
   shared writer compatible with the organizer's confirmed outside-footprint convention;
   reread exact bytes to validate range, dtype, masks, CRS, shape and transform. Only a
   separate slot selector can authorize upload. The present literal gate stops at step 0.
