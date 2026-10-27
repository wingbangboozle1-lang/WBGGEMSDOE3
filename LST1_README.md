# LST1 archive — research only, DO NOT SUBMIT

This historical lane does **not** provide a unique or cleared competition file.
The authoritative current decision is the [negative run card](evidence/run_card.json),
not the superseded LST1 readiness assertions. No candidate was generated and no slot
was used during the current audit.

## What was independently checked

On 2026-10-27 the saved LST1 zero-outside and NaN-outside TIFFs were read against the
pinned public-mirror sample and registered 17GEMSDOE witness. Both contain 32,810
positive cells, all inside the mirrored footprint, and **100%** of those cells overlap
the witness at distance zero, thus exceeding the >70% stop. Both are single-band
float32, EPSG:32611, match the mirror's 3,730 × 3,292 grid and transform, contain no
NaN/inf inside and have in-footprint range [0, 1]. The zero-outside ZIP passed its CRC
check and its one member's hash matches the TIFF. [Exact hashes and all checks](evidence/archive_audit.json).
The sample is a hash-pinned owner mirror, **not authenticated as an organizer download**.
The all-finite zero convention and NaN-outside convention have not been reconciled
with the organizer's wording or portal behavior; neither is asserted to be accepted.

The files remain under `submission/` for provenance and education only. Their former
unique/readiness labels and the independent verifier's PASS are **superseded**: the
previous audit excluded or adjusted registered dense references without authorization.
The copy once published on the LST1 Pages microsite has been withdrawn from that site;
the [archive notice](docs/lst1/index.html) links to the repository for inspection.

## Historical performance is not a validated improvement

The former local report labels a result HOLDOUT-DTI (`GEMSDOE32-HIDE-RECOVER-v3.0`,
22,232 withheld positives): candidate 0.06668 [0.05688, 0.07655], comparator proxy
0.09920 [0.08595, 0.11267], paired difference −0.03252 [−0.04103, −0.02372] (reported
spatial 95% CIs). **These are historical outputs, not independently established as
protocol-compliant**: the runner used a fixed H19-5-derived raster and D2.8 proxy;
binning and its canary used the complete catalogue, and the historical model's
training provenance may itself include withheld labels. Consequently those outputs do
not prove fold-local evaluation or support an estimated public/private score. The old
projection is not a score. See the [historical output](evidence/holdout_results.json)
and [current review](knowledge/review-and-irregularities-2026-10-26.md).

The generation, finalization, old site generator, and exemption-based checks have
been retired or rewritten to fail closed. Resolve the registry-support rule and
outside-footprint convention through an explicit upstream decision; then preregister
one lane, rebuild every catalogue-derived input within buffered whole-segment folds,
run the shared evaluator and writer, and obtain a separate selector decision. See
[README.md](README.md) for the standing instructions and current dashboard.
