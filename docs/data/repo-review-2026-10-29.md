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

No claim that a new method will exceed 0.2778 or the dated public leaderboard values is warranted. The committed public leaderboard observation is dated 2026-10-28 (rank 1 0.4544; 0.3195 at rank 26 in that capture), and the current environment cannot query DrivenData directly. It is a dated observation, not today's live leaderboard and not this project's score.

## Current-source feed finding and implementation

At `2026-10-29T20:24:47Z`, GitHub API checks found that **all 9/9 focus-site repositories had moved** from the pinned commit identities in `docs/sources.json`; the organizer reference-solution repository was unchanged. The exact observed HEADs, prior pins, timestamps, and error/status fields are in [`docs/freshness.json`](../docs/freshness.json) and [`evidence/latest-upstream-check.json`](../evidence/latest-upstream-check.json). These are GitHub identity checks only. A changed HEAD does not tell us whether a score, submission raster, or receipt changed.

Implemented a visible freshness panel on the site overview and executive summary. It shows the check time, links to observed peer commits, provides the machine-readable report, and warns that a change signal is not a score/TIFF update. The Pages workflow now refreshes this feed before rendering. This is deliberately a **drift alert**, not an automatic score scraper or approval path. The public leaderboard and official DrivenData data/submission pages cannot be queried here under the outbound-host/authentication limits, so the older public leaderboard observation remains marked with its date.

A concurrent upstream review, [witness-definition review](session-review-2026-10-29-witness.md), now supplies a byte-level measurement of the soft-probability witness: finite values range 0.000463–0.984116, so the literal finite-and-positive convention marks the full footprint while a ≥0.5 threshold marks 14.1%. This indicates a definition mismatch, not evidence that the witness is a sparse dot set. That upstream review kept DO-NOT-SUBMIT and did not change the protocol. It also reports the existing invdesign raster overlaps 0.9944 with a lattice, 0.8166 with a habitat comparator, and 0.7178 with another comparator; those historical measurements reinforce that changing the witness rule alone does not clear that artifact. Full saved measurement: [`evidence/witness_definition_check_2026-10-29.json`](../evidence/witness_definition_check_2026-10-29.json). I did not independently rerun that analysis in this review. The concurrent nine-site verification also reports that `data/template_grid.tif` has 12,279,160 finite zero cells, while the cited writer footprint has 5,167,373 cells; this needs resolution before any format validation. It also found a third-party mirror's `labels.tif` hash-identical to `existing_faults.tif`; that mirror's organizer provenance/license were not established and the copy was not used for holdout. See [`evidence/verification_2026_10_29.json`](../evidence/verification_2026_10_29.json).

## Preregistered geological candidates and validation status

The repository already has five ranked, differentiated, untested hypotheses in [`knowledge/preregistration-2026-10-28.md`](preregistration-2026-10-28.md) and its JSON copy:

1. Local multichannel radiometric mixing-manifold residual at concealed structures.
2. Replicated cross-catchment channel-profile discontinuities.
3. Sampling-corrected, strike-anisotropic shallow thermal evidence.
4. Repeatability across independent airborne acquisition crossings.
5. Landsat surface-alteration texture conditioned on independent structure.

Each has named input layers, a physical signature, a rationale for uncatalogued faults, code-difference notes, and a named non-fault mimic. The ranking is qualitative, not a projected DTI. **None was tested.** The top candidate must not be validated until the pre-placement duplicate stop is resolved and the official/organizer data, shared cache, and common holdout runtime are established. No candidate TIF is available in this review.

## Three review passes

### Pass 1 — inspect and implement

- Read the current README, project prompt, AGENTS working agreement, current negative card, prior reviews, source audit, preregistration, and locked protocol.
- Confirmed the project-level gate remains negative, the current site already contains the nine-site owner-report table and GEMSDOE32 caveat, and archived TIFFs are not linked as cleared submissions.
- Ran the GitHub source-identity checks; all nine peer sites were changed since the pinned references. Added a machine-readable freshness panel to the current Pages output and wired the scheduled Pages workflow to refresh the identities before rebuilding.

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
5. **Refresh official sources only where access permits.** The competition leaderboard/feed was not refreshed in this environment because DrivenData is outside the host allowlist. The public page and official sources linked in `evidence/official_source_check_2026-10-28.json` remain the manual verification references; this session did not re-fetch them.

## Reference links for manual review

- [DrivenData problem description and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DrivenData competition data page (login-gated)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE GDR INGENIOUS data submission #1391](https://gdr.openei.org/submissions/1391)
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
- [Official source audit with date/status/caveats](../evidence/official_source_check_2026-10-28.json)
