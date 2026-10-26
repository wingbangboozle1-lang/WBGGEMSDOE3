# Why `h33-h33-2-b2` scored 0.2778 — and whether higher is possible

**Evidence classes used on this page.** `OWNER-REPORTED` = a score written down by a sibling repo (no DrivenData receipt is
available to us). `OBSERVED-PUBLIC-PAGE` = read from drivendata.org today. `COMPUTED-HERE` = recomputed in this repo from bytes
we hash-checked. `HOLDOUT-DTI` = our spatially-blocked evaluator. Nothing here is an `ORGANIZER-CONFIRMED` score of a file we produced.

## 1. The metric, algebraically
Official definitions ([metric page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)): kernel
k(d) = max(1 − d/300 m, 0); TPw = Σ_g max_x p(x)k(d(x,g)); FPw = Σ_x p(x)[1 − max_g k(d(x,g))]; FNw = Σ_g [1 − max_x p(x)k].
With a binary emission of N dots and |G| truth pixels, let M = Σ_x p(x) max_g k. Then FPw = N − M, FNw = |G| − TPw and

  **DTI = TPw / [ 0.2 (TPw + N − M) + 0.8 |G| ]**.

Two asymmetries drive everything: credit is a **max** (a second dot beside an already-credited truth pixel adds nothing)
but false-positive mass is a **sum** (every extra dot costs 0.2 unless it sits near truth). Because the 3-px kernel pays
partial credit out to 300 m, a *sparse dotted lattice* keeps almost all credit of a solid line while paying a fraction of the N term.

**Break-even rule (COMPUTED-HERE).** Adding one isolated dot changes DTI by ≥ 0 iff its marginal credit exceeds about
0.2·DTI. At DTI = 0.2778 that is 0.056 kernel-credit units; with Σk = 9.38 over the 25-offset (radius-3-pixel) kernel support this means the hidden-truth
density around the dot must exceed ≈ 0.006 per 100 m pixel — several times the footprint-wide average (≈ 0.001–0.002 for a
hidden-truth mass of 4–10 thousand pixels, the bootstrap range found here). A dot below that density *lowers* the score.

## 2. The nested family that produced 0.2778 (all OWNER-REPORTED)
| step | dots | score | what changed |
|---|---|---|---|
| H19-5 solid network | 121,131 | 0.1922 | many adjacent, redundant dots |
| thinned to ≥2.8 px spacing (d2.8) | 44,090 | 0.2600 | N cut by 64 %, credit nearly kept |
| remove dots within 100 m of catalogue (B=1) | 40,199 | 0.2708 | those pixels are masked in scoring ([forum 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516)); a dot there earns ~no credit but costs 0.2 |
| also remove the 100–200 m annulus (B=2) | 37,654 | **0.2778** | same logic; annulus dots fall below the break-even density |
| + 1,200 "Anderson" mechanics dots | 38,854 | 0.2750 | the added dots are below break-even on average |

Each row is a *deletion or an addition that crosses the break-even density*, which is why the improvements are small and
monotone — the champion is a locally optimal pruning of one network, not a new source of information.

## 3. What the ledger does and does not show (COMPUTED-HERE)
* 112 distinct live-scored rasters were hash-verified and re-measured. Independent rasters that share only 51–67 % of their dots
  with H19-5 still score 0.219–0.248 (e.g. 62 % → 0.2478). So hidden truth is **not** confined to the H19-5 network.
* Rank correlation between score and "fraction of dots near H19-5" is 0.70, but all top rasters descend from H19-5, so this is
  confounded; a claim such as "73–96 % of truth lies on the network" is **not identified** by the ledger.
* With the product stratum (catalogue distance × H19-5 distance) a ledger-calibrated model predicts held-out *sites* with MAE
  0.026 (leave-site-out), 90th-percentile error 0.065. None of the 66 independent fields (19 bands, lidar, radiometrics, GeoDAWN,
  derived gradients, distances) improves on the stratum-only baseline in nested CV. The leakage canary passes: the largest
  single-field AUC against the catalogue is 0.658 (< 0.90).

## 4. Is a higher score possible?
Yes — the public board already shows it ([leaderboard, 2026-10-26](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)): #1 is 0.4437,
#5 (the initial-round prize line) is 0.3561, and #50 is 0.2826, so **0.2778 would sit just outside the top 50**.
Even with *zero* false positives, DTI = c/(0.2c + 0.8) for coverage c = TPw/|G|; 0.2778 needs c ≥ 0.235, 0.3561 needs c ≥ 0.307 and
0.4437 needs c ≥ 0.39. The leaders therefore recover at least ~40 % of the hidden truth with few false positives.
We found nothing in the nine sibling repos, and no signal in the 66 fields examined here, that carries that much *ledger-identified* information. Our
opinion (not a result): with the mirrored data alone the family is near its ceiling; a step change needs new information such as
metre-scale scarps (3DEP 1 m DEM), InSAR, or newer fault mapping — all untested because they could not be fetched in this sandbox.
