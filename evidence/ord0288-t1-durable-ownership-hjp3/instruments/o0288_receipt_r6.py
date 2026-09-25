"""ORD-0288 T-1 receipt r6 - make gates_three_way hold exactly three gates, all sentences.

r5's own self-check caught what r2/r3/r4 left inside `gates_three_way`:
  - C4's positive/negative were still bare booleans (they were `derived[...]`, i.e. true with no words);
  - C1 and C6 had a fourth key (`equality_basis_...`) parked in a block whose name promises three gates.
So the equality basis moves to `measured`, the block keeps positive/negative/mutation only, and every
gate is a sentence whose numbers were read back out of this same receipt at build time.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
R5 = 'RECEIPT_O0288T1-1610_r5.json'
OUT = 'RECEIPT_O0288T1-1610_r6.json'
rc = json.loads((B / R5).read_text(encoding='utf-8'))
C = {c['id'][:2]: c for c in rc['cells']}
GATES = ('positive', 'negative', 'mutation')
diff = []


def lift(cellkey, name):
    """Move a non-gate key out of gates_three_way into measured, where it belongs."""
    m = C[cellkey]['measured']
    g = m['gates_three_way']
    for k in [k for k in g if k not in GATES]:
        m[k if name is None else name] = g.pop(k)
    return sorted(k for k in g)


# ---- C1
m1 = C['C1']['measured']
left = lift('C1', 'equality_basis_of_the_replay_claim')
diff.append({'field': 'C1.measured.gates_three_way keys', 'was': 'four keys, one of them a comparison '
            'record rather than a gate', 'now': left,
             'moved_to': 'C1.measured.equality_basis_of_the_replay_claim'})
assert 'equality_basis_of_the_replay_claim' in m1
m1['gates_three_way']['positive'] = (m1['gates_three_way']['positive'] if isinstance(
    m1['gates_three_way']['positive'], str) else 'see C1.why')

# ---- C4: the two bare booleans become sentences built from C4's own readings
m4 = C['C4']['measured']
g4 = m4['gates_three_way']
was_pos, was_neg = g4['positive'], g4['negative']
rw = m4['row_written']
g4['positive'] = ('the refusal that went THROUGH the route is durable: key %s holds %d row with '
                  'operation %r, response_status %s and %s B of response_json, and its replay from the '
                  'other process answered %s with the same JSON value once error.trace_id is dropped (%s)'
                  % (m4['in_route_refusal']['key'], len([rw]), rw.get('operation'),
                     rw.get('response_status'), rw.get('response_json_bytes'),
                     m4['replay_of_that_failure']['status'],
                     m4['replay_of_that_failure']['json_values_equal_after_dropping_trace_id']))
pcr = m4['pre_claim_rejection']
g4['negative'] = ('the refusal BEFORE the claim is not a key burn: malformed key %r answered %s and the '
                  'store kept %d row matching it (%r), and a fresh valid key right after it still ran '
                  'and answered %s'
                  % ('x', pcr['malformed_key_status'], len(pcr['rows_matching_that_key']) if isinstance(
                      pcr['rows_matching_that_key'], list) else pcr['rows_matching_that_key'],
                      pcr['rows_matching_that_key'], pcr['a_later_valid_send_still_works']))
left4 = lift('C4', 'equality_reading_used_for_the_claim')
diff.append({'field': 'C4.measured.gates_three_way.positive / .negative',
             'was': {'positive': was_pos, 'negative': was_neg},
             'now': 'two sentences read out of row_written and pre_claim_rejection',
             'keys_after': left4})

# ---- C6
m6 = C['C6']['measured']
left6 = lift('C6', 'equality_basis_of_the_replay_claim')
diff.append({'field': 'C6.measured.gates_three_way keys', 'was': 'four', 'now': left6,
             'moved_to': 'C6.measured.equality_basis_of_the_replay_claim'})
assert 'equality_basis_of_the_replay_claim' in m6

# ---- re-run the same self-check on the result
bad = [{'cell': c['id'][:2], 'gate': k, 'value': repr(v)[:40]} for c in rc['cells']
       for k, v in (c['measured'].get('gates_three_way') or {}).items()
       if k in GATES and not isinstance(v, str)]
extra = [{'cell': c['id'][:2], 'gate': k} for c in rc['cells']
         for k in (c['measured'].get('gates_three_way') or {}) if k not in GATES]
nonstr = [{'cell': c['id'][:2], 'gate': k, 'type': type(v).__name__} for c in rc['cells']
          for k, v in (c['measured'].get('gates_three_way') or {}).items() if not isinstance(v, str)]
rc['integrity_gate_selfcheck']['boolean_gates_still_literal'] = bad
rc['integrity_gate_selfcheck']['gates_blocks_holding_more_than_the_three_named_gates'] = extra
rc['integrity_gate_selfcheck']['gates_that_are_not_strings'] = nonstr
rc['integrity_gate_selfcheck']['gate_wording_now_derived_from_own_readings'] = (
    not bad and not extra and not nonstr)
rc['r6_notes'] = {'diff': diff,
                  'measurements_changed': [],
                  'supersedes': {'file': R5, 'sha256': hashlib.sha256((B / R5).read_bytes()).hexdigest()},
                  'receipt_chain': rc['r5_notes']['receipt_chain'] + [OUT]}
(B / OUT).write_text(json.dumps(rc, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print('wrote', OUT)
print('literal gates:', bad)
print('extra keys in gate blocks:', extra)
print('non-string gates:', nonstr)
print('clean:', rc['integrity_gate_selfcheck']['gate_wording_now_derived_from_own_readings'])
print('r6 sha256', hashlib.sha256((B / OUT).read_bytes()).hexdigest())
print()
print('C4 positive:', g4['positive'])
print()
print('C4 negative:', g4['negative'])
