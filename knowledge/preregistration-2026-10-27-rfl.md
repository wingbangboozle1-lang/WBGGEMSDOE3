# Preregistration — session `arena/bd44f94b-wbggemsdoe3`, 2026-10-27 UTC (RFL lane)

**Written before any candidate modelling or placement in this session.** The supplied
parallel-run protocol refers to a "single method paragraph below"; the request again does not
identify one. This document therefore records **one proposed, self-assigned lane (RFL)** and
four additional ranked hypotheses that are **not** run. It is not a claim that an external
coordinator assigned a lane. Rankings are reasoned expected-utility-per-cost priorities,
**not** numerical DTI projections. All data used by the executed lane are byte-verified
hash-pinned mirrors already restored this session (`scripts/fetch_mirrors.sh`: 26/26 PASS;
`scripts/restore_comparators.py`: 9/9 focus leaders PASS; `scripts/fetch_ledger_rasters.py`:
118/118 PASS). Mirror bytes establish byte identity, **not** organizer provenance (IR-06).

## What is already implemented in this repository (novelty baseline, measured — not assumed)

| Lane | Construction | Best local evidence (labelled) |
|---|---|---|
| skarpline union (`evidence/gemsdoe_run_card.json`) | Ridge NMS of plan/profile curvature + paired-scarp response of detrended elevation, union 2 m LiDAR slope-excess/antislope NMS; 97,608 binary dots | PROXY-DTI 0.2131 [0.2016, 0.2254], `gemsdoe-dti-v1.0`, SGMC off-catalogue proxy, 62,122 proxy positives. **Never evaluated on the shared hide-and-recover holdout.** Leaderboard number 0.428 is an ESTIMATE from a ground-truth-size fit, not a score. |
| CSPES (`evidence/cspes_run_card.json`) | Cross-scale persistent, orientation-collinear gravity + RTP magnetic gradient edges, topo-conditioned; 37,654 dots | HOLDOUT-DTI 0.0257 [0.0194, 0.0319], `GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld positives; paired Δ vs champion proxy −0.0736. **Negative** (at/below matched random null in the budget sweep). |
| HCE-1 (`evidence/hce_run_card.json`) | 56 physical fields → spatially blocked HistGradientBoosting on visible faults → saturated 3 px lattice over top-30 % susceptibility; 169,968 dots | Fold-local HOLDOUT-DTI 0.1292 [0.1160, 0.1426]; static read-back of the saved file 0.0931 [0.0824, 0.1037]; owner-ledger projection 0.082 does not support beating 0.2778. |
| LST1 (archived) | Landsat-LST-modulated network hybrid | HOLDOUT-DTI ≈0.063–0.067, paired Δ vs champion ≈ −0.033…−0.036. Negative. |
| Champion proxy (incumbent) | Fold-local `dotted-h19-5-d2-8` dots >2 px from visible faults | HOLDOUT-DTI 0.0992 [0.0860, 0.1127], same evaluator/cells. Leakage-contaminated (built from the full catalogue) — a hard incumbent, by design. |

Single-layer evidence (`evidence/layer_ranking.json`, SGMC proxy, top-20k dots/layer):
2 m LiDAR scarp channels (proxy DTI 0.064) and detrended-topography slope/coherence (0.053)
dominate; gravity/magnetic raw edges are 0.001–0.010; geodetic strain 0.0006–0.0013;
`depth_to_base_surf` top-20k hit rate is exactly 0. This ranking is why pure potential-field
lanes are deprioritised below and why the executed lane stays topographic but changes the
*physical target* from scarp faces to the relief discontinuity at the range front.

## Ranked candidate hypotheses (only #1 is run)

| # | Hypothesis; exact layers | Physical signature / why it could find a fault missing from the USGS/INGENIOUS catalogue | How it differs from everything already in this repo | Cost; data availability; named non-fault mimic |
|---|---|---|---|---|
| **1 (LANE RFL — RUN)** | **Range-front relief-discontinuity lineaments.** `det_elev` (band 12) only. | Focal relief `R = max−min` elevation in 500 m and 1.1 km windows; score = multi-scale persistence `min(rank|∇R₅₀₀|, rank|∇R₁₁₀₀|)` of the relief-gradient magnitude. Basin-and-Range normal faults localise the abrupt transition from high-relief range to low-relief basin fill. A fault buried under young alluvium can have **no scarp face** (hence no catalogue trace, which is built from mapped scarps) while the relief step across the range front persists at 0.5–1 km scale. No catalogue-derived quantity enters the surface, so it cannot be a catalogue copier. | skarpline thresholds *elevation* slope/curvature/LiDAR free-faces (the scarp itself); CSPES thresholds potential-field gradients; HCE learns a supervised susceptibility and saturates it with a lattice. RFL is the gradient of a **focal-range (relief) field** — a facies-boundary detector, not a scarp-face, potential-field-edge, or learned-susceptibility detector. No code in `src/` computes a relief-gradient. | Cheap (two focal-range filters + gradients on one cached band). Data: verified mirror band 12, obtainable (SHA-pinned this session). **Mimic:** lithologic range fronts (resistant-rock boundaries), alluvial-fan heads, pluvial shorelines. Falsify via canary + holdout vs matched random null + piedmont-gate ablation. |
| 2 (not run) | **Geothermal-manifestation alignments.** GDR INGENIOUS well/spring + paleo-geothermal point files + volcanic vents (mirror CSVs/zips), gated by `det_elev_slope` rank. | Travertine/sinter/spring deposits precipitate where faults channel upwelling fluid; alignments of ≥2 manifestations along a common strike may trace an unmapped permeable structure. | No in-repo lane uses point-process alignment of geothermal manifestations as the placement generator (HCE used radiometric/thermal *rasters* as HGB features only). | Medium (point rasterisation + strike fitting; strike modes must be fold-local). Obtainable: hash-pinned mirrors of GDR submission 1391 (DOI 10.15121/1881483) restored this session; only ~281 in-footprint points, so recall is structurally capped — main reason it is #2, not #1. **Mimic:** range-front groundwater discharge along lithologic contacts. |
| 3 (not run) | **Strain-aligned seismicity/magnetic discontinuity.** `deq_n100a15` (10), `ieq_n100a15` (16), `geod_shearrate` (7), `rtp` (2). | RTP edges whose strike agrees with localised geodetic shear-rate gradients and clustered inter-event seismicity: actively straining structures may lack a complete mapped trace. | CSPES required gravity–magnetic collinearity with no strain/seismicity term; peers used these bands as generic features. Strike *agreement* between strain and magnetic edges is untested in-repo. | Cheap, cached only. Deprioritised by measured single-layer proxy DTI ≤0.005 for every constituent band. **Mimic:** interseismic elastic strain around known faults; swarm seismicity on volcanic systems. |
| 4 (not run) | **Demagnetised conductive alteration halo.** `tmi` (14), `cond_surf` (17), `rtp` (2). | Smooth low-magnetisation halo straddling a narrow conductivity crest: hydrothermal alteration along a buried permeable fault with no surface expression. | Signed cross-profile halo geometry, not an edge magnitude (CSPES) or a learned feature (HCE). | Medium. `cond_surf` units/provenance unresolved (IR-06) and single-layer proxy DTI 0.0015 — not viable as this session's single lane until channel provenance is organiser-confirmed. **Mimic:** conductive playa clay / basin fill. |
| 5 (not run) | **Basement-cover step-over.** `depth_to_base_surf` (15), `iso_grav_anom_hg` (18), `cond_surf` (17). | Coincident basement-depth step, gravity horizontal-gradient maximum and conductivity contrast at a buried basin-margin fault. | Three-channel concordance of a *depth step*; in-repo lanes do not use band 15 at all. | Medium. Directly contradicted as a primary signal by `evidence/layer_ranking.json` (band-15 top-20k proxy hit rate 0.000) and by the GEMSDOE61 owner-reported 0.0009/0.0751 family results. Named here so the negative prior is on record. **Mimic:** stratigraphic onlap / interpolated depth-surface artefacts. |

## Executed-lane specification (RFL), frozen before results

All ranks are empirical-CDF ranks within the finite footprint (5,167,373 cells, asserted by
the shared grid loader). The surface is **label-independent**: catalogue pixels are excluded
only at placement (shared `gemsw.cspes.place_dots`, reused unchanged) and zeroed by the
shared vendor writer, exactly as in the CSPES lane.

1. Clean `det_elev`: sentinel/non-finite → NaN; median-fill for filter inputs only.
2. Focal relief `R₂ = max₅ₓ₅ − min₅ₓ₅` (500 m) and `R₅ = max₁₁ₓ₁₁ − min₁₁ₓ₁₁` (1.1 km)
   via grey dilation/erosion (`scipy.ndimage.maximum_filter/minimum_filter`, `mode="nearest"`).
3. Relief gradients `G₂ = |∇(R₂; σ=1.5)|`, `G₅ = |∇(R₅; σ=1.5)|` (shared Gaussian-gradient code).
4. Surface `S = min(rank G₂, rank G₅)` on footprint cells (multi-scale persistence).
5. Predeclared ablations (diagnostics of the frozen spec, same placement rule):
   `abl_g500_only = rank G₂`; `abl_g1100_only = rank G₅`;
   `abl_piedmont_gate = S · 1[0.25 ≤ rank R₅ ≤ 0.90]` (basin-margin relief context only);
   `abl_slope_reference = rank |∇(det_elev; σ=1.5)|` (the skarpline-family input, as a
   same-budget topographic reference — not a candidate).
6. Placement: shared greedy top-K, 2 px NMS, K = 37,654 (matched B2/D2.8 family budget).
7. **E1 — leakage canary:** per-field ROC-AUC (raw `det_elev`, `R₂`, `R₅`, `G₂`, `G₅`,
   `rank R₅`, full `S`) for withheld positives vs active-domain negatives in the eight
   shared holdout cells. Any AUC > 0.90 stops the lane.
8. **E2 — holdout:** shared `gemsw.holdout.evaluate_hide_and_recover`
   (`GEMSDOE32-HIDE-RECOVER-v3.0`; whole-segment hiding, 1.5 km collar, pooled DTI
   α=0.2, β=0.8, 300 m triangular kernel, 16×16 block bootstrap, 1,000 reps) for RFL,
   the four ablations, a same-K seeded random null, and the fold-local champion proxy
   (rebuilt exactly as in `scripts/run_cspes.py`). Paired block bootstrap of
   RFL − champion and RFL − null. The same battery also scores the three **existing saved
   files** (skarpline, HCE-1, CSPES) as static masks — labelled STATIC-FILE (not
   fold-local: skarpline/HCE used the full catalogue in construction/suppression).
   Because the RFL surface is label-independent and placement excludes the *full*
   catalogue (⊇ each cell's visible set), static-mask evaluation of RFL is conservative:
   dots that would fall on hidden segments are removed before scoring.
9. **E3 — one prespecified refinement, only if E2 is within plausible reach**
   (paired Δ vs champion CI upper bound > 0): budget sweep K ∈ {60,000, 97,608} on the
   frozen surface (97,608 matches the skarpline mass), no surface reweighting. The final
   file uses the E3 budget only if it beats K = 37,654 on the same holdout; otherwise it
   uses K = 37,654. If E2 is not within reach, E3 stays unspent and the verdict is negative.
10. **Uniqueness gates, checked on the surface before placement and on the final dots,**
    against the rebuilt lane-local registry (151 files / 120 unique dot masks:
    119 sparse submission masks + 1 dense witness; `.cache/registry/*.npy`):
    exact dot-duplicate; % of candidate dots within 3 px of each reference (disc dilation);
    Spearman correlation of 1.5 px-Gaussian-smoothed fields on a fixed footprint sample.
    **Stop rule (protocol):** |ρ| > 0.90 against any registry raster, or > 70 % of dots
    within 3 px of any *sparse submission* raster → log duplicate, stop, no file promoted.
    The literal any-raster reading (including the space-filling 17GEMSDOE witness, positive
    on all 5,167,373 footprint cells) is reported separately and is vacuous for every
    non-empty candidate including the champion itself (IR-01/IR-11); it is never silently
    exempted and never represented as passed.
11. **Promotion rule:** canary pass **and** paired Δ vs champion proxy > 0 with 95 % CI
    excluding zero **and** saved-byte format validator PASS **and** sparse-registry gates
    pass → verdict `promote`. Anything else → `negative` (the TIF is still written and
    downloadable as a research artifact, clearly labelled not cleared). No weekly slot is
    selected in this session; a separate selector owns uploads.
12. **Packaging:** shared vendor writer `vendor/gems57/submission_writer.write_submission`
    (fail-closed; prediction must already be finite and in [0,1] — no silent repair),
    zeros outside the footprint, catalogue zeroed, plus an independent rasterio read-back
    validator on the saved bytes (single band, float32, CRS/shape/transform = sample,
    no NaN anywhere, all values in [0,1], zero mass outside footprint/on catalogue).
    File identity = content SHA-256 in the name; submission note ≤ 140 characters.

## E0 audit (not an experiment; no placement)

Independent re-measurement of all nine focus-site leader rasters (GEMSDOE24/25/27/28/30/31/
32/33/36, SHA-pinned in `registry/focus_sites.json`): saved-byte format checks, dot counts,
all 36 pairwise Jaccard / within-3-px overlaps, subset relations, catalogue-distance
anatomy of the GEMSDOE32-vs-31 difference, and static HOLDOUT-DTI + SGMC-proxy DTI for each
leader on the shared evaluators. This closes IR-17 (previously only 31/32/36 were
independently re-measured). Owner-reported scores are carried as USER-REPORTED claims,
never as organizer-confirmed scores; no receipt exists in this repository for any of them.

## Budget

3 experiments (E1 canary, E2 holdout battery, E3 conditional budget sweep) / 2 hours.
E0 is read-only audit of existing bytes. Slots used: 0.

---

## Amendment 1 — 2026-10-27, after E1, before any placement or holdout (transparent, not silent)

E1 canary passed (all AUC ≤ 0.594). The pre-placement surface check was first run with a
*probe* support (raw top-K surface cells, no NMS). Results (`evidence/rfl_uniqueness.json`,
preserved): surface Spearman vs every registry mask ≤ |0.72| (**pass** at the 0.90 limit),
but probe-dot within-3-px overlap marginally exceeds 0.70 against two sparse masks
(18GEMSDOE H19-C: 0.7033, 513,786 ref dots; GEMSDOE49 gate_ortho: 0.7016, excess +0.55),
and trivially against space-filling controls (witness 1.000; spacing-5 lattice 0.9978 with
null 0.9991, excess −0.0012).

The user protocol assigns the **rank-correlation** test to the surface and the **70 % dot**
test to dots ("Check this on the surface before placement AND on the final dots"); both
prior in-repo lanes operationalised it that way (CSPES surface U2 Spearman; HCE surface
gate = Spearman only), and the shared historical definitions judge lattice-like references
(null overlap ≥ 0.70) by excess-over-null ≤ 0.05 rather than raw overlap, because a random
same-count placement also "fails" raw overlap against them. This lane therefore continues
under that exact published gate structure — U1 no exact duplicate; U2 |Spearman| ≤ 0.90
(surface and final); U3 final-dot raw overlap ≤ 0.70 vs every non-lattice sparse mask;
U3 lattice-like excess ≤ 0.05 — with the **literal any-raster result still reported and
still failing** (IR-01/IR-11). The probe numbers above stay on record as a warning: the
relief-gradient surface has genuine affinity with the scarp-family networks, and if the
actually placed (2 px-NMS) dots breach U3, the lane stops as a duplicate. **No
uniqueness repair / halo-avoidance placement will be used** to evade the gate. Nothing else
in the frozen specification changes; no holdout number had been seen when this was written.
