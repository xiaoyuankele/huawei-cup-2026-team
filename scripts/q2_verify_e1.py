"""Audit E1 exported tables and optionally compare an independent rerun."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'experiments/runs/q2-e1-marginal-elasticity-20260925-r01'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,default=DEFAULT)
    parser.add_argument('--rerun-dir',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args();run=args.run_dir
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    metrics=json.loads((run/'metrics.json').read_text(encoding='utf-8'))
    for path,expected in manifest['input_sha256'].items():
        assert sha(ROOT/path)==expected,('changed input',path)
    comparisons=[]
    for name,expected in manifest['output_csv_sha256'].items():
        assert sha(run/name)==expected,('changed output',name)
        frame=pd.read_csv(run/name)
        row=dict(file=name,rows=len(frame),columns=len(frame.columns),sha256=expected)
        if args.rerun_dir:
            rerun=args.rerun_dir/name
            pd.testing.assert_frame_equal(frame,pd.read_csv(rerun),check_exact=True)
            assert sha(rerun)==expected,('different CSV bytes',name)
            row['rerun_identical']=True
        comparisons.append(row)
    if args.rerun_dir:
        assert metrics==json.loads((args.rerun_dir/'metrics.json').read_text(encoding='utf-8'))
    grid=pd.read_csv(run/'scale_grid.csv')
    assert len(grid)==1681 and not grid.duplicated(['N_params_B','D_tokens_B']).any()
    assert (grid[['N_params_B','D_tokens_B','predicted_loss','N_marginal_benefit','D_marginal_benefit']]>0).all().all()
    assert np.allclose(grid.elasticity_N,grid.N_params_B*grid.dL_dN_B/grid.predicted_loss)
    assert np.allclose(grid.elasticity_D,grid.D_tokens_B*grid.dL_dD_B/grid.predicted_loss)
    quality=pd.read_csv(run/'quality_piecewise.csv')
    nondifferentiable=quality.mapping_region.isin(['lower_kink','upper_kink']) & (quality.lambda_Q!=0)
    assert quality.dL_dQA.isna().equals(nondifferentiable)
    assert quality.elasticity_QA.notna().equals(quality.elasticity_QA_defined)
    assert quality.loc[quality.Q_A<=0,'elasticity_QA'].isna().all()
    assert quality.loc[quality.mapping_region=='clipped','dL_dQA'].eq(0).all()
    assert not quality.independent_Q_intervention_observed.any()
    directions=pd.read_csv(run/'simplex_directional_derivatives.csv')
    assert len(directions)==544 and not directions.duplicated(['axis','from_domain','to_domain']).any()
    assert directions.finite_endpoints_in_training_convex_hull.all()
    assert not directions.one_percentage_point_support_verified.any()
    assert directions.min_convex_weight.ge(0).all()
    reverse=directions.rename(columns={'to_domain':'from_domain','from_domain':'to_domain'})
    pair=directions.merge(reverse,on=['axis','to_domain','from_domain'],validate='one_to_one')
    assert np.allclose(pair.derivative_per_fraction_x,-pair.derivative_per_fraction_y)
    scenarios=pd.read_csv(run/'assumption_sensitivity.csv')
    assert len(scenarios)==9216 and not scenarios.observed_joint_row.any()
    assert scenarios.N_marginal_benefit.nunique()==1 and scenarios.D_marginal_benefit.nunique()==1
    checks=pd.read_csv(run/'verification_checks.csv')
    assert checks.passed.all() and checks.max_tolerance_fraction.le(1).all()
    assert int(checks.comparisons.sum())==metrics['scalar_comparisons']
    assert len(checks)==metrics['derivative_check_groups']
    summary=dict(status='PASS',frozen_input_hashes_unchanged=True,exported_csv_checks_pass=True,
        rerun_compared=args.rerun_dir is not None,compared_csvs=len(comparisons),
        derivative_check_groups=len(checks),scalar_comparisons=int(checks.comparisons.sum()),
        note='Calculation checks and repeat execution are not independent empirical experiments.',tables=comparisons)
    if args.report:
        args.report.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='tables'},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
