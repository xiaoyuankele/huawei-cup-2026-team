from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
m=json.loads((root/'docs/tasks/WP-C-file-manifest.json').read_text());bad=[]
for e in m['files']:
 p=root/e['path']
 if not p.exists() or p.stat().st_size!=e['bytes'] or sha(p)!=e['sha256']:bad.append(e['path'])
if bad:print('FAILED',bad);sys.exit(1)
print('Verified',len(m['files']),'files. This verifies bytes, not team acceptance.')
