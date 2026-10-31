# Candidate hypotheses ranked for the 2026-10-31 session

Selected and run: **H0-GGO** (below). The four others are recorded as ranked, unrun or
partially-diagnosed options for the next session. Nothing here is a score projection: the
only numbers in this file are HOLDOUT-DTI (this repo's shared instrument), proxy hit-rate
against a USGS external catalogue, or LEDGER-INVERSION ESTIMATE (owner-reported sibling
scores, no receipts).

## What the instrument landscape says (measured, this repo, 2026-10-31)

| Fact | Value | Where verified |
|---|---|---|
| Scored truth definition | expert-mapped faults **not** in the public USGS catalogue; public/private chunks; final round re-scored on expanded labels | [official problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| Metric | DTI, k(d)=max(1−d/300 m,0), α=0.2, β=0.8, TP_w uses **max** over the kernel | same page, "Mathematical representation" |
| Submission format | single band float32, EPSG:32611, 100 m, same bounds, **outside bounds null or NaN**, values in [0,1] | same page, "Submission format" |
| Footprint of the pinned `sample_submission.tif` mirror | 5,167,373 finite cells; 7,111,787 NaN | measured from bytes, sha256 `2176d08e…` |
| Public "labels" mirror is the *catalogue*, not the hidden truth | 60,988 positive cells, byte-identical to `existing_faults.tif` (sha256 `7ba308cc…`) | measured, sha256-verified against `registry/data_manifest.json` |
| Catalogue hide-and-recover holdout vs owner scores | Spearman **−0.15** on 11 archived submissions | `src/gemsdoe/validation.py` |
| Sibling ledger usable for calibration | 118 hash-pinned submission rasters with owner-reported scores | `registry/upstream_live_ledger_rasters.json`, fetched 2026-10-31 |

The last two rows are the reason this file exists: **the mandated holdout instrument is
anti-correlated with the target**, so a hypothesis cannot be selected on it alone. Any
hypothesis must be judged on (a) the external off-catalogue proxy and (b) the ledger
inversion, with the holdout reported as a diagnostic.

## H0-GGO — Cover-gated basement/gravity/geodetic concordance  **(SELECTED, RUN)**

* **Layers.** `iso_grav_anom` + its horizontal gradient and LoG (band 13/18 and derived),
  `depth_to_base_surf` step (band 15), `geod_2ndinv` + `geod_shearrate` (bands 4/7),
  `det_elev` curvature + slope (bands 12/19) used as a *weakness* gate, distance to the
  visible catalogue (>= 3 px) as an off-catalogue constraint.
* **Physical signature.** Colinearity within 2 px (200 m) between a gravity horizontal-gradient
  crest and a depth-to-basement crest, weighted by localised second-invariant strain rate —
  i.e. the same structure imaged by a potential-field edge at basement level and by the
  geodetic strain field at the surface.
* **Why it should catch a fault missing from the catalogue.** A Quaternary fault database is
  built from surface expression; under thick alluvium the scarp is absent, so the segment is
  recorded as "no exposure" or attributed to a neighbouring trace. Gravity gradients and
  basement-depth steps propagate through the cover, and interseismic strain localisation is a
  *kinematic* signature of the active fault regardless of exposure. The gate therefore
  deliberately down-weights the cells where the catalogue is most complete.
* **Difference from anything already in this repo.** Every implemented lane (`pipeline.py`
  morphology∪LiDAR union, `emit.py` ridge top-N, the H-A/H-B/H-C trio in `src/gemsdoe/features.py`)
  ranks by *strength* of ridge/edge evidence; none conditions on morphological **weakness**
  or on cover thickness as a selection criterion, and none uses the geodetic strain invariants
  as a concordance multiplier.
* **Named non-fault mimic.** Lithologic and intrusive contacts give the same gravity step;
  InSAR carries atmospheric/thermal ramps; groundwater pumping and mining give subsidence;
  thick-cover basins are simply unmapped at any resolution, which caps recall.
* **Cost.** Low — every input is already in the cached 76-band stack (no new external data).

## H1-RMIX — Radiometric mixing-manifold residual (UNRUN)

K–Th–U–total-count compositional closure residual at independently supported structures
(GeoDAWN radiometrics via the pinned `geodawn_rad_u8.tif`). Mimic: non-fault lithologic or
weathering contacts, flight-line levelling/clearance artefacts. Cost: low-medium (band math +
closure residual); expected gain: small, because radiometric alteration haloes are cm-to-m
scale features aliased into 100 m cells and the sibling that tried alteration-based conjunctive
mapping scored 0.0782 (GEMSDOE15, owner-reported).

## H2-XCATCH — Cross-catchment channel-profile discontinuity (UNRUN, data-limited)

Area- and lithology-conditioned paired channel-profile knickpoints with independent geophysical
orientation. Needs a hydrographic network + flow accumulation from the 1 m DEM list; the DEM
tiles are **not** obtainable from this sandbox (only GitHub, PyPI and npm are reachable), so the
named free official source is the USGS 3DEP REST service
(`https://www.usgs.gov/usgs-3dep/technical-documents`) plus NHD Plus Flowlines
(`https://www.usgs.gov/products/data-and-tools/nhd`) — both verified as public, neither verified
as obtainable here. Blocked on access, so not viable this session.

## H3-ANISO-THERM — Sampling-corrected anisotropic shallow thermal evidence (UNRUN)

Density-normalised anisotropic kernel on the INGENIOUS 2 m temperature probes
(`data/raw/external/2m_temperature_probe_INGENIOUS_regional_data.zip`, fetched and hash-verified
today). Mimic: sparse sampling clustered near known springs, basin/lithologic heat effects.
Cost: medium. Expected gain: uncertain — the geothermal-PINN sibling that used this family of
evidence reached 0.2750 (GEMSDOE36, owner-reported), so the signal is real but crowded.

## H4-XOVER — Acquisition-crossing repeatability (UNRUN, needs one more file)

Require independent crossing GeoDAWN flight lines to repeat an anomaly after line-level
correction. Needs `acquisition_block_id_100m.tif` (listed in `registry/registry_index.json`,
sha256 `2c0785c4…`, 85,031 bytes, in `buffedlizard55-lab/GEMSDOE24`) — obtainable through the
same pinned-mirror channel used today. Mimic: real lithologic contacts, tie-line levelling,
flight-line striping, terrain-clearance. Cost: medium. Value: this is a *filter* on other
lanes, not a stand-alone detector, so it is cheap to test next.

## Ranking actually used

| Rank | Hypothesis | Expected DTI gain | Cost | Status |
|---|---|---|---|---|
| 1 | H0-GGO | moderate (targets the catalogue's blind zone; disjoint from the crowded scarp-ridge family, which also serves the uniqueness lane) | low | **run today** |
| 2 | H4-XOVER | small alone, medium as a gate on any lane | medium (one pinned file) | next |
| 3 | H3-ANISO-THERM | small-medium | medium | queued |
| 4 | H1-RMIX | small | low | queued |
| 5 | H2-XCATCH | unknown | high + blocked on DEM access | blocked |

Results for H0-GGO: `evidence/ggo_experiment.json` and `evidence/ggo_run_card.json`.
