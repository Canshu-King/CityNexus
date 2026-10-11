# -*- coding: utf-8 -*-
"""Compare the dictionary's resolved copy, through its own non-hook exit, against the eight literal
pairs as they sat on the tip -- byte for byte, both locales. Lines are read out of the tip file, so no
string in this script is transcribed by hand."""

import io
import json
import re

BEFORE = r"D:\moodle\_jz_0576\before_TripItinerary.tsx"
RESOLVED = r"D:\moodle\_jz_0576\resolved_dict_copy.json"
OUT = r"D:\moodle\_jz_0576\byte_proof_r1.txt"

# (key, tip line of the zh arm, tip line of the en arm) -- the eight re-pointed reads
PAIRS = [
    ("itinerary.planWithAiNeedsPlaces", 294, 295),
    ("itinerary.planWithAi", 297, 298),
    ("itinerary.emptyPlanNoDays", 308, 309),
    ("itinerary.emptyNoPlan", 311, 312),
    ("itinerary.emptyReadingPlaces", 317, 318),
    ("itinerary.lengthUnknown", 386, 387),
    ("itinerary.dayByDay", 394, 395),
    ("itinerary.stopDisrupted", 515, 516),
]

LIT = re.compile(r'"((?:[^"\\\n]|\\.)*)"')


def arm(path, lineno):
    lines = io.open(path, encoding="utf-8").read().split("\n")
    raw = lines[lineno - 1]
    m = LIT.search(raw)
    if not m:
        raise SystemExit("ABORT no string literal on tip line %d of %s :: %r" % (lineno, path, raw[:60]))
    return m.group(1).encode().decode("unicode_escape") if "\\u" in m.group(1) else m.group(1)


def main():
    src = io.open(BEFORE, encoding="utf-8").read().split("\n")
    # the zh arm in the source is a JS string; JS and Python agree on these (no escapes used)
    got = json.load(io.open(RESOLVED, encoding="utf-8"))
    lines = ["ORD-0576 批一 加闸工 逐字节对拍（现尖那八对原文 vs 字典真出口 dictionaryCopy 解析值）"]
    bad = 0
    for i, (key, zl, el) in enumerate(PAIRS, 1):
        zh_old = LIT.search(src[zl - 1]).group(1)
        en_old = LIT.search(src[el - 1]).group(1)
        pair = got.get(key)
        if not pair:
            lines.append("%d MISSING resolved value for %s" % (i, key))
            bad += 1
            continue
        okz = pair["zh"] == zh_old
        oke = pair["en"] == en_old
        if not (okz and oke):
            bad += 1
        lines.append("%d %s zh %s (tip :%d) en %s (tip :%d)%s" % (
            i, "OK  " if (okz and oke) else "DIFF",
            "同文" if okz else "异文", zl,
            "同文" if oke else "异文", el,
            "" if (okz and oke) else "  <- zh 解析=%r 期望=%r / en 解析=%r 期望=%r" % (pair["zh"], zh_old, pair["en"], en_old)))
    lines.append("合计 8 处：逐字节同文 %d 处，异文 %d 处" % (8 - bad, bad))
    lines.append("跑法：node_modules/.bin/esbuild 探针 --bundle --platform=node --format=cjs 后 node 真跑 dictionaryCopy(locale,key)，探针取自 frontend/src/i18n/LocaleContext.tsx:2879")
    text = "\n".join(lines) + "\n"
    io.open(OUT, "w", encoding="utf-8", newline="").write(text)
    print(text)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
