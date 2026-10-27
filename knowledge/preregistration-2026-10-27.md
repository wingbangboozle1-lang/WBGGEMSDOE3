# Preregistration — session 2026-10-27 (SGCE lane)

**Written before any candidate modelling, placement or holdout run in this session.** The
parallel-run protocol still refers to a “single method paragraph below” that was never supplied;
as in the [previous preregistration](preregistration-2026-10-26.md) this is a **proposed** lane,
not an externally assigned one. Only H1 is executed. Budget: 3 experiments / 2 hours. No
submission slot is selected here.

## Official facts verified this session (links for manual review)

| Fact | Source |
|---|---|
| Task = predict **all** faults; public labels are known USGS/INGENIOUS faults; hidden test labels are **newly expert-identified faults**; Phase 2 re-scores against an expanded label set after expert review of all submissions | [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| DTI: triangular 300 m (3 px) kernel, α=0.2, β=0.8; TP uses `max` kernel credit per truth pixel; FP = Σ p(x)[1−max k]; pooled over all public-test pixels | [metric section](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric), [organizer pooling answer](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2) |
| Known USGS/INGENIOUS fault pixels are **masked / excluded from evaluation**, so predicting them does not help or hurt | [organizer answer, 16 Sep](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2) |
| Organizers will not disclose which data or fault types the experts used | [organizer answer, 23 Sep](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/7) |
| Format: one float32 band, EPSG:32611, 100 m, same bounds/transform, [0,1], null/NaN outside bounds | [submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format) |
| ≤3 submissions/week, one selected final GeoTIFF for both rounds, generative-AI disclosure required | [official rules §3.2](https://docs.nlr.gov/docs/fy26osti/96647.pdf) |
| GeoDAWN magnetics image **subsurface** geology/structure; radiometrics image surface materials; terrain clearance is variable; lidar was collected with 3DEP; data release CC0 1.0 | [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) |
| INGENIOUS compilation (2 m probes, Quaternary faults, slip/dilation tendency, geodetic shear/dilation, well/spring temperatures, seismicity) is public under CC BY 4.0 | [GDR submission 1391](https://gdr.openei.org/submissions/1391) |
| Public leaderboard leader observed 0.4544 on 2026-10-27 (timestamped observation, not our score, not a receipt) | [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) |

## Ranked new geological hypotheses (none of these was run in the previous session)

Priority is reasoned judgement about expected **holdout DTI** gain and implementation cost, not a
numerical forecast. Every hypothesis names the layers, the transform, the off-catalogue mechanism,
the non-fault mimic, and how it differs from code already in this repository.

| Rank | Hypothesis, layers and signature | Why it could catch an **uncatalogued** fault | Cost / data availability | Named mimic and prior-art difference |
|---|---|---|---|---|
| **H1 — SGCE (chosen lane)**: stress-gated along-strike continuation + metric-optimal coverage. Layers: cached `geod_dilaterate`, `geod_2ndinv`, `geod_shearrate`, `det_elev`, `det_elev_slope`, `tc`, `tmi_hg`, `iso_grav_anom_slope`, `cond_surf`, `depth_to_base_surf`, `ieq_n100a15`, LiDAR scarp bands, radiometric K/Th/U, `dist_sgmc_fault`; plus **fold-local** visible-catalogue geometry (connected-component PCA strike, endpoint continuation corridors, relay/step-over parallelograms, distance-to-visible annulus). Transform: rank-bin naive-Bayes susceptibility fitted on visible faults only × geometric continuation prior × strain gate, then Dinkelbach/submodular coverage placement of binary dots with the exact DTI kernel. | New expert-mapped faults in the Basin and Range are commonly along-strike continuations, relay ramps or en-échelon segments of mapped Quaternary faults whose surface scarp is subdued by alluvium. Extrapolating visible endpoints along a PCA strike, gated by present-day dilatational strain and potential-field edges, targets corridors that a point-wise feature model or a static ridge network cannot represent. | Medium CPU; **no new external data needed**. All layers are in the hash-pinned cached 19-band stack and the mirrored official external layers. Provenance of the mirror is hash-verified, not organizer-authenticated. | **Mimic:** lithologic contacts, aeromagnetic acquisition stripes, alluvial-fan/road edges and erosional scarps all create linear edges. Differs from `src/gemsw/candidate.py` (LST1 ledger tomography + H19-5 on/off quota), from GEMSDOE27 topo-gap closure and GEMSDOE33 tip-stepover rasters: no previous submission raster enters ρ, the geometric prior is rebuilt per fold from visible faults only, and dot count is set by explicit DTI marginal gain rather than a fixed ledger quota. |
| H2 — Radiometric–magnetic cross-gradient **null**: pixels where a magnetic tilt/gradient edge has no co-located radiometric K/Th/U edge, conditioned on low detrended-relief. | A fault juxtaposing subsurface magnetic units without changing surface soil/mineralogy is a buried structure that mapped-surface geology misses. | Low: cached `tc`, `tmi_hg`, `mag_anom`, radiometric `K/Th/U` extensions; no new data. | Mimic: buried nonmagnetic lithologic contact or variable survey terrain clearance (USGS explicitly warns about this). Related to CSPES in the previous preregistration, but tests a *cross-channel residual* rather than cross-scale persistence. |
| H3 — Seismicity-alignment continuation: anisotropic smoothing of `deq_n100a15`/`ieq_n100a15` along the local maximum strain axis, then ridge extraction. | Microseismicity alignments can reveal an active structure with no surface scarp; hidden labels may include such structures. | Low–medium: cached bands only. | Mimic: mining/blast clusters, cultural noise, spatial smoothing artifacts. Not equivalent to any field in `src/gemsw/features.py` (which uses raw distance/intensity bands and isotropic gradient magnitude). |
| H4 — Thermal/conductance pathway contrast: 2 m probe + well/spring temperature anomaly normalized by sample density, intersected with `cond_surf` gradients. | Advective fluid flow on an unmapped fault can produce a subtle shallow thermal anomaly even where topography is blank. | **High, not executable now.** Needs the GDR 1391 2 m probe and well/spring archives (public CC BY 4.0; a small mirror exists in `data/raw/external/`), plus bias modelling; exact AOI coverage and the archive's fitness for use are unverified. | Mimic: groundwater flow, lithologic thermal-conductivity contrasts, solar/climate effects and strongly biased sampling. GEMSDOE30 GDX already explored effort-normalized geothermal data; this would be an extension, not proven novel. |
| H5 — Final-round diversity coverage: allocate a fraction of dots to high-susceptibility pixels **not** covered by any public submission, exploiting Phase-2 expert review. | The organizer confirmed Phase 2 expands labels by reviewing all Phase 1 submissions; novel but plausible structures could be verified and added. | **Not validatable on hide-and-recover**: consensus over other teams' rasters is label-derived and would leak the visible catalogue in this holdout; no organizer receipt for our file. | Mimic: any novel-looking artifact would be reviewed by experts, so false novelty is a real risk. Listed as a research direction, **not** an executable lane. |

## Frozen plan for H1 (single lane)

1. Restore the shared template, cached 19-band feature stack, sample, labels, official external
   layers and a locally rebuilt registry. Reuse `src/gemsw/holdout.py` (the same evaluator as the
   incumbent), `src/gemsw/alloc.py`, `src/gemsw/writer.py` and `src/gemsw/features.py`. No private
   fork of the shared 57GEMSDOE evaluator/writer is created; the GEMSDOE32-derived vendored
   evaluator is used for a **matched** comparison with the incumbent holdout result already in
   `evidence/holdout_results.json`.
2. **Leakage canary**: for each static field used, measure single-field AUC for visible-vs-hidden
   catalogue segments on the same holdout folds. Any AUC > 0.90 stops the lane. Also verify every
   catalogue-derived field is recomputed from `cell.visible_full` only.
3. Build `ρ` per fold from visible-only geometry + static features; normalise its total mass to the
   preregistered 13,000 hidden-truth-equivalent pixels (a modelling scale, **not** a claim about
   the hidden label count). Place binary dots with `A.allocate` (α=0.2, β=0.8, R=3 px), fixed-point
   μ, cap ≤60,000 dots, and mask visible faults pixel-exactly. At most three prespecified
   experiments: (E1) σ=15 px geometric decay, cap 45k; (E2) σ=25 px, cap 45k; (E3) whichever of
   E1/E2 is better, cap 60k. No parameter search beyond these.
4. Holdout = `GEMSDOE32-HIDE-RECOVER-v3.0`, 8 cells (4 quadrants × 2 draws), 1.5 km collar,
   whole connected fault components withheld, pooled TP/FP/FN, 1,000-replicate spatial-cluster
   bootstrap 95 % CI and a **paired** CI against the recomputed champion proxy on identical folds.
   Promotion requires paired Δ lower 95 % bound > 0. Report HOLDOUT-DTI with evaluator version,
   withheld positive count and CI; never present it as a leaderboard score.
5. Uniqueness measured on the pre-placement surface and on final dots against every locally
   restored registry dot mask: |Spearman| ≤0.90 and 3-px directed overlap ≤0.70. **Documented
   interpretation (flagged for user ratification):** “a registry raster's dots” means a discrete
   sparse emission mask (≤15 % of footprint cells). Continuous probability fields and
   space-filling calibration lattices are compared by the rank-correlation test and by overlap
   **excess over a same-count random null**, because their positive support covers essentially the
   whole footprint and the literal support reading makes any nonempty candidate a duplicate
   (proof in [IR-01](review-and-irregularities-2026-10-26.md)). Both readings are reported; the
   literal-strict reading remains blocked.
6. Write the final TIFF pair with the unchanged shared writer, re-read the bytes, validate
   single-band float32 / CRS / shape / transform / finite in-footprint [0,1] / zero on catalogue /
   outside-footprint convention, hash it, and emit one JSON run card. **No weekly slot is
   selected**; a separate selector must read the live quota first.

## Named external sources that would be needed for the unrun hypotheses

- [GDR 1391](https://gdr.openei.org/submissions/1391) — 2 m temperature probes, well/spring
  temperatures, Quaternary faults, slip/dilation tendency, seismicity; public CC BY 4.0
  (verified obtainable from the page; a hash-pinned partial mirror is already in `data/raw/external/`).
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) / [GeoDAWN lidar](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — 1 m bare-earth DEM tiles; free, but tile-level AOI coverage and retrieval inside this sandbox were not verified this session, so no hypothesis here depends on downloading new DEM tiles.
- [USGS ScienceBase GeoDAWN area map](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) — study-area boundary; not needed for H1.

**Irregularities already flagged:** owner-reported historical scores are not organizer receipts;
the mirrored sample is not authenticated as the current official sample; the official
“null/NaN outside bounds” wording conflicts with an all-finite writer; the shared uniqueness tool
is one-sided in ρ; a densely positive registered raster makes the literal overlap rule
unsatisfiable. See [review-and-irregularities-2026-10-26.md](review-and-irregularities-2026-10-26.md).
