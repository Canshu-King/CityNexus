"""ORD-0312 M3, re-bound at 03:3x: the phone chain was re-deployed, so the generation to pin moved.

The commander's new probe `evidence/cmdr-deploy-ORD-0302-b5/phone_probe_after_r1.json` names
`9a669c8bec863fadf31d5158f4a1be66aec49f23` and three served rows. This run does three things, all read-only:

  1. takes his probe and landing receipt back over the API by 40-hex and re-hashes them, so every coordinate I
     cite is bytes I actually read;
  2. fetches ALL THREE rows myself through the shared hop at :4781 (GET only) - the JS, the CSS and the service
     worker - and compares bytes + sha256 + status against his rows, which is the part I could not claim last
     time because I had only ever fetched the JS row;
  3. reads the page a second time to see WHICH asset it now names, and checks his retention claim (the superseded
     bundle must still be fetchable, since the deploy unions rather than deletes).

What it deliberately does NOT do: re-bind my pass-3 arms. Those ran on the generation that was in service before
this deploy, so their generation field is written here as a named difference, not silently moved forward.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util as iu
import json
import pathlib
import re
import subprocess
import time
import urllib.error
import urllib.request

OUT = pathlib.Path('D:/moodle/_hjp3_0312p4_0926')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
REPO = pathlib.Path('D:/moodle/CityNexus')
HOP = 'http://127.0.0.1:4781'
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

PROBE_PATH = 'evidence/cmdr-deploy-ORD-0302-b5/phone_probe_after_r1.json'
PROBE_BLOB = '4f67fce417b49d0d87e13d08cd050b5a8d0bd9bc'
DEPLOY_PATH = 'evidence/cmdr-deploy-ORD-0302-b5/deploy_receipt_r1.json'
DEPLOY_BLOB = '55178a00cfc7125179ec7b50111ec92e2500aa05'
LAND_PATH = 'evidence/cmdr-landing-ORD-0302-b5/preflight_r1.json'
LAND_BLOB = 'e2420d98ef2bf26e6b3bfc83049ab17d2b463a96'
NEW_TIP = '9a669c8bec863fadf31d5158f4a1be66aec49f23'
OLD_ASSET = 'assets/index-DWgtVWb0.js'


def fetch_blob(sha):
    raw = base64.b64decode(pub.api('/git/blobs/' + sha)['content'])
    return raw, hashlib.sha1(b'blob %d\0' % len(raw) + raw).hexdigest()


def get(path):
    r = urllib.request.Request(HOP + path)
    r.add_header('User-Agent', 'hjp3-p4-m3-gen2-readonly')
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=90) as f:
            b = f.read()
            return {'path': path, 'http_status': f.status, 'content_type': f.headers.get('content-type'),
                    'bytes': len(b), 'sha256_64_hex': hashlib.sha256(b).hexdigest(),
                    'elapsed_ms': int((time.time() - t0) * 1000)}
    except urllib.error.HTTPError as e:
        b = e.read()
        return {'path': path, 'http_status': e.code, 'content_type': e.headers.get('content-type'),
                'bytes': len(b), 'sha256_64_hex': hashlib.sha256(b).hexdigest(),
                'elapsed_ms': int((time.time() - t0) * 1000), 'error': 'HTTP_ERROR'}
    except Exception as e:  # noqa: BLE0001
        return {'path': path, 'http_status': None, 'error': type(e).__name__ + ': ' + str(e)[:120],
                'bytes': None, 'sha256_64_hex': None}


tip, tree, _rows = pub.branch_rows()
on_branch = {r['path']: r['sha'] for r in
             pub.api('/git/trees/' + tip + '?recursive=1')['tree'] if 'sha' in r}
probe_raw, probe_re = fetch_blob(PROBE_BLOB)
probe = json.loads(probe_raw.decode('utf-8'))
deploy_raw, deploy_re = fetch_blob(DEPLOY_BLOB)
deploy = json.loads(deploy_raw.decode('utf-8'))
land_raw, land_re = fetch_blob(LAND_BLOB)
land = json.loads(land_raw.decode('utf-8'))

def get_page():
    """One read of the served page. The asset NAME it references and the hash of its bytes come out; the HTML
    itself never does, so this run cannot smuggle a response body into an evidence file."""
    r = urllib.request.Request(HOP + '/')
    r.add_header('User-Agent', 'hjp3-p4-m3-gen2-readonly')
    with urllib.request.urlopen(r, timeout=90) as f:
        st, html = f.status, f.read()
    m = re.search(r'''["'](/assets/index-[^"']+\.js)["']''', html.decode('utf-8', 'replace'))
    return {'http_status': st, 'bytes': len(html), 'sha256_64_hex': hashlib.sha256(html).hexdigest(),
            'asset_named_by_the_served_page': (m.group(1).lstrip('/') if m else None)}


idx = get_page()
page_names = idx['asset_named_by_the_served_page']

prow = {(r['path'] or '').lstrip('/'): r for r in probe['rows']}
mine = {}
for path in sorted(prow):
    mine[path] = get('/' + path if path.startswith('v10-sw') else '/' + path)
old_still = get('/' + OLD_ASSET)

rows_cmp = {}
for path, pr in prow.items():
    my = mine.get(path) or {}
    rows_cmp[path] = {
        'probe_row': {'bytes': pr.get('served_bytes'), 'sha256_head': str(pr.get('served_sha256'))[:16],
                      'sha256_full': pr.get('served_sha256'), 'http_status': pr.get('http_status'),
                      'content_type': pr.get('content_type')},
        'my_read': {'bytes': my.get('bytes'), 'sha256_full': my.get('sha256_64_hex'),
                    'http_status': my.get('http_status'), 'content_type': my.get('content_type')},
        'bytes_equal': bool(my.get('bytes') == pr.get('served_bytes')),
        'sha256_equal': bool(my.get('sha256_64_hex') == pr.get('served_sha256')),
        'status_equal': bool(my.get('http_status') == pr.get('http_status'))}

mir = subprocess.run(['git', '-C', str(REPO), 'ls-remote', 'origin',
                      'refs/heads/mirror/integration-frontend-apple-pass1'],
                     capture_output=True, text=True, encoding='utf-8', errors='replace')
mirror_sha = ([ln.split()[0] for ln in (mir.stdout or '').splitlines() if ln.strip()] + [None])[0]

out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'order': 'ORD-0312 M3 re-bound at 03:32 (generation moved: B\'s ORD-0302 b5 landed and the chain was cut over)',
       'lane': 'HJ-P3 aad2d1f2-4de9-406b-a5df-afa0e2bcea58',
       'scope': 'which front-end bytes the shared phone chain serves NOW, and whether they equal the rows in the '
                'commander\'s post-cutover probe',
       'how_read': 'GET /git/blobs/<40hex> over the API + re-hash for his artefacts; 1 read of the served page and '
                   'one GET per served row through http://127.0.0.1:4781 (the hop the phone uses). 0 POST, '
                   '0 write, 0 credential, 0 database, 0 deploy action.',
       'requests_to_the_chain': 2 + len(prow) + 1,
       'cmdr_artefacts_read_back': {
           'phone_probe_after_r1': {'path': PROBE_PATH, 'cited_blob': PROBE_BLOB,
                                    'recomputed_from_bytes_i_read': probe_re,
                                    'cited_equals_recomputed': probe_re == PROBE_BLOB,
                                    'bytes': len(probe_raw),
                                    'also_on_branch_at_that_path': on_branch.get(PROBE_PATH),
                                    'schema': probe.get('schema'), 'probed_at_local': probe.get('probed_at_local'),
                                    'generation_under_test': probe.get('generation_under_test'),
                                    'overall': probe.get('overall'),
                                    'rows_named': [r['path'] for r in probe['rows']]},
           'deploy_receipt_r1': {'path': DEPLOY_PATH, 'cited_blob': DEPLOY_BLOB,
                                 'recomputed': deploy_re, 'cited_equals_recomputed': deploy_re == DEPLOY_BLOB,
                                 'bytes': len(deploy_raw),
                                 'also_on_branch_at_that_path': on_branch.get(DEPLOY_PATH),
                                 'fields_seen': {k: deploy.get(k) for k in
                                                 ('overall', 'generation_under_test', 'target', 'swapped_at_local')
                                                 if k in deploy}},
           'landing_preflight_r1': {'path': LAND_PATH, 'cited_blob': LAND_BLOB, 'recomputed': land_re,
                                    'cited_equals_recomputed': land_re == LAND_BLOB,
                                    'bytes': len(land_raw),
                                    'also_on_branch_at_that_path': on_branch.get(LAND_PATH),
                                    'fields_seen': {k: land.get(k) for k in
                                                    ('overall', 'verdict', 'generation_under_test') if k in land}}},
       'generation_under_test': probe.get('generation_under_test'),
       'generation_named_by_the_commander_03_32': NEW_TIP,
       'generation_field_equals_his_number': bool(probe.get('generation_under_test') == NEW_TIP),
       'mirror_tip_read_at_this_minute': mirror_sha,
       'mirror_tip_equals_the_ordered_generation': bool(mirror_sha == NEW_TIP),
       'served_page': {'names_this_asset': page_names,
                       'index_bytes': idx.get('index_bytes') or mine.get('__none__', {}).get('bytes'),
                       'http_status': idx.get('http_status')},
       'per_row_mine_vs_probe': rows_cmp,
       'retention_check_of_the_superseded_bundle': {
           'path': OLD_ASSET, 'http_status': old_still.get('http_status'), 'bytes': old_still.get('bytes'),
           'sha256_full': old_still.get('sha256_64_hex'),
           'equals_the_generation_i_measured_pass3': bool(
               old_still.get('sha256_64_hex') == '1c90b81eca9e8947b05821586b6c1d2af2ff69487f266006d3d7ae16bd74c51c')},
       'generation_of_my_pass3_arms': {
           'tip': '7856e03f6238da3000976eb6e690a448dfa39b9a',
           'served_asset_at_the_time': OLD_ASSET,
           'still_in_service_now': bool(page_names == OLD_ASSET),
           'what_this_means': 'My pass-3 readings belong to the generation that was serving before this cutover. '
                              'They are not re-pointed by citing a newer probe; if ORD-0312 wants same-generation '
                              'readings the arms have to be re-run on ' + NEW_TIP + '.'},
       }
all_rows = [v for v in rows_cmp.values()]
out['verdict'] = {
    'every_cited_cmdr_blob_resolves_to_the_bytes_i_read': bool(
        probe_re == PROBE_BLOB and deploy_re == DEPLOY_BLOB and land_re == LAND_BLOB
        and on_branch.get(PROBE_PATH) == PROBE_BLOB),
    'the_new_probe_pins_the_generation_the_commander_named': bool(
        probe.get('generation_under_test') == NEW_TIP),
    'the_chain_now_serves_the_asset_the_probe_names': bool(page_names in prow),
    'all_three_rows_match_my_own_read_byte_for_byte': bool(all(v['bytes_equal'] and v['sha256_equal']
                                                               for v in all_rows)) and bool(all_rows),
    'and_every_row_returns_the_status_the_probe_recorded': bool(all(v['status_equal'] for v in all_rows)),
    'the_superseded_bundle_is_still_fetchable': bool(old_still.get('http_status') == 200
                                                     and old_still.get('sha256_64_hex')),
    'my_pass3_arms_are_on_the_previous_generation': bool(page_names != OLD_ASSET)}
out['verdict']['ALL_HOLD'] = all(v for k, v in out['verdict'].items() if k != 'ALL_HOLD')
p = OUT / 'ord0312_m3_binding_reread_gen2.json'
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print('wrote', p.name, p.stat().st_size, 'B')
print(json.dumps(out['verdict'], ensure_ascii=False, indent=1))
print('page names:', page_names, '| rows:', json.dumps(
    {k: {'mine': v['my_read']['bytes'], 'probe': v['probe_row']['bytes'], 'eq': v['bytes_equal'] and v['sha256_equal']}
     for k, v in rows_cmp.items()}, ensure_ascii=False))
print('old bundle still served:', json.dumps(out['retention_check_of_the_superseded_bundle'], ensure_ascii=False))
