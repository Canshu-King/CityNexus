"""The pass-3 rig, re-pointed at the 03:3x generation instead of a copy of itself.

`p3_rig.py` is already published, so its bytes are frozen; what the 03:32 order needs is the same machine aimed
at a different bundle. This wrapper loads that module, replaces its globals with the new batch's paths and ports,
and dispatches the same subcommands. Nothing about the mechanism changes: one-time database, my own ports, the
pairing hop in front of a real backend, a private preview face, and the identity probe that proves the port I
read belongs to the process I started.

  python r4_rig.py start dep pass
  python r4_rig.py stop
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

spec = iu.spec_from_file_location('p3rig', str(SRC / 'p3_rig.py'))
rig = iu.module_from_spec(spec)
spec.loader.exec_module(rig)

rig.BASE = BASE
rig.GEN = {'dep': {'tip': TIP, 'snap': BASE / 'snap_gen2', 'dist': BASE / 'dist_gen2'},
           'old': {'tip': MUT_TIP, 'snap': BASE / 'snap_mut2', 'dist': BASE / 'dist_mut2'}}
rig.PORTS = {'backend': 8661, 'proxy': 8662, 'face_dep': 8663, 'face_old': 8664}
# the state file keeps the rig's own name on purpose: `p3_arms.py` reads `p3_rig_state.json` out of BASE, and a
# rename here would make the reader assert against a file that is not written
rig.STATE = BASE / 'p3_rig_state.json'
rig.PIDS = BASE / 'p3_rig_pids.json'

cmd = sys.argv[1]
print('rig re-pointed: BASE=%s dep=%s old=%s ports=%s' % (BASE, TIP[:12], 'mut2', rig.PORTS), flush=True)
if cmd == 'start':
    spec_arg = None
    if len(sys.argv) > 4 and sys.argv[4].startswith('{'):
        spec_arg = json.loads(sys.argv[4])
    elif len(sys.argv) > 4 and pathlib.Path(sys.argv[4]).exists():
        spec_arg = json.loads(pathlib.Path(sys.argv[4]).read_text(encoding='utf-8'))
    rig.do_start(sys.argv[2], sys.argv[3], spec_arg)
elif cmd == 'lock':
    rig.do_lock(sys.argv[2], sys.argv[3])
elif cmd == 'stop':
    rig.do_stop()
elif cmd == 'ports':
    rig.do_ports()
else:
    raise SystemExit('unknown command ' + cmd)
