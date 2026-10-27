"""Fail-closed global release gate for competition artifacts.

A lane-level card can describe a useful experiment, but it cannot authorize an
upload.  The public site must only display an upload action when the governing
run card records an explicit selector approval for the exact saved bytes and
all mandatory evidence classes are present.
"""
from __future__ import annotations

from typing import Any


REQUIRED_HOLDOUT_LABEL = "HOLDOUT-DTI"


def evaluate_release_gate(authority: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Return a serialisable, fail-closed release decision.

    ``authority`` is the repository-level run card.  ``candidate`` is a
    lane-specific card.  A candidate with a local format pass or a proxy metric
    remains research-only unless *all* release predicates pass.
    """
    reasons: list[str] = []
    candidate_sha = candidate.get("sha256") or candidate.get("raster_sha256")
    candidate_name = candidate.get("submission") or candidate.get("submission_name")
    holdout = candidate.get("holdout_result") or candidate.get("holdout_dti") or {}
    label = str(holdout.get("label", ""))

    if authority.get("verdict") != "promote":
        reasons.append("The governing run card verdict is not promote.")
    if authority.get("selector_approval") is not True:
        reasons.append("No separate selector approval is recorded.")
    if not candidate_sha:
        reasons.append("The candidate card does not identify immutable raster bytes.")
    if authority.get("raster_sha256") != candidate_sha:
        reasons.append("The governing run card does not approve this candidate SHA-256.")
    if candidate.get("verdict") != "promote":
        reasons.append("The candidate lane itself is not marked promote.")
    if not label.startswith(REQUIRED_HOLDOUT_LABEL):
        reasons.append("The candidate has no compliant HOLDOUT-DTI result; PROXY-DTI is not a release metric.")

    # A card may explicitly expose a literal gate.  Its failure must never be
    # hidden by a separate content-aware or density-adjusted diagnostic.
    uniqueness = candidate.get("uniqueness") or candidate.get("registry") or {}
    literal_pass = uniqueness.get("literal_pass")
    if literal_pass is not True:
        reasons.append("The candidate does not record a passing literal all-registry uniqueness gate.")

    approved = not reasons
    return {
        "schema": "gems-release-gate-v1",
        "decision": "SUBMIT" if approved else "DO-NOT-SUBMIT",
        "okay_to_submit": approved,
        "okay_to_download_for_research": bool(candidate_name and candidate_sha),
        "candidate": {
            "submission": candidate_name,
            "sha256": candidate_sha,
            "lane_verdict": candidate.get("verdict"),
            "holdout_label": label or None,
            "literal_registry_pass": literal_pass,
        },
        "authority": {
            "verdict": authority.get("verdict"),
            "selector_approval": authority.get("selector_approval"),
            "raster_sha256": authority.get("raster_sha256"),
        },
        "blocking_reasons": reasons,
    }
