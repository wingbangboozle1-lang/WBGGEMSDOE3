# WBGGEMSDOE3 — Great Basin fault-discovery research

> **Session rule:** read this README from the top at the beginning of every project session. It is the standing brief and current decision record. Update the status only from reproducible evidence; never turn an estimate into a score.

## Current decision — 2026-10-26

# 🔴 NOT READY — DO NOT SUBMIT

**There is no newly generated TIFF in this repository, and no file here is approved for download or competition upload.** No scientifically defensible candidate can be built or evaluated in this checkout: it contains only this README at the starting commit, and has no competition rasters, cached feature stack, shared evaluator/writer, or assigned single-method lane. The public DrivenData data page is login-walled according to the project brief; this sandbox cannot reach that host. We will not synthesize a TIFF from old submissions, random noise, or an incomplete raster just to provide a download button.

The focus-site raster audit below is **forensic/educational only**. It verified the bytes and dot-overlap of the historical files, not their organizer-reported scores. All nine focus-site winners fail the requested `≤70%` directed dot-overlap rule against at least one other winner among the same nine. The best *reported* historical result in the set is the GEMSDOE32 H33-B2 file at `0.2778`, but no submission-page receipt tying that score to its exact raster hash was found in the reviewed GitHub evidence. **Do not submit any historical file as a new unique candidate.**

- [Executive summary, nine-site table, and portal procedure](docs/executive-summary.html)
- [Candidate geology hypotheses (planning only)](docs/hypotheses.html)
- [Research knowledge base](docs/knowledge-base.html)
- [Why the `0.2778` report is not a causal proof](docs/why-02778.html)
- [Known irregularities and access blockers](docs/irregularities.html)
- [Automated public-repository activity feed (not a score feed)](docs/feed.html)
- [Registry uniqueness check and manifest requirements](docs/registry-check.html)
- [Sources and verification limits](docs/sources.html)
- [Machine-readable nine-site raster audit](docs/data/focus-site-audit.json)
- [Negative run card](docs/data/run-card.json)

## Standing project brief

The objective is to maximize the probability of a high placement in the DrivenData DOE GEMS competition by finding **scientifically defensible, genuinely unique, automatically validated** raster predictions for uncatalogued faults in the Great Basin. The target is fault discovery relevant to geothermal systems; a geothermal anomaly alone is not a fault label. The deliverable, when and only when all gates pass, is a single-band GeoTIFF matching the competition sample submission's CRS, dimensions, and affine transform, with **every stored prediction finite and in `[0, 1]`**. The landing page must make the download/submit decision obvious. A format pass alone is not scientific approval.

Prioritize the nine requested repositories: `GEMSDOE24`, `GEMSDOE25`, `GEMSDOE27`, `GEMSDOE28`, `GEMSDOE30`, `GEMSDOE31`, `GEMSDOE32`, `GEMSDOE33`, and `GEMSDOE36`. For each, record the best *reported historical* file, score provenance, byte hash, and whether its emitted dots meet the focus-set uniqueness rule. Never describe an unverified owner report or a projection as an organizer-confirmed score.

### Non-negotiable experiment and release protocol

1. **Single lane:** follow only the explicitly assigned method paragraph. If the prompt has no unambiguous lane paragraph, stop before a candidate experiment. Before placement, compare the candidate surface against every available registry raster; stop and log a duplicate if any absolute Spearman rank-correlation is `>0.90`. After placement, stop and log a duplicate if more than `70%` of candidate dots fall within `3` raster pixels of any registry raster's dots. No lattice or other-registry exemption is allowed unless the owner changes the rule.
2. **Reuse shared tools:** use the canonical cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`. Do not maintain a private copy of the shared evaluator or writer. If a shared tool is wrong, repair it in the shared template and report the fix; do not silently fork it here.
3. **Holdout:** hide whole fault segments with a buffer; derive every catalogue-based feature from visible faults only; mask visible faults pixel-exactly; compute the pooled distance-weighted Tversky index with `alpha=0.2`, `beta=0.8`, and the `300 m` triangular kernel. Report every result as **HOLDOUT-DTI** with evaluator version, number of withheld positives, and a `95%` confidence interval. Holdout-DTI is not the competition score.
4. **Leakage canary:** test every feature alone on the same holdout. AUC above `0.90` is presumed leakage until disproven.
5. **Run card:** end every experiment with one JSON card containing the hypothesis, mechanism, named non-fault mimic, HOLDOUT-DTI and confidence interval, registry correlation/overlap, raster SHA-256, saved-byte validator result, submission name, a note no longer than `140` characters, and verdict `promote` or `negative`. Negative results are valid deliverables.
6. **Budget and slot discipline:** stop after at most `3` experiments or `2` hours. Do not use a weekly competition slot until a separate selector confirms all gates and the live weekly cap. Do not submit automatically from this site.
7. **No copy-as-candidate:** prior TIFFs may be inspected for learning, hashing, and duplicate analysis only. Every candidate must be built from the actual inputs using a documented method, not copied or trivially transformed from an old submission.
8. **Three-pass review:** implement/verify, inspect for bugs and assumptions, then re-check the complete request. Document unresolved limitations instead of masking them.

### Verified work in this checkout

- Reviewed the nine historical winner rasters from immutable GitHub commits through the GitHub API. Downloaded bytes were written only to temporary storage, never copied into this repository, and all nine SHA-256 hashes matched the prior audit manifest.
- Independently read each raster with Rasterio: the nine files share `EPSG:32611`, shape `3730 × 3292`, and the affine transform `(100, 0, 243350, 0, -100, 4508550)`. They are single-band `float32` rasters. Two selected historical variants have NaNs outside the finite footprint; those bytes fail the full-grid `[0,1]` preflight required here.
- Independently recomputed all `72` directed within-`3`-pixel comparisons among the nine focus-site winner masks. The minimum was `86.718954%`, above the requested `70%` ceiling. `GEMSDOE25` and `GEMSDOE30` masks are exact matches; the GEMSDOE32 mask is a strict subset of GEMSDOE31 and GEMSDOE36.
- Independently verified the GEMSDOE32 H33-B2 TIFF hash and that its positive pixels are a strict subset of the selected GEMSDOE25 D2.8 mask, with `6,436` positive pixels removed. This establishes raster lineage only; it does not establish why the hidden-test score changed.
- Added an automated preflight for future candidate TIFF bytes: `validate_submission.py` checks saved format/range/grid and known-catalogue overlap; `validate_registry_uniqueness.py` checks surface Spearman and final-dot overlap against every hash-pinned entry in a caller-supplied complete registry manifest. Neither check authorizes a live submission. The full canonical registry is absent here, so no uniqueness clearance is available.
- No model/holdout experiment was run, no candidate TIFF was generated, and no competition slot was used.

See [the audit JSON](docs/data/focus-site-audit.json) for immutable source commits, paths, hashes, grid metadata, pairwise overlap results, and limitations. Historical scores in that table are `OWNER-REPORTED`, not `ORGANIZER-CONFIRMED`.

## Research question: why did GEMSDOE32 report `0.2778`?

The best-supported answer is conditional. The reported H33-B2 TIFF is a sparse `37,654`-dot subset of the D2.8 mask. Under the competition's distance-weighted Tversky objective, reducing redundant prediction mass can improve precision if it removes predictions with little marginal credit while retaining enough coverage of hidden faults. That is a plausible mechanism, not proof: private test labels are unavailable, the score-to-hash receipt is absent, and the archived metric/lineage analysis does not expose the organizer's true TP/FP/FN breakdown. The exact score attribution and causal explanation therefore remain unverified. See [the detailed note](docs/why-02778.html).

The prompt contains conflicting public-leader values (`0.3195` and `0.4413`). An upstream project report also records a later `0.4437` snapshot, but this checkout did not independently access the live DrivenData leaderboard. None of those figures is treated as current here. See [irregularities](docs/irregularities.html).

## Data, permissions, and project limitations

- **Competition inputs:** the required training features, labels, sample submission, existing-fault mask, and cached feature stack are absent. The data page requires DrivenData account access per the project brief. Do not commit private competition data or upload credentials.
- **Shared template:** the existing research project at [GEMSDOE32](https://github.com/buffedlizard55-lab/GEMSDOE32) contains the shared evaluator/writer code and many prior experiments; it is not an official organizer source. Its inspected checkout does not contain the ignored raster cache. It also records a space-filling-lattice exception that conflicts with this brief's literal uniqueness rule; do not rely on that exception or copy a candidate from it.
- **Official references:** the competition, rules PDF, USGS GeoDAWN page, DOE GDR INGENIOUS record, and EPSG page are listed in [Sources](docs/sources.html). This environment did not fetch those non-GitHub hosts; URLs are provided for review, not represented as freshly verified here.
- **Feed and leaderboard automation:** a scheduled GitHub Actions build refreshes public `main` commit metadata for the nine focus repositories in [the activity feed](docs/feed.html). It does not scrape scores. There is no authenticated DrivenData session or official receipt in this repository; automatic leaderboard polling/submission is not implemented. A live leaderboard value or an owner-page number is not a submission receipt.
- **Environment:** the submission validator needs Python, NumPy, Rasterio, and a local official sample raster. Run `python -m pip install -r requirements.txt` before using it.

## Arena core values

### Maximize P(Win)

> “Maximize the Probability of Winning”: our decision making framework. In every decision, we weigh tradeoffs, assess risk, and choose the path that maximizes the probability that Arena succeeds. We set aside our emotions and make tough decisions in order to maximize P(Win). “Maximize P(Win)” frees us from constraints and clarifies that we must put Arena first.

### Own the Outcome

> We own results end to end — not just our individual slice of the work. When problems arise and we have the means to act, we do so without waiting for permission or assignment. We treat failure and success as signals and use them to improve. At Arena, we stay accountable to the final outcome.
