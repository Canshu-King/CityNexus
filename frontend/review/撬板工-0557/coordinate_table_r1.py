# -*- coding: utf-8 -*-
u"""逐枚坐标表：改前（现尖字节）/ 改后（本枝字节）/ 字典两侧，全部现读，不抄账本。

用法：python coordinate_table_r1.py <前端根>
输出：stdout 与 <前端根>/review/撬板工-0557/coordinate_table_r1.txt 同一份数。
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys

REPO = r"D:\moodle\CityNexus"
TIP = "08577f1986b8bbc095f1c319a952909fcf343717"
PAIRS = [
    ("legacy.persistedOperationUpdate", "Persisted operation update"),
    ("legacy.generalRecovery", "general recovery"),
    ("legacy.standingMissionHint", "Activate a standing mission once; subsequent city signals can launch recovery without a new chat message."),
    ("legacy.noDominantFailureMode", "No dominant failure mode"),
    ("legacy.notEvaluated", "not evaluated"),
    ("legacy.validatedActivity", "validated Activity"),
    ("legacy.noActionableTarget", "no actionable target"),
    ("legacy.outcomeEvidence", "outcome evidence"),
    ("legacy.explicitWins", "explicit wins"),
    ("legacy.notReported", "not reported"),
    ("legacy.noUpcomingActivity", "no upcoming activity"),
    ("legacy.noActiveC4", "No active C4"),
    ("legacy.notAvailable", "not available"),
    ("legacy.unnamedCommitment", u"未命名承诺 · 服务器没给名字"),
    ("legacy.verifiedFeasible", "verified feasible"),
    ("legacy.notFeasible", "not feasible"),
    ("legacy.notPreserved", "not preserved"),
    ("legacy.verifiedEvidenceAttached", "verified evidence attached"),
    ("legacy.evidenceUnavailable", "evidence unavailable"),
]
NOT_MOVED = [
    (u"CityNexus request failed", "模块层 errorNote()，该文件此处无取词钩子"),
    (u"CityNexus request refused (HTTP ${status})", "同上，且带插值"),
]


def tip_lines(rel, tip=TIP):
    p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (tip, rel)], capture_output=True)
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace").split("\n")


def find(lines, needle, startswith=False):
    hits = []
    for i, ln in enumerate(lines or [], 1):
        if (ln.strip().startswith(needle) if startswith else needle in ln):
            hits.append(i)
    return hits


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--tip", default=TIP)
    a = ap.parse_args(argv)
    fe = a.root
    mn = os.path.join(fe, "src", "main.tsx")
    dic = os.path.join(fe, "src", "i18n", "LocaleContext.tsx")
    cand = io.open(mn, encoding="utf-8").read().split("\n")
    dictc = io.open(dic, encoding="utf-8").read().split("\n")
    tip_m = tip_lines("frontend/src/main.tsx", a.tip)
    out = []
    out.append(u"改前列取自 %s 这枚现尖对象里的 frontend/src/main.tsx；改后列取自本枝工作树。" % a.tip)
    out.append(u"%-34s %-12s %-12s %-12s %s" % ("键名", "改前行", "改后行", "en 字典行", "zhCN 字典行"))
    bad = 0
    for key, literal in PAIRS:
        before = find(tip_m, '"%s"' % literal) or find(tip_m, literal)
        after = find(cand, 't("%s")' % key)
        en = find(dictc[:dictc.index(next(l for l in dictc if l.startswith("const zhCN: Dict")))], '"%s":' % key)
        zh = find(dictc[dictc.index(next(l for l in dictc if l.startswith("const zhCN: Dict"))) + 1:], '"%s":' % key)
        zh_line = [z + dictc.index(next(l for l in dictc if l.startswith("const zhCN: Dict"))) + 1 for z in zh]
        ok = len(before) >= 1 and len(after) == 1 and len(en) == 1 and len(zh_line) == 1
        if not ok:
            bad += 1
        out.append(u"%-34s %-12s %-12s %-12s %s%s" % (
            key,
            ",".join(str(x) for x in before) or u"读不出",
            ",".join(str(x) for x in after) or u"读不出",
            en[0] if en else u"读不出",
            zh_line[0] if zh_line else u"读不出",
            u"" if ok else u"   ← 这一枚四列没齐"))
    out.append(u"逐枚四列齐的 %d 枚，不齐 %d 枚（分母 %d 枚）" % (len(PAIRS) - bad, bad, len(PAIRS)))
    out.append(u"本单没搬走的（表里点了名、但落在模块层，等号令者裁『透传取词函数』那一档）：")
    for literal, why in NOT_MOVED:
        hits = find(tip_m, literal)
        hits2 = find(cand, literal)
        out.append(u"  %r｜改前行 %s｜本枝行 %s（仍在原处）｜成因：%s" % (literal, hits, hits2, why))
    text = "\n".join(out) + "\n"
    io.open(os.path.join(fe, "review", u"撬板工-0557", "coordinate_table_r1.txt"), "w", encoding="utf-8").write(text)
    sys.stdout.write(text)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
