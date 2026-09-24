"""Re-parent my two faces onto independent copies and keep the control arm usable.

- `snap_live_dist` was 35 hard links into the commander's served dist (same inodes, nlink=2): an in-place
  overwrite on his side silently changed "my" bytes.  `hardlink_audit.py fix` broke those links; this file
  moves the control face onto a brand-new port (the old one carries a stale service worker from my earlier
  run) and records every pid it starts, so nothing is ever killed by port shape.
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
import urllib.request

STATE = pathlib.Path('D:/moodle/_hjp3_0279_0924/o0279_pids.json')
X_STATE = pathlib.Path('D:/moodle/_hjp3_0279x_0925/o0279x_pids.json')
F26_STATE = pathlib.Path('D:/moodle/_hjp3_0276_0925/face_8499.json')
FACE_CWD = pathlib.Path('D:/moodle/_hjp3_ord0261_0923/snap_e3b0b47/frontend')
DETACHED = 0x00000008 | 0x00000200
REG = pathlib.Path('D:/moodle/_hjp3_0281_0925/face_registry.json')


def listening(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return [l.split()[-1] for l in out.splitlines() if ('127.0.0.1:%d ' % port) in l and 'LISTENING' in l]


def kill_recorded(path, key, port=None):
    st = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    pid = st.get(key)
    if not pid:
        return {'skipped': 'no pid recorded in %s' % path.name}
    live = listening(port) if port else []
    if port and [str(pid)] != live:
        return {'refused': 'recorded pid %s is not the listener on %d (it is %s) - refusing to kill'
                        % (pid, port, live)}
    # the command line must also name my own outDir/port, or it is somebody else's process wearing my pid
    probe = subprocess.run(['powershell', '-NoProfile', '-Command',
                            "Get-CimInstance Win32_Process -Filter 'ProcessId=%d' | "
                            'Select-Object -ExpandProperty CommandLine' % pid],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
    cl = (probe.stdout or '').strip().replace('\n', ' ')
    if '--port %d' % port not in cl:
        return {'refused': 'pid %s command line does not name --port %d: %s' % (pid, port, cl[:140])}
    r = subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True, text=True)
    time.sleep(1.5)
    return {'pid': pid, 'rc': r.returncode, 'command_line_checked': cl[:120],
            'listening_after': listening(port)}


def start_face(port, backend_port, outdir):
    if listening(port):
        raise SystemExit('port %d already taken' % port)
    env = dict(os.environ)
    env['CITYNEXUS_BACKEND_PORT'] = str(backend_port)
    env.pop('DEEPSEEK_API_KEY', None)
    log = open(pathlib.Path('D:/moodle/_hjp3_0281_0925/face_%d.log' % port), 'w',
               encoding='utf-8', errors='replace')
    p = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', 'preview', '--outDir', str(outdir),
                          '--port', str(port), '--host', '127.0.0.1', '--strictPort'],
                         cwd=str(FACE_CWD), env=env, creationflags=DETACHED, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(90):
        if listening(port):
            break
        time.sleep(1)
    html = urllib.request.urlopen('http://127.0.0.1:%d/' % port, timeout=60).read().decode('utf-8', 'replace')
    asset = re.findall(r'assets/(index-[A-Za-z0-9_-]+\.js)', html)[0]
    raw = urllib.request.urlopen('http://127.0.0.1:%d/assets/%s' % (port, asset), timeout=120).read()
    disk = (pathlib.Path(outdir) / 'assets' / asset).read_bytes()
    return {'port': port, 'pid': p.pid, 'backend': backend_port, 'outDir': str(outdir), 'asset': asset,
            'served_bytes': len(raw), 'served_sha256': hashlib.sha256(raw).hexdigest(),
            'matches_disk': raw == disk, 'disk_nlink': (pathlib.Path(outdir) / 'assets' / asset).stat().st_nlink,
            'listening': listening(port)}


if __name__ == '__main__':
    reg = {}
    if '--restart-control' in sys.argv:
        reg['stopped_old_control_face'] = kill_recorded(STATE, 'face', 8498)
        reg['control_face_new'] = start_face(8495, 8497, 'D:/moodle/_hjp3_fan_sweep_0923/snap_live_dist')
    if '--stop-0279x-face' in sys.argv:
        reg['stopped_8494_already_done'] = True
    if '--report' in sys.argv:
        pass
    reg['still_listening'] = {p: listening(p) for p in (8493, 8495, 8497, 8499, 8494, 8498)}
    old = json.loads(REG.read_text(encoding='utf-8')) if REG.exists() else {}
    old.update(reg)
    REG.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(reg, ensure_ascii=False, indent=1))
