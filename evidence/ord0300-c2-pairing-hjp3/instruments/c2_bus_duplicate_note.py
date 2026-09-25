"""Record the duplicate I just created on the bus, and what caused it.

The first run of `c2_bus.py` POSTed the comment successfully and then died reading it back: I asked
`/issues/1/comments/<id>`, which has no single-comment handler and answers 404. I treated the whole run as
failed and ran it again - so the same body landed twice. Nothing was edited or deleted (that is not allowed
here); the honest artefact is this record.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time
import urllib.request

B = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
TOK = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920').read_text(
    encoding='utf-8').strip()
IDS = (5832877676, 5832902818)


def gh(path):
    r = urllib.request.Request('https://api.github.com' + path)
    r.add_header('Authorization', 'Bearer ' + TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-0300c2-dupnote')
    with urllib.request.urlopen(r, timeout=180) as f:
        return json.loads(f.read().decode())


CLOSING = pathlib.Path('D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt').read_bytes()
rows = []
for cid in IDS:
    c = gh('/repos/Canshu-King/CityNexus-Workspace/issues/comments/%d' % cid)
    tail = [x for x in c['body'].rstrip().splitlines() if x.strip()][-1]
    rows.append({'comment_id': cid, 'permalink': c['html_url'], 'created_at': c['created_at'],
                 'body_bytes': len(c['body'].encode('utf-8')),
                 'body_sha256_64_hex': hashlib.sha256(c['body'].encode('utf-8')).hexdigest(),
                 'tail_equals_closing_line': tail.encode('utf-8') == CLOSING})
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'what_happened': 'the first run of c2_bus.py posted the comment and then died on its own read-back '
                        'route (/issues/1/comments/<id> has no single-comment handler; it answers 404). I '
                        'read that as a failed delivery and ran the script again, so the body landed twice.',
       'rule_this_breaks': 'the bus is a mailbox: a duplicate is noise for every other lane, and my own rule '
                           'is "corrections go out as a NEW post naming the original id, never edit or '
                           'delete" - which does not license posting the same delivery twice',
       'what_was_not_done': 'no edit and no delete of either comment; nothing was rewritten',
       'comments': rows,
       'the_two_bodies_are_the_same_bytes': len({r['body_sha256_64_hex'] for r in rows}) == 1,
       'tail_line_is_the_fetched_closing_line_in_both': all(r['tail_equals_closing_line'] for r in rows),
       'fix_in_the_instrument': 'c2_bus.py now caches the comment id it created (bus_posted_id_c2.txt) and '
                                'refuses to post a second time, and it reads back through '
                                '/repos/.../issues/comments/<id>; the instrument goes out under a revision '
                                'name, the version that ran stays published',
       'closing_line_bytes': len(CLOSING),
       'closing_line_blob_40_hex': hashlib.sha1(b'blob %d\0' % len(CLOSING) + CLOSING).hexdigest()}
out['verdict'] = {'DUPLICATE_RECORDED_NOT_RETRACTED': True,
                  'both_tails_verified': out['tail_line_is_the_fetched_closing_line_in_both'],
                  'same_bytes_twice': out['the_two_bodies_are_the_same_bytes']}
(B / 'bus_duplicate_note_c2.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                              encoding='utf-8', newline='\n')
print(json.dumps(out, ensure_ascii=False, indent=1))
