# Three-pass review — 2026-10-26

## Pass 1 — implementation and measured results

* Inspected the starting checkout: only README.md; no existing model pipeline.
* Retrieved nine GitHub source inventories and source pages plus the organizer reference README/notebook. Stored source pins and SHA-256 receipts.
* Restored 12 comparison inputs from commit-pinned mirrors with SHA-256 validation; kept the TIFFs out of Git.
* Independently computed all directed focus-nine pairwise overlaps and binary Spearman correlations, exact support identities, catalogue-distance pruning identity and lattice coverage bound.
* Preserved seven shared instruments byte-for-byte, with checksum tests. No shared tool was privately modified.
* Built the static site, executive guide, research review, four prospective hypotheses, evidence downloads and negative run card.
* No model experiment, candidate-generation step, holdout performance estimate, live-slot selection or upload was executed.

## Pass 2 — bugs, assumptions and edge cases

* Added an outside-footprint numeric range check. An outside sentinel such as -9999 must not pass merely because the footprint is in range; NaN-outside and zero-outside are distinguished rather than equated.
* Added rejection of invalid template metadata/empty footprint, grid mismatch, NaN/Inf inside and out-of-range values.
* Tested the strict >70% boundary: equality does not trigger the bound. Tested the first forced budget and its predecessor.
* Corrected a test's initial assumption that the shared metric returns a scalar: it returns a dictionary. The shared implementation was not changed.
* Distinguished identical spatial support from identical TIFF bytes. Do not call the final binary-raster correlation a pre-placement surface correlation.
* Source freshness records drift (including GEMSDOE31) without silently refreshing the scientific snapshot. No claim is made to have a live leaderboard feed.
* Identified shared-template ambiguity, source-authentication limitations, missing lane, missing feature cache, missing matched baseline, missing score receipts and the controls-exemption irregularity in peer reports.

## Pass 3 — requirement reconciliation and final verification

* 20 tests pass locally: synthetic validator adversarial cases, strict threshold bounds, whole-component hiding/training purging smoke test, pinned shared bytes, source hashes, negative decision, local HTML links and deterministic site regeneration.
* Repeated the full pinned-raster audit successfully. Running format preflight on GEMSDOE32 reports valid numeric range/grid but explicitly keeps `ok_to_submit=false`.
* Git whitespace check passes for authored changes. Raw source snapshots and unmodified vendor files retain upstream content, including upstream formatting.
* GitHub CI is configured to rerun the tests, rebuild the site, restore the historical inputs and reproduce audit JSON. A daily/manual freshness workflow uploads a report artifact without changing branches or scientific evidence.
* The existing Pages configuration is main/root. A root redirect and no-Jekyll marker route users to the static site after merge.
* The README records a normalized operational copy of the current prompt, not a falsely claimed verbatim transcript. Original historical peer wording is retained in source snapshots with provenance.

## Explicit unmet requirements — no false completion claim

A genuinely new high-scoring, validated TIFF is **not delivered**. No HOLDOUT-DTI or calibrated leaderboard estimate is available for a new candidate. The top prospective geological hypothesis was not executed because the lane is unspecified, inputs/baseline are not restored/authenticated and the standard-budget literal uniqueness bound already fails. This does not prove every scientifically meaningful lower-budget candidate is impossible.

Not all original external sources or prior submissions were independently reviewed. Only GitHub-hosted official reference code and peer artifacts were reachable; the nine historical audit rasters are a subset of the full evolving registry. Organizer score receipts, live cap, official data licenses and portal acceptance remain unverified.

The next session should resolve these preconditions before further model work. Do not silently weaken the rule, choose uncovered lattice pixels to evade it, regenerate a known baseline or spend a submission slot to test an invalid candidate.

## Concurrent-main integration recheck

Main advanced to `35d7ccf` during PR creation. Merged it into the session branch,
retained its evidence and full pinned 57GEMSDOE package, and preserved its audit
APIs under `scripts/audit_preflight.py` plus 18 active tests. Conflicting historical
site/build files were archived, not silently discarded. Explicit pytest testpaths
exclude historical archive test copies from active discovery. The integrated suite
passes **38 tests**. Template-family ambiguity remains a blocker to scientific
execution; no attempt was made to merge their metric definitions or change bytes.

## Deployment follow-up

After merge, both the legacy Pages publisher (main/root) and an inherited custom
workflow published successfully, but the latter uploaded only docs/ to the root.
That creates a race between two different URL layouts. Removed the competing
custom publisher (historical YAML archived) and retained the confirmed existing
legacy configuration, root redirect and stable /docs/ URLs. Other CI and source
freshness workflows remain active. Both integrated CI checks passed after PR #4.
