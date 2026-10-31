"""Load the current, qualitative GEMS research hypotheses.

This module deliberately does not contain numeric DTI projections. Earlier
hypothesis drafts in this file contained unsupported numeric score ranges and
are retired. The current source of truth is the dated, evidence-bound
preregistration in evidence/preregistration_2026-10-31.json.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION = ROOT / "evidence" / "preregistration_2026-10-31.json"


def load_hypotheses() -> list[dict]:
    return json.loads(PREREGISTRATION.read_text(encoding="utf-8"))["hypotheses"]


def list_hypotheses() -> None:
    for hypothesis in load_hypotheses():
        print(
            f"{hypothesis['rank']} | {hypothesis['id']} | {hypothesis['name']} | "
            f"{hypothesis['expected_gain_vs_cost']} | "
            f"cost={hypothesis['implementation_cost']} | NOT RUN"
        )


if __name__ == "__main__":
    list_hypotheses()
