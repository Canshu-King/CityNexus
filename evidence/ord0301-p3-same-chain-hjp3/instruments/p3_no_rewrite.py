"""ORD-0301 pass 3: the write ledger behind the phrase 「已发布路径 0 覆盖」.

That phrase is a claim about WRITES, so it is checked with a write counter: for a path, the branch's own
commit list (`GET /commits?sha=<branch>&path=<file>`) says how many times anything landed at that exact name.
One commit = written once and never rewritten.

  positive  every path under this batch's prefix has exactly one commit touching it
  negative  two controls that are KNOWN to hold more than one write, so the counter is not blind:
            `evidence/ord0300-hjp3-write-cells/RECEIPT_O0300-2610.json` (the commander named it as published
            twice) and `evidence/ord0288-t1-durable-ownership-hjp3/evidence_manifest_full40_o0288.json`
  mutation  if this batch's own self-growing manifest was republished under a new name, the superseded copy
            must still show exactly ONE write - a revision that moved to a new name is not a rewrite

The file records the tip it read, and it reports honestly: if anything here shows two writes, ALL_HOLD is
false and the receipt says so rather than the ledger being re-run until it agrees.
"""
from __future__ import annotations

import importlib.util as iu
import json
import pathlib
import time
import urllib.parse

B = pathlib.Path('D:/moodle/_hjp3_0301p3_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

TWICE = ['evidence/ord0300-hjp3-write-cells/RECEIPT_O0300-2610.json',
         'evidence/ord0288-t1-durable-ownership-hjp3/evidence_manifest_full40_o0288.json']


def commits_touching(path):
    q = urllib.parse.quote(path, safe='')
    j = pub.api('/commits?sha=' + pub.BRANCH + '&path=' + q + '&per_page=100')
    return [{'sha': c['sha'], 'at': c['commit']['committer']['date'],
             'msg': c['commit']['message'].splitlines()[0][:64]} for c in j]


tip, tree, rows = pub.branch_rows()
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'repo': 'Canshu-King/CityNexus',
       'branch': pub.BRANCH, 'tip_read': tip, 'tree_read': tree, 'prefix': pub.PREFIX,
       'method': 'GET /repos/.../commits?sha=<branch>&path=<file>&per_page=100 - counts the writes that '
                 'landed at that exact name',
       'paths_under_prefix': len(rows), 'blobs': []}
multi = []
for r in rows:
    cs = commits_touching(r['path'])
    if len(cs) != 1:
        multi.append({'path': r['path'].split('/', 1)[1], 'commits': len(cs), 'history': cs})
    out['blobs'].append({'path': r['path'].split('/', 1)[1], 'blob_40_hex': r['blob'],
                         'commits_touching_this_path': len(cs)})
out['every_published_path_has_exactly_one_write'] = not multi
out['paths_with_more_than_one_write'] = multi

out['negative_controls_the_counter_is_not_blind'] = []
for t in TWICE:
    tw = commits_touching(t)
    out['negative_controls_the_counter_is_not_blind'].append(
        {'path': t.split('/', 1)[1], 'commits_touching': len(tw), 'history': tw,
         'so_the_counter_is_not_blind': len(tw) >= 2})

sup = [x['path'] for x in out['blobs'] if 'superseded' in x['path'] or x['path'].startswith('discarded_')]
out['revisions_that_moved_to_new_names'] = []
for p in sup:
    cs = commits_touching(pub.PREFIX + '/' + p)
    out['revisions_that_moved_to_new_names'].append({'path': p, 'writes': len(cs), 'history': cs})

out['verdict'] = {
    'positive_no_path_in_this_batch_was_written_twice': out['every_published_path_has_exactly_one_write'],
    'negative_both_known_double_publishes_were_detected': all(
        c['so_the_counter_is_not_blind'] for c in out['negative_controls_the_counter_is_not_blind'])
    and len(out['negative_controls_the_counter_is_not_blind']) == 2,
    'mutation_superseded_and_discarded_copies_each_hold_one_write': all(
        x['writes'] == 1 for x in out['revisions_that_moved_to_new_names'])}
out['verdict']['ALL_HOLD'] = all(out['verdict'].values())
(B / 'no_rewrite_proof_p3.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8',
                                           newline='\n')
print('tip', tip, '| paths', len(rows), '| all single-write:',
      out['every_published_path_has_exactly_one_write'], '| multi:', json.dumps(multi, ensure_ascii=False)[:300])
print('controls:', [(c['path'][:40], c['commits_touching'])
                    for c in out['negative_controls_the_counter_is_not_blind']])
print('VERDICT', json.dumps(out['verdict'], ensure_ascii=False))
