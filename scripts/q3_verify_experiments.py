"""Independent full-variable checks for both quality-cost coordinates and bounds."""
import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import q3_run_experiments as x

checks=[]
for axis in x.M['mixture']['axes']:
    for kind in ['exponential','power','logarithmic']:
        for coord in ['Q_A','Q_B']:
            for C,ctx,scope in [(1e19,2048,'unrestricted'),(1e22,32768,'unrestricted'),
                                (1e24,131072,'unrestricted'),(1e24,2048,'B1_rectangle')]:
                r=x.process_opt(C,ctx,axis,kind,x.P0,scope,coord=coord)
                dense=x.process_opt(C,ctx,axis,kind,x.P0,scope,coord=coord,grid_size=1025)
                ax=x.M['mixture']['axes'][axis];q0=r['Q0']
                def obj(z):
                    n,d=np.exp(z[:2]); qb=float(x.transport(z[2],ax)) if coord=='Q_A' else z[2]
                    return x.E+x.A*n**(-x.AL)+x.B*d**(-x.BE)+x.COEF*(qb-ax['Q_B_reference'])
                def con(z):
                    n,d=np.exp(z[:2]); b=(x.cost(z[2],kind)-x.cost(q0,kind))/1e9
                    return 1-d*((6+x.ETA*ctx)*n+b)/(C/1e18)
                # Above the mapping ceiling, benefit is constant and cost rises.
                # Exclude this dominated segment to avoid finite differences across a kink.
                bounds=[(-20,20),(-20,20),(q0,r['Q_upper'])]
                if scope=='B1_rectangle':
                    bounds=[tuple(np.log(x.M['scale']['support'][v])) for v in ['N_params_B','D_tokens_B']]+[(q0,r['Q_upper'])]
                starts=[]
                for q in [q0,(q0+r['Q_upper'])/2,r['Q_upper']]:
                    b=(x.cost(q,kind)-x.cost(q0,kind))/1e9
                    n,d,_=x.nd_opt(C,ctx,b,scope)
                    starts.append([np.log(n),np.log(max(np.exp(bounds[1][0]),.75*d)),q])
                fits=[minimize(obj,z,method='SLSQP',bounds=bounds,constraints=[{'type':'ineq','fun':con}],
                    options={'maxiter':1000,'ftol':1e-11}) for z in starts]
                feasible=[s for s in fits if s.success and con(s.x)>-1e-7]
                assert feasible, (axis,kind,coord,C)
                best=min(feasible,key=lambda s:s.fun)
                assert abs(best.fun-r['predicted_loss'])<1e-7,(r,best.fun)
                assert abs(dense['predicted_loss']-r['predicted_loss'])<1e-7
                checks.append(dict(axis=axis,cost=kind,coordinate=coord,budget=C,context=ctx,scope=scope,
                    successful_starts=len(feasible),full_variable_loss=best.fun,reduced_loss=r['predicted_loss'],
                    difference=best.fun-r['predicted_loss'],dense_grid_difference=dense['predicted_loss']-r['predicted_loss'],
                    budget_slack=con(best.x)))
pd.DataFrame(checks).to_csv(x.OUT/'independent_multistart_checks.csv',index=False)
summary=dict(cases=len(checks),max_full_difference=max(abs(r['difference']) for r in checks),
             max_grid_difference=max(abs(r['dense_grid_difference']) for r in checks),
             successful_starts=sum(r['successful_starts'] for r in checks),attempted_starts=len(checks)*3)
(x.OUT/'independent_verification.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
