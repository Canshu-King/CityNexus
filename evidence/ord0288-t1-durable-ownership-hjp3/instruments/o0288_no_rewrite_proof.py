"""ORD-0288 T-1: prove from commit history that no published path in this batch was ever re-PUT.

"已发布路径 0 覆盖" is a claim about writes, so it is checked with a write ledger: for a given path the
branch's own commit list (`GET /commits?path=...&sha=commander/control`) says how many times anything
landed at that name. One commit = written once and never rewritten.

  positive  every file this batch published has exactly ONE commit touching it
  negative  a method control - `evidence/ord0300-hjp3-write-cells/RECEIPT_O0300-2610.json` is the file the
            commander himself named as having been published twice; if my counter says 1 for that path,
            the method is blind and nothing here proves anything
  mutation  the two superseded pairs (instrument + boundary proof) must have DIFFERENT blobs, each with
            its own single commit - so the revision really went to a new name instead of replacing bytes

Everything is read from the branch at run time; the file records the tip it read.
"""
from __future__ import annotations

import hashlib
import importlib.util as iu
import json
import pathlib
import time
import urllib.parse

SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
B = pathlib.Path('D:/moodle/_hjp3_0288t1_0925')
spec = iu.spec_from_file_location('pub', str(SRC / 'o0288_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

PAIRS = [('instruments/o0288_md_final.py', 'instruments/o0288_md_final_r2.py'),
         ('boundary_proof_O0288T1.json', 'boundary_proof_O0288T1_r2.json')]
TWICE = 'evidence/ord0300-hjp3-write-cells/RECEIPT_O0300-2610.json'


def commits_touching(path):
    q = urllib.parse.quote(path, safe='')
    j = pub.api('/commits?sha=' + pub.BRANCH + '&path=' + q + '&per_page=100')
    return [{'sha': c['sha'], 'at': c['commit']['committer']['date'],
             'msg': c['commit']['message'].splitlines()[0][:70]} for c in j]


tip, tree, rows = pub.branch_rows()
on_branch = {r['path']: r['blob'] for r in rows}
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'repo': 'Canshu-King/CityNexus',
       'branch': pub.BRANCH, 'tip_read': tip, 'tree_read': tree,
       'method': 'GET /repos/.../commits?sha=<branch>&path=<file>&per_page=100 - counts the writes that '
                 'landed at that exact name',
       'files_under_prefix_now': len([r for r in rows if '.' in r['path'].split('/')[-1]]),
       'blobs': []}
single, multi = 0, []
for r in sorted(rows, key=lambda x: x['path']):
    if '.' not in r['path'].split('/')[-1]:
        continue
    cs = commits_touching(r['path'])
    single += len(cs) == 1
    if len(cs) != 1:
        multi.append({'path': r['path'].split('/', 1)[1], 'commits': len(cs), 'history': cs})
    out['blobs'].append({'path': r['path'].split('/', 1)[1], 'blob_40_hex': r['blob'],
                         'commits_touching_this_path': len(cs)})
out['every_published_path_has_exactly_one_write'] = not multi
out['paths_with_more_than_one_write'] = multi

tw = commits_touching(TWICE)
out['negative_control_method_sees_a_real_double_publish'] = {
    'path': TWICE.split('/', 1)[1], 'commits_touching': len(tw), 'history': tw,
    'so_the_counter_is_not_blind': len(tw) >= 2}

out['pairs'] = []
for old, new in PAIRS:
    bo, bn = on_branch.get(pub.PREFIX + '/' + old), on_branch.get(pub.PREFIX + '/' + new)
    co, cn = commits_touching(pub.PREFIX + '/' + old), commits_touching(pub.PREFIX + '/' + new)
    out['pairs'].append({'superseded_path': old, 'revision_path': new,
                         'superseded_blob_40_hex': bo, 'revision_blob_40_hex': bn,
                         'blobs_differ': bo != bn,
                         'superseded_writes': len(co), 'revision_writes': len(cn),
                         'superseded_history': co, 'revision_history': cn})
out['verdict'] = {
    'positive_no_path_in_this_batch_was_written_twice': out['every_published_path_has_exactly_one_write'],
    'negative_the_counter_detected_the_known_double_publish_in_ORD_0300':
        out['negative_control_method_sees_a_real_double_publish']['so_the_counter_is_not_blind'],
    'mutation_each_superseded_pair_is_two_names_two_blobs_one_write_each': all(
        p['blobs_differ'] and p['superseded_writes'] == 1 and p['revision_writes'] == 1
        for p in out['pairs'])}
out['verdict']['ALL_HOLD'] = all(out['verdict'].values())
(B / 'no_rewrite_proof_o0288.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                               encoding='utf-8', newline='\n')
print('tip', tip, '| paths', len(out['blobs']), '| all single-write:',
      out['every_published_path_has_exactly_one_write'], '| multi-write paths:',
      json.dumps(multi, ensure_ascii=False)[:300])
print('ORD-0300 double-publish control:',
      out['negative_control_method_sees_a_real_double_publish']['commits_touching'], 'writes')
print('pairs:', json.dumps([{k: p[k] for k in ('superseded_path', 'blobs_differ', 'superseded_writes',
                                               'revision_writes')} for p in out['pairs']],
                           ensure_ascii=False))
print('VERDICT', json.dumps(out['verdict'], ensure_ascii=False))
