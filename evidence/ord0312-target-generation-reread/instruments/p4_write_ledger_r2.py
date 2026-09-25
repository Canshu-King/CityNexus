"""Correction + write ledger for the re-issue note (issuecomment-5837162504).

Two things are fixed here and nothing else is re-stated:
  * the count in that note is wrong: `17` came from adding the per-phase logs up while the first log was in the
    list twice (once as a named variable, once through the glob). Counted by DISTINCT remote name it is 12, and
    the whole ORD-0312/0316/T-1x span including the earlier batch is 30 paths.
  * the claim `旧名一件未覆盖` is a claim about WRITES, so it is counted with the branch's own commit list per
    path rather than asserted. The path the gate refused is included: it must show ZERO commits, which is what
    "nothing uploaded" looks like from the outside.
"""
from __future__ import annotations

import importlib.util as iu
import json
import pathlib
import time
import urllib.parse
import urllib.request

OUT = pathlib.Path('D:/moodle/_hjp3_0312p4_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)
CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
assert len(CLOSING) == 83

REFUSED = 'evidence/ord0300-c2-pairing-hjp3/arm_old_old_lock_C2-214340_gate_refused_original.json'
TWICE = ['evidence/ord0300-hjp3-write-cells/RECEIPT_O0300-2610.json',
         'evidence/ord0300-c2-pairing-hjp3/evidence_manifest_full40_c2.json',
         'evidence/ord0288-t1-durable-ownership-hjp3/evidence_manifest_full40_o0288_r2.json']
REISSUE = ['ship_result_p4_r2.json', 'ship_result_p4_r3.json', 'ship_result_p4_r4.json']


def commits_touching(path):
    q = urllib.parse.quote(path, safe='')
    j = pub.api('/commits?sha=' + pub.BRANCH + '&path=' + q + '&per_page=100')
    return [c['sha'] for c in j]


all_logs = sorted(pathlib.Path('.').glob('ship_result_p4*.json'))
logs = {p.name: json.loads(p.read_text(encoding='utf-8'))
        for p in [OUT / n for n in ['ship_result_p4.json'] + REISSUE]}
distinct = sorted({x['remote'] for lg in logs.values() for x in lg['pushed']})
reissue = sorted({x['remote'] for n in REISSUE for x in logs[n]['pushed']})
reissue_rows = sum(len(logs[n]['pushed']) for n in REISSUE)

writes = {}
for p in distinct:
    writes[p] = commits_touching(p)
one_write = {p: len(w) for p, w in writes.items() if p != REFUSED}
over = sorted([{'path': p, 'writes': n} for p, n in one_write.items() if n != 1], key=lambda x: x['path'])
controls = [{'path': t, 'writes': len(commits_touching(t))} for t in TWICE]

rescan_proof = {'reissue_rows_summed': reissue_rows,
                'reissue_distinct_paths': len(reissue),
                'duplicate_rows_inside_the_reissue': reissue_rows - len(reissue),
                'why_the_note_said_17': 'the r2 log was added to the list twice, once by name and once through '
                                        'the glob, so its rows were summed twice',
                'whole_span_distinct_paths': len(distinct)}
proof = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'branch': pub.BRANCH,
         'tip_read': pub.api('/git/ref/heads/' + pub.BRANCH)['object']['sha'],
         'method': 'GET /repos/.../commits?sha=<branch>&path=<file> - a path written once has one commit; a '
                   're-PUT would have two; the refused upload must have none',
         'per_path_writes': dict(sorted(((p, len(w)) for p, w in writes.items()), key=lambda kv: kv[0])),
         'paths_with_more_than_one_write': over,
         'the_gate_refused_path': {'path': REFUSED, 'commits_touching': len(writes[REFUSED]),
                                   'meaning': 'zero commits = nothing ever landed under that name'},
         'controls_known_to_hold_two_writes': controls,
         'counting_correction': rescan_proof}
proof['verdict'] = {
    'no_path_in_this_span_was_written_twice': not over,
    'the_refused_original_never_landed': len(writes[REFUSED]) == 0,
    'the_double_publish_controls_are_detected': all(c['writes'] >= 2 for c in controls) and len(controls) == 3,
}
proof['verdict']['ALL_HOLD'] = all(proof['verdict'].values())
(OUT / 'write_ledger_p4_span.json').write_text(json.dumps(proof, ensure_ascii=False, indent=1),
                                               encoding='utf-8', newline='\n')
print(json.dumps({'tip': proof['tip_read'], 'span_paths': len(distinct), 'reissue_paths': len(reissue),
                  'rows_summed': reissue_rows, 'over': over,
                  'refused_commits': len(writes[REFUSED]), 'controls': controls,
                  'verdict': proof['verdict']}, ensure_ascii=False, indent=1))
