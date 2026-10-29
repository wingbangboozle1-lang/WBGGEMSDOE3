# Repository review — 2026-10-29

## Decision

**DO NOT SUBMIT. No candidate TIFF was generated, validated, or selected.** The 2026-10-28 project-wide gate remains active. After this review's first commit, `main` advanced with PR #59 and added a reproducible witness-definition measurement: the registered comparator is a soft-probability surface, so interpreting every positive finite value as a discrete “dot” makes its 100% support a definition artifact. The new measurement does not itself change the protocol or authorize candidate construction; the associated review explicitly leaves the gate closed pending a documented protocol decision. This review performed source-feed/site engineering and software tests only. It did not run a geological experiment or holdout, spend a submission slot, or attempt a portal upload.

This review supplements, and does not rewrite, the 2026-10-28 preregistration, run card, or release gate. Historical scores in the nine-site table remain owner/user reports, not organizer receipts. “Estimated score” remains “Not estimable”; no score projection is justified by this review.

## Three review passes

### Pass 1 — inventory and evidence review

- Read the repository's working agreement, reconstructed task brief, README, release protocol, current negative run card, preregistration, registry-witness evidence, official-source audit, current site builder/checker, and the nine-site evidence table.
- Confirmed that the requested nine sites are already represented in the executive summary, with immutable historical artifact references, owner-reported score labels, no score estimate, a within-focus-site overlap measurement, and a clear **DO NOT SUBMIT** decision.
- Refreshed the GitHub source-identity monitor for the nine focus repositories. All **9/9** requests succeeded; each site's current `main` head differs from the repository's 2026-10-26 baseline. This is a source-change signal only: it does not show that a particular score or TIFF changed, nor that an owner report is a competition receipt. Machine record: [`evidence/latest-upstream-check.json`](../evidence/latest-upstream-check.json).
- A current GEMSDOE32 source tree contains an owner-generated focus rescore record dated 2026-10-29, but that record is not a DrivenData receipt and is not part of this repository's independently replayed shared-tool evidence. It does not establish the current highest submission across the nine sites. No claim from that file is promoted to a project score here.
- Concurrent main update (PR #59): the pinned registry raster was remeasured and confirmed as soft probability, with 5,167,373 positive finite cells, 728,137 cells above 0.5, and a top-37,654 threshold of 0.843843. This supports that the prior 100%-overlap blocker depends on defining every positive probability value as a “dot.” It does not authorize changing the user protocol; the main-branch review keeps the release gate negative pending an explicit documented protocol decision. See [`evidence/witness_definition_check_2026-10-29.json`](../evidence/witness_definition_check_2026-10-29.json) and [`knowledge/session-review-2026-10-29-witness.md`](../knowledge/session-review-2026-10-29-witness.md).
- Identified a product gap: the Pages workflow refreshed `evidence/latest-upstream-check.json`, but the active builder did not copy or display it. Therefore visitors could not see that all nine source repositories had advanced.

### Pass 2 — bug/assumption review and repair

- Updated `scripts/build_site.py` to require a structurally complete, explicitly non-authorizing nine-site source-identity report, copy that exact JSON to the published site, and display its checked time and checked/changed/unknown counts on the homepage.
- Added explicit language that source-head changes are not score, TIFF, receipt, or registry validation. The new panel does not affect candidate status or bypass the release gate.
- Updated `scripts/check_site.py` and `tests/test_site.py` to enforce source-report completeness, exact equality between source and published JSON, the visibly caveated homepage panel, and never-authorize semantics.
- Rebuilt the site. The generated nine-site executive table still presents no score estimate and no download-as-submission link. The negative release gate remains unchanged.

### Pass 3 — full recheck

- `scripts/check_site.py`: PASS, fail-closed negative decision, hash-bound evidence, no candidate links, and local links resolve.
- `pytest`: **237 passed, 4 skipped**. The 72 warnings are existing Rasterio `Affine` pending-deprecation warnings (not test failures).
- JSON parsing of both the source and published upstream reports: PASS.
- A run without pytest installed initially failed because the system Python is externally managed. A local ignored `.venv` was created and dependencies installed from the declared `requirements.txt`; no environment files were added to Git.
- No geological holdout was run: the repository's active duplicate stop bars feature construction/placement. No new candidate score, confidence interval, TIFF hash, or validator result exists.

## Current status and limitations

1. **All nine focus-source repositories changed after the checked 2026-10-26 baseline.** The immutable references in the existing comparison remain valid for the files they pin, but they cannot be treated as a current census of each site's candidates. Re-audit current site artifacts and receipts before updating the “best submission” rows.
2. **No verified score for the reported GEMSDOE32 0.2778.** Its recorded byte/support relationship can motivate a hypothesis, but cannot establish why the hidden evaluator awarded that score. The observed public-leaderboard maximum in the repository is a dated 2026-10-28 observation, not a current fetch and not a score for these site files.
3. **No new unique TIF is approved.** Main-branch evidence shows the dense witness is a soft-probability surface, so its universal overlap under the all-values-greater-than-zero rule is definition-dependent rather than candidate-specific. The release gate nevertheless remains DO NOT SUBMIT: the user protocol's intended dot definition has not been formally reconciled with the registry comparator, prior candidate-specific uniqueness audits identify other dense/lattice comparators, and no shared holdout or portal-format clearance exists. Do not silently change definitions or construct a candidate while the recorded gate remains closed.
4. **Competition data and portal state remain unavailable here.** The DrivenData data and submission pages require login, no authenticated user data/receipt/quota are available, and the sandbox's outbound-host policy does not permit direct requests to DrivenData. The public GitHub source monitor works, but is not a substitute for a live official leaderboard or a complete raster audit.
5. **Hypotheses remain prospective.** The existing five preregistered hypotheses and their named mimics/costs are ranked qualitatively; there is no defensible DTI projection or fresh `HOLDOUT-DTI` from this review.

## Next work, in order

1. Reconcile the user's “dots” overlap rule with the continuous-probability registry entry in a versioned protocol update; keep the gate closed until that definition is authorized and the full comparator set is re-audited. Independently authenticate reference/template/registry provenance.
2. Reconcile the current changed site heads against immutable artifact bytes and any actual submission-page receipts. Keep public claims, owner reports, holdout scores, and organizer-confirmed scores in separate evidence classes.
3. Restore the common pinned cache and shared holdout/writer runtime only after lane assignment and eligibility are documented. Then run the leakage canary and spatially blocked holdout under the preregistered protocol, within the three-experiment/two-hour budget.
4. Have a separate selector read the live portal cap and review any promoted candidate. No weekly slot is selected by this research lane.
5. Watch the official site for the deadline discrepancy already documented in the source audit. The Pages workflow can refresh the public leaderboard when its hosted runner can reach DrivenData; a failed attempt must remain explicitly stale.

## Reproducible verification commands

```bash
.venv/bin/python scripts/refresh_upstream.py
.venv/bin/python scripts/build_site.py
.venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q
```
