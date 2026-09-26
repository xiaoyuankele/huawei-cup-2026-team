"""Independent exported-certificate and repeat-run checks for E3."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from q2_e3_quality_substitution import ROOT, sha, dump


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rerun-dir', required=True, type=Path)
    args = ap.parse_args()
    cfg = json.loads((ROOT/'configs/q2-e3-quality-parameter-substitution.json').read_text())
    out = ROOT/'experiments/runs'/cfg['run_id']
    manifest = json.loads((out/'manifest.json').read_text())
    model = json.loads((ROOT/cfg['model']).read_text())
    mix = model['mixture']
    f = pd.read_csv(ROOT/cfg['bridge'],usecols=['dataset']+mix['columns'])
    P = f[f.dataset=='A4_A5_train_1m'][mix['columns']].to_numpy()
    p0 = np.asarray(mix['p_reference'])
    support = pd.read_csv(out/'quality_path_support.csv')
    weights = pd.read_csv(out/'support_weights.csv')
    duals = pd.read_csv(out/'support_duals.csv')
    for row in support.itertuples():
        ax = mix['axes'][row.axis]; v = np.asarray(ax['p_on_Q_loading'])
        w = np.zeros(len(P)); sub = weights[weights.axis==row.axis]
        w[sub.train_position.to_numpy(int)] = sub.weight
        assert w.min() >= -cfg['lp_tolerance']
        assert abs(w.sum()-1) < cfg['witness_atol']
        assert np.max(np.abs(w@P-p0-row.t_hull_max*v)) < cfg['witness_atol']
        y = duals[duals.axis==row.axis].iloc[0][[f'y_{j}' for j in range(18)]].to_numpy(float)
        upper = ax['Q_A_train_max']-ax['Q_A_reference']
        dual = np.r_[p0,1.]@y+upper*row.t_upper_price
        assert abs(dual+row.t_hull_max)<cfg['witness_atol']
        assert (np.vstack([P.T,np.ones(len(P))]).T@y).max()<cfg['witness_atol']
        assert -1+v@y[:17]-row.t_upper_price>=-cfg['witness_atol']
    A = model['scale']['parameters']['A']; alpha = model['scale']['parameters']['alpha']
    for name,gain in [('recipe_substitution.csv','gain_total'),('quality_path_curves.csv','gain')]:
        df = pd.read_csv(out/name, float_precision='round_trip')
        assert not df.observed_joint_row.any()
        S = A*df.N0_B**(-alpha)
        for col,status,term in [('N_required_B','required_status',S+df[gain]),
                                ('N_scale_equivalent_B','scale_status',S-df[gain])]:
            finite = df[status]=='FINITE'
            assert (term[finite]>0).all() and (term[~finite]<=0).all()
            assert df.loc[~finite,col].isna().all()
            assert np.max(np.abs(A*df.loc[finite,col]**(-alpha)-term[finite]))<cfg['equality_atol']
        expect = cfg['compute_coefficient_kappa']*cfg['D_reference_B']*(df.N0_B-df.N_required_B)*1e18
        assert np.allclose(expect,df.quality_cost_ceiling_FLOPs,equal_nan=True)
    comparisons = {}
    for name, digest in manifest['outputs'].items():
        assert sha(out/name)==digest
        assert sha(args.rerun_dir/name)==digest, name
        comparisons[name] = digest
    assert sha(out/'metrics.json')==sha(args.rerun_dir/'metrics.json')==manifest['metrics_sha256']
    assert all(sha(ROOT/p)==h for p,h in manifest['inputs'].items())
    checks = pd.read_csv(out/'verification_checks.csv')
    assert checks.passed.all()
    result = dict(status='PASS',certificate_axes=2,csv_files_byte_identical=len(comparisons),
                  metrics_byte_identical=True,inputs_unchanged=True,
                  exported_inverse_and_cost_checks=True,files=comparisons)
    dump(out/'reproduction_verification.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
