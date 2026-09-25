"""ORD-0291: put every write leg in frontend/src on its real channel, resolved PER FILE.

Why the care: `request` and `requestJson` are defined several times over (one helper per API module), so a
name-based lookup over-claims.  Here a site's helper is resolved inside the site's own file; if the file has
no such definition, its `import ... from '...'` lines are followed one hop and the definition is read there.
Anything still unresolved is named, not guessed.

Channels:
  RAW_FETCH            - the leg calls fetch( itself and never sees the deadline wrapper
  WRAPPER              - it reaches fetchWithReadDeadline, where readDeadline.ts:43-45 short-circuits writes
  OTHER                - reaches a fetch through some other helper (named per row)
  UNRESOLVED           - definition not found in one hop
"""
from __future__ import annotations

import json
import pathlib
import re

TREE = pathlib.Path('D:/moodle/_qoder_wt_45b0a5e')
SRC = TREE / 'frontend' / 'src'
OUT = pathlib.Path('D:/moodle/_hjp3_0291_0925/write_channels.json')

LIT = re.compile(r'method:\s*[`"\'](POST|PUT|PATCH|DELETE)[`"\']')
CALL = re.compile(r'\b([A-Za-z_$][\w$]*)\s*(?:<[^<>*]*>)?\s*\(')
SKIP = {'if', 'for', 'while', 'switch', 'return', 'await', 'catch', 'then', 'void', 'new', 'JSON',
        'String', 'Number', 'Array', 'Object', 'Promise', 'useMutation', 'useQuery'}
IMPORT = re.compile(r"import\s+(?:type\s+)?\{([^}]*)\}\s*from\s*['\"]([^'\"]+)['\"]")


REQUESTISH = re.compile(r'^(fetch|.*[Rr]equest.*|.*[Pp]ost.*|.*[Pp]ut.*|.*[Pp]atch.*|.*[Dd]elete.*)$')


def first_call(line):
    """Prefer a request-shaped call name; an unrelated call on the same line (JSON.stringify(...) etc.) is
    the object being built, not the channel the leg travels on."""
    names = [cm.group(1) for cm in CALL.finditer(line) if cm.group(1) not in SKIP]
    for n in names:
        if REQUESTISH.match(n):
            return n
    return names[0] if names else None


def enclosing(lines, i):
    n = first_call(lines[i])
    if n:
        return n
    for j in range(i - 1, max(-1, i - 13), -1):
        n = first_call(lines[j])
        if n:
            return n
    return None


def definition(name, path):
    """The body of `name` as defined in `path`, or None."""
    if not path.exists():
        return None
    txt = path.read_text(encoding='utf-8', errors='replace')
    m = (re.search(r'(?:async\s+)?function\s+%s\s*(?:<[^<>*]*>)?\s*\(' % re.escape(name), txt)
         or re.search(r'(?:const|export const)\s+%s\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::[^=]+)?=>' % re.escape(name), txt))
    if not m:
        return None
    return txt[m.start():m.start() + 1800]


def resolve(name, site_path):
    body = definition(name, site_path)
    if body:
        return body, str(site_path.relative_to(TREE)).replace('\\', '/') + ' (same file)'
    st = site_path.read_text(encoding='utf-8', errors='replace')
    for m in IMPORT.finditer(st):
        names = [x.strip().split(' as ')[-1] for x in m.group(1).split(',') if x.strip()]
        if name not in names:
            continue
        spec = m.group(2)
        if spec.startswith('@/'):
            target = SRC / spec[2:]
        elif spec.startswith('.'):
            target = (site_path.parent / spec).resolve()
        else:
            continue
        for cand in (target.with_suffix('.ts'), target.with_suffix('.tsx'), target / 'index.ts'):
            body = definition(name, cand)
            if body:
                return body, str(cand.relative_to(TREE)).replace('\\', '/') + ' (imported)'
    return None, None


rows = []
for p in sorted(SRC.rglob('*.ts*')):
    rel = str(p.relative_to(TREE)).replace('\\', '/')
    lines = p.read_text(encoding='utf-8', errors='replace').splitlines()
    for i, line in enumerate(lines):
        m = LIT.search(line)
        if not m:
            continue
        call = enclosing(lines, i)
        row = {'file': rel, 'line': i + 1, 'method': m.group(1), 'enclosing_call': call}
        if call == 'fetch':
            row['channel'] = 'RAW_FETCH'
        elif not call:
            row['channel'] = 'UNRESOLVED'
        else:
            body, where = resolve(call, p)
            if body is None:
                row['channel'] = 'UNRESOLVED'
                row['helper'] = '%s (%s)' % (call, where or 'definition not found in one hop')
            else:
                row['helper'] = '%s @ %s' % (call, where)
                if 'fetchWithReadDeadline' in body:
                    row['channel'] = 'WRAPPER'
                elif re.search(r'[^t]\bfetch\(', body):
                    row['channel'] = 'OTHER'
                else:
                    row['channel'] = 'OTHER'
        rows.append(row)

tally = {}
for r in rows:
    tally[r['channel']] = tally.get(r['channel'], 0) + 1
report = {
    'tree': str(TREE),
    'search_space': 'every *.ts / *.tsx under frontend/src; rows matched by method:"POST|PUT|PATCH|DELETE"',
    'write_method_literals': len(rows), 'channel_tally': tally,
    'per_site': rows,
    'coverage': 'NOT EXHAUSTIVE - the enclosing call is the first call-shaped token on the literal line else on '
                'the 12 lines above; a helper is followed exactly one import hop; UNRESOLVED rows are listed '
                'rather than assigned to a channel',
}
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps({'write_method_literals': len(rows), 'channel_tally': tally}, ensure_ascii=False, indent=1))
