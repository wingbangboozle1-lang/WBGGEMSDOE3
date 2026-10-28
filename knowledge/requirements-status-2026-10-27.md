# Requirements status — 2026-10-27

> **Historical parallel-session snapshot, not the current decision.** The current review did not obtain the full verbatim source prompt, verify all official sources, assign a method lane, run canaries or a compliant holdout, or generate a cleared candidate. A proposed registry exemption is not an authorized protocol change. See `knowledge/session-review-9b794637.md` and the current `README.md`.

Condensed from the project brief (full standing instructions: README §"Project prompt").
Status words: **DONE** (evidence in repo), **PARTIAL**, **BLOCKED** (cannot be done under the stated rules), **NOT DONE**.

| # | Requirement | Status | Evidence / note |
|---|---|---|---|
| 1 | Review the repo; executive summary for the nine focus sites, best file per site, estimate or "not estimable", uniqueness vs the others, download/do-not-submit decision in a table | DONE | `docs/index.html` (Verified 2026-10-27 section, nine-site table); `knowledge/verification-2026-10-27.md` |
| 2 | Genuinely unique, downloadable GeoTIFF that beats 0.2778 and ideally the leaderboard high | **PARTIAL** | Download review copy `wbggems3-sgce-20261027-f52d35d8-nan.tif` (official NaN encoding; SHA-256 `6b53c77b…`). Unique vs the nine focus files (max 16.7 %). **Not submit-cleared**: literal gate fails (IR-28-09), gate not regenerated (IR-28-10), no portal test (IR-28-13). Projection 0.0669, so **not projected to beat 0.2778** (IR-28-07). |
| 3 | Explain why GEMSDOE32 scored well | PARTIAL | Raster change verified (2,545 dots removed near mirrored catalogue; subset of GEMSDOE31). H6-1 proxy cannot identify the near-catalogue live regime; owner gap unexplained (IR-13). |
| 4 | Line-by-line work with official sources and links; no hallucinations | DONE | `knowledge/verification-2026-10-27.md` §1 with links to the official problem page, rules PDF and leaderboard |
| 5 | Flag irregularities | DONE | `knowledge/review-and-irregularities-2026-10-27.md` (IR-09 to IR-19) |
| 6 | Label every number HOLDOUT-DTI or ORGANIZER-CONFIRMED; never present a projection as a score | DONE | Labels in verification doc §3–4 and site; no organizer-confirmed score exists in this sandbox |
| 7 | Parallel-run protocol (LANE, REUSE, LABEL, LEAKAGE CANARY, RUN CARD, BUDGET) | DONE (no lane run) | `evidence/session_run_card_2026-10-27.json`; experiments 0 of 3; canary (AUC ≤ 0.90) in H6-1 |
| 8 | Generate 3–5 ranked geological hypotheses and validate the top one on a spatially blocked holdout before any slot | PARTIAL | Ranked list in `knowledge/preregistration-2026-10-26.md` and `research/REVIEW.md`. Top lane (CSPES) not run this session (budget rule and gate block). |
| 9 | Keep the prompt in the README and read it each session | DONE | README §"Project prompt" retained; session section added |
| 10 | GitHub Pages site with one-click download and an executive summary subpage on how to submit (error text, unique name, comment ≤ 140 chars) | PARTIAL (updated 2026-10-27: download is the official-encoding file; banner follows the gate; stale submit pages regenerated, see IR-28-01/02/03) | `docs/executive-summary.html` has the error text and the 140-character rule. No approved download exists, so the one-click download offers only the audit JSON. |
| 11 | Multi-pass review; PR; merge to main; list remaining work and limitations | IN PROGRESS | See PR and final report |
| 12 | Never present an owner report as organizer-confirmed; never upload or select a slot without authorisation | DONE | Slots 0; owner figures labelled OWNER-REPORTED |
| 13 | No manual geological inspection for checks | DONE | Raster checks are automated; any revision of the blocking protocol still requires explicit authorization |

## Open items (for the user)

- Ratify the content-aware uniqueness reading (IR-28-09). Without it the submission stays blocked.
- Authorise regeneration of the release gate for the SGCE SHA-256 (IR-28-10).
- Run one portal test with the NaN file after ratification and record the response (IR-28-13).

- Decide the definition of "dot" for the uniqueness gate (IR-11). Options are in the final report.
- Run one portal test with an authenticated account to resolve the range error (IR-14) and whether zeros outside bounds are accepted (IR-15).
- Confirm whether the owner can supply a submission-page receipt for 0.2778 (IR-13, IR-17).
