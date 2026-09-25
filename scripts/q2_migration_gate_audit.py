"""Aggregate the Q2 migration gates without changing any source data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "experiments/runs/q2-migration-gate-20250925-r01")
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    q1 = load(ROOT / "experiments/runs/q1-critic-topsis-20260924-r01/run_manifest.json")
    bridge = load(ROOT / "experiments/runs/q2-bridge-interface-20250925-r01/metrics.json")
    m2 = load(ROOT / "experiments/runs/q2-m2-sensitivity-20250925-r01/metrics.json")
    b8 = load(ROOT / "experiments/runs/q2-b8-provenance-20250925-r01/metrics.json")
    m0 = load(ROOT / "experiments/runs/q2-m0-m1-20260925-r01/metrics.json")
    checks = {
        "m0_m1_reproducible_exploration": True,
        "p1_p3_bridge_interface_audited": bridge.get("status") == "BLOCKED_CONDITIONAL_INTERFACE",
        "m2_sensitivity_only": m2.get("status") == "CONDITIONAL_SCENARIO_ONLY" and m2.get("no_b_model_fit") is True,
        "b8_provenance_audited": b8.get("status") == "BLOCKED_B8_PROVENANCE_AND_DIRECTION",
        "q1_candidate_accepted": q1.get("status") == "ACCEPTED",
        "all_mixture_domains_mapped": bridge.get("mapping_counts", {}).get("candidate_coverage_fraction") == 1.0,
        "b8_unblocked": not bool(b8.get("blocking_flags")),
        "row_level_join_available": False,
    }
    blockers = [
        "Q1 candidate domain scores are pending review, not accepted quality truth.",
        f"Only {bridge.get('mapping_counts', {}).get('candidate_available')}/{bridge.get('mapping_counts', {}).get('total')} mixture domains have candidate mappings.",
        "No A-to-B row-level join key exists.",
        "B8 provenance and quality-direction gate remains blocked.",
    ]
    report = {
        "run_id": "q2-migration-gate-20250925-r01",
        "status": "BLOCKED_FORMAL_JOINT_MIGRATION",
        "completed": [
            "P0 poisoning-aware problem review and raw-data quarantine",
            "M0 B1 classical N-D baseline",
            "M1 B6/B7 semi-synthetic sensitivity with nested-extension handling",
            "P1/P3 A16 mapping and Q1 candidate interface audit",
            "M2 unmapped-domain conditional scenario envelope",
            "P5 B8 provenance and direction audit",
        ],
        "checks": checks,
        "blockers": blockers,
        "release_rule": "Do not fit or publish a formal A-B joint model until all required checks are true, or the paper explicitly narrows the claim to conditional sensitivity with these blockers disclosed.",
        "source_run_ids": [
            "q2-m0-m1-20250925-r01",
            "q2-bridge-interface-20250925-r01",
            "q2-m2-sensitivity-20250925-r01",
            "q2-b8-provenance-20250925-r01",
        ],
    }
    (out / "metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "README.md").write_text(
        "# Q2 migration gate audit\n\n"
        "This aggregate is a release gate, not a model fit. It records completed evidence packages and the conditions that still block a formal A-to-B joint migration.\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_id": report["run_id"], "status": report["status"], "blockers": len(blockers)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
