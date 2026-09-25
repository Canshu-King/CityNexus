"""ORD-0291 T-c constant probe - setup: two private dist copies and two brand-new faces.

Rules I am holding to (the ones I asked for in 0288/0281 and the commander repeated in ③):
  - product bytes 0 changed: the bundle is patched only inside MY private copies;
  - the constant is named: file, byte offset, before-literal, after-literal, and both sha256s;
  - faces run on brand-new ports over frozen, self-consistent dists (asserted before start:
    every file nlink==1 and the asset named by index.html exists on disk);
  - the two arms are identical except the one 4-byte literal.

  stage make  : build probe_X (byte-identical copy) and probe_Xhalf (`12e3` -> `6e03`)
  stage serve : start the silent origin + one face per arm on fresh ports, print served sha256
  stage stop  : kill only the pids this file recorded
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request

BASE = pathlib.Path('D:/moodle/_hjp3_0291_0925')
FROZEN = pathlib.Path('D:/moodle/_hjp3_0276_0925/dist_frozen')
FACE_CWD = pathlib.Path('D:/moodle/_hjp3_ord0261_0923/snap_e3b0b47/frontend')
ASSET = 'index-CtuiCkKf.js'
LITERAL_BEFORE = '12e3'          # READ_DEADLINE_MS = 12_000
LITERAL_AFTER = '6e03'           # 6e03 === 6000, same length so no byte offsets move
ARMS = {'X': 8487, 'Xhalf': 8486}
ORIGIN_PORT = 8595
REG = BASE / 'probe_state.json'
DETACHED = 0x00000008 | 0x00000200


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def preflight(dist: pathlib.Path) -> dict:
    """My own 06:2x rule, applied before a face is believed: independent files + self-consistent shell."""
    files = [p for p in dist.rglob('*') if p.is_file()]
    html = (dist / 'index.html').read_text(encoding='utf-8')
    ref = re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)', html)
    return {'files': len(files), 'nlink_gt1': sum(1 for p in files if p.stat().st_nlink > 1),
            'referenced_assets': ref, 'assets_present': [(a, (dist / 'assets' / a).exists()) for a in ref]}


def do_make():
    src = FROZEN / 'assets' / ASSET
    raw = src.read_bytes()
    count = raw.decode('utf-8').count(LITERAL_BEFORE)
    if count != 1:
        raise SystemExit('literal %s occurs %d times - refusing an ambiguous patch' % (LITERAL_BEFORE, count))
    off = raw.decode('utf-8').index(LITERAL_BEFORE)
    made = {'source_asset': {'path': str(src), 'bytes': len(raw), 'sha256': sha(src),
                             'literal': LITERAL_BEFORE, 'literal_offset': offset_report(src, off),
                             'context': raw.decode()[off - 60:off + 40]}}
    for arm in ARMS:
        d = BASE / ('dist_' + arm)
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(FROZEN, d)
        if arm == 'Xhalf':
            target = d / 'assets' / ASSET
            patched = target.read_bytes().decode('utf-8').replace(LITERAL_BEFORE, LITERAL_AFTER, 1).encode('utf-8')
            assert len(patched) == len(raw), 'length must not change'
            target.write_bytes(patched)
        made[arm] = {'dist': str(d), 'asset_sha256': sha(d / 'assets' / ASSET),
                     'asset_bytes': (d / 'assets' / ASSET).stat().st_size,
                     'preflight': preflight(d)}
    made['patch'] = {'before': LITERAL_BEFORE, 'after': LITERAL_AFTER, 'offset': off,
                     'ms_before': int(float(LITERAL_BEFORE)), 'ms_after': int(float(LITERAL_AFTER)),
                     'occurrences_of_before_literal': count,
                     'why_equal_length': 'a same-length literal keeps every other byte offset valid, so the '
                                         'only difference between arms is the deadline value'}
    REG.write_text(json.dumps(made, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(made, ensure_ascii=False, indent=1))


def offset_report(path: pathlib.Path, char_index: int) -> dict:
    raw = path.read_bytes()
    txt = raw.decode('utf-8')
    byte_off = raw.index(LITERAL_BEFORE.encode())
    return {'char_index': char_index, 'byte_offset': byte_off, 'char_eq_byte': char_index == byte_off}


def listening(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return [l.split()[-1] for l in out.splitlines() if ('127.0.0.1:%d ' % port) in l and 'LISTENING' in l]


def silent_thread():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('127.0.0.1', ORIGIN_PORT))
    s.listen(64)
    held = []
    while True:
        c, _ = s.accept()
        held.append(c)          # accept, never answer


def do_serve():
    st = json.loads(REG.read_text(encoding='utf-8'))
    if listening(ORIGIN_PORT):
        raise SystemExit('origin port %d taken' % ORIGIN_PORT)
    threading.Thread(target=silent_thread, daemon=True).start()
    procs = {}
    env = dict(os.environ)
    env['CITYNEXUS_BACKEND_PORT'] = str(ORIGIN_PORT)
    env.pop('DEEPSEEK_API_KEY', None)
    for arm, port in ARMS.items():
        if listening(port):
            raise SystemExit('face port %d taken' % port)
        log = open(BASE / ('face_%s.log' % arm), 'w', encoding='utf-8', errors='replace')
        p = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview',
                              '--outDir', str(BASE / ('dist_' + arm)), '--port', str(port),
                              '--host', '127.0.0.1', '--strictPort'],
                             cwd=str(FACE_CWD), env=env, creationflags=DETACHED,
                             stdout=log, stderr=subprocess.STDOUT)
        for _ in range(90):
            if listening(port):
                break
            time.sleep(1)
        html = urllib.request.urlopen('http://127.0.0.1:%d/' % port, timeout=60).read().decode()
        ref = re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)', html)[0]
        raw = urllib.request.urlopen('http://127.0.0.1:%d/assets/%s' % (port, ref), timeout=120).read()
        procs[arm] = {'port': port, 'pid': p.pid, 'served_asset': ref,
                      'served_sha256': hashlib.sha256(raw).hexdigest(),
                      'matches_copy_on_disk': raw == (BASE / ('dist_' + arm) / 'assets' / ref).read_bytes(),
                      'arm_expected_sha': st[arm]['asset_sha256'],
                      'sha_matches_expected_arm_value': hashlib.sha256(raw).hexdigest() == st[arm]['asset_sha256']}
    st['faces'] = procs
    st['origin_pid_note'] = 'silent origin lives inside this python process; it dies with it'
    REG.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(procs, ensure_ascii=False, indent=1), flush=True)
    # keep the process (and therefore the silent origin thread) alive until a stop flag appears
    flag = BASE / 'stop.flag'
    if flag.exists():
        flag.unlink()
    while not flag.exists():
        time.sleep(1)
    flag.unlink()


def do_stop():
    st = json.loads(REG.read_text(encoding='utf-8')) if REG.exists() else {}
    out = {}
    for arm, f in (st.get('faces') or {}).items():
        r = subprocess.run(['taskkill', '/PID', str(f['pid']), '/T', '/F'], capture_output=True, text=True)
        out[arm] = {'pid': f['pid'], 'rc': r.returncode}
    time.sleep(1.5)
    out['listening_after'] = {p: listening(p) for p in list(ARMS.values()) + [ORIGIN_PORT]}
    print(json.dumps(out, ensure_ascii=False))


{'make': do_make, 'serve': do_serve, 'stop': do_stop}[sys.argv[1]]()
