"""Validate scoped workflow contracts without loading private settings or run data."""
from pathlib import Path
import re

ORDER = ('Inputs', 'Process', 'Checkpoints', 'Audit', 'Outputs')
HEADERS = {
    'Inputs': ['Source', 'File/Location', 'Section/Scope', 'Why'],
    'Checkpoints': ['After Step', 'Agent Presents', 'Human Decides'],
    'Audit': ['Check', 'Pass Condition'],
    'Outputs': ['Artifact', 'Location', 'Format'],
}
LINK = re.compile(r'\[[^\]]*\]\(([^)]+)\)')


def headings(text):
    """Headings outside code fences; examples are not live section owners."""
    result, fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith(('```', '~~~')):
            fence = not fence
        if not fence and re.match(r'^#{1,6} ', line):
            result.append(line.lstrip('#').strip())
    return result


def sections(text):
    result, name = {}, None
    for line in text.splitlines():
        if line.startswith('## '):
            name = line[3:]
            result[name] = []
        elif name:
            result[name].append(line)
    return result


def table(lines):
    rows = [line for line in lines if line.startswith('|')]
    return [[cell.strip() for cell in row.strip('|').split('|')] for row in rows]


def slug(heading):
    return re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-')


def contract_errors(root, routes):
    root = Path(root)
    errors = []
    if len((root / 'CONTEXT.md').read_text().splitlines()) > 80:
        errors.append('CONTEXT.md: exceeds 80 lines')
    for area in ('workflows', '_shared', '_system', 'setup'):
        for path in (root / area).rglob('*.md'):
            if '.venv' in path.parts or path.is_symlink():
                continue
            limit = 80 if path.name == 'CONTEXT.md' else 200
            if len(path.read_text().splitlines()) > limit:
                errors.append(f'{path.relative_to(root)}: exceeds {limit} lines')
    for name, route in routes.items():
        path = root / route['workflow']
        text = path.read_text()
        secs = sections(text)
        if (list(secs) != [s for s in ORDER if s in secs]
                or not {'Inputs', 'Process', 'Audit', 'Outputs'} <= set(secs)):
            errors.append(name + ': missing or unordered contract sections')
        for section, header in HEADERS.items():
            if section not in secs:
                continue
            rows = table(secs[section])
            if not rows or rows[0] != header or len(rows) < 3:
                errors.append(name + ': invalid ' + section + ' table')
            elif any(len(row) != len(header) or not all(row) for row in rows[2:]):
                errors.append(name + ': empty or malformed ' + section + ' row')
        steps = [int(m[1]) for line in secs.get('Process', [])
                 if (m := re.match(r'^(\d+)\. ', line))]
        if not steps or steps != list(range(1, len(steps) + 1)):
            errors.append(name + ': invalid Process numbering')
        for row in table(secs.get('Checkpoints', []))[2:]:
            if not row or not row[0].isdigit() or int(row[0]) not in steps:
                errors.append(name + ': checkpoint names a missing step')
        inputs = table(secs.get('Inputs', []))[2:]
        for row in inputs:
            if len(row) != 4:
                continue
            for link in LINK.findall(row[1]):
                if '://' in link or '<' in link:
                    continue
                file, _, anchor = link.partition('#')
                target = (path.parent / file).resolve()
                if root.resolve() not in target.parents or not target.is_file():
                    errors.append(name + ': missing or external input reference: ' + link)
                    continue
                names = headings(target.read_text())
                if anchor and anchor not in {slug(h) for h in names}:
                    errors.append(name + ': missing linked section: ' + link)
                for heading in re.findall(r'"([^"]+)"', row[2]):
                    if heading not in names:
                        errors.append(name + ': missing scoped section: ' + heading)
        for ref in (path.parent / 'references').glob('*.md'):
            if f'references/{ref.name}' not in '\n'.join(secs.get('Inputs', [])):
                errors.append(name + ': unrouted reference: ' + ref.name)
    return errors
