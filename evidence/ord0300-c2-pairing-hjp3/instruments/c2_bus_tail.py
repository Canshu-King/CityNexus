"""Read the tail of the coordination bus (Canshu-King/CityNexus-Workspace issue #1) with retries.

Why a script: this link drops TLS mid-request often enough that a single-shot fetch reads as "the bus is
down". Each page is small (per_page=20) because a 100-item page has been truncating mid-body, and the walk
stops at the first empty page. Output: the newest comments with id, author, timestamp and the first line, so
a delivery post can name the comment it answers instead of guessing.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.request

TOK = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920').read_text(
    encoding='utf-8').strip()
API = 'https://api.github.com/repos/Canshu-King/CityNexus-Workspace'
B = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')


def gh(path):
    last = None
    for a in range(6):
        r = urllib.request.Request(API + path)
        r.add_header('Authorization', 'Bearer ' + TOK)
        r.add_header('Accept', 'application/vnd.github+json')
        r.add_header('User-Agent', 'hjp3-bus-tail')
        try:
            with urllib.request.urlopen(r, timeout=120) as f:
                return json.loads(f.read().decode())
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 + 2 * a)
    raise SystemExit('bus unreadable after retries: %s' % str(last)[:120])


since = sys.argv[1] if len(sys.argv) > 1 else '2026-09-25T09:00:00Z'
page, out, scanned = 1, [], 0
while page <= 20:
    cs = gh('/issues/1/comments?since=%s&per_page=20&page=%d&sort=created&direction=asc'
            % (since.replace(':', '%3A').replace(' ', '+'), page))
    if not isinstance(cs, list) or not cs:
        break
    scanned += len(cs)
    out += cs
    if len(cs) < 20:
        break
    page += 1
rows = [{'id': c['id'], 'at': c['created_at'], 'who': c['user']['login'],
         'url': c['html_url'], 'bytes': len(c['body'].encode('utf-8')),
         'first_line': c['body'].strip().splitlines()[0][:150] if c['body'].strip() else '(empty)',
         'body': c['body']} for c in out]
(B / 'bus_tail_c2.json').write_text(json.dumps(
    {'read_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'since': since, 'pages_walked': page,
     'comments': len(rows), 'last_id_before_this_read': rows[-1]['id'] if rows else None,
     'rows': rows}, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
for r in rows:
    print('%s %-16s %11d %s' % (r['at'], r['who'], r['id'], r['first_line'][:96]))
print('comments read:', len(rows), '| pages walked:', page, '| last id:',
      rows[-1]['id'] if rows else None)
