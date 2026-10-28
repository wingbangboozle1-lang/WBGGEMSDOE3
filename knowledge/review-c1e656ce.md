# Repository review — 2026-10-28

**Decision: DO NOT SUBMIT.** This was a repository, evidence, and release-path review only. It produced no new geological experiment, candidate surface, dot set, GeoTIFF, holdout result, upload, or slot selection. The machine-readable record is [`evidence/session_c1e656ce_run_card.json`](../evidence/session_c1e656ce_run_card.json); the generated [latest-review page](../docs/session-review.html) and [release gate](../docs/data/release_gate.json) are the publication copies.

## Review passes

1. **Authority and completeness:** reconciled the current release/candidate cards, prompt and operating protocol, nine-site evidence, generated pages, tests, and publishing entry points. The authoritative gate is negative (`gems-release-gate-v1`, nine blockers). The requested single method paragraph is not identifiable in the available materials. Only the template raster is present; the authenticated competition stack, labels, sample submission, segment IDs, and saved buffered holdout cache are absent.
2. **Evidence, assumptions, and failure modes:** checked the GEMSDOE32 0.2778 claim, the nine named sites, pair arithmetic, the literal uniqueness rule, the mirrored witness, historical download paths, and the prior [0,1] portal rejection. The 0.2778 remains `OWNER-REPORTED` without a receipt. The byte-level pair audit finds 37,654 positive H33-B2 cells are a subset of the 40,199-cell H27-4 support; 2,545 cells were removed at measured distances of 1.414–2.000 pixels from the mirrored catalogue. This supports a possible catalogue-collar precision trade-off, not score causality or a future score.
3. **Implementation and recheck:** performed one read-only, hash-pinned public-mirror witness recheck; rebuilt the fail-closed site; checked current pages, links, evidence hashes, download notices, retired positive generators, and published JSON decisions; then ran the full repository test suite. The local witness raster is positive on 5,167,373/5,167,373 mirrored-footprint cells. Conditional on those mirror bytes and the recorded support rule, any nonempty in-footprint candidate exceeds the literal 70% directed-overlap stop. This is not an authenticated organizer registry or proof of complete registry coverage.

## Verification

- `scripts/build_site.py`: PASS.
- `scripts/check_site.py`: PASS.
- `python -m pytest -q`: **236 passed, 4 skipped**; 72 existing Rasterio `PendingDeprecationWarning`s about Affine multiplication; no test failures.
- Positive stale publisher outputs are blocked or marked historical. The old KHD `SUBMISSION-READY` JSON is replaced with an explicit negative archive record. Historical TIFFs remain research-only; a local format diagnostic does not establish portal acceptance.
- No candidate-specific holdout, leakage canary, correlation, final-dot overlap, current raster hash, or validator result exists. Those fields are correctly null/NOT RUN in the run card. No geological experiment or competition slot was consumed.

## Unresolved blockers

The mirrored registry witness is a conditional stop that must not be waived silently. Authenticated competition inputs and the shared buffered holdout cache are unavailable; the assigned method paragraph is unidentified; and the exact rejected upload bytes/receipt needed to diagnose the portal's `[0, 1]` error are absent. Do not generate a cosmetic TIFF or represent the prior research downloads as unique, accepted, or submission-cleared. If prerequisites and the literal registry stop are resolved through an authorized decision, resume with the shared evaluator/writer and the separate selector.
