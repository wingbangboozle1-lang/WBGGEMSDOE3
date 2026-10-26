# Three-pass implementation review — 2026-10-26 UTC

This is an engineering/data audit, not a model experiment or a competition score.

## Pass 1 — implement and measure

- Discovered that this checkout contained only the initial README; reviewed all nine priority sites and authoritative competition, USGS and DOE sources.
- Restored the hash-pinned owner-mirrored raw feature raster, catalogue and grid; restored the shared evaluator and writer unchanged to an ignored cache. No cached feature arrays or official-authenticated copies were found.
- Re-read nine historic rasters, the purportedly approved GEMSDOE27 candidate, and a registry witness. Calculated the B2 lineage, pairwise directional proximity and the pre-placement counting bound. Wrote the negative JSON run card without generating a raster.
- Built a GitHub Pages dashboard, executive submission guide, source inventory, conservative on-disk validator, deterministic input restoration and a public-feed refresh script.

## Pass 2 — adversarial review and fixes

- Confirmed the exact registry manifest includes the witness, rather than inferring membership from the file name. Checked hashes and the inclusive Euclidean 3-pixel disk.
- Confirmed the mirrored sample's positive pixels equal known labels. Restricted it to grid/mask use in all scientific code.
- Corrected the submission guide: the portal excerpt supplies a file field and optional note, not an independently verified name field; use a unique filename.
- Hardened validation to reject external dataset sidecars, a non-GeoTIFF driver, a wrong template, a changed-on-disk artifact, out-of-range / nonfinite values and mask mismatches. A format failure under this stricter local policy is not asserted to be a portal rejection.
- Added multipart hash-failure/atomic-write, stale-feed, redirect-security, rank-correlation, boundary, masked-nodata, sidecar and bad-range tests.

## Pass 3 — cross-check original request

- No TIFF, canary or holdout DTI is claimed after the literal duplicate stop. The user's mandatory unique high-scoring TIFF and trained model therefore remain **not delivered**; inventing a result or exempting the lattice would violate the same prompt's stop rule.
- Each historical figure is identified as a user/owner claim without a score receipt. The public leaderboard feed has a timestamp and remains stale if refresh fails. It never controls a submission gate.
- Checked that the nine-site table has a reference file, reported claim, unknown leaderboard estimate, measured uniqueness failure and explicit no-submit status. The historical files are for educational/audit use only.
- Exercised desktop and mobile Pages rendering, site filter, public-feed display, internal links and responsive width. Confirmed the preview serves an assembled static directory, not `.git` or local raw rasters.
- The shared metric's prose overstates a bound on marginal truth credit. The default competition arithmetic was not proven wrong by this finding; this session has no write permission to the shared template, so no private fork or silent upstream change was made.

## Concurrent-main integration recheck

While this branch was under review, parallel work was merged into `main` at `966b9ad`. Its 35,000-dot step-over TIFFs were re-read without modifying them: 34,253 dots are inside the pinned mirrored footprint, 747 outside, and 34,205 of the inside dots are within 3 px of the registered lattice (**99.8599%**). This contradicts the earlier subset-only uniqueness claim and requires **DUPLICATE STOP**, independently of any score. The local validator also rejects the footprint mask and nonzero exterior; organizer portal behavior remains unverified. See `concurrent-candidate-audit.json` and `scripts/audit_parallel_candidate.py`.

A separately published synthetic TIFF has a 1200 × 1600, 30 m grid rather than the 3730 × 3292, 100 m competition grid. It is not a submission. We retained parallel files and original conflicting reports in `archive/concurrent-966b9ad/`, redirected misleading legacy landing pages, and disabled legacy generation/finalization/partial-registry approval until a full gate exists. No parallel TIFF is endorsed by this lane.

## Next prerequisites

1. A scientifically justified lower-budget lane (the counting bound alone cannot prove novelty); retain the full literal registry and never select cells merely to exploit lattice holes.
2. Restore the actual hash-matching shared cached bands and obtain permission to use the unlicensed owner template, then run each feature-only canary and the pinned buffered holdout against an actually comparable incumbent.
3. Obtain the organizer-authenticated sample/data, current team quota and score receipts; reconcile the range/nodata behavior with official guidance without spending a slot on a failing candidate.
4. Refresh the complete registry and rerun both surface and final-dot novelty checks. Only a separate selector may consider a candidate after all gates pass.
