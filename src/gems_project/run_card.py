"""Create a negative preflight card; no invented candidate or holdout values."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def make_card(audit_path: Path) -> dict:
    raw = Path(audit_path).read_bytes()
    audit = json.loads(raw)
    if audit.get("status") != "STOP_DUPLICATE_UNIVERSAL_WITNESS" or not audit["witness"].get("universal_blocker"):
        raise ValueError("a universal stop must be proven before this negative card is emitted")
    card = {
        "evidence_class": "NEGATIVE preflight, not a competition score",
        "hypothesis": "CSPES: cross-scale collinear gravity and reduced-to-pole magnetic gradient edges, conditioned on detrended elevation.",
        "mechanism": "A persistent multi-domain discontinuity may mark a buried structural boundary lacking a surface catalogue trace.",
        "named_non_fault_mimic": "Lithologic contact or aeromagnetic survey stripe.",
        "holdout_dti": {"label": "HOLDOUT-DTI", "value": None, "evaluator_version": "gems57-pooled-hide-v2 (planned, not run)",
                        "withheld_positives": None, "ci_95": None,
                        "reason": "Mandatory universal-registry STOP occurred before a surface, canary, placement, or holdout."},
        "correlation_overlap_vs_registry": {"surface_spearman": None, "final_dot_overlap": None, "candidate_tested": False,
            "witness_positive_inside_fraction": audit["witness"]["inside_fraction"],
            "witness_implied_overlap_for_any_nonempty_in_footprint_candidate": 1.0,
            "witness_sha256": audit["witness"]["sha256"],
            "registry_coverage": "One registered witness proves failure; the current full registry was not exhaustively re-audited."},
        "raster_sha256": None,
        "validator_output": {"status": "NOT_RUN: no new candidate raster exists",
            "required": "No NaN in footprint; values in [0,1]; single float32 band; CRS, shape and affine equal verified sample."},
        "submission_name": None,
        "submission_note": "No candidate; mandatory registry duplicate stop. DO NOT SUBMIT.",
        "verdict": "negative", "selector_approval": False, "experiments": 0, "slots_spent": 0,
        "run_time_utc": audit["checked_utc"],
        "source_audit_sha256": hashlib.sha256(raw).hexdigest(),
        "follow_up": "Resolve the literal registry support definition by explicit protocol revision; reconcile the shared tool's one-sided rho and outside-footprint convention upstream; then rerun canaries, blocked holdout, registry checks and validation.",
    }
    # Concurrent work is preserved and audited, but is not this lane's candidate.
    concurrent_path = Path(audit_path).with_name("concurrent_audit.json")
    if concurrent_path.exists():
        concurrent_raw = concurrent_path.read_bytes()
        concurrent = json.loads(concurrent_raw)
        step = concurrent["artifacts"]["step_zeros"]
        if (step["forward_overlap_registered_witness"] <= 0.70
                or step["eligible_to_submit"] or step["shared_format_report"]["ok"]):
            raise ValueError("parallel audit no longer supports the recorded negative decision")
        card["parallel_artifact_review"] = {
            "evidence_sha256": hashlib.sha256(concurrent_raw).hexdigest(),
            "reviewed_sha256": step["sha256"],
            "forward_overlap_vs_registered_witness": step["forward_overlap_registered_witness"],
            "outside_mirrored_footprint": step["outside_mirrored_footprint"],
            "verdict": "negative; research only, not this lane's candidate",
        }
    if len(card["submission_note"]) > 140:
        raise ValueError("note is longer than the project limit")
    return card
