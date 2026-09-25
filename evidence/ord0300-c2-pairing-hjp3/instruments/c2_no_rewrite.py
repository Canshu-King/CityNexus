"""ORD-0300 C2 challenge: prove from the branch's own write ledger that no published path was re-PUT.

"已发布路径 0 覆盖" is a claim about writes, so it is counted with writes: `GET /commits?path=...` on
`commander/control` says how many times anything landed at that exact name. One commit = written once.

  positive  every path in this prefix has exactly ONE commit touching it
  negative  the counter must not be blind: the commander's own named double publish
            (`.../ord0300-hjp3-write-cells/RECEIPT_O0300-2610.json`) has to read >= 2
  mutation  my own recorded violation from ORD-0288 (the manifest I re-PUT) has to read >= 2 as well, on a
            different prefix - so the method sees a real overwrite wherever it happened, and the clean
            reading here is not an artefact of looking only where it suits me

Everything is read from the branch at run time and the tip it read is recorded.
"""
from __future__ import annotations

import importlib.util as iu
import json
import pathlib
import sys
import time
import urllib.parse

SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
B = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
spec = iu.spec_from_file_location('pub', str(SRC / 'c2_publish.py'))
pub = iu.module_from_spec(spec)
sys.path.insert(0, str(SRC))
spec.loader.exec_module(pub)

TWICE_ORD0300 = 'evidence/ord0300-hjp3-write-cells/RECEIPT_O0300-2610.json'
MY_VIOLATION = 'evidence/ord0288-t1-durable-ownership-hjp3/evidence_manifest_full40_o0288_r2.json'


def commits_touching(path):
    j = pub.api('/commits?sha=' + pub.BRANCH + '&path=' + urllib.parse.quote(path, safe='')
                + '&per_page=100')
    return [{'sha': c['sha'], 'at': c['commit']['committer']['date'],
             'msg': c['commit']['message'].splitlines()[0][:70]} for c in j]


tip, tree, rows = pub.branch_rows()
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'repo': 'Canshu-King/CityNexus',
       'branch': pub.BRANCH, 'tip_read': tip, 'tree_read': tree, 'prefix': pub.PREFIX,
       'method': 'GET /repos/.../commits?sha=<branch>&path=<file>&per_page=100 = how many times anything '
                 'landed at that exact name',
       'paths_under_prefix_now': len(rows), 'blobs': []}
single, multi = 0, []
for r in rows:
    cs = commits_touching(r['path'])
    single += len(cs) == 1
    if len(cs) != 1:
        multi.append({'path': r['path'].split('/', 1)[1], 'commits': len(cs), 'history': cs})
    out['blobs'].append({'path': r['path'].split('/', 1)[1], 'blob_40_hex': r['blob'],
                         'size': r['size'], 'commits_touching_this_path': len(cs)})
out['paths_counted'] = len(out['blobs'])
out['every_published_path_in_this_prefix_has_exactly_one_write'] = not multi and single == len(rows)
out['paths_with_more_than_one_write'] = multi

for label, path in (('the_double_publish_the_commander_himself_named_ORD_0300', TWICE_ORD0300),
                    ('the_overwrite_I_recorded_against_myself_in_ORD_0288', MY_VIOLATION)):
    cs = commits_touching(path)
    out['control_%s' % label] = {'path': path, 'commits_touching': len(cs), 'history': cs,
                                 'so_the_counter_is_not_blind': len(cs) >= 2}

controls = [k for k in out if k.startswith('control_')]
out['verdict'] = {
    'positive_no_path_in_this_prefix_was_written_twice':
        out['every_published_path_in_this_prefix_has_exactly_one_write'],
    'negative_both_counters_detected_a_real_double_publish':
        all(out[k]['so_the_counter_is_not_blind'] for k in controls),
    'mutation_this_batch_itself_offered_a_re_put_and_the_gate_refused_it': bool(
        json.loads((B / 'gate_selftest_publish_c2.json').read_text(encoding='utf-8'))
        ['verdict']['mutation_same_name_different_bytes_is_refused'])}
out['verdict']['ALL_HOLD'] = all(out['verdict'].values())
(B / 'no_rewrite_proof_c2.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                            encoding='utf-8', newline='\n')
print('tip', tip[:12], '| paths', out['paths_counted'], '| all single-write:',
      out['every_published_path_in_this_prefix_has_exactly_one_write'],
      '| multi:', json.dumps(multi, ensure_ascii=False)[:200])
for k in controls:
    print('%s -> %d writes' % (k, out[k]['commits_touching']))
print('VERDICT', json.dumps(out['verdict'], ensure_ascii=False))
