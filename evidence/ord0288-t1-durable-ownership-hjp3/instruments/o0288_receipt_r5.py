"""ORD-0288 T-1 receipt r5 - the shipping copy.

Two things r4 still owed, both about itself:
 1. r4 said "r3 printed a wrong list" without quoting it. The real r3 value is read back off disk here.
 2. EVIDENCE_INTEGRITY_GATE_V1 allows a short hex string only as explicitly-labelled display, so the
    leftover 16-hex values are inventoried mechanically and each one's key path is checked for that.

Nothing about a measurement changes in this file; if it did, this batch would need new arms, not a new
receipt name.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
R4 = 'RECEIPT_O0288T1-1610_r4.json'
R3 = 'RECEIPT_O0288T1-1610_r3.json'
OUT = 'RECEIPT_O0288T1-1610_r5.json'
rc = json.loads((B / R4).read_text(encoding='utf-8'))
r3 = json.loads((B / R3).read_text(encoding='utf-8'))


def walk(o, p=''):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, p + '/' + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, p + '[%d]' % i)
    elif isinstance(o, str):
        yield p, o


# ---- 1. quote what r3 really printed
rc['r3_notes']['this_field_was_wrong_in_r3'] = (
    'r3 printed cells_untouched_by_r3 = %s, which named C4/C6/C7 as untouched even though r2 had '
    'rewritten their measured blocks and their `why` - the filter compared cell ids against the wrong '
    'tuple. r4 corrected it to %s (only C5 was untouched by r3).'
    % (json.dumps(r3['r3_notes']['cells_untouched_by_r3'], ensure_ascii=False),
       json.dumps(rc['r3_notes']['cells_untouched_by_r3'], ensure_ascii=False)))

# ---- 2. inventory every short hex string and prove each is labelled history
C5 = next(c for c in rc['cells'] if c['id'].startswith('C5'))
short = [(p, s) for p, s in walk(rc) if re.fullmatch(r'[0-9a-f]{7,39}', s)]
unlabelled = [(p, s) for p, s in short if 'was' not in p.lower()]
rc['integrity_gate_selfcheck'] = {
    'short_hex_strings_in_this_receipt': [{'path': p, 'value': s} for p, s in short],
    'count': len(short),
    'every_one_of_them_sits_under_a_key_path_naming_it_as_a_previous_value': not unlabelled,
    'paths_that_would_break_the_rule': [p for p, s in unlabelled],
    'authoritative_full_length_coordinates': {
        'measured_on_tip': rc['measured_on'],
        'frozen_tip': rc['frozen_tip'],
        'pristine_backend_app_main_py_sha256': C5['measured']['private_copy'][
            'pristine_main_py_sha256'],
        'crash_mutant_app_main_py_sha256': C5['measured']['private_copy']['main_py_sha256'],
        'receipt_r4_sha256_this_one_supersedes': hashlib.sha256((B / R4).read_bytes()).hexdigest(),
        'receipt_r3_sha256': hashlib.sha256((B / R3).read_bytes()).hexdigest()},
    'rule': 'EVIDENCE_INTEGRITY_GATE_V1 - coordinates go out full length; a short prefix is allowed only '
            'where the field itself says it is an earlier value',
    'boolean_gates_still_literal': [
        {'cell': c['id'][:2], 'gate': k} for c in rc['cells']
        for k, v in (c['measured'].get('gates_three_way') or {}).items() if not isinstance(v, str)]}

# ---- the shipped chain
rc['r5_notes'] = {'diff': [
    {'field': 'r3_notes.this_field_was_wrong_in_r3', 'was': 'asserted r3 was wrong without quoting it',
     'now': rc['r3_notes']['this_field_was_wrong_in_r3'], 'derived_from': R3 + ' read back off disk'},
    {'field': 'integrity_gate_selfcheck', 'was': 'absent',
     'now': '%d short hex strings inventoried, every one under a path that names it as a previous value: %s'
            % (rc['integrity_gate_selfcheck']['count'],
               rc['integrity_gate_selfcheck'][
                   'every_one_of_them_sits_under_a_key_path_naming_it_as_a_previous_value']),
     'derived_from': 'walked this receipt object at build time'}],
    'no_measurement_changed_in_r5': True,
    'supersedes': {'file': R4, 'sha256': hashlib.sha256((B / R4).read_bytes()).hexdigest()},
    'receipt_chain': ['RECEIPT_O0288T1-1610.json', 'RECEIPT_O0288T1-1610_r2.json',
                      'RECEIPT_O0288T1-1610_r3.json', R4, OUT]}
(B / OUT).write_text(json.dumps(rc, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print('wrote', OUT)
print('short hex:', rc['integrity_gate_selfcheck']['count'],
      '| all labelled:', rc['integrity_gate_selfcheck'][
          'every_one_of_them_sits_under_a_key_path_naming_it_as_a_previous_value'],
      '| offenders:', rc['integrity_gate_selfcheck']['paths_that_would_break_the_rule'])
print('literal (non-sentence) gates left:', rc['integrity_gate_selfcheck']['boolean_gates_still_literal'])
print('r5 sha256', hashlib.sha256((B / OUT).read_bytes()).hexdigest())
print('derived map:', json.dumps(rc['derived'], ensure_ascii=False))
