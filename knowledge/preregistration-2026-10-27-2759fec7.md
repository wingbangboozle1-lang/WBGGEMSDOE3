# Preregistration — session `arena/2759fec7-wbggemsdoe3`, 2026-10-27 UTC

**Written before any candidate modelling, placement, or holdout run in this session.**
The parallel-run protocol refers to a "single method paragraph below" that was never
supplied; as in prior sessions this records a **proposed, self-assigned lane**, not an
externally assigned one. Only H1 is executed. Budget: 3 experiments / 2 hours wall time.
No submission slot is selected here; no weekly slot is spent.

## Official facts re-verified this session (links for manual review)

| Fact | Source |
|---|---|
| Task = predict **all** faults; public labels are known USGS/INGENIOUS faults; hidden test labels are **newly expert-identified faults**; Phase 2 re-scores against an expanded label set after expert review of all submissions | [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| DTI: triangular 300 m (3 px) kernel, α=0.2, β=0.8; TP uses `max` kernel credit per truth pixel; pooled over all public-test pixels | [metric section](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric), [organizer pooling answer](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2) |
| Known USGS/INGENIOUS fault pixels are **masked / excluded from evaluation** | [organizer answer, 16 Sep](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2) |
| Organizers will not disclose which data or fault types the experts used | [organizer answer, 23 Sep](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/7) |
| Format: one float32 band, EPSG:32611, 100 m, same bounds/transform, [0,1], null/NaN outside bounds | [submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format) |
| ≤3 submissions/week, one selected final GeoTIFF for both rounds, generative-AI disclosure required | [official rules §3.2](https://docs.nlr.gov/docs/fy26osti/96647.pdf) |
| GeoDAWN magnetics image **subsurface** geology/structure; radiometrics image surface materials; variable terrain clearance; CC0 1.0 | [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) |
| INGENIOUS compilation public under CC BY 4.0 | [GDR submission 1391](https://gdr.openei.org/submissions/1391) |
| Band semantics used below (rtp, mag_anom, tmi_hg/vg, iso_grav_anom[_hg/_vg/_slope], det_elev[_slope], depth_to_base_surf, cond_surf, geod_*, deq/ieq) | Re-read 2026-10-27 from `training_features.tif` band tags of the hash-pinned public mirror (byte-identity only, **not** organizer-authenticated) |

## Ranked new geological hypotheses (only H1 is run)

Priority is reasoned judgement about expected **holdout DTI** gain per implementation cost,
not a numerical forecast. Every row names layers, transform, off-catalogue mechanism,
non-fault mimic, and difference from code already in this repository.

| Rank | Hypothesis, layers, signature | Why it could catch an **uncatalogued** fault | Cost / data | Mimic, falsification, prior-art difference |
|---|---|---|---|---|
| **H1 — AMDC (lane)**. **Antisymmetric magnetic-dipole gate on fold-legal tip continuation.** Layers: `rtp`, `mag_anom`, `tmi` (bands 2,1,14), `iso_grav_anom`+`_hg`+`_slope` (13,18,5), `det_elev`+`_slope` (12,19), `depth_to_base_surf` (15), `cond_surf` (17), `geod_2ndinv` (4), `ieq_n100a15` (16); fold-local visible-catalogue geometry (connected-component PCA strike, 25 px endpoint corridors, exp(−d/15 px) annulus). Transform: rank-bin naive-Bayes susceptibility fitted on **visible faults only** × geometric continuation prior × **odd-symmetric perpendicular RTP step test** evaluated along each corridor's own strike, then greedy DTI-optimal dot placement with the exact kernel. The NB uses exactly 10 fields: `rtp`, `mag_anom`, `iso_grav_anom`, `iso_grav_anom_hg`, `iso_grav_anom_slope`, `det_elev_slope`, `depth_to_base_surf`, `cond_surf`, `geod_2ndinv`, `ieq_n100a15` (raw `tmi`/`det_elev` excluded as redundant). | A small-offset buried fault steps magnetic basement: RTP shows an **antisymmetric pair** (high one side, low the other), not a symmetric ridge. Such a fault has no surface scarp, so it is missing from the mapped catalogue, yet its continuation corridor is predictable from visible tips. All prior lanes use **symmetric** detectors (gradient magnitude, tilt magnitude, curvature magnitude, cross-channel agreement) that fire equally on ridges, dikes, and contacts; the signed odd test is blind to symmetric ridges and selective for steps. | Medium CPU; **no new external data** — all bands are in the template's cached 19-band stack restored 2026-10-27. | **Mimic:** a dipping lithologic contact also produces a magnetic step. Suppressed by (a) requiring along-strike corridor continuity from a visible fault tip, (b) co-located gravity-step support, (c) thin-cover stratification (thick cover mutes basement steps). Falsified by a canary failure or a holdout loss vs the matched champion. Differs from SGCE (`src/gemsw/sgce.py`: isotropic annulus + PCA corridors + **strain** gate, no signed test), HCE-1 (cross-channel **agreement**/congruence), THCS-OOF (HGB on raw bands + CELF), CSPES (cross-scale persistence), skarpline (curvature-magnitude ridges). The geometric prior is the same family as SGCE's, rebuilt fold-locally; the dipole gate is new. |
| H2 — Demagnetization-deficit detector. Layers: `iso_grav_anom_hg`, `tmi_hg`, `cond_surf`, `depth_to_base_surf`. Transform: rank(grav_hg) − rank(tmi_hg) conditioned on thin cover and a conductivity crest. | Hydrothermal alteration along a permeable fault destroys magnetite: the gravity step persists while the magnetic edge is muted. Mapped scarps show both edges; an altered blind fault shows the deficit. | Low CPU; cached bands only. | Mimic: thick conductive cover mutes magnetics generally → cover stratification + SGMC-distance audit. Differs from every congruence method (which reward channel **agreement**); this rewards calibrated **disagreement**. Not run (budget). |
| H3 — Anisotropic microseismic ridge. Layers: `ieq_n100a15`, `deq_n100a15`, `geod_shearrate`, `geod_dilaterate`. Transform: structure-tensor-guided smoothing of seismicity density along the local maximum-strain axis, then ridge NMS. | Microseismic lineaments mark active structures with no surface scarp; hidden labels may include them. | Low–medium CPU; cached bands only. | Mimic: mine blasts, mislocated clusters. Differs from LBCAL and GEMSDOE33-s33 raw-field use (isotropic, unconditioned). Not run (budget). |
| H4 — Transverse topographic antisymmetry. Layers: `det_elev`, `det_elev_slope`. Transform: odd-profile (antisymmetric) elevation residual across candidate NNE/N-S strikes; suppress even (ridge) energy. | Fault-offset drainages and fold limbs produce antisymmetric transverse profiles that curvature-magnitude ridges miss. | Medium CPU; cached bands only. | Mimic: shorelines, terraces, roads, fan edges → TIGER road-distance audit. Differs from skarpline (curvature **magnitude** + NMS). Not run (budget). |
| H5 — Sub-cover conductivity stringer anchored to a basement gravity step. Layers: `cond_surf`, `depth_to_base_surf`, `iso_grav_anom_hg`. Transform: narrow conductivity crest × thick-cover mask × gravity-step support. | A blind conduit under alluvium expresses as a conductivity stringer with no scarp. | Medium–high CPU; validation of the hydrothermal interpretation needs GDR 1391 2 m-probe/well archives (public CC BY 4.0; sandbox byte-level fetch **not verified**) → **not viable as a validated lane now**. Mimic: saline aquifers, clay lenses. Related to THCS geothermal block; extension, not proven novelty. Not run. |

## Frozen plan for H1 (AMDC, single lane)

1. **Reuse, don't rebuild.** Grid/flags from the pinned shared template (`vendor/gems57/grid.py`,
   commit `822a0ce5`); cached 19-band stack (`.cache/57GEMSDOE-*/.cache/features/`);
   holdout `vendor/gems57/holdout.py`; scoring/CI `vendor/gems57/evaluate_holdout.py`;
   placement `vendor/gems57/emit.py`; writer `vendor/gems57/submission_writer.py`;
   validators `vendor/gems57/validate.py` + `gates.format_report`. No private fork: any shared-tool
   defect is fixed in `vendor/` once and reported, otherwise the tool is used as-is.
2. **Holdout (hide-and-recover):** `holdout.build_holdout(grid, modes=("all",), seeds=(20,21))` →
   8 cells (4 quadrants × 2 draws), whole fault segments (≤12 px chunks) withheld at 20%,
   1.2 km boundary erosion, segments wholly inside the scored domain only, every
   catalogue-derived feature from `ctx.visible(key)` only, visible faults masked pixel-exactly,
   pooled DTI α=0.2 β=0.8 R=3 px. 95% CI + paired Δ CI by `evaluate_holdout.pooled_summary`
   (paired physical spatial-cluster percentile bootstrap, ≥1000 draws). Evaluator version
   `gems57-pooled-hide-v2` is recorded on every number.
3. **Matched ranking (learning only):** the 9 focus-site rasters and every repo-shipped TIF are
   scored as **fixed emissions** on the identical 8 cells (truth withheld, visible masked).
   Fixed historical emissions may contain dots on withheld segments (built from the full
   catalogue); they are reference points, not fold-legal competitors. Our fold-legal candidate
   beating them is therefore the stronger result. No historical raster is copied as a submission.
4. **Leakage canary (before trusting any result):** per static field, pooled AUC of
   withheld-truth pixels vs active background over the 8 cells. Any max(AUC, 1−AUC) > 0.90
   stops the lane. Static geophysical fields take no catalogue input by construction; the
   canary is still run per protocol.
5. **Three prespecified experiments:** (E1) dipole gate τ = footprint median (permissive),
   cap 45k; (E2) τ = upper tertile (strict), cap 45k; (E3) winner of E1/E2 at cap 60k.
   Modelling scale mass = 13,000 (same convention as SGCE for comparability; a scale, **not**
   a claim about hidden label count). Dots excluded within 2.01 px of visible faults
   (masked/near-masked zone) and on visible faults pixel-exactly.
6. **Uniqueness (surface before placement AND final dots):** |Spearman| ≤ 0.90 and ≤70% of
   dots within 3 px of any one registry raster's dots. Registry scope = 9 pinned focus
   rasters + every TIF already shipped in this repo (`docs/`, `submission/`, `archive/`) +
   the spacing-5 lattice control + the 17GEMSDOE dense control (fetched best-effort; if
   unfetchable, the scope gap is disclosed, not silently dropped). The 118-raster owner
   ledger is attempted best-effort within budget; whatever is not fetched is disclosed as a
   scope limit. Dense 100%-support controls are reported under both the literal reading and
   a content-aware (null-excess) reading, flagged for ratification, exactly as prior lanes did.
7. **Validator on saved bytes:** single float32 band, EPSG:32611, 3730×3292, exact transform,
   all-finite, values in [0,1] (the portal "[0,1]" guard), zero positive pixels on the mapped
   catalogue, zero NaN inside the footprint, single-TIFF ZIP round-trip. Both zeros-mode
   (primary) and the writer's contract are checked; NaN-outside variants are diagnostics only.
8. **Promotion rule (all required):** canary PASS; paired HOLDOUT-DTI Δ lower 95% bound > 0
   vs the focus-32 B2 fixed-emission champion on identical cells; uniqueness PASS under the
   content-aware reading with the literal reading disclosed; validator PASS on saved bytes.
   Otherwise verdict `negative` (a deliverable). A projection is labelled PROJECTION with
   method + interval and is never written as a score.
9. **Projection (not a score):** ordinary least-squares fit of owner-reported score on
   matched holdout DTI over the 9 focus rasters (reported R² + leave-one-out MAE); the
   candidate's projection = fit(candidate holdout) with the LOOCV interval. Owner reports are
   unverified (no receipts); the projection inherits that weakness and is labelled as such.

## Registry / uniqueness contract note

The literal positive-support reading is unsatisfiable against a dense 100%-support control
(any nonempty candidate has 100% forward overlap) — the standing IR-01 conflict. This lane
checks both readings, promotes only on the content-aware PASS, and flags the literal reading
for user ratification. No threshold is silently changed.
