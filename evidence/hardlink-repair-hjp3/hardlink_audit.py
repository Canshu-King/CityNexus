"""Audit (and optionally repair) hard links inside my own snapshot dist directories.

Why: the commander reported that my `snap_live_dist` was not a copy at all but extra directory entries
pointing at the *same inodes* as his served dist - so an in-place overwrite on his side silently changed
"my" bytes, which is exactly how my blank-page reading happened.  Repair = give every shared-inode file its
own copy, inside my directories only; the other lane's paths are never written to.

  audit : print inode / nlink / sha256 per file for my dirs and the served dist
  fix   : for every file with nlink > 1 inside MY dirs, rewrite it as an independent copy and verify
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys

MINE = [pathlib.Path('D:/moodle/_hjp3_fan_sweep_0923/snap_live_dist'),
        pathlib.Path('D:/moodle/_hjp3_0281_0925/dist_frozen'),
        pathlib.Path('D:/moodle/_hjp3_0276_0925/dist_frozen')]
THEIRS = pathlib.Path('D:/moodle/_qoder_preview_20260920/dist')
OUT = pathlib.Path('D:/moodle/_hjp3_0281_0925/hardlink_audit.json')
MODE = sys.argv[1] if len(sys.argv) > 1 else 'audit'


def stat_row(p: pathlib.Path) -> dict:
    st = p.stat()
    return {'path': str(p), 'bytes': st.st_size, 'inode': st.st_ino, 'nlink': st.st_nlink,
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}


def collect(root: pathlib.Path) -> list:
    return [stat_row(p) for p in sorted(root.rglob('*')) if p.is_file()] if root.exists() else []


def main():
    mine = {str(r): collect(r) for r in MINE}
    theirs = collect(THEIRS)
    by_inode = {}
    for row in theirs:
        by_inode.setdefault(row['inode'], []).append(('theirs', row['path']))
    shared = []
    for src, rows in mine.items():
        for row in rows:
            if row['inode'] in by_inode:
                shared.append({'mine': row['path'], 'inode': row['inode'], 'nlink': row['nlink'],
                               'theirs': by_inode[row['inode']], 'sha256_equal':
                               all(hashlib.sha256(pathlib.Path(t[1]).read_bytes()).hexdigest() == row['sha256']
                                   for t in by_inode[row['inode']])})
            elif row['nlink'] > 1:
                shared.append({'mine': row['path'], 'inode': row['inode'], 'nlink': row['nlink'],
                               'theirs': None, 'sha256_equal': None})
    report = {'mode': MODE, 'my_dirs': {k: len(v) for k, v in mine.items()},
              'their_files': len(theirs), 'shared_inode_files': len(shared), 'shared': shared[:40]}

    if MODE == 'fix':
        fixed = []
        for item in list(shared):
            p = pathlib.Path(item['mine'])
            st = p.stat()
            if st.st_nlink < 2:
                continue
            data = p.read_bytes()
            tmp = p.with_name(p.name + '.deflink.tmp')
            with open(tmp, 'wb') as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, p)                      # breaks the hard link: new inode at the same name
            after = p.stat()
            fixed.append({'path': str(p), 'inode_before': st.st_ino, 'inode_after': after.st_ino,
                          'nlink_after': after.st_nlink,
                          'bytes_equal': after.st_size == len(data),
                          'sha256_equal': hashlib.sha256(p.read_bytes()).hexdigest() ==
                                          hashlib.sha256(data).hexdigest()})
        report['fixed'] = fixed
        report['fix_all_independent'] = all(f['nlink_after'] == 1 and f['bytes_equal'] and f['sha256_equal']
                                            for f in fixed)
        # re-audit after the repair so the claim is a post-state, not an intention
        still = [i for i in collect_all_mine() if i['nlink'] > 1]
        report['recheck_files_still_shared'] = len(still)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('shared', 'fixed')}, ensure_ascii=False, indent=1))
    if shared:
        print('first shared:', json.dumps(shared[0], ensure_ascii=False)[:400])


def collect_all_mine():
    rows = []
    for r in MINE:
        rows += collect(r)
    return rows


main()
