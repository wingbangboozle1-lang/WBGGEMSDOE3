# LST1 — historical research record (DO NOT SUBMIT)

> **Decision: DO NOT SUBMIT.** This is a superseded research lane, not a current candidate. Its historical uniqueness claim relied on a lattice-null exception that is not in the binding literal rule. The reclassified run card fails the literal registry gate; there is no selector approval, no organizer receipt, and no leaderboard score estimate.
>
> Current project-wide decision and evidence: [README.md](README.md), [three-pass review](evidence/review_passes.md), and [current run card](evidence/run_card.json). This LST1 record is retained for audit/education only.

## Artifact identity — research only

- Historical artifact identifier: `wbggems3-lst1-hybrid-20261026-0a0229da`. Do not reuse it as a submission name.
- Historical note: `LST1 historical research artifact; fails the literal registry-overlap rule; not approved for upload.`. Do not paste this into a submission form.
- Historical file/evidence links, if present, are exposed from [`docs/lst1/`](docs/lst1/index.html) as research-only downloads. The current repository makes no claim that these bytes are unique or accepted by the organizer.
- Literal registry overlap gate in the historical run card: **FAIL**. `ready_to_submit` is **false** after strict reclassification; selector approval is **false**.

## Performance evidence — historical, not a leaderboard estimate

The archived record labels this as **HOLDOUT-DTI**, evaluator `GEMSDOE32-HIDE-RECOVER-v3.0`, with 22232 withheld positive pixels. Historical candidate value: `0.06667963650357954`; 95% CI `[0.05687878008106799, 0.07654650125890987]`. Historical champion-proxy value: `0.09920232315251679`; 95% CI `[0.08595140754809347, 0.11266835751415871]`; paired delta `-0.032522686648937274`; 95% CI `[-0.04103065991359588, -0.02372020631208074]`.

This result uses legacy evaluator `GEMSDOE32-HIDE-RECOVER-v3.0`, not the currently prescribed shared `gems57-pooled-hide-v2`; it cannot be treated as a current-protocol validation or a public/private leaderboard estimate. No score is inferred from it. The raw ledger-model projection retained in archived diagnostics is explicitly **NOT_A_SCORE** and is quarantined from current-facing pages.

## Method and status

The LST1 method and its shortcomings are documented in `knowledge/`, `content/`, and the archived JSON artifacts. It has not been reproduced in this review. Its historical budget record exceeds the standing experiment limit; no additional experiment or slot was used in this review. The required universal-witness stop prevents candidate construction, holdout runs, and TIFF writing under the current literal protocol.

The H33/B2 value mentioned in repository records remains an **unverified owner/user-reported claim**, not an organizer receipt tied to a specific uploaded SHA-256. Raster comparison can document a pruning operation but cannot prove score causality or show that a distinct method improves the result. Current improvement potential is **unknown / not estimable**.

## Safe checks and restoration

```bash
.venv/bin/python -m pytest -q
python scripts/build_site.py && python scripts/check_site.py
bash scripts/restore_shared_data.sh --template-only
bash scripts/restore_shared_data.sh --dry-run
```

Do not run the retired candidate generator (`scripts/build_submission.py`), any holdout script, or a slot selector without an explicit protocol resolution and authorization. Full shared-data restoration downloads a hash-pinned public mirror, not an organizer-authenticated dataset; it is not needed to resolve the present stop.

## Official references (links only; not fetched during the current review)

- [DrivenData competition](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Official metric and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official competition overview and data](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [Official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

These links are not evidence of current account quota, live leaderboard values, or acceptance of any historical file.
