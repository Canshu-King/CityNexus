"""Verify the ORD-0279 offset coordinate the red team corrected: char index vs byte index.

My published reading used `str.index()` on DECODED text, which counts UTF-16/unicode characters, not
bytes - so on a bundle containing CJK literals it is smaller than the byte offset.  This prints both, for
the asset I actually measured and for the asset now being served, so the was/now line is a measurement
rather than an argument.
"""
from __future__ import annotations

import hashlib
import io
import json
import pathlib

ASSETS = {
    'measured_in_ORD-0279 (ChOTTCvB)':
        pathlib.Path('D:/moodle/_hjp3_fan_sweep_0923/snap_live_dist/assets/index-ChOTTCvB.js'),
    'now served (CtuiCkKf, frozen)':
        pathlib.Path('D:/moodle/_hjp3_0276_0925/dist_frozen/assets/index-CtuiCkKf.js'),
}
NEEDLE = 'async function vb('
GUARD = 'if(r!=="GET"&&r!=="HEAD")return fetch(t,e);'
out = {}
for label, p in ASSETS.items():
    if not p.exists():
        out[label] = {'missing': True}
        continue
    raw = p.read_bytes()
    txt = raw.decode('utf-8')
    ci = txt.index(NEEDLE)
    bi = raw.index(NEEDLE.encode())
    gi_c = txt.index(GUARD)
    gi_b = raw.index(GUARD.encode())
    out[label] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                  'vb_char_index': ci, 'vb_byte_offset': bi,
                  'guard_char_index': gi_c, 'guard_byte_offset': gi_b,
                  'multibyte_chars_before_vb': bi - ci,
                  'read_deadline_constant': txt[txt.rindex('pb=', 0, ci):txt.rindex('pb=', 0, ci) + 8]
                                            if 'pb=' in txt[:ci] else None}
pathlib.Path('D:/moodle/_hjp3_0281_0925/offset_check.json').parent.mkdir(exist_ok=True)
pathlib.Path('D:/moodle/_hjp3_0281_0925/offset_check.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(out, ensure_ascii=False, indent=1))
