#!/usr/bin/env python3
"""Initialize private settings without overwrite; report configuration gaps."""
import argparse
import hashlib
import json
import sys
from zoneinfo import ZoneInfo
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared/scripts"))
from coverage_check import quarter_bounds
import yaml
from wrappers import ROOT, load_routes, safe_path

PRIVATE = {'_shared/policy.yaml': '_shared/policy.example.yaml',
           '_shared/adapters.json': '_shared/adapters.example.json'}


def initialize(root=ROOT):
    paths = [(safe_path(root, dest), safe_path(root, source)) for dest, source in PRIVATE.items()]
    for dest, source in paths:
        if dest.exists() and not dest.is_file():
            raise ValueError('configuration destination is not a file')
        if not source.is_file():
            raise ValueError('missing example: ' + str(source))
    result = []
    for dest, source in paths:
        try:
            with dest.open('xb') as stream:
                stream.write(source.read_bytes())
            dest.chmod(0o600)
            result.append('created ' + str(dest.relative_to(root)))
        except FileExistsError:
            result.append('preserved ' + str(dest.relative_to(root)))
    return result


def policy_hash(root=ROOT):
    return hashlib.sha256(safe_path(root, '_shared/policy.yaml').read_bytes()).hexdigest()


def doctor(root=ROOT, workflow=None, effects=False):
    routes = load_routes(root)
    names = [workflow] if workflow else list(routes)
    errors = []
    try:
        policy = yaml.safe_load(safe_path(root, '_shared/policy.yaml').read_text())
        adapters = json.loads(safe_path(root, '_shared/adapters.json').read_text())
        if not isinstance(policy, dict) or not isinstance(adapters, dict):
            raise ValueError('policy and adapter configuration must be objects')
        if adapters.get('version') != 2:
            errors.append('unsupported adapter configuration version')
        if adapters.get('policy_sha256') != policy_hash(root):
            errors.append('policy has not been reviewed at its current hash')
        identity = policy['identity']
        local_today = datetime.now(ZoneInfo(identity['timezone'])).date()
        needs_crm = any('crm.read' in routes[name]['required'] for name in names)
        if needs_crm and (not identity.get('owner_id') or not identity.get('owner_email')
                          or identity['owner_email'].endswith('@example.com')):
            errors.append('configure real seller identity and verify CRM identity readback')
        if set(names) & {'pipeline-review', 'forecast-weekly'}:
            quarter_bounds(local_today, policy['forecast'])
        if 'pilot-usage' in names:
            ZoneInfo(policy['pilot_usage']['timezone'])
        if adapters.get('mode') != 'configured':
            errors.append('deployment is in example mode')
        capabilities = adapters.get('capabilities', {})
        status = {}
        for name in names:
            row = routes[name]
            required = row['required'] + (row['effects'] if effects else [])
            if name == 'close' and effects:
                if policy['close']['handoff']['enabled']:
                    required = required + ['handoff.post']
                    if not policy['close']['handoff']['destination'] or not policy['close']['handoff']['owners']:
                        errors.append('configure handoff destination and owners')
                if policy['close']['provisioning']['enabled']:
                    required = required + ['provisioning.execute']
                    if not policy['close']['provisioning']['contract']:
                        errors.append('review the full provisioning and recovery contract')
            if any(c.startswith('crm.') for c in required):
                if not adapters.get('field_mappings') or not adapters.get('state_mappings'):
                    errors.append(name + ': configure native CRM field and state mappings')
            gaps = []
            for capability in required:
                config = capabilities.get(capability, {})
                if not isinstance(config, dict):
                    gaps.append(capability)
                    continue
                if (config.get('status') != 'configured' or not config.get('tool')
                        or not config.get('contract') or not config.get('verified_at')):
                    gaps.append(capability)
            optional = [c for c in row['optional'] if not isinstance(capabilities.get(c), dict) or capabilities[c].get('status') != 'configured']
            status[name] = {'missing': gaps, 'optional_missing': optional}
        return {'ready': not errors and not any(row['missing'] for row in status.values()),
                'errors': errors, 'workflows': status,
                'limit': 'Configuration only. Verify live tools, access and contracts. No approval is granted.'}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {'ready': False, 'errors': [str(exc)], 'hint': 'Run setup.py init, then follow setup/questionnaire.md.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init', 'doctor', 'policy-hash'])
    parser.add_argument('--workflow', choices=list(load_routes()))
    parser.add_argument('--effects', action='store_true', help='check write capabilities; never approval')
    args = parser.parse_args()
    if args.action == 'init':
        print('\n'.join(initialize()))
        return 0
    if args.action == 'policy-hash':
        print(policy_hash())
        return 0
    result = doctor(workflow=args.workflow, effects=args.effects)
    print(json.dumps(result, indent=2))
    return 0 if result['ready'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
