"""Find the commander's challenge on the coordination bus and record its id + permalink.

The bus is `Canshu-King/CityNexus-Workspace` issue #1. Large pages reset mid-body on this link, so this
walks small pages with `since=` and retries the TLS drops that this network produces.
"""
from __future__ import annotations

import json
import pathlib
import time
import urllib.parse
import urllib.request

TOK = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920').read_text(
    encoding='utf-8').strip()
B = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
NEEDLES = ('同果', '挑战你', 'UI_FETCH_DIED')


def gh(path):
    for a in range(6):
        r = urllib.request.Request('https://api.github.com' + path)
        r.add_header('Authorization', 'Bearer ' + TOK)
        r.add_header('Accept', 'application/vnd.github+json')
        r.add_header('User-Agent', 'hjp3-0300c2-busscan')
        try:
            with urllib.request.urlopen(r, timeout=120) as f:
                return json.loads(f.read().decode())
        except Exception as e:  # noqa: BLE001
            if a == 5:
                raise
            print('  retry %d: %s' % (a, str(e)[:70]), flush=True)
            time.sleep(2 + 2 * a)


since = urllib.parse.quote('2026-09-25T09:30:00Z')
page, hits, seen = 1, [], 0
while page <= 14:
    cs = gh('/repos/Canshu-King/CityNexus-Workspace/issues/1/comments'
            '?since=%s&per_page=20&page=%d&sort=created&direction=asc' % (since, page))
    if not cs:
        break
    seen += len(cs)
    for c in cs:
        body = c['body']
        if any(n in body for n in NEEDLES):
            hits.append({'id': c['id'], 'at': c['created_at'], 'who': c['user']['login'],
                         'permalink': c['html_url'], 'first_line': body.splitlines()[0][:160],
                         'mentions_this_lane': ('HJ-P3' in body or 'aad2d1f2' in body
                                                or 'C2 那一格' in body),
                         'bytes': len(body.encode('utf-8'))})
    if len(cs) < 20:
        break
    page += 1
out = {'scanned_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'comments_scanned': seen,
       'pages_walked': page, 'needles': list(NEEDLES), 'hits': hits}
(B / 'bus_challenge_scan_c2.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                             encoding='utf-8', newline='\n')
print(json.dumps(out, ensure_ascii=False, indent=1))
