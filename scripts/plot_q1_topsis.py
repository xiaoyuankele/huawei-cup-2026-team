"""Plot full-record descriptive domain means and matched domain changes."""
from pathlib import Path
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=ap.parse_args();root=args.root.resolve()
    rd=root/'experiments/runs/q1-critic-topsis-20260924-r01'
    d=pd.read_csv(rd/'tables/full_vs_A1.csv').sort_values('full_mean',ascending=False)
    assert len(d)==7 and d.n_full_unique.sum()==261086 and d.n_A1.sum()==51230
    out=rd/'figures';out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':7,'axes.titlesize':8,'axes.labelsize':7,'xtick.labelsize':6.5,'ytick.labelsize':6.5,'axes.spines.right':False,'axes.spines.top':False,'axes.linewidth':.6,'legend.frameon':False,'svg.fonttype':'none','pdf.fonttype':42,'savefig.facecolor':'white'})
    fig,axes=plt.subplots(1,2,figsize=(7.2047,4.3307),gridspec_kw={'width_ratios':[1.8,1]})
    fig.subplots_adjust(left=.30,right=.96,bottom=.21,top=.82,wspace=.35)
    y=np.arange(len(d));a,b=axes
    a.scatter(d.A1_mean,y-.10,s=16,marker='s',color='#777777',label='A1',zorder=3)
    a.scatter(d.full_mean,y+.10,s=21,marker='o',color='#286A91',label='Full unique union',zorder=4)
    a.set_yticks(y,[f'{r.domain}\n{int(r.n_A1):,} → {int(r.n_full_unique):,}' for r in d.itertuples()]);a.invert_yaxis()
    a.set_xlim(45,70);a.set_xticks([45,50,55,60,65,70]);a.set_xlabel('Mean quality score (0–100)');a.grid(axis='x',color='#E6E6E6',lw=.5)
    a.set_title('a  Domain quality',loc='left',fontweight='bold',pad=15)
    a.legend(loc='lower left',bbox_to_anchor=(-.02,1.10),ncol=2,fontsize=6.5,handletextpad=.4,columnspacing=.9)
    b.axvline(0,color='#BBBBBB',lw=.8)
    b.hlines(y,0,d.difference_points,color='#286A91',lw=1.3)
    b.scatter(d.difference_points,y,s=18,color='#286A91',zorder=3)
    b.set_yticks(y,[]);b.invert_yaxis();b.set_xlim(-.45,.18);b.set_xticks([-.4,-.2,0]);b.set_xlabel('Full − A1 (points)')
    b.set_title('b  Within-domain change',loc='left',fontweight='bold',pad=15)
    for yy,value in zip(y,d.difference_points):b.text(.17,yy,f'{value:+.3f}',ha='right',va='center',fontsize=6.5)
    fig.suptitle('CRITIC-weighted TOPSIS: A1 versus all available records',fontsize=9,y=.97)
    fig.text(.04,.095,'Counts: A1 → full unique union. Only arxiv and github have additional records.',fontsize=6.5)
    fig.text(.04,.055,'Descriptive sample means; shared A1-fit scale and weights. No inferential error bars.',fontsize=6.5)
    fig.savefig(out/'domain_quality_comparison.pdf')
    fig.savefig(out/'domain_quality_comparison.svg')
    fig.savefig(out/'domain_quality_comparison.png',dpi=300)
    plt.close(fig)


if __name__=='__main__':main()
