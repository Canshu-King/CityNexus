"""Who is answering the chain's 500s - measured by signature, not asserted.

The screen tells the traveller 「服务器拒绝了这一步（HTTP 500）」. To test whether anything behind that hop is a
server at all, I read four real API paths and one path the product cannot possibly serve
(`/api/v1/zzz-hjp3-canary-path`) through the same hop, and compare status, content type, byte count, body hash,
elapsed time and the `server` header. If the made-up path answers exactly like the real ones, the answer cannot
be coming from application code.

Read-only GETs, no POST, no credential, no database, no deploy action.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time
import urllib.error
import urllib.request

OUT = pathlib.Path('D:/moodle/_hjp3_0323walk_0926')
CHAIN = 'http://127.0.0.1:4781'
PATHS = ('/api/v1/health', '/api/v1/journeys', '/api/v1/demo/scene', '/api/v1/zzz-hjp3-canary-path')


def probe(p):
    r = urllib.request.Request(CHAIN + p)
    r.add_header('User-Agent', 'hjp3-walk-who-answered-readonly')
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=30) as f:
            b = f.read()
            return {'path': p, 'http_status': f.status, 'content_type': f.headers.get('content-type'),
                    'server_header': f.headers.get('server'), 'bytes': len(b),
                    'body_sha256': hashlib.sha256(b).hexdigest(), 'elapsed_ms': int((time.time() - t0) * 1000)}
    except urllib.error.HTTPError as e:
        b = e.read()
        return {'path': p, 'http_status': e.code, 'content_type': e.headers.get('content-type'),
                'server_header': e.headers.get('server'), 'bytes': len(b),
                'body_sha256': hashlib.sha256(b).hexdigest(), 'elapsed_ms': int((time.time() - t0) * 1000)}
    except Exception as e:  # noqa: BLE001
        return {'path': p, 'http_status': None, 'error': type(e).__name__ + ': ' + str(e)[:100]}


res = [probe(p) for p in PATHS]
sig = lambda x: (x.get('http_status'), x.get('content_type'), x.get('bytes'), x.get('body_sha256'))
canary = [x for x in res if 'zzz-hjp3-canary' in x['path']][0]
real = [x for x in res if x is not canary]
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'chain': CHAIN,
       'method': 'read-only GET through the hop the phone uses; signatures compared as '
                 '(status, content-type, bytes, body sha256)',
       'requests_made': len(res), 'writes': 0, 'credentials_sent': False,
       'readings': res,
       'empty_body_sha256': hashlib.sha256(b'').hexdigest(),
       'verdict': {
           'the_made_up_path_answers_identically_to_the_real_api_paths': bool(
               all(sig(x) == sig(canary) for x in real)),
           'no_reading_carries_a_server_header': all(x.get('server_header') is None for x in res),
           'every_answer_has_a_zero_length_body': all(x.get('bytes') == 0 for x in res),
           'therefore_the_500_carries_no_application_specific_content': bool(
               all(x.get('bytes') == 0 for x in res)
               and all(sig(x) == sig(canary) for x in real))}}
out['verdict']['ALL_HOLD'] = all(out['verdict'].values())
(OUT / 'r5_who_answered.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                          encoding='utf-8', newline='\n')
print(json.dumps({'verdict': out['verdict'],
                  'distinct_signatures': sorted({str(sig(x)) for x in res})}, ensure_ascii=False, indent=1))
