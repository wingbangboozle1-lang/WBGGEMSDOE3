# Preregistration — 2026-10-27 session (CSPES lane)

**Written before any candidate modelling or placement this session.** The
2026-10-26 preregistration named CSPES as the proposed single lane but no
surface, canary, placement or holdout was ever run (a universal-registry
preflight stopped that session; see `evidence/run_card.json`). This document
(a) carries CSPES forward as the one lane executed today, and (b) records four
additional ranked hypotheses that are **not** run, in line with the one-lane
budget. Every hypothesis below uses only the hash-pinned 19-band public mirror
already cached locally; none needs new external data, so all are executable in
this sandbox subject to the three-experiment budget. Ranks are qualitative
expected utility per unit cost, **not** projected DTI gains.

## Data actually available (verified this session, not assumed)

`data/raw/training_features.tif` (SHA-pinned via the shared 57GEMSDOE template,
bridge provenance — not an organizer receipt), 19 float32 bands, EPSG:32611,
3,730 × 3,292, 100 m. Band descriptions read from the GeoTIFF itself:

1 `mag_anom`, 2 `rtp`, 3 `tmi_hg`, 4 `geod_2ndinv`, 5 `iso_grav_anom_slope`,
6 `tc` (tilt angle / total curvature, magnetic edge detector),
7 `geod_shearrate`, 8 `geod_dilaterate`, 9 `tmi_vg`, 10 `deq_n100a15`,
11 `iso_grav_anom_vg`, 12 `det_elev`, 13 `iso_grav_anom`, 14 `tmi`,
15 `depth_to_base_surf`, 16 `ieq_n100a15`, 17 `cond_surf`,
18 `iso_grav_anom_hg`, 19 `det_elev_slope`. Mirror band semantics remain
unauthenticated by an organizer source (IR-06); physical interpretations below
are hypotheses, and every derived feature passes a single-feature leakage
canary before use.

## Ranked candidates

| Priority | Hypothesis; exact layers | Physical signature and why it could find an off-catalogue fault | Named non-fault mimic; falsification | Novelty vs. repo/peers; cost |
|---|---|---|---|---|
| **1 (RUN)** | **CSPES — cross-scale potential-field edge stability.** `iso_grav_anom` (13), `rtp` (2), conditioned by `det_elev` (12). | Gradient-magnitude edges of gravity and RTP magnetics that **persist across scales (σ=2,5 px)** and whose gradient **orientations are collinear**; down-weight cells where the same edge is fully explained by detrended-topography gradient. A buried basin-bounding or blind structure can produce persistent, aligned density and magnetization contrasts where no surface scarp is mapped. No catalogue-derived feature is used, so the construction is label-independent and leak-free by construction. | Lithologic contact, volcanic margin, aeromagnetic acquisition stripe. Falsify with: single-feature AUC canary (AUC > 0.90 = leakage alarm), a scale-shuffled control, and the topo-only ablation. | Distinct from GEMSDOE31 PGR31 (pseudo-gravity regression) and GEMSDOE32 SPCP (curvature crests): CSPES tests **cross-scale persistence plus cross-field directional agreement**, not residuals or curvature. The LST1 feature library contains a single-scale rank-product `crossgrad_rank_grav_mag_s3` with no orientation term, no scale persistence and no topo conditioning; CSPES is a different estimator. Medium CPU, cached data only. |
| 2 (not run) | **Strain-aligned magnetic discontinuity.** `geod_shearrate` (7), `geod_dilaterate` (8), `geod_2ndinv` (4), `rtp` (2). | RTP edges whose strike agrees with localized geodetic strain-rate gradients: active structures localizing present-day strain may lack a complete catalogue trace. | Interseismic elastic strain around known faults, InSAR/GPS processing artifacts, groundwater pumping. Falsify with flight-block / strain-scrambled controls and canary. | Peers use geodetic bands as generic gradient features (LST1 library); none documented requires **strike agreement** between strain and magnetic edges. Cheap, cached only. |
| 3 (not run) | **Basement-cover step-over.** `depth_to_base_surf` (15), `cond_surf` (17), `iso_grav_anom_hg` (18). | Sharp basement-depth gradients co-located with conductivity contrasts and gravity HG maxima: buried basin-margin faults under cover. | Stratigraphic onlap, interpolated depth surface artifacts, basin-fill conductivity changes. Falsify against SGMC mapped contacts and depth-field permutation. | GEMSDOE61 "basement-step" exists (owner score 0.0009/0.0751 — weak evidence the family is easy to get right); our variant requires three-channel concordance, not depth alone. Medium cost. |
| 4 (not run) | **Phase-based tilt crest with gravity confirmation.** `tc` (6), `iso_grav_anom_hg` (18), `tmi_hg` (3). | Tilt-angle zero/crest crossings (amplitude-invariant magnetic edges) confirmed by gravity HG maxima — robust to remanence and survey elevation. | Dipping non-fault contacts, dike swarms, deep basement edges. Falsify with remanence-stratified and amplitude-null controls. | GEMSDOE73 already ships a Blakely horizontal-gradient method (owner 0.1917); this is adjacent prior art, hence rank 4, and must be mathematically distinguished (phase vs. amplitude maxima) before any novelty claim. Cheap. |
| 5 (not run) | **Demagnetized conductive alteration halo.** `tmi` (14), `cond_surf` (17), `rtp` (2). | Smooth low-magnetization halo straddling a conductivity crest: alteration along a buried permeable structure with no surface trace. | Conductive clay, playa/basin fill, culture. Falsify with geology-matched lateral-shift nulls. | Extends the 2026-10-26 rank-2 "demagnetization halo" idea; GEMSDOE30 GDX already explored effort-normalized geothermal data, so novelty is narrow. Medium cost; `cond_surf` units/provenance unresolved (IR-06). |

## Executed-lane specification (CSPES), frozen before results

All rank transforms are empirical CDF ranks within the finite footprint
(uniform marginals, so no arbitrary band weighting).

1. Clean bands: float32 sentinel `< -1e30` and non-finite → NaN; median-fill
   only for filter inputs; footprint from `sample_submission.tif`
   (5,167,373 cells, asserted).
2. Gradient magnitudes `G_x(σ)` for x ∈ {gravity, rtp, elev} at σ = 2, 5 px
   (elev: σ = 1.5, 3, 6) via Gaussian gradient; gradient orientations
   θ_g, θ_m from the σ = 2 Gaussian gradients.
3. Per-field scale persistence `P_g = min(rank G_g(2), rank G_g(5))`,
   `P_m` analogously.
4. Collinearity `A = (1 + cos(θ_g − θ_m)) / 2` (polarity-invariant).
5. Topographic conditioning `T = rank G_elev(2)`; factor `(1 − 0.5 T)`.
6. Surface `S = P_g · P_m · (0.5 + 0.5 A) · (1 − 0.5 T)`, evaluated only on
   footprint cells; catalogue pixels are excluded from placement (the shared
   writer also zeroes them).
7. Placement: greedy top-K with min-Euclidean-distance 2 px non-maximum
   suppression (avoids stacking dots inside one 300 m kernel; prespecified,
   not tuned per fold). Primary budget K = 37,654 to match the B2/D2.8
   incumbent family for a same-budget paired comparison.
8. Leakage canary (experiment 1): per constituent field, ROC-AUC for hidden
   fault pixels vs active-domain negatives inside the eight holdout cells.
   AUC > 0.90 stops the lane.
9. Holdout (experiment 2): shared `evaluate_hide_and_recover`
   (GEMSDOE32-HIDE-RECOVER-v3.0; whole-segment hiding, 1.5 km collar,
   pooled DTI α=0.2 β=0.8, 300 m triangular kernel, 16×16 block bootstrap,
   1,000 reps). Matched incumbent: fold-local D2.8 champion proxy
   (`dotted-h19-5-d2-8` dots farther than 2 px from visible faults), same
   cells, same evaluator, paired block bootstrap of the DTI difference.
   Experiment 3 is reserved for one prespecified refinement (budget sweep
   30k/37.654k/45k, no surface reweighting) and only if experiment 2 is
   within plausible reach; otherwise the budget stays unspent.
10. Promotion rule: a positive paired Δ with a 95% CI excluding zero, canary
    pass, format validator PASS on saved bytes, and registry gates before
    placement and on final dots. Anything else is a documented negative.
    No weekly slot is selected here; a separate selector owns uploads.

## Registry / uniqueness treatment this session

The literal user rule (any registry raster, >70% of dots within 3 px or
|Spearman| > 0.90) remains unsatisfiable against the registered 17GEMSDOE
space-filling probability raster (IR-01). This session therefore reports,
for the same candidate bytes, **both**:

- the **literal any-raster result**, including the dense witness (overlap and
  correlation measured directly, never silently exempted), and
- the **sparse-submission result** against every locally restorable,
  hash-pinned historical submission raster (nine focus-site leaders, 118
  ledger rasters, 19 template registry rasters, the spacing-5 lattice null),
  using the shared `gemsw/uniq.py` definitions (excess-over-null for
  lattice-like references; two-sided |Spearman|).

Coverage of the committed 522-file/296-mask index is stated exactly; a pass on
the rebuilt subset is never represented as a full-registry clearance. The
run card carries both verdicts and the selector decides under the standing
protocol.
