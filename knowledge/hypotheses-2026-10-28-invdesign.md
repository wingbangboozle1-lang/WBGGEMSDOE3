# INVDESIGN lane — hypotheses, sources and verified numbers (2026-10-28)

Evidence classes used strictly: **ORGANIZER-CONFIRMED** (a submission-page receipt exists),
**OWNER-REPORTED** (a sibling project's published claim), **MEASURED** (recomputed here from bytes),
**ESTIMATE** (model output). Nothing below is presented as a competition score unless it is a receipt.

## Official sources (fetched and read on 2026-10-28)

| Source | What it establishes | Link |
|---|---|---|
| Competition problem description | metric definition (DW-Tversky, α=0.2, β=0.8, 300 m triangular kernel), submission format ([0,1], EPSG:32611, 100 m, same bounds), that the **scored truth is faults absent from the public catalogue** | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ |
| Public leaderboard | #1 = **0.4544** (`xiaofanhu`, 33 submissions) read 2026-10-28. The brief's 0.4413 / 0.3195 are stale | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ |
| Data page | competition files require login (training_features.tif, labels.tif, sample_submission.tif, 1m_DEM_links.csv) | https://www.drivendata.org/competitions/306/competition-doe-gems/data/ |
| Reference solution | baseline approach published by the organiser | https://github.com/drivendataorg/gems-prize-reference-solution |
| GeoDAWN (USGS) | airborne magnetic/radiometric surveys of the study area; DOI 10.5066/P93LGLVQ; ScienceBase item 657e1d85d34e23d3533209f7 | https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and |
| INGENIOUS (GBCGE) | the geothermal-favourability project behind the catalogue | https://gbcge.org/current-projects/ingenious/ |
| EPSG:32611 | WGS 84 / UTM zone 11N, the submission CRS | https://epsg.io/32611 |
| Tversky index | the similarity family the metric belongs to | https://en.wikipedia.org/wiki/Tversky_index |
| DOE GEMS technical report | programme context (PDF) | https://docs.nrel.gov/docs/fy26osti/96647.pdf |
| GDR #1391 | DOE Geothermal Data Repository submission used for wells/springs and heat-flow context | https://gdr.openei.org/submissions/1391 |

**Unverified and flagged for manual review:** the provenance of `derived_sgmc_faults_100m_u8.tif` is
recorded only as “derived from USGS SGMC geologic-map faults (proxy only)” in
`registry/data_manifest.json`; this session did not independently confirm the SGMC release DOI, so no
SGMC DOI is asserted anywhere in the site or README.

## The decisive measurement (MEASURED + arithmetic)

`scripts/pair_identification.py`, from the bytes:

* `GEMSDOE32 …e5eb6e7e-zeros` (owner-reported **0.2778**, 37,654 dots) contains **no dot** that is not in
  `GEMSDOE28 h27-4` (owner-reported **0.2708**, 40,199 dots): set difference in = 0, out = **2,545**.
* **100%** of the 2,545 removed dots lie within 3 px of the public catalogue (median **2 px**); only
  **11.7%** of all h27-4 dots do. Since the scored truth is off-catalogue, those dots earned 0 credit
  while each paid α = 0.2 into the denominator.
* Two equations, two unknowns (T unchanged by the edit):
  `M = 0.2(s₁N₁ − s₂N₂)/(0.8(s₂ − s₁)) = 15,200 cells`,
  `T = s₂(0.2N₂ + 0.8M) = 5,470 cells` (36.0% coverage). Δ predicted +0.0071 vs observed +0.0070.
* Cross-check on six independent files: implied T = 5,230–5,481. `focus_site_table.py` gives
  Spearman(dot count, score) = **−0.983** over the nine focus champions.

## Ranked hypotheses (expected DTI improvement ÷ implementation cost)

1. **Metric-arithmetic inverse design** — implement. Layers: tomographic posterior + 1 m LiDAR scarp
   (`ex_max`, `step_max`, `lapneg_max`, `coh100`) + |∇TMI_up150| + |∇TC|. Signature: credit per dot.
   Why off-catalogue: the catalogue is used as a *negative* mask, matching how the truth is defined.
   Different from anything in this repo: every prior lane optimised a probability surface or a
   hide-and-recover holdout; none used the metric's algebra as the design objective.
2. **Chain placement** — 3 px spacing along traced lineaments; one dot on a fault earns k = 1, ⅔, ⅓
   across three consecutive truth cells, an isolated dot earns ≤ 1. Not yet emitted.
3. **Relay/stepover anatomy in the 4–30 px collar** — deprioritised: GEMSDOE33 already occupies that
   ground, so the uniqueness gate is at risk.
4. **Geothermal-discharge gating** (K/Th/U, TC, GDR springs/wells) — rejected: sibling live scores for
   geothermal-gated designs are 0.03–0.19, i.e. 1.5–9× worse than the 0.2778 champion.
5. **Blind faults in basin fill** (62-channel `training_features.tif`, second-invariant strain,
   depth-to-base) — blocked: the official file needs the authenticated DrivenData download.

## Named non-fault mimics
Quaternary alluvial-fan / lake-shore constructional scarps, road and rail cuts, stock tanks (LiDAR
scarp morphology); lithological contacts rather than faults (magnetic and radiometric gradients);
evapotranspiration and playa evaporites (radiometric K).

## What would falsify this lane
A receipt below ~0.15 on the submitted file (the design's dots are no better than a random subset of a
sibling's), or a re-fit of the posterior that moves the truth mass off the maxima used here. Both are
recorded as the decision rule in `how-to-submit.html`.
