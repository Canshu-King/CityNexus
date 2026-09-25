"""Read-only third timestamp on the same question: does the shared phone chain still serve the asset the
commander's new probe pins, at the minute this block is published?

Two GETs against :4781 (the hop the phone uses), nothing written, no credentials, no database. The asset name is
taken OUT OF the served index.html - not from my build list, that is the mistake that manufactured my 20:0x
claim - and then that name is fetched and hashed. Compared against (a) the JS row of
`evidence/cmdr-phone-side-probe-0115/probe_r2.json` as re-read by `p4_m3_bind.py`, (b) my own 22:0x and 00:1x
readings, (c) my `git archive` build of the generation that probe names.

Why a third reading: the mirror branch had moved again between the probe (01:15) and this block, so "which
generation is online" is re-measured rather than carried over.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import time
import urllib.request

OUT = pathlib.Path('D:/moodle/_hjp3_0312p4_0926')
REPO = pathlib.Path('D:/moodle/CityNexus')
BIND = json.loads((pathlib.Path('D:/moodle/_hjp3_0301p3_0925') / 'served_generation_bind_c2.json')
                  .read_text(encoding='utf-8'))
RC = json.loads((OUT / 'ord0312_m3_binding_reread.json').read_text(encoding='utf-8'))['row_checks'][
    'js_asset_i_read_myself']
GEN = json.loads((OUT / 'ord0312_m3_binding_reread.json').read_text(encoding='utf-8'))[
    'generation_under_test']
probe, mine00, mine22 = RC['probe_row'], RC['my_00_1x_read'], RC['my_22_0x_read']


def get(url):
    r = urllib.request.Request(url)
    r.add_header('User-Agent', 'hjp3-p4-served-now-readonly')
    with urllib.request.urlopen(r, timeout=60) as f:
        return f.status, f.read()


def h(d):
    return hashlib.sha256(d).hexdigest()


st, idx = get('http://127.0.0.1:4781/')
m = re.search(r'''["'](/assets/index-[^"']+\.js)["']''', idx.decode('utf-8', 'replace'))
now = {'index_http_status': st, 'index_bytes': len(idx), 'index_sha256_64_hex': h(idx),
       'asset_named_by_the_served_page': (m.group(1) if m else '').lstrip('/')}
if m:
    s2, ab = get('http://127.0.0.1:4781' + m.group(1))
    now.update({'asset_http_status': s2, 'asset_bytes': len(ab), 'asset_sha256_64_hex': h(ab)})

name = now['asset_named_by_the_served_page']
built = BIND['builds']['7856e03f']
same = lambda x: bool(x and x == now.get('asset_sha256_64_hex'))
out = {
    'artifact': 'HJP3-P4-ORCH-SERVED-RECHECK', 'schema': 'CNX_HJP3_SERVED_GENERATION_RECHECK_V1',
    'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    'how_read': 'two GETs through http://127.0.0.1:4781, asset name taken out of the served index.html; '
                '0 POST, 0 write, 0 credential, 0 database, 0 deploy action',
    'requests_made': 2, 'methods': ['GET', 'GET'], 'writes': 0, 'credentials_sent': False,
    'served_now': now,
    'probe_js_row_cmdr_0115': probe,
    'my_00_1x_read': mine00, 'my_22_0x_read': mine22,
    'my_build_of_the_generation_the_probe_names': {
        'generation': built['tip'], 'built_asset': built['built_asset'].lstrip('/'),
        'built_bytes': built['built_bytes'], 'built_sha256_64_hex': built['built_sha256_64_hex']},
    'comparisons': {
        'asset_name_equals_the_probe_row': name == probe['path'].lstrip('/'),
        'bytes_equal_the_probe_row': same(probe['served_sha256']),
        'bytes_equal_my_00_1x_read': same(mine00['sha256_64_hex']),
        'bytes_equal_my_22_0x_read': same(mine22['sha256_64_hex']),
        'bytes_equal_my_build_of_that_generation': same(built['built_sha256_64_hex']),
        'generation_the_probe_names': GEN},
    'mirror_tip_read_at_this_minute': None,
    'mirror_tip_named_by_the_commander_at_00_36': '2344145ce6342b6ac32ac4d0955c0f524d8c9320',
}
r = subprocess.run(['git', '-C', str(REPO), 'ls-remote', 'origin',
                    'refs/heads/mirror/integration-frontend-apple-pass1'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
lines = [ln.split() for ln in (r.stdout or '').splitlines() if ln.strip()]
assert r.returncode == 0 and len(lines) == 1, (r.returncode, r.stdout[:200], r.stderr[:200])
out['mirror_tip_read_at_this_minute'] = lines[0][0]
out['mirror_has_moved_since_his_read'] = (
    lines[0][0] != '2344145ce6342b6ac32ac4d0955c0f524d8c9320')
c = out['comparisons']
out['verdict'] = {
    'the_chain_still_serves_what_the_probe_pins': bool(
        c['asset_name_equals_the_probe_row'] and c['bytes_equal_the_probe_row']),
    'and_those_bytes_are_my_build_of_that_generation': bool(c['bytes_equal_my_build_of_that_generation']),
    'and_my_three_timestamps_agree': bool(c['bytes_equal_my_00_1x_read'] and c['bytes_equal_my_22_0x_read'])}
out['verdict']['ALL_HOLD'] = all(out['verdict'].values())
p = OUT / ('served_generation_recheck_p4_%s.json' % time.strftime('%H%M'))
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print('wrote', p.name, p.stat().st_size, 'B | ALL_HOLD', out['verdict']['ALL_HOLD'])
print(json.dumps({'served_now': now, 'comparisons': c, 'verdict': out['verdict'],
                  'mirror': out['mirror_tip_read_at_this_minute'],
                  'mirror_moved': out['mirror_has_moved_since_his_read']}, ensure_ascii=False, indent=1))
