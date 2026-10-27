# Historical hypothesis slate — not current score estimates

The following slate was preregistered on 2026-10-26, before its historical LST1 work. Any “expected gain” below is only a speculative planning prior from that older document; it is **not** a score, a current leaderboard estimate, or a result. The registry witness now blocks every nonempty in-footprint candidate under the literal rule. No new experiment was run during this review, and none of these hypotheses authorizes bypassing that stop.

The user-specified study set is GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, and 36. Prior work was inspected through pinned public repositories/mirrors; those hashes establish local byte identity, not organizer provenance. Novelty is not established merely by this repository review.

| Historical rank | Hypothesis | Layers / proposed mechanism | Off-catalogue rationale | Main confounder | Novelty vs. repo | Cost / external data | Status |
|---|---|---|---|---|---|---|---|
| 1 | W1 — ledger-supervised density tomography | 19 training bands, lidar and derived terrain/geophysical fields; fit a density model from historical raster/score associations, then allocate dots | Could rank uncatalogued-fault locations if independent submission patterns identify signal beyond the catalogue | Score/raster claims are unreceipted, submission lineages are correlated, and the old holdout/evaluator is not the current shared protocol | Overlaps with GEMSDOE28/27 tomography and GEMSDOE32 LLI; old LST1 added more fields and nested CV, but novelty and generalization are unproven | Medium; historical mirror data only | Historical run; negative under legacy evaluator; not current validation |
| 2 | W2 — residual gap-fill quota | Reallocate a preregistered share to high model-density areas lacking a nearby H19-5 network dot | Attempts to find off-network faults using residual model signal | Inherits W1 leakage, lineage, and calibration limitations | Related to W1 quota arm and GEMSDOE27 annulus allocation | Low; no new external data | Not separately validated under current protocol |
| 3 | W3 — metre-scale scarp matched filter | 3DEP 1 m elevation / profile curvature and scarp cross-section filters | Fault scarps may be visible in fine-scale terrain but absent from the training catalogue | Erosion, roads, lithology, and the fact that not every labelled fault has a surface scarp | Similar ideas appear in sibling notes; no novelty claim | High; requires official tiles and substantial storage | Not run; source availability/provenance must be rechecked |
| 4 | W4 — InSAR velocity steps | Sentinel-1 / OPERA line-of-sight velocity discontinuities | Active deformation may expose uncatalogued structures | Arid basin may be slowly deforming; atmospheric and processing artifacts | Prior sibling notes mention related data; novelty unclear | High; NASA ASF/Earthdata access and preprocessing | Not run; access not verified in this review |
| 5 | W5 — newer-vintage fault mapping | Compare current USGS Quaternary fault mapping with training catalogue | Newly mapped traces might add off-catalogue geometry | Catalogue changes may reflect terminology or source updates, not new truth | Related sibling variants exist; novelty unclear | Medium; official source and dates must be checked | Not run; source availability/provenance must be rechecked |

## Historical W1 record — explicitly not current-protocol evidence

The archived LST1 artifacts contain a spatially blocked **HOLDOUT-DTI** analysis under evaluator `GEMSDOE32-HIDE-RECOVER-v3.0`, with 22,232 withheld positives. For example, `lst_mod_quota` candidate pooled DTI is 0.06668 (95% CI 0.05688–0.07655); its champion proxy is 0.09920 (95% CI 0.08595–0.11267); paired delta −0.03252 (95% CI −0.04103 to −0.02372). These are historical metrics only: the evaluator differs from the prescribed `gems57-pooled-hide-v2`, the old construction exceeds the experiment budget, and no result establishes a leaderboard score.

The old run card's ledger projection is quarantined as **NOT_A_SCORE**. Its historical “unique” status used a lattice-null exception and is superseded: the literal rule fails. Do not interpret “delivered,” “unique,” or `ready_to_submit` from older documents as current approval.

## Gate before any future test

1. A protocol owner must clarify the registry rule's treatment of dense/continuous rasters and the universal witness. No support mask, threshold, registry scope, or exception may be changed silently.
2. Only after that stop is explicitly resolved may an authorized lane run single-feature leakage canaries (AUC >0.90 is leakage until disproved), whole-segment buffered holdout tests, and the shared `gems57-pooled-hide-v2` evaluator/writer.
3. Report performance only as `HOLDOUT-DTI` with evaluator version, withheld-positive count and 95% CI, or `ORGANIZER-CONFIRMED` with a submission receipt. Use a separate selector for any real slot.

## Official source pointers

These links were retained from earlier research and were **not fetched during the current review**. Recheck them before planning data acquisition:

- USGS 3DEP: https://www.usgs.gov/3d-elevation-program
- DrivenData competition and data page: https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- NASA ASF: https://asf.alaska.edu/
- USGS Quaternary Fault and Fold Database: https://www.usgs.gov/programs/earthquake-hazards/faults
