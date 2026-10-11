# -*- coding: utf-8 -*-
"""ORD-0585 delta: dictionary key counts tip-vs-tree and the visible-CJK / inline-pair counts on the
file I edited, using the commander's own regexes imported from his ruler."""
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
TIP = "a368e12313b505d444c871cb79375339f72a6c5c"
DICT = "frontend/src/i18n/LocaleContext.tsx"
TARGET = "frontend/src/features/recovery/V14RecoveryTruthPanel.tsx"
OUT = os.path.join(WT, "delta_0585_r1.txt")
KEYROW = re.compile(u'^\\s*"([^"]+)":\\s*"((?:[^"\\\\]|\\\\.)*)"\\s*,?\\s*$')
PAIR = re.compile(u'zh\\s*\\?\\s*"((?:[^"\\\\]|\\\\.)*)"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"')


def get(rel, rev=None):
    if rev:
        p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, rel)], capture_output=True)
        if p.returncode:
            sys.exit("ABORT git show " + rel)
        return p.stdout.decode("utf-8")
    return io.open(os.path.join(WT, rel.replace("/", os.sep)), encoding="utf-8").read()


def halves(src):
    i, j, k = (src.index("const en: Dict"), src.index("const zhCN: Dict"), src.index("const dictionaries"))
    out = {}
    for name, chunk in (("en", src[i:j]), ("zh", src[j:k])):
        d = {}
        for line in chunk.split("\n"):
            s = line.strip()
            if s.startswith("//") or s.startswith("*"):
                continue
            m = KEYROW.match(line)
            if m:
                d[m.group(1)] = m.group(2)
        out[name] = d
    return out


h_t, h_m = halves(get(DICT, TIP)), halves(get(DICT))
assert len(h_t["en"]) > 1000 and len(h_t["zh"]) > 1000, "dictionary parse blind: %d/%d" % (
    len(h_t["en"]), len(h_t["zh"]))
lines = [u"ORD-0585 delta  尖 %s vs 本树" % TIP[:10], u"",
         u"字典键数：尖 en=%d zh=%d ；本树 en=%d zh=%d" % (len(h_t["en"]), len(h_t["zh"]), len(h_m["en"]), len(h_m["zh"])),
         u"本树新增 en=%d zh=%d，删除 en=%d zh=%d" % (len(set(h_m["en"]) - set(h_t["en"])),
                                                     len(set(h_m["zh"]) - set(h_t["zh"])),
                                                     len(set(h_t["en"]) - set(h_m["en"])),
                                                     len(set(h_t["zh"]) - set(h_m["zh"]))),
         u"新增键名：%s" % u", ".join(sorted(set(h_m["en"]) - set(h_t["en"]))),
         u"尖上对称差=%s ；本树对称差=%s" % (sorted(set(h_t["en"]) ^ set(h_t["zh"])), sorted(set(h_m["en"]) ^ set(h_m["zh"])))]

t = u"\n".join(ruler.strip_comments(get(TARGET, TIP)))
m = u"\n".join(ruler.strip_comments(get(TARGET)))
ct = sum(1 for ln in t.split("\n") if ruler.CJK.search(ln))
cm = sum(1 for ln in m.split("\n") if ruler.CJK.search(ln))
lines += [u"", u"%s" % TARGET,
          u"  带汉字的可见行：尖=%d 本树=%d（差 %+d）" % (ct, cm, cm - ct),
          u"  同形成对（zh ? 「中」 : 「英」）：尖=%d 本树=%d（差 %+d）" % (len(PAIR.findall(t)), len(PAIR.findall(m)),
                                                                       len(PAIR.findall(m)) - len(PAIR.findall(t)))]
io.open(OUT, "w", encoding="utf-8", newline="\n").write(u"\n".join(lines) + u"\n")
print("WROTE " + OUT)
