# -*- coding: utf-8 -*-
"""ORD-0576 delta: dictionary key counts tip-vs-tree, and the visible-CJK / inline-pair counts on the
two files I edited, using the commander's own regexes imported from his ruler."""
from __future__ import print_function

import io
import os
import re
import subprocess
import sys

sys.path.insert(0, r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
import _cmdr_inline_literal_cjk_r2 as ruler  # noqa: E402

WT = r"D:\moodle\_qoder_lupaigongjia_0576"
REPO = "D:/moodle/CityNexus"
TIP = "8a44ea61aeb81d999a17913a18828b725ea463f2"
DICT = "frontend/src/i18n/LocaleContext.tsx"
FILES = ["frontend/src/features/discovery/DestinationPreparationPanel.tsx",
         "frontend/src/features/checklist/PretripChecklistPanel.tsx"]
OUT = os.path.join(WT, "delta_0576_r1.txt")
KEY = re.compile(u'^\\s*"([^"]+)":\\s*"((?:[^"\\\\]|\\\\.)*)"\\s*,?\\s*$')


def show(rel, rev=None):
    if rev:
        p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, rel)], capture_output=True)
        if p.returncode:
            sys.exit("ABORT git show %s" % rel)
        return p.stdout.decode("utf-8")
    return io.open(os.path.join(WT, rel.replace("/", os.sep)), encoding="utf-8").read()


def halves(src):
    i = src.index("const en: Dict")
    j = src.index("const zhCN: Dict")
    k = src.index("const dictionaries")
    out = {}
    for name, chunk in (("en", src[i:j]), ("zh", src[j:k])):
        d = {}
        for line in chunk.split("\n"):
            s = line.strip()
            if s.startswith("//") or s.startswith("*"):
                continue
            m = KEY.match(line)
            if m:
                d[m.group(1)] = m.group(2)
        out[name] = d
    return out


lines = []
_th = halves(show(DICT, TIP))
_mh = halves(show(DICT))
tip_en, tip_zh = _th["en"], _th["zh"]
my_en, my_zh = _mh["en"], _mh["zh"]
assert len(tip_en) > 1000 and len(tip_zh) > 1000, "dictionary parse produced %d/%d keys -- instrument is blind" % (
    len(tip_en), len(tip_zh))
lines.append(u"字典键数：尖 en=%d zh=%d ；本树 en=%d zh=%d" % (len(tip_en), len(tip_zh), len(my_en), len(my_zh)))
lines.append(u"本树新增 en=%d zh=%d，删除 en=%d zh=%d" % (
    len(set(my_en) - set(tip_en)), len(set(my_zh) - set(tip_zh)),
    len(set(tip_en) - set(my_en)), len(set(tip_zh) - set(my_zh))))
lines.append(u"新增键名：%s" % u", ".join(sorted(set(my_en) - set(tip_en))))
lines.append(u"两侧对称差：%s" % (sorted(set(my_en) ^ set(my_zh)) or u"空"))
lines.append(u"尖上对称差：%s" % (sorted(set(tip_en) ^ set(tip_zh)) or u"空"))
lines.append(u"")

PAIR = re.compile(u'zh\\s*\\?\\s*"((?:[^"\\\\]|\\\\.)*)"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"')
for rel in FILES:
    t = show(rel, TIP)
    m = show(rel)
    ht = u"\n".join(ruler.strip_comments(t))
    hm = u"\n".join(ruler.strip_comments(m))
    ct = sum(1 for ln in ht.split("\n") if ruler.CJK.search(ln))
    cm = sum(1 for ln in hm.split("\n") if ruler.CJK.search(ln))
    pt = len(PAIR.findall(ht))
    pm = len(PAIR.findall(hm))
    lines.append(u"%s" % rel)
    lines.append(u"  带汉字的可见行：尖=%d 本树=%d（差 %+d）" % (ct, cm, cm - ct))
    lines.append(u"  同形成对（zh ? 「中」 : 「英」）：尖=%d 本树=%d（差 %+d）" % (pt, pm, pm - pt))
io.open(OUT, "w", encoding="utf-8", newline="\n").write(u"\n".join(lines) + u"\n")
print("WROTE " + OUT)
for l in lines:
    print(l.encode("utf-8").decode("utf-8") if False else "")
