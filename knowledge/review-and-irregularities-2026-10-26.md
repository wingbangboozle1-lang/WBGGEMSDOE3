# Review and irregularities — 2026-10-26

## Executive conclusion

**No competition GeoTIFF is cleared; do not upload a historical or parallel file.**
This audit did not create a candidate, but another branch merged one during this work.
The literal protocol is unsatisfiable for any nonempty in-footprint prediction under the shared
registry's finite-positive support definition. `evidence/focus_audit.json` is a
reproducible raster measurement; it is not a leaderboard or holdout score.

### IR-01 — universal duplicate witness

The [registered 17GEMSDOE E-proba raster](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif)
(SHA-256 `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`) is present in the
[shared registry evidence](https://github.com/buffedlizard55-lab/57GEMSDOE/blob/822a0ce5546c7b6749cdd82eb145b6b3e616603d/evidence/uniqueness_session6_full_registry_696.json).
It is finite and positive on **all 5,167,373** finite cells of the hash-pinned mirrored sample, on the same grid.
The shared [`uniqueness.py`](https://github.com/buffedlizard55-lab/57GEMSDOE/blob/822a0ce5546c7b6749cdd82eb145b6b3e616603d/src/gems57/uniqueness.py)
defines support as finite and positive. Every nonempty set of allowed dots is contained
in that support; hence at distance zero (and therefore within 3 px), forward overlap is
100%, strictly greater than 70%. This is a proof, not an extrapolation from examples.
The spacing-5 lattice is an independent warning but **is not** a universal proof: 6,649
footprint cells are farther than 3 px from its support.

**Protocol implication:** stop before generating a surface, placing dots, or spending a
slot. A defensible future policy could explicitly define which registered continuous and
space-filling controls are comparators, and preregister a symmetric/content-aware test,
but this would be a **change** to the user's literal rule. It cannot be silently applied.

### IR-02 — inconsistent site advice / partial scopes

[GEMSDOE27's page](https://buffedlizard55-lab.github.io/GEMSDOE27/) recommends its H31
file based on a 27-raster comparison. The exact pinned file was reread and passes the
shared local all-finite format report, but every one of its 37,654 positive pixels is
within 3 px of the dense registered witness. It is **not** cleared under the requested
literal any-registry rule. Its surface and holdout were not replayed in this audit.
GEMSDOE32's H47 audit also reported `literal_rule_passed: false` while displaying a
separate density-adjusted pass; the literal rule has no such exception here. Neither a
local format pass nor a subset registry audit authorizes a slot.

### IR-03 — owner claims lack upload receipts

The values in `registry/focus_sites.json` are user/owner-reported claims, not scores
copied from an authenticated submission-page receipt. A hash-pinned file and repeated
text do not establish which bytes were uploaded, what score the organizer assigned, or
whether the leaderboard values are directly comparable. The official public
[leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
is a separately timestamped public observation, not a receipt for our file. No
calibrated estimate or new HOLDOUT-DTI is asserted.

### IR-04 — sample provenance and outside-footprint convention

The mirror's sample (`2176d08e...`) includes 60,988 ones, although the public problem
description describes the sample as predicting total absence. It is used here only to
establish a local grid and finite footprint; it is not proven to be the current official
sample. The [official format text](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
says data outside the bounds must be null/NaN. The mirrored sample has 7,111,787 NaNs
outside its finite footprint; the shared `submission_writer.py`, by contrast, writes
all-finite zeros there with no nodata value or validity mask. These are **different**
conventions, not simply stricter versus looser. It is unclear whether the organizer's
“bounds” wording refers to this sample mask or only the rectangular raster extent, and
we have no acceptance receipt. This is an unresolved **format risk**, independent of the
registry stop: check with organizers and reconcile the shared writer once upstream before
any upload. The prior range error does not establish the cause or acceptance of either
convention. Validate every scored pixel as finite and in range; do not silently clip or
fill failed predictions to make them appear valid.

### IR-05 — shared metric documentation overstates marginal-credit bound

At pinned template commit `822a0ce...`, the [shared metric docstring](https://github.com/buffedlizard55-lab/57GEMSDOE/blob/822a0ce5546c7b6749cdd82eb145b6b3e616603d/src/gems57/metric.py)
says `dT <= k_self`. One dot can cover multiple truth pixels, so this is false. A
7×7 synthetic fixture with truth at `(3,3)` and `(3,4)` and a dot at `(3,3)` gives
`dT = 1 + 2/3` while `k_self = 1`. The exact shared implementation accepts separate
`dT` and `k_self`; this example identifies a prose defect, **not** a default-parameter
computation defect. `tests/test_shared_metric.py` reproduces the counterexample and
checks the shared official-kernel calculation against brute force.

The template repository is a separate public repository on which this session's GitHub
identity has **read-only** access. An attempt to report the issue upstream was rejected
with `Resource not accessible by integration`; no private fork was created. The shared
documentation and test must be corrected by a maintainer. The session branch restriction
also prevents pushing a different branch to that repository.

### IR-06 — upstream data semantics are not authenticated

The mirror supplies band descriptions, but cryptographic pins only establish which bytes
were retrieved. Some names/descriptions (notably `tc`) are ambiguous; do not assign a
physical meaning based solely on the mirror description. Reconcile band semantics,
licenses, DEM coverage and feature provenance against organizer or official metadata
before a scientific training run. User-provided links to DrivenData and Dropbox are
outside this sandbox's outbound allowlist; the official data tab redirects to login.

### IR-07 — shared rank gate is one-sided, user rule is two-sided

The user specifies `|rank-correlation| > 0.90`. At pinned commit `822a0ce...`, the
[shared uniqueness comparator](https://github.com/buffedlizard55-lab/57GEMSDOE/blob/822a0ce5546c7b6749cdd82eb145b6b3e616603d/src/gems57/uniqueness.py)
sets `duplicate_by_rho` using `rho > 0.90` and its two-phase summary applies the same
one-sided test. A synthetic summary with `rho = -1` and overlap `0` is therefore not
reported as a duplicate upstream, while the requested absolute-rank rule requires a
stop. `tests/test_shared_metric.py` reproduces this mismatch. Our independent nine-site
*analysis* uses `abs(rho)` and strict thresholds, but the shared tool was **not**
modified or privately forked. The currently observed positive-overlap witness alone
already forces a stop; this additional defect does not create a candidate or change
that verdict. A maintainer must correct and test the shared tool once upstream before
it can certify any future two-sided clearance. The existing attempt to report another
shared defect failed because this integration has read-only access.

### IR-08 — parallel merge created a candidate that fails the literal gates

At main commit [`966b9ad`](https://github.com/wingbangboozle1-lang/WBGGEMSDOE3/tree/966b9ad722df057ca21ac5d6666c54e4626c957c),
another session merged a 35,000-dot step-over raster with SHA-256
`5d4515665dc8f3f31aa0249a32a56002f86aef199c2033cb39d836bc41adb059`. We did not
create it or replay its pre-placement surface. Against the registered 17GEMSDOE
witness, **34,492/35,000 = 98.5486%** of all emitted dots are within 3 px; all
34,253 dots inside the mirrored footprint overlap. Both exceed the literal 70% stop.
The preceding reported 26.77%/58-file pass is a *narrower comparator set*, not a full
registry pass, and its implementation uses `>0.5` for positive support instead of the
shared `>0` definition. It substitutes final dots for an independent pre-placement
surface in the reported calculation; its pre-placement gate was not verified here.

The all-zero `data/template_grid.tif` used by that run marks all 12,279,160 rectangular
cells finite, unlike the 5,167,373-cell finite footprint of the pinned owner-mirrored
sample. Under that explicitly mirror-relative footprint, the candidate has 747
positive cells outside the allowed domain and 463 in-footprint positives on the pinned
mapped-fault raster. The pinned shared `format_report` fails it on the first issue;
it is not a competition validation or official data provenance check. The claim that
all dots avoid the catalogue was based on the previous B2 prediction, not the actual
mirrored fault catalogue. The local shared writer's no-positive-catalogue constraint
therefore fails if applied. The user's earlier portal range rejection is not diagnosed
by this observation.

Its `-nan` twin is not a unique prediction: its positive mask is identical to the zero
version, it has a NaN nodata tag, and its stored array has **zero NaN cells**. The
separately generated `site/` stand-in is 1,200×1,600 at 30 m; a prior archived H80
stand-in is 1,024×1,024 at 30 m. Neither matches the mirrored competition grid. All
files and prior claims are preserved as research history, but no local/portal acceptance,
feature canary, spatial HOLDOUT-DTI, or organizer receipt was verified. See
[evidence/concurrent_audit.json](../evidence/concurrent_audit.json) for pinned bytes,
counts, format reports, and reproducible source paths.

## Independent file-level evidence behind the B2 question

The B2 support contains 37,654 pixels and is an exact subset of the pinned GEMSDOE28
H27-4 support of 40,199. The 2,545 removed pixels are 1.414–2.0 pixels from the mapped
fault mask; the closest kept pixel is 2.236 pixels away. See `h33_mechanism` in the audit.
This demonstrates catalogue-proximity pruning, not the reason for an unverified score:
the hidden truth, the actual receipt and the effective evaluation mask are unavailable.
The metric's 300 m tolerance, low false-positive weight and coverage/redundancy trade-off
make sparse near-trace predictions a plausible *hypothesis*, not a causal finding. It
is not possible to establish that a novel candidate will beat the reported incumbent
without a correctly constructed holdout and ultimately an organizer receipt.

## Data and next-session handoff

- The unmodified shared template's own `prepare_data.py --fetch --cache-bands` was run.
  The 19-band feature mirror, labels, sample, four external assets and five source parts
  matched their pinned hashes; cache files are deliberately untracked. Recreate them
  with `bash scripts/restore_shared_data.sh`.
- One binary witness makes further candidate construction fail under the stated rule.
  This lane generated no AUC canary, geological experiment, holdout CI, new raster,
  or portal submission; other branches created the research artifacts reviewed in IR-08. The maximum experiment budget was not consumed.
- After an explicit protocol revision: confirm source licensing and band meanings;
  freeze the comparator inventory and lane; run canaries; fit each fold using only visible
  fault segments; compute pooled DTI and paired spatial-block CI against a matched
  incumbent; perform the registry gates before placement and on final dots; write and
  reread via the shared writer; run the separate quota selector. Do not treat a proxy as
  a leaderboard score.

## Three review passes completed

1. **Source and preflight review.** Checked the official task and metric, pinned the
   shared template and owner-mirrored data, hash-checked historical files and measured
   the full-footprint witness. Corrected a mistyped reference digest and a Python 3.11
   archive-extraction compatibility defect in the local bootstrap before rerunning it.
2. **Scientific, format and concurrency review.** Recorded four ranked unrun physical
   hypotheses and official-source confounders. Distinguished historical claims from
   receipts; corrected outside-bounds versus all-finite-writer wording; exposed the
   shared rank gate's one-sided behavior with a synthetic test. Independently measured
   the subsequently merged parallel TIFFs; preserved their original files and prior
   claims, replaced approval language with a negative decision, and disabled incomplete
   legacy generator/finalizer/uniqueness entrypoints rather than silently changing the
   shared tool.
3. **Integration and release review.** Merged concurrent main history into this session's
   branch without dropping its artifacts, adapted the preexisting test that assumed no
   research TIFF could exist, and added negative-guard tests. Verified the complete test
   suite, hash-bound audit/card, reproducible site, and local links. Headless Chromium
   exercised all four pages at desktop and mobile widths, checked response codes and
   banners, and found no page-wide overflow; a swipe hint and keyboard-focusable table
   were added for the mobile table. Leaderboard staleness is determined at view time so
   an interrupted scheduled deployment cannot leave an old observation labeled fresh.

The shared repository is read-only to this integration. Neither the one-sided rank gate
nor the uncertain outside-footprint convention was patched in a private fork; both need
upstream maintainer/organizer resolution before any future clearance.
