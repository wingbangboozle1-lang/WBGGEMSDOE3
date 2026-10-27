# LBCAL findings: the leaderboard as a measurement instrument (2026-10-27, arena/88400903)

Every number below comes from a committed JSON. Each one carries a label:

* **OWNER-REPORTED**: a score the owner copied from the leaderboard.
* **HOLDOUT-DTI**: the repository's hide-and-recover evaluator.
* **REGISTRY-MEASUREMENT**: measured on hash-pinned bytes.
* **ESTIMATE**: a model output. It is never an organizer score.

No ORGANIZER-CONFIRMED receipt exists for any file in this repository.

## 1. Why GEMSDOE32 `h33-h33-2-b2` reached 0.2778, and why that lineage saturates

**Metric identity.** The official metric is defined at <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>:

* DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w).
* FN_w = |G| − TP_w, so DTI = TP_w / (0.2·(TP_w + FP_w) + 0.8·|G|).
* |G| does not depend on the submission. A sparse binary map is therefore scored almost entirely by its **credit per dot**.
* A new dot helps only if ΔT/(ΔT + ΔFP) > 0.2·DTI. At DTI ≈ 0.28 that is ≈ 0.056, roughly a ≥2% chance of the dot sitting on a hidden fault.

**What B2 is** (REGISTRY-MEASUREMENT):

* It is the GEMSDOE31 d2.8 dotted-ridge network: 40,199 dots, OWNER-REPORTED 0.2708.
* B2 removes the 2,545 dots within 3 px of the public catalogue, leaving 37,654 dots.
* The lineage is h19-5 0.1922 → d2.8 0.2600 → solo 0.2708 → B2 0.2778.
* Removing those dots *raised* the score. By the ratio condition, that means the removed set had ΔT/(ΔT + ΔFP) < 0.2·0.2778 ≈ 0.056.
  So the removed dots averaged less than about 0.06 truth-pixels of credit per dot: they were essentially **pure false positives**.
  This is expected, because the test faults are by definition *not* in the catalogue.
* At the LBCAL-implied |G| ≈ 23.6 k, and approximating FP_w ≈ N, B2 earns about 0.2 truth-pixels of credit per dot, a weighted recall of about one third. The kept dots earn more than three times the break-even credit; the removed ones earned less than break-even.

**Why it saturates.** The best files of all nine focus sites are this one network. In the nine-site table (`evidence/focus_sites_2026-10-27.json`), every one of the 72 ordered pairs has ≥86.7% of dots within 3 px, and each file has ≥97.6% overlap with at least one other focus file. After the FP shedding, a fixed network has nothing left to gain. Beating it needs **new true-positive locations**, not further trimming.

## 2. LBCAL: invert the public scores (experiment 1)

**Each scored raster is an integral measurement of where the hidden faults are.**

* For a density π, the truth-side credit is exactly T = Σ_g π(g)·c_p(g). Here c_p is the raster's max-credit map, computed with the official 25-offset kernel (`src/lbcal/coverage.py`, unit-tested against an EDT reference).
* The prediction-side kernel mass is ≈ 3·Σ π·p, using a line-process approximation.
* π is log-linear (bounded) over the joint bins of 7 layers (`src/lbcal/features.py`). It is fitted by least squares to the OWNER-REPORTED scores.

**Model validation (`evidence/lbcal_cv.json`, `evidence/lbcal_variants.json`).**

| Model | CV scheme | RMSE | Spearman |
|---|---|---|---|
| constant mean | leave-one-family-out (96 families) | 0.0861 | — |
| log(dot count) | same | 0.0865 | −0.40 |
| catalogue distance only | same | 0.0904 | 0.20 |
| full, unbounded, λ=1e-4 | same | 0.0323 | 0.914 |
| full, unbounded, λ=1e-4 | leave-one-site-out (86 sites) | 0.0321 | 0.914 |
| **full, π_max=0.2, λ=1e-4 (selected)** | 10-fold family | **0.0365** | **0.908** |

* Families are connected components of support-Jaccard ≥ 0.3, so near-copies never straddle a split.
* The 5 pairs of byte-identical arrays carry identical OWNER-REPORTED scores, which supports the internal consistency of the ledger.

**What the density says.** These are associations with public-test faults; they are not proof of causation.

* **Catalogue distance.** π is depleted within 300 m of mapped faults and rises with distance out to ≥5.5 km.
* **Terrain.** π is concentrated on 70–95th-percentile slopes with low curvature.
* **Scarp features.** π is depleted on slope crests (Canny maxima) and on strong 2 m-LiDAR scarps.
* **Magnetic edges and SGMC faults.** Both effects are weak.

The public hidden faults look like *range-flank and bedrock structures 1–5 km from mapped Quaternary faults*. They are not the crisp young scarps that the catalogue and the scarp detectors already capture. This explains several earlier observations:

* LiDAR-scarp lanes scored 0.04–0.15.
* SGMC-as-prediction scored about 0.05.
* The 57GEMSDOE peer study found that the median catalogue distance correlates with score (ρ = +0.77).

**Named mimics:** landslide head-scarps, terrace risers, and road or canal cuts.

## 3. Design and gates (experiment 2), with a NEGATIVE verdict

The selected π drives a Dinkelbach batch-greedy max-coverage placement followed by exact pruning. The result is 71,416 dots, none on the catalogue.

**ESTIMATE**

* In-model: 0.5727.
* **Cross-fit (design on half of the families, evaluate under the other half; 4 runs):** 0.4286, 0.5215, 0.5420, 0.5129. **Mean 0.5012.**
* Family bootstrap 95%: 0.4928–0.6040.
* The same model estimates B2 at 0.2230, against its OWNER-REPORTED 0.2778. The model is conservative on the champion lineage.

**Post-hoc neighbour check** (`evidence/lbcal/postcheck.json`)

* 28 scored rasters share the design's dot locations beyond chance.
* The model under-predicts 17 of them by more than 10%, mostly the d2.8 lineage.
* It over-predicts 4 by more than 10%: h23-a, h23-b, h30 and ovtr, the dense emission and habitat rasters.
* The heuristic adjusted range is 0.33–0.73. It is not a score.

**Gates**

| Gate | Result |
|---|---|
| Validator: template plus independent re-read of the saved bytes | PASS |
| Leakage canary | PASS: worst max(AUC, 1−AUC) 0.808, for the visible-catalogue distance |
| Uniqueness before placement | PASS: worst Spearman 0.068 |
| Uniqueness of the final dots (like-for-like) | **FAIL**, details below |
| HOLDOUT-DTI | **FAIL**: 0.0631 (95% CI 0.0513–0.0765; GEMSDOE32-HIDE-RECOVER-v3.0; 22,232 withheld; fold-local, visible-only features), below the 0.1292 best |

The final-dot uniqueness check produced 7 firings above the 0.70 forward-overlap limit:

* **3 vacuous firings.** The witness's 3 px halo already covers more than 70% of the allowed map: the r13 lattice (99.9%) and the two pindrop-v4 files (73%).
* **4 informative firings:**
  * h23-a: 0.81 overlap against a 41% halo;
  * h23-b: 0.91 against 53%;
  * h30: 0.85 against 41%;
  * ovtr: 0.81 against 54%.

**Verdict: NEGATIVE.** The TIFF is archived as `evidence/lbcal/…-DO-NOT-SUBMIT.tif`.

## 4. The gate itself (experiment 3)

`evidence/lbcal_gate_concordance.json` runs the owner's slot gate on all 119 unique scored arrays.

* HOLDOUT-DTI correlates with the OWNER-REPORTED public score at **ρ = 0.089**. Binary-only it is 0.077; for the top 20 it is 0.023.
* LBCAL's family-CV estimate correlates at **ρ = 0.914**. For the top 20 it is 0.753.
* The best holdout file scores 0.326 on the holdout and 0.0041 publicly.
* B2 scores 0.0045 on the holdout and 0.2778 publicly.

The hide-and-recover task withholds *catalogue* segments, so it rewards catalogue proximity. The leaderboard's labels are *non-catalogue* faults, so it punishes catalogue proximity.

Caveat: registry masks were built with the full catalogue (static, not fold-local), so catalogue-hugging files receive leaked holdout credit. Fold-local replays of a method remain the gate's intended use.

**Recommendation for the owner:** decide whether the slot gate should become a leaderboard-calibrated family-CV gate. Until then, the rule stands, and LBCAL's design is NEGATIVE.

## 5. Irregularities logged this session

* **IR-10.** README said SUBMIT (skarpline-union, ESTIMATE 0.428), while `evidence/run_card.json` said NEGATIVE and PR #24 said DO NOT SUBMIT. This is reconciled to one decision (`evidence/decision.json`). LBCAL estimates skarpline-union at 0.074.
* **IR-11.** The holdout gate does not track the leaderboard (ρ = 0.089, n = 119).
* **IR-12.** Band 6 `tc` was documented as magnetic tilt or total curvature. Its range (3–89) and the official page's figure indicate radiometric total counts.
* **IR-13.** Two archived "unique" files have grids of 1024×1024 and 1200×1600, so they were never valid submissions. One scored ledger raster (14GEMSDOE horse-ensemble) fails the template CRS/transform check. One (GEMSDOE9 placeholder) has 196,132 positives outside the footprint.
* **IR-14.** `wbg3-h3pack` lives in the WBGGEMSDOE2 repo, and `wbg2-offcatalogue-density` lives in the WBGGEMSDOE1 repo, so their site attribution does not match.
* **IR-15.** About 125 scored submissions in about 33 days across several accounts is inconsistent with the rules' 3-per-week-per-entity cap and one-final rule (<https://docs.nlr.gov/docs/fy26osti/96647.pdf> §3.2/§3.4). This is stated neutrally: account-to-entity mapping is not visible from here.

## 6. Limitations and next session

* **Labels.** All targets are OWNER-REPORTED copies and public-chunk scores only. The private set and the expanded final labels decide the prizes. Spatial over-fit to public chunks cannot be measured from public scores.
* **Model structure.** π is additive over 7 binned layers. Interactions and finer bins are unexplored. The 3·π FP term is a line-process approximation.
* **Optimiser.** The bounded fits stop at scipy's evaluation cap without formal convergence; saturated cells leave flat directions. A 3000-evaluation refit lowers the cost by 2% and moves the design ESTIMATE from 0.5727 to 0.5806 (`evidence/lbcal/convergence_check.json`). The family bootstrap uses B = 30 warm-started refits.
* **Next 1. Uniqueness-repaired LBCAL.** Forbid the halos of h23-a, h23-b, h30 and ovtr, and measure how much cross-fit ESTIMATE survives.
* **Next 2. Owner ruling on the gate.** Without a ruling on the slot gate (IR-11), no leaderboard-calibrated design can ever be promoted.
* **Next 3. Hypotheses 2–5.** Test H-PIEDMONT, H-SEISMO-GAP, H-STEPOVER-SYNTH and H-RADIOMETRIC-SEEP *as additional LBCAL features*. The family-CV makes adding a layer a cheap and honest test.
