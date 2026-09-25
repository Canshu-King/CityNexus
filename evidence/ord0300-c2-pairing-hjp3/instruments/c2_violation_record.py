"""Self-report: I re-PUT a published path again, and this time the cause is my own publisher's tail stage.

`c2_publish.py` sends the batch through an identical-or-refuse gate, but the `manifest` stage calls the raw
publisher directly - the same hole that produced the ORD-0288 violation the commander already logged. So when
the manifest was regenerated over a larger final path set, it landed on a path that had already been published,
and the first copy's listing (70 files) was replaced by a newer one (87 files) under the same name.

Nothing is hidden and nothing is "restored by overwriting a third time": both commits and both blobs are
recorded here with the retrieval route for the older bytes, the tool is fixed so the stage cannot bypass the
gate again, and the fixed instrument goes out under a revision name while the version that ran stays published.
"""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import time
import urllib.parse
import urllib.request

B = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
TOK = pathlib.Path('D:/moodle/_qoder_recovery_20260919/.api_tok_20260920').read_text(
    encoding='utf-8').strip()
P = 'Canshu-King/CityNexus'
PATH = 'evidence/ord0300-c2-pairing-hjp3/evidence_manifest_full40_c2.json'
BLOBS = {'first': '983e39b6072a00569b61bbe23bdec38377a670ce',
         'second': '3f7b2cd25a0a5ac5215c789942094ef09eda92d4'}
COMMITS = {'first': 'eb719aa8d30cfb64292d4e7ca3cb399a1b6f76b9',
           'second': '1751bb51a2f40242f1c5dbe164c63b50d15e1a79'}


def gh(path):
    r = urllib.request.Request('https://api.github.com' + path)
    r.add_header('Authorization', 'Bearer ' + TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'hjp3-0300c2-violation')
    with urllib.request.urlopen(r, timeout=180) as f:
        return json.loads(f.read().decode())


def read_blob(sha):
    o = gh('/repos/%s/git/blobs/%s' % (P, sha))
    raw = base64.b64decode(o['content'])
    return raw, hashlib.sha1(b'blob %d\0' % len(raw) + raw).hexdigest() == sha


side = {}
for tag, sha in BLOBS.items():
    raw, ok = read_blob(sha)
    d = json.loads(raw.decode('utf-8'))
    side[tag] = {'blob_40_hex': sha, 'bytes': len(raw), 'sha1_recomputes_from_fetched_bytes': ok,
                 'commit_40_hex': COMMITS[tag], 'files_listed_inside': d['count'],
                 'tip_it_listed': d['commit_tip'], 'generated_at_local': d['generated_at_local'],
                 'how_to_retrieve': 'GET /repos/%s/git/blobs/%s (still addressable), or the file at commit %s'
                                    % (P, sha, COMMITS[tag])}
hist = gh('/repos/%s/commits?sha=commander/control&path=%s&per_page=100'
          % (P, urllib.parse.quote(PATH, safe='')))
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'lane': 'HJ-P3 aad2d1f2',
       'what_i_did': 'wrote a path that had already been published, with different bytes, under the same name',
       'path': PATH,
       'writes_this_path_now_has': len(hist),
       'commit_list_from_the_branch': [{'sha': c['sha'], 'at': c['commit']['committer']['date'],
                                        'msg': c['commit']['message'].splitlines()[0][:70]} for c in hist],
       'the_two_copies': side,
       'bytes_actually_lost': 'none - git keeps both blobs and both commits; the first copy is still '
                              'retrievable by blob id or by checking the file out at its commit',
       'root_cause': 'the `manifest` stage of c2_publish.py calls the low-level publisher directly instead of '
                     'going through the batch gate, exactly the hole the commander named in ORD-0288 '
                     '(`Q57` proposal). The gate is the only thing that refuses a same-name/different-bytes '
                     'write, and a direct call cannot see it.',
       'fix_applied_in_the_tool': 'c2_publish.py now routes the manifest and md stages through the same '
                                  'identical-or-refuse gate, so a revision can only ever land under a new '
                                  'name; the version that ran stays published as an instrument revision',
       'what_i_did_not_do': 'no revert, no third write over the same path to "put the old bytes back", no '
                            'deletion - a third write would be the same mistake',
       'this_batch_other_self_report': 'the bus delivery post also went out twice (issuecomment-5832877676 and '
                                       'issuecomment-5832902818) because the script died on a 404 read-back '
                                       'route and I re-ran it; recorded in bus_duplicate_note_c2.json and '
                                       'corrected by issuecomment-5832932960',
       'effect_on_readings': 'none. Every measurement in RECEIPT_O0300C2-1955_r3.json and the pairing that '
                             'lifts the challenged cell is untouched by this; what is damaged is my own '
                             '"已发布路径 0 覆盖" claim for this prefix, and the write ledger now has to say 2 '
                             'for this path instead of 1'}
out['no_longer_true'] = {
    'every_path_in_this_prefix_has_exactly_one_write': False,
    'where_the_honest_reading_lives': 'no_rewrite_proof_c2_r2.json reports this path with 2 writes; the earlier '
                                      'ledger block for this batch asserted 1-for-every-path and is corrected '
                                      'by the addendum rather than edited'}
(B / 'overwrite_violation_c2.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                               encoding='utf-8', newline='\n')
print(json.dumps({'writes': out['writes_this_path_now_has'],
                  'first': side['first']['bytes'], 'second': side['second']['bytes'],
                  'both_recompute': [side[k]['sha1_recomputes_from_fetched_bytes'] for k in side],
                  'listed_files': [side[k]['files_listed_inside'] for k in side]}, ensure_ascii=False))
print('wrote overwrite_violation_c2.json')
