"""Batch setup for the 03:32 re-run: export the NEW tip and build it into my own outDir.

This is step 1 of "re-measure ORD-0312's discriminating cells on the generation that is actually serving now".
It exists as its own script because the honest failure mode is a missing bundle, and I want the cost and the
first bad reading on the record before I spend the rig's time: `git archive` (read-only) of `backend frontend`,
the sheet blob re-hashed from the exported bytes and compared to what the tip's tree says, a junction for
node_modules, then `vite build` into a private outDir.

Nothing shared is touched: the product tree, the release dist, the phone chain and the tunnels are not written,
no database is created here, and the generation assertion is the one that stops me from accidentally re-running
the previous generation.
"""
from __future__ import annotations

import importlib.util as iu
import json
import pathlib
import sys
import time

SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
BASE = pathlib.Path('D:/moodle/_hjp3_0312r_0926')
WHICH = 'gen2'
TIP = '9a669c8bec863fadf31d5158f4a1be66aec49f23'
SHEET_BLOB = 'fc4d6111dc013008b610a240aab096deebe2436f'

spec = iu.spec_from_file_location('cs', str(SRC / 'c2_setup.py'))
cs = iu.module_from_spec(spec)
sys.dont_write_bytecode = True
spec.loader.exec_module(cs)
cs.BASE = BASE
cs.TIPS = {WHICH: TIP}
cs.BLOBS = {WHICH: SHEET_BLOB}
BASE.mkdir(exist_ok=True)

t0 = time.time()
ex = cs.export(WHICH, TIP)
t_export = time.time() - t0
print('exported in %.1fs | sheet blob matches the tip: %s | unguarded reads: %s | guarded reads: %s'
      % (t_export, ex['sheet_blob_matches_the_generation'], ex['unguarded_detail_reads'],
         ex['guarded_detail_reads']), flush=True)
assert ex['sheet_blob_matches_the_generation'], 'the export is not the generation I asked for'
t1 = time.time()
junction = cs.junction(BASE / ('snap_%s' % WHICH) / 'frontend')
b = cs.build(WHICH, BASE / ('snap_%s' % WHICH) / 'frontend', BASE / ('dist_%s' % WHICH))
t_build = time.time() - t1
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'which': WHICH, 'tip': TIP,
       'sheet_blob_expected': SHEET_BLOB, 'how_read': 'git archive (read-only) of backend+frontend, re-hash of '
                                                      'the sheet off the exported bytes, private outDir build',
       'seconds_export': round(t_export, 1), 'seconds_build': round(t_build, 1),
       'junction': junction, 'export': ex, 'bundle': b,
       'served_rows_from_the_commanders_probe': {
           'js_asset_this_build_should_equal': '/assets/index-JMSnur7a.js'},
       'boundaries': '0 write to the product tree / release dist / phone chain / tunnels; no database here; '
                     'no demo/reset; no credential printed'}
out['built_asset_matches_the_probe_row_name'] = bool(
    b['asset'].lstrip('/') in {'assets/index-JMSnur7a.js', 'index-JMSnur7a.js'})
out['built_bytes_equal_the_probe_row'] = None
(BASE / 'setup_facts_gen2.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                            encoding='utf-8', newline='\n')
print(json.dumps({'seconds_export': out['seconds_export'], 'seconds_build': out['seconds_build'],
                  'asset': b['asset'], 'bytes': b['bytes'], 'sha256': b['sha256_64_hex'][:16],
                  'name_matches_probe_row': out['built_asset_matches_the_probe_row_name'],
                  'markers': b.get('markers')}, ensure_ascii=False), flush=True)
