# Candidate geological hypotheses — 2026-10-31 (H66 lane)

**Purpose.** Five distinct, testable ways to place dots on faults that the public
USGS/INGENIOUS catalogue does not contain. Rank is research priority (expected DTI
improvement per unit cost), **not** a score projection: no number here is a score.

**Why new geological information is required at all.** The byte-verified chain in
`content/why-0.2778.md` shows that the nine focus files are one and the same
121,131-cell parent network, re-thinned and re-pruned (GEMSDOE31 → GEMSDOE32 is
*only* a 2-px catalogue-band exclusion, reproduced with 0 mismatches). Every dot
of that network lies within 3 px of the family, so any re-cut of it is a
duplicate under the project's own rule, and the metric algebra says the family
is already near its own ceiling: a marginal dot needs kernel credit
k > α·DTI ≈ 0.056 to pay for itself, and every tested addition *hurt*.

**Common infrastructure (shared, never forked).** Pinned template
57GEMSDOE @ `822a0ce5546c7b6749cdd82eb145b6b3e616603d`:
`gems57.metric` (α=0.2, β=0.8, 300 m triangular kernel), `gems57.holdout`
(whole-component hiding with a 3-px feature collar and 12-px domain erosion),
`gems57.evaluate_holdout` (pooled DTI + paired spatial-cluster bootstrap),
`gems57.emit` (exact-DTI greedy allocator), `gems57.submission_writer`
(fail-closed writer) and `gems57.uniqueness` (registry audit). The feature
stack is the template's own cached quantile bank
(`scripts/prep_feature_stack.py`): per band, a global rank `q` and a 9-cell
local standardised contrast `z`.

---

## Rank 1 — H66-SPRP · catalogue-independent supervised ridge probability  ✅ TESTED THIS SESSION

* **Layers.** All 19 official GeoDAWN/competition bands: `mag_anom`, `rtp`,
  `tmi`, `tmi_hg`, `tmi_vg`, `iso_grav_anom`, `iso_grav_anom_hg`,
  `iso_grav_anom_vg`, `iso_grav_anom_slope`, `tc` (tilt angle), `det_elev`,
  `det_elev_slope`, `depth_to_base_surf`, `cond_surf`, `geod_2ndinv`,
  `geod_shearrate`, `geod_dilaterate`, `deq_n100a15`, `ieq_n100a15`.
  38 features = per band {`q`, `z`}.
* **Physical signature targeted.** A fault in this setting is a *narrow local
  magnetic/gravity contrast* (tilt-angle and gradient ridge) plus a possible
  topographic scarp; `z` is exactly that signature (local standardised contrast
  against the 9-cell neighbourhood), and `q` carries the regional level so the
  classifier can tell "high everywhere" from "locally anomalous".
* **Why it should catch a fault missing from the catalogue.** The classifier
  never sees where the catalogue is. It is trained on *visible* mapped faults
  only and then asked for that geophysical expression everywhere, including
  terrain with little or no mapping. No catalogue-distance, catalogue-density
  or catalogue-shape feature enters the model, so the fold-local holdout has no
  catalogue channel that could leak (canary max AUC 0.65 < 0.90).
* **How it differs from anything already in this repo.** Every previous lane is
  catalogue-relative: HCE-1 (congruence), THCS-OOF (catalogue-free but
  feature-level), LBCAL (score-fitted density), TDE-30K (score tomography),
  CSPES (edge stability), AMDC (magnetic dipole), KHD, FCHD, RFL, LST1. None
  trains a classifier on the official 19-band stack, and none emits with the
  shared exact-DTI allocator over a supervised probability field.
* **Named non-fault mimic.** Lithologic/weathering contacts and mafic
  magnetic-source edges (a dyke swarm has the same local magnetic contrast as
  a fault); buried basin-margin flexures in the gravity bands.
* **Cost / data access.** Low — CPU only, no GPU; the official stack is already
  hash-pinned locally (`4371c82e…`, 418,912,844 B). ~80 s per full-grid
  prediction, ~5 s per fold fit.
* **Result.** See `evidence/h66_sprp/holdout.json` (HOLDOUT-DTI with CI),
  `evidence/h66_sprp/leakage_canary.json`, `evidence/h66_sprp/uniqueness.json`.
  This is the lane that produced the downloadable submission.

## Rank 2 — H67-SARPCORR · cross-physics ridge agreement cascade

* **Layers.** `tc` (tilt angle), `tmi_hg`, `tmi_vg`, `iso_grav_anom_hg`,
  `iso_grav_anom_vg`, `det_elev_slope`.
* **Signature.** Non-maximum-suppressed ridge crests of the magnetic tilt-angle
  and of the isostatic-gravity horizontal gradient, kept only where an
  independent magnetic crest and an independent gravity crest agree within
  1–2 px (two different physical sources, two different instruments).
* **Why uncatalogued.** The parent network that every focus file re-cuts is
  topographic-led ("h19-5 … powerlaw budget, multiline corroborated"). A
  magnetics/gravity-led network privileges structures whose topographic
  expression is weak — the classic blind basement faults.
* **Difference from the repo.** No lane builds an explicit cross-physics ridge
  *graph* with agreement gating on the official tilt-angle and
  gravity-gradient bands; the CSPES lane measures edge stability, not
  agreement between two physical sources.
* **Named non-fault mimic.** Dyke swarms and mafic contacts (magnetic crest
  without a gravity counterpart) and carbonate-platform / basin-margin edges
  (gravity counterpart without a magnetic crest).
* **Cost / access.** Low–moderate: ridge tracing on 12.3 M cells, ~1 GB RAM
  working set; no new data.

## Rank 3 — H68-THERM · geothermal-context anchored emission

* **Layers.** `cond_surf`, `det_elev`, `tc`, `tmi_hg` **plus** the free,
  official geothermal context: DOE GDR #1391 wells/springs and volcanic vents
  (CC BY 4.0), the INGENIOUS 2-m temperature-probe regional dataset, and the
  regional paleogeothermal compilation — all already mirrored locally under
  `data/raw/external/`.
* **Signature.** A geophysical lineament is emitted only where it passes within
  ~1 km of a geothermal indicator (spring/well/vent/probe) *and* the
  conductivity band steps across it.
* **Why uncatalogued.** The competition's hidden truth is the operators' own
  detailed fault mapping, which is concentrated on geothermal systems; the
  family emits globally, so a context-gated emission can spend its dot budget
  where the truth actually is.
* **Difference from the repo.** Prior lanes used thermal/radiometric channels
  only as corroboration inside a global network; none used a geothermal
  indicator as an *anchor gate*.
* **Named non-fault mimic.** Springs and wells sited on roads, canals and
  human-made cuts; probe arrays along access roads — the GDR and INGENIOUS
  point data are strongly road-biased.
* **Cost / access.** Low if the GDR/INGENIOUS mirrors stay reachable (they are
  hash-pinned locally); the official sources are
  <https://gdr.openei.org/submissions/1391> and
  <https://gbcge.org/current-projects/ingenious/>.

## Rank 4 — H69-STRAT · basement-block boundary faults (no magnetic signal)

* **Layers.** `depth_to_base_surf`, `iso_grav_anom` (isostatic residual),
  `iso_grav_anom_vg`, `cond_surf`.
* **Signature.** Iso-depth contours of basement depth that step laterally —
  a gravity gradient aligned with a basement step, with no magnetic edge at
  all.
* **Why uncatalogued.** Blind faults that juxtapose basement blocks produce a
  gravity step but no magnetic anomaly, so every magnetics-led method (the
  whole focus family) misses them by construction.
* **Difference from the repo.** The LBCAL and TDE lanes use gravity and
  conductivity only as density columns; neither isolates basement-step
  boundaries.
* **Named non-fault mimic.** Depositional facies boundaries and paleo-basin
  margins in the basin fill, which step basement depth without being faults.
* **Cost / access.** Low; official bands only.

## Rank 5 — H70-DTRACER · catalogue-conditional splay extrapolation

* **Layers.** Visible catalogue geometry (segment ends, stepovers, relay
  ramps) + the full 19-band stack for the trace shape.
* **Signature.** Short splays launched from a mapped segment tip into the
  1–2 km gap between two mapped strands, oriented along the local structural
  grain (the `z` ridge azimuth), then allocated under the exact DTI bar.
* **Why uncatalogued.** New traces in a refined structural map are mostly short
  splays and relay ramps between mapped strands — exactly the population the
  family (a global skeleton) cannot add, because its parent network is already
  saturated in the halo of every mapped strand.
* **Difference from the repo.** The off-catalogue "step-over / damage-zone"
  lane of 2026-10-29 proposed corridors but never allocated them under the
  shared DTI bar and never rebuilt them fold-locally.
* **Named non-fault mimic.** Erosional jogs and along-strike segmentation of a
  single fault strand (geometric, not structural).
* **Cost / access.** Moderate; catalogue-derived, so every feature must be
  rebuilt from the *visible* faults only inside each fold, which multiplies the
  cost by the number of folds.

---

## Pruning rules that apply to all five

1. Each hypothesis is tested on the shared hide-and-recover instrument with a
   per-feature leakage canary (AUC > 0.90 ⇒ leakage).
2. An emission is only promoted if it beats the current comparable holdout best
   on identical folds with a paired CI whose lower bound is above zero.
3. Uniqueness is checked twice — literally against every indexed registry
   raster, and like-for-like against registry rasters that are themselves dot
   fields — and both readings are published.
4. No weekly slot is spent by a research lane.
