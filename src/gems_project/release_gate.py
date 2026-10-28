"""Fail-closed project release gate. This is not an organizer validator.

Evidence must be independently collected and bound to saved bytes by the caller;
this schema check alone is not a substitute for replaying scientific audits.
A lane-local verdict, an estimate, or a format pass cannot select a weekly slot.
"""
from __future__ import annotations

import math
import re
from typing import Any

SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _number(value: Any, low: float, high: float) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and low <= value <= high)


def _interval(value: Any, low: float, high: float) -> bool:
    return (isinstance(value, (list, tuple)) and len(value) == 2
            and all(_number(x, low, high) for x in value) and value[0] <= value[1])


def _mapping(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def evaluate_release_gate(authority: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Reconcile one candidate with a separate, exact-byte selector authorization.

    Canonical prospective evidence fields are documented in knowledge/protocol.md.
    Old lane cards do not become approvable merely by changing their verdict: all
    missing, malformed, false, and truthy-but-not-boolean gates fail closed.
    """
    reasons: list[str] = []
    candidate_sha = candidate.get("sha256") or candidate.get("raster_sha256")
    candidate_name = candidate.get("submission") or candidate.get("submission_name")
    note = candidate.get("submission_note") or candidate.get("note")
    holdout = _mapping(candidate.get("holdout_result") or candidate.get("holdout_dti"))
    label = holdout.get("label")

    if authority.get("verdict") != "promote":
        reasons.append("The governing run card verdict is not promote.")
    if authority.get("selector_approval") is not True:
        reasons.append("No separate selector approval is recorded.")
    if not isinstance(candidate_sha, str) or not SHA256.fullmatch(candidate_sha):
        reasons.append("The candidate does not identify a valid SHA-256 digest.")
    if authority.get("raster_sha256") != candidate_sha or not candidate_sha:
        reasons.append("The governing run card does not approve this candidate SHA-256.")
    if candidate.get("verdict") != "promote":
        reasons.append("The candidate lane itself is not marked promote.")
    if not isinstance(candidate_name, str) or not candidate_name.strip() or len(candidate_name) > 140:
        reasons.append("The candidate has no valid submission name.")
    if not isinstance(note, str) or not note.strip() or len(note) > 140:
        reasons.append("The submission note is missing or exceeds 140 characters.")

    value, ci = holdout.get("value"), holdout.get("ci95")
    n = holdout.get("withheld_positives")
    paired = holdout.get("paired_delta_ci95")
    baseline = holdout.get("matched_baseline_dti")
    if (label != "HOLDOUT-DTI" or not isinstance(holdout.get("evaluator_version"), str)
            or not holdout["evaluator_version"].strip()
            or not isinstance(n, int) or isinstance(n, bool) or n <= 0
            or not _number(value, 0, 1) or not _interval(ci, 0, 1)
            or not ci[0] <= value <= ci[1]
            or holdout.get("fold_local_catalogue_features") is not True
            or holdout.get("matched_incumbent_folds") is not True
            or not _number(baseline, 0, 1) or value <= baseline
            or not _interval(paired, -1, 1) or paired[0] <= 0):
        reasons.append("A comparable fold-local HOLDOUT-DTI, evaluator, positive count, CI and positive paired improvement are not all established.")

    canary = _mapping(candidate.get("canary"))
    count, tested = canary.get("n_features"), canary.get("n_features_tested")
    if (canary.get("all_features_tested") is not True
            or not isinstance(count, int) or isinstance(count, bool) or count <= 0
            or not isinstance(tested, int) or isinstance(tested, bool) or tested != count
            or not _number(canary.get("max_auc"), 0, 0.90)):
        reasons.append("A complete per-feature leakage canary is missing or exceeds the threshold.")

    uniqueness = _mapping(candidate.get("uniqueness") or candidate.get("registry"))
    literal_pass = uniqueness.get("literal_pass")
    expected, checked = uniqueness.get("registry_expected"), uniqueness.get("registry_checked")
    if (literal_pass is not True or uniqueness.get("complete_registry") is not True
            or not isinstance(expected, int) or isinstance(expected, bool) or expected <= 0
            or not isinstance(checked, int) or isinstance(checked, bool) or checked != expected):
        reasons.append("The candidate does not record a complete passing literal all-registry uniqueness gate.")
    for name in ("surface", "final"):
        phase = _mapping(uniqueness.get(name))
        if (phase.get("passed") is not True
                or not _number(phase.get("max_abs_spearman"), 0, 0.90)
                or not _number(phase.get("max_dot_overlap"), 0, 0.70)):
            reasons.append(f"The {name} phase lacks passing literal correlation and overlap measurements.")

    validation = _mapping(candidate.get("validator"))
    required = ("passed", "single_band", "dtype_float32", "no_inf", "no_nan_inside_footprint",
                "values_in_0_1", "crs_shape_transform_match", "outside_footprint_compliant",
                "saved_bytes_equal_audited_dots")
    footprint_sha = validation.get("reference_footprint_sha256")
    outside_policy = validation.get("outside_footprint_policy")
    positives = validation.get("positive_cells_inside_footprint")
    if (any(validation.get(key) is not True for key in required)
            or validation.get("sha256") != candidate_sha or not candidate_sha
            or not isinstance(footprint_sha, str) or not SHA256.fullmatch(footprint_sha)
            or not isinstance(outside_policy, str) or not outside_policy.strip()
            or not isinstance(positives, int) or isinstance(positives, bool) or positives <= 0):
        reasons.append("Saved-byte format validation is missing, incomplete, or bound to different bytes.")

    approved = not reasons
    return {
        "schema": "gems-release-gate-v1",
        "decision": "SUBMIT" if approved else "DO-NOT-SUBMIT",
        "okay_to_submit": approved,
        "okay_to_download_for_research": bool(candidate_name and candidate_sha),
        "candidate": {"submission": candidate_name, "sha256": candidate_sha,
                      "lane_verdict": candidate.get("verdict"), "holdout_label": label,
                      "literal_registry_pass": literal_pass},
        "authority": {"verdict": authority.get("verdict"),
                      "selector_approval": authority.get("selector_approval"),
                      "raster_sha256": authority.get("raster_sha256")},
        "blocking_reasons": reasons,
    }
