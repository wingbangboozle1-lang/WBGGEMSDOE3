# Review lane 8c70511f — 2026-10-27

## Decision and scope

Negative preflight; zero experiments, zero new rasters, zero competition slots.
The prompt supplies no identifiable single method paragraph. This session is an
approval-safety review, not an externally assigned geological lane. The literal
uniqueness stop takes precedence over the demand to keep iterating. No silent
content-aware exception or forced novelty repair is authorized.

The previous top-level SUBMIT decision did not meet the user's stated gates.
`evidence/gemsdoe_run_card.json` retains historical measurements and forecast for
provenance, but its approval is withdrawn. The forecast is not a leaderboard
measurement, nor a defensible out-of-family confidence interval. A fit to related,
owner-reported historical submissions does not establish independent calibration.
AUC below 0.90 is not proof that all leakage is absent.

## Evidence hierarchy and sources

- Organizer reference implementation: https://github.com/drivendataorg/gems-prize-reference-solution
- Official problem/format (link for review, not fetched here): https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Historical byte audit: `evidence/focus_audit.json`. Its pinned source URLs,
  hashes, comparison scope and owner claims are preserved in the executive table.
- Registry witness: https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif
  Saved audit records 5,167,373 positive footprint cells out of 5,167,373. This
  is previously measured evidence, not a raster measurement repeated here.
- `research/REVIEW.md` and `evidence/h6_1_proximity_pruning_holdout.json`
  explain B2's support change and the limitations of causal inference from it.

DrivenData/USGS/Dropbox/NLR are outside the permitted outbound hosts. This is a
network limitation, not proof that those services lack data. Hidden labels,
authenticated receipts, current weekly cap and organizer data provenance are not
available. Current feature caches are absent. GPU training is not established as
necessary: the cached CPU geological methods are a separate workflow.

## Prospective hypotheses — ranked before any implementation

These are provisional mathematical distinctions, not claims of global novelty.
Expected utility is qualitative; no numerical DTI improvement is asserted. All
require registry feasibility first. Cached mirror band names are not authenticated
physical metadata. None is execution-ready until units and upstream processes are
verified. No external-dependent proposal is represented as obtainable here.

| Rank | Layers and physical signature | Off-catalogue rationale | Difference from reviewed implementation; cost | Non-fault mimic and falsification |
|---|---|---|---|---|
| 1 | RTP and gravity anomaly: test *signed cross-edge profile asymmetry* after fitting local planar backgrounds; require the asymmetry direction to persist over multiple along-strike profiles | A buried dipping density/magnetization boundary could produce asymmetric profiles without a surface trace | CSPES tests gradient persistence/collinearity, not background-residual cross-profile asymmetry; peers have dip methods, so novelty is provisional. Medium CPU | Dipping lithologic contact or remanence; symmetric-profile ablation and spatially shifted cross-field control |
| 2 | Detrended elevation and RTP: compare signed horizontal offsets between repeated elevation slope-breaks and magnetic profile edges, conditioning on local valley direction | Consistent displaced subsurface/surface boundaries might detect partly buried fault continuations | Skarpline unions scarp supports; this estimates repeated cross-field offsets. Distinctness from HCE congruence needs full source review. Medium CPU | Erosional valley walls; reject offsets that follow drainage direction or fail leave-one-profile-out replication |
| 3 | Gravity anomaly and depth-to-base surface: compare observed cross-profile curvature with a forward-modelled basin-interface response; rank structured residual breaks rather than either raw gradient | Basement discontinuities beneath smooth cover may lack a catalogue trace | Existing basement-step family uses gradients; proposed residual explicitly subtracts a forward response. High cost, not yet viable because density contrast/units and depth surface independence are unresolved | Interpolation seams and lateral density changes; synthetic seam control and provenance audit before any canary |
| 4 | Magnetic and gravity anomaly grids: local phase reversal of cross-spectral coherence on opposite sides of a persistent boundary | Juxtaposed blocks could alter relative potential-field phase even without an exposed scarp | Different from edge-magnitude concordance and curvature ranks; FFT phase estimator not found in the reviewed lane descriptions, not an exhaustive global novelty claim. Medium/high CPU | Survey stitching or non-fault intrusive contact; acquisition-block controls and phase-randomized null |

The top candidate is **not tested** because the mandatory overlap feasibility
preflight already fails for every nonempty in-footprint support under the saved
witness. Generating an empty TIFF, renaming a prior TIFF, excluding the witness,
or forcing dots away from comparators is not a scientific solution.

## Three passes

1. **Implementation:** traced conflicting approvals to the current renderer and
   proxy finalizer; replaced top-level publication with a fail-closed renderer,
   retained research TIFFs and historical evidence, and disabled the superseded
   proxy approval finalizer. Added explicit promotion gates including released
   artifact equivalence and separate selector approval.
2. **Bug review:** added tests that missing/false/truthy non-boolean gates cannot
   authorize promotion, changed tests that previously required unconditional
   promotion, and kept historical download byte-integrity checks. Existing lane
   pages remain historical lane records, not repository-wide approval.
3. **Requirement recheck:** rebuilt the four pages, checked local links and
   decision consistency, ran the test suite, and inspected the final diff.
   Test execution results are recorded in the PR/session response; hypotheses
   were not implemented, no new holdout result or TIFF is claimed.

## Next eligible work

1. Coordinator must explicitly revise or retain the literal definition of dots
   for dense/lattice controls. Retaining it entails a negative outcome, not more
   experiments. Also assign a single method lane.
2. Restore SHA-pinned shared data; authenticate band semantics and common mask.
3. Fix any shared evaluator discrepancy once in the actual template, not in a
   private metric fork. Compare to organizer reference semantics with fixtures.
4. Only after feasibility, preregister the top candidate and baseline, run each
   feature canary, buffered whole-segment fold-local holdout and paired CI,
   surface plus final registry audit, and saved-byte writer validation. Evaluate
   any uniqueness repair as part of the method in every fold.
5. Publish only if every gate passes; the separate selector checks real weekly
   quota. Record the upload receipt with byte hash for ORGANIZER-CONFIRMED data.

## Executed checks

122 tests passed, 4 cache-dependent tests skipped; 53 upstream rasterio/Affine
deprecation warnings. Site checker and diff whitespace check passed. The existing
research TIFF was reopened and passed finite/range/single-band and local template
CRS/shape/transform checks (`evidence/review_8c70511f_validator.json`).
Organizer reference HEAD observed through GitHub API: `aebe92f7c8a990f0e3443451b7a825d9afd6336b`; this confirms repository identity, not a review of all notebook lines.

The existing PROJECT_PROMPT.md calls itself verbatim but is a prior condensed
standing brief, not the full latest repeated chat text. No claim of exact prompt
transcription is made by this review. Full original requirements remain in chat.
