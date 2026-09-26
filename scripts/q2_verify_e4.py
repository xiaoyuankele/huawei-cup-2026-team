import argparse, json, hashlib
from pathlib import Path
import numpy as np, pandas as pd
from q2_e4_b9_b10_extrapolation import ROOT,sha
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--rerun-dir',type=Path,required=True);a=ap.parse_args()
    cfg=json.loads((ROOT/'configs/q2-e4-b9-b10-extrapolation.json').read_text());out=ROOT/'experiments/runs'/cfg['run_id'];m=json.loads((out/'manifest.json').read_text())
    for name,d in m['outputs'].items():
        assert sha(out/name)==d and sha(a.rerun_dir/name)==d,name
    assert sha(out/'metrics.json')==sha(a.rerun_dir/'metrics.json')==m['metrics_sha256']
    g=pd.read_csv(out/'scale_extrapolation_grid.csv');q=pd.read_csv(out/'quality_extrapolation_grid.csv');s=pd.read_csv(out/'exponent_sensitivity.csv')
    assert not g.observed_joint_row.any() and not q.observed_joint_row.any() and not s.observed_joint_row.any()
    model=json.loads((ROOT/cfg['model']).read_text()); p=model['scale']['parameters'];E,A,b,alpha,beta=[p[x] for x in ['E','A','B','alpha','beta']]
    assert np.allclose(g.dL_dlogN,-alpha*A*g.N_params_B**(-alpha));assert np.allclose(g.dL_dlogD,-beta*b*g.D_tokens_B**(-beta))
    assert q[q.quality_case=='reference'].quality_increment_loss.abs().max()<1e-12
    assert json.loads((out/'metrics.json').read_text())['row_level_loss_loaded'] is False
    print(json.dumps({'status':'PASS','csv_files_byte_identical':len(m['outputs']),'metrics_byte_identical':True,'inputs_unchanged':True,'row_level_loss_loaded':False},indent=2))
if __name__=='__main__': main()
