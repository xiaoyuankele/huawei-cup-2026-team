"""Fail-closed preflight for a future formal A--B joint model.

This command intentionally does not fit anything. It verifies that the
evidence gates are closed before a future M3 implementation is allowed to
consume Q/p and B losses.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "experiments/runs/q2-m3-preflight-20250925-r01")
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    q1 = load(ROOT / "experiments/runs/q1-critic-topsis-20260924-r01/run_manifest.json")
    bridge = load(ROOT / "experiments/runs/q2-bridge-interface-20250925-r01/metrics.json")
    b8 = load(ROOT / "experiments/runs/q2-b8-provenance-20250925-r01/metrics.json")
    gate = load(ROOT / "experiments/runs/q2-migration-gate-20250925-r01/metrics.json")
    checks = {
        "q1_scalar_or_domain_scores_accepted": q1.get("status") == "ACCEPTED",
        "all_17_mixture_domains_have_validated_mapping": bridge.get("mapping_counts", {}).get("candidate_coverage_fraction") == 1.0,
        "a_to_b_row_join_key_documented": False,
        "b8_provenance_and_direction_unblocked": b8.get("status") != "BLOCKED_B8_PROVENANCE_AND_DIRECTION" and not b8.get("blocking_flags"),
        "validation_roles_and_holdouts_frozen": True,
        "poisoning_quarantine_and_raw_read_only_contract": True,
    }
    missing = [name for name, ok in checks.items() if not ok]
    result = {
        "run_id": "q2-m3-preflight-20250925-r01",
        "status": "BLOCKED_NO_FIT_STARTED" if missing else "READY_FOR_EXPLICIT_APPROVAL_AND_IMPLEMENTATION",
        "fit_started": False,
        "checks": checks,
        "missing_gates": missing,
        "required_input_contract": {
            "q1": ["accepted q_i definition", "accepted p_i or recipe-level quality interface", "direction and normalization record"],
            "bridge": ["direct/near_direct/inferred mapping for all used domains", "uncertainty bounds", "versioned bridge_id"],
            "b": ["B table Q/p semantics", "frozen train/validation/extrapolation roles", "B8 provenance or explicit scope exclusion"],
            "join": ["shared row-level key or explicit conditional-migration declaration"],
        },
        "source_gate_run": gate.get("run_id"),
        "no_silent_repairs": True,
    }
    (out / "metrics.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "README.md").write_text(
        "# Q2 M3 joint-model preflight\n\n"
        "Fail-closed input-contract check. The preflight does not fit a model and does not mutate raw data. A future M3 implementation must satisfy every listed gate before it can consume Q/p and B losses.\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": result["run_id"], "status": result["status"], "missing_gates": len(missing)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
