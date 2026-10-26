"""Fail-closed entry point for the retired H_STEP-OVER raster generator.

The earlier implementation placed 35,000 binary dots by distance from one
historical catalogue raster. It did not use the authenticated competition
feature stack, run the required holdout, or establish complete-registry
uniqueness; the registered-lattice lower bound is 81%. This file intentionally
writes nothing. A future lane-specific model must be preregistered and evaluated
with the shared tools before any export is enabled.
"""
import json


def main() -> int:
    report = {
        "status": "BLOCKED_RETIRED_GENERATOR",
        "candidate_generation_performed": False,
        "reason": "The legacy geometry-only candidate fails the literal registered-lattice overlap bound and has no assigned lane or compliant holdout.",
        "current_artifact": "docs/downloads/wb-gems-doe-3-stepover-damagezone-35000d-20261026T215413Z-zeros.tif",
        "current_decision": "AUDIT ONLY / DO NOT SUBMIT",
        "next_action": "Assign a method lane and restore authenticated inputs/folds/registry; implement a fold-safe method using the pinned shared evaluator and writer.",
    }
    print(json.dumps(report, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
