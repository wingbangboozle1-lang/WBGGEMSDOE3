# Preregistration — 2026-10-28 — KHD lane (Kernel-Keep / Halo-Displace)

Session `arena/7702e9ff-wbggemsdoe3`. Written **before** running the emission
experiment. Numbers already measured this session (byte-exact subset algebra,
family halo coverage) are evidence, not outcomes of the experiments below.

## Established evidence used to rank hypotheses (measured 2026-10-28)

From the SHA-pinned focus rasters (all counts recomputed from bytes this session):

| raster | n dots | on catalogue | 1–2 px band | owner-reported |
|---|---:|---:|---:|---:|
| GEMSDOE24 d1-5 | 60,069 | 5,355 | 3,414 | 0.2477 |
| GEMSDOE25 d2-8 | 44,090 | 3,891 | 2,545 | 0.2600 |
| GEMSDOE27 tgc-on-d1-5 | 61,328 | 5,413 | 3,462 | 0.2449 |
| GEMSDOE28 h36-rung30 | 37,660 | 0 | 2,353 | 0.2710 |
| GEMSDOE30 d28-poisson (same support as 25) | 44,090 | 3,891 | 2,545 | 0.2600 |
| GEMSDOE31 solo-d28 | 40,199 | 0 | 2,545 | 0.2708 |
| **GEMSDOE32 B2** | **37,654** | **0** | **0** | **0.2778** |
| GEMSDOE33 tip-stepover | 41,865 | 1,377 | 2,517 | 0.2632 |
| GEMSDOE36 pinn | 38,854 | 0 | 0 | 0.2750 |

Byte-exact identities (verified `np.array_equal` this session):

1. `GEMSDOE31 = GEMSDOE25 − {dots on catalogue}` (44,090 − 3,891 = 40,199).
   One-change score delta: **+0.0108**.
2. `GEMSDOE32 = GEMSDOE31 − {dots at 1.01–2.01 px from catalogue}`
   (40,199 − 2,545 = 37,654). One-change score delta: **+0.0070**.
3. `GEMSDOE36 = GEMSDOE32 ∪ {1,200 extra dots}`. One-change score delta: **−0.0028**.
4. The h19-5 multiline network (121,131 positive cells) is **100% covered within
   3 px by the focus-family union**; 0 network cells lie >3 px from the family.
   Novel (>3 px from every focus file) space is entirely off-network:
   3,977,508 cells, of which 39,511 are within 3 px of the network.

Consequence for the directed 70 % uniqueness rule: a candidate that keeps ≥30 %
of its dots in the novel pool (>3 px from each comparator) passes the rule
against every focus file; a candidate that stays on-network fails it.

## Ranked geological hypotheses (3–5), all new to this repo's implemented lanes

### H1 — KHD: catalogue-halo redundancy completion + halo-displacement (TOP)
- **Layers:** `existing_faults.tif` (geometry only), h19-5 multiline-corroborated
  surface (pinned mirror), ledger-tomographic hidden-truth density ρ̂ (LST strata
  of catalogue-distance × network-distance), optional lidar-scarp concordance.
- **Signature:** exact marginal DTI credit map (triangular kernel R = 3 px) under
  ρ̂; keep a dot only while its marginal two-sided gain is positive; displace the
  minimum-value dots into the novel pool until every comparator's directed 3-px
  overlap ≤ 0.65.
- **Why it catches faults missing from the catalogue:** the hidden truth is the
  unmapped continuation of the mapped system; B2's measured gains came from
  removing FP mass whose kernel credit was duplicated by ≥2 px neighbours, not
  from removing coverage. Completing that pruning under ρ̂ removes the remaining
  low-credit mass anywhere on the network (e.g. d1-5's parallel redundancy), and
  halo-displacement spends the freed budget on the best remaining off-network
  structure (secondary lineaments, linkage corridors) where unmapped segments live.
- **Difference from anything implemented here:** no lane in this repo ran an
  exact marginal keep/prune pass on the family skeleton; B2's trim was
  band-based only (catalogue distance). The FCHD knapsack allocator targeted
  uniqueness from scratch with a 62-ch feature rho; KHD starts from the
  empirically optimal skeleton and moves only the minimum mass.
- **Non-fault mimic that could produce the same signature:** basin-fill drainage
  lineaments and lithologic contacts in the SGMC can look like ridge traces
  off-network; ρ̂ strata learned from the ledger damp them but cannot eliminate
  them. Named control: an equal-count strata-shuffled field.

### H2 — tip-linkage corridors from catalogue geometry only
- **Layers:** `existing_faults.tif` segment endpoints/step-over gaps, det_elev
  ridge (band 12), lidar scarp channels.
- **Signature:** corridor-closure transform between opposing segment tips
  (relay-ramp geometry), ridge concordance inside the corridor.
- **Why unmapped faults:** displacement transfers between mapped segments in
  relay ramps — the classic host of blind geothermal systems; the catalogue
  stops at mapped trace ends.
- **Difference:** GEMSDOE33's tip-stepover variant modified the network dots and
  scored 0.2632 with 1,377 on-catalogue dots; this builds corridors from
  geometry alone, zero on-catalogue emission, novelty-capped.
- **Mimic:** stream valleys cutting between ridge spurs (same corridor shape).
- **Rank:** expected gain ≤ H1; higher construction cost.

### H3 — radiometric alteration-cap vent habitat dots
- **Layers:** `geodawn_rad_u8` (K, Th, U channels), 2 m temperature probes
  (GDR 1391 mirror), wellspring/spring CSVs, SGMC unit contacts.
- **Signature:** K-depletion ∩ Th/U elevation ∩ curvature-high contact; binary
  dots at concordant cells only.
- **Why unmapped faults:** hydrothermal upflow leaves alteration halos where no
  Holocene scarp exists; the catalogue maps faults, not vents.
- **Difference:** 15GEMSDOE conj_alteration_mag was a soft surface (0.0782);
  this is binary emission under the DTI marginal bar.
- **Mimic:** weathered ash-flow tuffs and caldera rims show the same K-depletion.
- **Rank:** third; needs channel dequantisation work.

### H4 — Euler depth-cluster / Curie corridor dots
- **Layers:** tmi/rtp (bands 14/2), iso_grav_anom (13), depth_to_base_surf (15).
- **Signature:** clustered Euler deconvolution window solutions + shallow Curie
  ridge concordance.
- **Difference:** GEMSDOE28 h38 Euler dots rode the family skeleton (0.2707);
  this is off-family placement for uniqueness.
- **Mimic:** intrusive bodies with no structural permeability.
- **Rank:** fourth.

### H5 — background-seismicity / strain-rate corridor dots (NOT RUN)
- **Layers:** competition seismicity + geodetic strain bands.
- **Difference:** GEMSDOE33 seisdil-strain-seismicity scored 0.0963 (negative
  evidence); listed for completeness only.
- **Rank:** fifth, low expected value.

## Preregistered experiments (budget: 3)

- **E1 (primary):** LST ρ̂ fit on the 118-probe ledger (site-family CV reported);
  KHD emission at budget B = 37,654 (family-optimal); uniqueness caps 0.65 vs
  every sparse registry comparator; zeros-outside encoding. Outputs:
  LEDGER-PROJECTION (with CV MAE) + uniqueness audit (surface and final).
- **E2:** shared hide-and-recover holdout (whole-segment buffered withholding,
  visible-fault-only catalogue features) of E1 vs byte-exact B2 reference and an
  equal-count strata-shuffled control on identical folds. Labelled HOLDOUT-DTI
  with evaluator version + withheld positives + 95 % cluster-bootstrap CI.
  **Known limitation (documented, not fixed here):** catalogue-holdout DTI is
  anti-correlated with owner-reported scores for the dotted family
  (Spearman −0.146, `knowledge/protocol-revisions-2026-10-27.md` R2); E2 is a
  leak/quality gate, not a leaderboard proxy.
- **E3 (sensitivity):** budget scan {34,000, 37,654, 41,000} under the same caps
  to verify the empirical optimum is not an artifact; promotion goes to the best
  projected variant.

Stop after 3 experiments or 2 h. Negative results are deliverables. No weekly
submission slot is spent by this lane; promotion to a real slot is the selector's
decision.

## Leak canary (gate 0)
Each feature used for placement (ρ̂ strata map, ridge concordance, lidar fields)
is scored alone on the same holdout; AUC > 0.90 is leakage until proven
otherwise. Catalogue-derived distances are computed from the **visible** faults
inside each fold.
