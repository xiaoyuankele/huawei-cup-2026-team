import argparse, json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from q2_e4_b9_b10_extrapolation import ROOT,sha
W=180/25.4
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['DejaVu Sans'],'font.size':8,'axes.labelsize':8,'axes.titlesize':9,
                     'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'pdf.fonttype':42,'svg.fonttype':'none',
                     'axes.spines.top':False,'axes.spines.right':False})
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run-dir',type=Path,default=ROOT/'experiments/runs/q2-e4-b9-b10-extrapolation-20260926-r01');a=ap.parse_args();r=a.run_dir;out=r/'figures';out.mkdir(exist_ok=True)
 g=pd.read_csv(r/'scale_extrapolation_grid.csv');q=pd.read_csv(r/'quality_extrapolation_grid.csv');ex=[]
 def save(fig,name):
  for suffix in ['.svg','.pdf','.png']:
   p=out/(name+suffix);fig.savefig(p,dpi=300)
   if suffix=='.svg':p.write_text('\n'.join(x.rstrip() for x in p.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n')
   ex.append(p)
  plt.close(fig)
 fig,ax=plt.subplots(1,2,figsize=(W,85/25.4),layout='constrained')
 for j,(D,label) in enumerate([(1,'D = 1B'),(100,'D = 100B')]):
  s=g[g.D_tokens_B==D].sort_values('N_params_B');ax[j].plot(s.N_params_B,s.scale_loss,'o-',color='#0072B2',label='frozen scale term')
  ax[j].axvspan(.070542,11.965825,color='#999999',alpha=.16,label='B1 N support')
  ax[j].set_xscale('log');ax[j].set(xlabel='N parameters (B)',ylabel='Predicted Loss',title=label);ax[j].legend(frameon=False)
 fig.suptitle('B9/B10 range-conditioned model extrapolation | B1 support shaded',fontsize=9);save(fig,'E4_scale_extrapolation')
 fig,axs=plt.subplots(1,2,figsize=(W,85/25.4),layout='constrained')
 for ax,(axis,label) in zip(axs,[('Q_A_topsis_0_1','TOPSIS'),('quality_score_soft_proxy_0_1','Soft proxy')]):
  s=q[(q.axis==axis)&(q.N_params_B==10000)&(q.lambda_Q==1)&(q.quality_case!='reference')].sort_values('D_tokens_B')
  for case,color in [('feasible_99pct','#0072B2'),('formal_coordinate','#D55E00')]:
   x=s[s.quality_case==case];ax.plot(x.D_tokens_B,x.quality_gain,'o-',color=color,label=case.replace('_',' '))
  ax.set_xscale('log');ax.set(xlabel='D tokens (B)',ylabel='Conditional quality Loss reduction',title=f'{label} at N = 10000B');ax.legend(frameon=False)
 fig.suptitle('Quality scenarios remain conditional beyond B1 support',fontsize=9);save(fig,'E4_quality_high_scale')
 (out/'export_manifest.json').write_text(json.dumps({'source_script_sha256':sha(Path(__file__)),'source_csvs':{x:sha(r/x) for x in ['scale_extrapolation_grid.csv','quality_extrapolation_grid.csv','exponent_sensitivity.csv']},'exports':{p.name:sha(p) for p in ex},'status':'SELF_CHECK_NOT_PEER_REVIEW'},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
