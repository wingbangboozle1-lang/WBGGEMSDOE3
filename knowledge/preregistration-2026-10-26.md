# Preregistration: geologic hypotheses and the lane for this session

**Written before any candidate modelling or placement, 2026-10-26 UTC.** The supplied
parallel-run protocol refers to a “single method paragraph below,” but the request does
not identify such a paragraph. This is a proposed single lane, not an assertion that an
external coordinator assigned one. No other hypothesis will be run in this session.
All ranks below are reasoned priorities, **not numerical estimates** of an improvement.
The repository initially contained only a README; “new here” does not mean globally new.

## Proposed lane: cross-scale potential-field edge stability (CSPES)

On the **shared, hash-pinned 57GEMSDOE feature stack**, evaluate a label-independent
combination of scale-stable, collinear gravity and reduced-to-pole magnetic gradients,
conditioned on the detrended-elevation gradient. A persistent, concordant discontinuity
may indicate a buried structural boundary whose surface trace is subtle or absent from
the public catalogue. A lithologic contact, volcanic body, or survey/processing stripe
can produce the same pattern. Do not claim that the signal is a fault or a geothermal
vent. This is a hypothesis; no performance claim is made. It differs from the existing
GEMSDOE31 PGR31 regression of pseudo-gravity against gravity and from GEMSDOE32 SPCP's
curvature-crest/conduit model by testing cross-scale persistence and directional
agreement, not pseudo-gravity residuals or curvature crests. Those comparisons do not
prove that no other project has tried a similar approach.

## Ranked candidates (only the first is in this lane)

| Priority | Hypothesis and exact inputs | Signature / why it could find a missing fault | Cost and availability | Known confounder and prior-art caveat |
|---|---|---|---|---|
| 1 | CSPES: gravity `iso_grav_anom`, magnetic `rtp`, detrended elevation `det_elev`; all from cached 19-band mirror. | Compare orientation and stability of first-derivative edges over prespecified scales; condition, rather than draw, on surface relief. Buried offsets may persist in potential fields where a scarp is subdued. | Medium CPU; no new source required, but the public GitHub mirror is not independently organizer-authenticated. | Lithologic contacts / aeromagnetic acquisition artifacts; related potential-field approaches exist in GEMSDOE31/32, so novelty is not established beyond the distinction above. |
| 2 | Cross-channel consistency: 3DEP bare-earth DEM and hydrography-derived flow paths. | Several consistently displaced or deflected drainage channels across one lineament may indicate a trace not already mapped. | High; requires raw 3DEP DEM tiles, not the cached 100 m detrended feature. USGS says 3DEP products are free/unrestricted; actual contest-tile coverage and download in this sandbox are unverified. **Not executable now.** | Lithologic controls, erosion, fans and human diversion also bend channels. USGS explicitly says not every bend is fault-related. |
| 3 | Multi-scale gradient disagreement between isostatic gravity and magnetic intensity, conditioned on regional geodetic shear. | A persistent density discontinuity without a corresponding magnetic contact might indicate a buried basin margin where outcrop-based mapping is poor. | Medium, uses cached features only. | Nonmagnetic lithologic contacts and interpolation; close to GEMSDOE31 PGR31 and other potential-field work. |
| 4 | Thermal anomaly **contrast**, from INGENIOUS 2 m probes and well/spring temperatures, normalized by sampled-site density and constrained by surface geology. | An asymmetric thermal plume crossing a structural gradient could indicate a fluid pathway in covered terrain. | High; official public [GDR 1391](https://gdr.openei.org/submissions/1391) lists both datasets under CC BY 4.0; bytes, AOI coverage, sampling bias, and access from this sandbox are unverified. **Not executable now.** | Groundwater flow, climate and sampling bias; GEMSDOE30 GDX already explored effort-normalized geothermal data, so this is a related extension, not a proven globally novel method. |

## Stop and evaluation plan

Before placement, and again on final dots, compare against **every** raster in the
pinned registry using literal finite-positive support, with no dense-raster exception.
Any one overlap greater than 70% or absolute Spearman above 0.90 is a stop. A preflight
universal witness also stops generation if it proves every nonempty candidate fails.
Only if that gate allows a candidate, use the pinned shared `evaluate_holdout.py` and
`submission_writer.py`, not a fork. Run a single-feature AUC canary per feature on
whole-fault-segment buffered, spatially blocked folds; recompute catalogue-derived
features from visible faults only; mask visible faults pixel-exactly; pool TP/FP/FN
before DTI with α=0.2, β=0.8, 300 m triangular kernel. Report evaluator version,
withheld-positive count and paired spatial-block 95% CI. Only a paired win over a
matched same-evaluator incumbent may enter the separate selector. No weekly slot will
be spent in this session. At most three experiments / two hours.

## Official scientific sources

- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and): magnetic data reflect subsurface geology, radiometrics surface materials; variable terrain clearance matters.
- [DrivenData problem statement](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/): fault prediction, labels, layers, metric, format.
- [USGS tectonic geomorphology](https://www.usgs.gov/programs/earthquake-hazards/science/tectonic-geomorphology-and-near-field-geodesy): deflected and offset streams are possible fault indicators, not proof.
- [USGS fault guide](https://pubs.usgs.gov/of/2005/1127/chapter1.pdf): not all channel bends are fault-related.
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program): data free and unrestricted; tile-level availability here is not established.
- [INGENIOUS GDR](https://gdr.openei.org/submissions/1391): public CC BY 4.0 compilation; attribution and fitness for use are required.
