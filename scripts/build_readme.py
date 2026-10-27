#!/usr/bin/env python3
"""Build a fail-closed, research-only LST1 handoff from its historical evidence."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rc = json.loads((ROOT / "evidence/lst1_run_card.json").read_text())
hold = rc.get("holdout", {})
candidate = hold.get("candidate", {})
champion = hold.get("champion_proxy", {})
paired = hold.get("paired_delta_vs_champion_proxy") or {}
ci = paired.get("ci95", [None, None])
name = rc.get("submission_name", "unknown")
note = rc.get("submission_note", "")
literal_pass = bool(rc.get("registry_audit", {}).get("literal_rule_pass", False))

text = f"""# LST1 — historical research record (DO NOT SUBMIT)

> **Decision: DO NOT SUBMIT.** This is a superseded research lane, not a current candidate. Its historical uniqueness claim relied on a lattice-null exception that is not in the binding literal rule. The reclassified run card fails the literal registry gate; there is no selector approval, no organizer receipt, and no leaderboard score estimate.
>
> Current project-wide decision and evidence: [README.md](README.md), [three-pass review](evidence/review_passes.md), and [current run card](evidence/run_card.json). This LST1 record is retained for audit/education only.

## Artifact identity — research only

- Historical artifact identifier: `{name}`. Do not reuse it as a submission name.
- Historical note: `{note}`. Do not paste this into a submission form.
- Historical file/evidence links, if present, are exposed from [`docs/lst1/`](docs/lst1/index.html) as research-only downloads. The current repository makes no claim that these bytes are unique or accepted by the organizer.
- Literal registry overlap gate in the historical run card: **{"PASS" if literal_pass else "FAIL"}**. `ready_to_submit` is **{"true" if rc.get("ready_to_submit") else "false"}** after strict reclassification; selector approval is **false**.

## Performance evidence — historical, not a leaderboard estimate

The archived record labels this as **HOLDOUT-DTI**, evaluator `{hold.get("evaluator", "not recorded")}`, with {hold.get("withheld_positive_pixels", "an unrecorded number of")} withheld positive pixels. Historical candidate value: `{candidate.get("dti")}`; 95% CI `{candidate.get("ci95")}`. Historical champion-proxy value: `{champion.get("dti")}`; 95% CI `{champion.get("ci95")}`; paired delta `{paired.get("delta")}`; 95% CI `{ci}`.

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
"""
(ROOT / "LST1_README.md").write_text(text, encoding="utf-8")
print("LST1_README written", len(text))
