# -*- coding: utf-8 -*-
"""ORD-0570 复核：那页 CN 草稿里属于 pendingSetCopy.ts 的每一行，逐行与现尖上模块自己的两臂对一次。
只读分析，不改产品码。坐标全部现取（草稿那列行号是旧尖一代的，搬动之后已经错位）。"""
from __future__ import print_function

import io
import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
TIP = "f219dfef4ddc5addcdeb73e65cfac95f4ae7ab1c"
REL = "frontend/src/features/pending/pendingSetCopy.ts"
DRAFT = "D:/moodle/_cn19_copydraft_0213.txt"
OUT = "D:/moodle/_qoder_lupaigongjia_0570/review/lupaigongjia-0570/draft_review_0570_r1.txt"
MIGRATED = {"pending.title", "pending.sub", "pending.loading"}

KEYROW = re.compile(u'^\\s*"([^"]+)":\\s*(?:"((?:[^"\\\\]|\\\\.)*)"|\\s*$)', 0)


def show(rev, path):
    p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, path)],
                       capture_output=True)
    if p.returncode:
        sys.exit("ABORT git show rc=%d %s" % (p.returncode, p.stderr[:200]))
    return p.stdout.decode("utf-8")


def parse_tables(src):
    u"""Return {key: {'en': (line, value), 'zh': (line, value)}} for the module's own two halves.

    A value may sit on the line after the key (`"pending.deleteDayRule":` then the string), so a
    key row without a value stays pending until the next row that opens with a quote closes it."""
    lines = src.split("\n")
    halves = {}
    cur = None
    pending = None
    for idx, raw in enumerate(lines, 1):
        s = raw.strip()
        if s.startswith("en: {") or s.startswith('"en": {'):
            cur = "en"
            continue
        if s.startswith('"zh-CN": {') or s.startswith("zhCN: {") or s.startswith("zh: {"):
            cur = "zh"
            continue
        if cur is None:
            continue
        m = KEYROW.match(raw)
        if m:
            key, value = m.group(1), m.group(2)
            if value is None:
                pending = key
            else:
                halves.setdefault(key, {})[cur] = (idx, value)
                pending = None
            continue
        if s.startswith('"') and pending is not None:
            v = re.match(u'^"((?:[^"\\\\]|\\\\.)*)"\\s*,?\\s*$', s)
            if v is None:
                sys.exit("ABORT continuation row not parseable at line %d: %r" % (idx, s[:60]))
            halves.setdefault(pending, {})[cur] = (idx, v.group(1))
            pending = None
    return halves


src = show(TIP, REL)
tab = parse_tables(src)

rows = []
for raw in io.open(DRAFT, encoding="utf-8").read().split("\n"):
    if "pendingSetCopy.ts" not in raw:
        continue
    parts = [x.strip() for x in raw.split("|")]
    if len(parts) != 4:
        continue
    rows.append(parts)

out = [u"# 草稿复核 tip=%s 模块=%s 草稿行=%d" % (TIP, REL, len(rows))]
agree = differ = missing_zh = missing_en = casemangle = 0
for key, zh, en, old_coord in rows:
    got = tab.get(key, {})
    zh_row, en_row = got.get("zh"), got.get("en")
    if key in MIGRATED:
        out.append(u"MIGRATED %s | 草稿 %s | 本轮已搬进字典两侧，模块里两臂都删了（现尖 %s 已无此行）"
                   % (key, old_coord, REL))
        continue
    if zh_row is None or en_row is None:
        head, _, tail = key.rpartition(".")
        real = "%s.%s" % (head, tail.upper())
        got_real = tab.get(real, {})
        if real in tab and got_real.get("zh") and got_real.get("en"):
            casemangle += 1
            out.append(u"CASEMANGLE %s | 草稿 %s | 模块里真有这枚键，是 %s（现尖 zh:%d en:%d）—— 照草稿键名落笔会新建一枚撞不上取词点的键"
                       % (key, old_coord, real, got_real["zh"][0], got_real["en"][0]))
            continue
        missing_zh += zh_row is None
        missing_en += en_row is None
        out.append(u"NOTFOUND %s | 草稿 %s | 模块现读 zh=%s en=%s"
                   % (key, old_coord, zh_row and zh_row[0], en_row and en_row[0]))
        continue
    if en_row[1] == en:
        agree += 1
        out.append(u"MATCH    %s | 现尖 zh:%d en:%d | 建议英文与模块 en 臂逐字相同" % (key, zh_row[0], en_row[0]))
    else:
        differ += 1
        out.append(u"DIFF     %s | 现尖 zh:%d en:%d | 模块 en 臂=%r | 草稿建议=%r"
                   % (key, zh_row[0], en_row[0], en_row[1], en))

out.append(u"# 合计：MATCH %d、DIFF %d、CASEMANGLE %d、NOTFOUND %d（zh 缺 %d / en 缺 %d）、已搬 %d"
           % (agree, differ, casemangle, missing_zh + missing_en, missing_zh, missing_en, len(MIGRATED)))
io.open(OUT, "w", encoding="utf-8", newline="\n").write(u"\n".join(out) + u"\n")
print("WROTE %s rows=%d" % (OUT, len(out)))
