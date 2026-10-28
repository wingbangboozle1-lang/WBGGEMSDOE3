# Preregistration — 2026-10-28 session `arena/6984642c` (`ADJDIS` lane)

**Frozen before experiment execution: `0 / 3` experiments used at time of writing.**
**Evaluator locked**: `GEMSDOE32-HIDE-RECOVER-v3.0` (`22,232` withheld positives, 4 quadrants ×
draws 20/21, 15 px train collar, visible-fault evaluation gate `b_visible_px = 2.0`,
pooled DTI α=0.2, β=0.8, 300 m triangular kernel). Baseline to beat: the champion
proxy (`gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif`, owner-reported 0.2600 on
its own site) re-scored on identical folds — FCHD recorded `0.099202`; this session re-measures it
fresh before any experiment and must reproduce it exactly (same evaluator, same seed) or stop.

**Data restored and SHA-256 verified this session**: 26 files in `registry/data_manifest.json`
(418,912,844-byte `training_features.tif` + labels + sample + externals), 4 FCHD externals
(`registry/fchd_external_manifest.json`), 12 focus/comparator pins (`research/input_manifest.json`),
118 ledger rasters, 14 addendum rasters, 17 Oct-27 peer rasters (2 relocated to the default
branch after an upstream rewrite; bytes re-verified against the registered SHA-256 — see
`evidence/peer_fetch_resilient_2026-10-28.json`), and the `17GEMSDOE` dense witness
(`ab0a0a62eecf066a…`). Mirror pins prove byte identity, not organizer provenance.

## Why this lane exists (mechanism-first reading of the focus evidence)

Byte-level facts already established in this repository (`content/why-0.2778.md`,
`evidence/focus_audit.json`, `knowledge/preregistration-2026-10-27-fchd.md`):

* The nine focus-site leaders are one family: `h19-5 (121,131 px) ⊃ d1.5/d2.8 (44,090/40,199 px) ⊃
  B2 (37,654 px)`, pairwise 3-px overlaps `0.867–1.000`, all sitting **≥ ~2.2 px** off the public
  catalogue. Their owner-reported scores (0.2449–0.2778) are the only consistent
  organizer-score-like signal in the ledger, and they all come from one mechanism: emit a sparse
  halo just outside the known-fault exclusion zone, where hidden strands that continue or en-échelon
  parallel the mapped strands fall inside the 300 m kernel while catalogue-adjacent false positives
  are trimmed (B2's 2,545 removed cells at 1.4–2 px).
* On our hide-and-recover instrument the same family splits: the d2.8 halo recovers
  `0.099202` because hidden components adjacent to visible ones stay inside its kernel reach,
  while B2 (dots gated out at ≤2 px) collapses to `0.0045` on shipped bytes. No prior
  `WBGGEMSDOE3` lane has reproduced the adjacency mechanism **and** kept the registry gates —
  `SGCE` used broad `exp(-d_vis/15)` rings with 102,208 dots (ledger collapse, IR-11),
  `H6-1` tested pruning, not placement, `LST1` allocated by strata without a physical surface.

**Single method paragraph (lane definition).** `ADJDIS` = two-phase, fold-legal emission:
**Phase A (adjacency quota)** places at most `s·K` dots on a Gaussian visibility-adjacency ridge
`band(d) = exp(-0.5((d - d0)/σ)^2)` (default `d0 = 4.0 px`, `σ = 2.5 px`) computed **only** from each
holdout cell's visible catalogue (`cell.visible_full`; from `existing_faults.tif` only at full-map
export), restricted to `2.0 < d_vis ≤ 10.0 px`; **Phase B (discovery)** places the remaining
`(1-s)·K` dots strictly at `d_vis > 10.0 px`, ranked by the sharpened zero-catalogue physical OOF
posterior reused from the shared FCHD stack (`predict_oof_surfaces`, E1 physical or E2+NCM).
Both phases run through the shared `celf_knapsack_allocate` (per-phase multi-comparator cap
`0.635`), the shared evaluator, and the shared `vendor.gems57.submission_writer`. Default
`K = 38,000`, default split `s = 0.60`.

## Ranked candidate hypotheses (5), by expected holdout lift vs cost

| Rank | ID | Layers & physical signature | Why it should catch faults missing from the USGS/INGENIOUS catalogue | Difference from everything already in this repo | Named non-fault mimics & falsification | Data obtainability | Expected HOLDOUT-DTI lift vs 0.0992 | Cost |
|---:|---|---|---|---|---|---|---|---|
| **1 (EXECUTE)** | **`ADJDIS`** | Fold-visible catalogue distance field only (no new raster): Gaussian ridge at `d0=4 px` off visible traces; Phase B = reused 62/72-feature physical OOF posterior (chi/facet/liDAR/worms/radiometrics/GDR #1391) | Hidden strands concentrate just beyond mapped traces (relay splays, en-échelon continuations, blind offsets of the same structure); the focus-family leaderboard evidence says this halo is where organizer score lives, and >10 px discovery captures strands the family's kernel cannot reach | First lane to **quota** adjacency under the registry caps (≤0.635 per phase, ≤0.70 union) instead of SGCE's unbounded rings or FCHD's purely feature-ranked placement; adjacency is a surface here, not a post-hoc prune | Colluvial wedges and faceted-spur base-of-slope channel incision along range fronts; playa-margin risers. Falsify by Draw-21 regression and by band-only canary >0.90 | In-repo: catalogue mirror + FCHD stack (verified this session) | **+0.006 to +0.020** (mechanism has the only score-like evidence; quota may bind below the pure-halo ceiling) | ~35 min |
| 2 | `GSTR-ASEIS` | `training_features` b4/b7/b8 (geodetic 2nd-invariant, shear, dilatation) structure-tensor localization **gated low** by b16 `ieq`/b10 `deq` (aseismic complement); b17 `cond_surf` corroboration | Aseismic creeping strands (no scarp, no seismicity) are absent from scarp-based andismic catalogues alike; strain localizes where slip is accommodated silently | No lane used the geodetic−seismic **complement** as the central operator; HCE used strain only as one collinear edge channel among many, FCHD did not gate on seismicity | Smooth GPS/InSAR interpolation artifacts at station edges; interseismic locking transitions; geothermal production subsidence. Canary first — smooth fields can leak via footprint coverage | In-repo bands only (no new download) | +0.003 to +0.010 (unknown spatial resolution of strain fields at 100 m) | ~20 min |
| 3 | `CND-ALT` | b17 `cond_surf` + b6 `tc` tilt edges + `geodawn_rad` Th/K ratio: concordant alteration-conductivity lineaments under alluvium | Fluid-altered fault zones conduct; basin fill hides them from optical/scarp mapping; alteration halo outlives the scarp | HCE/THCS used conductivity as a supporting collinear channel, never as a gated alteration-pair consensus with independent radiometric corroboration | Saline playa brines, clay-rich basin fill, conductive aquitards. Require radiometric corroboration to fire | In-repo bands + `geodawn_rad_u8` (verified) | +0.002 to +0.008 | ~20 min |
| 4 | `QEPI-FOCAL` | b10 `deq` / b16 `ieq` gradient ridges (earthquake-density lineament edges) + `depth_to_base_surf` concealment gate | Diffuse seismicity lines mark strands never compiled into surface-fault maps | Peer `GEMSDOE33 s33` scored 0.0963 owner-reported with a seismicity product, so expect registry crowding; our ridge-edge operator and concealment gating differ | Quarry/volcano swarms, induced seismicity clusters (RSA basin). Must clear ≤0.70 overlap vs `GEMSDOE33` or stop | In-repo bands only | +0.001 to +0.006 (crowding risk) | ~15 min |
| 5 | `SHORE-STEP` | `dem10_chi zmean_m` Sehoo shoreline (~1,338 m) differential warping steps + GDR paleo-tufa alignments | Post-15.5 ka 2–8 m offsets displace a formerly horizontal lake datum where eolian sand hides the scarp | Preregistered as FCHD rank-4 but never executed; still untried anywhere | Windward/leeward wave runup scatter ≤3 m; tufa benches without tectonics. Require along-strike step persistence | In-repo chi raster + GDR zips (verified) | +0.002 to +0.006, recall ceiling ≈28 % of footprint | ~25 min |

Hypotheses 2–5 are **not executed** in this session; ranks 1-only execution is the frozen plan.
No hypothesis needs data outside this sandbox; the previous INSAR idea stays blocked
(`asf.alaska.edu` is outside the outbound allowlist — not proposed as viable here).

## Frozen 3-experiment plan for `ADJDIS`

1. **E1 `ADJDIS-E1-BAND`** (1/3): defaults — `s = 0.60`, `d0 = 4.0`, `σ = 2.5`, `K = 38,000`,
   Phase-B surface = FCHD `predict_oof_surfaces(…, use_ncm_struct=False)` (reused, not refit).
   Purpose: isolate the adjacency mechanism under the uniqueness quota.
2. **E2 `ADJDIS-E2-FUSION-GRID`** (2/3): Phase-B surface = FCHD `use_ncm_struct=True` posterior.
   Draw-20 grid `s ∈ {0.45, 0.60, 0.70}` × `d0 ∈ {3.5, 4.0, 5.0}` (σ fixed 2.5); select the single
   best cell by Draw-20 mean DTI; verify on Draw-21; report pooled.
3. **E3 `ADJDIS-E3-BUDGET`** (3/3): winner of E2 × budget sweep `K ∈ {35,000, 38,000, 42,000}`
   selected strictly on Draw-20, verified on Draw-21. This output — and only this output — is
   written through the shared writer, byte-validated, uniqueness-audited and run-carded.

No further tuning after E3. Parameter search never reads Draw-21.

## Frozen gates (all must pass for a method-level `promote`; a slot is a separate selector step)

* **G0 canary**: every feature used alone on the same holdout ≤ 0.90 directional AUC —
  the new `adjacency_band` row computed this session, plus the reused 62 static + 10 NCM rows
  re-measured this session (fresh receipt `evidence/adjdis_leakage_canary.json`).
* **G1 holdout superiority**: pooled HOLDOUT-DTI of the E3 winner **> 0.099202** (re-measured
  champion proxy) with paired 95 % block-bootstrap Δ lower bound > 0; also reported vs FCHD-E2
  (`0.097024`, internal incumbent).
* **G2 discipline**: emitted dots within `[15,000]–[50,000]`.
* **G3 uniqueness**: pre-placement `max |Spearman| ≤ 0.90` for band surface, Phase-B surface and
  the piecewise full-map surface; post-placement union `U1` not an exact duplicate,
  `max non-lattice 3-px overlap ≤ 0.70` across the shared full registry **and** a direct
  measurement against the FCHD file that `discover_all_comparator_tifs` excludes by substring
  (if that direct measurement exceeds 0.70 → duplicate stop, verdict negative, no rescue beyond
  the already-frozen E2/E3 grids). Lattice null excess ≤ +0.05. The literal dense-witness reading
  (IR-01/IR-09, 100 % for any non-empty raster) is reported transparently and **not** waived here.
* **G4 format**: shared writer → reopen bytes → single band, float32, all finite, all values in
  `[0,1]`, exact CRS/shape/transform vs `sample_submission.tif`, zero outside footprint for the
  zeros encoding, zero on catalogue pixels, note ≤ 140 chars.

Promotion here means **method-level eligibility for the separate selector** (weekly cap unknown
in this sandbox). It is not an organizer-confirmed score, not selector approval, and not a waiver
of the literal IR-01 blocker that keeps the published site decision at DO-NOT-SUBMIT until the
user ratifies the content-aware reading.

## Reference links (official / in-repo)

* Competition metric & rules: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
* Staff scoring clarification (known-fault masking): https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516
* Tversky index: https://en.wikipedia.org/wiki/Tversky_index
* Focus-family byte evidence: `evidence/focus_audit.json`, `content/why-0.2778.md`
* Shared allocator/evaluator/writer: `src/fchd/registry_full.py`, `src/gemsw/holdout.py`,
  `vendor/gems57/submission_writer.py`
