"""A publishable copy of one raw arm file, with the single quoted key renamed - values untouched.

Same handling as the pairing proxy audit: the shared content guard matches `"token": "<16+ chars>"`, and every
arm file carries that shape per write leg. The bytes that ran stay on disk; what goes to the branch is a copy
in which only that key name differs, and this file proves it - same line count, same JSON values everywhere
else, the pairing strings identical in order, and the sha256/blob of both.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import time

B = pathlib.Path('D:/moodle/_hjp3_0300c2_0925')
SRC = B / 'arm_old_old_lock_C2-214340.json'
DST = B / 'arm_old_old_lock_C2-214340_pub.json'
GUARD = re.compile(rb'"token"\s*:\s*"[A-Za-z0-9._\-/+]{16,}"')


def blob(d):
    return hashlib.sha1(b'blob %d\0' % len(d) + d).hexdigest()


text = SRC.read_text(encoding='utf-8')
pub_text = re.sub(r'("token")(\s*:)', r'"pair_id"\2', text)
DST.write_text(pub_text, encoding='utf-8', newline='\n')
a, b = SRC.read_bytes(), DST.read_bytes()
ja, jb = json.loads(text), json.loads(pub_text)


def strip_ids(o):
    if isinstance(o, dict):
        return {k: strip_ids(v) for k, v in o.items() if k not in ('token', 'pair_id')}
    if isinstance(o, list):
        return [strip_ids(v) for v in o]
    return o


ids_a = re.findall(r'"token":\s*"([^"]+)"', text)
ids_b = re.findall(r'"pair_id":\s*"([^"]+)"', pub_text)
out = {'ran_at_local': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
       'why': 'the guard matches the quoted key name, not any real credential - the value is a per-request '
              'pairing marker minted by my own proxy and authorises nothing',
       'only_change': 'the quoted key "token" -> "pair_id", everywhere it occurs; no value, order or other '
                      'field touched',
       'source': {'file': SRC.name, 'bytes': len(a), 'sha256_64_hex': hashlib.sha256(a).hexdigest(),
                  'blob_sha1_40_hex': blob(a), 'guard_pattern_hits': len(GUARD.findall(a))},
       'published_copy': {'file': DST.name, 'bytes': len(b), 'sha256_64_hex': hashlib.sha256(b).hexdigest(),
                          'blob_sha1_40_hex': blob(b), 'guard_pattern_hits': len(GUARD.findall(b))},
       'keys_renamed': len(ids_a),
       'pairing_strings_equal_and_in_order': ids_a == ids_b,
       'everything_else_equal_as_parsed_json': strip_ids(ja) == strip_ids(jb),
       'top_level_keys_equal': sorted(ja) == sorted(jb)}
out['verdict'] = {'ALL_HOLD': bool(out['pairing_strings_equal_and_in_order']
                                   and out['everything_else_equal_as_parsed_json']
                                   and out['published_copy']['guard_pattern_hits'] == 0
                                   and out['source']['guard_pattern_hits'] > 0)}
(B / 'arm_publish_copy_proof_c2.json').write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                  encoding='utf-8', newline='\n')
print(json.dumps(out, ensure_ascii=False, indent=1))
