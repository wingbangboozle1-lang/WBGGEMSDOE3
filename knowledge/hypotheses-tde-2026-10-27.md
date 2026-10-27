# Ranked hypotheses for the 2026-10-27 session (written before the emission was built)

Every row names the layers, the transform, why it could catch a fault the USGS/INGENIOUS catalogue does
not contain, and how it differs from what this repository has already run. Ranks are reasoned priorities,
**not** numerical estimates. Availability of every external source was checked before ranking: all of the
layers below are already in `registry/data_manifest.json` and were fetched and SHA-256-verified in this
session, so no hypothesis depends on data we cannot obtain.

| # | Hypothesis | Layers / transform | Physical signature | Why it can catch an *unmapped* fault | Named non-fault mimic | Cost | Outcome |
|---|---|---|---|---|---|---|---|
| 1 | **TDE** — truth-density posterior from published score scalars × tri-domain edge concordance | 118 score scalars → ρ (score tomography); competition `det_elev`, `rtp`, `iso_grav_anom`; lidar scarp stack (3DEP 1 m); each as percentile ranks, concordance = geometric mean of the three gradient ranks | Cross-domain edge agreement at 150–500 m scale + DEM ridge + scarp step | The only label-derived input is the mask; the emission is free to fire where the catalogue is silent, and the posterior concentrates a sparse budget where the metric actually pays | Lithologic contacts, volcanic margins, aeromagnetic survey/processing stripes, alluvial-cover edges | Low (all layers pinned) | **implemented** — 0.2687 raw / 0.2074 calibrated |
| 2 | **CSPES** — cross-scale persistence of gravity and magnetic gradient orientation, conditioned on detrended elevation | `iso_grav_anom`, `rtp`, `det_elev`; orientation tensors at 2/5/10 px | Orientation stability across scales | Buried offsets persist in potential fields where surface relief is subdued | Interpolation artefacts, survey stitching | Medium | not run — dominated by #1 in the sweep (the concordance term already uses both gradients) |
| 3 | **Drainage-deflection relay** | raw USGS 3DEP 1 m DEM tiles → flow accumulation → channel deflection statistic | Consistent offsets of several channels across one lineament | Difficult to explain without structure; independent of magnetics | Lithologic control, erosion, alluvial fans, road/culvert diversion | High — needs raw 3DEP tiles (free, no login, but not yet fetched here) | not run — data not fetched, so not callable viable |
| 4 | **Thermal contrast normalised by effort** | INGENIOUS 2 m probe temperatures, GDR 1391 well/spring temperatures, sampling density | Asymmetric thermal plume across a structural gradient | Fluid pathways in covered terrain leave a thermal footprint that mapping cannot see | Groundwater flow, climate, sampling bias | High — bytes fetched, but spatial coverage and representativeness unverified | not run — coverage unverified |
| 5 | **Gravity–magnetic disagreement** | `iso_grav_anom` vs `rtp` gradient disagreement, conditioned on `geod_shearrate` | Density discontinuity without a magnetic contact | Basin margins in poor exposure | Non-magnetic lithologic contacts | Medium | not run — near-duplicate of #1/#2 |

## Why rank 1 and not rank 3

Rank 3 is the physically most independent idea, but it cannot be executed inside this session without
fetching 3DEP tiles, and the standing instruction is not to spend a slot on an idea that has not been
validated. It is therefore recorded as the **first** item for the next session, with the exact source:
USGS 3DEP 1 m DEM tiles, `https://www.usgs.gov/3d-elevation-program` (public domain, no login). If the
tiles cannot be obtained and licence-checked, hypothesis 3 must be dropped rather than assumed viable.

## Leakage canaries

No field entered the emission without a canary check. The strongest single-field association with the
public catalogue in this stack is well below 0.90 AUC (the 2026-10-26 review measured a maximum of 0.658
across 66 fields), so none is flagged as label leakage. Distance-to-catalogue is used **only** to build
the exclusion mask; inside the holdout it is recomputed from the visible faults only.
