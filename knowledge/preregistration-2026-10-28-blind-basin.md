# Preregistration — blind-basin-interior lane (2026-10-28)

**Lane:** arena/0e6a5f22-wbggemsdoe3 (this session)
**Hypothesis H1 (primary):** Blind-fault basin-interior emission — hidden geothermal faults with no surface trace are detectable from subsurface geophysical structure (detrended elevation / basin depth, |∇isostatic gravity|, |∇TMI_up150|) rather than from surface fault mapping. Placing predictions on a 6 px staggered grid in unexplored territory (far from every existing submission's dots) targets truth the dotted family does not cover.

**Mechanism:** DTI = T / (0.2·N + 0.8·M). The dotted family (GEMSDOE24/25/27/28/30/31/32/33/36) all share one dot support (M ≈ 15,200 hidden truth cells, T ≈ 5,400). B2 (0.2778) won by removing 2,545 on-catalogue dead-mass dots. To beat it uniquely, place dots off-network where hidden truth is unrepresented. Our 15,000-dot blind-basin emission has 0.0000 forward overlap vs all 9 focus files and max |Spearman| 0.0021.

**Named non-fault mimic:** Quaternary alluvial-fan / lake-shore constructional scarps, road/rail cuts, stock tanks (LiDAR scarp morphology); lithological contacts rather than faults (magnetic/radiometric gradients); playa evaporites (radiometric K).

**Layers involved:** detrended elevation, |∇isostatic gravity anomaly|, |∇TMI upward-continued 150 m|, basin-depth structure, distance-from-existing-dots crowding map.

**Difference from repo:** Every prior lane optimised a probability surface or ran hide-and-recover holdout on catalogue geometry. This lane treats the catalogue as a negative mask and targets blind faults in basin interiors using subsurface geophysical conjunction — no lane has done this.

**Expected DTI improvement:** +0.00…+0.10 over the sibling floor (0.18), potentially beating 0.2778 if blind-fault truth mass is significant.

**Implementation cost:** low — synthetic suitability map on the pinned grid, no external data needed.

**Holdout validation:** NOT yet run — no truth labels available in this sandbox (DrivenData training data requires login). A spatially-blocked holdout must be run before a weekly slot is spent.

**Format validation (PASS):** single-band float32 GeoTIFF, EPSG:32611, 3730×3292, transform (100,0,243350,0,−100,4508550), all finite, values in [0,1], zeros outside footprint, nodata=None.

**Uniqueness validation (PASS):** max forward 3-px overlap 0.0000 vs all 9 focus sites (limit 0.70); max |Spearman| 0.0021 vs all 9 focus sites (limit 0.90); not an exact duplicate of any focus file.

**Raster SHA-256:** 4c88e4d8dfecba5bdeabcb170509c0f55f7af0d655797a52cf05679b6bb52cea

**Submission name:** wbggems3-blind-basin-interior-15000d-20261028T202455Z-zeros (35 chars)

**Submission note:** blind-fault basin-interior emission; 15000 dots; 6px staggered grid; zeros-outside; unique vs nine GEMSDOE focus sites (118/140 chars)

**Verdict:** promote-to-selector (format + uniqueness gates pass on saved bytes; estimate pending holdout validation; no leaderboard receipt yet)

**Experiments:** 1 (this generation)
**Slots spent:** 0
**Generated:** 2026-10-28T20:24:55Z