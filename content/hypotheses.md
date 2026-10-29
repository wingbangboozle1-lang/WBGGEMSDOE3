# Hypotheses — ranked for research priority (not score estimates)

**Status: prospective research plan only. No hypothesis has been tested. No submission approved.**

These are 3–5 distinct geological hypotheses not previously implemented in this repo or in the GEMSDOE24/25/27/28/30/31/32/33/36 sites. Ranks are qualitative pre-run research priority — not DTI estimates, not score projections, and not a submission choice. Every entry names the specific layer(s), the physical signature, why it should catch a fault missing from the USGS/INGENIOUS catalogue, the named non-fault mimic, how it differs from existing repo code, expected gain vs cost, and data-access status.

---

## H1 — Off-catalogue dilational step-over / damage-zone conduits (IMPLEMENTED — WBG-GEMS-3 TIF)

**Layers:** off-trace structural damage zones; dilational step-over / relay-zone corridors between en-echelon mapped segments; blind structures absent from the USGS/INGENIOUS catalogue.

**Physical signature:** distance-to-catalogue-trace band of 100 m–1.5 km (damage zone / dilation width), with soft Gaussian probability across corridor width and along-corridor continuity at dilational jogs. Implemented as NE-SW trending corridors (azimuth ≈55°, half-width ≈600 m) with soft probability decay from corridor centre; dots placed by Poisson-disk thinning (min spacing ≈300 m).

**Why it catches uncatalogued faults:** Every GEMSDOE24/25/27/28/30/31/32/33/36 high-scorer (0.2449–0.2778) places dots ON or within 1–2 px of the h19-5 / catalogue fault network (≥97.6% 3-px overlap within the nine-site set). Dots 100 m–1.5 km off mapped traces target blind structures absent from the catalogue and cannot earn credit for known faults.

**Named non-fault mimic:** lithologic/weathering contacts, basin-floor sedimentary contacts, or relict drainages aligned with corridor orientation.

**How it differs from repo code:** All existing GEMSDOE high-scorers and repo lanes dot on/near the catalogue network. WBG-GEMS-3 places soft-probability dots strictly OFF-network. This is the hypothesis implemented by `scripts/generate_unique_submission.py` → `docs/downloads/wbg-gems-offnet-conduit-latest.tif`.

**Expected DTI improvement:** Unknown (no holdout score; no label access). Qualitatively: targets the largest uncovered region of the competition label space (off-network blind faults).

**Implementation cost:** Low — uses only the public grid geometry; no external data required.

**Data-access status:** Available (public grid only).

**Test status:** TIF generated and format-validated (all values in [0,1], correct CRS/shape/transform). HOLDOUT-DTI not computable (no label access). Not cleared for submission.

---

## H2 — Local radiometric mixing-manifold residual at concealed structures (NOT IMPLEMENTED)

**Layers:** GeoDAWN airborne radiometrics (K, Th, U, total-count channels) at the competition AOI.

**Physical signature:** A permeability/alteration corridor or buried structural boundary preserves a narrow compositional break in the local K–Th–U–total-count log-ratio space, even where surface scarps are muted. Fit a robust local compositional baseline (robust covariance / minimum covariance determinant on log-ratios within a moving window); measure the out-of-manifold Mahalanobis residual; require continuity across scales and independent alignment with a potential-field edge.

**Why it catches uncatalogued faults:** Concealed or blind faults may not produce surface expression but can focus hydrothermal alteration that changes radiometric surface composition. Raw K/Th or U/Th ratios already exist in some lanes; the distinguishing feature is the local multichannel closure/manifold residual with explicit stratification by cover/relief — not another raw ratio or generic edge.

**Named non-fault mimic:** non-fault lithologic/weathering contact; GeoDAWN flight-line leveling or variable aircraft clearance as acquisition mimics.

**How it differs from repo code:** HCE already has simple K/Th and U/Th log ratios and phase congruence; THCS/FCHD contain radiometric ratio/gradient features. H2 adds a local multichannel closure/manifold residual with explicit stratification — a genuinely different test if not already present in the shared feature stack.

**Expected DTI improvement:** Medium — radiometric alteration is a direct geothermal proxy but mimic risk is high.

**Implementation cost:** Low–medium if the pinned GeoDAWN layers are available.

**Data-access status:** UNVERIFIED — AOI coverage, file versions, and provenance of local GeoDAWN bands are not established. USGS GeoDAWN page: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and

---

## H3 — Sampling-corrected, strike-anisotropic shallow thermal evidence (NOT IMPLEMENTED)

**Layers:** DOE GDR #1391 geothermal/geochemical observations (springs, wells, temperature logs); USGS 3DEP DEM for topographic correction.

**Physical signature:** If shallow heat is transported by fault-controlled permeability, its spatial support is elongated along an independently estimated structural direction rather than isotropic. Build observation-density-normalized thermal residuals; compare a preregistered anisotropic kernel aligned only to an independent geophysical/strain orientation against a matched isotropic bandwidth baseline. Preserve spatially grouped holdout; never use any `dist_known_fault` column or catalogue-derived feature.

**Why it catches uncatalogued faults:** Fault zones act as conduits for shallow thermal anomalies; anisotropy reveals the structural control even where individual surface traces are weak or missing from the catalogue.

**Named non-fault mimic:** sparse/biased sampling around known hot springs and wells; basin-scale heat flow or lithologic conductivity contrasts.

**How it differs from repo code:** THCS/FCHD already rasterize GDR points with Gaussian/isotropic smoothing. H3 adds anisotropy plus explicit sampling-density correction — not merely adding GDR features.

**Expected DTI improvement:** Medium — direct thermal signal but sampling bias is a major confound.

**Implementation cost:** Medium — requires GDR archive access and sampling-bias diagnostics.

**Data-access status:** UNVERIFIED — GDR #1391: https://gdr.openei.org/submissions/1391 (CC BY 4.0 stated; local file provenance unverified).

---

## H4 — Cross-catchment channel-profile discontinuity (NOT IMPLEMENTED)

**Layers:** USGS 3DEP DEM; hydrography / stream network; independent magnetic/gravity corroboration.

**Physical signature:** A fault-related uplift/offset or basin-margin hinge produces a repeatable stream-power / knickpoint discontinuity across neighboring catchments. Derive channel profiles independently from DEM; compare matched, lithology-/area-conditioned profile breaks across adjacent catchments; require coherent structural orientation and independent potential-field corroboration. Withhold entire fault segments plus buffer; derive catalogue features only from visible faults.

**Why it catches uncatalogued faults:** A fault offset may be too weak to map as an individual scarp but still disrupts drainage organization across catchments. Paired cross-catchment residuals add information beyond single-channel metrics already in FCHD.

**Named non-fault mimic:** resistant bedrock/lithologic contact; nontectonic base-level change; roads, dams, drainage edits.

**How it differs from repo code:** FCHD has chi-channel and step metrics. H4's incremental question is whether paired, cross-catchment profile residuals add information beyond single-channel metrics.

**Expected DTI improvement:** Low–medium — topographic signal is indirect and mimic risk is high.

**Implementation cost:** Medium–high — raw DEM/coverage, hydrography, licensing, and reproducible acquisition for the exact AOI are UNVERIFIED.

**Data-access status:** UNVERIFIED — USGS 3DEP: https://www.usgs.gov/3d-elevation-program

---

## H5 — Landsat surface-alteration texture conditioned on independent structure (NOT IMPLEMENTED)

**Layers:** USGS Landsat Collection 2 surface reflectance / temperature products (cloud/snow-screened, season-matched).

**Physical signature:** Persistent clay/iron-oxide or thermal contrast marks hydrothermal alteration above permeable structures where geophysics alone is ambiguous. Construct preregistered alteration contrasts (e.g., clay index, iron oxide index, thermal anomaly); test only spatial texture/orientation against independent structural evidence; compare against same-lithology and vegetation/cover-matched controls. Never infer faults from spectral anomalies alone.

**Why it catches uncatalogued faults:** Surface alteration can mark blind permeability pathways not visible in potential-fields or topography.

**Named non-fault mimic:** host-rock lithology/soil differences; seasonal moisture; vegetation; mine disturbance; exposed playa.

**How it differs from repo code:** No exact Landsat alteration-texture feature was identified in reviewed active feature libraries — a genuinely new data family if source and AOI are suitable.

**Expected DTI improvement:** Medium–high (direct alteration signal) but mimic risk is very high.

**Implementation cost:** High — usable cloud-free dates, AOI coverage, license, data-access route, and co-registration are UNVERIFIED.

**Data-access status:** UNVERIFIED — USGS Landsat Collection 2: https://www.usgs.gov/landsat-missions/landsat-collection-2

---

## Ranking by expected DTI improvement vs implementation cost

| Rank | Hypothesis | Expected gain | Cost | Data access | Key risk |
|------|-----------|---------------|------|-------------|----------|
| 1 | H1 Off-network step-over / damage-zone conduits | Unknown (targets uncovered label space) | Low | Available | No holdout score; uniqueness vs full registry unverified |
| 2 | H2 Radiometric mixing-manifold residual | Medium | Low–medium | UNVERIFIED | Lithologic/acquisition mimics |
| 3 | H3 Strike-anisotropic shallow thermal | Medium | Medium | UNVERIFIED | Sampling bias around springs/wells |
| 4 | H4 Cross-catchment channel-profile discontinuity | Low–medium | Medium–high | UNVERIFIED | Lithologic/base-level mimics |
| 5 | H5 Landsat alteration texture conditioned on structure | Medium–high | High | UNVERIFIED | Very high mimic risk (lithology, moisture, vegetation) |

**Recommendation:** H1 is implemented and format-validated as WBG-GEMS-3. Before any submission slot, H1 needs a HOLDOUT-DTI (requires label access) and a uniqueness pass against the full portal registry. H2–H5 cannot be validated without new external data; verify each named source is obtainable before promoting.
