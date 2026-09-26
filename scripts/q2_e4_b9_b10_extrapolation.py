"""Range-conditioned B9/B10 extrapolation audit using frozen Q2 v1."""
import argparse, hashlib, itertools, json, subprocess, platform
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from q2_finalize_model import predict_scenario

ROOT=Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config',type=Path,default=ROOT/'configs/q2-e4-b9-b10-extrapolation.json'); ap.add_argument('--output-dir',type=Path)
    a=ap.parse_args(); cfg=json.loads(a.config.read_text(encoding='utf-8')); out=a.output_dir or ROOT/'experiments/runs'/cfg['run_id']; out.mkdir(parents=True,exist_ok=True)
    model_path=ROOT/cfg['model']; audit_path=ROOT/cfg['b9_b10_audit']; support_path=ROOT/cfg['e3_support']
    model=json.loads(model_path.read_text(encoding='utf-8')); audit=json.loads(audit_path.read_text(encoding='utf-8')); support=pd.read_csv(support_path)
    assert audit['status']=='B9_B10_EXTRAPOLATION_ONLY' and audit['checks']['fit_or_refit'] is False
    assert audit['checks']['used_as_true_validation'] is False
    par=model['scale']['parameters']; E,A,B,alpha,beta=[par[x] for x in ['E','A','B','alpha','beta']]
    nlo,nhi=model['scale']['support']['N_params_B']; dlo,dhi=model['scale']['support']['D_tokens_B']
    axes=list(model['mixture']['axes']); p0=np.asarray(model['mixture']['p_reference']); cols=model['mixture']['columns']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in [model_path,audit_path,support_path,a.config.resolve(),Path(__file__).resolve(),ROOT/'scripts/q2_finalize_model.py']}
    checks=[]; outputs=[]
    def check(name,actual,expected=0.,tol=1e-10):
        err=np.abs(np.asarray(actual)-np.asarray(expected)); m=float(np.max(err,initial=0)); ok=bool(np.isfinite(err).all() and m<=tol)
        checks.append(dict(check=name,comparisons=int(err.size),max_absolute_error=m,tolerance=tol,passed=ok)); assert ok,checks[-1]
    def save(name,df):
        df.to_csv(out/name,index=False,lineterminator='\n'); outputs.append(name); return df
    def scale_loss(N,D,aa=alpha,bb=beta): return E+A*np.asarray(N,dtype=float)**(-aa)+B*np.asarray(D,dtype=float)**(-bb)
    def predict(points,N,D,axis,lq):
        f=pd.DataFrame(np.atleast_2d(points),columns=cols); f['N_params_B']=N; f['D_tokens_B']=D
        return predict_scenario(f,model,axis,lambda_q=lq,lambda_p=0)
    ngrid=np.asarray(cfg['N_grid_B'],float); dgrid=np.asarray(cfg['D_grid_B'],float)
    # Reference scale grid: all points are scenarios, with explicit B1 support flags.
    rows=[]
    for N,D in itertools.product(ngrid,dgrid):
        L=float(scale_loss(N,D)); ln=-alpha*A*N**(-alpha); ld=-beta*B*D**(-beta)
        rows.append(dict(N_params_B=N,D_tokens_B=D,scale_loss=L,dL_dlogN=ln,dL_dlogD=ld,
            loss_elasticity_N=ln/L,loss_elasticity_D=ld/L,
            N_in_B1_range=bool(nlo<=N<=nhi),D_in_B1_range=bool(dlo<=D<=dhi),
            joint_B1_range=bool(nlo<=N<=nhi and dlo<=D<=dhi),N_extrapolation_factor=max(N/nhi,nlo/N),
            D_extrapolation_factor=max(D/dhi,dlo/D),observed_joint_row=False))
    grid=save('scale_extrapolation_grid.csv',pd.DataFrame(rows))
    # Quality path conditions imported from E3, while keeping formal coordinate clearly separate.
    curves=[]
    for axis in axes:
        s=support[support.axis==axis].iloc[0]; ax=model['mixture']['axes'][axis]; q=np.asarray(ax['domain_quality']); v=np.asarray(ax['p_on_Q_loading'])
        cases={'reference':p0,'feasible_99pct':p0+float(s.t_safe)*v,'formal_coordinate':p0+float(s.t_hull_max)*v}
        for case,p in cases.items():
            for lq,N,D in itertools.product(cfg['lambda_Q'],ngrid,dgrid):
                z=predict(p,N,D,axis,lq).iloc[0]; base=float(scale_loss(N,D))
                dq=float(z.delta_Q); total=float(z.predicted_loss_scenario)
                curves.append(dict(axis=axis,quality_case=case,lambda_Q=lq,N_params_B=N,D_tokens_B=D,
                    scale_loss=base,quality_increment_loss=dq,predicted_loss=total,
                    quality_gain=-dq,relative_to_scale=(total/base-1),N_in_B1_range=bool(nlo<=N<=nhi),
                    D_in_B1_range=bool(dlo<=D<=dhi),observed_joint_row=False))
    quality=save('quality_extrapolation_grid.csv',pd.DataFrame(curves))
    # Deterministic exponent stress, explicitly not an uncertainty interval.
    sens=[]
    for N,D in itertools.product(ngrid,dgrid):
        base=float(scale_loss(N,D))
        for param in ['alpha','beta']:
          for rel in cfg[param+'_relative_perturbations']:
            aa=alpha*(1+rel) if param=='alpha' else alpha; bb=beta*(1+rel) if param=='beta' else beta
            val=float(scale_loss(N,D,aa,bb))
            sens.append(dict(N_params_B=N,D_tokens_B=D,perturbed_parameter=param,relative_change=rel,
               baseline_loss=base,perturbed_loss=val,delta=val-base,observed_joint_row=False))
    sensitivity=save('exponent_sensitivity.csv',pd.DataFrame(sens))
    coverage_rows=[]
    for src,info in audit['files'].items():
        coverage_rows.append(dict(source=src,rows=info['rows'],N_min_B=info['n_min'],N_max_B=info['n_max'],D_min_B=info['d_min'],D_max_B=info['d_max'],
            max_N_over_B1=float(info['n_max']/nhi),max_D_over_B1=float(info['d_max']/dhi),
            row_level_loss_available=False,estimated_loss_allowed=(src=='B10'),source_metadata_complete=audit['checks']['source_metadata_complete'],
            interpretation='range and provenance audit only'))
    coverage=save('b9_b10_coverage.csv',pd.DataFrame(coverage_rows))
    # Analytical monotonicity and asymptotic checks.
    check('N_monotonic_scale',np.diff(scale_loss(ngrid,1)),np.minimum(np.diff(scale_loss(ngrid,1)),0),tol=1e-12)
    check('D_monotonic_scale',np.diff(scale_loss(1,dgrid)),np.minimum(np.diff(scale_loss(1,dgrid)),0),tol=1e-12)
    check('N_gradient',grid.dL_dlogN,-alpha*A*grid.N_params_B**(-alpha),tol=1e-12)
    check('D_gradient',grid.dL_dlogD,-beta*B*grid.D_tokens_B**(-beta),tol=1e-12)
    check('asymptotic_floor',scale_loss(1e100,1e100),E,tol=1e-10)
    check('reference_quality_zero',quality[quality.quality_case=='reference'].quality_increment_loss,0.,tol=1e-12)
    save('verification_checks.csv',pd.DataFrame(checks))
    metrics=dict(status='RUN_COMPLETE_RANGE_CONDITIONED',grid_rows=len(grid),quality_rows=len(quality),sensitivity_rows=len(sensitivity),coverage_rows=len(coverage),
        checks=len(checks),numerical_comparisons=sum(x['comparisons'] for x in checks),B9_B10_rows={'B9':audit['files']['B9']['rows'],'B10':audit['files']['B10']['rows']},
        max_N_extrapolation_factor=float(max(x['max_N_over_B1'] for x in coverage_rows)),max_D_extrapolation_factor=float(max(x['max_D_over_B1'] for x in coverage_rows)),
        row_level_loss_loaded=False,fit_new_parameters=False,used_as_true_validation=False,inputs_unchanged=True,interpretation='Conditional trend and range audit; no B10 outcome comparison')
    dump(out/'metrics.json',metrics)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    dump(out/'manifest.json',dict(task_id='T-Q2-E4',run_id=cfg['run_id'],git_commit=commit,created_at=datetime.now(timezone.utc).isoformat(),
        inputs=hashes,outputs={f:sha(out/f) for f in outputs},metrics_sha256=sha(out/'metrics.json'),inference_status='RANGE_CONDITIONED_NOT_VALIDATION',
        source_data_roles={'B9':'metadata/range only','B10':'estimated baseline/range only'}))
    print(json.dumps(metrics,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
