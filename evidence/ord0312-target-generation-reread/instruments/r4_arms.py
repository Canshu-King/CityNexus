"""The pass-3 arm table, aimed at the 03:3x generation and its same-generation unguarded mutant.

`p3_arms.py` is published and its arm table is exactly what ORD-0312 asks for, so this wrapper changes only where
it looks: the batch directory, the rig it spawns, and the two tips it asserts against. The arms themselves are
unchanged, which is the point - a re-run that quietly edits its own assertions is not a re-run.

  python r4_arms.py list
  python r4_arms.py 0        # one arm by index
  python r4_arms.py 0,1,3,4  # a subset
"""
from __future__ import annotations

import importlib.util as iu
import json
import pathlib
import sys

SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
BASE = pathlib.Path('D:/moodle/_hjp3_0312r_0926')
TIP = '9a669c8bec863fadf31d5158f4a1be66aec49f23'
MUT_TIP = TIP + '+unguarded_mutant(private)'

spec = iu.spec_from_file_location('p3arms', str(SRC / 'p3_arms.py'))
ar = iu.module_from_spec(spec)
spec.loader.exec_module(ar)

ar.BASE = BASE
ar.RIG = str(SRC / 'r4_rig.py')
ar.PAIR_LOG = BASE / 'p3_pair_log.jsonl'
ar.READY = BASE / 'p3_sheet_ready.flag'
ar.TIPS = {'dep': TIP, 'old': MUT_TIP}
BASE.mkdir(exist_ok=True)
print('arms re-pointed: BASE=%s RIG=%s TIPS=%s' % (BASE, ar.RIG, json.dumps(ar.TIPS)[:70]), flush=True)

if sys.argv[1] == 'list':
    print(json.dumps([{'i': i, 'arm': '%s/%s' % (a[0], (a[3] or {}).get('name') or a[2]), 'intent': a[5][:90]}
                      for i, a in enumerate(ar.ARMS)], ensure_ascii=False, indent=1))
    raise SystemExit(0)
idxs = sys.argv[1].split(',') if sys.argv[1] != 'all' else [str(i) for i in range(len(ar.ARMS))]
res = []
for i in idxs:
    print('=== arm', i, ar.ARMS[int(i)][0], ar.ARMS[int(i)][2], flush=True)
    res.append(ar.run_arm(*ar.ARMS[int(i)]))
print(json.dumps([{'arm': x['arm'], 'run': x['run_id'], 'failed': x.get('failed', False)} for x in res],
                 ensure_ascii=False))
