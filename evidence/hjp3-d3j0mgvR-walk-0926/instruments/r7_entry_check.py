"""Entry check for the newest phone generation, persisted instead of printed.

The commander's order gave the tunnel host, the bundle name the home page should name, and one new field on
`/api/v1/health` (`ai_state=DISABLED_BY_OPS`). Those are the three things a later reading has to be bound to, so
they are recorded here with bytes and hashes rather than left in a console: the shell and the named asset are read
over BOTH entries (the phone's own hop and the public tunnel) and compared, and the health payload is reduced to
its field names plus the two AI fields - no other content of any response body is copied out.

Also scanned, from the exact bytes of the served asset: the anchor literals a UI reading has to be able to name
(`journey-link-copy`, `journey-link-message`, `data-cnx-field`), the four journey-link sentences the product can
show, and the inbox route names. That way a claim like "the control exists but sits behind a sub-tab" is a
measurement over bytes, not a memory of clicking.

Read-only GETs; no clicks; no writes; the password is used only as a Basic header and an assert refuses to write
the artefact if it appears anywhere in it.
"""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import re
import time
import urllib.error
import urllib.request

OUT = pathlib.Path('D:/moodle/_hjp3_d3j0_0926')
AUTH = pathlib.Path('D:/moodle/_qoder_preview_20260920/run/preview_auth.txt').read_text(encoding='utf-8').split()
user, secret = AUTH[0], AUTH[1]
BASIC = 'Basic ' + base64.b64encode(('%s:%s' % (user, secret)).encode()).decode()
LOCAL = 'http://127.0.0.1:4781'
PUBLIC = 'https://jets-saints-tomatoes-eric.trycloudflare.com'
NAMED_ASSET = '/assets/index-D3j0mgvR.js'
DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))
LITERALS = ('journey-link-copy', 'journey-link-message', 'journey-link-action', 'data-cnx-field',
            'inbox.copyJourneyLink', 'inbox.journeyLinkCopied', 'inbox.journeyLinkNoJourney',
            'inbox.journeyLinkInsecureContext', 'inbox.journeyLinkClipboardUnavailable',
            'trips-tab-bookings', 'trip-itinerary-empty', '先让 AI 帮你规划', '还没有可看的行程',
            '这台服务已接入 AI 模型', 'ai_state', 'DISABLED_BY_OPS')


def get(base, path, auth=False, want=False):
    r = urllib.request.Request(base + path)
    r.add_header('User-Agent', 'hjp3-r7-entry-check-readonly')
    if auth:
        r.add_header('Authorization', BASIC)
    t0 = time.time()
    body = b''
    try:
        with DIRECT.open(r, timeout=60) as f:
            body = f.read()
            row = {'path': path, 'status': f.status, 'content_type': f.headers.get('content-type'),
                   'server': f.headers.get('server'), 'bytes': len(body),
                   'sha256': hashlib.sha256(body).hexdigest(), 'elapsed_ms': int((time.time() - t0) * 1000)}
    except urllib.error.HTTPError as e:
        body = e.read()
        row = {'path': path, 'status': e.code, 'content_type': e.headers.get('content-type'),
               'server': e.headers.get('server'), 'bytes': len(body),
               'sha256': hashlib.sha256(body).hexdigest(), 'elapsed_ms': int((time.time() - t0) * 1000)}
    except Exception as e:  # noqa: BLE001
        return ({'path': path, 'status': None,
                'error': type(e).__name__ + ': ' + str(e)[:110]}, b'')
    return (row, body) if want else (row, body)


def probe(base, auth):
    shell, html_b = get(base, '/', auth, want=True)
    html = html_b.decode('utf-8', 'replace')
    asset = (re.search(r'"(/assets/index-[^"]+\.js)"', html) or [None, None])[1]
    arow, ab = get(base, asset, auth, want=True) if asset else (None, b'')
    health, hb = get(base, '/api/v1/health', auth, want=True)
    hkeys, ai_fields = None, None
    if hb:
        try:
            j = json.loads(hb.decode('utf-8', 'replace'))
            hkeys = sorted(j.keys())
            ai_fields = {k: j.get(k) for k in ('ai', 'ai_state') if k in j}
        except Exception:  # noqa: BLE001
            hkeys = 'NOT_JSON'
    return {'base': base, 'auth_sent': bool(auth), 'username_used': user, 'shell': shell,
            'asset_named_by_the_shell': asset, 'asset_row': arow,
            'asset_matches_the_name_the_commander_gave': asset == NAMED_ASSET,
            'health_row': health, 'health_field_names': hkeys, 'health_ai_fields': ai_fields,
            'asset_bytes_object': ab}


res = [probe(LOCAL, False), probe(PUBLIC, True)]
asset_src = res[0]['asset_bytes_object'].decode('utf-8', 'replace')
lits = {x: {'occurrences': asset_src.count(x), 'first_byte_offset': asset_src.find(x)} for x in LITERALS}
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'named_asset_by_the_commander': NAMED_ASSET,
       'method': 'GET the shell and the asset it names on both entries, GET /api/v1/health, then a literal search '
                 'over the asset bytes; no-proxy opener because this shell exports HTTP(S)_PROXY at a dead port',
       'requests_made': 6, 'clicks': 0, 'writes': 0,
       'entries': [{k: v for k, v in e.items() if k != 'asset_bytes_object'} for e in res],
       'same_asset_name_on_both_entries': res[0]['asset_named_by_the_shell'] == res[1]['asset_named_by_the_shell'],
       'same_asset_bytes_on_both_entries': bool(res[0]['asset_row'] and res[1]['asset_row']
                                                and res[0]['asset_row']['sha256'] == res[1]['asset_row']['sha256']),
       'asset_literal_search_over_the_served_bytes': lits,
       'data_cnx_field_literal_count': lits['data-cnx-field']['occurrences']}
blob = json.dumps(out, ensure_ascii=False, indent=1)
assert secret not in blob, 'the secret would have been written into the artefact'
(OUT / 'r7_entry_check.json').write_text(blob, encoding='utf-8', newline='\n')
print(json.dumps({'entries': [[e['base'][:12], e['shell']['status'] if 'status' in e['shell'] else e['shell'],
                              e['asset_named_by_the_shell'],
                              (e['asset_row'] or {}).get('bytes'), ((e['asset_row'] or {}).get('sha256') or '')[:16],
                              e['health_row'].get('status'), e['health_row'].get('bytes'), e['health_ai_fields'],
                              e['asset_matches_the_name_the_commander_gave']] for e in out['entries']],
                  'same_name': out['same_asset_name_on_both_entries'],
                  'same_bytes': out['same_asset_bytes_on_both_entries']}, ensure_ascii=False, indent=1))
print(json.dumps(out['asset_literal_search_over_the_served_bytes'], ensure_ascii=False, indent=1)[:1500])
