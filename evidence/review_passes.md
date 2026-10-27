# Three-pass repository review — 2026-10-27

## Pass 1 — inspect requirements and evidence

- Read `README.md`, `AGENTS.md`, the preregistration, irregularity register, scientific review, and the current run card before changing code.
- Reviewed the nine requested site artifacts and the executive dashboard. Their score figures are owner-reported historical claims, not organizer receipts; no calibrated leaderboard estimate is available.
- Rechecked the pinned registry witness described in `evidence/focus_audit.json`: under the shared finite-positive support definition it is positive at every cell of the mirrored sample footprint. Thus every nonempty in-footprint dot set overlaps that witness at distance zero and exceeds the literal overlap threshold. The mirror is hash-pinned but not independently authenticated as an organizer download.
- Reviewed the H33 B2 raster comparison: its decoded positive support is a subset of the H27-4 reference, with near-catalogue pixels removed and none added. This documents a raster operation, not a causal explanation of the unreceipted score claim.
- No surface, candidate, holdout, feature canary, or submission was run. The mandatory duplicate stop precedes experiments; no weekly slot was used.
- The repository's public leaderboard observation is dated 2026-10-26 and is stale for this review. No fresh attributable public page was fetched, so conflicting user-supplied leaderboard figures were not reconciled.

## Pass 2 — code and assumptions review; fixes

- Found `scripts/restore_shared_data.sh` invoked a missing `scripts/restore_shared_data.py`. Added the missing driver to verify the pinned shared template and delegate data restoration to its own `scripts/prepare_data.py`; `--template-only` and `--dry-run` avoid fetching data. The bridge remains a peer mirror, not official provenance.
- Found the local read-only preflight helper applied a one-sided rank-correlation stop despite the project rule specifying absolute Spearman correlation. Changed it to `abs(rho) > 0.90` and added a negative-correlation regression test.
- Found the historical LST1 path could mark `ready_to_submit=true` while its own evidence recorded `U3_literal_pass=false`, because it substituted a lattice-null exception. Updated its finalizer to require the literal gate and complete registry scope; retired both the old candidate builder and the lattice-exempt independent verifier. The run card now says `NOT_ESTIMABLE` and omits the projection values; the raw build diagnostic stays in the evidence archive, unlinked from the current-facing subsite. The TIFF remains research-only.
- The vendored shared template itself still contains the documented one-sided rank gate and is read-only to this integration. No private fork or local patch of the shared package was made. The independent audit continues to apply the two-sided rule; an upstream maintainer must correct the shared tool.

## Pass 3 — acceptance review and remaining work

- The current authoritative card remains `evidence/run_card.json`: verdict `negative`, no raster SHA, no candidate, no selector approval. The requested high-scoring unique TIFF was **not** produced because the literal rule makes every nonempty candidate fail. Do not download or submit any historical or parallel TIFF as a new submission.
- The main dashboard distinguishes historical owner claims from actual estimates, shows “Not estimable” for leaderboard projection, and marks every requested historical file “DO NOT SUBMIT.” The LST1 subsite now shows a permanent DO NOT SUBMIT banner, suppresses the old projection range, identifies legacy HOLDOUT-DTI correctly, and offers only research-labeled downloads; it is not an approved alternate route.
- A prior LST1 run card and page used nonliteral uniqueness exceptions and contained a projected score range. Those outputs are historical research only and are superseded for current decisions. Do not use that projection or old `ready_to_submit` field as a score or approval.
- A current spatially blocked HOLDOUT-DTI was not run in this review: there is no eligible lane after the duplicate stop, and the prescribed experiment budget is not permission to bypass a mandatory stop. No new performance number is claimed.

### Reproduction and checks

Verified after the changes:

- `.venv/bin/python -m pytest -q` — **90 passed**, 38 existing Rasterio warnings.
- `.venv/bin/python scripts/build_site.py && .venv/bin/python scripts/check_site.py` — **4 pages built; required pages, local links, and negative status PASS**.
- `bash scripts/restore_shared_data.sh --template-only` — pinned template verified; no data fetched.
- `bash scripts/restore_shared_data.sh --dry-run` — printed the upstream `prepare_data.py --fetch --cache-bands` command; did not execute it.
- `.venv/bin/python scripts/finalize.py` — historical card reclassified: literal overlap and registry-scope gates FAIL; current evaluator, current-file validation, and selector are unavailable/false; `ready_to_submit=false`; verdict NEGATIVE. No raster was written.

Full `bash scripts/restore_shared_data.sh` fetches the pinned public bridge and 19 ignored band caches. Do not mistake its successful SHA checks for organizer authentication. No new candidate generation or model evaluation is authorized until the literal registry conflict is explicitly resolved.

### Open limitations / handoff

1. A protocol owner must clarify whether continuous, full-footprint probability rasters count as registry “dots.” Any exception changes the current literal rule and must be explicit and preregistered; do not silently adjust support, scope, or thresholds.
2. The shared uniqueness package's signed-rho defect and the sample's outside-footprint convention need upstream/organizer resolution. This integration cannot modify the shared repository.
3. DrivenData training data, hidden labels, account quota, and submission-page receipts are unavailable here. Public score snapshots are timestamped observations only.
4. Only after the policy blocker is resolved should the preregistered single lane run feature-only leakage canaries and buffered whole-segment recovery with the shared evaluator, then use the unchanged shared writer and a separate slot selector.
