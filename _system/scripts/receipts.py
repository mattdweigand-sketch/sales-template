#!/usr/bin/env python3
"""Bind explicit normalized helper inputs to preserved raw provider evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from run import external_path


def instant(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timestamps require a timezone offset')
    return parsed


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_file(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('symlinked receipt path')
    return path.read_bytes()


def run_info(run):
    run = external_path(run)
    info = json.loads(read_file(run / 'run.json'))
    if info.get('version') != 1:
        raise ValueError('unknown run format')
    return run, instant(info['started_at'])


def capture(run, call_id, raw_input, raw_output, normalized, started_at, completed_at, provider):
    run, since = run_info(run)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', call_id):
        raise ValueError('invalid call ID')
    start, end = instant(started_at), instant(completed_at)
    if not since <= start <= end <= datetime.now(timezone.utc):
        raise ValueError('call times must be within the current run and not in the future')
    if not provider.strip():
        raise ValueError('provider tool name is required')
    normal = json.loads(read_file(normalized))
    if set(normal) != {'input', 'output'} or not isinstance(normal['input'], dict) or not isinstance(normal['output'], dict):
        raise ValueError('normalized JSON needs exactly input and output objects')
    if not isinstance(normal['input'].get('arguments'), dict):
        raise ValueError('normalized input requires arguments')
    if not isinstance(normal['output'].get('result'), dict):
        raise ValueError('normalized output requires a result object, including failures')
    for obj, key, value in [(normal['input'], 'started_at', started_at), (normal['output'], 'completed_at', completed_at)]:
        if key in obj and obj[key] != value:
            raise ValueError('normalized timestamp conflicts with actual call time')
        obj[key] = value
    reference = '../raw/output_' + call_id + '.json'
    result = normal['output']['result']
    if 'provider_reference' in result and result['provider_reference'] != reference:
        raise ValueError('normalized provider reference must match captured raw output')
    result['provider_reference'] = reference
    blobs = {
        f'raw/input_{call_id}.json': read_file(raw_input),
        f'raw/output_{call_id}.json': read_file(raw_output),
        f'calls/input_{call_id}.json': (json.dumps(normal['input'], indent=2)+'\n').encode(),
        f'calls/output_{call_id}.json': (json.dumps(normal['output'], indent=2)+'\n').encode(),
    }
    receipt = {'version': 1, 'call_id': call_id, 'provider': provider,
               'started_at': started_at, 'completed_at': completed_at,
               'files': {rel: digest(blob) for rel, blob in blobs.items()}}
    blobs[f'calls/receipt_{call_id}.json'] = (json.dumps(receipt, indent=2)+'\n').encode()
    destinations = [run / rel for rel in blobs]
    for dest in destinations:
        external_path(dest)
        if dest.exists():
            raise ValueError('call ID already captured; preserve evidence and use a new ID')
    created = []
    try:
        for rel, blob in blobs.items():
            dest = run / rel
            with dest.open('xb') as stream:
                stream.write(blob)
            created.append(dest)
            dest.chmod(0o600)
            # Legacy helpers sort calls by mtime. Bind it to the actual call time.
            os.utime(dest, (end.timestamp(), end.timestamp()))
    except BaseException:
        for dest in created:
            dest.unlink()
        raise
    return receipt


def verify(run):
    errors = []
    try:
        run, since = run_info(run)
        expected = set()
        receipts = list((run / 'calls').glob('receipt_*.json'))
        if not receipts:
            raise ValueError('no captured receipts')
        for file in receipts:
            receipt = json.loads(read_file(file))
            call_id = file.stem[len('receipt_'):]
            if receipt.get('version') != 1 or receipt.get('call_id') != call_id or not receipt.get('provider'):
                raise ValueError('invalid receipt metadata')
            start, end = instant(receipt['started_at']), instant(receipt['completed_at'])
            if not since <= start <= end <= datetime.now(timezone.utc):
                raise ValueError('stale or invalid call timestamp: ' + call_id)
            required = {f'{folder}/{kind}_{call_id}.json' for folder in ['raw','calls'] for kind in ['input','output']}
            if set(receipt['files']) != required:
                raise ValueError('receipt file set differs: ' + call_id)
            for rel, sha in receipt['files'].items():
                path = run / rel
                if digest(read_file(path)) != sha:
                    errors.append('receipt changed: ' + rel)
                if rel.startswith('calls/'):
                    expected.add(path.name)
                    if abs(path.stat().st_mtime - end.timestamp()) > 1:
                        errors.append('normalized file timestamp differs: ' + rel)
        actual = {p.name for p in (run / 'calls').glob('*.json') if p.name.startswith(('input_', 'output_'))}
        if actual != expected:
            errors.append('unbound or missing normalized calls')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    return errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    capture_parser = sub.add_parser('capture')
    for name in ['run', 'call-id', 'raw-input', 'raw-output', 'normalized', 'started-at', 'completed-at', 'provider']:
        capture_parser.add_argument('--'+name, required=True)
    check = sub.add_parser('verify')
    check.add_argument('--run', required=True)
    args = parser.parse_args()
    try:
        if args.action == 'capture':
            print(json.dumps(capture(**{k:v for k,v in vars(args).items() if k != 'action'}), indent=2))
        else:
            errors = verify(args.run)
            print(json.dumps({'ready': not errors, 'errors': errors,
                'limit': 'Byte integrity and run binding only; review raw-to-normalized semantics and provider access.'}, indent=2))
            raise SystemExit(bool(errors))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
