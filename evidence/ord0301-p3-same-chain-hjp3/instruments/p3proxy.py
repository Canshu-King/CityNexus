"""ORD-0301 pass 3: the pairing proxy, revised under a NEW name (CMDR-0925-2128 - instrument paths are
never rewritten; `c2proxy.py` stays on the branch exactly as published).

What the commander asked of this pass, verbatim in effect:
  (2) "把'服务器侧那一发'与'屏上那一发'改成同一代理链路里取" - so BOTH readings below are taken from the one
      hop this request really traversed: the audit line is written by this process, for this request, and the
      same id rides back in `X-HJP3-Pair`, which the page's own Response and the browser's own network stack
      then report. There is no second probe of the backend anywhere in this batch.
  (3) "非 JSON 正文与带 envelope 的 4xx 分开列" - so every record now carries the answer's BODY CLASS as a
      measurement (`body_parses_as_json`, `top_level_keys`, `content_type`), computed here from the bytes this
      hop held, instead of being inferred from the status code.

Two ways an answer can be produced, and the record names which one it was:
  reached_upstream=True                  the product itself rendered those bytes;
  answered_by='instrument_origin_per_spec'  I rendered them, the product was never asked.
The `mutate_extra_key` mode is a third thing and is disclosed as such: the request leaves the page untouched,
this hop adds one forbidden key to the JSON body, and the ANSWER is still the product's own envelope - so a
real 4xx envelope can be paired to a real screen without inventing its bytes.
"""
from __future__ import annotations

import http.client
import json
import os
import pathlib
import sqlite3
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM_HOST = '127.0.0.1'
UPSTREAM_PORT = int(os.environ['P3_UPSTREAM_PORT'])
LOG = pathlib.Path(os.environ['P3_PAIR_LOG'])
MODE = os.environ.get('P3_PROXY_MODE', 'pass')   # pass | mutate_extra_key | answer_spec | lock_behind_hop | abort_on_write
LOCK_DB = pathlib.Path(os.environ['P3_LOCK_DB']) if os.environ.get('P3_LOCK_DB') else None
LOCK_HOLD_SECS = int(os.environ.get('P3_LOCK_HOLD_SECS', '40'))
SPEC = json.loads(os.environ['P3_ANSWER_SPEC']) if os.environ.get('P3_ANSWER_SPEC') else None
MUTATE_KEY = os.environ.get('P3_MUTATE_KEY', 'p3_forbidden_probe')
WRITE_SUFFIX = '/agent/commands'
LOCK = threading.Lock()


def body_class(data, content_type):
    """The class is READ from the bytes, and the content-type header is reported next to it so a
    text/plain body carrying JSON would show up as what it is rather than being smoothed over."""
    parsed = None
    keys = None
    try:
        v = json.loads(data.decode('utf-8'))
        parsed = True
        keys = sorted(v.keys())[:8] if isinstance(v, dict) else type(v).__name__
    except Exception:  # noqa: BLE001
        parsed = False
    return {'body_parses_as_json': parsed, 'top_level_keys': keys,
            'content_type': content_type, 'bytes': len(data)}


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _audit(self, rec):
        rec['at'] = time.strftime('%Y-%m-%dT%H:%M:%S') + ('%03d' % (time.time() * 1000 % 1000))
        with LOCK:
            with LOG.open('a', encoding='utf-8') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + chr(10))

    def _answer(self, pair_id, status, content_type, data, reason=None):
        self.send_response(status, reason or self.responses.get(status, ('',))[0] or 'Error')
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-HJP3-Pair', pair_id)
        self.end_headers()
        self.wfile.write(data)

    def _handle(self, method):
        pair_id = 'hjp3p3-' + uuid.uuid4().hex[:16]
        length = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(length) if length else b''
        path = self.path
        is_write = method == 'POST' and path.endswith(WRITE_SUFFIX)
        rec = {'pair_id': pair_id, 'method': method, 'path': path, 'mode': MODE,
               'targeted_leg': bool(is_write), 'request_bytes': len(body),
               'request_body_head': body[:120].decode('utf-8', 'replace'),
               'proxy_seen_at': time.strftime('%H:%M:%S')}

        if MODE == 'abort_on_write' and is_write:
            rec.update({'reached_upstream': False, 'answered_by': 'nobody',
                        'why': 'this hop refused the leg before the product; the page sees a transport death'})
            self._audit(rec)
            self.send_error(502, 'aborted by instrument')
            return

        if MODE == 'answer_spec' and is_write and SPEC:
            data = (SPEC['body'].encode('utf-8') if isinstance(SPEC['body'], str)
                    else json.dumps(SPEC['body'], ensure_ascii=False).encode('utf-8'))
            rec.update({'reached_upstream': False, 'answered_by': 'instrument_origin_per_spec',
                        'spec_name': SPEC.get('name'), 'upstream_status': SPEC['status'],
                        'upstream_elapsed_ms': 0})
            rec.update(body_class(data, SPEC['content_type']))
            rec['body_head'] = data[:120].decode('utf-8', 'replace')
            self._audit(rec)
            self._answer(pair_id, SPEC['status'], SPEC['content_type'], data, SPEC.get('reason'))
            return

        hop_in = dict(self.headers)
        # The face in front of me is `vite preview`, which forwards the browser's headers in LOWER CASE.
        # Popping 'Content-Length' by its browser spelling therefore removed nothing, and re-adding my own
        # length put two Content-Length headers on one request with two different values - h11 answered 400
        # "Invalid HTTP request received." in 1 ms. A pilot arm measured exactly that (see runs_excluded),
        # so the hop now drops every case variant by lowercase name and states what it changed.
        drop = ('host', 'content-length', 'connection', 'accept-encoding', 'transfer-encoding',
                'keep-alive', 'upgrade', 'proxy-connection', 'te', 'expect')
        hop = {k: v for k, v in hop_in.items() if k.lower() not in drop}
        dropped = sorted({k for k in hop_in if k.lower() in drop})
        hop['Accept-Encoding'] = 'identity'
        hop['Host'] = '%s:%d' % (UPSTREAM_HOST, UPSTREAM_PORT)
        sent = body
        if MODE == 'mutate_extra_key' and is_write:
            obj = json.loads(body.decode('utf-8'))
            before = sorted(obj.keys())
            obj[MUTATE_KEY] = 1
            sent = json.dumps(obj, ensure_ascii=False).encode('utf-8')
            rec['request_mutation'] = {
                'added_key': MUTATE_KEY, 'keys_before': before, 'keys_after': sorted(obj.keys()),
                'request_bytes_before': len(body), 'request_bytes_after': len(sent),
                'sha256_before': hashlib_sha(body), 'sha256_after': hashlib_sha(sent),
                'who_sent_what': 'the page sent the untouched body; this hop added the key, and the product '
                                'answered with its own envelope'}
        hop['Content-Length'] = str(len(sent))
        rec['hop_headers'] = {'dropped_case_insensitive': dropped,
                              'set_by_this_hop': ['Accept-Encoding', 'Host', 'Content-Length'],
                              'count_forwarded': len(hop)}
        # `lock_behind_hop`: the two arms that need a REAL contended 500 cannot afford a race. The earlier
        # recipe (a separate process grabs the write lock when it sees a flag file) died twice: the page's
        # submit button is `aria-disabled` for a moment while the hub re-reads under the lock, Playwright
        # waits for an enabled control, and the leg is never sent (both first attempts are in
        # runs_excluded). Here the SAME process that carries the leg owns the contention, so ordering is
        # not a schedule outcome: take the write lock, prove a second writer is refused, forward, release.
        hop_lock = None
        holder = None
        if MODE == 'lock_behind_hop' and is_write and LOCK_DB:
            hop_lock = {'db': str(LOCK_DB), 'hold_seconds_planned': LOCK_HOLD_SECS,
                        'acquired': False, 'rows_touched': None, 'second_writer_refused': None}
            t_acquire = time.time()
            holder = None
            while time.time() - t_acquire < 20:
                try:
                    holder = sqlite3.connect(str(LOCK_DB), timeout=1, isolation_level=None)
                    holder.execute('BEGIN IMMEDIATE')
                    holder.execute('UPDATE journeys SET title = title')
                    hop_lock['rows_touched'] = holder.execute('SELECT changes()').fetchone()[0]
                    hop_lock['acquired'] = True
                    hop_lock['acquired_after_ms'] = int((time.time() - t_acquire) * 1000)
                    break
                except Exception as e:  # noqa: BLE001
                    hop_lock['acquire_error'] = str(e)[:90]
                    try:
                        holder.close()
                    except Exception:  # noqa: BLE001
                        pass
                    holder = None
                    time.sleep(0.5)
            if hop_lock['acquired']:
                probe = None
                try:
                    probe = sqlite3.connect(str(LOCK_DB), timeout=0, isolation_level=None)
                    probe.execute('BEGIN IMMEDIATE')
                    hop_lock['second_writer_refused'] = False
                    probe.execute('ROLLBACK')
                except Exception:  # noqa: BLE001
                    hop_lock['second_writer_refused'] = True
                finally:
                    try:
                        probe.close()
                    except Exception:  # noqa: BLE001
                        pass
            rec['hop_lock'] = hop_lock
        t0 = time.time()
        try:
            conn = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=180)
            conn.request(method, path, body=sent, headers=hop)
            res = conn.getresponse()
            data = res.read()
            uh = dict(res.getheaders())
            conn.close()
        except Exception as e:  # noqa: BLE001
            rec.update({'reached_upstream': False, 'answered_by': 'nobody',
                        'upstream_error': str(e)[:160]})
            if hop_lock:
                hop_lock['release'] = _release(holder, t0)
            self._audit(rec)
            self.send_error(502, 'upstream failed')
            return
        if hop_lock:
            hop_lock['release'] = _release(holder, t0)
        ct = uh.get('Content-Type') or uh.get('content-type')
        rec.update({'reached_upstream': True, 'answered_by': 'product', 'upstream_status': res.status,
                    'upstream_elapsed_ms': int((time.time() - t0) * 1000)})
        rec.update(body_class(data, ct))
        rec['body_head'] = data[:160].decode('utf-8', 'replace')
        self._audit(rec)
        out = {k: v for k, v in uh.items()
               if k.lower() not in ('transfer-encoding', 'content-length', 'connection', 'content-type')}
        self._answer(pair_id, res.status, ct or 'application/octet-stream', data, res.reason)

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


def _release(holder, t0):
    """Roll the hop's own write transaction back and report how long the contention really lasted -
    the number the arm's 500 timing is read against, not a planned number."""
    if holder is None:
        return {'rolled_back': False, 'why': 'no holder'}
    held_ms = int((time.time() - t0) * 1000)
    out = {'held_ms_around_the_forward': held_ms}
    try:
        holder.execute('ROLLBACK')
        out['rolled_back'] = True
    except Exception as e:  # noqa: BLE001
        out['rolled_back'] = False
        out['rollback_error'] = str(e)[:90]
    try:
        holder.close()
    except Exception:  # noqa: BLE001
        pass
    return out


def hashlib_sha(d):
    import hashlib
    return hashlib.sha256(d).hexdigest()


if __name__ == '__main__':
    port = int(sys.argv[1])
    LOG.parent.mkdir(exist_ok=True)
    print('p3 pairing proxy on %d -> %s:%d mode=%s spec=%s log=%s'
          % (port, UPSTREAM_HOST, UPSTREAM_PORT, MODE, (SPEC or {}).get('name'), LOG), flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
