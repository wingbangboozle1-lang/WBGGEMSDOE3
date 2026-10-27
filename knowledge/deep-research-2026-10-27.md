# Deep research notes — 2026-10-27

Working notes behind the current submission. Every claim below is either (a) quoted from an official
source with a link, or (b) a number measured in this repository, in which case the file that contains the
measurement is named. Nothing here is a leaderboard projection dressed as a fact.

---

## 1. What the competition actually measures

From the problem page ([page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)):

- Target: **surface fault probability** over the GeoDAWN/INGENIOUS area of the northwestern Great Basin,
  on a fixed 100 m grid (EPSG:32611, 3730×3292), one float32 band in [0,1].
- Metric: a **distance-weighted Tversky index** with α = 0.2, β = 0.8 and a triangular kernel of radius
  300 m: `DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)`.
- Prizes: Initial round, $50k shared by the top five ($10k each); Final round, $250k. Rules:
  [official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) (≤ 3 submissions/week, one final
  choice across both rounds, generative-AI disclosure, reproducible solution assets).

Three consequences, derived in `docs/research.html` §2 and verified numerically in `src/gemsdoe/metric.py`:

1. Because `TP_w + FN_w = |G|` (every truth pixel is either hit or missed), the metric is algebraically
   `DTI = TP_w / (0.2·(TP_w + FP_w) + 0.8·|G|)`. **Mass and hits are the only two levers.**
2. For a fixed support, raising the emitted value strictly increases DTI. **Binary 1.0 on the support is
   optimal**; soft probabilities are dominated (measured: dilating the exact label set by 1 px already costs
   0.12 DTI — `evidence/gemsdoe_run_card.json`).
3. A correct cell is worth ~5 wrong ones at k = 1. **Precision beats coverage.**

## 2. The structural fact that decides strategy

The organiser's ground truth is *faults that are absent from the public catalogue* (the task text says the
labels are expert-annotated faults; the public catalogue is provided as a feature layer). Therefore:

- Predicting catalogue cells earns nothing and costs 0.2 each. Every archived winning file zeroes or avoids
  them: measured, all nine focus-site files have **0** dots exactly on catalogue cells.
- A *catalogue-holdout* validation is anti-correlated with the real metric (Spearman **−0.146** against
  eleven organizer-reported scores; see `knowledge/protocol-revisions-2026-10-27.md` R2). This is the single
  most expensive trap in this competition: it rewards exactly the behaviour that scores badly.
- A classifier trained on catalogue labels learns the catalogue, not the fault population. Measured:
  76-feature HistGradientBoosting, out-of-sample AUC **0.538** on withheld faults, with its top
  probabilities sitting a median 1 px from visible catalogue cells.

## 3. Data inventory: free, official, and actually reachable

| Layer | Official source | Free? | Reachable from this sandbox? | Used here |
|---|---|---|---|---|
| 19-band competition feature stack (magnetics, gravity, depth-to-basement, conductivity, seismicity, geodetic strain, detrended elevation …) | [DrivenData data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (login) | yes, with account | **no** — restored from a hash-pinned public mirror, SHA-256 verified | yes (76 derived features) |
| 2 m LiDAR scarp channels (12 bands) | USGS [3DEP](https://www.usgs.gov/3d-elevation-program), tile list in the competition PDF | yes, public domain | partially — derived by owner CI from 706/716 tiles; the tif is reachable | **yes**, half of the submission |
| USGS State Geologic Map Compilation faults (21,765 features) | [DS 1052](https://pubs.usgs.gov/publication/ds1052), [data DOI](https://doi.org/10.5066/F7WH2N65) | yes | only via a derived 100 m raster on GitHub | **yes**, validation proxy |
| Quaternary fault traces (regional) | [USGS Qfaults](https://earthquake.usgs.gov/hazards/qfaults/) / [INGENIOUS GDR 1391](https://gdr.openei.org/submissions/1391) (CC BY 4.0) | yes | yes (GitHub mirror) | yes, as the catalogue to suppress |
| GeoDAWN airborne magnetics/radiometrics | [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | yes | via the competition bands only | yes (as bands) |
| Regional geothermal wells/springs, 2 m temperature probes | INGENIOUS, GDR | yes | mirror in `data/external` | audited, not used as a support |
| 1 m DEM flow lines / drainage offsets | [USGS NHD](https://www.usgs.gov/national-hydrography) + 3DEP | yes | **no** (`prd-tnm.s3.amazonaws.com`, `hydro.nationalmap.gov` blocked) | not run (H5) |
| Slow-slip / seismicity clustering | [USGS ComCat](https://earthquake.usgs.gov/fdsnws/event/1/) | yes | **no** (api not allowlisted) | only the competition's seismicity bands |
| Sentinel-1 InSAR | [ASF](https://asf.alaska.edu/) | yes, with login | no | not attempted (B&R faults are largely interseismically locked) |

**Obtainability statement.** The submission as shipped needs nothing that is not already inside this
repository: the LiDAR tif is a 14 MB public-domain product, the SGMC raster is a 100 m derivative of a USGS
release, and the rest is the competition's own data. The blocked rows are *future* work, named so that the
blocker is explicit rather than implied.

## 4. Measured layer ranking (`evidence/layer_ranking.json`)

Top-20k support per channel, two-polarity (|value − median|), scored on the SGMC proxy (62,122 positives);
`h` is the kernel-weighted hit rate, i.e. credit per unit of emitted mass.

| Family | Best h | Median h | Channels |
|---|---|---|---|
| 2 m LiDAR scarp | **0.173** (`ex_mean`) | 0.148 | 10 |
| detrended topography | 0.142 (`de_coh_s2`) | 0.067 | 24 |
| thermal conductivity | 0.115 (`tc_log_s1`) | 0.069 | 3 |
| magnetic | 0.092 (`rtp_coh_s2`) | 0.022 | 18 |
| seismicity (distance fields) | 0.090 (`des_log_s2`) | 0.025 | 4 |
| gravity | 0.053 (`iso_grav_anom_coh_s2`) | 0.006 | 12 |
| conductivity | 0.024 | 0.016 | 4 |
| seismicity (inter-event) | 0.013 | 0.013 | 4 |
| geodetic strain | 0.003 | 0.003 | 3 |
| depth-to-basement | 0.001 | 0.001 | 4 |

Caveat that must travel with this table: a smooth regional field can score by covering the right *region*
rather than by tracing a fault. Thermal conductivity at 0.115 is that case — its top-20k support is a blob,
and blob emission at any mass from 0.1% to 5% measured ≤ 0.0215 DTI. Only lineament-shaped information can be
converted into a competitive support.

## 5. Contrarian findings (each one measured, each one a decision that was changed)

1. **Potential fields are not the discovery signal here.** Magnetics 0.092, gravity 0.053, depth-to-basement
   0.001 — against 0.173 for a single LiDAR slope-excess channel. The literature on buried fault detection in
   the Great Basin leads with potential fields; on *this label set* the labels are geomorphic.
2. **Depth-to-basement carries no off-catalogue information at all.** The "hidden range-front hinge" story is
   dead for this competition. Do not spend a lane on it.
3. **A probability field is the wrong output format.** The metric pays per truth pixel within 300 m; a
   calibrated probability map spreads mass everywhere and scores ~0.02. A thin binary crest scores ~0.36.
4. **The published "best" files are one network.** All 36 pairwise comparisons among the nine focus files
   exceed the duplicate rule (87–100% of dots within 3 px, Jaccard 0.342–1.000); GEMSDOE25 and GEMSDOE30 are
   the same mask. The champion differs from GEMSDOE36 by 1,200 cells. Reported scores of 0.2449–0.2778 are
   the *same method* with different trims.
5. **The champion's mechanism is a catalogue-distance trim, not a new detector.** The 0.2778 file is an exact
   subset of GEMSDOE31's 40,199-dot base with 2,545 dots removed — and all 2,545 lie within 3 px of a mapped
   fault. That single operation is worth +0.007 over its base.
6. **The uniqueness rule as written is unsatisfiable**, because a registered raster is positive on every
   footprint cell. Any team implementing it literally cannot submit. See R1 in
   `knowledge/protocol-revisions-2026-10-27.md`.

## 6. Overlooked approaches, ranked by expected gain per unit cost

| Rank | Idea | Why it could pay | Cost | Status |
|---|---|---|---|---|
| 1 | **2 m LiDAR scarp union** (done) | information that is not in the 100 m bands at all | low: one public-domain 14 MB tif | shipped, half of the file |
| 2 | **Ridge-crest emission instead of zone thresholds** (done) | 3–10× the DTI of the same field thresholded | low: NMS is 20 lines | shipped, other half |
| 3 | **Drainage-offset corridors** (H5) | offsets persist along a trace where scarps are eroded; independent of slope | medium: needs 3DEP/NHD tiles (blocked here) | blocked on egress |
| 4 | **Scarp-age weighting from SGMC attributes** | fresh scarps are more likely to be the unmapped ones; SGMC carries fault age/class | low if the attribute table is available | not started |
| 5 | **Thermal-conductivity *edges*** rather than values | tc is mid-table on information but smooth; a hinge transform might linearise it | low: already in the stack | not started; a dated 0.115 is a real lead |
| 6 | **LiDAR coverage mask as a covariate** | 3.89M grid cells have 2 m data; unsupported areas cannot produce LiDAR hits, so the operating point should differ there | low | not started |
| 7 | **InSAR / creep** | a small subset of Basin & Range faults creep | high: needs ASF login + processing | out of scope |

## 7. What a top-3 result would require

The public leaderboard's best observed value is 0.4437 (2026-10-26, `registry/leaderboard.json`); this file's
**estimate** is 0.428 with a 95% interval of 0.385–0.481. Concretely, the model says the marginal levers are:

- `dDTI/dh = N·(0.2N + 0.8|G|) / (0.2N·(1+h) + 0.8|G|)²`. Evaluated at N = 97,608, h = 0.1539,
  |G| = 15,672.5 this is 2.55, so **+0.01 of hit rate is worth +0.026 DTI** (exact difference: +0.0253).
  Hit rate is the only lever that matters much.
- Mass is nearly saturated: the sweep over (60k, 40k) → (50k, 40k) → (70k, 40k) moves the estimate by
  < 0.015, and both ends are worse. Do not chase mass.
- Therefore the next real gain has to come from **new information**, i.e. rows 3–6 above, not from tuning.

## 8. Sources

- Competition: [overview](https://www.drivendata.org/competitions/306/competition-doe-gems/) ·
  [problem & metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) ·
  [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) ·
  [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) ·
  [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) ·
  [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- Data: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) ·
  [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) ·
  [SGMC DS 1052](https://pubs.usgs.gov/publication/ds1052) ·
  [SGMC data](https://doi.org/10.5066/F7WH2N65) ·
  [USGS Qfaults](https://earthquake.usgs.gov/hazards/qfaults/) ·
  [NHD](https://www.usgs.gov/national-hydrography) ·
  [INGENIOUS GDR 1391](https://gdr.openei.org/submissions/1391)
- Method: [Tversky index](https://en.wikipedia.org/wiki/Tversky_index) ·
  [EPSG:32611](https://epsg.io/32611)
