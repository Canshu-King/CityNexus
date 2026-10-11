# -*- coding: utf-8 -*-
"""ORD-0585 apply: the one traveler-visible inline pair in V14RecoveryTruthPanel -> dictionary key.
Refuses to write unless every assertion holds (single hit, key free on both sides, tails found)."""
from __future__ import print_function

import io
import os
import sys

WT = r"D:\moodle\_qoder_lupaigongjia_0576"
SRC = os.path.join(WT, "frontend", "src")
PANEL = os.path.join(SRC, "features", "recovery", "V14RecoveryTruthPanel.tsx")
DICT = os.path.join(SRC, "i18n", "LocaleContext.tsx")
READ = os.path.join(WT, "apply_0585_r1.txt")

KEY = u"recovery.acceptanceUnanswered"
ZH = u"这步接受没有得到可确认的答复，结果未知。"
EN = u"This acceptance got no confirmable answer; the result is unknown."
OLD = u'          : zh\n            ? "%s"\n            : "%s",\n' % (ZH, EN)
NEW = u'          : t("%s"),\n' % KEY


def read(path):
    return io.open(path, encoding="utf-8", newline="").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def line_of(text, needle):
    return text.count("\n", 0, text.index(needle)) + 1


panel = read(PANEL)
dicts = read(DICT)

if panel.count(OLD) != 1:
    sys.exit("ABORT old snippet hits %d times, expected 1" % panel.count(OLD))
if panel.count(NEW) != 0:
    sys.exit("ABORT new snippet already present")
if u'"%s":' % KEY in dicts:
    sys.exit("ABORT key already in dictionary: " + KEY)

old_line = line_of(panel, OLD)
panel = panel.replace(OLD, NEW)

EN_HEAD = u"const en: Dict = {"
ZH_HEAD = u"const zhCN: Dict = {"


def tail(text, head):
    i = text.index(head)
    return text.index(u"\n};", i) + 1


en_tail = tail(dicts, EN_HEAD)
dicts = dicts[:en_tail] + u'  "%s": "%s",\n' % (KEY, EN) + dicts[en_tail:]
zh_tail = tail(dicts, ZH_HEAD)
dicts = dicts[:zh_tail] + u'  "%s": "%s",\n' % (KEY, ZH) + dicts[zh_tail:]

write(PANEL, panel)
write(DICT, dicts)

lines = [u"ORD-0585 apply readout", u"",
         u"REPLACE %s in V14RecoveryTruthPanel.tsx at line %d (bytes_old=%d bytes_new=%d)"
         % (KEY, old_line, len(OLD.encode("utf-8")), len(NEW.encode("utf-8"))),
         u"改后组件行号=%d" % line_of(panel, u': t("%s"),' % KEY),
         u"字典 en 行号=%d zh 行号=%d" % (line_of(dicts, u'  "%s": "%s",' % (KEY, EN)),
                                          line_of(dicts, u'  "%s": "%s",' % (KEY, ZH))),
         u"zh_bytes=%d en_bytes=%d" % (len(ZH.encode("utf-8")), len(EN.encode("utf-8")))]
io.open(READ, "w", encoding="utf-8", newline="\n").write(u"\n".join(lines) + u"\n")
print("OK " + READ)
