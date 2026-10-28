# Preregistered candidates — NOT an assigned lane, experiment, or score projection

The referenced “single method paragraph” was not identifiable in the available prompt/repo
materials. These four ideas are therefore **prospective research options only**; none is
selected, implemented, or tested in this review. They are ranked qualitatively by relative
expected DTI upside versus implementation cost. The ranking is not a numeric DTI forecast,
and no hypothesis is known to be novel across every peer repository. A repository/code
comparison is required before any method assignment.

| Rank | Hypothesis and conceptual layers | Physical signature / transform | Why it might find uncatalogued faults | Named non-fault mimic and falsification | Difference from inspected implementations; relative upside and cost |
|---|---|---|---|---|---|
| 1 | **Depth-consistent oblique contact displacement**; if available and documented: magnetic field, gravity, and magnetic-source-depth grids | Upward-continue potential fields at several heights; measure the signed horizontal-gradient displacement across profiles; require a stable dip direction and coherent displacement across scales rather than a single edge | A buried, dipping structure may displace geophysical gradients without a surface trace or catalogue-distance input | **Dipping lithologic contact** can make the same edge/profile pattern. Compare against independent mapped geologic contacts and a depth-scrambled / profile-reversal null; failure of directional stability falsifies the mechanism | Distinct from one-height edge scoring or a single Euler-depth cluster; not globally novel until peer code is checked. **Relative upside: highest of these options, very uncertain. Cost: medium.** |
| 2 | **Scale-conditioned magnetic / conductivity halo**; if available and documented: magnetic field and surface conductivity | Remove a local background, then test for a signed low-magnetization residual flanking a narrow conductivity crest, with repeatable cross-profile geometry | Alteration or fluid-related conductivity along a buried permeable structure could leave a paired halo away from mapped faults | **Conductive clay, basin fill, or a fresh volcanic contact** may mimic it. Use geology-matched controls, lateral shifts, and survey-block controls; reject if the signature follows mapped lithology or acquisition blocks | Tests a joint signed residual pattern rather than a generic conductivity ridge. Similar concepts exist in the broader project/peer ecosystem, so novelty is unproven. **Relative upside: moderate. Cost: medium.** |
| 3 | **Drainage-independent displaced scarp pairs**; if available and documented: elevation and magnetic field | Pair curvature zero-crossings on opposite sides of a magnetic edge; measure a consistent displacement while rejecting drainage-aligned curvature and long planar terraces | A small offset surface may be absent from a regional fault catalogue; the candidate feature is the paired displacement, not slope magnitude alone | **Shoreline terraces, roads, and alluvial channels** can form paired breaks. Compare to drainage/terrace masks, rotated profiles, and matched non-fault terrain; fail if the paired pattern persists in the nulls | Differs from stand-alone slope, curvature, step, or tip-continuation scores. **Relative upside: low-to-moderate. Cost: high** because DEM resolution and geomorphic controls matter. |
| 4 | **Radiometric mixture-boundary discordance**; if available and documented: K/Th/U grids plus magnetic field | Fit a local multiband compositional-mixture manifold; score persistent residuals normal to magnetic discontinuities, not raw band ratios | Hydrothermal redistribution could depart from a local lithologic mixing trend near a buried structure | **Soil moisture, transported sediment, lithologic contact, or survey seam** can mimic discordance. Require moisture/geology/flight-block controls and persistence across scales | A local mixture-model residual is different from a simple radiometric edge-concordance vote. **Relative upside: low-to-moderate with high confounding risk. Cost: medium-high.** |

## Feasibility, data provenance, and official sourcing

The checked-in `data/` directory contains only `template_grid.tif`; the competition feature
stack, labels, sample-submission raster and saved holdout folds/cache are absent. Earlier
upstream receipts list anonymous band names such as `band01`…`band19`, which do not by
themselves establish physical channel identity. No layer in the table is asserted to exist
in this checkout or to have verified units. A GitHub mirror hash establishes byte identity
with that mirror, not organizer origin.

The specific source needed for an authenticated numerical test is the DrivenData
[competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
for `training_features.tif`, `labels.tif`, the sample grid and any required metadata. The
page requires competition authentication, which is unavailable to this agent; the
DrivenData host is also outside this sandbox's permitted outbound hosts. Consequently,
none of the four ideas is presently validated or execution-ready here. No new external
dataset is proposed as a substitute for the required competition inputs.

For external confounder checks, the following official/free references are useful to a
human reviewer, but were not fetched or verified as obtainable from this environment:

- [USGS GeoDAWN airborne magnetic and radiometric survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS 3D Elevation Program](https://www.usgs.gov/3d-elevation-program)
- [DOE GDR INGENIOUS collection](https://gdr.openei.org/submissions/1391)
- [DrivenData organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)

The target competition is fault prediction, not geothermal-vent detection. Even a validated
fault-map improvement would not by itself demonstrate a vent, geothermal resource, or
thermal discharge. No scientific or score conclusion follows from this hypothesis list.
