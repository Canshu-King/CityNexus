"""ORD-0291: a selective origin - answer every READ, swallow every WRITE.

Why this arm exists: on the write-lock rig the server always answers the parked POST at ~32.3 s (SQLite
busy_timeout 30 s), so a future write deadline set ABOVE busy_timeout - which Q36=1 now requires - can never
be told apart from "no deadline at all" by looking at a duration.  Against an origin that answers the boot
reads (so the hub renders and the traveller really can press 开始规划) and then goes silent for the POST, the
client timer is the only thing that can ever end the wait.  That is the rig B needs after 0281 ships.

  stage serve <port> <backend_port>   - run it until stop.flag appears next to this file
Nothing here touches the product: the backend is a read-only pass-through target on MY one-time DB.
"""
from __future__ import annotations

import json
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = pathlib.Path('D:/moodle/_hjp3_0291_0925')
HELD = []
SILENCE = threading.Event()
STATS = {'answered': 0, 'silenced': 0, 'silenced_paths': []}


class H(BaseHTTPRequestHandler):
    backend_port = 8493

    def log_message(self, *a):
        pass

    def _proxy(self):
        if self.command in ('POST', 'PUT', 'PATCH', 'DELETE'):
            length = int(self.headers.get('content-length') or 0)
            if length:
                self.rfile.read(length)
            STATS['silenced'] += 1
            if len(STATS['silenced_paths']) < 20:
                STATS['silenced_paths'].append(self.path)
            STATS.setdefault('silenced_log', []).append({'path': self.path, 'method': self.command,
                                                         'at': time.strftime('%H:%M:%S')})
            c = self.connection           # accept the connection and never write a response
            HELD.append(c)
            SILENCE.wait(timeout=600)     # hold the handler thread, or returning would CLOSE the socket and
            return                        # http-proxy would answer the browser with its own 500
        req = urllib.request.Request('http://127.0.0.1:%d%s' % (self.backend_port, self.path),
                                     method=self.command)
        for k in ('Accept', 'Accept-Language', 'Content-Type'):
            if self.headers.get(k):
                req.add_header(k, self.headers[k])
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
                self.send_response(r.status)
                for k, v in r.getheaders():
                    if k.lower() not in ('transfer-encoding', 'connection', 'content-length'):
                        self.send_header(k, v)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                STATS['answered'] += 1
        except urllib.error.HTTPError as e:
            body = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', e.headers.get('content-type') or 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            STATS['answered'] += 1
        except Exception as e:  # noqa: BLE001
            body = json.dumps({'error': {'code': 'PROXY_FAIL', 'message': str(e)[:120]}}).encode()
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    do_GET = do_HEAD = do_OPTIONS = do_POST = do_PUT = do_PATCH = do_DELETE = _proxy


def do_serve(port: int, backend_port: int):
    H.backend_port = backend_port
    srv = ThreadingHTTPServer(('127.0.0.1', port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    probe = urllib.request.Request('http://127.0.0.1:%d/api/v1/health' % port, method='GET')
    with urllib.request.urlopen(probe, timeout=60) as r:
        health = r.status
    state = {'port': port, 'backend_port': backend_port, 'pid': __import__('os').getpid(),
             'health_probe_via_origin': health, 'started_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
             'note': 'reads pass through to %d, writes are accepted and never answered' % backend_port}
    (BASE / ('selective_origin_%d.json' % port)).write_text(json.dumps(state, ensure_ascii=False, indent=1),
                                                            encoding='utf-8')
    print(json.dumps(state, ensure_ascii=False), flush=True)
    flag = BASE / ('stop_origin_%d.flag' % port)
    if flag.exists():
        flag.unlink()
    while not flag.exists():
        time.sleep(1)
        (BASE / ('selective_origin_%d_stats.json' % port)).write_text(
            json.dumps(STATS, ensure_ascii=False, indent=1), encoding='utf-8')
    flag.unlink()
    SILENCE.set()
    srv.shutdown()


if __name__ == '__main__':
    if sys.argv[1] == 'serve':
        do_serve(int(sys.argv[2]), int(sys.argv[3]))
    else:
        raise SystemExit('unknown stage')
