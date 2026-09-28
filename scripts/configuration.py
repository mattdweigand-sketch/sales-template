"""Scoped setup contracts. These validate configuration, never provider access."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

LEGACY_PRIVATE = {'_shared/policy.json', '_shared/adapters.md', '.claude/settings.local.json'}
CURRENT_PRIVATE = {'_shared/policy.yaml', '_shared/adapters.json', '.codex/config.toml'}

CONTRACT_KEYS = {
    'crm.read': 'identity queries pagination errors types',
    'crm.write': 'payload preconditions deduplication readback recovery',
    'mail.read': 'identity search pagination full_body history_limits errors',
    'mail.draft': 'reply_parent payload deduplication readback recovery',
    'calendar.read': 'identity queries pagination timezone errors',
    'transcripts.read': 'identity lookup provenance full_text errors',
    'usage.read': 'source fields grain scope pagination timezone unit errors',
    'handoff.post': 'destination payload deduplication readback recovery',
    'provisioning.execute': 'eligibility payload side_effects idempotency readback recovery',
    'pdf.render': 'binary inspection',
    'web.read': 'retrieval dates links',
}
CONTRACT_KEYS = {key: value.split() for key, value in CONTRACT_KEYS.items()}

POLICY_BLOCKS = {
    'sales-call-prep': 'identity crm pipeline call_prep research tooling',
    'interaction-sync': 'identity crm call_prep interaction email_voice followup pipeline tooling',
    'task-triage-speed-run': 'identity crm pipeline followup email_voice tooling',
    'pipeline-review': 'identity crm pipeline forecast reporting cadence tooling',
    'forecast-weekly': 'identity crm pipeline forecast reporting cadence tooling',
    'pilot-usage': 'identity company pilot_usage tooling',
    'close': 'identity crm pipeline close',
}

# Baseline logical fields used by the procedures. Conditional fields are added below.
CRM_FIELDS = {
    'sales-call-prep': {
        'Account': 'Id Name Website Industry NumberOfEmployees Description OwnerId',
        'Contact': 'Id AccountId Name Email',
        'Opportunity': 'Id AccountId Name StageName Amount CloseDate NextSteps IsClosed',
        'Task': 'Id WhatId WhoId Subject ActivityDate Status Description TaskSubtype Direction',
    },
    'interaction-sync': {
        'Account': 'Id Name',
        'Contact': 'Id AccountId FirstName LastName Name Email Title OwnerId Description',
        'Opportunity': 'Id AccountId Name StageName Amount CloseDate NextSteps IsClosed',
        'OpportunityContactRole': 'Id OpportunityId ContactId Role',
        'Task': 'Id WhatId WhoId OwnerId Subject ActivityDate Status Description TaskSubtype',
    },
    'task-triage-speed-run': {
        'Account': 'Id Name',
        'Contact': 'Id AccountId FirstName LastName Name Email Title OwnerId Description Account.Name',
        'Task': 'Id OwnerId WhoId WhatId What.Name Subject ActivityDate Status IsClosed Description',
    },
    'pipeline-review': {
        'Opportunity': 'Id OwnerId IsClosed Name StageName Amount CloseDate NextSteps LastActivityDate ForecastCategoryName Type Account.Name AccountId',
        'Contact': 'Id Email AccountId',
        'Task': 'Id Subject ActivityDate Status IsClosed TaskSubtype Direction WhatId AccountId Who.Name',
        'Event': 'Id Subject ActivityDate StartDateTime EndDateTime WhatId AccountId',
    },
    'forecast-weekly': {
        'Opportunity': 'Id OwnerId IsClosed IsWon Name StageName Amount CloseDate NextSteps LastActivityDate ForecastCategoryName Account.Name AccountId',
        'Contact': 'Id Name Email AccountId',
        'Task': 'Id Subject ActivityDate Status IsClosed TaskSubtype Direction WhatId AccountId Who.Name',
        'Event': 'Id Subject ActivityDate StartDateTime EndDateTime WhatId AccountId',
    },
    'close': {
        'Opportunity': 'Id AccountId StageName IsClosed IsWon Amount Currency CloseDate NextSteps AgreementReference SignatureDate',
        'Account': 'Id Name',
        'Contact': 'Id AccountId Name Email',
        'Task': 'Id WhatId WhoId OwnerId Subject ActivityDate Status Description',
    },
}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def requirements(workflow, policy, capabilities):
    fields = {obj: set(names.split()) for obj, names in CRM_FIELDS.get(workflow, {}).items()}
    pipeline = policy.get('pipeline', {})
    if workflow in {'interaction-sync', 'pipeline-review'} and isinstance(pipeline, dict):
        required = pipeline.get('required_fields', {})
        if isinstance(required, dict):
            for names in required.values():
                if isinstance(names, list):
                    fields['Opportunity'].update(name for name in names if text(name))
        conditions = pipeline.get('conditional_fields', [])
        for row in conditions if isinstance(conditions, list) else []:
            if isinstance(row, dict):
                if text(row.get('field')):
                    fields['Opportunity'].add(row['field'])
                if isinstance(row.get('when'), dict):
                    fields['Opportunity'].update(x for x in row['when'] if text(x))
    if workflow == 'close':
        close = policy.get('close', {})
        if isinstance(close, dict) and isinstance(close.get('required_fields'), list):
            fields['Opportunity'].update(x for x in close['required_fields'] if text(x))
    states = {}
    if 'Task' in fields:
        states['Task.Status'] = ['open', 'completed']
    if 'Opportunity' in fields:
        states['Opportunity.state'] = ['open', 'won', 'lost']
    if 'Opportunity' in fields and isinstance(pipeline, dict):
        stages = pipeline.get('stage_order', [])
        if isinstance(stages, list):
            states['Opportunity.StageName'] = [s for s in stages if text(s)]
    if workflow == 'forecast-weekly':
        states['Opportunity.ForecastCategoryName'] = ['commit', 'upside']
    return {'policy_blocks': POLICY_BLOCKS[workflow].split(),
            'field_mappings': {obj: sorted(names) for obj, names in fields.items()},
            'state_mappings': states,
            'data_contracts': {c: CONTRACT_KEYS[c] for c in capabilities}}


def capability_errors(adapters, capability):
    errors = []
    config = adapters.get('capabilities', {}).get(capability)
    if not isinstance(config, dict):
        return [capability + ': missing capability object']
    if config.get('status') != 'configured':
        errors.append(capability + ': not configured')
    for key in ('provider', 'tool', 'contract'):
        if not text(config.get(key)):
            errors.append(f'{capability}.{key}: required nonempty text')
    try:
        verified = datetime.fromisoformat(config['verified_at'].replace('Z', '+00:00'))
        if verified.utcoffset() is None or verified > datetime.now(timezone.utc):
            raise ValueError('expected past or current offset-aware time')
    except (KeyError, TypeError, ValueError, AttributeError):
        errors.append(capability + '.verified_at: expected past or current offset-aware ISO timestamp')
    contract = adapters.get('data_contracts', {}).get(capability)
    for key in CONTRACT_KEYS[capability]:
        if not isinstance(contract, dict) or not text(contract.get(key)):
            errors.append(f'data_contracts.{capability}.{key}: required mapping/behavior description')
    return errors


def mapping_errors(adapters, required):
    errors = []
    for kind in ('field_mappings', 'state_mappings'):
        for group, names in required[kind].items():
            mappings = adapters[kind].get(group)
            for name in names:
                if not isinstance(mappings, dict) or not text(mappings.get(name)):
                    errors.append(f'{kind}.{group}.{name}: required native mapping')
    return errors


def validate_policy(policy, example, workflow, root):
    """Validate selected structure and local constraints, not business meaning."""
    from coverage_check import quarter_bounds
    from hygiene_check import validate_policy as validate_hygiene
    errors = []
    dynamic = {'pipeline.required_fields', 'pipeline.stage_entry', 'forecast.targets',
               'call_prep.call_type', 'call_prep.expected_information'}

    def shape(value, default, path):
        if default is None:
            return
        if type(value) is not type(default):
            errors.append(path + ': expected ' + type(default).__name__)
            return
        if isinstance(default, dict) and path not in dynamic:
            for key, child in default.items():
                # Only the timezone is needed for a supplied pilot export.
                if path == 'identity' and workflow == 'pilot-usage' and key != 'timezone':
                    continue
                if path == 'tooling' and key == 'scripts':
                    continue
                if key not in value:
                    errors.append(path + '.' + key + ': missing setting')
                else:
                    shape(value[key], child, path + '.' + key)
        elif isinstance(default, list) and default:
            for index, item in enumerate(value):
                shape(item, default[0], f'{path}[{index}]')
        elif isinstance(value, str) and not value.strip():
            errors.append(path + ': expected nonempty text')

    for block in POLICY_BLOCKS[workflow].split():
        if block not in policy:
            errors.append('policy.' + block + ': missing block')
        else:
            shape(policy[block], example[block], block)
    if errors:
        return errors
    try:
        identity = policy['identity']
        today = datetime.now(ZoneInfo(identity['timezone'])).date()
        if workflow != 'pilot-usage':
            if not text(identity['owner_id']) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', identity['owner_email']) or identity['owner_email'].lower().endswith('@example.com'):
                errors.append('identity: configure verified owner ID and email')
            if not identity['internal_domains'] or 'example.com' in [d.lower() for d in identity['internal_domains']]:
                errors.append('identity.internal_domains: replace example domains')
            url = urlparse(policy['crm']['record_url'])
            if url.scheme not in {'http', 'https'} or not url.hostname or url.hostname.endswith('example.com') or '{Id}' not in policy['crm']['record_url']:
                errors.append('crm.record_url: configure a real HTTP(S) record URL containing {Id}')
        if 'pipeline' in POLICY_BLOCKS[workflow].split():
            validate_hygiene(policy)
            pp = policy['pipeline']
            for key in ('activity_days', 'closed_lost_silence_days'):
                if type(pp[key]) is not int or pp[key] < 0:
                    errors.append('pipeline.' + key + ': expected nonnegative integer')
            if not pp['in_scope_stages'] or len(pp['in_scope_stages']) != len(set(pp['in_scope_stages'])):
                errors.append('pipeline.in_scope_stages: expected unique nonempty scope')
            if any(not text(pp['stage_entry'].get(stage)) for stage in pp['in_scope_stages']) or set(pp['stage_entry']) - set(pp['stage_order']):
                errors.append('pipeline.stage_entry: supply criteria for every in-scope stage using configured keys')
        if workflow in {'interaction-sync', 'task-triage-speed-run', 'pipeline-review', 'forecast-weekly', 'close'}:
            author = identity['note_author']
            formats = [policy['crm']['note_prefix'], policy['crm']['cooldown_marker']]
            if 'pipeline' in POLICY_BLOCKS[workflow].split():
                formats += [policy['pipeline']['note_next_line'], policy['pipeline']['note_history_line']]
            if author == 'SELLER' or any('SELLER' in value or author not in value for value in formats):
                errors.append('identity.note_author: replace SELLER consistently in CRM and pipeline note formats')
        if workflow in {'interaction-sync', 'task-triage-speed-run'}:
            for key, value in policy['followup'].items():
                if type(value) is not int or value < (1 if key == 'recycle_after_unanswered' else 0):
                    errors.append('followup.' + key + ': invalid interval/count')
            voice = policy['email_voice']
            if re.search(r'\bSeller\b', voice['closing'], re.I):
                errors.append('email_voice.closing: replace the example seller signature')
            collateral = voice['collateral_path']
            if collateral is not None:
                path = Path(collateral).expanduser()
                if not path.is_absolute() or not path.is_dir() or path.resolve() == root.resolve() or root.resolve() in path.resolve().parents:
                    errors.append('email_voice.collateral_path: use an existing absolute directory outside the repo or null')
        if workflow in {'sales-call-prep', 'interaction-sync'}:
            cp = policy['call_prep']
            if not cp['call_type'] or any(not text(k) or not text(v) for k, v in cp['call_type'].items()):
                errors.append('call_prep.call_type: expected named types with criteria')
            if set(cp['call_type']) != set(cp['expected_information']) or any(not isinstance(v, list) or not v or any(not text(x) for x in v) for v in cp['expected_information'].values()):
                errors.append('call_prep.expected_information: supply questions for each configured call type')
        if workflow in {'pipeline-review', 'forecast-weekly'}:
            forecast = policy['forecast']
            quarter_bounds(today, forecast)
            if not forecast['commit_stages'] or not set(forecast['commit_stages']) <= set(policy['pipeline']['stage_order']):
                errors.append('forecast.commit_stages: use configured stage keys')
            if set(forecast['sources']) != {'crm','mail','calendar'} or len(forecast['sources']) != 3:
                errors.append('forecast.sources: configure crm, mail and calendar exactly once')
            for key, value in forecast['targets'].items():
                from datetime import date
                date.fromisoformat(key)
                if value is None or isinstance(value, bool) or not Decimal(str(value)).is_finite() or Decimal(str(value)) < 0:
                    errors.append('forecast.targets: expected finite nonnegative targets keyed by quarter-start date')
            target = forecast['target_default']
            if target is not None and (isinstance(target, bool) or not Decimal(str(target)).is_finite() or Decimal(str(target)) < 0):
                errors.append('forecast.target_default: expected nonnegative amount or null')
            if not re.fullmatch(r'[A-Z]{3}', policy['reporting']['currency']) or not 0 <= policy['reporting']['amount_decimal_places'] <= 6:
                errors.append('reporting: configure currency and 0..6 decimal places')
            cadence = policy['cadence']
            if not cadence['working_days'] or any(type(day) is not int or not 0 <= day <= 6 for day in cadence['working_days'] + [cadence['extended_review_weekday'], cadence['week_start_weekday']]):
                errors.append('cadence: weekdays must be integers from 0 to 6')
        if workflow == 'pilot-usage':
            cfg = policy['pilot_usage']
            ZoneInfo(cfg['timezone'])
            if not 0 <= cfg['usage_decimal_places'] <= 6 or not re.fullmatch(r'#[0-9a-fA-F]{6}', cfg['pdf']['accent_color']) or cfg['pdf']['page_size'] != 'Letter' or cfg['pdf']['timeout_seconds'] <= 0:
                errors.append('pilot_usage: check precision, PDF color, Letter size and positive timeout')
            if any(value in {'Example Company', 'Example Product'} for value in [policy['company']['name'], policy['company']['product_name'], cfg['pdf']['author']]):
                errors.append('company/pilot_usage: replace example report branding')
        scripts = {
            'sales-call-prep': ['mail_contact_stats'],
            'interaction-sync': [],
            'task-triage-speed-run': ['mail_contact_stats', 'triage_check', 'closeout_check'],
            'pipeline-review': ['hygiene_check', 'mail_digest', 'coverage_check'],
            'forecast-weekly': ['hygiene_check', 'mail_digest', 'coverage_check', 'forecast_math', 'forecast_notify'],
            'pilot-usage': ['pilot_usage'], 'close': [],
        }
        from wrappers import safe_path
        for key in scripts[workflow]:
            path = policy['tooling']['scripts'][key]
            if not text(path) or not safe_path(root, path).is_file():
                errors.append('tooling.scripts.' + key + ': missing repository helper')
        for block, keys in {'tooling':['calendar_lookback_days','calendar_lookahead_days','mail_search_max_addresses'], 'call_prep':['history_days'], 'research':['max_sources'], 'interaction':['max_buyer_quotes'], 'forecast':['activity_days','next_quarter_preview_days'], 'close':['followup_days']}.items():
            if block in POLICY_BLOCKS[workflow].split():
                for key in keys:
                    if type(policy[block][key]) is not int or policy[block][key] < 0:
                        errors.append(block + '.' + key + ': expected nonnegative integer')
    except (KeyError, TypeError, ValueError, AttributeError, InvalidOperation) as exc:
        errors.append('policy: ' + str(exc))
    return errors
