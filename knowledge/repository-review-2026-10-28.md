# Repository review — 2026-10-28

## Executive finding

**No file is cleared for submission by the strict request in this session. Do not click submit based on the current landing page.** The site currently advertises `wbggems3-invdesign-anchor-20k-zeros.tif` with a green **SUBMIT** banner and an ESTIMATE near 0.47. That publication state conflicts with the latest conservative review evidence and with the user's explicit protocol: the candidate has no compliant whole-segment buffered HOLDOUT-DTI, the literal registry rule has a documented full-footprint witness that makes all nonempty in-footprint supports fail, and the separate selector must decide whether to spend a slot. The file-format check and site consistency check are not scientific validation or organizer acceptance.

This is an audit finding, not a new experiment, a competition score, or approval to upload. No TIF was created, altered, selected, or uploaded in this review.

## Directly verified repository facts

| Finding | Repository evidence | Interpretation |
|---|---|---|
| The primary page claims “SUBMIT THIS FILE” and estimate 0.47 | `docs/index.html`, `docs/executive-summary.html` | Potentially unsafe: claim is stronger than available protocol-compliant evidence. |
| The published release gate says `SUBMIT` | `docs/data/release_gate.json`; enforced by `scripts/check_site.py` | The checker validates agreement with its chosen evidence cards; it does not validate whether the required hide-and-recover experiment was run. |
| The inverse-design run card reports `holdout_dti: null` and expressly says no compliant holdout was run | `evidence/run_card_v3.json` | Cannot satisfy the user's prerequisite to beat the current holdout best. Its fitted-score validation is not a replacement for HOLDOUT-DTI. |
| Its score of about 0.47 is an estimate, not an organizer-confirmed score | `evidence/run_card_v3.json`; no submission receipt is recorded | Must not be presented as a confirmed score. The user's requirement to label estimates correctly is important here. |
| Another independent review card is `negative`, records zero experiments, no candidate, and no new TIF | `evidence/review_2026-10-28.json` and `evidence/review_2026-10-28_run_card.json` | Conflicts with the positive root-site decision; site-level authority is not reconciled. |
| Registry evidence contains a witness positive on every cell in the mirrored footprint | `evidence/review_2026-10-28_run_card.json` and referenced prior witness evidence | Under the literal positive-support interpretation, this makes any non-empty candidate fail the stated directed-overlap limit. The witness scope/provenance caveat remains documented; this is not proof the whole registry is correctly represented. |
| The KHD experiment is negative on its stated holdout | `evidence/khd_run_card.json` | KHD's paired delta vs B2 is negative, `-0.00446`, with stated 95% CI `[-0.00522, -0.00375]`; this is HOLDOUT-DTI for that evaluator/fold, not a leaderboard score. |
| Site check passes | `python scripts/check_site.py` | This verifies internal consistency of the positive release gate, not that gate's scientific sufficiency. |
| Tests could not be run in this checkout | `python -m pytest -q` returned `No module named pytest`; no `.venv` is present | Test status is **not run**, not passing or failing. Install project test dependencies before claiming a passing test run. |

## Review of the nine focus sites

The existing root README and executive-summary page include a nine-site table for GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 and 36. Listed scores are explicitly marked owner-reported rather than organizer receipts. The supplied user table identifies GEMSDOE32 H33-B2 at 0.2778 as highest among the specified submissions; this session did not fetch and independently verify all remote pages (outbound access to the listed sites is not guaranteed here). The exact causal explanation for 0.2778 is not established. Repository byte comparisons support a sparse-pruning/subset relationship, but without truth labels and a receipt-to-hash link this is a mechanism hypothesis, not proof of why the organizer assigned that score.

**Do not infer that the 0.47 model estimate is likely to beat 0.2778.** Its confidence interval is broad and its stated calibration comes from published/owner-reported probes, while the required holdout is absent. Also, the public leaderboard figures in the prompt are time-sensitive; no current leaderboard was verified in this review.

## Required repair before the site can advertise a submission

1. Replace the green submission CTA with a prominent **NOT CLEARED — DO NOT SUBMIT** status until a candidate passes all required gates.
2. Make the publication checker derive clearance from one hash-bound authority card that requires: assigned lane, <=3 experiments / <=2 hours, per-feature leakage canaries, fold-local whole-segment buffered hide-and-recover using the shared evaluator, positive paired HOLDOUT-DTI improvement over the frozen baseline with 95% CI, pre-placement and final uniqueness tests against the agreed complete registry, independent saved-byte format validation, and selector approval kept separate.
3. Resolve the contradiction between the full-footprint registry witness and the sparse/content-aware alternative. Do not silently switch overlap definitions or exempt a registry raster. Document protocol revision and scope before running candidate generation.
4. Stop calling files “submission-ready” solely because GeoTIFF format checks pass. A passing file-format check is necessary but not sufficient.
5. Ensure current pages and generated pages both reflect the same authority; tests should fail if any main page says SUBMIT while the authoritative card is negative or missing.
6. Re-run tests in an environment with the dependencies installed. Keep full suite results separate from any HOLDOUT-DTI evidence.

## Suggested next research sequence (not executed)

The repo has several candidate-method notes. Do not start another geological experiment until the assignment lane is unambiguous and the literal uniqueness contradiction is resolved. Then restore the authenticated template feature stack, shared holdout inputs, labels and fault-segment geometry; establish a frozen baseline; preregister at most three feature tests; run single-feature leakage canaries before combined scoring; run the shared evaluator; report the exact number of withheld positives and paired spatial-block CI. External-data hypotheses should proceed only after provenance, CRS, coverage, license, and obtainability are verified from official sources.

## Sources/manual review

- Competition overview: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Competition rules: https://www.drivendata.org/competitions/306/competition-doe-gems/
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- USGS GeoDAWN source: https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- DOE GDR INGENIOUS submission: https://gdr.openei.org/submissions/1391
- Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/

The URLs are provided for manual source review. This session did not claim that external webpages were freshly verified.
