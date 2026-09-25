"""ORD-0300 driver: run one cell so the tap lands inside a bounded write-lock schedule.

The page is loaded and the sheet filled BEFORE any lock is taken (a boot read that writes would otherwise
park and the hub would never paint), then `sheet_ready.flag` → the rig arms → `lock_armed.flag` → the tap.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0300_0925')
RIG = pathlib.Path('D:/moodle/HJ-P3_evidence/o0300_rig.py')
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
RUN = os.environ.get('RUN_ID', 'O0300-2610')

stage = sys.argv[1]
secs_spec = sys.argv[2]                     # "70" or a schedule like "20,45"
plan = [int(x) for x in secs_spec.split(',')]
gap = int(sys.argv[3]) if len(sys.argv) > 3 else 0
rounds = int(sys.argv[4]) if len(sys.argv) > 4 else 1
cap = sys.argv[5] if len(sys.argv) > 5 else '70000'

for f in (BASE / 'sheet_ready.flag', BASE / 'lock_armed.flag'):
    if f.exists():
        f.unlink()

env = {**os.environ, 'RUN_ID': RUN, 'CAP_MS': cap, 'NEED_LOCK': '1' if rounds else '0'}
log = open(BASE / ('cell_%s_locklog.txt' % stage), 'w', encoding='utf-8', errors='replace')
node = subprocess.Popen(['node', str(BASE / 'o0300_cells.cjs'), stage], cwd=str(BASE), env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                        encoding='utf-8', errors='replace')
lock = None
if rounds:
    t0 = time.time()
    while time.time() - t0 < 120:
        if (BASE / 'sheet_ready.flag').exists():
            lock = subprocess.Popen([PY, str(RIG), 'lock', secs_spec, str(gap), str(len(plan))],
                                    stdout=log, stderr=subprocess.STDOUT, text=True,
                                    encoding='utf-8', errors='replace')
            armed = None
            t1 = time.time()
            while time.time() - t1 < 40:
                if 'ARMED' in (BASE / ('cell_%s_locklog.txt' % stage)).read_text(encoding='utf-8',
                                                                                  errors='replace'):
                    armed = time.strftime('%H:%M:%S')
                    break
                time.sleep(0.2)
            if armed is None:
                print('LOCK NEVER ARMED - aborting', flush=True)
                node.kill()
                sys.exit(1)
            (BASE / 'lock_armed.flag').write_text(armed, encoding='utf-8')
            print('window 1 of %s armed at %s' % (secs_spec, armed), flush=True)
            break
        if node.poll() is not None:
            print('NODE EXITED EARLY rc=%s' % node.returncode, flush=True)
            break
        time.sleep(0.25)

out, _ = node.communicate(timeout=400)
(BASE / ('cell_%s_node.txt' % stage)).write_text(out or '', encoding='utf-8')
print(out, flush=True)
if lock is not None:
    lock.wait(timeout=sum(plan) + gap * len(plan) + 90)
log.flush()
print('LOCK LOG:', (BASE / ('cell_%s_locklog.txt' % stage)).read_text(encoding='utf-8'), flush=True)
for f in (BASE / 'sheet_ready.flag', BASE / 'lock_armed.flag'):
    if f.exists():
        f.unlink()
