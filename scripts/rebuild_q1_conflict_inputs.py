"""Rebuild normalized records from read-only original attachments and frozen Q1 parameters.
Usage: python scripts/rebuild_q1_conflict_inputs.py --raw-root /path/to/real_attachments --run-dir ...
Writes only the normalized input inside the specified run directory.
"""
from pathlib import Path
import argparse,hashlib,json,lzma,math
import pandas as pd

def main(raw,run):
    (run/'artifacts').mkdir(parents=True,exist_ok=True)
    inp=run/'inputs';stats=json.loads((inp/'normalization_stats.json').read_text());weights=json.loads((inp/'q1_model.json').read_text())['weights'];cols=list(weights)
    paths={'A1':'slimpajama_quality_signal_sample.jsonl.xz','A2':'slimpajama_quality_extended/arxiv_part-6777d8857c6e-000486.jsonl.xz','A3':'slimpajama_quality_extended/github_part-6777d8857c6e-000275.jsonl.xz'}
    costs={'rps_doc_frac_no_alph_words','rps_doc_frac_chars_top_2gram','rps_doc_frac_chars_top_3gram'};rows=[]
    for dataset,rel in paths.items():
        p=raw/'A_data_value'/rel;h=hashlib.sha256()
        with p.open('rb') as f:
            for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
        if h.hexdigest()!=stats['raw_hash_before'][dataset]:raise ValueError(f'Raw input hash mismatch: {dataset}')
        with lzma.open(p,'rt') as f:
            for line in f:
                r=json.loads(line);values={}
                for col in cols:
                    if col=='fineweb_edu':value=r[col][0] if isinstance(r[col],list) else r[col]
                    elif col.endswith('_margin'):
                        key='ad_en' if col.startswith('ad_') else 'fluency_en';value=r[key][1]-r[key][0]
                    elif col.endswith('_expected'):
                        logits=r[col.removesuffix('_expected')];exp=[math.exp(v-max(logits)) for v in logits];value=sum(k*v for k,v in enumerate(exp))/sum(exp)
                    elif col.startswith('qurater_'):value=r['qurater'][{'qurater_writing_style':0,'qurater_facts_trivia':2,'qurater_educational_value':3}[col]]
                    else:value=r[col]
                    if not math.isfinite(value):raise ValueError(f'Nonfinite selected indicator: {r["id"]}, {col}')
                    st=stats['fit_statistics'][col];lo=st['oriented_p01'];hi=st['oriented_p99'];value=-value if col in costs else value
                    values[col]=.5 if hi==lo else max(0,min(1,(value-lo)/(hi-lo)))
                sid=str(r['id']);split='fit' if int.from_bytes(hashlib.sha256(('20260923|'+sid).encode()).digest()[:8],'big')%100<80 else 'holdout'
                domain={'A2':'arxiv','A3':'github'}.get(dataset) or r.get('_source_domain') or r.get('sub_path','').split('/')[0]
                rows.append({'id':sid,'dataset':dataset,'domain':domain,'split':split,**values})
        print(dataset,'read',flush=True)
    pd.DataFrame(rows).to_csv(run/'artifacts/normalized_records.csv.gz',index=False,compression={'method':'gzip','mtime':0},float_format='%.17g')
    print('Rebuilt',len(rows),'records. Raw sources unchanged.')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--raw-root',required=True,type=Path);ap.add_argument('--run-dir',required=True,type=Path);a=ap.parse_args();main(a.raw_root,a.run_dir)
