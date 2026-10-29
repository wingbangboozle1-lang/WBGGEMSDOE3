# Repository review — 2026-10-29 UTC

## Decision

**DO NOT SUBMIT. No new TIFF was generated; no geological experiment or holdout was run; no weekly slot was used.** The repository's release gate remains negative, so this review did not build or place a candidate. A concurrent 2026-10-29 main-branch evidence review measured the registered witness as a soft-probability surface and found that treating every finite value greater than zero as a "dot" is a definition mismatch; that review does **not** change the gate or authorize a new dot definition. It also records independent high-overlap lattice/other comparators for the existing invdesign raster. The measurements are conditional on hash-pinned owner mirrors, not organizer provenance or a complete portal-registry census. Keep the gate closed until the definitions and all-registry checks are resolved. See the negative run card and witness-definition review linked below.

This review did not independently inspect the nine peer repositories' new content or verify new submission receipts. It refreshed source commit identities only. It therefore does **not** revise the nine-site score/file table, claim new scores, or treat changed source HEADs as evidence that a TIFF or score changed.

Machine-readable review card: [`evidence/repo_review_2026-10-29.json`](../evidence/repo_review_2026-10-29.json).

## Executive decision for the requested sites

The highest historical value in the repository's pinned nine-site audit is GEMSDOE32's **OWNER-REPORTED 0.2778**. That is not an organizer receipt or a current independent evaluation. The old peer-site scores are context only. A defensible prospective score estimate is **not available**, and every listed file remains research-only / **not approved to download and submit**.

| Site | Pinned historical top file in this repo | Owner/user-reported score | Current estimate | Submission decision |
|---|---|---:|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | 0.2477 | Not estimable | Do not submit |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` | 0.2600 | Not estimable | Do not submit |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` | 0.2449 | Not estimable | Do not submit |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` | 0.2710 | Not estimable | Do not submit |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | 0.2600 | Not estimable | Do not submit |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` | 0.2708 | Not estimable | Do not submit |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | **0.2778** | Not estimable | Do not submit |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 0.2632 | Not estimable | Do not submit |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 0.2750 | Not estimable | Do not submit |

These rows are sourced from the frozen audit [`evidence/focus_audit.json`](../evidence/focus_audit.json) and rendered on the [executive summary](../docs/executive-summary.html). The scores are explicitly classified as owner/user reports without receipts. The highest among them is not a recommendation, and uniqueness inside the nine-site comparison is not the same as passing the full registry gate.

### What the 0.2778 report could mean—and what it does not prove

The saved pair-identification analysis says the GEMSDOE32 B2 positive support is an exact subset of the GEMSDOE28 H27-4 base, with 2,545 cells removed near a mirrored catalogue. Given the official task's false-positive-sensitive distance-weighted Tversky construction (as recorded in the source audit), pruning low-credit predictions while retaining useful fault coverage is a plausible way to improve the metric. That is a **mechanistic possibility**, not a verified causal explanation: no organizer receipt binds the score to those bytes, and hidden labels are unavailable. The score cannot be independently reproduced from the repository evidence.

No claim that a new method will exceed 0.2778 or the dated public leaderboard values is warranted. The merged repository contains a later dated public-page capture from 2026-10-29: rank 1 = 0.4544, rank 25 = 0.3330, and rank 26 = 0.3328; the earlier 0.3195 was rank 26 in the 2026-10-28 capture. The 0.4413 and 0.3195 figures in the prompt are not the public high in these dated captures. This review did not fetch the site independently; the 2026-10-29 capture was added by a concurrent session, its exact response time is unavailable, and the automated public-feed last-success remains 2026-10-28. These are public-test observations, not this project's scores or receipts.

## Current-source feed finding and implementation

At `2026-10-29T20:24:47Z`, GitHub API checks found that **all 9/9 focus-site repositories had moved** from the pinned commit identities in `docs/sources.json`; the organizer reference-solution repository was unchanged. The exact observed HEADs, prior pins, timestamps, and error/status fields are in [`docs/freshness.json`](../docs/freshness.json) and [`evidence/latest-upstream-check.json`](../evidence/latest-upstream-check.json). These are GitHub identity checks only. A changed HEAD does not tell us whether a score, submission raster, or receipt changed.

The current Pages site exposes the existing scheduled nine-site identity monitor (`evidence/latest-upstream-check.json`) on the overview page and labels it as GitHub HEAD drift only, not a score/TIFF/receipt update. The Pages workflow refreshes that monitor before rendering. This review's independently refreshed `docs/freshness.json` is retained as a date-stamped identity check, not as a score feed. The public leaderboard observation from 2026-10-29 was supplied by a concurrent repo review; it is a dated page capture, not an automated feed success or a project result.

A concurrent upstream review, [witness-definition review](session-review-2026-10-29-witness.md), now supplies a byte-level measurement of the soft-probability witness: finite values range 0.000463–0.984116, so the literal finite-and-positive convention marks the full footprint while a ≥0.5 threshold marks 14.1%. This indicates a definition mismatch, not evidence that the witness is a sparse dot set. That upstream review kept DO-NOT-SUBMIT and did not change the protocol. It also reports the existing invdesign raster overlaps 0.9944 with a lattice, 0.8166 with a habitat comparator, and 0.7178 with another comparator; those historical measurements reinforce that changing the witness rule alone does not clear that artifact. Full saved measurement: [`evidence/witness_definition_check_2026-10-29.json`](../evidence/witness_definition_check_2026-10-29.json). I did not independently rerun that analysis in this review. The concurrent nine-site verification also reports that `data/template_grid.tif` has 12,279,160 finite zero cells, while the cited writer footprint has 5,167,373 cells; this needs resolution before any format validation. It also found a third-party mirror's `labels.tif` hash-identical to `existing_faults.tif`; that mirror's organizer provenance/license were not established and the copy was not used for holdout. See [`evidence/verification_2026_10_29.json`](../evidence/verification_2026_10_29.json).

## Preregistered geological candidates and validation status

The repository already has five ranked, differentiated, untested hypotheses in [`knowledge/preregistration-2026-10-28.md`](preregistration-2026-10-28.md) and its JSON copy:

1. Local multichannel radiometric mixing-manifold residual at concealed structures.
2. Replicated cross-catchment channel-profile discontinuities.
3. Sampling-corrected, strike-anisotropic shallow thermal evidence.
4. Repeatability across independent airborne acquisition crossings.
5. Landsat surface-alteration texture conditioned on independent structure.

Each has named input layers, a physical signature, a rationale for uncatalogued faults, code-difference notes, and a named non-fault mimic. The ranking is qualitative, not a projected DTI. **None was tested.** The top candidate must not be validated until the pre-placement duplicate stop is resolved and the official/organizer data, shared cache, and common holdout runtime are established. No candidate TIF is available in this review.

A concurrent 2026-10-29 review also proposed three additional candidates (not tested here): (1) **H7-FM**, highest priority there: USGS ComCat focal-mechanism nodal-plane strike clustering, potentially revealing microseismicity on unmapped faults; mimics include quarry blasts and induced seismicity. USGS API documentation is linked in the 2026-10-29 official-source audit, but regional mechanism coverage is unverified. (2) **H6-ECO**: NASA ECOSTRESS nighttime land-surface-temperature anomalies along structural trends; potential mimics include irrigation/vegetation and playa/albedo; the NASA JPL data page is documented but access was not verified. (3) **H8-MT**: magnetotelluric resistivity contrast, potentially sensitive to fluid-bearing structures; clay alteration/conductive sediment are mimics, but the proposed source URL returned "Page not found" and this hypothesis is blocked pending a verified official data source. These three are in [`knowledge/review-2026-10-29-session.md`](review-2026-10-29-session.md) and [`evidence/official_source_check_2026-10-29.json`](../evidence/official_source_check_2026-10-29.json); none clears the release/holdout blockers.

## Three review passes

### Pass 1 — inspect and implement

- Read the current README, project prompt, AGENTS working agreement, current negative card, prior reviews, source audit, preregistration, and locked protocol.
- Confirmed the project-level gate remains negative, the current site already contains the nine-site owner-report table and GEMSDOE32 caveat, and archived TIFFs are not linked as cleared submissions.
- Ran GitHub source-identity checks; all nine peer sites had changed since the pinned references. Reconciled the report with the existing Pages monitor, which already refreshes the nine-site identities before rebuilding and exposes them with an explicit non-score caveat.

### Pass 2 — adversarial review

- Checked the panel's language and data path: it reports only commit identity, links the exact observed peer commit, does not rewrite owner scores, and does not permit promotion or file download.
- Rechecked the literal-witness stop, candidate-free run card, and conditional provenance statement. No attempt was made to evade the duplicate rule, fabricate a unique raster, or infer hidden-label performance.
- Confirmed the monitor includes all nine required focus sites and fails visibly as `UNKNOWN` if identities are unavailable; source changes are not conflated with score changes.

### Pass 3 — original-request and software verification

- Rechecked the executive summary against the nine requested site IDs, score-label requirements, GEMSDOE32 uncertainty, no-score-estimate limitation, and explicit no-download/no-submit status.
- Ran `scripts/build_site.py` and `scripts/check_site.py`: **PASS**.
- Ran `.venv/bin/python -m pytest -q` after merging the concurrent upstream verification: **242 passed, 4 skipped, 72 Rasterio deprecation warnings**.
- Ran Python `compileall` on `scripts`, `src`, and `tests`: **PASS**; `git diff --check`: **PASS**.
- No candidate validator or holdout was run because there is no eligible candidate and the blocker is upstream of placement.

## Limitations / next work

1. **Re-audit the changed peer commits.** For each of the nine repositories, inspect current reviewed source files and exact TIFF hashes; distinguish new candidates, withdrawals, receipts, claimed scores, and old artifacts. Only update the executive table when the source and evidence type are pinned and explicitly classified. Start with GEMSDOE32, then GEMSDOE36 and GEMSDOE28, whose historical claims are nearest the observed top. The original request's designated single method paragraph is not identifiable in the reconstructed project brief, so no lane was inferred.
2. **Resolve the comparator/dot definition with defensible evidence.** The concurrent witness-definition audit supports that a continuous soft-probability surface is not automatically a set of "dots"; the active release gate has not adopted a revised comparator policy. Do not change thresholds ad hoc. Document whether dense calibration/null rasters are compared as surfaces or discrete dots, then rerun the all-registry audit; the prior invdesign raster still failed other comparator overlaps even if the dense witness were redefined.
3. **Restore authenticated organizer inputs and shared runtime.** Current checkout lacks the feature cache, labels, whole-segment buffered folds and established common runtime. Owner mirrors do not prove organizer provenance. Official data/submission pages require login.
4. **Do not infer a leaderboard score from a holdout or owner claim.** The project needs matched whole-segment holdout evidence, per-feature leakage canaries, a complete all-registry pre/post placement audit, and saved-byte format validation. A separate selector must still verify current weekly quota before any slot use.
5. **Refresh official sources only where access permits.** This review did not re-fetch DrivenData. The merged repository contains a separately captured 2026-10-29 public leaderboard and official-source check; automated leaderboard-feed metadata still marks 2026-10-28 as its last scheduled success. The 2026-10-29 page capture has date-only precision and is not an organizer receipt. See both dated source audits before quoting a rank or deadline.

## Reference links for manual review

- [DrivenData problem description and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DrivenData competition data page (login-gated)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE GDR INGENIOUS data submission #1391](https://gdr.openei.org/submissions/1391)
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
- [Official source audit, 2026-10-29](../evidence/official_source_check_2026-10-29.json) and [2026-10-28 prior audit](../evidence/official_source_check_2026-10-28.json)
- [Public leaderboard capture, 2026-10-29](../evidence/leaderboard_observation_2026-10-29.json) and [2026-10-28 prior capture](../evidence/leaderboard_observation_2026-10-28.json)
- [Nine-site source identity feed](../evidence/latest-upstream-check.json)
