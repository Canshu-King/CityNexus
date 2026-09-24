"""ORD-0281 定形的现场佐证：读腿的期限今天真的会响，写腿不会。

Why this is measured and not argued: `readDeadline.ts:10-12` says the deadline is deliberately reads-only,
because aborting a write is an idempotency question.  To define ORD-0281's cells I need to know that the
timer machinery really fires and what sentence it puts on screen - so the write-leg wording can be required
to be *different* and still nameable.

  origin :8597  accepts the TCP connection and never answers (the silent third state)
  face   :8596  vite preview on my frozen bundle, proxy pinned to :8597, brand-new port (no SW history)
"""
from __future__ import annotations

import json
import os
import pathlib
import socket
import subprocess
import threading
import time

BASE = pathlib.Path('D:/moodle/_hjp3_0281_0925')
FROZEN = pathlib.Path('D:/moodle/_hjp3_0276_0925/dist_frozen')
FACE_CWD = pathlib.Path('D:/moodle/_hjp3_ord0261_0923/snap_e3b0b47/frontend')
ORIGIN_PORT, FACE_PORT = 8597, 8596
DETACHED = 0x00000008 | 0x00000200
STATE = BASE / 'silent_face_state.json'


def silent_origin():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('127.0.0.1', ORIGIN_PORT))
    s.listen(64)
    held = []
    while True:
        c, _ = s.accept()
        held.append(c)  # accept, read nothing, never reply


def listening(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return [l.split()[-1] for l in out.splitlines() if ('127.0.0.1:%d ' % port) in l and 'LISTENING' in l]


def do_start():
    if listening(ORIGIN_PORT) or listening(FACE_PORT):
        raise SystemExit('refusing to start: %d/%d already taken' % (ORIGIN_PORT, FACE_PORT))
    t = threading.Thread(target=silent_origin, daemon=True)
    t.start()
    env = dict(os.environ)
    env['CITYNEXUS_BACKEND_PORT'] = str(ORIGIN_PORT)
    env.pop('DEEPSEEK_API_KEY', None)
    log = open(BASE / 'silent_face.log', 'w', encoding='utf-8', errors='replace')
    f = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview', '--outDir', str(FROZEN),
                          '--port', str(FACE_PORT), '--host', '127.0.0.1', '--strictPort'],
                         cwd=str(FACE_CWD), env=env, creationflags=DETACHED, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(90):
        if listening(FACE_PORT):
            break
        time.sleep(1)
    # prove the origin is silent, not refused: a real connection is accepted and stays unanswered
    probe = {'connect_accepted': None, 'answered_within_3s': None}
    try:
        c = socket.create_connection(('127.0.0.1', ORIGIN_PORT), timeout=3)
        probe['connect_accepted'] = True
        c.sendall(b'GET /api/v1/travelers HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n')
        try:
            probe['answered_within_3s'] = bool(c.recv(64))
        except Exception:
            probe['answered_within_3s'] = False
        c.close()
    except Exception as e:
        probe['connect_accepted'] = 'ERR ' + str(e)[:80]
    STATE.write_text(json.dumps({'face_pid': f.pid, 'origin_port': ORIGIN_PORT, 'face_port': FACE_PORT,
                                 'probe': probe, 'listening': listening(FACE_PORT)}, ensure_ascii=False, indent=1),
                     encoding='utf-8')
    print(json.dumps({'face_pid': f.pid, 'probe': probe, 'face_listening': listening(FACE_PORT)},
                     ensure_ascii=False))


def do_stop():
    st = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}
    r = subprocess.run(['taskkill', '/PID', str(st.get('face_pid')), '/T', '/F'], capture_output=True, text=True)
    time.sleep(1.5)
    print(json.dumps({'killed_face_rc': r.returncode, 'face_listening': listening(FACE_PORT),
                      'origin_listening': listening(ORIGIN_PORT)}, ensure_ascii=False))


{'start': do_start, 'stop': do_stop}[__import__('sys').argv[1]]()
