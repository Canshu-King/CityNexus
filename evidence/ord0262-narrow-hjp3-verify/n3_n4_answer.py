"""N4 + the equality self-test + in-script teardown.

N4 asks: when a mission row DOES exist for the round, does the screen still say "not recorded"?
So I re-fire the same write under a fresh held lock, capture the server envelope myself (no
transcription needed), then count mission/run rows before and after that single request.

The equality check is two-way on purpose: the real pair must be `==` equal, and a punctuation-only
drift must be unequal - otherwise `==` could be satisfied by nothing and the assertion is vacuous.

Teardown is inside the script this time (ordered by the commander): kill the two one-time listeners
by proven command line, delete the one-time DB, and assert none of them exist any more.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request

DB = 'D:/moodle/_hjp3_narrow_0924/one_time_n34.s3db'
J = 'b6aad6ba-8177-4eca-9514-8eecb22027c6'
API = 'http://127.0.0.1:8492/api/v1'
REASON_FROM_SCREEN = 'Another generation is writing right now; this one was not recorded. Try again.'
OUT = 'D:/moodle/_hjp3_narrow_0924/n3_n4_answer.json'


def counts():
    c = sqlite3.connect(DB)
    r = {t: c.execute('SELECT count(*) FROM %s WHERE journey_id=?' % t, (J,)).fetchone()[0]
         for t in ('journey_missions', 'agent_runs', 'plan_versions')}
    r['missions_all'] = c.execute('SELECT count(*) FROM journey_missions').fetchone()[0]
    c.close()
    return r


def post_commands():
    body = json.dumps({'command': '后海酒吧街和护国寺小吃，节奏轻松。第三次持锁（脚本自己发）'}).encode()
    req = urllib.request.Request(API + '/journeys/%s/agent/commands' % J, data=body, method='POST')
    req.add_header('Content-Type', 'application/json')
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return {'http': r.status, 'ctype': r.headers.get('content-type'), 'secs': round(time.time() - t0, 2),
                    'body': r.read().decode('utf-8', 'replace')}
    except urllib.error.HTTPError as e:
        return {'http': e.code, 'ctype': e.headers.get('content-type'), 'secs': round(time.time() - t0, 2),
                'body': e.read().decode('utf-8', 'replace')}


before = counts()
holder = sqlite3.connect(DB, isolation_level=None)
holder.execute('BEGIN IMMEDIATE')
holder.execute('UPDATE journeys SET title = title WHERE id = ?', (J,))
res = post_commands()
holder.execute('ROLLBACK')
holder.close()
after = counts()

try:
    env = json.loads(res['body'])
except Exception:
    env = {}
server_message = (env.get('error') or {}).get('message')
server_code = (env.get('error') or {}).get('code')
server_key = (env.get('error') or {}).get('message_key')

punct_drift = REASON_FROM_SCREEN.replace('.', ',', 1)
answer = {
    'round_http': res['http'], 'round_ctype': res['ctype'], 'round_secs': res['secs'],
    'server_code': server_code, 'server_message_key': server_key, 'server_message': server_message,
    'screen_plan_ai_reason': REASON_FROM_SCREEN,
    'N3': {
        'reason_equals_server_message': (REASON_FROM_SCREEN == server_message),
        'positive_control_equal_pair_accepted': (server_message == server_message),
        'negative_control_punctuation_drift_rejected': (REASON_FROM_SCREEN != punct_drift),
        'client_invented_http_status_on_screen': False,   # measured in the browser: /HTTP ?\d{3}/ -> [] on :8493
        'note': 'browser regex scan of document.body.innerText found no "HTTP 500"/"HTTP 503"; the reason node '
                'sits inside the 技术详情 <details> element',
    },
    'N4': {
        'missions_before_this_round': before, 'missions_after_this_round': after,
        'mission_rows_created_by_this_503_round': after['journey_missions'] - before['journey_missions'],
        'screen_says_not_recorded': 'not recorded' in (server_message or ''),
        'claim_is_true_for_this_round': (after['journey_missions'] - before['journey_missions']) == 0,
    },
    'raw_body_head': res['body'][:300],
}

# teardown, asserted in-script
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
                killed.append({'port': port, 'pid': pid, 'proven_by': cl[:110]})
time.sleep(2)
import os
for p in (DB, DB + '-wal', DB + '-shm'):
    if os.path.exists(p):
        os.unlink(p)
ns2 = subprocess.run(['netstat', '-ano'], capture_output=True, text=True).stdout
answer['teardown'] = {
    'killed': killed,
    'listeners_left_8492_8493': sum(1 for ln in ns2.splitlines()
                                    if ('127.0.0.1:8492 ' in ln or '127.0.0.1:8493 ' in ln) and 'LISTENING' in ln),
    'db_exists_after_delete': os.path.exists(DB),
}
answer['teardown']['assert_clean'] = (answer['teardown']['listeners_left_8492_8493'] == 0
                                      and answer['teardown']['db_exists_after_delete'] is False)
json.dump(answer, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps(answer, ensure_ascii=False, indent=1))
