"""My own three-face byte binding for the newest phone generation, taken over GET only.

The artefact the commander cited for `ab12c17a` is a render check (`CNX_CMDR_RENDER_CHECK_V1`), which carries no
asset rows and no generation field, so it cannot be used to pin bytes. His previous-generation artefact
(`CNX_CMDR_PHONE_SIDE_PROBE_V1`) did carry three rows. Rather than borrow that shape, I read the same three faces
myself through the hop the phone uses: the JS asset the shell names, the CSS asset the shell names, and the
service worker. Each row records status, content type, the `server` header, byte length and sha256 of the bytes I
received, so any later claim about this generation can be checked against a reading of mine instead of against a
sentence.

Boundaries: GET only; 0 clicks; the wizard was not walked; 0 writes; 0 credentials; :4782 and the tunnel not
contacted; nothing read from a database.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import time
import urllib.request

OUT = pathlib.Path('D:/moodle/_hjp3_0323walk_0926')
CHAIN = 'http://127.0.0.1:4781'


def get(p, want_text=False):
    r = urllib.request.Request(CHAIN + p)
    r.add_header('User-Agent', 'hjp3-face-get-readonly')
    t0 = time.time()
    with urllib.request.urlopen(r, timeout=60) as f:
        b = f.read()
        row = {'path': p, 'http_status': f.status, 'content_type': f.headers.get('content-type'),
               'server_header': f.headers.get('server'), 'bytes_received': len(b),
               'sha256_of_bytes_i_received': hashlib.sha256(b).hexdigest(),
               'elapsed_ms': int((time.time() - t0) * 1000)}
        return (row, b.decode('utf-8', 'replace')) if want_text else row


shell, html = get('/', True)
js = (re.search(r'"(/assets/index-[^"]+\.js)"', html) or [None, None])[1]
css = (re.search(r'"(/assets/index-[^"]+\.css)"', html) or [None, None])[1]
sw = '/v10-sw.js'
rows = [get(p) for p in [x for x in (js, css, sw) if x]]
rc = json.loads((OUT / 'r5_recheck_raw.json').read_text(encoding='utf-8'))['binding']
scan = json.loads((OUT / 'r5_anchor_scan.json').read_text(encoding='utf-8'))['asset']

by_path = {r['path']: r for r in rows}
js_row = by_path.get(js or '', {})
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'chain': CHAIN,
       'method': 'GET the shell, then GET each asset the shell names, plus the service worker; sha256 over the '
                 'bytes I received',
       'requests_made': len(rows) + 1, 'clicks': 0, 'writes': 0, 'credentials_sent': False,
       'shell': shell,
       'assets_named_by_the_shell': {'js': js, 'css': css, 'service_worker': sw},
       'rows': rows,
       'js_row_equals_my_click_pass': bool(js_row.get('bytes_received') == rc['asset_bytes']
                                           and js_row.get('sha256_of_bytes_i_received')
                                           == rc['asset_sha256_64_hex']),
       'js_row_equals_my_anchor_scan': bool(js_row.get('sha256_of_bytes_i_received')
                                            == scan['body_sha256']),
       'every_row_has_a_server_header': all(r['server_header'] is not None for r in rows)}
(OUT / 'r5_faces_get.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                       encoding='utf-8', newline='\n')
print(json.dumps({'shell_bytes': shell['bytes_received'], 'assets': out['assets_named_by_the_shell'],
                  'js_equals_click_pass': out['js_row_equals_my_click_pass'],
                  'js_equals_anchor_scan': out['js_row_equals_my_anchor_scan'],
                  'rows': [{k: r[k] for k in ('path', 'http_status', 'bytes_received', 'server_header',
                                              'sha256_of_bytes_i_received')} for r in rows]},
                 ensure_ascii=False, indent=1))
