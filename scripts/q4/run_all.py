"""Reproduce the exploratory Q4 run from the repository root.

Example: python scripts/q4/run_all.py --data-dir data/origin/C_efficiency_evolution
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


ORDER = [
    "q4_baseline_experiment.py",
    "q4_robustness_experiment.py",
    "q4_family_quantile_experiment.py",
    "q4_nested_quantile_experiment.py",
    "q4_c8_panel_quantile_experiment.py",
    "q4_compute_constrained_scenarios.py",
    "q4_c8_compute_scenarios.py",
    "q4_loss_bridge_audit.py",
    "q4_task_frontier_audit.py",
    "q4_time_placebo_test.py",
    "q4_error_evaluation.py",
    "q4_r2_evaluation.py",
    "q4_c8_cluster_bootstrap.py",
    "q4_protocol_experiment.py",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, default=Path("experiments/runs/q4-frontier-20260926-r01"))
    args = parser.parse_args()
    if not (args.data_dir / "leaderboard_cleaned.csv").is_file():
        raise SystemExit(f"missing Attachment C input: {args.data_dir / 'leaderboard_cleaned.csv'}")
    if not (args.run_dir / "q3_baseline_ND_optima.csv").is_file():
        raise SystemExit(f"missing exploratory Q3 scenario input: {args.run_dir / 'q3_baseline_ND_optima.csv'}")
    env = os.environ.copy()
    env["Q4_DATA_DIR"] = str(args.data_dir.resolve())
    env["Q4_RUN_DIR"] = str(args.run_dir.resolve())
    scripts = Path(__file__).resolve().parent
    log = args.run_dir / "run.log"
    with log.open("w", encoding="utf-8") as sink:
        for name in ORDER:
            command = [sys.executable, str(scripts / name)]
            print(f"Running {name}", flush=True)
            completed = subprocess.run(command, env=env, text=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
            output = completed.stdout
            for private, label in ((str(Path.cwd()), "<repo>"),
                                   (str(args.data_dir.resolve()), "<attachment-c>"),
                                   (sys.prefix, "<python-env>")):
                output = output.replace(private, label)
            sink.write(f"\n=== {name} (exit {completed.returncode}) ===\n{output}\n")
            sink.flush()
            if completed.returncode:
                raise SystemExit(f"{name} failed; see {log}")
    summary = subprocess.run([sys.executable, str(scripts / "summarize_run.py")], env=env, check=False)
    if summary.returncode:
        raise SystemExit("summary publication failed")
    print(f"Completed {len(ORDER)} scripts; log: {log}")


if __name__ == "__main__":
    main()
