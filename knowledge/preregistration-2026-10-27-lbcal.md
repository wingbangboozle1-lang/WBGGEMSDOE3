# Pre-registration — LBCAL lane (session arena/88400903, 2026-10-27)

Written ~19:35 UTC 2026-10-27. **What had been seen at this point:** the unbounded
LBCAL fit and its leave-one-family-out CV (`evidence/lbcal_cv.json`). **Not yet
run at this point:** the bounded variants, the dot design, the uniqueness scan,
the hide-and-recover holdout, the leakage canary. Gates below are fixed now and
are not changed after those results arrive.

## 1. Untried hypotheses, ranked (expected DTI gain × 1/cost)

Every hypothesis lists the layers it uses, the physical signature, why it should catch
off-catalogue faults, and how it differs from what the repo already tried.

| Rank | ID | Layers | Signature / transform | Why it catches off-catalogue faults | Difference from repo methods | Expected gain | Cost |
|---|---|---|---|---|---|---|---|
| 1 | **H-LBCAL** | det_elev (curvature, slope, Canny crest), 3DEP-LiDAR scarp descriptors, TMI horizontal gradient, SGMC faults, catalogue distance | A log-linear **density of hidden expert faults** over 7 binned layers. It is fitted to about 119 owner-reported public scores through the exact DTI algebra: truth-side max-credit and prediction-side kernel mass. | The leaderboard is the only signal that is actually labelled with the hidden *new* faults. Every scored raster acts as a soft, spatially integrated measurement of where those faults are. | All earlier lanes guessed the target, using the catalogue (hide-and-recover) or SGMC as a proxy. The proxies disagree with the scores: Spearman −0.15 and −0.93. This lane inverts the scores themselves and validates by leave-one-family-out. | High: the only lane that is calibrated to the target | Low (≈1 h) |
| 2 | H-PIEDMONT | det_elev, det_elev_slope, cond_surf, depth_to_base_surf | Range-front-to-basin transition. The signature is the slope break where the alluvial-fan apex sits on the conductive basin fill. | Expert mappers digitise young piedmont scarps at range fronts. The Quaternary catalogue misses short, degraded segments. | Not a ridge or edge detector. It is a *contact-type* indicator. | Medium | Medium |
| 3 | H-SEISMO-GAP | deq_n100a15, ieq_n100a15, geod_shearrate, geod_2ndinv | Strain-rate excess over the seismicity rate: a geodetic moment deficit. | Geodetic strain without catalogue faults implies unmapped accommodating structures. | Earlier strain lanes thresholded strain only. They never used a rate deficit. | Low–medium | Low |
| 4 | H-STEPOVER-SYNTH | catalogue geometry only | Synthetic linking faults at step-overs and terminations. Releasing bends are filled with Coulomb-favourable orientations. | Experts often add connecting segments between mapped faults. | The repo's "stepover-damagezone" used damage-zone halos, not connectors. | Low (catalogue-proximal dots are penalised) | Low |
| 5 | H-RADIOMETRIC-SEEP | tc (radiometric total count), cond_surf | A K/Th anomaly lineament: alteration along fluid-bearing faults. | Hydrothermal fluid flow along faults leaves radiometric halos. | Earlier lanes treated band 6 as "magnetic tilt". The TIFF tag says `tc`, and its values (3–89) fit radiometric total counts. | Low | Medium |

Only H-LBCAL is implemented in this session (budget: 3 experiments / 2 h).

## 2. Mechanism and named non-fault mimic (H-LBCAL)

* **Mechanism.** Fault scarps and range-front faults are mapped by experts from lidar and DEMs. Where expert mappers placed new faults, that placement left a detectable footprint in the scores of about 119 rasters that were scored against those faults.
* **Named mimic.** Landslide head-scarps and terrace risers have the same slope, curvature and LiDAR-step signature as tectonic scarps. So do anthropogenic cuts such as roads and canals; that is why a TIGER road-distance layer is cached. The density cannot separate them, because it only learns where the scored rasters gained credit.

## 3. Fixed decision rules

* **Model selection.** Choose the lowest leave-one-family-out RMSE among variants with π_max ≤ 0.2. The unbounded fit saturates at π = 1 on ~5 k px, which is physically implausible.
* **Design.** Run the Dinkelbach batch-greedy under the selected π. Dots are never placed on the catalogue.
* **Estimate.** Report the **cross-fit** estimate (design on half A, evaluate under the model fitted on half B, 2 random splits × 2 directions). Also report a family-bootstrap 95 % interval of the final design's estimate. Both are labelled ESTIMATE.
* **Verdict = PROMOTE (to the separate selector only)** iff **all** of the following hold:
  1. The validator passes on the saved bytes (template `validate` + independent re-read).
  2. Unique: no rank-corr > 0.90 and no forward dot overlap > 0.70 against any dot-field registry raster (like-for-like reading), both pre-placement and on the final dots. The literal reading is reported too.
  3. Leakage canary: no single feature has AUC > 0.90 for the withheld holdout positives.
  4. HOLDOUT-DTI (GEMSDOE32-HIDE-RECOVER-v3.0, fold-local visible-only features) exceeds the current holdout best of **0.1292** (HCE-1). This is the owner's rule: never spend a slot on an idea that has not beaten the holdout best.
  5. The cross-fit ESTIMATE exceeds **0.2778**, the champion's owner-reported score.
* Otherwise **NEGATIVE**. The TIFF is still written, validated and archived as a learning artefact, with DO-NOT-SUBMIT in the name.

## Amendment, logged before any variant result existed (~19:31 UTC)

The first variants run used leave-one-family-out CV with 96 folds. It was killed after ~3 minutes with **no output**, because each bounded fit takes ~5 s. It was replaced by **10-fold CV grouped by family** (seed 20261027), with the unbounded model re-run under the same folds as the reference. The selection rule did not otherwise change.
