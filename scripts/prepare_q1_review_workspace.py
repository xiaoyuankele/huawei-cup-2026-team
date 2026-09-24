"""Materialize an isolated copy of the submitted local experiment without changing WP-A."""
from pathlib import Path
import argparse, shutil

def prepare(root, output):
    root=Path(root).resolve(); output=Path(output).resolve()
    if output == root or root in output.parents or output in root.parents:
        raise ValueError('Use a separate sibling directory, not an ancestor or child of the repository')
    if output.exists():
        raise FileExistsError('Output must not exist; no overwrite is performed')
    shutil.copytree(root,output,ignore=shutil.ignore_patterns('.git','__pycache__','origin','local','problem'))
    candidate=root/'reference/preprocessing_refresh_candidate'
    for source in candidate.rglob('*'):
        if source.is_file() and source.name != 'README.md':
            target=output/source.relative_to(candidate); target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
    return output

if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--root',default='.');parser.add_argument('--output',required=True)
    args=parser.parse_args();print(prepare(args.root,args.output))
