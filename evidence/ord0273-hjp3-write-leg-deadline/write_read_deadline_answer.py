"""ORD-0273 grid-1 input facts: write-leg vs read-leg deadline asymmetry, plus in-script teardown.

Arms (both on the shipped bundle index-ChOTTCvB.js served by my one-time face :8493):
  READ  (control, positive): hang `**/experience**` -> the app itself declares 「等了 12 秒」 and enters a
        named state with doors. Independent earlier reading under the same constant: GET /experience
        duration = 12,001 ms from resource timing.
  WRITE (test): hang `**/agent/commands**` -> no abort at 23 s and no abort at 61 s, the on-screen
        counter reads 23 then 60, no terminal state, the only exit is the user's own 取消 button.
Source coordinate for the mechanism (same bundle): `async function vb(t,e={},n=pb){const r=(e.method??"GET")
.toUpperCase(); if(r!=="GET"&&r!=="HEAD") return fetch(t,e); …}` with `const pb=12e3`, and the deadline error
is `ReadDeadlineMissed`. So the AbortController+12 s timer are built only on the GET/HEAD path.

Teardown is asserted here, not by hand: kill the two one-time listeners (proven by CommandLine first),
delete the one-time DB (plus -wal/-shm), then assert no listener and no file remain.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time

BASE = 'D:/moodle/_hjp3_narrow_0924/'
DB = BASE + 'one_time_n34.s3db'
BUNDLE = 'D:/moodle/_hjp3_fan_sweep_0923/snap_live_dist/assets/index-ChOTTCvB.js'
OUT = BASE + 'write_read_deadline.json'

facts = {
    'gen': {'face': 'http://127.0.0.1:8493', 'backend': 'http://127.0.0.1:8492',
            'frontend_bundle': 'index-ChOTTCvB.js', 'backend_tree': 'candidate 3093eea773c79fa00744fe72d1f2c43b4d0bd75e',
            'viewport': '390x844'},
    'source_coordinate': {
        'file': BUNDLE,
        'sha256': '2d56a79632efc0c6b30396ebbddcd54bd84c0d2fa6a30d3f20d09f4655d419de',
        'deadline_constant': 'pb = 12e3',
        'wrapper': 'vb(t, e = {}, n = pb) -> const r = (e.method ?? "GET").toUpperCase(); if (r !== "GET" && r !== "HEAD") return fetch(t, e);',
        'error_name': 'ReadDeadlineMissed',
        'read': 'the AbortController and the 12 s setTimeout are constructed only after the GET/HEAD guard, so a POST/PUT path is handed straight to fetch with no timer of its own',
    },
    'arm_read_control_positive': {
        'injection': "page.route('**/experience**') -> never fulfils (browser-side, labelled)",
        'screen_verbatim': '没有回音 / 等了 12 秒，这台服务器一个字也没回答 / 这一发读取到了期限仍然没有任何回答：服务器既没有拒绝，也没有答应，它只是没有说话。你的行程数据没有丢，这台设备上有已保存的行程，用下面的按钮可以只读查看这份本地快照；也可以再试一次。/ 看已保存的只读副本 / 重试 / 归因详情',
        'terminal_state': 'named state with three doors, declared at 12 s by the app itself',
        'independent_reading_same_constant': 'GET /experience duration = 12,001 ms (resource timing, earlier run in this lane)',
    },
    'arm_write_test': {
        'injection': "page.route('**/agent/commands**') -> never fulfils (browser-side, labelled)",
        'at_23s': {'on_screen_counter_seconds': 23, 'aborted_after_ms': None, 'terminal': False},
        'at_61s': {'on_screen_counter_seconds': 60, 'aborted_after_ms': None, 'terminal': False},
        'screen_verbatim': '发出请求，等待模型返回 · 已等待 N 秒 / 后端不会中途汇报进度，所以这里只有真实等待时间，没有百分比，也没有猜。/ ✓ 读取已有方案作为基线 ● 发出请求，等待模型返回 ○ 核对本次是否真的产出了新方案 / 取消 / 取消并关闭 / 规划中…',
        'client_deadline_exists': False,
        'what_ends_it': 'only the traveller pressing 取消 / 取消并关闭 (no automatic terminal state observed up to 61 s)',
    },
    'honest_limits': [
        'the write arm was observed to 61 s, not to a proven infinity',
        'my fetch wrapper is installed after page load, so a navigation wipes it; the read-arm positive evidence is the '
        "screen's own 「等了 12 秒」 plus the earlier 12,001 ms resource-timing reading, not an abort event from the wrapper",
        'both faults were injected browser-side; the one-time backend was healthy underneath',
    ],
}

killed = []
for port in (8492, 8493):
    ns = subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout
    for ln in ns.splitlines():
        if ('127.0.0.1:%d ' % port) in ln and 'LISTENING' in ln:
            pid = ln.split()[-1]
            cl = subprocess.run(['powershell', '-NoProfile', '-Command',
                                 "(Get-CimInstance Win32_Process -Filter 'ProcessId=%s').CommandLine" % pid],
                                capture_output=True, text=True).stdout.strip()
            if 'uvicorn app.main:app' in cl or 'vite.js preview' in cl:
                subprocess.run(['powershell', '-NoProfile', '-Command', 'Stop-Process -Id %s -Force' % pid],
                               capture_output=True)
                killed.append({'port': port, 'pid': pid, 'proven_by': cl[:120]})
time.sleep(2)
for p in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(p):
        os.unlink(p)
ns2 = subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout
facts['teardown'] = {
    'killed': killed,
    'listeners_left_8492_8493': sum(1 for ln in ns2.splitlines()
                                    if (('127.0.0.1:8492 ' in ln) or ('127.0.0.1:8493 ' in ln)) and 'LISTENING' in ln),
    'db_exists_after_delete': os.path.exists(DB),
}
facts['teardown']['assert_clean'] = (facts['teardown']['listeners_left_8492_8493'] == 0
                                     and facts['teardown']['db_exists_after_delete'] is False)
json.dump(facts, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('assert_clean =', facts['teardown']['assert_clean'], '| killed', len(killed), '| wrote', OUT)
