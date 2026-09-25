"""Read-only re-check of what the shared chain actually serves, before accepting any claim that a given
commit is "the online base" (the commander's ORD-0288 note names dc964086; my 22:0x reading said the served
bytes equal my 7856e03f build - one of those two readings is out of date, so both are quoted with timestamps
and neither is trusted).

Method, unchanged from the correction it exists to test: take the asset name OUT OF the served index.html
(not from my own build list - that is the mistake that manufactured my 20:0x claim), hash the bytes the chain
returns for that name, and compare against the three builds this lane already made from `git archive` exports.
Two GETs, no writes, no credentials, no database, no deploy action.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import time
import urllib.request

P3 = pathlib.Path('D:/moodle/_hjp3_0301p3_0925')
REPO = pathlib.Path('D:/moodle/CityNexus')
BASE = json.loads((P3 / 'served_generation_bind_c2.json').read_text(encoding='utf-8'))


def get(url):
    r = urllib.request.Request(url)
    r.add_header('User-Agent', 'hjp3-p3-recheck-readonly')
    with urllib.request.urlopen(r, timeout=60) as f:
        return f.status, f.read()


def sha(d):
    return hashlib.sha256(d).hexdigest()


st, idx = get('http://127.0.0.1:4781/')
html = idx.decode('utf-8', 'replace')
m = re.search(r'''["'](/assets/index-[^"']+\.js)["']''', html)
served = {'index_http_status': st, 'index_bytes': len(idx), 'index_sha256_64_hex': sha(idx),
          'asset_referenced_by_the_served_page': m.group(1) if m else None}
if m:
    s2, ab = get('http://127.0.0.1:4781' + m.group(1))
    served.update({'asset_http_status': s2, 'asset_bytes': len(ab), 'asset_sha256_64_hex': sha(ab)})
cmp = {}
for tag, ent in BASE['builds'].items():
    cmp[tag] = {'tip': ent['tip'], 'built_asset': (ent.get('built_asset') or '').lstrip('/'),
                'built_sha256_64_hex': ent.get('built_sha256_64_hex'),
                'equals_what_is_served_now': bool(
                    ent.get('built_sha256_64_hex') == served.get('asset_sha256_64_hex'))}
remote = {}
for ref in ('refs/heads/commander/control', 'HEAD'):
    r = subprocess.run(['git', 'ls-remote', 'origin', ref], cwd=str(REPO), capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    lines = [l.split() for l in (r.stdout or '').splitlines() if l.strip()]
    remote[ref] = {'sha': lines[0][0] if lines else None, 'rc': r.returncode}
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'requests_made': 2,
       'methods': ['GET', 'GET'], 'writes': 0, 'credentials_sent': False,
       'why': 'the commander named dc964086 as the online base at 00:0x; my own earlier reading named a '
              'different commit, so the question is measured again rather than argued',
       'served_now': served,
       'compared_against_my_three_builds': cmp,
       'my_previous_reading_22_0x': {'asset': BASE['served']['asset_referenced_by_the_served_page'],
                                     'sha256_64_hex': BASE['served']['asset_sha256_64_hex'],
                                     'which_candidate_matched': BASE['verdict']['served_tip_full_40_hex']},
       'same_asset_name_as_then': served.get('asset_referenced_by_the_served_page')
       == BASE['served']['asset_referenced_by_the_served_page'],
       'same_bytes_as_then': served.get('asset_sha256_64_hex') == BASE['served']['asset_sha256_64_hex'],
       'authority_refs': remote,
       'commander_claim_that_phone_is_on_dc964086_scored': cmp['dc964086']['equals_what_is_served_now'],
       'my_22_0x_reading_still_holds': cmp['7856e03f']['equals_what_is_served_now']}
(P3 / 'served_generation_recheck_p3.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                     encoding='utf-8', newline='\n')
print(json.dumps({k: out[k] for k in ('served_now', 'commander_claim_that_phone_is_on_dc964086_scored',
                                      'my_22_0x_reading_still_holds', 'same_bytes_as_then',
                                      'authority_refs')}, ensure_ascii=False, indent=1))
print('per candidate:', json.dumps(cmp, ensure_ascii=False))
