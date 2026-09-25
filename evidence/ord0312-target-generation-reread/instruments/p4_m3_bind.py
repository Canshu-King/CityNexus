"""ORD-0312 M3, closed against the commander's NEW probe: bind every reading of the pass-3 batch to the asset
the phone chain actually serves, and say which rows I verified myself and which I only carry by his artefact.

The order's M3 wording: "每格读数必须命名其资产文件名与 sha256，并与 blob <那枚探针件> 里那三条逐字节一致".
Yesterday the cited blob pinned a different generation, so M3 was a stop-and-report. He has now shipped
`evidence/cmdr-phone-side-probe-0115/probe_r2.json`, which pins 7856e03f - the generation my arms ran on.

So this file does three things and nothing else:
  1. reads his probe back over the API and re-hashes it, so the coordinate I cite is the bytes I read;
  2. compares its three rows against MY OWN served-page readings (22:0x and 00:1x, both GET-only), row by row;
  3. writes the per-cell binding table for the pass-3 arms: asset name + sha256, and the equality against
     the probe - plus a named limit for the rows I did not fetch myself.

Boundaries: read-only `GET /git/blobs/...` against the branch and 0 requests to the phone chain in this run;
0 product bytes; no ref moved; no credential sent.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util as iu
import json
import pathlib
import time

OUT = pathlib.Path('D:/moodle/_hjp3_0312p4_0926')
P3 = pathlib.Path('D:/moodle/_hjp3_0301p3_0925')
SRC = pathlib.Path('D:/moodle/HJ-P3_evidence')
spec = iu.spec_from_file_location('pub', str(SRC / 'p3_publish.py'))
pub = iu.module_from_spec(spec)
spec.loader.exec_module(pub)

PROBE_PATH = 'evidence/cmdr-phone-side-probe-0115/probe_r2.json'
PROBE_BLOB_CITED = 'c6c6ce251520e9656b985129d00cd049ad35774a'
P312 = 'evidence/ord0312-target-generation-reread'
P3P = 'evidence/ord0301-p3-same-chain-hjp3'

tip, tree, rows = pub.branch_rows()
on_branch = {r['path']: r['sha'] for r in pub.api('/git/trees/' + tip + '?recursive=1')['tree'] if 'sha' in r}
obj = pub.api('/git/blobs/' + PROBE_BLOB_CITED)
raw = base64.b64decode(obj['content'])
recomputed = hashlib.sha1(b'blob %d\0' % len(raw) + raw).hexdigest()
probe = json.loads(raw.decode('utf-8'))
bind = json.loads((P3 / 'served_generation_bind_c2.json').read_text(encoding='utf-8'))
rech = json.loads((P3 / 'served_generation_recheck_p3.json').read_text(encoding='utf-8'))
SC = json.loads((P3 / 'p3_scored.json').read_text(encoding='utf-8'))
G = SC['generations']

prow = {r['path'].lstrip('/'): r for r in probe['rows']}
my_js = {'at_22_0x': bind['served'], 'at_00_1x': rech['served_now']}
js_path = (rech['served_now'].get('asset_referenced_by_the_served_page') or '').lstrip('/')
p_js = prow.get(js_path) or {}
row_checks = {
    'js_asset_i_read_myself': {
        'probe_row': {'path': p_js.get('path'), 'served_bytes': p_js.get('served_bytes'),
                      'served_sha256': p_js.get('served_sha256'), 'http_status': p_js.get('http_status')},
        'my_22_0x_read': {'asset': (bind['served']['asset_referenced_by_the_served_page'] or '').lstrip('/'),
                          'bytes': bind['served']['asset_bytes'],
                          'sha256_64_hex': bind['served']['asset_sha256_64_hex']},
        'my_00_1x_read': {'asset': js_path, 'bytes': rech['served_now']['asset_bytes'],
                          'sha256_64_hex': rech['served_now']['asset_sha256_64_hex']},
        'probe_equals_my_22_0x_read': bool(p_js.get('served_sha256')
                                           == bind['served']['asset_sha256_64_hex']
                                           and p_js.get('served_bytes') == bind['served']['asset_bytes']),
        'probe_equals_my_00_1x_read': bool(p_js.get('served_sha256')
                                           == rech['served_now']['asset_sha256_64_hex']
                                           and p_js.get('served_bytes') == rech['served_now']['asset_bytes']),
        'my_two_reads_agree': bool(bind['served']['asset_sha256_64_hex']
                                   == rech['served_now']['asset_sha256_64_hex'])},
    'rows_i_did_not_fetch': {
        k: {'in_the_probe': prow.get(k, {}).get('served_sha256'),
            'in_the_probe_bytes': prow.get(k, {}).get('served_bytes'),
            'my_own_read': 'NOT MEASURED BY ME - I never fetched this row; carrying it means trusting his '
                           'artefact, so it is named, not folded in'}
        for k in prow if k != js_path}}

per_cell = {}
for r in SC['arms_scored']:
    gen = r['gen']
    b = G[gen]
    per_cell[r['run_id']] = {'generation': b['tip'], 'asset_named_by_my_build': b['asset_referenced_by_my_built_index'],
                             'asset_bytes': b['bytes'], 'asset_sha256_64_hex': b['sha256_64_hex'],
                             'equals_the_probe_row_for_that_asset': bool(
                                 (prow.get(b['asset_referenced_by_my_built_index'].lstrip('/')) or {}).get(
                                     'served_sha256') == b['sha256_64_hex']),
                             'served_asset_equals_this_cells_asset': bool(
                                 b['asset_referenced_by_my_built_index'].lstrip('/') == js_path
                                 and b['sha256_64_hex'] == rech['served_now']['asset_sha256_64_hex'])}

out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'order': 'ORD-0312 M3 - generation binding against the new probe',
       'lane': 'HJ-P3 aad2d1f2-4de9-406b-a5df-afa0e2bcea58',
       'scope': 'the front-end asset the phone chain serves, and the per-arm binding of pass-3 readings to it',
       'generation_under_test': probe['generation_under_test'],
       'artifact_read': {'path': PROBE_PATH, 'cited_blob': PROBE_BLOB_CITED,
                         'blob_recomputed_from_bytes_i_read': recomputed,
                         'cited_equals_recomputed': recomputed == PROBE_BLOB_CITED,
                         'bytes': len(raw),
                         'also_on_branch_at_that_path': on_branch.get(PROBE_PATH),
                         'probe_probed_at_local': probe['probed_at_local'],
                         'probe_overall': probe.get('overall'),
                         'probe_serve_root': probe.get('serve_root'),
                         'probe_tunnel_host': probe.get('tunnel_host')},
       'how_read': 'GET /git/blobs/<40hex> over the API and re-hash with the git blob header; the phone chain '
                   'was NOT contacted by this run (my own two reads of it were at 22:0x and 00:1x, GET only)',
       'probe_generation_matches_the_ordered_generation': bool(
           probe['generation_under_test'] == G['dep']['tip']),
       'row_checks': row_checks,
       'per_arm_binding': per_cell,
       'arms_bound': len(per_cell),
       'arms_on_the_served_generation': sum(1 for v in per_cell.values() if v['served_asset_equals_this_cells_asset']),
       'limit_named': 'M3 is closed for the JS asset row, which I fetched twice myself and which matches his '
                      'probe byte for byte. The CSS and the service-worker rows are HIS readings, not mine: '
                      'my cells do not depend on them, so I do not claim them as verified here.',
       'verdict': {
           'the_cited_probe_blob_resolves_and_matches_its_bytes': bool(
               on_branch.get(PROBE_PATH) == PROBE_BLOB_CITED and recomputed == PROBE_BLOB_CITED),
           'the_probe_pins_the_generation_my_arms_ran_on': bool(
               probe['generation_under_test'] == G['dep']['tip']),
           'my_two_own_reads_of_the_served_asset_agree': row_checks['js_asset_i_read_myself']['my_two_reads_agree'],
           'the_probe_row_equals_my_own_read_byte_for_byte': bool(
               row_checks['js_asset_i_read_myself']['probe_equals_my_22_0x_read']
               and row_checks['js_asset_i_read_myself']['probe_equals_my_00_1x_read']),
           'every_pass3_arm_names_its_asset_and_sha256': all(
               v['asset_named_by_my_build'] and len(v['asset_sha256_64_hex']) == 64 for v in per_cell.values()),
           'arms_measured_on_the_served_generation_match_it': bool(
               sum(1 for v in per_cell.values() if v['served_asset_equals_this_cells_asset'])
               == sum(1 for r in SC['arms_scored'] if r['gen'] == 'dep'))}}
out['verdict']['ALL_HOLD'] = all(v for k, v in out['verdict'].items() if k != 'ALL_HOLD')
(OUT / 'ord0312_m3_binding_reread.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                    encoding='utf-8', newline='\n')
print(json.dumps(out['verdict'], ensure_ascii=False))
print('probe rows:', json.dumps([r['path'] for r in probe['rows']], ensure_ascii=False))
print('js row mine vs probe:', json.dumps(
    {k: v for k, v in row_checks['js_asset_i_read_myself'].items() if k.startswith(('probe_equals', 'my_two'))},
    ensure_ascii=False))
print('arms on served generation:', out['arms_on_the_served_generation'], '/', out['arms_bound'])
