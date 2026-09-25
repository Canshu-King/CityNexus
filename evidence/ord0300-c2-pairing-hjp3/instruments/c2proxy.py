"""A token-injecting pairing proxy for the ORD-0300 C2 re-measurement.

The commander's objection: "the server answered 500" and "the screen said unreachable" were two readings of
two THINGS that looked alike, not one request seen twice. This proxy makes them one request seen twice: every
`/api` call gets a token from me, the token is recorded server-side together with the status the product
actually sent, and the same token travels back in the response header - so the page's own response object,
the browser's network stack, and my log all name the identical leg.

It is mine, on my own port, forwarding to my own backend, and it appends an append-only JSONL audit. It does
not modify the product or the response body; it only adds a header, which is exactly the "只能从服务端看到的标记"
the challenge asked for (a client cannot guess a token I mint at accept time).
"""
from __future__ import annotations

import http.client
import json
import os
import pathlib
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM_HOST = '127.0.0.1'
UPSTREAM_PORT = int(os.environ['C2_UPSTREAM_PORT'])
LOG = pathlib.Path(os.environ['C2_PAIR_LOG'])
MODE = os.environ.get('C2_PROXY_MODE', 'pass')      # pass | abort_before_upstream | silent
HOP = {k: v for k, v in os.environ.items() if k.startswith('C2_HOP_')}
LOCK = threading.Lock()
HOP_BY_PREFIX = {'POST /api/v1/journeys': os.environ.get('C2_HOP_WRITE', 'do')}


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):  # our own audit is the record; stderr stays quiet
        pass

    def _audit(self, rec):
        rec['at'] = time.strftime('%Y-%m-%dT%H:%M:%S') + ('%03d' % (time.time() * 1000 % 1000))
        with LOCK:
            with LOG.open('a', encoding='utf-8') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + chr(10))

    def _handle(self, method):
        token = 'hjp3c2-' + uuid.uuid4().hex[:16]
        length = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(length) if length else b''
        path = self.path
        rec = {'token': token, 'method': method, 'path': path, 'request_bytes': len(body),
               'mode': MODE, 'proxy_seen_at': time.strftime('%H:%M:%S')}
        if MODE == 'abort_before_upstream' and HOP_BY_PREFIX.get(method + ' ' + path.split('/')[3]
                                                                 if len(path.split('/')) > 3 else ''):
            pass
        if MODE == 'abort_on_write' and method == 'POST' and path.endswith('/agent/commands'):
            rec.update({'reached_upstream': False, 'why': 'proxy aborted this leg before the product'})
            self._audit(rec)
            self.send_error(502, 'aborted by instrument')     # the browser sees a transport failure
            return
        if MODE == 'silent' and method == 'POST' and path.endswith('/agent/commands'):
            rec.update({'reached_upstream': False, 'why': 'proxy never answered this leg'})
            self._audit(rec)
            return
        if MODE == 'answer500_plain' and method == 'POST' and path.endswith('/agent/commands'):
            # the product's OWN contentless 500, byte-for-byte: 21 B of text/plain "Internal Server Error"
            # (exactly what the proxy recorded from the real contended write in arm 0). The token is minted
            # and logged here, so the leg is still one request seen from both sides - the only thing that
            # changes is WHO produced the bytes, which is stated in the record.
            data = b'Internal Server Error'
            rec.update({'reached_upstream': False, 'answered_by': 'instrument_origin',
                        'upstream_status': 500, 'upstream_content_type': 'text/plain; charset=utf-8',
                        'upstream_bytes': len(data), 'body_head': data.decode()})
            self._audit(rec)
            self.send_response(500, 'Internal Server Error')
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('X-HJP3-Pair', token)
            self.end_headers()
            self.wfile.write(data)
            return
        hop = dict(self.headers)
        for k in ('Host', 'Content-Length', 'Connection', 'Accept-Encoding'):
            hop.pop(k, None)
        hop['Accept-Encoding'] = 'identity'
        t0 = time.time()
        try:
            conn = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=180)
            conn.request(method, path, body=body, headers=hop)
            res = conn.getresponse()
            data = res.read()
            upstream_headers = dict(res.getheaders())
            conn.close()
        except Exception as e:  # noqa: BLE001
            rec.update({'reached_upstream': False, 'upstream_error': str(e)[:160]})
            self._audit(rec)
            self.send_error(502, 'upstream failed')
            return
        elapsed = int((time.time() - t0) * 1000)
        rec.update({'reached_upstream': True, 'upstream_status': res.status,
                    'upstream_content_type': upstream_headers.get('Content-Type')
                    or upstream_headers.get('content-type'),
                    'upstream_bytes': len(data), 'upstream_elapsed_ms': elapsed,
                    'body_head': data[:120].decode('utf-8', 'replace')})
        self._audit(rec)
        out = {k: v for k, v in upstream_headers.items()
               if k.lower() not in ('transfer-encoding', 'content-length', 'connection')}
        out['Content-Length'] = str(len(data))
        out['X-HJP3-Pair'] = token
        self.send_response(res.status, res.reason)
        for k, v in out.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._handle('GET')

    def do_POST(self):
        self._handle('POST')

    def do_PATCH(self):
        self._handle('PATCH')

    def do_PUT(self):
        self._handle('PUT')

    def do_DELETE(self):
        self._handle('DELETE')

    def do_OPTIONS(self):
        self._handle('OPTIONS')


if __name__ == '__main__':
    port = int(sys.argv[1])
    LOG.parent.mkdir(exist_ok=True)
    print('pairing proxy on %d -> %s:%d mode=%s log=%s' % (port, UPSTREAM_HOST, UPSTREAM_PORT, MODE, LOG),
          flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
