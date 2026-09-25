"""Portable paths for the archived Q2 research workflow."""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW_ROOT = Path(os.environ.get('Q2_RAW_ROOT', REPO / 'data/origin/real_attachments')).resolve()
RUNS = Path(os.environ.get('Q2_RUNS_ROOT', REPO / 'experiments/runs')).resolve()


def source_ref(path):
    path = Path(path).resolve()
    for root, prefix in [(RAW_ROOT, 'raw'), (RUNS, 'experiments/runs'), (REPO, '')]:
        try:
            relative = path.relative_to(root).as_posix()
            return '/'.join(filter(None, [prefix, '' if relative == '.' else relative]))
        except ValueError:
            pass
    return 'external/' + path.name
