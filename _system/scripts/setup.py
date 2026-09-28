#!/usr/bin/env python3
"""Initialize private settings without overwrite; report scoped configuration gaps."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '_shared/scripts'))
import yaml
from wrappers import ROOT, load_routes, safe_path
from configuration import (LEGACY_PRIVATE, requirements, validate_policy,
                           capability_errors, mapping_errors, text)

PRIVATE = {'_shared/policy.yaml': '_shared/policy.example.yaml',
           '_shared/adapters.json': '_shared/adapters.example.json'}
OPTIONAL_EFFECTS = {'handoff.post': 'handoff', 'provisioning.execute': 'provisioning'}


def initialize(root=ROOT):
    paths = [(safe_path(root, dest), safe_path(root, source)) for dest, source in PRIVATE.items()]
    for dest, source in paths:
        if dest.exists() and not dest.is_file():
            raise ValueError('configuration destination is not a file')
        if not source.is_file():
            raise ValueError('missing example: ' + str(source))
    result = []
    for old in sorted(LEGACY_PRIVATE):
        if (root / old).exists() or (root / old).is_symlink():
            result.append('legacy private settings preserved: ' + old + '; follow setup/migration.md')
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


def read_object(root, path, yaml_format=False):
    body = safe_path(root, path).read_text()
    result = yaml.safe_load(body) if yaml_format else json.loads(body)
    if not isinstance(result, dict):
        raise ValueError(path + ': expected an object')
    return result


def selected_effects(name, row, policy, effects=False, effect=None):
    allowed = row['effects'] + (list(OPTIONAL_EFFECTS) if name == 'close' else [])
    selected = list(dict.fromkeys(effect or []))
    if effects:
        selected = list(row['effects'])
        if name == 'close':
            close = policy.get('close', {})
            if isinstance(close, dict):
                for capability, key in OPTIONAL_EFFECTS.items():
                    cfg = close.get(key, {})
                    if isinstance(cfg, dict) and cfg.get('enabled') is True:
                        selected.append(capability)
    if any(c not in allowed for c in selected):
        raise ValueError(name + ': unsupported effect; allowed: ' + ', '.join(allowed))
    return selected


def effect_policy_errors(policy, selected):
    errors = []
    for capability, key in OPTIONAL_EFFECTS.items():
        if capability not in selected:
            continue
        cfg = policy.get('close', {}).get(key, {})
        if cfg.get('enabled') is not True:
            errors.append(capability + ': disabled in close policy')
        if key == 'handoff':
            owners = cfg.get('owners')
            if not text(cfg.get('destination')) or not isinstance(owners, list) or not owners or any(not text(x) for x in owners):
                errors.append('configure handoff destination and owners')
        elif not text(cfg.get('contract')):
            errors.append('review the full provisioning and recovery contract')
    return errors


def describe_requirements(root=ROOT, workflow=None, effects=False, effect=None):
    routes = load_routes(root)
    if effect and not workflow:
        raise ValueError('--effect requires --workflow')
    path = safe_path(root, '_shared/policy.yaml')
    policy = read_object(root, '_shared/policy.yaml' if path.exists() else '_shared/policy.example.yaml', True)
    result = {}
    for name in [workflow] if workflow else routes:
        row = routes[name]
        selected = selected_effects(name, row, policy, effects, effect)
        result[name] = requirements(name, policy, row['required'] + selected)
        result[name]['effects_checked'] = selected
    return result


def doctor(root=ROOT, workflow=None, effects=False, effect=None):
    try:
        routes = load_routes(root)
        if workflow is not None and workflow not in routes:
            raise ValueError('unknown workflow: ' + str(workflow))
        if effect and not workflow:
            raise ValueError('--effect requires --workflow')
        if effect and effects:
            raise ValueError('choose --effect or --effects, not both')
        policy = read_object(root, '_shared/policy.yaml', True)
        example = read_object(root, '_shared/policy.example.yaml', True)
        adapters = read_object(root, '_shared/adapters.json')
        errors = []
        if adapters.get('version') != 2:
            errors.append('unsupported adapter configuration version')
        if adapters.get('policy_sha256') != policy_hash(root):
            errors.append('policy has not been reviewed at its current hash')
        if 'mode' in policy:
            errors.append('remove obsolete policy.mode after review; adapters.mode is authoritative')
        if adapters.get('mode') != 'configured':
            errors.append('deployment is in example mode')
        for key in ('capabilities', 'field_mappings', 'state_mappings', 'data_contracts'):
            if not isinstance(adapters.get(key), dict):
                raise ValueError('adapters.' + key + ': expected an object')
        status = {}
        for name in [workflow] if workflow else routes:
            row = routes[name]
            selected = selected_effects(name, row, policy, effects, effect)
            required = row['required'] + selected
            policy_errors = validate_policy(policy, example, name, root)
            gaps = {c: capability_errors(adapters, c) for c in required}
            gaps = {c: reasons for c, reasons in gaps.items() if reasons}
            required_schema = requirements(name, policy, required)
            local_errors = policy_errors + mapping_errors(adapters, required_schema)
            if not policy_errors:
                local_errors += effect_policy_errors(policy, selected)
            optional = [c for c in row['optional'] if capability_errors(adapters, c)]
            status[name] = {'missing': list(gaps), 'capability_errors': gaps,
                            'errors': local_errors, 'optional_missing': optional,
                            'effects_checked': selected}
        return {'ready': not errors and not any(r['missing'] or r['errors'] for r in status.values()),
                'errors': errors, 'workflows': status,
                'limit': 'Configuration only. Verify live tools, access and contracts. No approval is granted.'}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, yaml.YAMLError) as exc:
        return {'ready': False, 'errors': [str(exc)],
                'hint': 'Run .venv/bin/python _system/scripts/setup.py init, then follow setup/questionnaire.md.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['init', 'requirements', 'doctor', 'policy-hash'])
    parser.add_argument('--workflow', choices=list(load_routes()))
    effects = parser.add_mutually_exclusive_group()
    effects.add_argument('--effects', action='store_true', help='check all workflow writes and enabled optional effects; never approval')
    effects.add_argument('--effect', action='append', help='check only this effect plus required reads; repeat for a combined proposal')
    args = parser.parse_args()
    if args.effect and not args.workflow:
        parser.error('--effect requires --workflow')
    if args.action == 'init':
        print('\n'.join(initialize()))
        return 0
    if args.action == 'policy-hash':
        print(policy_hash())
        return 0
    if args.action == 'requirements':
        print(json.dumps(describe_requirements(workflow=args.workflow, effects=args.effects, effect=args.effect), indent=2))
        return 0
    result = doctor(workflow=args.workflow, effects=args.effects, effect=args.effect)
    print(json.dumps(result, indent=2))
    return 0 if result['ready'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, AttributeError, yaml.YAMLError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
