"""ORD-0301: a scriptable outcome origin - the write leg answers whatever outcome the row asks for.

Why this exists: the product's own `agent/commands` path can only produce two of the five outcome
classes the order asks for (a contentless 500 under lock contention, and refused when the backend is
down).  To put 502/503/504, a 500 that *carries* the product's own envelope, a reset and a silent leg
on the same table, one arm has to control the bytes the browser receives while everything else on the
page stays real.  Reads pass through to MY backend so the hub still renders and the traveller really
can press 开始规划; only the POST's fate is manufactured.

Honesty rules this file obeys:
  - every request is logged with the policy stamp that served it, so a row's server-side reading is
    attributable to a declared configuration, not to my memory;
  - the envelope body is a file captured from a REAL product answer (written by the rig), never typed;
  - nothing here rewrites the product: the backend behind the pass-through is a uvicorn on my own
    one-time database.

  stage serve <port> <backend_port>          - runs until stop_origin_<port>.flag appears
"""
from __future__ import annotations

import json
import pathlib
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = pathlib.Path('D:/moodle/_hjp3_0301_0925')
POLICY = BASE / 'policy.json'
LOCK = threading.Lock()
STATS = {'answered_reads': 0, 'manufactured_writes': 0, 'held': 0, 'reset': 0, 'short_body': 0}
HELD = []
SILENCE = threading.Event()


def policy():
    try:
        return json.loads(POLICY.read_text(encoding='utf-8'))
    except Exception as e:  # noqa: BLE001
        return {'stamp': 'POLICY_UNREADABLE', 'error': str(e)[:160]}


def read_body_bytes(spec):
    """Body comes from a file on disk (captured real bytes) or a literal - never hand-typed here."""
    if not spec:
        return b''
    if isinstance(spec, dict) and spec.get('file'):
        return (BASE / spec['file']).read_bytes()
    return str(spec).encode('utf-8')


class H(BaseHTTPRequestHandler):
    backend_port = 8561
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _log(self, rec):
        with LOCK:
            STATS.setdefault('requests', []).append(rec)
            with (BASE / ('origin_%d_log.jsonl' % self.server.server_address[1])).open('a', encoding='utf-8') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')

    def _write(self):
        pol = policy()
        cfg = pol.get('write', {})
        length = int(self.headers.get('content-length') or 0)
        req_body = self.rfile.read(length) if length else b''
        stamp = pol.get('stamp')
        mode = cfg.get('mode', 'answer')
        rec = {'at': time.strftime('%H:%M:%S'), 'stamp': stamp, 'path': self.path, 'method': self.command,
               'leg': 'write', 'mode': mode, 'request_bytes': len(req_body),
               'status': None, 'content_type': cfg.get('content_type'), 'response_bytes': None,
               'delay_ms': cfg.get('delay_ms')}
        if mode == 'silent':
            STATS['held'] += 1
            HELD.append(self.connection)
            rec['note'] = 'accepted, never answered'
            self._log(rec)
            SILENCE.wait(timeout=cfg.get('hold_seconds', 300))
            return
        if mode == 'reset':
            STATS['reset'] += 1
            rec['note'] = 'request read, socket closed with no response bytes'
            self._log(rec)
            try:
                self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.connection.close()
            except Exception:  # noqa: BLE001
                pass
            self.close_connection = True
            return
        body = read_body_bytes(cfg.get('body'))
        status = int(cfg.get('status', 500))
        delay = int(cfg.get('delay_ms') or 0)
        if delay:
            time.sleep(delay / 1000.0)
        self.send_response(status)
        self.send_header('Content-Type', cfg.get('content_type', 'application/json'))
        declared = int(cfg.get('declared_content_length', len(body)))
        self.send_header('Content-Length', str(declared))
        self.end_headers()
        payload = body[: int(cfg.get('truncate_to', len(body)))]
        self.wfile.write(payload)
        STATS['manufactured_writes'] += 1
        rec.update({'status': status, 'declared_content_length': declared, 'bytes_written': len(payload),
                    'body_sha256_12': __import__('hashlib').sha256(body).hexdigest()[:12]})
        if declared != len(payload):
            STATS['short_body'] += 1
            rec['short_body'] = True
        self._log(rec)

    def _read(self):
        pol = policy()
        cfg = pol.get('read', {})
        mode = cfg.get('mode', 'proxy')
        stamp = pol.get('stamp')
        rec = {'at': time.strftime('%H:%M:%S'), 'stamp': stamp, 'path': self.path, 'method': self.command,
               'leg': 'read', 'mode': mode, 'status': None}
        if mode == 'silent':
            STATS['held'] += 1
            HELD.append(self.connection)
            self._log(rec)
            SILENCE.wait(timeout=cfg.get('hold_seconds', 300))
            return
        if int(cfg.get('delay_ms') or 0):
            time.sleep(int(cfg['delay_ms']) / 1000.0)
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
                rec.update({'status': r.status, 'bytes': len(body)})
                STATS['answered_reads'] += 1
        except urllib.error.HTTPError as e:
            body = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', e.headers.get('content-type') or 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            rec.update({'status': e.code, 'bytes': len(body), 'from_backend': True})
            STATS['answered_reads'] += 1
        except Exception as e:  # noqa: BLE001
            rec['error'] = str(e)[:160]
        self._log(rec)

    do_POST = do_PUT = do_PATCH = do_DELETE = _write
    do_GET = do_HEAD = do_OPTIONS = _read


def do_serve(port, backend_port):
    H.backend_port = int(backend_port)
    srv = ThreadingHTTPServer(('127.0.0.1', port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with urllib.request.urlopen('http://127.0.0.1:%d/api/v1/health' % port, timeout=60) as r:
        health = r.status
    state = {'port': port, 'backend_port': int(backend_port), 'pid': __import__('os').getpid(),
             'health_probe_via_origin': health, 'policy_file': str(POLICY),
             'started_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
             'note': 'reads pass through to %d; the write leg answers whatever policy.json declares'
                     % int(backend_port)}
    (BASE / ('outcome_origin_%d.json' % port)).write_text(json.dumps(state, ensure_ascii=False, indent=1),
                                                          encoding='utf-8')
    print(json.dumps(state, ensure_ascii=False), flush=True)
    flag = BASE / ('stop_origin_%d.flag' % port)
    if flag.exists():
        flag.unlink()
    while not flag.exists():
        time.sleep(1)
        (BASE / ('outcome_origin_%d_stats.json' % port)).write_text(
            json.dumps(STATS, ensure_ascii=False, indent=1), encoding='utf-8')
    flag.unlink()
    SILENCE.set()
    srv.shutdown()


if __name__ == '__main__':
    if sys.argv[1] == 'serve':
        do_serve(int(sys.argv[2]), int(sys.argv[3]))
    else:
        raise SystemExit('unknown stage')
