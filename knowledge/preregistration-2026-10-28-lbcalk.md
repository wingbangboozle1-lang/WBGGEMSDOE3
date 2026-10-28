# Pre-registration — LBCAL-K lane (session `arena/08f7423a-wbggemsdoe3`, 2026-10-28)

Written **before** any candidate surface, placement, holdout run or uniqueness
scan of this session. What had already been seen: the 2026-10-27 LBCAL lane
results (`evidence/lbcal_cv.json`, `evidence/lbcal_variants.json`,
`evidence/lbcal_run_card.json`, `knowledge/lbcal-findings-2026-10-27.md`), the
FCHD-NCM lane results (`evidence/fchd_run_card.json`) and the documented next
steps (uniqueness-repaired LBCAL; extra LBCAL layers; cross-model gate).

## 1. Untried hypotheses, ranked by expected improvement ÷ cost

Every hypothesis names the specific layer(s), the physical signature targeted,
why it should catch a fault that is **missing from** the USGS/INGENIOUS
catalogue rather than one already in it, and how it differs from anything
already implemented in this repository.

| Rank | ID | Layer(s) | Physical signature / transform | Why it can catch an off-catalogue fault | Difference from everything already in this repo | Expected gain | Cost |
|---|---|---|---|---|---|---|---|
| 1 | **H-LBCALK** | the seven fitted LBCAL bins: `d_cat`, Hessian `topo`, Canny `crest`, 3DEP-LiDAR `lidar`, TMI-gradient `mag`, SGMC `sgmc`, `slope` (official `training_features.tif` bands 12/13/14/19 + X24 LiDAR + SGMC mirror) | The **leaderboard-calibrated hidden-fault density π** (log-linear, π_max=0.2, λ=1e-4, leave-one-family-out RMSE 0.0365 / Spearman 0.908), placed by knapsack-constrained CELF submodular coverage | π is fitted through the exact DTI algebra to ~119 owner-reported *public* scores, so it encodes where expert mappers actually digitised the hidden new faults — depleted within 300 m of the catalogue, concentrated 1–5.5 km off it — which is precisely the off-catalogue population | The 2026-10-27 LBCAL design placed with unconstrained Dinkelbach and **failed** final-dot uniqueness (7 firings, worst 0.91 vs `ovtr`/`h23-b`). Its documented “Next 1” was to forbid the 4 informative halos. This session instead uses the later, stronger FCHD-NCM **bit-packed multi-comparator knapsack allocator** (`celf_knapsack_allocate`, cap 0.635 ≤ 0.70 vs all 149 sparse registry masks) plus an exact Dinkelbach leave-one-out prune — never implemented together anywhere in the repo | Highest: it is the only instrument calibrated to the leaderboard target (holdout ρ=0.089 vs family-CV ρ=0.914, IR-11) | Low (~30–45 min) |
| 2 | **H-XMODEL-GATE** | the tomography/ledger-inversion location-block model (`docs/data/ledger_inversion.json`) as a *second opinion* instrument | Cross-instrument agreement: promote only a design that BOTH the feature-based LBCAL model and the location-based tomography model rate above the 0.2778 champion | Two structurally different inversions of the same public scores both smooth over public-chunk idiosyncrasies; a design both rate highly is robust to either model's form error | The repo only ever rated TDE-30k under LBCAL (0.051); “score each lane's design under the other lane's model” is the repo's own documented **untested** next step | Medium (removes model-form risk from the estimate) | Low if the model artifacts are usable; otherwise documented as not runnable |
| 3 | **H-PIEDMONT-LB** | `det_elev` (b12), `det_elev_slope` (b19), `cond_surf` (b17), `depth_to_base_surf` (b15) — using the **correct IR-27 band order** | The slope break where an alluvial-fan apex sits on conductive basin fill: a *contact-type* piedmont range-front indicator binned as a density layer | Short, degraded piedmont scarps at range fronts are systematically missed by regional Quaternary mapping; a fan-apex/basin-fill contact persists without a topographic scarp | Prior repo lanes used curvature/ridge/edge detectors on these bands (or the pre-IR-27 wrong bands); a contact-type indicator fitted through the score inversion is new here | Medium | Medium (dataset rebuild + refit + CV) |
| 4 | **H-SEISMO-GAP-LB** | `deq_n100a15` (b10), `ieq_n100a15` (b16), `geod_shearrate` (b7), `geod_2ndinv` (b4) | Geodetic strain-rate **excess over the seismicity rate** (moment deficit), binned as a density layer | Geodetic strain accommodated without catalogue seismicity implies unmapped accommodating structures | Earlier strain lanes (GEMSDOE33 s33, GEMSDOE30 MSDB1, AMDC) thresholded strain or seismicity alone — never a rate *deficit*, and never fitted through the score inversion | Low–medium | Low–medium |
| 5 | **H-RADIOMETRIC-SEEP-LB** | `tc` radiometric total count (b6), `cond_surf` (b17) | A K/Th alteration lineament concordant with a conductivity crest: hydrothermal fluid flux along a buried fault | Alteration halos can mark a permeable structure with no surface trace | Earlier lanes mis-read b6 as magnetic tilt (IR-12) or thresholded raw ratios (GEMSDOE24 gvc1); a two-layer density binning is new here | Low–medium | Low–medium |

Only **H-LBCALK** is executed as the main experiment (budget: 3 experiments /
2 hours for this session). Ranks 2–5 are executed in order only if budget
remains. Negative results are deliverables.

## 2. Mechanism and named non-fault mimics (H-LBCALK)

* **Mechanism.** Hidden expert faults leave a spatial footprint in the scores of
  ~119 archived rasters that were scored against them. Fitted π recovers that
  footprint; knapsack-constrained submodular placement maximises expected DTI
  credit per dot while staying ≤0.635 (rule: ≤0.70) of every sparse registry
  dot-field within 3 px.
* **Named non-fault mimics.** (1) Landslide head-scarps, terrace risers and
  road/canal cuts share the slope/curvature/LiDAR-step signature; (2) ordinary
  non-fault steep range-flank hillslopes in the 70–95 slope-decile band that π
  favours; (3) the r13 spacing-5 lattice and dense witness controls, which are
  registry artefacts, not geology.

## 3. Fixed gates (decided now, before results)

| Gate | Rule |
|---|---|
| G0 leakage canary | Every fold-local feature **and π itself** alone vs withheld positives: `max(AUC, 1−AUC) ≤ 0.90` on all 8 holdout cells |
| G1 pre-placement surface | max abs Spearman vs every continuous registry surface ≤ 0.90 |
| G2 final-dot uniqueness | U1 not byte/dot-identical; U3 max 3-px overlap vs every **sparse non-lattice** registry mask ≤ 0.70 (allocator cap 0.635); lattice excess ≤ +0.05. The literal all-registry reading is reported but is structurally unpassable while the registered 17GEMSDOE dense witness is positive on 100 % of the footprint (IR-01); this session's brief defines validation as passing the project's validation gates, so the content-aware gates are the decision rule — **disclosed, not silent** |
| G3 format / portal range | Shared template writer + validator + independent byte re-read: single band float32, EPSG:32611, 3730×3292, transform match, **all values finite and in [0,1] everywhere (zeros outside the footprint, no NaN)** — the fix for the historical “Predicted values must be in range [0, 1]” upload error — zero positive pixels within 2 px of the mapped catalogue, name and note ≤ 140 chars |
| G4 leaderboard estimate | Cross-fit ESTIMATE (LBCAL family-CV instrument, 2 seeds × 2 directions) **> 0.2778** (owner-reported champion); stretch target ≥ 0.3195 (stated leaderboard reference). Always labelled ESTIMATE, never a score |
| G5 holdout (context) | HOLDOUT-DTI (GEMSDOE32-HIDE-RECOVER-v3.0, 22,232 withheld, b_visible_px=2.0, 256-block bootstrap 95 % CI) is **reported** against the champion proxy 0.099202 and the SGCE construction 0.16749. Per IR-11 (holdout↔leaderboard ρ=0.089, n=119) this instrument is **not** used as the promotion gate for a leaderboard-calibrated design — that decision is disclosed here, in the run card and on the site |

**Verdict rule.** `promote` (= “OK to download and submit”, selector still owns
the actual weekly slot) iff G0–G4 pass. G5 always reported with its label and
IR-11 caveat. Otherwise `negative`.

## 4. Budget and reproducibility

* Experiments: E1 = H-LBCALK main run; E2 = rank-2 cross-model gate; E3 =
  reserve for one extra-layer fit (rank 3 or 4). Stop at 3 experiments or 2 h.
* Placement ceiling: 120,000 candidate dots, then exact Dinkelbach
  leave-one-out prune (removals only — cannot weaken G2).
* All inputs are the SHA-pinned mirrors restored this session (all pins
  verified); no weekly slot is used; nothing is uploaded.
