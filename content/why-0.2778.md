# GEMSDOE32 B2: what the raster evidence does — and does not — establish

> **Evidence status:** the reported `0.2778` B2 value is an unverified user/owner-reported claim. No organizer receipt, submission identifier, or authenticated SHA-256 ties that value to a particular uploaded file. It is not an organizer-confirmed score and is not used as a current leaderboard value or estimate.
>
> The public-feed snapshot last recorded on 2026-10-26 is stale for the 2026-10-27 review. No fresh, attributable public observation was obtained here, so no leaderboard values are reconciled or inferred.

## What the local raster comparison shows

The pinned H33 B2 raster's decoded positive support is a subset of the H27-4 reference: the comparison shows pixels removed and no pixels added. This is consistent with a pruning operation. It does **not** establish that the uploaded B2 bytes were identical, that the reported score came from those bytes, or that pruning caused a score change. Those links require a submission receipt or another authenticated record.

The nested score sequence historically written in sibling-repository files is owner-reported only. Treat its rows as claims to investigate, not as confirmed organizer measurements. No row is a validated causal experiment because the exact uploaded bytes and receipts are absent.

## Metric intuition (historical analysis, not a score prediction)

The repository's archived analysis uses the official competition metric link (not re-fetched during this review): a distance-weighted Tversky index with a 300 m triangular kernel, `alpha=0.2`, and `beta=0.8`. For binary predicted dots, if `N` is the number of emitted dots, `M` the summed nearby-truth kernel credit, `TPw` the credited positive mass, and `|G|` the positive truth count, the archived derivation writes:

`DTI = TPw / [0.2 (TPw + N - M) + 0.8 |G|]`.

This algebra explains a **possible mechanism**: removing redundant or low-credit dots can reduce the penalty term while retaining much of the credit. It does not identify why an unreceipted score was obtained, nor does it predict a score for a new raster.

## What the repository's historical analysis found

- Historical sibling files and feature caches were mirrored and hash-checked locally; that establishes byte consistency with those mirrors, not organizer provenance.
- Archived comparisons indicate that several rasters differ through pruning and that independent-looking methods exist. Their reported leaderboard scores are not receipt-confirmed.
- The old LST1 holdout used `GEMSDOE32-HIDE-RECOVER-v3.0`, not the prescribed shared `gems57-pooled-hide-v2`. Its HOLDOUT-DTI values are historical diagnostics only and are not a current-protocol validation.
- The old ledger-model output is explicitly `NOT_A_SCORE`. Its calibration was method-dependent, so its former projection range has been removed from current-facing summaries and must not be treated as a leaderboard estimate.

## Can a distinct method improve the result?

**Unknown / not estimable from the available evidence.** The B2 bytes document a pruning operation, not a score-causal mechanism; no distinct method has been validated under the current shared evaluator. The current registry witness triggers the binding literal duplicate stop for every nonempty in-footprint candidate, so this repository did not run another experiment or create another TIFF. The preregistered hypotheses remain research ideas, not performance claims.

A new score estimate requires a validated, spatially blocked HOLDOUT-DTI result under the correct evaluator, with withheld-positive count and 95% CI. An organizer-confirmed score requires an authenticated submission receipt. Neither exists for a new candidate here.

## Links retained for verification

- [Official metric and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — link retained in the repository; not fetched during the current review.
- [Competition leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — requires a fresh timestamped observation before using any values.
- [Scoring clarification forum thread](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516) — retained as a source pointer, not re-fetched in this review.
