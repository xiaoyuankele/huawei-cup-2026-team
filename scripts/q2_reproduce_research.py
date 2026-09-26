"""Recompute numerical outputs into a separate directory; raw data is read-only."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-root', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output = args.output_root.resolve()
    raw_root = args.raw_root.resolve()
    if output == raw_root or raw_root in output.parents:
        parser.error('Output must be outside the read-only raw attachment directory.')
    if output == (repo / 'experiments/runs').resolve():
        parser.error('Choose a separate output directory to preserve the research archive.')
    if not args.raw_root.is_dir():
        parser.error('The controlled raw attachment directory does not exist.')
    env = dict(os.environ, Q2_RAW_ROOT=str(args.raw_root.resolve()), Q2_RUNS_ROOT=str(output), PYTHONIOENCODING='utf-8')
    scripts = ['q2_quality_scaling_link.py', 'q2_local_model_validation.py',
               'q2_combined_scenario_prototype.py', 'q2_calibration_sensitivity.py',
               'q2_finalize_model.py', 'q2_transfer_improvement.py']
    for script in scripts:
        print('RUN ' + script, flush=True)
        subprocess.run([sys.executable, str(repo / 'scripts' / script)], cwd=repo, env=env, check=True)
    print('Numerical rerun complete. Historical narrative reports are retained separately.')


if __name__ == '__main__':
    main()
