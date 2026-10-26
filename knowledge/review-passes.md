# Three-pass review, 2026-10-26

## Pass 1 — implement and verify

Inspected the initial one-line repository and nine GitHub repository trees.
Retrieved selected manifests, evaluator/writer code and peer summaries with
blob identities. Retrieved the organizer reference README/notebook. Restored
57GEMSDOE package using exact hash pins, not a rewritten scorer/writer. Built
the dated nine-site executive page, submission instructions, qualitative
hypotheses and fail-closed prerequisite/format/novelty tooling. This branch
produced no geological experiment or TIFF. The subsequently integrated base
contains an earlier PR #7 candidate, now reviewed in `evidence/run_card.json`;
it is audit-only and the pinned owner-mirror recheck measures 97.87% of all its
dots within 3 px of the registered lattice, above the literal 70% stop rule.

## Pass 2 — assumptions, edge cases, fixes

* Checked API provenance explicitly: the recursive tree response resolved
  from `main` returned a SHA accepted by the commits endpoint. Confirmed each
  snapshot commit and recorded its distinct root-tree SHA before building links.
* Exposed that historical `.tif` filenames are inferred from identifiers, not
  verified artifact paths; no dead/fake download buttons.
* Did not import upstream claims of byte-level equality as our measurements.
* Kept dense calibration lattice entries subject to the literal stop rule.
* After noticing the owner manifest marks `existing_faults.tif` byte-identical to `labels.tif`, changed the default restore/audit path to skip that label alias. The sample raster is used only for its finite/nodata mask, not its pixel values.
* Kept preflight file-presence separate from validated inputs and release approval.
* Tested NaN, infinity, range violations, CRS/shape/transform mismatch, nodata,
  duplicate overlap, degenerate novelty, template identity and source blob hashes.
* Identified conflicting peer shared-template pins; did not pretend our restored
  evaluator is universally agreed. No private evaluator modification.
* A standalone credit-per-dot threshold in upstream prose is not universally
  valid; executive summary uses the exact marginal component condition instead.

## Pass 3 — requirements and honest scope

18 tests pass on Python 3.11. Synthetic arrays/TIFFs in tests are temporary
fixtures, not competition submissions. Site generation is deterministic and CI
checks for drift. Snapshot links now use matching commit IDs. Source refresh
records timestamps and failures; it does not claim an authenticated live feed.
The run card uses nulls for every unmeasured scientific quantity. Confirmed
requirements **not fulfilled**: full verbatim prompt persistence (a structured
restatement is in README), a new unique TIFF, actual spatial holdout experiment,
complete byte-level peer raster comparisons, independent organizer score
receipts, official literature/metadata outside GitHub, and weekly selector
approval. These cannot honestly be certified by this audit. No hidden labels,
no submission slot use, no claim of beating any leaderboard value.

## Publication access check

Pages is already configured as legacy publishing from main at root. Changing
it to Actions deployment was denied by GitHub integration permissions (403).
Retained the existing mode and added a root entry page pointing to docs; removed
the incompatible Actions deployment workflow. Publication still requires the
existing GitHub Pages build to succeed; do not claim deployment before checking.

## Concurrent-main integration review

Main advanced to 8488b95 during PR creation. Preserved its synthetic generator,
TIFF/ZIP, manifest, earlier docs and cards under archive/concurrent-8488b95;
none are accepted as actual holdout, full-registry measurements or a matched
competition grid. Resolved executive-summary conflicts to the fail-closed page.
Retained the existing Pages workflow from main (prior GitHub run succeeded).
