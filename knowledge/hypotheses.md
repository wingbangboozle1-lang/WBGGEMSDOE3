# Preregistered candidates — NOT experiments or score projections

No method paragraph was supplied after the user's “LANE” instruction. These
are ranked **research options only**, not a lane selection. Nothing in this
list is certified new across all peer code. In this checkout, no detector was
implemented before this audit. Upstream has already attempted many edge,
curvature, conductivity, relay and depth methods; naming alone is not novelty.
The alternatives below require a full code/registry comparison after lane
assignment. Ranks are qualitative expected benefit per cost, not estimated DTI.

| Priority | Hypothesis / layers | Physical signature and transform | Why potentially unmapped, rather than a catalogue copier | Non-fault mimic / falsification | Difference and cost |
|---|---|---|---|---|---|
| 1 | Depth-consistent oblique contact discontinuity; provided magnetic field, gravity, magnetic-source depth | Multi-height upward continuation followed by cross-scale horizontal-gradient displacement; fit a consistent dip direction, penalize mismatched depth | Uses buried-source displacement without proximity-to-catalogue features; may expose blind contacts. Does not guarantee a fault | Dipping lithologic contact; compare to geologic boundaries and depth-scrambled control | Requires coherent displacement across heights, not a single Euler cluster or edge vote. Novelty against upstream depth-projection code not established. Medium CPU cost |
| 2 | Scale-conditioned demagnetization halo; provided magnetic and conductivity grids | Signed low-magnetization residual across a narrow conductivity crest, conditioned on regional background; symmetric cross-profile rather than raw edge magnitude | Alteration along a buried permeable structure could leave a halo without a surface trace; not trained to reproduce catalogue distances | Conductive clay, basin fill, fresh volcanic contacts; geology-matched null and lateral shifts | Joint signed residual geometry rather than generic conductivity ridge. Requires units/channel provenance before use. Medium cost |
| 3 | Drainage-independent displaced scarp pairs; provided elevation and magnetic grid | Match offset curvature zero-crossings on opposite sides of a magnetic edge, rejecting drainage-aligned curvature and long planar terraces | Small displaced surfaces may be absent from regional mapping; no fault catalogue used to construct transform | Shoreline terraces, roads and alluvial channels; reject with drainage/terrace nulls | Paired displacement residual, not stand-alone slope, step, curvature or tip continuation. High cost and DEM resolution may be inadequate |
| 4 | Radiometric mixture-boundary discordance; provided K/Th/U grids plus magnetic grid | Fit a local compositional mixing manifold, score spatially persistent residuals normal to magnetic discontinuities, not raw band ratios | Hydrothermal redistribution can depart from lithologic mixing at buried structures | Soil moisture, survey seams, transported sediments; flight-block and moisture controls needed | Residual to a local multiband manifold, not an edge-concordance vote. High confounding risk; medium/high cost |

## Feasibility and official sourcing

All four are conditional on the competition numerical stack actually containing
the named quantities with documented units. The retrieved upstream feature
receipt lists anonymous `band01`…`band19`; **that is insufficient to identify
physical channels**. No viable execution is claimed until descriptions and
provenance are recovered. The official reference README confirms data must be
obtained separately, not that any given mirror is authentic.

No candidate requires a new external dataset for an initial numerical test.
External confounder validation would benefit from official USGS GeoDAWN survey
metadata, USGS geologic maps and USGS 3DEP elevation. Their domains are outside
this environment's allowed outbound hosts. Sources named in the user request:

* https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
* https://www.usgs.gov/3d-elevation-program
* https://gdr.openei.org/submissions/1391

These URLs are **not fetched or verified as obtainable here**. No inaccessible
external-data hypothesis is proposed as immediately viable. Scientific
mechanisms above are hypotheses, not conclusions backed by a literature review.
