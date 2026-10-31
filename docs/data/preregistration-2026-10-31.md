# Preregistration — genuinely distinct candidate tests, 2026-10-31

**Status: research candidates only. No experiment, holdout, candidate TIFF, or slot action was run.** This review creates no file safe to download or submit. Machine-readable record: [`evidence/preregistration_2026-10-31.json`](../evidence/preregistration_2026-10-31.json).

## Stop and readiness

The required lane paragraph is absent from the reconstructed prompt; no method lane is assigned and none is inferred. The literal uniqueness stop is also active: the hash-pinned owner-mirrored witness is positive on all 5,167,373 cells of the mirrored sample footprint. Under the repository's finite-and-positive support rule, any nonempty in-footprint candidate would have 100% directed 3-px overlap, above the user's 70% stop. This is conditional on owner mirrors, not organizer-authenticated registry completeness. The shared feature cache is absent; the assigned shared evaluator/writer runtime was not restored or validated. **No candidate surface or holdout may be built under the current protocol.**

The scores on the nine-site table are owner/user reports, not receipts. The public leaderboard is a separate time-dependent observation. No projection is a score estimate.

## Novelty screen before ranking

The active THCS/FCHD code already includes DOE GDR #1391 2 m temperature probes, paleogeothermal sinter/tufa, well/spring temperatures, silica/cation geothermometry, and volcanic-vent proximity. The broader code also includes earthquake distance/density, geodetic strain, raw radiometric ratios/gradients, and raster-domain destriping. Those layers alone are not new hypotheses.

Prior repository notes already propose H4-XOVER, H5-LANDSAT, ECOSTRESS thermal anomalies, and simple focal-mechanism strike clustering. They are not counted here as new ideas. A line-level crossover test or a Landsat/ECOSTRESS layer alone should not be presented as new. These three candidates instead specify distinct observables/analysis, and each remains untested.

## Ranked hypotheses (qualitative expected gain vs implementation cost)

Ranks express pre-run expected research value only. **They are not DTI estimates, predictions, or submission choices.**

### 1. Positive well heat-flow residual corridors — medium-high potential / medium cost

**Layers.** The point coverage and residual attribute from the official USGS 2022 Great Basin heat-flow release (DOI [10.5066/P9BZPVUC](https://doi.org/10.5066/P9BZPVUC)); available quality attributes; independent geophysical orientation used only for corroboration.

**Mechanism and signature.** The release estimates a local conductive background and downweights outliers described as locally convective. Its point coverage includes a residual—the departure of an observed well from that estimated background—which the USGS says may help identify hydrothermal or groundwater influence. Test quality-weighted, sampling-density-corrected positive residual clusters and narrow corridors, rather than the broad background heat-flow map alone. Do not use distance to catalogue faults.

**Why an uncatalogued fault could be found.** Localized convective upflow may be focused along a permeable blind fault and can create a positive departure from regional conductive background without a mapped surface scarp.

**Named non-fault mimics.** Shallow groundwater circulation unrelated to tectonic conduits; lithologic thermal-conductivity contrasts; biased exploration-well placement; depth or measurement-quality artifacts.

**Difference from current code.** THCS/FCHD already use shallow probes, sinter/tufa, well/spring temperatures, and silica/cation geothermometry. This is a different point residual from a separate USGS heat-flow analysis, tested as a density/quality-controlled corridor. A background heat-flow layer by itself is not claimed as novel.

**Source/access check.** The official ScienceBase record was reachable and lists a 124.12 MB ZIP attachment. The archive was not downloaded, schema-inspected, hashed, or co-registered; exact footprint coverage, license details, and measurement fields remain unverified. This is a promising hypothesis, **not ready to implement**.

### 2. Conservative-ion hydrothermal mixing residuals — medium potential / medium-high cost

**Layers.** Spring/well aqueous-geochemistry tables in DOE GDR #1391, if the archive contains suitable conservative analytes; lithology, sample depth/date, and independent structure for controls.

**Mechanism and signature.** Deep geothermal fluid mixed with shallow meteoric water may produce a multivariate water-chemistry facies even when a single maximum temperature or geothermometer is weak. After verifying field availability, test residuals from conservative-ion ratios or a compositional mixing trajectory, controlling for evaporation, host-rock composition, well depth, and sample date.

**Why an uncatalogued fault could be found.** A spatially coherent fluid-mixing anomaly may mark a concealed permeable pathway independently of mapped fault traces.

**Named non-fault mimics.** Evaporative concentration on playas; water-rock reaction varying with lithology; well-screen mixing; agricultural/industrial contamination; uneven sampling.

**Difference from current code.** Existing THCS/FCHD code uses well/spring temperature and silica/cation geothermometry. This proposal tests a conservative-ion mixing residual, not another temperature estimate or proximity layer. The exact analytes are unknown until the archive schema is inspected.

**Source/access check.** The official GDR #1391 page is reachable, describes aqueous-geochemistry analyses, and states CC BY 4.0 with attribution. No archive was downloaded, and no usable conservative-ion columns or AOI coverage were verified. **Do not treat as viable until those fields are confirmed.**

### 3. Focal-mechanism stress inversion projected onto blind geophysical lineaments — low-to-moderate potential / medium-high cost

**Layers.** USGS ComCat focal-mechanism/moment-tensor products, lineaments extracted independently from potential fields, and existing strain only as a consistency check.

**Mechanism and signature.** Infer a regional stress tensor from multiple event mechanisms, then compute a preregistered slip/dilation propensity for blind lineament orientations. Keep nodal-plane ambiguity, mechanism quality, magnitude, depth, and randomized-orientation controls explicit.

**Why an uncatalogued fault could be found.** Mechanism orientations provide stress evidence independent of the mapped-fault catalogue; stress-compatible geophysical edges may be concealed active faults and possible fluid pathways.

**Named non-fault mimics.** Quarry blasts or induced seismicity; sparse and spatially biased mechanism coverage; nodal-plane ambiguity; non-fault lithologic contacts misread as lineaments.

**Difference from current code and prior art.** The active feature stack includes earthquake distance/density and geodetic-strain channels, but no focal-mechanism stress inversion projected onto independent blind lineaments. A simpler nodal-plane strike-clustering idea (H7-FM) was already proposed in the 2026-10-29 review and is **not** relabeled as new; this is a distinct but related, untested tensor-inversion variant.

**Source/access check.** The official USGS FDSN documentation is reachable and documents `producttype=focal-mechanism`, spatial bounds, and a count endpoint. A regional query attempt did not return through the page-retrieval tool, so AOI event count and mechanism completeness are unknown. **Do not implement unless a coverage screen succeeds.**

## Locked execution protocol

1. Do not begin until the exact assigned lane paragraph is present and the shared feature cache/evaluator/writer are restored and verified. Do not fork shared tools.
2. Keep the literal uniqueness stop. Check absolute surface Spearman correlation before placement; stop if it exceeds 0.90. Stop if more than 70% of final dots lie within 3 px of any registry raster. No lattice or dense-raster exemption is authorized.
3. If the stop is resolved by an evidence-based protocol correction, withhold whole fault segments plus a buffer, derive catalogue features only from visible faults, and pixel-exactly mask visible faults. Use pooled DTI (alpha=0.2, beta=0.8, 300 m triangular kernel). Test each feature alone; AUC >0.90 is leakage until explained.
4. Label only actual shared-evaluator results as `HOLDOUT-DTI` with evaluator version, withheld-positive count, and 95% CI. Label only actual receipt scores `ORGANIZER-CONFIRMED`. Never convert a projection into a score.
5. Stop after 3 experiments or 2 hours. No real slot selection in this lane; a separate selector owns promotion. No slot has been used in this review.
6. An eligible run ends with one JSON card containing hypothesis/mechanism/mimic, holdout and CI, correlation/overlap, raster SHA-256, validator outcomes, submission name/note (note <=140 chars), and promote/negative verdict. A negative result is complete.

## Current decision

**Negative.** These are research candidates, not validated hypotheses. The top-ranked heat-flow residual test was **not** run because lane assignment and the uniqueness gate block any candidate surface; the shared runtime is unavailable. No TIFF exists from this review, no download is safe, and no slot was selected. See [`evidence/session_2026-10-31_run_card.json`](../evidence/session_2026-10-31_run_card.json) and [`evidence/official_source_check_2026-10-31.json`](../evidence/official_source_check_2026-10-31.json).
