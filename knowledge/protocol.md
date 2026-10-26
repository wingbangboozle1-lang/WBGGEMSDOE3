# Release protocol and limitations

1. Read README and the user's task requirements first. Confirm the method lane
   exists; do not infer it from a generic request for novel methods.
2. Restore a provenance-checked template, footprint, catalogue, cached features,
   physical channel dictionary, whole-segment identifiers, buffered spatial
   folds and a complete registry of rasters including calibration/null entries.
   Hashes prove integrity against a mirror, not official authenticity.
3. Before placement, compare the candidate surface to **every** registry raster
   using Spearman rank correlation on the common footprint. The literal stop
   rule is correlation >0.90 or directed dot overlap >70% within 3 pixels.
   No exemption for a dense lattice is authorized. A threshold failure is a
   duplicate stop, not a parameter-tuning opportunity.
4. For hide-and-recover, withhold whole segments plus a buffer, remove them from
   every catalogue-derived feature and fitting input, and reconstruct all such
   features using visible faults only. Pixel-mask visible traces in evaluation.
   Keep footprints/regions identical for every arm. Check kernel-boundary
   effects and component tails. A static prediction from full-catalogue
   exclusions is not a compliant holdout result.
5. Run each feature alone on the same holdout. AUC >0.90 is a leakage canary
   until explained; record positives, negatives, masks, folds and CI. Below
   threshold does not prove absence of leakage.
6. Use shared `gems57-pooled-hide-v2` evaluator; pool metric components first.
   Report HOLDOUT-DTI, evaluator hashes, withheld positive count and spatial
   cluster bootstrap 95% CI. Compare paired to the incumbent on identical folds.
   Required promotion policy: candidate beats the current comparable holdout
   best and paired improvement's lower CI bound is positive. This conservative
   gate does not turn a surrogate into a hidden-test estimate.
7. After placement, repeat all-registry correlation/overlap, hash exact TIFF
   bytes, run finite/range/single-band/CRS/shape/transform checks. Never silently
   clip or fill invalid model output. All-finite release avoids NaN/nodata form
   ambiguity. A valid TIFF can still score poorly or be a duplicate.
8. A separate selector approves a weekly slot only after reading the actual
   current submission-page cap and usage. Neither is available here. No upload
   automation or submission credentials are included.
9. Stop after three experiments or two hours. Negative results are retained.
   This review ran no new geological experiment and no slot was used. The
   merged base contains an earlier 35,000-dot H_STEP-OVER TIFF; the current card
   reviews it as an existing artifact, not a new run. A commit-pinned owner-mirror
   recheck measured 97.87% of all its dots within 3 px of the registered lattice,
   failing the >70% stop rule. The mirrors are not organizer-authenticated. No
   data-free score exists.

## Shared-tool irregularity

Peers do not all use the same template. GEMSDOE36 pins GEMSDOE24; GEMSDOE31
pins 57GEMSDOE. This checkout restores the latter byte-for-byte at commit
822a0ce5546c7b6749cdd82eb145b6b3e616603d, using GEMSDOE31's hash manifest.
No shared code was fixed or forked. This restoration is an auditable API base,
not evidence that a lane was assigned or that the cache was recovered. A real
run must reconcile which instrument the parallel lanes share before comparison.

## Access limits

Outbound network hosts are limited to GitHub and Python/npm package registries.
DrivenData, Dropbox, USGS, GDR and PDF hosts are not directly accessible here.
There are no competition data or saved folds in the checkout. An upstream
GEMSDOE32 manifest identifies a 418,912,844-byte numerical-stack owner mirror
on GitHub, so data are not universally unobtainable; it is not downloaded
without the missing lane and cache contract. Labels/template mirrors are also
listed there. Cached stack paths in upstream receipts refer to that repo's
local filesystem, not files available here. No verified full registry inventory
or organizer score receipts were restored. Compute requirements cannot be
established before a method is selected; the official reference supports CPU.
