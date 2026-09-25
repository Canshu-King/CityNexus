"""ORD-0301 pass 3, stage 7: the boundary proof - the "I did not touch X" lines in the supplement are
readings too, so they are counted off disk instead of asserted.

A negative scan that finds nothing is blind, not clean, so every needle ships with a control that must HIT (the
pairing route has to appear in the arm files, the pairing header has to appear in the hop and the page), and
each hit is sorted into three roles before anything is concluded:

  actor     - a file that can actually do the thing (the rig that spawns and opens databases, the hop that
              carries requests, the browser reader, the binding probe) or an artefact one of them wrote;
  note      - prose in this batch's own builders and supplement, where naming a forbidden name is the point;
  scanner   - this file, which lists the needles it looks for.

Without that split my own docstring ("demo/reset is never called") reads as a demo/reset call, which is how a
scan like this usually gets dismissed - so the counts are reported per role rather than folded.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0301p3_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
REPO = pathlib.Path('D:/moodle/CityNexus')
SHEET = 'frontend/src/features/planning/PlanWithAiSheet.tsx'
ACTOR_NAMES = ('p3_rig.py', 'p3proxy.py', 'p3_arms.py', 'p3_cells.cjs', 'p3_setup.py')
NOTE_NAMES = ('p3_score.py', 'p3_receipt.py', 'p3_md.py', 'p3_publish.py', 'p3_boundary_check.py')
ACTORS = [SRC / n for n in ACTOR_NAMES] + [SRC / 'p3_cells.cjs']
ARTEFACTS = (sorted(BASE.glob('p3_arm_*.json')) + sorted(BASE.glob('p3_cell_*.json'))
             + sorted(BASE.glob('p3_rig_state_*.json')) + [BASE / 'p3_pair_log.jsonl'])
NOTES = [SRC / n for n in NOTE_NAMES if (SRC / n).exists()]
SCANNER = [SRC / 'p3_boundary.py']
DENIAL = ('never', 'no writes', 'not entered', 'forbidden', 'only', 'zero', '不', '禁止', '没有', '读写 0')


def blob_sha1(d):
    return hashlib.sha1(b'blob %d\0' % len(d) + d).hexdigest()


def role_of(f):
    if f in SCANNER:
        return 'scanner'
    if f in NOTES:
        return 'note'
    return 'actor'


def use_or_denial(line):
    """Inside the ACTOR role, a line with no denial word in it is treated as a use. The classifier ships with
    a control that must come out as a use, or the split is decoration."""
    low = line.lower()
    return 'named_in_denial' if any(d in low for d in DENIAL) else 'possible_use'


def scan(files, needle):
    hits = []
    for f in files:
        r = role_of(f)
        for i, line in enumerate(f.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            if needle.lower() in line.lower():
                hits.append({'file': f.name, 'line': i, 'role': r, 'reading': use_or_denial(line),
                             'head': line.strip()[:100]})
    return hits


NEEDLES = {
    'demo/reset': {'expect_uses': 0, 'note': 'the reset that wipes 52 tables incl. user journeys'},
    '_live.db': {'expect_uses': 0, 'note': 'the shared live database'},
    '_preview.db': {'expect_uses': 0, 'note': 'the shared preview database'},
    'git apply': {'expect_uses': 0, 'note': 'tree writes are forbidden; exports come from git archive'},
    '4782': {'expect_uses': 0, 'note': 'the phone-chain proxy port'},
    'DEEPSEEK_API_KEY': {'expect_uses': None, 'only_allowed_reading': '.pop(',
                         'note': 'must appear in actors only at the pop that removes it'},
    '4781': {'expect_uses': 1, 'note': 'the phone-chain face: the binding probe reads it, twice, GET only'},
    'agent/commands': {'expect_uses': None, 'control_kind': 'non_empty',
                       'note': 'CONTROL: the leg must be present in the artefacts'},
    'x-hjp3-pair': {'expect_uses': None, 'control_kind': 'non_empty',
                    'note': 'CONTROL: the hop must write it and the page must read it'},
}
ALL = ACTORS + ARTEFACTS + NOTES + SCANNER
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'roles': {'actor_files': [f.name for f in ACTORS], 'artefact_files': len(ARTEFACTS),
                 'note_files': [f.name for f in NOTES], 'scanner': [f.name for f in SCANNER]},
       'method': 'case-insensitive substring over every file this batch ran or wrote, then split by role',
       'needles': {}}
controls_hit = 0
for n, spec in NEEDLES.items():
    hits = scan(ALL, n)
    actor_art = [h for h in hits if h['role'] == 'actor']
    uses = [h for h in actor_art if h['reading'] == 'possible_use']
    rec = {'what_it_is': spec['note'], 'total_hits': len(hits),
           'in_actor_or_artefact': len(actor_art),
           'in_note_prose': len([h for h in hits if h['role'] == 'note']),
           'in_this_scanner': len([h for h in hits if h['role'] == 'scanner']),
           'uses_in_actor_or_artefact': [h['file'] + ':' + str(h['line']) for h in uses],
           'use_sites': uses[:6]}
    if spec.get('control_kind') == 'non_empty':
        rec['control'] = {'must_be_non_empty': True, 'satisfied': bool(actor_art)}
        controls_hit += bool(actor_art)
    elif 'only_allowed_reading' in spec:
        allowed = [h for h in uses if spec['only_allowed_reading'] in h['head']]
        rec['control'] = {'only_allowed_reading': spec['only_allowed_reading'],
                          'satisfied': len(uses) > 0 and len(allowed) == len(uses),
                          'found_at': [h['file'] + ':' + str(h['line']) for h in uses],
                          'not_allowed': [h['file'] + ':' + str(h['line']) for h in uses
                                          if h not in allowed]}
        controls_hit += rec['control']['satisfied']
    elif spec['expect_uses'] == 0:
        rec['control'] = {'must_be_empty': True, 'satisfied': uses == [],
                          'anything_found': [h['file'] + ':' + str(h['line']) for h in uses]}
    else:
        # the phone-chain needle: its uses are the declared read-only probe, so the control is "exactly the
        # binding instrument, and nothing else"
        names = sorted({h['file'] for h in uses})
        rec['control'] = {'allowed_files': ['p3_setup.py'], 'satisfied': names == ['p3_setup.py'],
                          'found_in': names}
        controls_hit += names == ['p3_setup.py']
    out['needles'][n] = rec
CTRL = [h for h in scan(ACTORS, 'x-hjp3-pair') if h['reading'] == 'possible_use']
classifier_control = bool(CTRL)
FORBIDDEN = tuple(k for k, sp in NEEDLES.items() if sp['expect_uses'] == 0)
pops = [h for h in scan(ACTORS, 'DEEPSEEK_API_KEY') if '.pop(' in h['head']]
assigns = [h for h in scan(ACTORS, 'DEEPSEEK_API_KEY') if ('environ[' in h['head'] or 'getenv' in h['head'])
           and '.pop(' not in h['head']]
bind = json.loads((BASE / 'served_generation_bind_c2.json').read_text(encoding='utf-8'))
arms = [json.loads(f.read_text(encoding='utf-8')) for f in sorted(BASE.glob('p3_arm_*.json'))]
EXP = {}
for gen, tip in (('dep', '7856e03f6238da3000976eb6e690a448dfa39b9a'),
                 ('old', 'dc964086c9d412573ac19d70b24b30e6c3ee6168')):
    rev = subprocess.run(['git', '-C', str(REPO), 'rev-parse', '%s:%s' % (tip, SHEET)],
                         capture_output=True, text=True, encoding='utf-8', errors='replace')
    local = blob_sha1((BASE / ('snap_%s' % tip[:8]) / SHEET).read_bytes())
    EXP[gen] = {'tip': tip, 'commit_blob_from_git': rev.stdout.strip(), 'export_blob_recomputed': local,
                'equal': bool(rev.stdout.strip()) and rev.stdout.strip() == local}
out['credentials'] = {'pop_sites_in_actors': [p['file'] + ':' + str(p['line']) for p in pops],
                      'assignment_or_read_sites': [a['file'] + ':' + str(a['line']) for a in assigns],
                      'authorization_header_in_any_arm_file': any(
                          'authorization' in json.dumps(a).lower() for a in arms)}
out['phone_chain'] = {'endpoint': '127.0.0.1:4781', 'requests_made': bind['requests_made'],
                      'methods': bind['methods'], 'writes': bind['writes'],
                      'credentials_sent': bind['credentials_sent'],
                      'arm_artefacts_naming_that_port': len(
                          [h for h in scan(ARTEFACTS, '4781') if h['role'] == 'actor']),
                      'how_counted': 'requests_made/methods/writes are fields the binding instrument wrote '
                                     'about its own run; the arm artefacts are counted on the left'}
out['product_bytes'] = {
    'sheet_under_test': SHEET, 'per_generation': EXP,
    'how_to_recheck': 'git -C D:/moodle/CityNexus rev-parse <tip>:<sheet> against a re-hash of that file '
                      'inside my export - equal means the export is the commit, not an edit of it'}
out['verdict'] = {
    'controls_found_what_they_must': controls_hit == 3,
    'the_use_versus_denial_classifier_has_a_positive_control': classifier_control,
    'no_forbidden_name_appears_as_an_action': all(
        out['needles'][n]['uses_in_actor_or_artefact'] == [] for n in FORBIDDEN),
    'credential_appears_in_actors_only_where_it_is_removed': bool(pops) and not assigns,
    'the_phone_chain_saw_only_reads': bind['writes'] == 0 and bind['methods'] == ['GET', 'GET'],
    'both_exports_are_their_own_commits': all(e['equal'] for e in EXP.values()),
    'no_arm_sent_any_authorization_header': not out['credentials']['authorization_header_in_any_arm_file']}
out['verdict']['ALL_HOLD'] = all(out['verdict'].values())
(BASE / 'p3_boundary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8',
                                       newline='\n')
print(json.dumps(out['verdict'], ensure_ascii=False))
for n, v in out['needles'].items():
    print('  %-18s total=%-4d actor/artefact=%-4d note=%-3d scanner=%-3d uses=%d %s'
          % (n, v['total_hits'], v['in_actor_or_artefact'], v['in_note_prose'], v['in_this_scanner'],
             len(v['uses_in_actor_or_artefact']), v['uses_in_actor_or_artefact'][:3]))
