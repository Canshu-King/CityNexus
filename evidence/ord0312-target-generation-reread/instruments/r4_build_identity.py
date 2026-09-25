"""Three-way byte identity on the new generation: my build, what the chain serves, and the commander's probe.

M3 asks the readings to name the served asset and match the probe byte for byte. The probe and my own GET already
agreed (`ord0312_m3_binding_reread_gen2.json`). What was still missing is the third corner: whether the bundle
*deployed* on the phone chain is the build of the commit the probe names, as opposed to a bundle that merely
carries that file name. So this lane exported `9a669c8b` read-only, built it into a private outDir, and compares.

Read-only throughout: `git archive` of the tip, a build inside my own directory, one GET of the served page.
"""
from __future__ import annotations

import json
import pathlib
import time

OUT = pathlib.Path('D:/moodle/_hjp3_0312p4_0926')
BASE = pathlib.Path('D:/moodle/_hjp3_0312r_0926')
P312 = 'evidence/ord0312-target-generation-reread'
G2 = json.loads((OUT / 'ord0312_m3_binding_reread_gen2.json').read_text(encoding='utf-8'))
SET = json.loads((BASE / 'setup_facts_gen2.json').read_text(encoding='utf-8'))

build = SET['bundle']
bname = build['asset'].lstrip('/')
js_row = [k for k in G2['per_row_mine_vs_probe'] if k.endswith('.js') and 'sw' not in k][0]
row = G2['per_row_mine_vs_probe'][js_row]
out = {
    'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    'order': 'ORD-0312 M3 - is the deployed bundle the build of the generation the probe names?',
    'lane': 'HJ-P3 aad2d1f2-4de9-406b-a5df-afa0e2bcea58',
    'generation': SET['tip'], 'sheet_blob_expected': SET['sheet_blob_expected'],
    'how_read': 'git archive (read-only) of backend+frontend -> vite build into a private outDir '
                '(%.1f s export + %.1f s build), compared to my own one GET of the served chain and to the '
                'commander\'s probe row; 0 write outside my own directory, 0 credential, 0 database'
                % (SET['seconds_export'], SET['seconds_build']),
    'my_build': {'asset': bname, 'bytes': build['bytes'], 'sha256_64_hex': build['sha256_64_hex'],
                 'sheet_blob_in_the_tree_i_built': SET['export']['sheet_blob_recomputed_40_hex'],
                 'markers': build.get('markers')},
    'my_read_of_the_chain': row['my_read'],
    'commander_probe_row': row['probe_row'],
    'comparisons': {
        'my_build_name_equals_the_served_name': bool(bname.split('/')[-1] == js_row.split('/')[-1]),
        'my_build_bytes_equal_the_served_bytes': bool(build['bytes'] == row['my_read']['bytes']),
        'my_build_sha256_equals_the_served_sha256': bool(
            build['sha256_64_hex'] == row['my_read']['sha256_full']),
        'my_build_sha256_equals_the_probe_row_sha256': bool(
            build['sha256_64_hex'] == row['probe_row']['sha256_full']),
        'the_tree_i_built_carries_the_guarded_sheet_only': bool(
            SET['export']['guarded_detail_reads'] and not SET['export']['unguarded_detail_reads']),
        'sheet_blob_matches_the_tip': SET['export']['sheet_blob_matches_the_generation']},
    'what_this_cannot_claim': 'This is a bundle-identity reading, not a UI reading. My pass-3 arm table still '
                              'belongs to the generation that served before this cutover, so ORD-0312 M3 is '
                              'PARTIAL until those arms are re-run on ' + SET['tip'][:12] + '…',
}
c = out['comparisons']
out['verdict'] = {'deployed_bundle_is_the_build_of_the_named_generation': bool(
    c['my_build_name_equals_the_served_name'] and c['my_build_bytes_equal_the_served_bytes']
    and c['my_build_sha256_equals_the_served_sha256'] and c['my_build_sha256_equals_the_probe_row_sha256'])}
out['verdict']['ALL_HOLD'] = all(out['verdict'].values())
p = OUT / 'ord0312_gen2_build_equals_served.json'
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8', newline='\n')
print('wrote', p.name, p.stat().st_size, 'B')
print(json.dumps(out['comparisons'], ensure_ascii=False, indent=1))
print('verdict:', json.dumps(out['verdict'], ensure_ascii=False))
