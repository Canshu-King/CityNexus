"""ORD-0288 T-1 receipt r7 - final copy: one wrong cross-reference, found by reading my own sentences.

C3's `mutation` gate pointed at "(C4)" for the crash arm. The crash arm is C5 - C4 is the error path that
DOES record a status, so the pointer named the opposite of what it meant. Everything else in r6 stands;
no measurement is touched here, and the Q38 ruler run against this file is kept in its own artefact
(q38_ruler_O0288T1_r7.txt) rather than embedded, so the receipt never quotes a verdict about itself.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
R6 = 'RECEIPT_O0288T1-1610_r6.json'
OUT = 'RECEIPT_O0288T1-1610_r7.json'
rc = json.loads((B / R6).read_text(encoding='utf-8'))
C = {c['id'][:2]: c for c in rc['cells']}
GATES = ('positive', 'negative', 'mutation')

crash_id = C['C5']['id']
c3 = C['C3']['measured']['gates_three_way']
was = c3['mutation']
c3['mutation'] = ('the arm that DOES win a claim and never land an answer is the crash arm (%s): it shows '
                  'the one failure mode this concurrency arm cannot show, because here the winner always '
                  'filled its row - %s'
                  % (crash_id.split('_', 1)[0], json.dumps(
                      {'first_send_status': C['C5']['measured']['first_send_status'],
                       'row_response_status_after_the_crash':
                           C['C5']['measured']['row_response_status_after_the_crash'],
                       'every_later_replay': C['C5']['measured']['replay_same_process']['status']},
                      ensure_ascii=False)))

bad = [{'cell': c['id'][:2], 'gate': k} for c in rc['cells']
       for k, v in (c['measured'].get('gates_three_way') or {}).items() if not isinstance(v, str)]
extra = [{'cell': c['id'][:2], 'gate': k} for c in rc['cells']
         for k in (c['measured'].get('gates_three_way') or {}) if k not in GATES]
rc['integrity_gate_selfcheck']['boolean_gates_still_literal'] = bad
rc['integrity_gate_selfcheck']['gates_blocks_holding_more_than_the_three_named_gates'] = extra

# every "see C<n>" / "C<n>:" pointer inside a cell must name a cell that exists
pointers = []
for c in rc['cells']:
    for k, v in (c['measured'].get('gates_three_way') or {}).items():
        import re
        for m in re.finditer(r'\bC([1-7])\b', v):
            target = 'C' + m.group(1)
            pointers.append({'from': c['id'][:2] + '.' + k, 'names': target,
                             'target_exists': target in C,
                             'target_id': (C[target]['id'] if target in C else None),
                             'context': v[max(0, m.start() - 46):m.start() + 12]})
rc['integrity_gate_selfcheck']['cross_cell_pointers'] = pointers
rc['integrity_gate_selfcheck']['cross_cell_pointers_all_resolving'] = all(p['target_exists'] for p in pointers)
rc['integrity_gate_selfcheck']['gate_wording_now_derived_from_own_readings'] = (not bad) and (not extra)

rc['r7_notes'] = {
    'diff': [{'field': 'C3.measured.gates_three_way.mutation', 'was': was, 'now': c3['mutation'],
              'why': 'it pointed at C4 (the error path that DOES record a status) when the crash arm it '
                     'describes is C5 - the sentence named the opposite of its own meaning'}],
    'measurements_changed': [],
    'supersedes': {'file': R6, 'sha256': hashlib.sha256((B / R6).read_bytes()).hexdigest()},
    'receipt_chain': rc['r6_notes']['receipt_chain'] + [OUT],
    'ruler': 'the Q38 r2 run against this exact file is published beside it as q38_ruler_O0288T1_r7.txt; '
             'this receipt deliberately does not quote its own verdict'}
(B / OUT).write_text(json.dumps(rc, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print('wrote', OUT)
print('non-string gates:', bad, '| extra keys:', extra)
print('pointers:', json.dumps([{'from': p['from'], 'names': p['names'], 'ok': p['target_exists']}
                              for p in pointers], ensure_ascii=False))
print('all resolving:', rc['integrity_gate_selfcheck']['cross_cell_pointers_all_resolving'])
print('r7 sha256', hashlib.sha256((B / OUT).read_bytes()).hexdigest())
print('C3 mutation:', c3['mutation'][:220])
