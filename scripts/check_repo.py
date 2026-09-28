#!/usr/bin/env python3
"""Check pointers, public files and links without requiring private settings."""
import json
from pathlib import Path
import re
import subprocess
import sys
import yaml
from wrappers import ROOT, load_routes, render
from configuration import CURRENT_PRIVATE, LEGACY_PRIVATE

PRIVATE = CURRENT_PRIVATE
SKIP = {'.git', '.venv', '__pycache__'}
# Split source labels so the scanner's own definitions do not match its content scan.
SOURCE_LABELS = ('perplex' + 'ity', 'ppl' + 'x', 'AGENTIC_' + 'WH')


def dependency_errors(root, routes):
    errors = []
    for name, row in routes.items():
        procedure = root / row['workflow']
        parts = procedure.read_text().split('---\n', 2)
        header = yaml.safe_load(parts[1]) if len(parts) == 3 and not parts[0] else None
        if not isinstance(header, dict) or not isinstance(header.get('reads'), str):
            errors.append(name + ': missing reads frontmatter')
            continue
        for ref in re.findall(r'(?:\.\./)*(?:[A-Za-z0-9_-]+/)+[A-Za-z0-9_.-]*', header['reads']):
            if ref in {'_shared/policy.yaml', '_shared/adapters.json'}:
                ref = ref.replace('.yaml', '.example.yaml').replace('.json', '.example.json')
            target = root / ref if ref.startswith(('_shared/', 'setup/', 'workflows/')) else procedure.parent / ref
            resolved = target.resolve()
            if root.resolve() not in resolved.parents or not target.exists():
                errors.append(name + ': missing or external reads dependency: ' + ref)
    return errors


def public_files(root):
    root = root.resolve()
    probe = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=root, capture_output=True, text=True)
    if probe.returncode == 0 and Path(probe.stdout.strip()).resolve() == root:
        result = subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'], cwd=root, capture_output=True, check=True)
        return sorted({Path(p) for p in result.stdout.decode().split('\0') if p})
    if (root / '.git').exists() or (root / '.git').is_symlink():
        raise ValueError('cannot inspect repository Git inventory')
    return sorted(p.relative_to(root) for p in root.rglob('*') if (p.is_file() or p.is_symlink())
                  and not SKIP.intersection(p.relative_to(root).parts)
                  and str(p.relative_to(root)) not in PRIVATE)


def check(root=ROOT):
    errors = render(root, check=True)
    routes = load_routes(root)
    errors += dependency_errors(root, routes)
    workflows = {p.name for p in (root / 'workflows').iterdir() if p.is_dir()}
    if set(routes) != workflows:
        errors.append('route/workflow mismatch')
    files = public_files(root)
    for rel in files:
        path = root / rel
        if path.is_symlink():
            errors.append('public symlink: ' + str(rel))
            continue
        if str(rel) in PRIVATE | LEGACY_PRIVATE or set(rel.parts) & {'output', 'outputs', 'runs'} or rel.name.startswith('.env'):
            errors.append('private/runtime material included: ' + str(rel))
            continue
        if not path.is_file():
            errors.append('missing tracked file: ' + str(rel))
            continue
        if path.suffix not in {'.md','.json','.py','.txt','.yml','.yaml'}:
            continue
        body = path.read_text()
        if any(term.lower() in body.lower() for term in SOURCE_LABELS):
            errors.append('source-specific branding or schema: ' + str(rel))
        if re.search(r'\b[A-Za-z][A-Za-z0-9_]+__c\b', body):
            errors.append('source custom API field; use a logical adapter field: ' + str(rel))
        if path.suffix == '.json':
            json.loads(body)
        if path.suffix == '.md':
            for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', body):
                if '://' in link or link.startswith('#') or '<' in link or '{' in link:
                    continue
                target = (path.parent / link.split('#')[0]).resolve()
                if not target.exists():
                    errors.append(f'broken link in {rel}: {link}')
        if 'current_session_' + 'context/' in body or '/home/' + 'user/workspace' in body:
            errors.append('obsolete host path: ' + str(rel))
        if re.search(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----', body):
            errors.append('private key material: ' + str(rel))
        if rel.suffix in {'.md', '.json', '.yaml'} and re.search(r'\b[CU][0-9A-Z]{10}\b', body):
            errors.append('source deployment identifier: ' + str(rel))
    return errors, len(files)


if __name__ == '__main__':
    try:
        errors, count = check()
        print('\n'.join(errors) if errors else f'PASS: {len(load_routes())} workflows; {count} public files; pointers, links and packaging.')
        sys.exit(bool(errors))
    except (OSError, ValueError, TypeError, yaml.YAMLError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
