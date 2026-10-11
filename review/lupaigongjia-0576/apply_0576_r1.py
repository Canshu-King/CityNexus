# -*- coding: utf-8 -*-
"""ORD-0576 apply: four traveler-visible inline bilingual pairs -> dictionary keys.

Every replacement is refused unless the old snippet is present exactly once in its file, and the
dictionary insert is refused unless both block tails are found.  Nothing is written unless all
six assertions pass, so a half-applied tree cannot be produced.
"""
from __future__ import print_function

import io
import json
import os
import sys

ROOT = r"D:\moodle\_qoder_lupaigongjia_0576\frontend\src"
PANEL = os.path.join(ROOT, "features", "discovery", "DestinationPreparationPanel.tsx")
CHECK = os.path.join(ROOT, "features", "checklist", "PretripChecklistPanel.tsx")
DICT = os.path.join(ROOT, "i18n", "LocaleContext.tsx")
READ = r"D:\moodle\_qoder_lupaigongjia_0576\apply_0576_r1.txt"

ROWS = [
    ("discovery.checkThisDestination", PANEL,
     u'{checking ? (t("discovery.askingTheServer")) : zh ? "看看能不能规划" : "Check this destination"}',
     u'{checking ? (t("discovery.askingTheServer")) : t("discovery.checkThisDestination")}',
     u"看看能不能规划", u"Check this destination"),
    ("discovery.retryLater", PANEL,
     u'{checking ? (t("discovery.tryingAgain")) : zh ? "稍后重试" : "Try again later"}',
     u'{checking ? (t("discovery.tryingAgain")) : t("discovery.retryLater")}',
     u"稍后重试", u"Try again later"),
    ("discovery.prepareThisDestination", PANEL,
     u'{busy ? (t("discovery.starting")) : zh ? "开始准备" : "Prepare this destination"}',
     u'{busy ? (t("discovery.starting")) : t("discovery.prepareThisDestination")}',
     u"开始准备", u"Prepare this destination"),
    ("detail.pretripScopeNote", CHECK, None, None, None, None),
]

CHECK_OLD = (u'            {zh\n'
             u'              ? "这里只列契约写明依据的两类检查：这一代方案的可行性失败、以及等待你决定的恢复方案。'
             u'完成状态由服务端事实自己消失，不需要你打勾；没跑过的检查不会被打勾，也不会出现在这里。"\n'
             u'              : "Only the two checks whose fields the contract declares live here: feasibility '
             u'failures on this plan generation, and a recovery awaiting your decision. Items disappear when '
             u"the server's fact changes -- nothing is ticked by hand, and a check that was not run is never "
             u'shown as passed and never shown at all."}\n')
CHECK_NEW = u'            {t("detail.pretripScopeNote")}\n'


def read(path):
    return io.open(path, encoding="utf-8", newline="").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def line_of(text, needle):
    i = text.index(needle)
    return text.count("\n", 0, i) + 1


panel = read(PANEL)
check = read(CHECK)
dicts = read(DICT)
log = []

# 1) component side -------------------------------------------------------------
edits = {}
for key, path, old, new, zhv, env in ROWS:
    if path == PANEL:
        body, name = panel, "PANEL"
    else:
        body, name = check, "CHECK"
    if path == CHECK:
        old, new, zhv, env = CHECK_OLD, CHECK_NEW, None, None
    n = body.count(old)
    if n != 1:
        sys.exit("ABORT %s %s: old snippet found %d times, expected 1" % (name, key, n))
    if body.count(new) != 0:
        sys.exit("ABORT %s %s: new snippet already present" % (name, key))
    ln = line_of(body, old)
    edits[key] = (path, old, new, ln)
    log.append(u"REPLACE %s in %s at line %d (bytes_old=%d bytes_new=%d)"
               % (key, os.path.basename(path), ln, len(old.encode("utf-8")), len(new.encode("utf-8"))))

for key, (path, old, new, ln) in edits.items():
    if path == PANEL:
        panel = panel.replace(old, new)
    else:
        check = check.replace(old, new)

# 2) dictionary side ------------------------------------------------------------
EN_HEAD = u"const en: Dict = {"
ZH_HEAD = u"const zhCN: Dict = {"


def block_tail(text, head):
    i = text.index(head)
    j = text.index(u"\n};", i)
    return j + 1  # index of the newline that closes the last key row


en_tail = block_tail(dicts, EN_HEAD)
zh_tail = block_tail(dicts, ZH_HEAD)
pairs = []
for key, path, old, new, zhv, env in ROWS:
    if key == "detail.pretripScopeNote":
        zhv = CHECK_OLD.split(u'? "')[1].split(u'"\n')[0]
        env = CHECK_OLD.split(u': "')[1].split(u'"}\n')[0]
    pairs.append((key, zhv, env))

en_add = u"".join(u'  "%s": "%s",\n' % (k, e.replace(u'"', u'\\"')) for k, _z, e in pairs)
zh_add = u"".join(u'  "%s": "%s",\n' % (k, z.replace(u'"', u'\\"')) for k, z, _e in pairs)
for key, zhv, env in pairs:
    if u'"%s":' % key in dicts:
        sys.exit("ABORT key already in dictionary: " + key)
dicts = dicts[:en_tail] + en_add + dicts[en_tail:]
zh_tail2 = block_tail(dicts, ZH_HEAD)
dicts = dicts[:zh_tail2] + zh_add + dicts[zh_tail2:]

write(PANEL, panel)
write(CHECK, check)
write(DICT, dicts)

# 3) readout --------------------------------------------------------------------
out = [u"ORD-0576 apply readout", u""]
out += log
out.append(u"")
out.append(u"字典插入：en 侧 %d 行、zh 侧 %d 行，各插在本块末尾" % (len(pairs), len(pairs)))
for key, zhv, env in pairs:
    out.append(u"KEY %s" % key)
    out.append(u"  zh_bytes=%d zh=%s" % (len(zhv.encode("utf-8")), zhv))
    out.append(u"  en_bytes=%d en=%s" % (len(env.encode("utf-8")), env))
out.append(u"")
out.append(u"改后行号 PANEL=%s CHECK=%s DICT_en_first=%s DICT_zh_first=%s" % (
    json.dumps([line_of(panel, u't("%s")' % k) for k, _p, _o, _n, _z, _e in ROWS[:3] if k in edits]),
    line_of(check, u'{t("detail.pretripScopeNote")}'),
    line_of(dicts, u'  "%s":' % pairs[0][0]),
    line_of(dicts, u'  "%s": "%s",\n' % (pairs[0][0], pairs[0][1])),
))
io.open(READ, "w", encoding="utf-8", newline="\n").write(u"\n".join(out) + u"\n")
print("OK wrote 3 files; readout %s" % READ)
