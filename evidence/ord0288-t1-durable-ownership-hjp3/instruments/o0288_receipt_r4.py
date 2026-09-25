"""ORD-0288 T-1 receipt r4 - the last four things r3 still got wrong about itself.

r3 fixed the sentences in C1/C2/C3 but left:
 1. C5's private_copy digests at 16 hex (r2 put the full values in a notes block instead of fixing the
    field the mutant cell actually carries) - EVIDENCE_INTEGRITY_GATE_V1 says the coordinate itself
    goes out full length, so it is rewritten here from the files on disk.
 2. C6 kept r1's `replay_status` next to r2's `replay_from_the_fresh_process`: two names, one reading.
 3. C3's `negative` gate said "after this arm the table holds 2 rows for 2 keys" - I pointed at
    `idempotency_rows_all_keys` for BOTH numbers and never read the key list that is sitting in the
    same durable read. And the arm's own extra flag `exactly_one_row_for_the_key` reads False while the
    store visibly holds one row for that key: the arm passed a bare key into a `WHERE key LIKE ?`
    pattern, so it matched nothing. Disclosed, not smoothed over.
 4. r3's `cells_untouched_by_r3` was built with the wrong filter and named C4/C6/C7 as untouched.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
R3 = 'RECEIPT_O0288T1-1610_r3.json'
OUT = 'RECEIPT_O0288T1-1610_r4.json'
rc = json.loads((B / R3).read_text(encoding='utf-8'))
C = {c['id'][:2]: c for c in rc['cells']}


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


diff = []

# ---------------------------------------------------------------- 1. C5 digests, full length
pc = C['C5']['measured']['private_copy']
tree = pathlib.Path(pc['dir'])
main_py = tree / 'app' / 'main.py'
pristine = B / 'backend' / 'app' / 'main.py'
diff.append({'field': 'C5.measured.private_copy.main_py_sha256 / pristine_main_py_sha256',
             'was': {'main_py_sha256': pc['main_py_sha256'],
                     'pristine_main_py_sha256': pc['pristine_main_py_sha256']},
             'now_is_full_length': True,
             'derived_from': 'sha256 recomputed from %s and %s at build time' % (main_py, pristine)})
pc['main_py_sha256_was_in_r1'] = pc['main_py_sha256']
pc['pristine_main_py_sha256_was_in_r1'] = pc['pristine_main_py_sha256']
pc['main_py_sha256'] = sha(main_py)
pc['pristine_main_py_sha256'] = sha(pristine)
pc['digest_length_hex'] = len(pc['main_py_sha256'])
pc['r1_short_values_are_prefixes_of_these'] = (pc['main_py_sha256'].startswith(
    pc['main_py_sha256_was_in_r1']) and pc['pristine_main_py_sha256'].startswith(
    pc['pristine_main_py_sha256_was_in_r1']))
for m in rc.get('r2_notes', {}).get('full_length_digests', {}).items():
    pass  # notes block stays as r2 wrote it; the field above is now the authoritative one

# ---------------------------------------------------------------- 2. C6: one name for one reading
c6 = C['C6']['measured']
diff.append({'field': 'C6.measured.replay_status vs replay_from_the_fresh_process',
             'was': {'replay_status': c6.get('replay_status'),
                     'replay_from_the_fresh_process': c6.get('replay_from_the_fresh_process')},
             'now': 'the r1 duplicate key is dropped; the reading survives once, under the r2 name that '
                    'says which process answered',
             'both_were_equal': c6.get('replay_status') == c6.get('replay_from_the_fresh_process')})
c6.pop('replay_status', None)
g6 = c6['gates_three_way']
g6['positive'] = ('key %s answered %s with %s B from pid %s, a process started after the owner (pid %s) '
                  'was killed, and idempotency_keys still holds %d row for it'
                  % (C['C1']['measured']['key'], c6['replay_from_the_fresh_process'], c6['replay_bytes'],
                     rc['r2_notes']['restart_predicate_inputs']['restarted_process_pid'],
                     c6['killed_pid'], c6['rows_holding_this_key_after_the_restart']))
g6['negative'] = ('C5: a claim that was won but never filled also survives the restart - it survives as '
                  'response_status NULL and answers %s to everyone, so durability of the row is not '
                  'recoverability of the answer'
                  % C['C5']['measured']['replay_after_a_fresh_process']['status'])
g6['mutation'] = ('C2: deleting the signature comparison in _replay_committed_accept makes this stored '
                  'row answer a DIFFERENT request (%s instead of %s) - the row C6 replays is the same '
                  'object the refusal guard reads'
                  % (C['C2']['measured']['mutant_that_removes_the_guard'][
                      'different_body_status_after_removing_it'],
                     C['C2']['measured']['status_when_pristine']))
g6['equality_basis_of_this_cells_own_claim'] = c6['three_ways_of_saying_the_same_answer']

# ---------------------------------------------------------------- 3. C3: read the key list, own the bad flag
c3 = C['C3']['measured']
arm = json.loads(sorted(B.glob('cell_t1a_same_key_concurrent_two_processes_*.json'))[-1].read_text(
    encoding='utf-8'))
listed = [r['key'] for r in (arm.get('durable_read_after') or {}).get('idempotency_keys', [])]
mine = [k for k in listed if k.endswith(c3['key'])]
c3['gates_three_way']['negative'] = (
    'the same durable read that holds 1 row for key %s lists %d rows for %d distinct keys (%s), so a '
    'second key claimed in the same window does get its own row - this arm only proves one owner per key'
    % (c3['key'], len(listed), len(set(listed)), ', '.join(listed)))
c3['arm_flag_discrepancy'] = {
    'the_arms_own_extra_flag': arm['extra']['exactly_one_row_for_the_key'],
    'what_the_store_actually_holds_for_this_key': len(mine),
    'this_receipt_uses': 'rows filtered out of the durable read by key suffix, recomputed here',
    'why_they_differ': 'the arm ran `SELECT ... FROM idempotency_keys WHERE key LIKE ?` and passed the '
                       'bare key %r, but stored keys are prefixed with the operation (%r), so that query '
                       'matched 0 rows and `sum(...) == 1` came out False. The flag is an artefact of my '
                       'own query, not a second reading of the store - the row is there.' % (
                           c3['key'], 'plans.generate:' + str(c3['key'])),
    'verified_by': 'the durable read in the same cell lists %d row(s) whose key ends with %s' % (
        len(mine), c3['key'])}
diff.append({'field': 'C3.gates_three_way.negative + new arm_flag_discrepancy',
             'was': '"a different key claimed in the same second adds its own row - see the 2 rows for '
                    'all keys after this arm" (both numbers came from one count field)',
             'now': c3['gates_three_way']['negative'],
             'derived_from': 'durable_read_after.idempotency_keys of the concurrent arm cell'})

# ---------------------------------------------------------------- 4. r3's wrong bookkeeping field
rc['r3_notes']['cells_untouched_by_r3'] = [k for k in sorted(C) if k in ('C5',)]
rc['r3_notes']['this_field_was_wrong_in_r3'] = (
    'r3 printed %s, which named C4/C6/C7 as untouched even though r2 had rewritten them - the filter '
    'compared against the wrong tuple' % (rc.get('r3_notes', {}).get('_was') or 'a wrong list'))
for k in ('C4', 'C6', 'C7'):
    pass

# ---------------------------------------------------------------- limits
rc['instrument_limits_disclosed'] = rc['instrument_limits_disclosed'] + [
    'every "same answer" claim in this receipt is stated at the JSON-value level after dropping '
    'error.trace_id; the raw bytes are NOT equal across any replay, because error.details re-serialises '
    'with a different key insertion order (recomputed per cell in r2_notes)',
    'one flag inside the concurrent arm\'s own `extra` is wrong (exactly_one_row_for_the_key = False); '
    'C3.arm_flag_discrepancy names the query that produced it and the durable read that refutes it',
    'no arm in this batch reached a 200, so what is proven durable is ownership of a refusal receipt; '
    'replay of a stored 200-with-plans payload is NOT measured here']

rc['r4_notes'] = {'diff': diff,
                  'supersedes': {'file': R3, 'sha256': sha(B / R3)},
                  'receipt_chain': ['RECEIPT_O0288T1-1610.json', 'RECEIPT_O0288T1-1610_r2.json',
                                    'RECEIPT_O0288T1-1610_r3.json', OUT]}
(B / OUT).write_text(json.dumps(rc, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
txt = (B / OUT).read_text(encoding='utf-8')
print('wrote', OUT)
print('r3 sha256', rc['r4_notes']['supersedes']['sha256'])
print('r4 sha256', sha(B / OUT))
print('C5 digests full:', len(pc['main_py_sha256']), len(pc['pristine_main_py_sha256']),
      '| prefixes hold:', pc['r1_short_values_are_prefixes_of_these'])
print('C3 negative:', c3['gates_three_way']['negative'][:180])
print('C3 discrepancy flag:', c3['arm_flag_discrepancy']['the_arms_own_extra_flag'],
      '-> rows actually listed:', c3['arm_flag_discrepancy']['what_the_store_actually_holds_for_this_key'])
print('paren artifacts left - (True):', txt.count('(True)'), '(False):', txt.count('(False)'))
print('16-hex-looking coordinates left:', len(__import__('re').findall(r'"[0-9a-f]{16}"', txt)))
