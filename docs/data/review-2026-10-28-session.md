# Repository review — Arena session 7393d521 — 2026-10-28

## Decision

**Negative preflight; DO NOT SUBMIT.** No candidate TIFF was generated, no holdout was run, no score was produced, and no real slot was selected. The current literal-registry stop fires before any scientific experiment or placement. The accompanying machine-readable card is [`evidence/session_7393d521_run_card.json`](../evidence/session_7393d521_run_card.json).

## Pass 1 — preregistration and implementation

Before changing the active site, recorded five distinct, ranked hypotheses in
[`knowledge/preregistration-2026-10-28.md`](preregistration-2026-10-28.md) and
[`evidence/preregistration_2026-10-28.json`](../evidence/preregistration_2026-10-28.json):

1. local radiometric mixing-manifold residual at concealed structures;
2. paired cross-catchment channel-profile discontinuity;
3. sampling-corrected, strike-anisotropic shallow thermal evidence;
4. acquisition-crossing repeatability in airborne data;
5. Landsat surface-alteration texture conditioned on independent structure.

Each names its layers, mechanism/signature, uncatalogued-fault rationale, named non-fault
mimic, repository-overlap distinction, cost, and data-access status. Ranks are qualitative
research priority only; no DTI is projected. All five are **NOT TESTED**. The owner-mirrored
feature stack is hash-pinned but not organizer-authenticated, and the shared cache/runtime is
absent.

Rebuilt the project-level decision path as fail-closed: `scripts/build_site.py` renders the
negative review; `scripts/check_site.py` validates current evidence, site tags, links, and
absence of candidate-download links. The retired positive renderer/gate/evidence-page scripts
were replaced by blocking stubs. Scoped FCHD/AMDC archives remain lane-negative. The top-level
research-download index deliberately offers no direct TIFF link; old TIFFs remain inventoried
and labeled research-only.

## Pass 2 — adversarial implementation/review pass

Reconciled the active generator, release gate, checker, README/AGENTS, and site-facing tests
against the witness stop. Updated tests that had required global `SUBMIT` or deterministic
no-op generation. Preserved lane-specific negative evidence and generic synthetic tests of the
release-gate schema; no historical run card is treated as current authority.

The stop remains conditional: the witness is a registered, SHA-256-pinned public owner mirror,
positive on 5,167,373/5,167,373 mirrored sample-footprint cells under the saved finite-and-
positive rule. It is not authenticated as organizer data and this is not a complete census of
the portal registry. Nevertheless, under the user's current literal overlap protocol, any
nonempty in-footprint prediction would fail the >70%/3-pixel dot-overlap threshold at 100%.
No surface rank-correlation was computed because there is no candidate surface. Do not dismiss
the blocker merely because a content-aware lane audit excludes it.

## Pass 3 — sources, task reconciliation, and final checks

Retrieved the official competition metric/format page, September 2026 official rules PDF,
public leaderboard, USGS GeoDAWN release, USGS ScienceBase record, DOE GDR #1391, USGS 3DEP,
and Landsat Collection 2 pages on 2026-10-28. The public submission and data routes redirected
to login. Full observations and caveats are in
[`evidence/official_source_check_2026-10-28.json`](../evidence/official_source_check_2026-10-28.json).

The official page confirms the 0.2/0.8 DTI weights and 300 m triangular kernel; the format
text requires EPSG:32611, 100 m, one float32 band, [0,1], and null/NaN outside bounds. The
September 2026 official rules state three submissions per week per entity, one final
submission across both rounds, and disclosure of generative-AI use in the narrative. The
competition home page lists a 2026-12-03 23:59 UTC end, while rules Appendix A.1 says 5 p.m.
ET on the deadline date; effective cutoff remains unresolved, with the earlier time safest.

Fetched the official leaderboard page and its HTMX fragment on 2026-10-28, confirming visible
rank 1 0.4544; rank 25 0.3217; rank 26 0.3195; rank 48 0.2895. The fetch interface does not
expose an exact timestamp; these are public-only observations, not a project score. The scheduled
GitHub Pages feed refreshes the public top/rank rows every six hours and preserves a marked stale
snapshot on failure, but that scheduled HTTP job itself was not invoked in this sandbox.

The nine requested focus scores remain owner/user reports without receipts. GEMSDOE32's
reported 0.2778 has a plausible metric mechanism: saved support analysis reports an exact
subset of the GEMSDOE28 base with 2,545 cells removed near a mirrored catalogue. This could
reduce false-positive mass, but cannot prove the cause without hidden labels and a receipt.

## Experiment/slot accounting

- Geological experiments: **0 / 3**.
- Experimental time: **0 / 2 hours**.
- Holdout runs: **0**; no evaluator version/value/CI/withheld-positive count is claimed.
- Candidate rasters generated: **0**; no raster SHA-256 exists for this review.
- Selector actions / weekly slots: **0 / 0**.
- Organizer receipts: none.

## Verification results

Final run after the revisions:

- `.venv/bin/python scripts/build_site.py`: **PASS**. Rebuilt the current negative site and the scoped AMDC/FCHD archive pages; no candidate or slot was created.
- `.venv/bin/python scripts/check_site.py`: **PASS**. The negative gate is hash-bound, candidate-download links are absent, and local HTML links resolve.
- `.venv/bin/python -m pytest -q`: **236 passed, 4 skipped** (72 upstream Rasterio deprecation warnings). The initial collection/build iterations exposed stale path and historical-test assumptions; they were corrected, and the complete suite now passes.
- After reconciling the advanced `main` base, rebuilt the complete site twice and compared the full `docs/` tree: **byte-stable across 204 files**, including generated JSON, the quarantined upstream artifact, and archive pages. The HCE recursive HTML determinism test also passes.
- The scheduled GitHub Pages workflow was reviewed: it refreshes the public fragment every six hours, retains/marks the last successful observation on failure, then rebuilds and checks the site. The updated parser/refresh behavior is covered by passing feed tests. The scheduled network workflow itself was not invoked in this sandbox, so the actual automated fragment refresh remains unverified here. The dated 2026-10-28 page observation has an unknown exact fetch time and is not represented as a live refresh.

These are software/site checks only. They do not run a geological experiment, generate a candidate, establish a holdout score, validate portal acceptance, authenticate the registry mirror, or authorize a submission.

## Base-branch reconciliation (after the initial review)

While PR #56 was being prepared, GitHub `main` advanced through PR #53 and introduced a
15,000-dot blind-basin TIFF plus a small accompanying record under `docs/downloads/`. It was
not generated or used as a candidate in this review. Its bytes were matched to the upstream-reported
SHA-256 only to identify the archived file; no science or format validator was run. The artifact
is retained only as an upstream historical file; the rebuilt top-level downloads index has no
direct TIFF link and the legacy inventory labels every file DO NOT SUBMIT. The current run card
records the source path and upstream-reported SHA-256 separately from this review's null candidate
fields. No new surface, score, holdout, or format-validation check was run on that artifact. The
literal witness stop remains binding and the file is not cleared.

## Remaining work / limits

1. Resolve the witness/registry protocol question only through a documented, evidence-based
   correction; do not waive the threshold ad hoc.
2. Restore authenticated competition data if permitted, verify the shared cache/template and
   common holdout/writer runtime, then run the preregistered protocol only if the uniqueness
   stop has been resolved.
3. Check the live portal quota and clarify the conflicting deadline with the organizer; no
   login, quota view, or receipt was available here.
4. If future scientific gates pass, a separate selector must make the one-final-entry choice.
   That action is outside this research lane.
