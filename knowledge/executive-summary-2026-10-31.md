# Executive summary — GEMSDOE focus sites, 2026-10-31

> ## DECISION: DO NOT DOWNLOAD OR SUBMIT ANY FILE
>
> **No TIFF is cleared, and none was generated this session.** Three reasons, each sufficient alone:
>
> 1. **Not unique.** Every focus file has at least 97.6% of its positive cells within 3 px of another focus file (measured below). Two of them (GEMSDOE32 and GEMSDOE31) are exact subsets of others.
> 2. **No score can be measured here.** The competition labels are behind a DrivenData login. `drivendata.org`, `dropbox.com`, `docs.nlr.gov` and `github.io` all return HTTP 000 from this sandbox (checked 2026-10-31). No HOLDOUT-DTI exists, so no candidate can be validated before a slot.
> 3. **Open protocol stop.** The repo's release gate (`docs/data/release_gate.json`) is still DO-NOT-SUBMIT. Resolving the dense-witness/dot-definition question needs an owner decision (options A/B/C below). Those options are not mine to pick.
>
> **What you can do now:** nothing to upload. Read the owner decision in [§6](#6-what-is-needed-to-clear-a-file).

Evidence for everything below: [`evidence/focus_measure_2026_10_31.json`](../evidence/focus_measure_2026_10_31.json) (measured) · [`scripts/measure_focus_files_2026_10_31.py`](../scripts/measure_focus_files_2026_10_31.py) (reproduces it) · [`evidence/run_card_2026_10_31.json`](../evidence/run_card_2026_10_31.json) (negative run card).

---

## 1. Best submission per site (what you asked for)

Scores are **OWNER-REPORTED / UNVERIFIED**. Each is from the owner's public site, not an organizer receipt. The "Estimate" column is **not a score**: no estimate can be produced here (see §4).

| Site | File to download? | Owner-reported score | Estimated score | Unique vs the other focus sites? | Decision |
|---|---|---:|---|---|---|
| GEMSDOE24 | Research only (`-nan`) | 0.2477 | Not estimable | **No** (100% of positives within 3 px of GEMSDOE30) | **DO NOT SUBMIT** |
| GEMSDOE25 | Research only (`-nan`) | 0.2600 | Not estimable | **No** (positive set **identical** to GEMSDOE30 — submitting it would be an exact duplicate) | **DO NOT SUBMIT** |
| GEMSDOE27 | Research only (`-nan`) | 0.2449 | Not estimable | **No** (98.0% within 3 px of GEMSDOE24) | **DO NOT SUBMIT** |
| GEMSDOE28 | Research only (`-nan`) | 0.2710 | Not estimable | **No** (100% within 3 px of GEMSDOE30) | **DO NOT SUBMIT** |
| GEMSDOE30 | Research only (no encoding suffix; 0 NaN cells measured) | 0.2600 | Not estimable | **No** (100% within 3 px of GEMSDOE27; positive set **identical** to GEMSDOE25) | **DO NOT SUBMIT** |
| GEMSDOE31 | Research only (`-nan`) | 0.2708 | Not estimable | **No** (100% within 3 px of GEMSDOE30) | **DO NOT SUBMIT** |
| **GEMSDOE32** | Research only (`-zeros`) | **0.2778** (highest) | Not estimable | **No** (100% within 3 px of GEMSDOE36; exact subset of GEMSDOE31, 25, 30, 36) | **DO NOT SUBMIT** |
| GEMSDOE33 | Research only (outside encoding not in name) | 0.2632 | Not estimable | **No** (99.7% within 3 px of GEMSDOE27) | **DO NOT SUBMIT** |
| GEMSDOE36 | Research only (`-zeros`) | 0.2750 | Not estimable | **No** (97.6% within 3 px of GEMSDOE27) | **DO NOT SUBMIT** |

**Highest owner-reported file: GEMSDOE32, `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`, 0.2778.** It is the best-scoring file here, and it is not unique, so it cannot be submitted as a new entry. Its pinned SHA-256 was re-checked against the saved audit: `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9` (match).

Download links for research are in [`evidence/focus_audit.json`](../evidence/focus_audit.json). They are research archive only, not a submission recommendation.

## 2. Why GEMSDOE32 scored highest (verified from the bytes)

I re-measured all nine files from their pinned commits and checked the set relations directly.

- **GEMSDOE32 has 37,654 positive cells, and all of them are inside GEMSDOE31** (40,199 positives). The 2,545 cells in GEMSDOE31 that are not in GEMSDOE32 are exactly the difference (`GEMSDOE31 − GEMSDOE32 = 2,545`). This matches the repo's explanation in [`content/why-0.2778.md`](../content/why-0.2778.md) (base file with a subset removed; the "GEMSDOE28 H27-4 base" in that note has 40,199 positives, the same count as GEMSDOE31's file).
- **GEMSDOE32 is also an exact subset of GEMSDOE25, GEMSDOE30 and GEMSDOE36** (all positives inside each).
- **GEMSDOE25 and GEMSDOE30 have identical positive support** (44,090 cells each; each is inside the other). **GEMSDOE24 is an exact subset of GEMSDOE27.** Any new file that copies these supports would be a duplicate.
- Removing 2,545 cells from GEMSDOE31 moved the owner-reported score from 0.2708 to 0.2778 (+0.0070). That is a measured *pairing*, not a proven cause: no hidden labels are available here to confirm the mechanism.

**Plain reading:** the owner's explanation is that the pruning removed cells 1–2 px from a catalogue fault. That rule could not be re-measured here, because the catalogue raster is only available as a third-party mirror (see §5). The subset result is verified; the mechanism is the owner's explanation, not verified.

## 3. Format check: why "Predicted values must be in range [0, 1]" can appear

Strict check, whole array (not just the footprint): finite, inside [0, 1], single band, EPSG:32611, 100 m transform, same shape.

| Site | NaN cells (whole array) | Strict [0,1] check, whole array | Verdict |
|---|---:|---|---|
| GEMSDOE24, 25, 27, 28, 31 (`-nan` files) | **7,111,787** each | **FAIL** (NaN is not in [0,1]) | Likely source of the portal error, if the portal's range test counts NaN |
| GEMSDOE32, 36 (`-zeros`); GEMSDOE30, 33 (no suffix) | 0 | PASS (values are finite) | Passes this check |

**Irregularity (flag for review):** the official format text says outside-bounds cells must be **null or NaN** (`evidence/official_source_check_2026-10-28.json`). The `-nan` files follow that text and fail the range check. The `-zeros` files pass the range check but use finite 0 outside, which the text does not list. **The two requirements conflict, and the portal's real behavior is unknown.** Resolving it needs either a documented answer from DrivenData or a deliberate test upload, and a test upload uses one of the 3 weekly slots. Not done here.

## 4. Estimate and projection (labelled so it is not misread)

- **Holdout-DTI: not run for any file.** Reason: no competition labels in this sandbox (HTTP 000 on DrivenData and Dropbox).
- **Ledger projection (NOT a score):** `docs/data/nine_site_table.json` gives 0.327–0.360 for these files. It is a model fit to owner-reported scores (CV MAE 0.037). Those projections sit above every owner-reported value in this set, so they are extrapolation. **Do not use them as an estimate.**
- **Leaderboard references:** the request cites 0.4413 (top) and 0.3195. The saved 2026-10-28 capture says rank 1 = 0.4544 and rank 26 = 0.3195 ([`evidence/leaderboard_observation_2026-10-28.json`](../evidence/leaderboard_observation_2026-10-28.json)). The live leaderboard could not be re-read from this sandbox. **Flagged: the figures disagree.**

## 5. Irregularities for manual review

1. **Third-party data.** The "competition data" in `data/` comes from an owner mirror (`scripts/download_competition_data.sh`), not from DrivenData. The owner's `labels.tif` is byte-identical to `existing_faults.tif` (recorded earlier as IR-29-03). Its origin is unverified. **Not used as ground truth here.**
2. **Template footprint.** `data/template_grid.tif` has 12,279,160 finite cells, all zero (IR-29-01). It does not match the claimed footprint of 5,167,373.
3. **Live homepage is stale.** The committed `docs/index.html` says "1 generated … Unique TIFF generated", which contradicts the release gate ("0 candidates"). The generator (`scripts/build_site.py`) renders the current fail-closed text. The committed `docs/` and the test expectations are from different revisions. Two tests fail on the clean tree (`test_published_index_states_not_ok_to_submit`, `test_latest_upstream_identity_feed_is_published_and_never_implies_approval`). I did not regenerate the site in this session.
4. **Tests rewrite tracked files.** Running `pytest` rewrites nine tracked `docs/` pages as a side effect. I reverted them. Fix: make tests write to a temp directory.
5. **Deadline conflict** (IR-29-05). The homepage says 2026-12-03 23:59 UTC; the rules say 5:00 p.m. ET. The earlier time is assumed.
6. **Catalogue not re-verified.** The "removed cells are 1.4–2 px from catalogue faults" claim is not checked here, because the catalogue is only a third-party mirror.

## 6. What is needed to clear a file

**Owner decision (required before any candidate):** pick one, recorded in the protocol.

- **A. Keep the literal rule.** No file is ever cleared under the current registry.
- **B. Redefine the dot set for the dense witness** (top-N or ≥0.5 cells) and re-run the uniqueness audit with the lattice class reported separately. Per [`knowledge/session-review-2026-10-29-witness.md`](session-review-2026-10-29-witness.md), this alone still does not clear the invdesign candidate.
- **C. Exclude dense and lattice comparators** (the 2026-10-28 convention). Requires a documented owner decision.

**Data (owner, from your own DrivenData login):** download the competition files and place them under `data/` as the reference notebook expects (`numeric_features.tif`, `labels.tif`), plus the sample submission. Source: [reference solution README](https://github.com/drivendataorg/gems-prize-reference-solution).

**Then, in order:** holdout (HOLDOUT-DTI with withheld count and 95% CI) → one candidate → strict format check → uniqueness check (≤70% within 3 px, plus the correlation check) → a human selector decides on a slot (3 per week, 1 final across both rounds).

## 7. Official sources (for manual review)

- [Competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/) · [problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) · [data (login)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) (checked earlier; not reachable from this sandbox on 2026-10-31)
- [Reference solution (read 2026-10-31)](https://github.com/drivendataorg/gems-prize-reference-solution) — `unet-mc-cv-reference-solution.ipynb`: input names `data/numeric_features.tif` and `data/labels.tif`; trains with a Tversky loss (α=0.2, β=0.8) and outputs sigmoid probabilities. Its "scoring metrics" are internal validation; it does **not** implement the competition's DTI scorer.
- [Staff: known-fault masking](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516) (cited in the 2026-10-29 summary)
- Owner files and commits: pinned in [`evidence/focus_audit.json`](../evidence/focus_audit.json)

---

*Not in this summary: no slot selection, no upload, no organizer receipt, no holdout score, and no candidate TIFF.*
