"""ORD-0291: drive one WRITE arm so the tap lands inside a bounded write-lock window.

Ordering matters and is the reason this driver exists: the hub must render while the DB is free (a boot read
that writes would otherwise park and I would never reach the sheet), so the page loads, opens the sheet and
fills the request, raises `sheet_ready.flag`, and only then do I arm the lock and release `lock_armed.flag`.
Nothing here changes the product: the same helper the ORD-0279-X rig used holds the transaction, and it
self-proves the hold by showing a second writer being refused.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0291_0925')
LOCKER = pathlib.Path('D:/moodle/HJ-P3_evidence/o0279x_serve.py')
PY = 'D:/moodle/CityNexus/.venv/Scripts/python.exe'
NODE = 'node'
RUN_ID = os.environ.get('RUN_ID', 'O0291-2507')
WINDOW = 100

arm, port, constant = sys.argv[1], sys.argv[2], sys.argv[3]
for f in (BASE / 'sheet_ready.flag', BASE / 'lock_armed.flag'):
    if f.exists():
        f.unlink()

log = open(BASE / ('writearm_%s_locklog.txt' % arm), 'w', encoding='utf-8', errors='replace')
node = subprocess.Popen([NODE, str(BASE / 'o0291_arms.cjs'), 'write', arm, port, constant],
                        cwd=str(BASE), env={**os.environ, 'RUN_ID': RUN_ID},
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                        encoding='utf-8', errors='replace')
lock = None
t0 = time.time()
while time.time() - t0 < 90:
    if (BASE / 'sheet_ready.flag').exists():
        lock = subprocess.Popen([PY, str(LOCKER), 'lock', str(WINDOW)], stdout=log, stderr=subprocess.STDOUT,
                                text=True, encoding='utf-8', errors='replace')
        armed_at = None
        t1 = time.time()
        while time.time() - t1 < 30:
            if 'ARMED' in (BASE / ('writearm_%s_locklog.txt' % arm)).read_text(encoding='utf-8', errors='replace'):
                armed_at = time.strftime('%H:%M:%S')
                break
            time.sleep(0.2)
        if armed_at is None:
            print('LOCK NEVER ARMED - aborting this arm', flush=True)
            node.kill()
            sys.exit(1)
        (BASE / 'lock_armed.flag').write_text(armed_at, encoding='utf-8')
        print('window armed at', armed_at, flush=True)
        break
    if node.poll() is not None:
        print('NODE EXITED EARLY rc=%s' % node.returncode, flush=True)
        break
    time.sleep(0.25)

out, _ = node.communicate(timeout=240)
(BASE / ('writearm_%s_node.txt' % arm)).write_text(out or '', encoding='utf-8')
print(out, flush=True)
if lock is not None:
    lock.wait(timeout=WINDOW + 60)
log.flush()
print('lock log:', pathlib.Path(BASE / ('writearm_%s_locklog.txt' % arm)).read_text(encoding='utf-8'), flush=True)
for f in (BASE / 'sheet_ready.flag', BASE / 'lock_armed.flag'):
    if f.exists():
        f.unlink()
