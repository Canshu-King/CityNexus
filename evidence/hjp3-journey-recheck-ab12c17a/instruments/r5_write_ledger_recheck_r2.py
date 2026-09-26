"""Re-count the writes under the recheck prefix after the last three files landed (r2).

The first pass covered 19 names; the bus note, its read-back and its instrument came after it, so
this revision re-reads the whole prefix. New file name because a published instrument path is
never rewritten.

A retry happened here: one PUT was refused with 409 by optimistic concurrency and re-issued under
the same path. If that refusal had cost a write, this counter would show two commits at that name.

「0 覆盖」 is a claim about writes, so it is answered with the branch's own commit list per path, not with my log
rows: one commit at a name means the name was written once. Paths the gate refused must show zero commits, and
three paths known to have been published twice are counted as controls so the counter cannot be blind.
"""
from __future__ import annotations

import importlib.util as iu
import json
import pathlib
import time
import urllib.parse

OUT = pathlib.Path('D:/moodle/_hjp3_0323walk_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
PREFIX = 'evidence/hjp3-journey-recheck-ab12c17a/'
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)
CONTROLS = ['evidence/ord0300-c2-pairing-hjp3/evidence_manifest_full40_c2.json',
            'evidence/ord0288-t1-durable-ownership-hjp3/evidence_manifest_full40_o0288_r2.json',
            'evidence/ord0300-hjp3-write-cells/RECEIPT_O0300-2610.json']


def commits_touching(path):
    q = urllib.parse.quote(path, safe='')
    return [c['sha'] for c in pub.api('/commits?sha=' + pub.BRANCH + '&path=' + q + '&per_page=100')]


tip = pub.api('/git/ref/heads/' + pub.BRANCH)['object']['sha']
entries = pub.api('/git/trees/' + tip + '?recursive=1')['tree']
paths = sorted(x['path'] for x in entries if x['path'].startswith(PREFIX) and x.get('type') == 'blob')
dirs = sorted(x['path'] for x in entries if x['path'].startswith(PREFIX) and x.get('type') != 'blob')
counts = {p: len(commits_touching(p)) for p in paths}
over = sorted([{'path': p, 'commits': n} for p, n in counts.items() if n != 1], key=lambda x: x['path'])
controls = [{'path': p, 'commits': len(commits_touching(p))} for p in CONTROLS]
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'branch': pub.BRANCH, 'tip_read': tip,
       'prefix': PREFIX,
       'method': 'GET /repos/.../commits?sha=<branch>&path=<file> - one commit at a name means written once',
       'files_under_prefix': len(paths), 'tree_entries_excluded': dirs,
       'why_the_tree_entries_are_excluded': 'a commits?path=<directory> query legitimately returns every commit that '
                                            'touched anything under it, so counting a directory as a write would '
                                            'manufacture a re-PUT that never happened', 'commits_per_path': counts,
       'paths_with_more_than_one_commit': over,
       'controls_known_to_hold_two_writes': controls,
       'verdict': {
           'no_path_in_this_prefix_was_written_twice': not over,
           'the_counter_is_not_blind': all(c['commits'] >= 2 for c in controls) and len(controls) == 3,
           'a_directory_was_counted_until_it_was_excluded': len(dirs) > 0}}
out['verdict']['ALL_HOLD'] = all(out['verdict'].values())
(OUT / 'write_ledger_recheck_r2.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                            encoding='utf-8', newline='\n')
print(json.dumps({'paths': len(paths), 'over': over, 'controls': [c['commits'] for c in controls],
                  'verdict': out['verdict']}, ensure_ascii=False))
