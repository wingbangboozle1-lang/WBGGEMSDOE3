# New Geological Hypotheses — DOE GEMS Prize (2026-10-29)

Target: unmapped surface-fault probability, not direct detection of geothermal vents.
All five hypotheses are **contrarian**: they place predictions OFF the USGS/INGENIOUS
catalogue (where the dotted family already saturates) and use independent physical
signatures to find faults the catalogue misses. This is the opposite strategy from
GEMSDOE24/25/27/30/31/32/33/36, which dot adjacent to known faults.

---

## H1 — Lidar scarp × thermal convergence (PRIMARY, implemented)

**Layers:** USGS 3DEP 1 m DEM-derived lidar scarp bands (12 u8 bands, 100 m grid);
GDR #1391 geothermal springs and Quaternary volcanic vents (row/col point sets).

**Physical signature:** Recent fault scarps survive as subtle topographic breaks
in 1 m lidar DEMs even where surface mapping missed them. Geothermal springs and
Quaternary vents mark active permeability. A lidar scarp within ~300 m of a thermal
feature is a strong blind-fault candidate.

**Why it catches uncatalogued faults:** The catalogue maps mature, through-going
faults. Young, blind, or splays faults near geothermal systems may have no surface
expression in geologic maps but do produce subtle scarps and local heat flow.

**Named mimic:** Glacial/fluvial terraces, landslide scarps, surficial deposits,
survey leveling artifacts.

**How it differs from repo:** The repo's dotted family (GEMSDOE24/25/27/30/31/32/33/36)
places dots adjacent to known catalogue faults. H1 places dots OFF the catalogue
(3.5 px buffer around known faults), weighted by lidar scarp strength and thermal
proximity. Zero dots fall on known faults.

**Expected DTI improvement:** High — targets the false-positive mass the catalogue
excludes from scoring, while capturing new true positives near thermal features.

**Implementation cost:** Low — uses existing external mirrors (lidar_scarp_features,
geodawn_rad, GDR CSV point sets). Implemented in scripts/generate_unique_submission.py.

---

## H2 — Radiometric alteration-halo edge (not yet implemented)

**Layers:** USGS GeoDAWN airborne radiometrics (K, Th, U, total count; Th/K, U/K,
U/Th ratios; TMI upward-continued 150 m).

**Physical signature:** Hydrothermal alteration (illite, argillic, advanced argillic)
enriches potassium and mobilises uranium/thorium along fault-controlled permeability
zones. The edge of a radiometric anomaly (gradient magnitude) marks the alteration
front, which often coincides with a concealed fault.

**Why it catches uncatalogued faults:** Concealed faults under alluvial cover have no
surface scarp but do host alteration halos visible in airborne radiometrics. The
catalogue does not map these.

**Named mimic:** Lithologic contacts, volcanic margins, survey tie-line leveling,
terrain clearance, drainage patterns.

**How it differs from repo:** The repo uses radiometrics as a supporting band (0.20
weight in H1). H2 would make radiometric edge gradients the primary driver, with
a Canny/Sobel edge detector on K/Th/U/TC.

**Expected DTI improvement:** Medium — radiometric anomalies are broad; edge thinning
is needed to avoid diffuse false positives.

**Implementation cost:** Medium — requires edge detection on 8 u8 bands; no new
external data needed (GeoDAWN mirrors already restored).

**Data check:** GeoDAWN u8 mirrors verified in registry/data_manifest.json. Obtainable.

---

## H3 — Off-catalogue distance-decay splays (not yet implemented)

**Layers:** Existing faults (labels.tif / existing_faults.tif, the catalogue).

**Physical signature:** New faults commonly occur as splays, step-overs, and relay
ramps within 2–8 px of mapped faults. Probability decays with distance from the
catalogue trace but peaks just outside the excluded buffer.

**Why it catches uncatalogued faults:** The catalogue is complete for major traces
but incomplete for minor splays. These minor structures host geothermal
permeability and are not in the USGS/INGENIOUS map.

**Named mimic:** Mapping artifacts, erosion gullies, road cuts.

**How it differs from repo:** The dotted family dots ON or immediately adjacent to
catalogue faults (which the organizer excludes from scoring). H3 places dots at
2–8 px OFF the traces, in the near-catalogue band where B2's pruning removed dots
but where new-fault credit may still exist.

**Expected DTI improvement:** Medium — near-catalogue dots were pruned by B2 for a
reason (false positives), but a narrow off-trace band may retain true-positive
credit.

**Implementation cost:** Low — distance transform of existing_faults.tif; no new
data.

**Data check:** existing_faults.tif already restored. Obtainable.

---

## H4 — Volcanic vent alignment with structural lineaments (not yet implemented)

**Layers:** GDR #1391 Quaternary volcanic vents (709 regional, 281 in footprint);
derived SGMC faults; lidar scarp bands.

**Physical signature:** Quaternary volcanism indicates recent extensional tectonism.
Faults aligned with volcanic vents but not in the catalogue are young structures
with active permeability — prime geothermal targets.

**Why it catches uncatalogued faults:** Volcanic vents post-date most mapped
faults. Faults controlling vent locations may be too young or subtle for the
catalogue but are visible as alignments in lidar and radiometrics.

**Named mimic:** Erosion cones, alluvial fans, drainage density anomalies.

**How it differs from repo:** The repo uses vents only as point proximity (H1).
H4 would require vent-to-vent alignment analysis and lineament extraction — not
currently implemented.

**Expected DTI improvement:** Low-Medium — only 281 vents in footprint, sparse
signal.

**Implementation cost:** Medium — requires lineament extraction and alignment
testing; vent CSV already restored.

**Data check:** gdr_volcanic_vents_in_footprint.csv verified. Obtainable.

---

## H5 — Road-distance exploration-bias correction (not yet implemented)

**Layers:** US Census TIGER/Line 2024 roads (tiger_road_distance_m.tif);
existing faults; lidar scarps.

**Physical signature:** Faults far from roads are under-mapped because geologists
don't walk there. A road-distance-corrected structural model up-weights remote
areas with independent geophysical support.

**Why it catches uncatalogued faults:** The catalogue has an exploration-access
bias. Remote geothermal systems with faults are systematically under-represented.

**Named mimic:** Actual absence of faults in remote areas (not all remote areas
have faults).

**How it differs from repo:** The repo does not use road distance as a bias
correction. tiger_road_distance_m.tif is restored but unused in any lane.

**Expected DTI improvement:** Low — bias correction does not create new signal,
only re-weights existing evidence.

**Implementation cost:** Low — one raster already restored.

**Data check:** tiger_road_distance_m.tif verified. Obtainable.

---

## Ranking by expected DTI improvement and cost

| Rank | Hypothesis | Expected DTI | Cost | Data status | Implemented? |
|------|-----------|-------------|------|-------------|--------------|
| 1 | H1 — Lidar scarp × thermal convergence | High | Low | Verified mirrors | YES (this submission) |
| 2 | H3 — Off-catalogue distance-decay splays | Medium | Low | existing_faults.tif | No |
| 3 | H2 — Radiometric alteration-halo edge | Medium | Medium | GeoDAWN mirrors | No |
| 4 | H4 — Volcanic vent alignment | Low-Medium | Medium | GDR vent CSV | No |
| 5 | H5 — Road-distance bias correction | Low | Low | TIGER road raster | No |

---

## Validation status

H1 was implemented and validated locally:
- Format: single-band float32, EPSG:32611, 3730x3292, exact transform, NaN outside
- Values: all finite in [0,1] inside footprint
- Dots: 18,000 off-catalogue dots, 0 on known faults
- Uniqueness: 8-21% dot overlap within 3px vs all nine focus sites (threshold: 70%)
- Status: RESEARCH ARTIFACT — NOT cleared for submission

The repository-wide release gate remains DO-NOT-SUBMIT (literal registry stop
unresolved). This hypothesis and its TIF are research artifacts pending gate
resolution and separate selector approval.
