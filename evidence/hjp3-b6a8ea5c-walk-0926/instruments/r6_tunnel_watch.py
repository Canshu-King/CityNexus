"""Is the public tunnel entry still up? Three samples against one control on the local hop.

My five cells were walked over the address the commander published, and that address answered 530 when I came back
to re-read the bundle after finishing - so before anyone grades those readings, the record needs to say which
entry was alive at which minute, and whether the phone's own hop was still serving the same bytes at the same time.
Cloudflare 530 is an orchestrator/origin failure, not my client's, and the three samples each carry a distinct
cf-ray id, which is what separates a one-shot blip from a state.

Read-only GETs, no credentials beyond the basic-auth header the entry requires, 0 writes, nothing repaired.
"""
from __future__ import annotations

import base64
import json
import pathlib
import time
import urllib.error
import urllib.request

OUT = pathlib.Path('D:/moodle/_hjp3_b6a8_0926')
PUB = 'https://administrator-personality-supervisor-peers.trycloudflare.com'
LOC = 'http://127.0.0.1:4781'
parts = [x for x in pathlib.Path('D:/moodle/_qoder_preview_20260920/run/preview_auth.txt').read_text(
    encoding='utf-8').split() if x]
BASIC = 'Basic ' + base64.b64encode(('%s:%s' % (parts[0], parts[1])).encode()).decode()
DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def hit(base, path, auth):
    r = urllib.request.Request(base + path)
    r.add_header('User-Agent', 'hjp3-r6-tunnel-watch')
    if auth:
        r.add_header('Authorization', BASIC)
    t0 = time.time()
    try:
        with DIRECT.open(r, timeout=40) as f:
            b = f.read()
            return {'path': path, 'status': f.status, 'bytes': len(b), 'server': f.headers.get('server'),
                    'cf_ray': f.headers.get('cf-ray'), 'elapsed_ms': int((time.time() - t0) * 1000)}
    except urllib.error.HTTPError as e:
        b = e.read()
        return {'path': path, 'status': e.code, 'bytes': len(b), 'server': e.headers.get('server'),
                'cf_ray': e.headers.get('cf-ray'), 'elapsed_ms': int((time.time() - t0) * 1000)}
    except Exception as e:  # noqa: BLE001
        return {'path': path, 'status': None, 'error': type(e).__name__ + ': ' + str(e)[:80],
                'elapsed_ms': int((time.time() - t0) * 1000)}


public = [hit(PUB, '/', True) for _ in range(3)]
time.sleep(1)
local = [hit(LOC, '/', False), hit(LOC, '/api/v1/health', False)]
gc = json.loads((OUT / 'r6_gen_check.json').read_text(encoding='utf-8'))
walked_asset = gc['entry_points'][0]['asset_named_by_the_shell']
walked_bytes = (gc['entry_points'][0]['asset_row'] or {}).get('bytes')
asset = hit(LOC, walked_asset, False)
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'method': 'three GETs of the published tunnel entry plus two GETs of the local hop, no-proxy opener, '
                 'basic auth from the named file',
       'public_entry': PUB, 'local_hop': LOC,
       'public_samples': public, 'local_samples': local + [asset],
       'walked_asset': walked_asset, 'walked_asset_bytes': walked_bytes,
       'distinct_cf_ray_ids': sorted({x.get('cf_ray') for x in public if x.get('cf_ray')}),
       'verdict': {
           'public_entry_answered_530_on_every_sample': all(x['status'] == 530 for x in public),
           'the_three_samples_are_three_separate_requests': len({x.get('cf_ray') for x in public
                                                                if x.get('cf_ray')}) == 3,
           'the_local_hop_is_serving_normally': bool(local[0]['status'] == 200 and local[1]['status'] == 200),
           'the_bundle_i_walked_is_still_on_the_local_hop': bool(
               asset.get('status') == 200 and asset.get('bytes') == walked_bytes)}}
blob = json.dumps(out, ensure_ascii=False, indent=1)
assert parts[1] not in blob, 'the secret would have been written into the artefact'
(OUT / 'r6_tunnel_watch.json').write_text(blob, encoding='utf-8', newline='\n')
print(json.dumps(out['verdict'], ensure_ascii=False, indent=1))
print('public:', [(x['status'], x['bytes'], x.get('cf_ray')) for x in public])
print('local:', [(x['path'], x['status'], x['bytes']) for x in local + [asset]])
