"""ORD-0291: start one face of one of MY private dist copies against a named backend port, verify it,
and register it.  Refuses to believe a port whose listener is not the pid it records.

  python o0291_face.py start <arm> <port> <backend_port>
  python o0291_face.py stop  <arm> <port>
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = pathlib.Path('D:/moodle/_hjp3_0291_0925')
REG = BASE / 'probe_state.json'
FACE_CWD = pathlib.Path('D:/moodle/_hjp3_ord0261_0923/snap_e3b0b47/frontend')
JOURNEY = '91f78c9b-b768-46c9-a62e-4ac09b6609da'
DETACHED = 0x00000008 | 0x00000200


def listening(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return [ln.split()[-1] for ln in out.splitlines()
            if ('127.0.0.1:%d ' % port) in ln and 'LISTENING' in ln]


def cmdline(pid):
    ps = ("Get-CimInstance Win32_Process -Filter 'ProcessId=%d' | "
          'Select-Object -ExpandProperty CommandLine' % pid)
    return subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True,
                          text=True, encoding='utf-8', errors='replace').stdout.strip()


def http(method, url, timeout=90):
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001
        return 'ERR', str(e)[:200].encode()


def do_start(arm, port, backend_port):
    st = json.loads(REG.read_text(encoding='utf-8'))
    port = int(port)
    if listening(port):
        raise SystemExit('port %d is already taken - this order asks for brand-new ports' % port)
    env = dict(os.environ)
    env['CITYNEXUS_BACKEND_PORT'] = str(backend_port)
    log = open(BASE / ('face_%d.log' % port), 'w', encoding='utf-8', errors='replace')
    p = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview',
                          '--outDir', str(BASE / ('dist_' + arm)), '--port', str(port),
                          '--host', '127.0.0.1', '--strictPort'],
                         cwd=str(FACE_CWD), env=env, creationflags=DETACHED,
                         stdout=log, stderr=subprocess.STDOUT)
    for _ in range(90):
        if listening(port):
            break
        time.sleep(1)
    html = http('GET', 'http://127.0.0.1:%d/' % port, 60)[1].decode('utf-8', 'replace')
    ref = re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)', html)[0]
    raw = http('GET', 'http://127.0.0.1:%d/assets/%s' % (port, ref), 120)[1]
    served = hashlib.sha256(raw).hexdigest()
    mine, _ = http('GET', 'http://127.0.0.1:%d/api/v1/journeys/%s' % (port, JOURNEY), 60)
    foreign, _ = http('GET', 'http://127.0.0.1:%d/api/v1/journeys/%s' % (port, str(uuid.UUID(int=0xC0FFEE))), 60)
    expected = st[arm]['asset_sha256']
    rec = {'arm': arm, 'port': port, 'pid': p.pid, 'backend_port': int(backend_port),
           'served_asset': ref, 'served_sha256': served, 'arm_expected_sha': expected,
           'sha_matches_expected_arm_value': served == expected,
           'cmdline': cmdline(p.pid),
           'proxy_ownership': {'mine_via_face': mine, 'foreign_via_face': foreign}}
    extra = st.get('faces_extra') or {}
    extra[str(port)] = rec
    st['faces_extra'] = extra
    REG.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8')
    if served != expected:
        raise SystemExit('face %d serves the wrong arm bytes' % port)
    print(json.dumps(rec, ensure_ascii=False, indent=1))


def do_stop(arm, port, backend_port=None):
    st = json.loads(REG.read_text(encoding='utf-8'))
    port = int(port)
    rec = (st.get('faces_extra') or {}).get(str(port))
    now = listening(port)
    if not rec or not now or int(now[0]) != rec['pid'] or ('--port %d' % port) not in cmdline(rec['pid']):
        print(json.dumps({'port': port, 'refused': 'RECORDED_PID_IS_NOT_THE_LISTENER'}, ensure_ascii=False))
        return
    r = subprocess.run(['taskkill', '/PID', str(rec['pid']), '/T', '/F'], capture_output=True, text=True)
    time.sleep(1.5)
    print(json.dumps({'port': port, 'pid': rec['pid'], 'rc': r.returncode,
                      'listening_after': listening(port)}, ensure_ascii=False))


cmd = sys.argv[1]
{'start': do_start, 'stop': do_stop}[cmd](sys.argv[2], sys.argv[3], sys.argv[4] if cmd == 'start' else None)
