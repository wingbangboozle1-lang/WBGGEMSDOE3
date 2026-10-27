#!/usr/bin/env python3
"""Reclassify a retired historical LST1 lane; this script never grants readiness.

Legacy format, overlap, canary, and holdout results are kept as diagnostics only.
Current literal uniqueness, complete registry scope, current shared evaluation,
current file validation, and separate selector approval are all required for a
new candidate; LST1 has none of those clearances and is permanently DO NOT SUBMIT.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ev = ROOT / "evidence"
b = json.load(open(ev / "build_result.json"))
h = json.load(open(ev / "holdout_results.json"))
fit = json.load(open(ev / "lst_fit.json"))
can = json.load(open(ev / "field_canary.json"))
u = b["uniqueness"]
val = b["validation"]
name = b["name"]
generated_utc = datetime.now(timezone.utc).isoformat()
NOTE = "LST1 historical research artifact; fails the literal registry-overlap rule; not approved for upload."
assert len(NOTE) <= 140, len(NOTE)
cand = h.get("lst_mod_quota", {})
pd = cand.get("paired_vs_champion_proxy", {})
literal_unique = bool(u.get("U3_literal_pass", False)
                      and u.get("U3_literal_scope_complete", False))
selector_approval = False
legacy_performance_win = bool(pd) and pd["ci95"][0] > 0
legacy_diagnostics = {
    "D1_historical_local_format_validator_pass": all(v["passed"] for v in val.values()),
    "D2_historical_exact_mask_subset_pass": bool(u.get("U1_pass", False)),
    "D3_historical_rank_subset_pass": bool(u.get("U2_pass", False)),
    "D4_historical_nonlattice_overlap_subset_pass": bool(u.get("U3_pass_nonlattice", False)),
    "D5_lattice_excess_legacy_diagnostic_only": bool(u.get("U3_lattice_excess_pass", False)),
    "D6_historical_feature_canary_pass": bool(can.get("all_pass", False)),
    "D7_historical_holdout_promotion_rule_pass": legacy_performance_win,
}
gates = {
    "G1_literal_overlap_le_0.70_for_every_registry_raster": literal_unique,
    "G2_registry_scope_complete_and_authenticated": bool(u.get("U3_literal_scope_complete", False)),
    "G3_current_shared_evaluator_result_available": False,
    "G4_current_candidate_file_validation_available": False,
    "G5_separate_selector_approval": selector_approval,
}
gate_status = {
    "G1_literal_overlap_le_0.70_for_every_registry_raster": "FAIL",
    "G2_registry_scope_complete_and_authenticated": "FAIL / INCOMPLETE",
    "G3_current_shared_evaluator_result_available": "NOT RUN",
    "G4_current_candidate_file_validation_available": "NOT RUN",
    "G5_separate_selector_approval": "NOT APPROVED",
}
ready = False  # LST1 is retired; no historical evidence can make it submission-ready.
promote = False
verdict = "NEGATIVE: retired LST1 research artifact; literal registry clearance fails; no upload approval."
card = dict(
    run_card_version="1", lane="WBGGEMSDOE3 / lst1", generated_utc=generated_utc,
    record_kind="HISTORICAL_LANE_RECLASSIFICATION", slot_selected=False,
    hypothesis="W1': hidden-truth density is identified by the live ledger only at the (catalogue-distance x H19-5-distance) stratum level; "
               "an allocation that keeps <=62% of dots on the H19-5 network and ranks the rest by a catalogue-trained naive-Bayes modulation can be unique AND hold-out-competitive.",
    mechanism="(1) 112 hash-verified live-scored rasters -> exact linear equations in TPw/M/|G| per stratum (NNLS, bootstrap lower-confidence-bound lambda); "
              "(2) Dinkelbach batch-greedy placement of 3-px-spaced dots, B=2 pruning, on/off-network quota; (3) uniqueness repair via avoid-zone of dense prior rasters.",
    mimic_process="No raster was copied. Dots are re-placed from a density map. The H19-5 network is used only as a nuisance stratum and as an overlap cap (never as a feature).",
    holdout=dict(label="HOLDOUT-DTI", evaluator=cand.get("evaluator"),
                 withheld_positive_pixels=cand.get("n_withheld"),
                 candidate=dict(dti=cand.get("pooled_dti"), ci95=cand.get("ci95")),
                 champion_proxy=dict(dti=h.get("champion_proxy", {}).get("pooled_dti"), ci95=h.get("champion_proxy", {}).get("ci95")),
                 paired_delta_vs_champion_proxy=pd, variants={k: dict(dti=v["pooled_dti"], ci95=v["ci95"], paired=v.get("paired_vs_champion_proxy")) for k, v in h.items()},
                 caveat="hold-out hides CATALOGUE segments; it is not the scored population of new faults; modulation is fitted on catalogue faults (partly circular)."),
    registry_audit=dict(n_registry_unique_dot_masks=u["n_registry_unique_dot_masks"], max_abs_spearman_smoothed=u["U2_max_abs_spearman"],
                        max_overlap_non_lattice=u["U3_max_overlap_nonlattice"], lattice_like_refs=u["U3_lattice_refs"], top10=u["top10_overlap"],
                        literal_rule_pass=bool(u.get("U3_literal_pass", False)),
                        literal_scope_complete=bool(u.get("U3_literal_scope_complete", False)),
                        literal_rule_note="No lattice/null exemption is permitted. Unclassified registry entries also fail closed."),
    raster_sha256={k: v["sha256"] for k, v in b["files"].items()}, dots_sha256=b["dots_sha256"],
    validator_output=val, legacy_diagnostics=legacy_diagnostics, gates=gates,
    gate_status=gate_status, submission_name=name, submission_note=NOTE, note_length=len(NOTE),
    label_of_numbers=dict(ORGANIZER_CONFIRMED="none for this file", LEADERBOARD_ESTIMATE="NOT_ESTIMABLE"),
    archived_diagnostics=dict(source="evidence/build_result.json", projection_status="QUARANTINED_NOT_A_SCORE",
                              used_for_current_approval=False),
    ledger_cv=dict(nested_leave_site_out_mae=fit["nested_family_cv"]["mae"], baseline_stratum_only_mae=fit["nested_family_cv"]["baseline_mae"],
                   fields_identified_by_ledger=fit["fields_identified_by_ledger"]),
    ready_to_submit=ready, file_integrity_and_uniqueness_pass=ready,
    legacy_holdout_promotion_rule_passed=bool(legacy_performance_win),
    current_evaluator_status="NOT_RUN: legacy HOLDOUT-DTI is not the current shared evaluator.",
    promotion_eligible=bool(promote),
    selector_approval=selector_approval,
    current_protocol_status="DO NOT SUBMIT: literal registry overlap is not cleared; registry scope is incomplete; current shared evaluation and file validation were not run; selector approval is false.",
    verdict=verdict,
    budget=dict(experiments_run="1 hypothesis; 5 hold-out variants + 2 diagnostics on the final construction; 2 builds (uniqueness repair). The pre-repair first run is kept in evidence/holdout_results_preLCB_firstrun.json. EXCEEDS the protocol budget of 3 experiments / 2 h - disclosed.", slot_selected=False),
    uniqueness_price_note="same hold-out, no avoid-zone (diagnostic only, violates the overlap cap): LCB -0.0155, median -0.0070 vs champion proxy; with avoid-zone: LCB -0.0325, median -0.0215",
)
json.dump(card, open(ev / "lst1_run_card.json", "w"), indent=1, default=float)
print(json.dumps({k: card[k] for k in ("gates", "ready_to_submit", "verdict", "submission_name", "note_length")}, indent=1))
