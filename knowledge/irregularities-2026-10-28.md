
## IR-KHD-01 (2026-10-28, KHD lane): two peer-prompt rasters absent at their pinned commit
The GEMSDOE92 references list hashes that the GEMSDOE33 repo does not serve at the pinned
commit (`gh api` → 404 "No commit found for the ref …"). They may have been force-pushed
away upstream or the pins were always wrong. Disclosed as `status: unavailable_upstream`
in `registry/peer_prompt_2026-10-27.json`; the shared fetcher now records failures and
continues instead of aborting the whole run.

## IR-KHD-02 (2026-10-28): shared knapsack post-guard cascade bug (fixed)
`celf_knapsack_allocate`'s post-guard loop removed dots without recomputing the
victim's relative violation, so with two or more simultaneously-violating comparators it
could delete the entire field (observed: 5,000-dot synthetic candidate → 0). Fixed once in
`src/fchd/registry_full.py`: removals capped at 50% of the selected set per comparator,
residual violation disclosed via `residual_cap_violation` instead of silently nuking.

## IR-KHD-03 (2026-10-28): score-estimate epistemics
(1) The LST projection is in-sample optimistic for candidates allocated against its own
ρ̂ support (B2: model 0.3047 vs owner 0.2778). (2) Owner receipts are not independently
authenticated. (3) The catalogue holdout is anti-correlated with the leaderboard for the
dotted family (documented Spearman −0.146 / −0.849). All headline numbers are labelled
ESTIMATE / HOLDOUT-DTI / OWNER-REPORTED; the only ORGANIZER-CONFIRMED numbers will be
receipts after an authorized submission.

## IR-KHD-04 (2026-10-28): leaderboard snapshots disagree
The brief cites 0.4413 and 0.3195 ("the score we want to beat"); dated registry snapshots
record 0.3195 (rank-1 DARD, 2026-10-03) and 0.4544 (xiaofanhu, 2026-10-27). All are
PUBLIC-LEADERBOARD OBSERVATIONS, none an organizer receipt. Flagged for review; not
resolved in this session.

## IR-KHD-05 (2026-10-28): literal dense-witness reading is unsatisfiable by construction
Re-measured on the emitted KHD raster: the 17GEMSDOE witness is positive on 100% of the
footprint, so the literal "dots within 3 px of one registry raster's dots" test returns
1.0 for EVERY non-empty submission, including the organizers' own sample_submission.tif.
The parallel-run protocol's operative gate is the content-aware one (sparse dot masks
compared directly; dense/lattice masks judged by excess over their own random null); the
literal number is reported alongside it and no longer used as an automatic stop.
