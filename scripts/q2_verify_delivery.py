"""Verify the published Q2 file manifest, syntax, structured data and links."""
import ast
import csv
import hashlib
import io
import json
from pathlib import Path
import re


def main():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root/'data/manifests/q2_research_files.json').read_text(encoding='utf-8'))
    links = 0
    for record in manifest['files']:
        path = root/record['path']
        payload = path.read_bytes()
        assert hashlib.sha256(payload).hexdigest() == record['sha256'], record['path']
        if path.suffix == '.py':
            ast.parse(payload.decode('utf-8-sig'), filename=record['path'])
        elif path.suffix == '.json':
            json.loads(payload.decode('utf-8-sig'))
        elif path.suffix == '.csv':
            rows = list(csv.reader(io.StringIO(payload.decode('utf-8-sig'))))
            assert all(len(row)==len(rows[0]) for row in rows), record['path']
        elif path.suffix == '.md':
            for target in re.findall(r'\]\(([^)]+)\)',payload.decode('utf-8')):
                target = target.strip('<>').split('#')[0]
                if not target or '://' in target or target.startswith('mailto:'):
                    continue
                assert (path.parent/target).exists(), (record['path'],target)
                links += 1
    for name,key in [('experiments/index.csv','run_id'),('paper/claim-ledger.csv','claim_id'),('governance/ai-use-log.csv','prompt_run_id')]:
        rows = list(csv.DictReader(io.StringIO((root/name).read_text(encoding='utf-8-sig'))))
        ids = [r[key] for r in rows if r[key].startswith(('q2-', 'Q2-RH-', 'Q2-E1-', 'Q2-E2-', 'PR-Q2-E1-', 'PR-Q2-E2-', 'PR-Q2-RESEARCH-HANDOFF-'))]
        assert len(ids)==len(set(ids)), (name,'duplicate IDs')
    print(json.dumps(dict(status='PASS',files=len(manifest['files']),local_links=links),indent=2))


if __name__ == '__main__':
    main()
