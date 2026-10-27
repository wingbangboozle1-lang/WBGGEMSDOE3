# Three-pass implementation and review — 2026-10-27 UTC

**Decision: negative / DO NOT SUBMIT.** This lane created no candidate, ran no
geological experiment and used no weekly slot. `evidence/run_card.json` is the
single authoritative current run card; other session cards are historical.
The user requested a genuinely new TIFF, but the mandatory literal duplicate
rule is unsatisfiable for every nonempty in-footprint candidate. Do not treat
this audit as a waiver, a score estimate, or selector approval.

## Pass 1 — implement and reproduce

- Read the standing instructions, existing evidence, nine focus-site references,
  shared-tool pins and historical experiment records. Restored the pinned public
  mirrors and 19 cached feature bands without altering the shared evaluator or
  writer. Mirrored bytes match their hashes; organizer provenance is not verified.
- Reproduced the universal registered witness: positive on all 5,167,373 mirrored
  footprint cells. Thus every in-footprint dot overlaps at distance zero, above the
  >70% stop, before any placement or holdout. See `evidence/focus_audit.json`.
- Added a saved-raster diagnostic and fail-closed guards on retired local writers,
  builders and release checks. A format diagnostic is not portal acceptance,
  novelty clearance, or an instruction to upload. Built the negative dashboard,
  source freshness monitor and research-only historical archive.

## Pass 2 — review and correct

- Inspected the prior LST1 artifacts, ZIP, fixed-raster holdout and deprecated
  uniqueness exemptions; verified their exact hashes and 100% witness overlap.
  Removed stale approval-bearing public duplicates and preserved original research
  bytes in `submission/`. The old holdout's fold-local compliance is not proven.
- Read current peer materials and audited the exact GEMSDOE28 S22C and GEMSDOE36 KPL
  TIFF bytes: each has 37,654 in-footprint positives and 100% witness overlap.
  The GEMSDOE27 H31 source's newer selector-required notice supersedes older
  promotional text. No peer holdout was replayed or promoted.
- Merged two parallel reviews from `main`, preserving their independent raster
  checks and the historical H6-1 receipt. Corrected overconfident interpretation:
  H6-1's context buffer excludes withheld truth within 3 px of visible catalogue
  traces, so its small proxy change cannot establish or rule out an effect on the
  unobserved competition score. Surveyed eight local TIFFs; none had *finite*
  values outside [0,1], but the portal error and its rejected bytes are unverified.
- The official problem specifies a GeoTIFF. ZIP acceptance appears in a historical
  peer-preserved portal description but was not independently verified; the current
  guide no longer presents it as a confirmed upload option.
- Rechecked official public information through the page viewer and refreshed all
  nine GitHub HEAD identities. A HEAD change is a freshness warning, not proof
  that a file or score changed. The public leaderboard leader was 0.4544 on
  2026-10-27, not a project score or upload receipt.

## Pass 3 — final recheck

- Independently reran `scripts/verify_2026_10_27.py`: **20/20 checks passed**;
  these are evidence/raster checks, not a candidate validator pass. The current
  evidence reports eight local TIFFs and the pinned historical H6-1 source hash.
- Rebuilt the site twice sequentially; the recursive docs file digest was identical.
  `scripts/check_site.py` passed required pages, local links and negative status.
  The local HTTP preview returned 200; visual browser rendering was not inspected.
- Full sequential `.venv/bin/python -m pytest -q`: **109 passed**, with 53
  rasterio/Affine pending-deprecation warnings. A clean archive without cached
  data also passed **105 tests, 4 skipped**, and reproduced the committed site.
  `git diff --check` passed. The pinned H6-1 numbers were not recomputed. CI and GitHub Pages deployment
  must be checked after merge, not inferred from local tests.

## Limitations and next actions

1. Obtain an explicit protocol-owner revision defining which support is compared
   for continuous, dense registry rasters. Do not silently exclude the witness.
2. Fix the shared tool's one-sided rank-correlation check upstream and reconcile
   official outside-bounds null/NaN wording with the shared writer's zero-fill
   behavior; clarify the previous portal range error without guessing its cause.
3. Assign one lane, run single-feature leakage canaries and buffered whole-segment
   holdouts against a matched incumbent using the unmodified shared evaluator,
   then check full registry surfaces/final dots and exact saved bytes. Only an
   independently selected candidate and current portal quota can authorize upload.
4. Obtain organizer receipts and authenticated data if available. Current public
   score claims are unreceipted, the hidden labels are unavailable, and no
   leaderboard improvement or winning probability can be responsibly estimated.
5. The README's operational instructions are condensed; its peer-preserved
   historical brief is explicitly not an independently verified transcript.
