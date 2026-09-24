"""Vector figures from saved exploratory tables. ReportLab; no sampled data omitted."""
from pathlib import Path
import argparse,json
import pandas as pd
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing,String,Line,Rect,Circle
from reportlab.graphics import renderSVG,renderPDF
from reportlab.lib.colors import HexColor,Color

BLUE='#2E5A88';ORANGE='#E8842B';GREEN='#36856D';GRAY='#777777'
FONT='WPCChinese'
def text(d,x,y,s,size=10,anchor='start',color='#222222'):
    d.add(String(x,y,str(s),fontName=FONT,fontSize=size,textAnchor=anchor,fillColor=HexColor(color)))
def save(d,path):renderSVG.drawToFile(d,str(path.with_suffix('.svg')));renderPDF.drawToFile(d,str(path.with_suffix('.pdf')))
def lines(path,series,xlim,ylim,xlabel,ylabel,xticks,yticks):
    d=Drawing(650,380);left,right,bottom,top=66,625,60,325
    sx=lambda x:left+(x-xlim[0])/(xlim[1]-xlim[0])*(right-left)
    sy=lambda y:bottom+(y-ylim[0])/(ylim[1]-ylim[0])*(top-bottom)
    for y in yticks:
        d.add(Line(left,sy(y),right,sy(y),strokeColor=HexColor('#dddddd'),strokeWidth=.5));text(d,left-9,sy(y)-3,f'{y:g}',9,'end')
    for x in xticks:text(d,sx(x),bottom-17,f'{x:g}',9,'middle')
    d.add(Line(left,bottom,left,top,strokeColor=HexColor('#444444')));d.add(Line(left,bottom,right,bottom,strokeColor=HexColor('#444444')))
    text(d,(left+right)/2,20,xlabel,11,'middle');text(d,left,top+12,ylabel,10)
    for k,(name,x,y,color) in enumerate(series):
        for i in range(len(x)-1):d.add(Line(sx(x[i]),sy(y[i]),sx(x[i+1]),sy(y[i+1]),strokeColor=HexColor(color),strokeWidth=1.7,strokeDashArray=None if k==0 else [5,2] if k==1 else [2,2]))
        for xx,yy in zip(x,y):d.add(Circle(sx(xx),sy(yy),3,fillColor=HexColor(color),strokeColor=HexColor(color)))
        xx=left+k*180;d.add(Line(xx,362,xx+20,362,strokeColor=HexColor(color),strokeWidth=2));text(d,xx+25,359,name,9)
    save(d,path)
def main(root,font=None):
    candidates=[Path(font)] if font else [Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf'),Path('/Library/Fonts/Arial Unicode.ttf'),Path('C:/Windows/Fonts/msyh.ttf')]
    found=next((p for p in candidates if p.exists()),None)
    if found is None:raise SystemExit('请通过 --font 指定支持中文的 TrueType 字体文件；字体不随交付包分发。')
    pdfmetrics.registerFont(TTFont(FONT,str(found)))
    out=root/'figures';out.mkdir(exist_ok=True);s=pd.read_csv(root/'results/conflict_summary.csv');ss=pd.read_csv(root/'results/threshold_sensitivity.csv');ls=pd.read_csv(root/'results/lambda_sensitivity.csv')
    d=Drawing(650,390);a=s[(s.partition=='A1_full')&(s.domain!='ALL')].sort_values('conflict_rate',ascending=True)
    left,right=205,605
    labels={'arxiv':'学术论文（arxiv）','book':'图书（book）','c4':'网页语料（c4）','commoncrawl':'网络抓取（commoncrawl）','github':'代码（github）','stackexchange':'问答（stackexchange）','wikipedia':'百科（wikipedia）'}
    for tick in range(0,71,10):
        xx=left+(right-left)*tick/70;d.add(Line(xx,65,xx,340,strokeColor=HexColor('#dddddd'),strokeWidth=.5));text(d,xx,49,tick,9,'middle')
    for i,r in enumerate(a.itertuples()):
        y=80+i*38;val=r.conflict_rate*100;xx=(right-left)*val/70
        text(d,left-10,y+4,labels[r.domain],10,'end');d.add(Rect(left,y,xx,17,fillColor=HexColor(BLUE),strokeColor=None));text(d,left+xx+7,y+4,f'{val:.2f}%（{r.n:,}条）',8)
    text(d,205,364,'A1抽样集：五维评价，固定20%与80%分位阈值',10);text(d,(left+right)/2,20,'候选冲突比例（%）',11,'middle');save(d,out/'fig1_domain_conflict')
    series=[]
    for part,name,col in [('A1_holdout','A1内部留出集',BLUE),('A2_new','A2新增学术论文',ORANGE),('A3_new','A3新增代码',GREEN)]:
        t=ss[(ss.features=='groups5')&(ss.partition==part)].sort_values('tail_probability');series.append((name,list(t.tail_probability*100),list(t.rate*100),col))
    lines(out/'fig2_threshold_sensitivity',series,(10,25),(0,85),'低分位阈值 p（%），高分位阈值为 100-p','候选冲突比例（%）',[10,15,20,25],[0,20,40,60,80])
    series=[]
    for part,name,col in [('A1_holdout','A1内部留出集',BLUE),('A2_new','A2新增学术论文',ORANGE),('A3_new','A3新增代码',GREEN)]:
        t=ls[ls.partition==part].sort_values('lambda');series.append((name,list(t['lambda']),list(t['mean']),col))
    lines(out/'fig3_compensation_sensitivity',series,(0,.5),(25,85),'偏好保守程度参数 λ','候选质量评分均值（0—100分）',[0,.1,.25,.5],[30,40,50,60,70,80])
    (out/'figure_manifest.json').write_text(json.dumps({'status':'exploratory_not_accepted','backend':'ReportLab vector drawing','fig1':{'input':'results/conflict_summary.csv','partition':'A1_full','all_domains':True},'fig2':{'input':'results/threshold_sensitivity.csv','fit':'A1_fit only','partitions':['A1_holdout','A2_new','A3_new']},'fig3':{'input':'results/lambda_sensitivity.csv','interpretation':'preference sensitivity, not accuracy or improvement'},'formats':['SVG editable text','PDF vector','PNG preview generated from SVG'],'error_bars':'none; descriptive values, not population estimates'},indent=2))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]/'experiments/runs/q1-conflict-trial-20260924-r01');ap.add_argument('--font');a=ap.parse_args();main(a.root,a.font)
