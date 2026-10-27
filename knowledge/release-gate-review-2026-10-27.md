# Repository-wide release-gate review — 2026-10-27 UTC

## Decision

**DO NOT SUBMIT.** This review did not create a raster, run a new geological
experiment, spend a weekly slot, or turn an estimate into a score. It reconciles
conflicting lane-level artifacts against the governing negative run card.

The only locally downloadable repository candidate is
`wbggemsdoe3-skarpline-union-20261027-610acf58-zeros.tif`, SHA-256
`610acf58905f3b461971bd4a5c67ff7c30894cd92dca20f480f27ecc66de5bb2`. It is
**format-valid for local checks but not approved for a competition upload**.
The machine-readable conclusion is [`evidence/release_gate.json`](../evidence/release_gate.json).

## Verified reconciliation

| Requirement | Evidence inspected | Result |
|---|---|---|
| Governing release decision | `evidence/run_card.json` | `negative`; `selector_approval: false`; no selected raster SHA-256 |
| Candidate lane conclusion | `evidence/gemsdoe_run_card.json` | lane says `promote`, but its evaluation label is `PROXY-DTI (not a competition score)` |
| Required holdout class | User protocol: buffered hide-and-recover HOLDOUT-DTI | **Missing for the candidate**; proxy does not satisfy this class |
| Literal registry rule | governing card and `evidence/verification_2026-10-27.json` | **Fails/has no pass record**; a dense registered control is positive on the full mirrored footprint |
| Saved-byte format | candidate run card; independent local re-read | locally valid single-band float32, same pinned grid, finite `[0,1]`; this does **not** establish portal acceptance |
| Candidate identity | SHA-256 recomputation of published `docs/downloads/` TIFF | matches the candidate card |
| Historical focus leaders | `evidence/focus_audit.json` | all nine listed leaders overlap another focus artifact above the stated 70% three-pixel threshold; none is a new upload candidate |

The release gate blocks for five independent reasons: the governing verdict is
negative; selector approval is absent; the governing card does not authorize the
candidate SHA-256; the candidate has PROXY-DTI rather than the required
HOLDOUT-DTI; and the candidate lacks a passing literal all-registry uniqueness
record. Any one is sufficient to stop an upload.

## What can be said about GEMSDOE32 B2

`GEMSDOE32` B2's `0.2778` is retained as **OWNER-REPORTED**, not
ORGANIZER-CONFIRMED: no submission-page receipt tied to its hash exists here.
The local byte audit verifies a structural observation: the B2 support has 37,654
pixels and is an exact subset of a 40,199-pixel historical base, with 2,545
catalogue-proximal pixels removed. Sparse, catalogue-suppressed placement is
consistent with the stated α=0.2, β=0.8, 300 m distance-weighted metric, but
neither the bytes nor a proxy identifies a causal hidden-label score. No honest
claim that another file beats `0.2778`, `0.3195`, `0.4413`, or any current public
leaderboard value follows from this repository.

## Three implementation/review passes

1. **Implementation.** Added a fail-closed release-gate evaluator. It requires a
   governing `promote` decision, explicit selector approval, the exact approved
   candidate SHA-256, a `HOLDOUT-DTI` label, a candidate lane promotion, and a
   literal registry pass. The release decision is serialized with hashes of both
   input cards.
2. **Bug and edge-case review.** Rebuilt the dashboard so its metadata and call to
   action come from the global gate, not a lane-local card. Research downloads are
   still available but are visibly marked **DO NOT SUBMIT**. The HCE pages now
   display the global stop so a content-aware lane diagnostic cannot override it.
   The checker verifies links, decision metadata, published-byte SHA-256, and all
   four root pages.
3. **Final re-check.** Rebuilt the root and HCE sites; `scripts/check_site.py`
   passed; `pytest` passed 120 tests with 4 intentional skips; `git diff --check`
   passed. The release gate was recomputed from the two source cards and its
   candidate SHA-256 was independently matched to the published TIFF.

## Official/manual-review links and access boundary

* [DrivenData problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
* [Competition overview](https://www.drivendata.org/competitions/306/competition-doe-gems/)
* [Public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
* [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
* [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
* [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
* [INGENIOUS GDR record](https://gdr.openei.org/submissions/1391)

This sandbox can access GitHub and package registries, but not the official
DrivenData/USGS/GDR download hosts listed above. Their links are provided for
manual review; this review does not claim to have fetched, authenticated, or
licensed their bytes. The official training/test data remain an access blocker
for a new compliant experiment.

## Next session: precise, non-manual work

1. Obtain an explicit protocol-owner decision defining the support of a dense,
   continuous registry raster in the three-pixel overlap rule. Do not silently
   reclassify it.
2. Obtain organizer-authenticated input files and sample-submission convention,
   especially the outside-footprint behavior that caused the historic range error.
3. Assign one geological lane, freeze its 3–5 hypothesis ranking before execution,
   run all feature canaries, then use the shared buffered hide-and-recover
   evaluator. Stop after three experiments or two hours.
4. Only add a candidate to the selector when it has a positive paired
   HOLDOUT-DTI interval, a literal registry pass, a saved-byte validator pass,
   and a current quota check. Preserve the portal receipt next to the exact SHA-256.
