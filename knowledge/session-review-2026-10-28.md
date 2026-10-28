# Session review — 2026-10-28

**Verdict: negative / DO NOT SUBMIT.** This was a repository review and
preflight, not a geological experiment. No new raster or TIF was generated,
no holdout DTI was measured, no competition slot was used, and no leaderboard
submission was made. The machine-readable record is
[`evidence/session_review_2026-10-28.json`](../evidence/session_review_2026-10-28.json).

## Pass 1 — inspect and establish what is reproducible

- Read the standing project brief, `README.md`, `AGENTS.md`, the release
  protocol, the existing ranked preregistration, the current dashboard, and
  the negative run cards. The request's “single method paragraph” does not
  identify an assigned geological lane in the available repository context;
  do not infer one from its general hypotheses.
- Reviewed the existing four ranked candidates in
  [`preregistration-2026-10-27-9b794637.md`](preregistration-2026-10-27-9b794637.md).
  These are proposals, not proven novel ideas or completed experiments. The
  highest-ranked is repeated signed profile asymmetry in gravity and reduced-
  to-pole magnetics after removing a local planar background. Its plausible
  non-fault mimics include dipping lithologic contacts, remanent magnetization,
  and interpolation artifacts. The cited official USGS GeoDAWN URL is retained
  for review, but this environment cannot fetch that host, and no authenticated
  band semantics/stack were restored here.
- Confirmed the documented all-footprint registry witness: its positive
  support covers all 5,167,373 cells in the mirrored submission footprint.
  Under the protocol's current shared interpretation (`finite & value > 0` as
  the registry dot support), any nonempty in-footprint candidate would have
  100% directed overlap with that witness at zero distance and thus exceed the
  70% stop. This is a saved mirrored-raster measurement, **not** a new
  candidate audit, leaderboard score, or proof the mirror is organizer-authentic.
  Because the rule says to stop on this condition, no candidate surface was
  constructed or tested. A dense probability surface is arguably not a
  meaningful “dots” comparator, but silently exempting it would change the
  supplied rule; this needs an explicit protocol decision before experiments.
- The repository contains only `data/template_grid.tif` in `data/`; no restored
  competition feature stack, training labels, or saved holdout folds were
  present. The project's stated sandbox host allowlist also excludes
  DrivenData, Dropbox, USGS, GDR, and the PDF host. Therefore this session
  could not independently retrieve the official competition data or verify
  current portal rules/quota. Public owner mirrors do not establish organizer
  provenance.

## Pass 2 — run available verification and identify edge cases

- Installed the pinned project requirements in an ignored local `.venv`.
  `python -m pytest -q` initially could not start because system Python had no
  pytest; after installing requirements, the complete available suite passed:
  **224 passed, 4 skipped**, with 72 Rasterio pending-deprecation warnings.
  The skips are preserved as skips, not described as passing tests.
- `python scripts/check_site.py` passed: negative gate, source hashes, witness,
  research bytes, statuses, and local links.
- Rechecked that no new changes to a candidate, release authority, submission
  slot, or public site were made. The current root decision remains negative.
  Existing historic/downloadable research TIFs remain labeled as research-only;
  none is presented as cleared for upload.
- A dated public leaderboard observation already in the repository is not a
  live check. The user's supplied `0.3195` and other historical values cannot
  be reconciled with prior repository observations without a timestamped
  organizer page capture; neither is treated as today's verified score.

## Pass 3 — map request to a safe next action

- The desired new TIF and the explicit stop rule conflict under the current
  literal registry support definition. Generating a file by changing its name,
  tiny values, or dots would not satisfy the required uniqueness gate; it would
  merely bypass it. No file is cleared for download-and-submit.
- The four ranked candidates already provide the requested candidate set and
  their relative rationale/costs. The top one cannot be validated honestly
  without the cached feature stack, labels, segment/fold definitions, and shared
  evaluator inputs. Attempting a holdout without those would be a different,
  unverified experiment. Do not claim a HOLDOUT-DTI or predicted competition
  score.
- **Before the next experiment:** (1) explicitly resolve whether the registry
  rule applies literally to dense continuous probability rasters or whether
  the registry should separately classify comparator types; (2) identify the
  actual method paragraph/lane; (3) restore hash-pinned template, feature stack,
  labels, whole-fault segment identifiers, buffered folds and registry inputs;
  (4) verify official source metadata and competition output rules. Then use
  the shared evaluator/writer, feature-alone leakage canaries, paired spatial
  holdout and full pre/post placement uniqueness audit within the three-run /
  two-hour budget. Until then, the correct result is negative.

## Verification limits and sources

The existing preregistration lists the official source leads and their
availability status. Primary manual-review links include the [DrivenData
competition](https://www.drivendata.org/competitions/306/competition-doe-gems/),
[competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/),
[official USGS GeoDAWN dataset](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
[DOE GDR INGENIOUS submission 1391](https://gdr.openei.org/submissions/1391),
and [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).
These are source leads, not evidence that their content was fetched or
independently re-verified in this session. See
[`knowledge/protocol.md`](protocol.md) and the prior
[`evidence/registry_witness_recheck_2026-10-27.json`](../evidence/registry_witness_recheck_2026-10-27.json)
for the precise release conditions and provenance caveats.
