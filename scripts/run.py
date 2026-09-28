#!/usr/bin/env python3
"""Create an isolated evidence/output directory outside the repository."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from wrappers import ROOT, load_routes


def external_path(path, root=ROOT):
    path = Path(path).expanduser().absolute()
    for component in [path, *path.parents]:
        if component.is_symlink():
            raise ValueError('symlinked run path: ' + str(component))
    resolved = path.resolve()
    if resolved == root.resolve() or root.resolve() in resolved.parents:
        raise ValueError('run data must stay outside the repository')
    return resolved


def initialize(workflow, base=None, root=ROOT):
    if workflow not in load_routes(root):
        raise ValueError('unknown workflow')
    parent = external_path(base or Path.home() / '.local/share/sales-template/runs', root)
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    run = Path(tempfile.mkdtemp(prefix=workflow + '-', dir=parent))
    for folder in ['raw', 'calls', 'outputs']:
        (run / folder).mkdir(mode=0o700)
    now = datetime.now(timezone.utc).astimezone().isoformat()
    (run / 'run.json').write_text(json.dumps({'version': 1, 'workflow': workflow,
        'started_at': now, 'repo': str(root.resolve()), 'mode': 'evidence'}, indent=2) + '\n')
    (run / 'run.json').chmod(0o600)
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init'])
    parser.add_argument('workflow', choices=list(load_routes()))
    parser.add_argument('--base', type=Path)
    args = parser.parse_args()
    print(initialize(args.workflow, args.base))
