"""ORD-0301: name WHO produced the HTTP answer a row reads - the product, my origin, or the vite proxy.

A browser-side 'status 500' is not the same fact when the product never saw the request: with the
upstream port empty, and with my origin closing the socket, the vite preview proxy writes its own
500 / text/plain / 0 B.  This probe asks the same face twice over - once through the browser path
(the arm's own leg record) and once from outside the browser - and prints the headers that tell the
two answerers apart, plus which upstream port is actually listening.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = pathlib.Path('D:/moodle/_hjp3_0301_0925')
STATE = json.loads((BASE / 'o0301_state.json').read_text(encoding='utf-8'))
ORIGIN, BP = 8563, 8561


def listening(port):
    out = subprocess.run(['netstat', '-ano'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return [ln.split()[-1] for ln in out.splitlines()
            if ('127.0.0.1:%d ' % int(port)) in ln and 'LISTENING' in ln]


def ask(url, method, body, timeout):
    req = urllib.request.Request(url, method=method)
    t0 = time.time()
    if body is not None:
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, body.encode() if body else None, timeout=timeout) as r:
            raw = r.read()
            return {'status': r.status, 'content_type': r.headers.get('content-type'),
                    'bytes': len(raw), 'headers': {k.lower(): v for k, v in r.getheaders()
                                                   if k.lower() in ('server', 'date', 'connection',
                                                                    'content-length', 'via', 'x-powered-by')},
                    'body_head': raw[:120].decode('utf-8', 'replace'),
                    'elapsed_ms': int((time.time() - t0) * 1000)}
    except urllib.error.HTTPError as e:
        raw = e.read()
        return {'status': e.code, 'content_type': e.headers.get('content-type'), 'bytes': len(raw),
                'headers': {k.lower(): v for k, v in e.headers.items()
                            if k.lower() in ('server', 'date', 'connection', 'content-length', 'via',
                                             'x-powered-by')},
                'body_head': raw[:120].decode('utf-8', 'replace'),
                'http_error': str(e)[:120],
                'elapsed_ms': int((time.time() - t0) * 1000)}
    except Exception as e:  # noqa: BLE001
        return {'status': None, 'error': type(e).__name__ + ': ' + str(e)[:160],
                'elapsed_ms': int((time.time() - t0) * 1000)}


face_port, stamp, out_file, timeout = int(sys.argv[1]), sys.argv[2], sys.argv[3], float(sys.argv[4])
face = next((f for f in STATE['faces'] if f['port'] == face_port), None)
if face is None:
    raise SystemExit('face %d is not in my state file' % face_port)
upstream = face['upstream_backend_port']
jid = STATE['seed']['journey_id']
is_origin = upstream == ORIGIN
url = 'http://127.0.0.1:%d/api/v1/journeys/%s/%s' % (face_port, jid,
                                                     'agent/commands' if is_origin else 'experience')
out = {'asked': url, 'face_port': face_port, 'face_tag': face['tag'], 'policy_stamp': stamp,
       'method': 'POST' if is_origin else 'GET',
       'why_this_method': ('the controlled face manufactures the POST outcome, so the probe asks the '
                           'same leg the traveller hits'
                           if is_origin else
                           'the real-backend face is probed with a READ so this probe adds no write to '
                           'the product database'),
       'upstream_port': upstream,
       'upstream_listening': bool(listening(upstream)),
       'origin_listening': bool(listening(ORIGIN)),
       'real_backend_listening': bool(listening(BP)),
       'probe': ask(url, 'POST' if is_origin else 'GET',
                    json.dumps({'command': 'ORD-0301 sibling probe'}) if is_origin else None, timeout)}
(BASE / out_file).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(out, ensure_ascii=False)[:900])
