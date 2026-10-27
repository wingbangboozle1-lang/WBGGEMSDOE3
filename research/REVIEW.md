> **Historical 2026-10-26 review; superseded where inconsistent with the 2026-10-27 audit.** The official source descriptions were subsequently accessible via a research page fetch; full official competition data remain login-walled. See [current review](../knowledge/review-and-irregularities-2026-10-26.md) and [run card](../evidence/run_card.json).

# Executive research review — 2026-10-26

## Decision: negative; no new submission authorized

This repository started at `891b84e` with only a 13-byte README. There was no prior pipeline, feature cache, experiment, or local next-step implementation to continue. The supplied statement that data placement is the only blocker does not describe this checkout. No geological experiment was run and no weekly slot was used. The requested high-scoring, unique downloadable TIFF has **not** been produced. Generating random pixels, perturbing an old TIFF, or renaming it would not meet the brief.

The single-method paragraph is missing from the supplied parallel-run protocol. This session therefore performed read-only comparison and infrastructure work, not an invented geological lane. The experiment budget remains zero of three; the two-hour limit also applies to future execution.

## What we actually verified

`python scripts/restore_comparators.py` restores nine historical leaders, a sample grid, a fault catalogue, and a registered lattice from commit-pinned GitHub owner mirrors. Every byte stream is SHA-256 checked. These are **not independently organizer-authenticated data**. `python scripts/audit.py` independently computes the results in `docs/audit.json`.

* All nine historical leaders fail the literal final-dot uniqueness rule against at least one of the other eight. Format-valid does not mean unique or eligible.
* GEMSDOE25 and GEMSDOE30 have identical positive-pixel support. Different GeoTIFF bytes do not establish scientific novelty.
* GEMSDOE32's B2 support is exactly GEMSDOE25's D2.8 support with 6,436 dots removed and none added. The removed dots are exactly those at Euclidean catalogue distance at most two pixels. This is a verified raster identity, not a geological interpretation.
* The registered five-pixel lattice covers 5,160,724 of 5,167,373 footprint pixels within three pixels, leaving 6,649 uncovered. For any 37,654 distinct dots, at least 31,005 must overlap: 82.34185%, beyond the strict 70% limit. This is a combinatorial lower bound, **not** a measured candidate overlap or a DTI score. It forces failure at budgets of 22,164 or more. Smaller budgets are not automatically unique and must not be chosen simply to game the registry.
* Pre-placement continuous surfaces were not reconstructed. Historical binary-raster Spearman values are explicitly final-output measurements, not surface checks. The audit is a pinned historical subset, not an exhaustive inventory of every present-day submission.

## Why the reported GEMSDOE32 result might improve

The claimed leaderboard values in the user brief are quarantined as unverified historical claims; no submission-page receipt was retrieved. In particular, the asserted GEMSDOE32 value is not labelled ORGANIZER-CONFIRMED. The user also supplied incompatible current leaderboard highs, which cannot be resolved from these rasters.

The exact support identity above supports a **placement explanation**, not evidence of new fault discovery: catalogue-near pruning can reduce false-positive mass in an asymmetric distance-tolerant metric while preserving coverage of hidden faults. It can also remove genuine nearby new faults. Sparse dots may avoid redundant predicted mass, but this trade-off depends on the hidden truth and the organizer's precise metric implementation. Neither the removal identity nor a filename proves causality for the claimed improvement. A model named “PINN” is not evidence of physics validation.

The organizer reference notebook documents fault detection, a U-Net, and Tversky training loss with false-positive weight 0.2 and false-negative weight 0.8. It does **not** establish that its random-patch validation is the requested buffered hide-and-recover evaluator, nor calibrate leaderboard forecasts. See the pinned notebook under `research/sources/gems-prize-reference-solution/` and its GitHub source in `docs/sources.json`.

The relevant target is unlabelled **fault geometry**, not direct geothermal-vent classification. A physically plausible geothermal indicator may be an excellent process proxy and still be a poor fault-location predictor. Basin fill, lithologic boundaries, dikes, alluvial channels, and survey processing can all mimic useful-looking structure.

## Four prospective hypotheses, ranked before implementation

Ranking is qualitative expected utility relative to cost, **not a projected DTI gain**. None is implemented in this initially empty repository; uniqueness across all external projects is not established. The reviewed source-tree inventories already contain many magnetic, radiometric, drainage, curvature, and contact experiments. These ideas must be compared with their full implementations before assignment, not declared globally novel from titles.

| Rank / hypothesis | Specific layers and physical signature | Why an uncatalogued fault could be detected | Named confounder; test that could reject it | Cost / viability |
|---|---|---|---|---|
| 1. Cross-scale displacement of radiometric domains | GeoDAWN potassium, thorium and uranium grids plus magnetic RTP; oriented cross-correlation of radiometric texture on opposing sides of a persistent magnetic edge, looking for coherent lateral offsets rather than simple gradient coincidence | Offset shallow material domains could expose a concealed continuation without requiring proximity to a mapped trace | Fluvial sorting, alluvial fan boundaries and lithologic contacts; require offset consistency across independent radioelements and spatial scales, and compare a zero-offset ablation | Medium. Owner manifests contain radiometric products, but quantized caches may erase offsets. Raw official data access and resolution must be confirmed. Not execution-ready here. |
| 2. Curvature change under sediment cover | GeoDAWN RTP and upward-continued magnetic grids; signed edge-location migration across continuation heights, conditioned on elevation-derived basin margins | A dipping buried interface could migrate laterally with effective observation height even where no topographic scarp is mapped | Dipping non-fault lithologic contact or remanent magnetization; compare to a fixed-edge model and stratify by magnetic amplitude | Medium. Similar dip-projection and depth experiments exist in peers; distinguish mathematically before claiming novelty. Mirror data manifest available, cache not restored. |
| 3. Repeated stratigraphic displacement across independent drainages | USGS 3DEP elevation, slope and drainage profiles; detect consistent elevation/knickpoint offsets across multiple separate catchments, rejecting points explained by local channel convergence | A buried or eroded fault could produce repeated disequilibrium rather than one conspicuous scarp | Resistant beds, lake shorelines and base-level changes; leave-one-catchment-out ablations and lithology controls | High. Peer drainage/knickpoint lanes exist. Official DEM coverage and download access not verified here; not viable for execution yet. |
| 4. Profile-domain magnetic reproducibility | USGS GeoDAWN original flight and tie-line magnetic observations; require an anomaly to recur at intersecting tracks after height correction instead of trusting grid streaks | Buried fault-related contrasts can exist beneath smooth topography and beyond the existing catalogue | Dike swarms, magnetic lithologic contacts, acquisition striping; cross-track replication and track-direction negative controls | High. A GEMSDOE36 preflight already proposes this family, so do not select it as a new parallel lane. Raw profile archives were not retrieved. |

Official source candidates: [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [ScienceBase record cited by peer](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7), [USGS 3DEP](https://www.usgs.gov/3d-elevation-program). These hosts are outside this session's outbound allowlist. Therefore their present availability, licenses, band metadata, and spatial coverage were **not independently verified** and no external-data-dependent idea is marked viable. Do not confuse a source URL with a successful data-access check.

## Validation design for the next eligible lane

1. Resolve the missing lane and shared-template identity. Peers name both GEMSDOE24 and 57GEMSDOE. This repo preserves the seven GEMSDOE24 instrument files byte-for-byte with pins; it does not maintain a private evaluator. The upstream `evaluate_holdout.py` is a hypothesis-specific orchestration script, not a generic training entry point. Do not run it as though it evaluates a new method.
2. Restore and authenticate a cached feature stack with band names, units, transforms and provenance. Never use the sample prediction values or historical predictions as geological features. The mirror manifest says `labels.tif` and `existing_faults.tif` have the same hash; they are not independent test labels.
3. Freeze the full literal registry including controls. Run necessary placement-feasibility bounds before building a surface. No silent lattice exemptions and no adversarial placement to evade overlap.
4. Preregister one candidate and a matched baseline. Hide whole fault components/segments with a spatial buffer; rebuild every catalogue-derived feature using only visible faults. Mask visible faults pixel-exactly in scoring. Audit components crossing block boundaries and valid no-data edges.
5. Test each source and transformed feature alone. AUC above 0.90 stops the experiment until leakage is disproved. Preserve failure reports.
6. Check the pre-placement surface against every registered raster, then evaluate out-of-fold predictions using shared pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). Report evaluator identity, withheld-positive count and spatial/block bootstrap 95% CI. Reconstruct the current-best method out-of-fold with the same split; a full-catalogue historical TIFF is not a valid baseline.
7. Promotion requires a positive paired improvement with uncertainty, not simply a point estimate. Check final-dot correlations and three-pixel overlap against the full registry before export. Stop at a duplicate.
8. Reuse the shared writer; reject malformed inputs before its sanitization, reopen saved bytes, verify values, footprint, CRS/shape/transform, hash and note length. Inspect the official outside-footprint convention before selecting zero or NaN packaging. The user-reported range error is consistent with invalid/sentinel values, but its cause cannot be proven without the rejected file.
9. A separate selector must check current submission cap and remaining slots. No automatic upload or slot selection occurs in this repository. Missing evidence means DO NOT SUBMIT, not human inspection required.

## Source hierarchy and limitations

Official organizer code is authoritative for what that code implements. Peer repositories are evidence of their own code/artifacts, not official score receipts or literature. Hashes establish identity, not authenticity or data licenses. DrivenData, Dropbox, USGS, NLR and GDR are outside the allowed network hosts here; no claim is made that their links were fetched or that their data are unobtainable elsewhere. GitHub access is working.

No honest leaderboard estimate can currently be assigned. Cross-site owner scores are a biased, repeated family of placements and lack verified upload-to-byte mappings. A regression on them would not create a validated forecast. Do not claim the requested leaderboard target is attainable from the existing evidence.

## Core values applied

**Maximize P(Win):** protect scarce slots, demand scientific incremental value, and publish negative results instead of chasing optimistic projections. **Own the Outcome:** resolve missing infrastructure, automate exact checks, retain evidence and state blockers explicitly. These values do not override competition rules or statistical validity.
