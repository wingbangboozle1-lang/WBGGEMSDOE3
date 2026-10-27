# What can explain the reported GEMSDOE32 B2 result?

**Owner-reported historical claim, not organizer-confirmed:** 0.2778 for the pinned
GEMSDOE32 H33 B2 file. We did not obtain a DrivenData receipt linking this score to
these bytes or the hidden labels, so neither the value nor its causal explanation can
be independently verified. Its upstream repository has advanced since the pinned file
was selected; this is not a verified current ranking.

## What the rasters establish

The B2 positive support has 37,654 cells and is an exact subset of the 40,199 positive
cells in the pinned GEMSDOE28 H27-4 base: 2,545 cells were removed and none added.
Those removed cells lie 1.414–2 pixels from the mirrored fault catalogue; the nearest
retained cell is 2.236 pixels away. The decoded masks, grid and hashes were checked in
[evidence/focus_audit.json](../evidence/focus_audit.json). This describes a placement
change, not an identified improvement in geology or score.

The [official metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
uses pooled, distance-tolerant Tversky with α=0.2, β=0.8 and a 300 m triangular
kernel. Thinning can reduce redundant prediction mass; deleting predictions can reduce
false-positive mass but can also lose true-positive credit. Which effect dominates
requires the unavailable hidden labels and exact evaluated bytes. There is no defensible
numeric break-even density or causal decomposition from these artifacts alone.
[Staff clarify](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516)
that **known-fault pixels** are excluded in both rounds; that does not imply all
neighboring pixels are excluded. The B2 removal is near the catalogue, not necessarily
on excluded pixels.

## Can a new TIF beat it?

Unknown. Another participant's higher public leaderboard result is evidence that a
higher competition score exists, not that a new file from this project will achieve it.
This session produced no candidate or valid local holdout estimate. The literal
registry definition stops every nonempty in-footprint candidate because a registered
soft raster is positive throughout the footprint; do not submit or silently exempt it.
See the [current dashboard](../docs/index.html) and [negative card](../evidence/run_card.json).
