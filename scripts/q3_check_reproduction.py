"""Compare a fresh portable run to the archived Q3 exploratory results."""
from pathlib import Path
import json, os
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'experiments/runs/q3-frozen-q2-exploration-20260925-r01'
OUT=Path(os.environ.get('Q3_OUTPUT_ROOT',str(ROOT/'local/q3-reproduction')))
rows=[]
for file in sorted(ARCHIVE.glob('*.csv')):
    old=pd.read_csv(file);new=pd.read_csv(OUT/file.name)
    pd.testing.assert_frame_equal(old,new,check_exact=False,rtol=1e-10,atol=1e-10)
    rows.append(dict(file=file.name,rows=len(old),columns=len(old.columns),status='PASS'))
old=json.loads((ARCHIVE/'independent_verification.json').read_text())
new=json.loads((OUT/'independent_verification.json').read_text())
for k in old: assert np.isclose(old[k],new[k],rtol=1e-10,atol=1e-10),k
summary=dict(status='PASS',csv_tables=rows,independent_verification=new,rtol=1e-10,atol=1e-10)
(OUT/'reproduction_verification.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
