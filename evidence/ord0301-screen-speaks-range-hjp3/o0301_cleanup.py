"""Kill ONLY listeners whose command line carries one of my own signatures; report the rest untouched.

This exists because ORD-0300 taught me that a compound teardown boolean can be measured half and
because a port being 'not the default one' is not a reason to kill what sits on it.
"""
from __future__ import annotations

import json
import subprocess
import sys

MINE = ('app.main:app', 'vite.js preview', 'o0301_origin.py', 'o0291_selective_origin.py',
        'o0300_rig.py', 'uvicorn app.main')


def listeners(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return [ln.split()[-1] for ln in out.splitlines()
            if ('127.0.0.1:%d ' % port) in ln and 'LISTENING' in ln]


def cmdline(pid):
    ps = ("Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | "
          'Select-Object -ExpandProperty CommandLine' % pid)
    return subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True,
                          text=True, encoding='utf-8', errors='replace').stdout.strip()


report = {}
for port in [int(x) for x in sys.argv[1:]]:
    for pid in set(listeners(port)):
        cl = cmdline(pid)
        mine = any(s in cl for s in MINE)
        entry = {'pid': pid, 'cmdline': cl[:200], 'mine': mine, 'killed': False}
        if mine:
            subprocess.run(['taskkill', '/PID', pid, '/T', '/F'], capture_output=True)
            entry['killed'] = True
        report.setdefault(str(port), []).append(entry)
print(json.dumps({'actions': report,
                  'still_listening': {p: listeners(int(p)) for p in report}}, ensure_ascii=False, indent=1))
