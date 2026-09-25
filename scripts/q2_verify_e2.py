"""Independently inspect exported E2 certificates and optionally a full rerun."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from q2_finalize_model import predict_scenario

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'experiments/runs/q2-e2-domain-substitution-20260925-r01'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,default=DEFAULT)
    parser.add_argument('--rerun-dir',type=Path)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args();r=args.run_dir
    m=json.loads((r/'manifest.json').read_text(encoding='utf-8'));cfg=m['config']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for name,expected in m['input_sha256'].items():assert sha(ROOT/name)==expected,name
    for name,expected in m['output_csv_sha256'].items():
        assert sha(r/name)==expected,name
        if args.rerun_dir:assert sha(args.rerun_dir/name)==expected,('rerun',name)
    assert sha(r/'metrics.json')==m['metrics_sha256']
    if args.rerun_dir:assert json.loads((r/'metrics.json').read_text())==json.loads((args.rerun_dir/'metrics.json').read_text())
    model=json.loads((ROOT/cfg['model']).read_text());mix=model['mixture'];cols=mix['columns'];k=len(cols)
    train=pd.read_csv(ROOT/cfg['bridge'],usecols=['dataset','index']+cols).query("dataset == 'A4_A5_train_1m'")
    p=train[cols].to_numpy();p0=np.array(mix['p_reference']);n=len(p);eye=np.eye(k)
    rays=pd.read_csv(r/'substitution_support.csv');weights=pd.read_csv(r/'support_weights.csv');duals=pd.read_csv(r/'support_duals.csv').set_index('direction_id')
    assert len(rays)==272 and not rays.duplicated(['to_index','from_index']).any()
    assert (rays.lp_status==0).all()
    tol=cfg['witness_atol']
    for ray in rays.itertuples():
        w=np.zeros(n);group=weights[weights.direction_id==ray.direction_id]
        positions=group.train_position.to_numpy(int);w[positions]=group.weight
        assert np.array_equal(group.source_recipe_id.to_numpy(),train['index'].to_numpy()[positions])
        direction=eye[ray.to_index]-eye[ray.from_index]
        assert w.min()>=-tol and abs(w.sum()-1)<tol
        assert np.max(abs(w@p-p0-ray.hull_limit*direction))<tol
        y=duals.loc[ray.direction_id].to_numpy(float)
        assert np.max(p@y[:k]+y[k])<tol
        assert -1+direction@y[:k]-ray.delta_upper_price>=-tol and ray.delta_upper_price<=tol
        bound=np.r_[p0,1.]@y+p0[ray.from_index]*ray.delta_upper_price
        assert abs(-ray.hull_limit-bound)<tol
        assert np.isclose(ray.safe_hull_limit,cfg['hull_safety_fraction']*ray.hull_limit)
    finite=pd.read_csv(r/'finite_substitution.csv')
    assert len(finite)==272*2*(len(cfg['absolute_swap_fractions'])+len(cfg['supported_limit_fractions']))
    unsupported=finite[~finite.training_hull_supported]
    assert unsupported[['delta_loss','delta_quality','delta_residual']].isna().all().all()
    supported=finite[finite.training_hull_supported]
    for axis,g in supported.groupby('axis'):
        pts=np.tile(p0,(len(g),1));steps=g.swap_fraction.to_numpy();idx=np.arange(len(g))
        pts[idx,g.to_index.to_numpy(int)]+=steps;pts[idx,g.from_index.to_numpy(int)]-=steps
        f=pd.DataFrame(pts,columns=cols);f['N_params_B']=cfg['reference_N_B'];f['D_tokens_B']=cfg['reference_D_B']
        pred=predict_scenario(f,model,axis)
        base=pd.DataFrame([p0],columns=cols);base['N_params_B']=cfg['reference_N_B'];base['D_tokens_B']=cfg['reference_D_B']
        l0=predict_scenario(base,model,axis).predicted_loss_scenario.iloc[0]
        assert np.max(abs(pred.predicted_loss_scenario.to_numpy()-l0-g.delta_loss.to_numpy()))<cfg['prediction_atol']
        assert np.max(abs(g.delta_loss-g.delta_quality-g.delta_residual))<cfg['prediction_atol']
    # Previously archived E1 derivative is an independent exported cross-check.
    e1=pd.read_csv(ROOT/'experiments/runs/q2-e1-marginal-elasticity-20260925-r01/simplex_directional_derivatives.csv')
    sens=pd.read_csv(r/'assumption_sensitivity.csv');nominal=sens.query('lambda_Q == 1 and lambda_p == 1')
    matched=nominal.merge(e1,on=['axis','to_index','from_index'],validate='one_to_one')
    assert len(matched)==544 and np.max(abs(matched.slope_per_fraction-matched.derivative_per_fraction))<1e-10
    reverse=sens.merge(sens,left_on=['axis','lambda_Q','lambda_p','to_index','from_index'],right_on=['axis','lambda_Q','lambda_p','from_index','to_index'])
    assert np.max(abs(reverse.slope_per_fraction_x+reverse.slope_per_fraction_y))<1e-12
    inter=pd.read_csv(r/'interior_interactions.csv');basis=pd.read_csv(r/'interaction_witness_basis.csv')
    assert len(inter)==4080 and inter.all_corners_training_hull_supported.all()
    b=basis[[f'coef_{i}' for i in range(k)]].to_numpy();uniform=np.full(n,1/n)
    for row in inter.drop_duplicates(['donor_index','to1_index','to2_index']).itertuples():
        b1=b[:,row.to1_index]-b[:,row.donor_index];b2=b[:,row.to2_index]-b[:,row.donor_index]
        for u,v in [(0,0),(1,0),(0,1),(1,1)]:
            w=uniform+row.step*(u*b1+v*b2)
            pp=p0+row.step*(u*(eye[row.to1_index]-eye[row.donor_index])+v*(eye[row.to2_index]-eye[row.donor_index]))
            assert w.min()>=0 and np.max(abs(w@p-pp))<tol
    assert np.max(abs(inter.loss11-inter.loss10-inter.loss01+inter.loss00))<cfg['interaction_zero_atol']
    stress=pd.read_csv(r/'clipping_stress_interactions.csv')
    assert len(stress)==12240 and stress.pure_baseline_outside_training_hull.all()
    assert np.max(abs(stress.interaction_loss-stress.clip_only_interaction))<cfg['prediction_atol']
    assert (stress.loc[stress.nonzero_interaction,'any_corner_clipped']).all()
    assert pd.read_csv(r/'verification_checks.csv').passed.all()
    positive=sens.query('lambda_Q > 0 and lambda_p > 0 and to_index < from_index')
    positive_flips=int((positive.groupby(['to_index','from_index']).sign.nunique()>1).sum())
    stability=pd.read_csv(r/'direction_stability.csv')
    result=dict(status='PASS',input_hashes_unchanged=True,lp_primal_and_dual_certificates=272,
                independently_reconstructed_corner_designs=2040,e1_derivative_matches=544,csv_files=len(m['output_csv_sha256']),
                positive_strength_subset_flipped_pairs=positive_flips,
                wide_assumption_flipped_pairs=int(stability.sign_flips.sum()),
                rerun_byte_identical=bool(args.rerun_dir),package_status='REVIEW_BLOCKED',empirical_validation=False)
    if args.report:args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
