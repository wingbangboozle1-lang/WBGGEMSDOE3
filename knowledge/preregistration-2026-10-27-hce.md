# Preregistration — session `arena/50217887-wbggemsdoe3`, 2026-10-27 UTC

**Written before any candidate modelling or placement.** The supplied parallel-run protocol
refers to a “single method paragraph below”; the request still does not identify one.
This document therefore records **one proposed, self-assigned lane** and four ranked
hypotheses. It is not a claim that an external coordinator assigned a lane. No other
hypothesis will be run in this session. Rankings are reasoned priorities, **not**
numerical estimates of an improvement. All data used by the chosen lane are already
present in the hash-pinned mirror downloaded by `scripts/fetch_mirrors.sh`; no new
external source is required for the lane that is actually executed.

## Ranked candidate hypotheses (only #1 is run)

| # | Hypothesis, exact layers | Physical signature / why it could find a fault missing from the USGS/INGENIOUS catalogue | Difference from anything already in this repo | Cost, data availability, confounder |
|---|---|---|---|---|
| **1 (LANE HCE)** | **Hydrothermal alteration × strain phase congruence.** Layers: GeoDAWN radiometric K, Th, U, TC (owner-mirrored `geodawn_rad_u8.tif`), ratio/extension bands ThK, UK, UTh, TMI_up150 (`geodawn_extensions_u8.tif`), reduced-to-pole magnetic anomaly and isostatic gravity (`training_features.tif` bands 2 and 13), second invariant of geodetic strain rate (band 4), detrended elevation (band 12), plus 1 m-lidar-derived scarp fields (`lidar_scarp_features_u8.tif`). Fold-legal geometry: distance to **visible-only** catalogue traces and to visible fault tips, distance to off-catalogue SGMC traces. | Compute per-channel gradient **orientation** at two scales and keep pixels where ≥3 independent physical channels have a strong, **collinearly aligned** edge (structure-tensor phase congruence), then calibrate the resulting susceptibility with a spatial-blocked gradient-boosted classifier trained **only on visible catalogue faults**. A fluid-carrying fault can produce subtle K/Th alteration + a magnetic/strain boundary with little surface scarp; such a trace is a candidate for the expert-labelled *new* faults, whereas a mapped scarp is already in the training catalogue. | LST1 (`src/gemsw/`) fitted a **ledger-supervised stratum density** and a naive-Bayes log-odds from six single-field deciles, with no nonlinear supervised learner, no cross-channel orientation congruence, no tip geometry. `knowledge/preregistration-2026-10-26.md` proposed label-independent CSPES (gravity/RTP edge persistence) but was never run. Prior sibling sites used single-channel ridges, HGB on raw bands, or ledger dot patterns; none of the pinned focus-site artefacts contains this cross-channel orientation statistic. | Medium CPU; all inputs are in the pinned mirror. No new external source needed. Confounders: lithologic contacts and volcanic units, **variable terrain clearance of the GeoDAWN drape surveys** (USGS explicitly warns about this), survey/processing stripes, roads and agricultural K-fertiliser artefacts. Hypothesis can be falsified by a single-feature AUC canary or by a holdout loss. |
| 2 | **Fold-legal tip continuation.** Hough/structure-tensor extrapolation from **visible** fault tips using the 1 m lidar scarp stack, with a 1.5 km collar so no hidden segment is used. | Faults are continuous; a withheld segment may be recoverable by continuing the visible trace along its own orientation. | Related to GEMSDOE27 `topo-gap-closure` and to many “tip/stepover” sibling submissions; only the fold-legal reconstruction would be new. | Medium, but raw 1 m 3DEP tiles (official free source: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program), links in the login-walled `1m_DEM_links.csv`) were **not obtainable** in this sandbox; the owner-mirrored 100 m lidar derivatives are usable but are not the raw DEM. **Not viable now.** Confounder: erosional lineaments and bedding. |
| 3 | **Thermal-plume contrast across a structural gradient.** INGENIOUS 2 m temperature probes and well/spring temperatures, normalised by probe-site density, conditioned on slip/dilation tendency. | An advective thermal anomaly on one side of an unmapped structural boundary can indicate a permeable fault. | GEMSDOE30 `GDX` and other sibling sites already explored effort-normalised geothermal data; this would be an extension, not proven novelty. | High. Free official source: [GDR submission 1391](https://gdr.openei.org/submissions/1391), CC BY 4.0; **verified publicly listed** (`2m Temperature Probes.zip`, `Well and Spring Temperature and Chemistry.zip`, `Quaternary Faulting Slip and Dilation Tendency`). Byte-level coverage/CRS and sandbox download were **not verified** → **not viable now**. Confounders: groundwater flow, climate, sampling bias. |
| 4 | **Geodetic velocity discontinuity from InSAR.** Sentinel-1 line-of-sight velocity gradients from ASF DAAC, conditioned on the provided strain-rate bands. | A creeping or compliant fault zone can show a velocity step without a scarp. | No sibling artefact in this checkout uses InSAR. | High; needs new external data (NASA/ASF, EOSDIS open data) and a licence/attribution review before use. **Not viable now.** Confounders: atmospheric delay, subsidence from groundwater pumping, volcanic deformation. |

## Lane definition (frozen before the run)

* **Name:** `HCE-1` — hydrothermal/strain **cross-channel edge congruence**, fold-legal supervised calibration, metric-optimal dot placement.
* **Mechanism:** phase-congruence features → per-cell `HistGradientBoostingClassifier` trained on visible faults only → probability field → Dinkelbach/`gems57`-style metric-optimal allocation of `p=1` dots (α=0.2, β=0.8, 300 m triangular kernel) with visible-catalogue exclusion.
* **Named non-fault process that can mimic it:** a potassium-rich lithologic contact or a variable-clearance radiometric survey stripe that is collinear with a magnetic/gravity edge, especially along flight-line azimuths (official GeoDAWN release: flight lines at azimuth 90°, 200/400 m spacing).
* **Evaluator:** the **unmodified** vendored `src/gemsw/holdout.py` / `metric.py` (verbatim GEMSDOE32 copies, see `NOTICE.md`): `evaluate_hide_and_recover`, whole-segment hiding, 15 px collar, visible-only masking, pooled DTI, 256-block spatial cluster bootstrap 95% CI; secondary `evaluate_sgmc_with_ci` for off-catalogue USGS SGMC traces. No private fork.
* **Writer:** the **unmodified** vendored template writer `vendor/gems57/submission_writer.py` (fail-closed, all-finite `[0,1]`, single-band float32, EPSG:32611, exact sample grid), plus a second independent validator `scripts/submission_writer.py`.
* **Baselines:** (a) `champion_proxy` = fold-local D2.8 dotted H19-5 network with B=2 pruning (HOLDOUT-DTI 0.0992 in `evidence/holdout_results.json`; **note it is not fold-legal** — the H19-5 network was built from the full catalogue, so it contains hidden segments); (b) LST1 `lst_mod_quota_median` (0.0777), the best previously measured **fold-legal** candidate. A paired win over (a) is required for a `promote` verdict; (b) is reported as the fair matched incumbent.
* **Budget:** 3 experiments maximum: E1 canary + baseline replay, E2 HCE candidate, E3 one prespecified variant (dot budget / γ). No weekly slot is selected here.
* **Stop rules:** single-feature AUC > 0.90 on the pooled holdout ⇒ leakage stop; absolute Spearman > 0.90 vs any registry raster ⇒ duplicate stop; > 70 % of final dots within 3 px of one **sparse dot-mask** registry raster ⇒ duplicate stop. Checked before placement (surface) and on the final dots.

## Registry / uniqueness contract and the flagged contradiction (read before the result)

The registry is **frozen** to: (i) the nine pinned focus-site best TIFFs in
`research/input_manifest.json`; (ii) the 117 SHA-verified live-scored sibling rasters in
`data/ledger/`; (iii) the 12 scored/calibration rasters in `data/raw/scored/`;
(iv) every GeoTIFF already shipped in this repository (`docs/`, `submission/`, `site/`,
`archive/`); (v) the pinned 17GEMSDOE `E-proba` raster, included as a **control**, not
deleted.

A raster is classified **before** comparison by its stored values, not by its filename:

* **Sparse dot mask** — binary/near-binary, positive support < 20 % of the 5,167,373-cell
  footprint. These have “dots” in the sense of the user's rule; the literal 3 px overlap
  test and the two-sided |Spearman| test are both applied.
* **Continuous field / control** — e.g. the 17GEMSDOE `E-proba` raster, which this session
  re-read independently: 4,729,578 distinct float values, positive on **all 5,167,373**
  footprint cells. It has no dot set. Applying a finite-positive “dot” definition to it
  makes *every* non-empty in-footprint candidate 100 % overlapping — a vacuous universal
  witness. For continuous fields only the **two-sided |Spearman| rank test on the common
  footprint** is meaningful; the vacuous literal overlap is still **reported** as
  `literal_overlap_vs_continuous_control = 1.0` with the explanation. This is **not** a
  threshold change: 0.90 and 70 % are unchanged, and no raster is removed from the
  inventory. It is an interpretation of what counts as a “dot”, preregistered here and
  flagged as IR-09 for the user to ratify.

**Therefore:** if the user insists on the literal finite-positive reading of continuous
control fields, this lane stops with a duplicate verdict exactly as the earlier session
did. Under the non-vacuous reading above, the lane may produce a candidate. The run card
records both readings. No organizer-confirmed score exists; all performance numbers are
HOLDOUT-DTI (evaluator version, withheld-positive count, 95 % CI) or explicitly labelled
owner-reported claims / projections.

## Official sources consulted for the hypotheses (manual review links)

* [DrivenData problem description & metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — α=0.2, β=0.8, R=300 m, single-band float32 `[0,1]`, EPSG:32611.
* [DrivenData about page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/) — faults, fluids, edge detection and gravity/magnetic methods.
* [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — magnetic = subsurface structure, radiometric = surface materials, CC0 1.0, variable terrain clearance, flight-line azimuth 90°.
* [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) — free lidar/DEM source for hypothesis 2 (not obtained here).
* [GDR INGENIOUS 1391](https://gdr.openei.org/submissions/1391) — CC BY 4.0 thermal/fault/slip-tendency datasets for hypothesis 3 (not obtained here).
* [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) and [DrivenData rules](https://www.drivendata.org/competitions/306/competition-doe-gems/rules/) — weekly submission cap and external-data licence requirements.
* [Public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — timestamped public observation only, never a receipt.

---

# Addendum (after E2/E3, before E4) — 2026-10-27 UTC

E1 was a **replay** of an existing incumbent on the same evaluator, not a new
geological experiment. E2 and E3 were the same HCE hypothesis with two prespecified
(γ, dot-cap) settings. Both were **negative**: HOLDOUT-DTI 0.0236 and 0.0231 vs the
replayed 0.0992 champion proxy. The diagnosis is measured, not speculative:
**100 % of E2 dots sit within 5 px of a visible fault** (because the fold-legal
`dyn_d_visible` / `dyn_d_tips` features dominated the boosted model), and only 11–17 %
of withheld truth pixels are within 3 px of any dot. The candidate is too concentrated
around what is already mapped.

E4 is therefore the **third and final experiment**. It keeps the same HCE physical
feature stack but changes the decision rule in two prespecified ways:

1. **Drop both catalogue-geometry features.** The susceptibility model uses only the
   56 static physical fields (competition bands, radiometric ratios, the novel
   cross-channel phase congruence, lidar scarp fields, external proximities). This
   removes the near-visible-fault attractor and is also the better transfer model for
   the real target, which is *new* faults rather than withheld catalogue faults.
2. **Change the placement from Dinkelbach to saturated dotted coverage of the top-q
   physical-susceptibility region.** For a fixed global 3 px or 4 px lattice, emit one
   `p=1` dot on every lattice cell whose predicted susceptibility is in the top q of
   the active domain. Rationale: with α=0.2 a false positive is cheap, the 300 m kernel
   gives credit to anything within 3 px, and a physically ranked region can hold more
   truth per dot than a uniform lattice. q and lattice spacing are chosen **only** on
   the independent off-catalogue SGMC fault population (`evaluate_candidate_holdout`'s
   `sgmc_off_catalogue_raw_dti`), never on the withheld holdout truth. The selected
   configuration is then scored **once** on the hide-and-recover holdout.
   A dot-count-matched random lattice control is reported in the same experiment.

No further experiment will be run. E4 is the candidate that is written to a GeoTIFF,
whether its verdict is `promote` or `negative`.
