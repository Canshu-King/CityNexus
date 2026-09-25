"""ORD-0288 T-1 final receipt for shipping: the working lineage r1..r7 folded into one named file.

Why a new name instead of editing r7: the Q38 r2 run on r7 came back
Q38_GATE_SOFT_FINDINGS / 1 soft (WHY_NOT_FROM_OWN_READINGS on C7). Cause: C7's `why` quoted the tip as
`dc964086c9d4`, a 12-character prefix, while its own reading stores the 40-character tip - so the
sentence carried no token the尺 could match, and EVIDENCE_INTEGRITY_GATE_V1 forbids a short coordinate
outside a field that says it is a previous value. Fixed here by quoting the tip in full and by naming
the two readings C7 actually owns.

The r1..r7 files stay on disk untouched; this file records each one's sha256 so the lineage is auditable
without publishing seven receipts.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
SRC = 'RECEIPT_O0288T1-1610_r7.json'
OUT = 'RECEIPT_O0288T1-1730.json'
LINEAGE = ['RECEIPT_O0288T1-1610.json', 'RECEIPT_O0288T1-1610_r2.json', 'RECEIPT_O0288T1-1610_r3.json',
           'RECEIPT_O0288T1-1610_r4.json', 'RECEIPT_O0288T1-1610_r5.json',
           'RECEIPT_O0288T1-1610_r6.json', SRC]
rc = json.loads((B / SRC).read_text(encoding='utf-8'))
C = {c['id'][:2]: c for c in rc['cells']}
GATES = ('positive', 'negative', 'mutation')

tip = rc['measured_on']
assert len(tip) == 40 and all(ch in '0123456789abcdef' for ch in tip), 'tip is not a 40-hex coordinate'
c7 = C['C7']['measured']
C['C7']['why'] = (
    "this cell owns three readings and names only what they support: (1) "
    "agent_commands_route_has_no_idempotency_parameter = %s, read from %s of the exported tree at %s, so "
    "the no-key write leg ORD-0288 also asked about has no key row to inspect at all; (2) %s; (3) %s - "
    "every keyed send here answered %s or %s and plan_versions stayed %s in all %d durable reads, so a "
    "replay of a stored 200-with-plans receipt is NOT measured in this batch. That is why this cell "
    "reports scope limits instead of a green."
    % (c7['agent_commands_route_has_no_idempotency_parameter'], 'backend/app/main.py', tip,
       c7['mission_bound_leg_not_exercised'],
       json.dumps({'statuses': sorted(c7['only_refusal_receipts_were_ever_replayed']['plan_versions_rows']),
                   'plan_versions': list(c7['only_refusal_receipts_were_ever_replayed'][
                       'plan_versions_rows'].values())}, ensure_ascii=False),
       422, 409, 0, len(c7['only_refusal_receipts_were_ever_replayed']['plan_versions_rows'])))

# re-run every self-check against the shipped file
bad = [{'cell': c['id'][:2], 'gate': k} for c in rc['cells']
       for k, v in (c['measured'].get('gates_three_way') or {}).items() if not isinstance(v, str)]
extra = [{'cell': c['id'][:2], 'gate': k} for c in rc['cells']
         for k in (c['measured'].get('gates_three_way') or {}) if k not in GATES]
import re
pointers = [{'from': c['id'][:2] + '.' + k, 'names': 'C' + m.group(1),
             'target_exists': ('C' + m.group(1)) in C}
            for c in rc['cells'] for k, v in (c['measured'].get('gates_three_way') or {}).items()
            for m in re.finditer(r'\bC([1-7])\b', v)]
short = [{'path': p, 'value': s} for p, s in (
    (pa, v) for c in rc['cells'] for pa, v in [(c['id'][:2] + '.why', c['why'])]
    if re.search(r'(?<![0-9a-f])[0-9a-f]{7,39}(?![0-9a-f])', v))]
rc['integrity_gate_selfcheck'].update({
    'boolean_gates_still_literal': bad,
    'gates_blocks_holding_more_than_the_three_named_gates': extra,
    'cross_cell_pointers': pointers,
    'cross_cell_pointers_all_resolving': all(p['target_exists'] for p in pointers),
    'gate_wording_now_derived_from_own_readings': (not bad) and (not extra),
    'short_hex_in_cell_why_fields': short,
})
rc['lineage'] = {'shipped_file': OUT,
                 'working_files_left_untouched_on_disk': [
                     {'file': f, 'sha256': hashlib.sha256((B / f).read_bytes()).hexdigest(),
                      'bytes': (B / f).stat().st_size} for f in LINEAGE],
                 'why_seven_revisions_exist': 'each revision fixed something the previous one asserted '
                                              'without earning it; the diffs are in r1_diff, r3_notes, '
                                              'r4_notes, r6 is in its own diff block, r7 in r7_notes',
                 'no_measurement_changed_in_any_revision': 'arms ran once, at 16:23-16:32; every revision '
                                                            'after that re-read the same cell files'}
rc['shipped_from'] = {'file': SRC, 'sha256': hashlib.sha256((B / SRC).read_bytes()).hexdigest()}
rc['receipt_sha256_self_reference'] = 'this field cannot hold the digest of the file it appears in; the ' \
                                      'authoritative digest is read back from the branch after the push'
(B / OUT).write_text(json.dumps(rc, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print('wrote', OUT, (B / OUT).stat().st_size, 'B')
print('non-string gates:', bad, '| extra:', extra, '| pointers ok:',
      rc['integrity_gate_selfcheck']['cross_cell_pointers_all_resolving'])
print('short hex in why:', json.dumps(short, ensure_ascii=False)[:200])
print('C7 why:', C['C7']['why'][:400])
