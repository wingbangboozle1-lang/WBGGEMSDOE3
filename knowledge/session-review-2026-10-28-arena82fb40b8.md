# Session review — `arena/82fb40b8-wbggemsdoe3` (2026-10-28)

## Decision

**Negative — do not submit or select a slot. No new candidate TIFF was generated.**
This is a fail-closed result, not an inability to complete a safe step. The
standing protocol's literal uniqueness gate has a measured universal blocker:
the registered witness is positive on every valid cell of the pinned mirrored
footprint, so any nonempty in-footprint candidate has 100% directed positive-
support overlap with that witness at zero distance. That exceeds the stated
70% stop. The measurement is recorded in
[`evidence/registry_witness_recheck_2026-10-27.json`](../evidence/registry_witness_recheck_2026-10-27.json);
it is not a score, not a complete current registry audit, and the mirror is not
authenticated as an organizer download. In addition, the protocol's referenced
“single method paragraph” is not identified in the repository or supplied task.
It would be unsafe to invent an assigned lane.

No weekly submission slot was used. There is no comparable HOLDOUT-DTI for a
new candidate, no new leak-canary result, no new surface/final-dot audit, no
candidate SHA-256, and no submission-ready TIFF. The existing historical TIFFs
remain research artifacts. A format test or historical owner report cannot
replace the required release gates or an organizer receipt.

## GEMSDOE32: what can and cannot be inferred

The pinned GEMSDOE32 B2 mask is documented as a subset of the GEMSDOE28 H27-4
mask, with pixels removed near the mirrored mapped-fault layer. This supports a
construction-level explanation: pruning near known traces can lower false
positive mass while retaining some coverage under a distance-tolerant metric.
It does **not** establish that pruning caused the owner-reported leaderboard
value, because the actual upload-to-bytes receipt and hidden labels are absent.
It also does not establish that the method will outperform a holdout baseline.
The executive summary correctly leaves a new-submission estimate “not
estimable”; do not convert the historical claim into a forecast.

The prompt contains inconsistent, time-dependent headline leaderboard values.
The repository's latest timestamped public observation is stale and this
sandbox's network allowlist does not permit a live DrivenData fetch. Therefore
none of those figures is presented here as a current observation or as a score
for a repository candidate. Refresh only through the existing audited feed when
its configured source is reachable; retain the timestamp and stale status.

## Prospective hypotheses for a future, authorized lane

These are research proposals, **not executed experiments, viable candidates,
novelty claims, or score forecasts**. Qualitative rank expresses reasoned
priority only. Similar approaches exist in the repository and peer ledger, so
novelty must be checked against exact implementations before selecting a lane.
Because the current literal duplicate stop occurs before surface construction,
none may be implemented until the registry definition is explicitly reconciled
and a lane is assigned.

| Priority | Layers and physical signature | Why it might find an uncatalogued fault | Main non-fault mimic | Difference / cost / data status |
|---|---|---|---|---|
| 1 | Cached magnetic RTP and gravity anomaly: compare signed cross-edge profile asymmetry at multiple scales and require along-strike repeatability. | A buried dipping structural boundary may persist in potential fields where the surface scarp is subdued or covered. | Dipping lithologic contact, remanent magnetization, or survey striping. | Distinct from simple gradient unions by testing signed profile shape and repeatability; related potential-field work already exists. Medium cost if the pinned stack is available. Official source lead: [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and). Live source and tile-level availability were not verified in this session. |
| 2 | Bare-earth elevation and drainage profiles: detect a common signed knickpoint/offset across independent catchments, conditioned on valley orientation and rejected when explained by local channel geometry. | Repeated displacement across separate channels is less dependent on an exposed scarp and could reveal a concealed structure. | Resistant strata, lake shorelines, base-level change, or human channel modification. | Moves from scarp magnitude to replicated cross-catchment evidence; related geomorphic/scarp work exists. High cost because raw DEM/hydrography acquisition and coverage must be verified. Official source lead: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program); obtainability for this exact footprint is unverified. |
| 3 | Geodetic dilation/shear plus seismicity intensity: extract anisotropic lineaments aligned with local strain, test stability across scales and withheld spatial blocks. | A structure with microseismic expression and no clear surface rupture could be absent from the mapped-fault catalogue. | Mining/blasting, event-location artifacts, or broad regional strain unrelated to a mapped fault. | Tests directional cross-layer alignment rather than raw seismicity proximity; related strain/seismicity lanes exist. Medium cost if the official INGENIOUS assets are available. Source lead: [DOE GDR submission 1391](https://gdr.openei.org/submissions/1391); current endpoint, coverage, and data terms were not rechecked here. |
| 4 | Thermal probes and well/spring temperatures plus surface thermal-conductivity/radiometric context: estimate sampling-density-adjusted local thermal residuals and test alignment with independent structural evidence. | Advective heat transport may reveal a concealed fluid pathway even where geomorphology is weak; use only as corroboration for fault localization. | Groundwater flow, climate/seasonality, lithology, solar exposure, and biased well placement. | Extends pointwise temperature evidence into a sampling-aware residual, but geothermal-proxy work already appears in the peer ledger. High cost; new external data and bias controls required. Source lead: [DOE GDR submission 1391](https://gdr.openei.org/submissions/1391); obtainability and footprint coverage were not verified in this session. |

These proposals do not say that a predicted fault is a geothermal vent. The
competition target is fault geometry; geothermal process evidence is at most a
potential covariate. Official references are supplied for review, but the
network restriction prevented live verification of their current contents in
this session. Do not call an external-data hypothesis viable until files,
coverage, provenance, license, and permitted use have been checked.

## Three review passes

1. **Pass 1 — repository and evidence review:** read the standing brief and
   session handoff; checked the current release gate, run cards, focus-site
   summary, registry-witness evidence, and site pages. Confirmed that the
   authority is `DO-NOT-SUBMIT`; found no current authorization for a new lane.
2. **Pass 2 — implementation/test review:** made no model or TIFF changes
   because the pre-placement stop is dispositive. Created an isolated virtual
   environment using the repository requirements; restored the pinned shared
   template. `scripts/check_site.py` passed. Full test suite: **227 passed**;
   72 Rasterio pending-deprecation warnings. No experiment was counted or
   submission slot used.
3. **Pass 3 — requirement re-check:** verified that the executive summary
   distinguishes historical reports from estimates, that current download links
   mark existing TIFFs research-only, and that the root dashboard says no file
   is cleared. Rechecked that no new score, unique candidate, or portal
   acceptance is claimed. Existing lane cards contain historical positive
   language, but the current root release gate remains negative and supersedes
   those lane-level claims for release decisions.

## Next work / blockers

1. Resolve the contradictory lane instruction and define, in writing, whether
   the universal full-footprint raster is included in the literal dot-overlap
   comparison. Do not silently exempt it: changing that definition changes the
   user's protocol. Until resolved, candidate construction cannot satisfy the
   literal overlap gate.
2. Restore an authenticated current sample, catalogue, feature stack, labels,
   cached spatial folds, and complete up-to-date registry; mirrors currently
   prove byte identity only. DrivenData data and submission pages require
   account access, and their quota/receipts are unavailable here.
3. Reconcile the official outside-footprint encoding with the shared writer and
   obtain portal evidence for the prior `[0, 1]` error. The rejected bytes are
   not available, so its cause is unknown.
4. Once gates are feasible and a lane is assigned, reuse the shared evaluator,
   writer and cached stack; run all single-feature canaries, whole-segment
   buffered hide-and-recover with fold-local catalogue features, a paired
   spatial-block confidence interval, and surface plus final-dot registry
   checks. Only a separate selector may consider a slot.
5. Refresh the public leaderboard through the audited feed when reachable.
   Store timestamps and distinguish public leaderboard observations from
   organizer receipts; do not infer a new candidate's score from peer claims.
