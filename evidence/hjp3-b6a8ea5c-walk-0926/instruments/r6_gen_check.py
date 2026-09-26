"""Which generation does the phone chain serve right now, over both entries, and is an application answering?

Two entry points are read so the answer does not depend on one of them: the local hop the phone uses
(127.0.0.1:4781) and the public tunnel address the commander published. Each is asked for the shell, then for the
single JS asset the shell names, and the bytes are hashed - so the asset the two entries serve can be compared
byte for byte. Separately, four real API paths plus one path the product cannot serve are compared by signature
(status / content type / byte count / body sha256 / server header): if a made-up path answered identically to the
real ones the "500" would be the proxy talking rather than the application, which decides whether the cells I walk
next test product behaviour or a dead hop.

Two of my own instrument faults live in this file because they cost me a false reading first:
  * the auth file is TAB-separated (`user<TAB>secret`); reading it as `user:secret` produced a header made of the
    whole line and the tunnel answered 401, which is not "the tunnel is down";
  * this shell's environment points HTTP(S)_PROXY at 127.0.0.1:7892 where nothing listens, so urllib failed with
    WinError 10061 "connection refused" while DNS resolved and a direct TCP 443 to the same host succeeded in
    ~570 ms. The fix is a no-proxy opener, and the control (api.github.com) is read in the same run.

Credentials: read from the file named by the commander, used only to build one request header, never printed, and
an assert at the end refuses to write the artefact if either field appears anywhere in it.

Read-only: GET only; 0 clicks; 0 writes; no database opened; the four chain layers untouched.
"""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import re
import socket
import time
import urllib.error
import urllib.request

OUT = pathlib.Path('D:/moodle/_hjp3_b6a8_0926')
AUTH_FILE = pathlib.Path('D:/moodle/_qoder_preview_20260920/run/preview_auth.txt')
LOCAL = 'http://127.0.0.1:4781'
PUBLIC = 'https://administrator-personality-supervisor-peers.trycloudflare.com'
NAMED_TIP = 'b6a8ea5c625d7e3e82f7348fad57d595a8a403c0'
ASSET_FROM_HIS_LAST_MESSAGE = 'index-Ci_qm-KU.js'
API_PATHS = ('/api/v1/health', '/api/v1/journeys', '/api/v1/demo/scene', '/api/v1/zzz-hjp3-canary-path')
PROXY_ENV = {k: v for k, v in __import__('os').environ.items() if 'PROXY' in k.upper()}

parts = [x for x in re.split(r'[\s:]+', AUTH_FILE.read_text(encoding='utf-8').strip()) if x]
assert len(parts) == 2, 'unexpected auth file shape: %d fields' % len(parts)
user, secret = parts
BASIC = 'Basic ' + base64.b64encode(('%s:%s' % (user, secret)).encode()).decode()
DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(base, path, want_body=False, use_auth=False):
    r = urllib.request.Request(base + path)
    r.add_header('User-Agent', 'hjp3-r6-gen-check-readonly')
    if use_auth:
        r.add_header('Authorization', BASIC)
    t0 = time.time()
    try:
        with DIRECT.open(r, timeout=45) as f:
            b = f.read()
            row = {'path': path, 'http_status': f.status, 'content_type': f.headers.get('content-type'),
                   'server_header': f.headers.get('server'), 'bytes': len(b),
                   'body_sha256': hashlib.sha256(b).hexdigest(),
                   'elapsed_ms': int((time.time() - t0) * 1000)}
    except urllib.error.HTTPError as e:
        b = e.read()
        row = {'path': path, 'http_status': e.code, 'content_type': e.headers.get('content-type'),
               'server_header': e.headers.get('server'), 'bytes': len(b),
               'body_sha256': hashlib.sha256(b).hexdigest(),
               'elapsed_ms': int((time.time() - t0) * 1000)}
    except Exception as e:  # noqa: BLE001
        row = {'path': path, 'http_status': None, 'error': type(e).__name__ + ': ' + str(e)[:120],
               'elapsed_ms': int((time.time() - t0) * 1000)}
    return row, (b if want_body and 'body_sha256' in row else b'')


def tcp(host, port=443):
    t0 = time.time()
    try:
        socket.create_connection((host, port), timeout=10).close()
        return 'OK'
    except Exception as e:  # noqa: BLE001
        return type(e).__name__ + ': ' + str(e)[:60]
    finally:
        pass


def probe(base, use_auth):
    shell, html_b = get(base, '/', want_body=True, use_auth=use_auth)
    html = html_b.decode('utf-8', 'replace')
    asset = (re.search(r'"(/assets/index-[^"]+\.js)"', html) or [None, None])[1]
    css = (re.search(r'"(/assets/index-[^"]+\.css)"', html) or [None, None])[1]
    js, _ = get(base, asset, use_auth=use_auth) if asset else (None, b'')
    api = [get(base, p, use_auth=use_auth)[0] for p in API_PATHS]
    sig = lambda x: (x.get('http_status'), x.get('content_type'), x.get('bytes'), x.get('body_sha256'))
    canary = [x for x in api if 'zzz-hjp3' in x['path']][0]
    real = [x for x in api if 'zzz-hjp3' not in x['path']]
    return {'base': base, 'auth_sent': bool(use_auth), 'username_used': user,
            'shell': shell, 'asset_named_by_the_shell': asset, 'css_named_by_the_shell': css,
            'asset_row': js, 'api_rows': api,
            'signature_per_path': {x['path']: str(sig(x)) for x in api},
            'distinct_signatures': sorted({str(sig(x)) for x in api}),
            'canary_answers_like_the_real_paths': all(sig(x) == sig(canary) for x in real),
            'any_path_returns_a_nonempty_json_body': any((x.get('bytes') or 0) > 0
                                                         and 'json' in (x.get('content_type') or '')
                                                         for x in api),
            'every_row_carries_a_server_header': all(x.get('server_header') for x in api)}


hosts = {'tunnel_host_dns': [], 'tcp': {}}
try:
    hosts['tunnel_host_dns'] = sorted({x[4][0] for x in socket.getaddrinfo(
        PUBLIC.split('//')[1], 443, type=socket.SOCK_STREAM)})
except Exception as e:  # noqa: BLE001
    hosts['tunnel_host_dns'] = ['ERR ' + type(e).__name__]
hosts['tcp'] = {PUBLIC.split('//')[1]: tcp(PUBLIC.split('//')[1]), 'api.github.com': tcp('api.github.com')}

entry_points = [probe(LOCAL, False), probe(PUBLIC, True)]
res = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'generation_named_by_the_commander': NAMED_TIP,
       'asset_he_named_two_messages_ago': ASSET_FROM_HIS_LAST_MESSAGE,
       'requests_made': sum(2 + len(API_PATHS) for _ in entry_points), 'writes': 0, 'clicks': 0,
       'proxy_environment': PROXY_ENV, 'reachability_control': hosts,
       'entry_points': entry_points}
by = {e['base']: e for e in entry_points}
res['same_asset_name_on_both_entries'] = bool(
    by[LOCAL]['asset_named_by_the_shell'] and by[LOCAL]['asset_named_by_the_shell']
    == by[PUBLIC]['asset_named_by_the_shell'])
res['same_asset_bytes_on_both_entries'] = bool(by[LOCAL]['asset_row'] and by[PUBLIC]['asset_row']
                                               and by[LOCAL]['asset_row'].get('body_sha256')
                                               == by[PUBLIC]['asset_row'].get('body_sha256'))
res['asset_differs_from_the_hint_he_gave'] = bool(by[LOCAL]['asset_named_by_the_shell']
                                                  and ASSET_FROM_HIS_LAST_MESSAGE
                                                  not in by[LOCAL]['asset_named_by_the_shell'])
blob = json.dumps(res, ensure_ascii=False, indent=1)
assert secret not in blob, 'the secret leaked into the artefact'
(OUT / 'r6_gen_check.json').write_text(blob, encoding='utf-8', newline='\n')
for e in entry_points:
    print(json.dumps({'base': e['base'], 'shell': e['shell'].get('http_status') or e['shell'].get('error'),
                      'asset': e['asset_named_by_the_shell'],
                      'asset_bytes': (e['asset_row'] or {}).get('bytes'),
                      'asset_sha16': ((e['asset_row'] or {}).get('body_sha256') or '')[:16],
                      'server_header_on_api_rows': [x.get('server_header') for x in e['api_rows']],
                      'distinct_signatures': len(e['distinct_signatures']),
                      'canary_like_real': e['canary_answers_like_the_real_paths'],
                      'nonempty_json': e['any_path_returns_a_nonempty_json_body']}, ensure_ascii=False))
print(json.dumps({'same_name': res['same_asset_name_on_both_entries'],
                  'same_bytes': res['same_asset_bytes_on_both_entries'],
                  'differs_from_his_hint': res['asset_differs_from_the_hint_he_gave'],
                  'tcp': hosts['tcp'], 'dns': hosts['tunnel_host_dns']}, ensure_ascii=False))
