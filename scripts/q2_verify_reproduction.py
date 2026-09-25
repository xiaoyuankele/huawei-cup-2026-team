"""Compare rerun CSVs with archived research tables, preserving row order."""
import argparse
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import scipy
import sklearn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    imported = json.loads((repo / 'data/manifests/q2_research_import.json').read_text(encoding='utf-8'))
    records = []
    for item in imported['files']:
        relative = Path(item['path'])
        if relative.suffix != '.csv':
            continue
        archived = repo / relative
        rerun = args.output_root / relative.relative_to('experiments/runs')
        if relative.name == 'quality-direction-audit.csv':
            records.append(dict(path=relative.as_posix(), status='historical_manual_audit_not_regenerated'))
            continue
        if not rerun.exists():
            raise AssertionError(f'Missing rerun: {relative}')
        left, right = pd.read_csv(archived), pd.read_csv(rerun)
        pd.testing.assert_frame_equal(left, right, check_exact=False, rtol=1e-10, atol=1e-10)
        numeric = left.select_dtypes(include='number').columns
        delta = (left[numeric] - right[numeric]).abs().to_numpy()
        maximum = float(np.nanmax(delta)) if delta.size and np.isfinite(delta).any() else 0.
        records.append(dict(path=relative.as_posix(), status='PASS', rows=len(left), columns=len(left.columns),
                            max_absolute_numeric_difference=maximum,
                            archived_sha256=hashlib.sha256(archived.read_bytes()).hexdigest(),
                            rerun_sha256=hashlib.sha256(rerun.read_bytes()).hexdigest()))
    # Frozen model values must also survive path portability changes.
    model = Path('q2-model-finalization-20260925/model_parameters.json')
    assert json.loads((repo/'experiments/runs'/model).read_text(encoding='utf-8')) == json.loads((args.output_root/model).read_text(encoding='utf-8'))
    result = dict(status='PASS', tolerance=dict(rtol=1e-10, atol=1e-10),
                  compared_csvs=sum(r['status']=='PASS' for r in records), model_parameters_equal=True,
                  environment=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                                   scipy=scipy.__version__, scikit_learn=sklearn.__version__),
                  note='Numerical equivalence only; archived narrative and historical source/script hashes intentionally retained. No independent scientific review implied.',
                  files=records)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
