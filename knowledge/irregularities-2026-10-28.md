# Irregularities and corrections — 2026-10-28

This file preserves prior lane findings and explicitly corrects a policy conflict. Historical
lane results do not override the controlling user protocol or the current site-wide release
gate.

## IR-KHD-01: two peer-prompt rasters absent at their pinned commit

The GEMSDOE92 references list hashes that the GEMSDOE33 repository did not serve at the
pinned commit (`gh api` returned 404, “No commit found for the ref …”). They may have been
force-pushed away or the pins may have been wrong. `registry/peer_prompt_2026-10-27.json`
records `status: unavailable_upstream`; the shared fetcher records failures and continues.

## IR-KHD-02: shared knapsack post-guard cascade bug (fixed)

`celf_knapsack_allocate`'s post-guard loop removed dots without recomputing the victim's
relative violation, so multiple simultaneously violating comparators could delete the
entire field (observed in a 5,000-dot synthetic candidate). It was fixed once in
`src/fchd/registry_full.py`: removals are capped at 50% of the selected set per comparator,
and residual violations are disclosed rather than silently deleting all predictions.

## IR-KHD-03: score-estimate epistemics

Prior KHD analyses reported in-sample projections and owner-vs-holdout associations. They
are not score receipts or a validated estimate for a new candidate. Owner-reported values
are unauthenticated; catalogue hide-and-recover results have been reported as anti-correlated
with leaderboard claims for some dotted families. Preserve the evidence class on each
number; do not select a submission from a projection or association.

## IR-KHD-04: leaderboard snapshots disagree

The retained brief cites public values 0.4413 and 0.3195. A saved official-page observation
dated 2026-10-27 records 0.4544 at the top and 0.3195 at rank 25. These are dated
`PUBLIC-LEADERBOARD OBSERVATIONS`, not receipts for project files; the live page was not
rechecked in this review. Do not describe any of them as the current live state without a
fresh authorized fetch.

## IR-KHD-05 correction: content-aware interpretation is not authorized

An earlier KHD note asserted that a content-aware comparison was the “operative gate” and
that the literal dense-witness result should not be an automatic stop. **That assertion is
withdrawn.** It was a lane-level interpretation, not an authorized change to the user's
controlling rule, and it conflicts with `knowledge/protocol.md` and the retained user brief
in `README.md`. There is no dense-raster or content-aware exemption in the current protocol.

The saved mirrored audit reports a registered witness positive on all 5,167,373 cells of
the mirrored sample footprint under its finite-and-positive support definition. Conditional
on those mirror bytes, that grid alignment, and a nonempty candidate whose positive cells
are inside the footprint, directed overlap is 100% even at zero distance. This exceeds the
literal 70% threshold, so the current operational protocol requires recording a duplicate
and stopping. The measurement is against one public owner mirror; it does **not** prove
complete registry coverage or organizer authenticity. It also does not measure any new
candidate: no candidate was generated in the current review. The fresh read-only recheck for this review is
[`evidence/session_c1e656ce_witness_recheck.json`](../evidence/session_c1e656ce_witness_recheck.json); the
[`2026-10-27 report`](../evidence/registry_witness_recheck_2026-10-27.json) remains historical.

The prior content-aware comparisons remain historical research measurements only. They do
not waive the stop or clear any TIFF for download-and-submit use.

## IR-SITE-01: contradictory positive site release (corrected)

The checked-in `docs/data/release_gate.json`, `docs/data/decision.json`, root pages, and
README had been generated from a positive schema-v2 path. They advertised a `SUBMIT`
recommendation even though the run cards recorded no compliant holdout for that candidate,
no literal registry pass, and no separate selector approval. The old `build_site.py` also
returned a successful no-op when that v2 gate existed, while `check_site.py` and current-site
tests enforced the positive state. Historical positive builders could recreate the claim.

The positive publication path is retired. `scripts/build_site.py` now always regenerates a
negative, evidence-bound site; `scripts/check_site.py` and the current-site tests require
`DO-NOT-SUBMIT`; historical positive publishers are blocked before writing. Review also
found a stale `docs/data/khd_release.json` that said `SUBMISSION-READY` despite its negative
lane card and failed literal uniqueness gate. The current site builder replaces it with an
explicit negative archive record. The original lane cards and TIFFs are preserved for
provenance and are not endorsements.

## IR-PROMPT-01: no assigned method paragraph or full authenticated input set

The available brief contains a “single method paragraph” instruction but no identifiable
assigned paragraph. The only tracked raster under `data/` is `template_grid.tif`; the
competition feature stack, labels, sample-submission raster and saved holdout cache are
absent. Hash-pinned GitHub mirrors, if fetched, establish identity with those mirror bytes,
not organizer origin. No experiment or candidate can be claimed until a lane, provenance,
shared cache and evaluator inputs are available and the literal pre-placement stop is
resolved under an authorized protocol.
