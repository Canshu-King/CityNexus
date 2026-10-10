# -*- coding: utf-8 -*-
u"""撬板工 0557 的反控尺：验 ORD-0557 交件里 main.tsx 那 19 枚兜底串确实走了字典，且零枚屏上文本被换掉。

用法：python legacy_parity_arm_r1.py <树根>      # 树根指前端根（含 src/）
退出码：0 = 全绿；1 = 有坏格（逐格点名坐标）。

判据分两半，各自说清它盯什么：
  改动那半（A1-A5）：本单要的形状——19 枚串离开 main.tsx 的字面量、进两本字典、两臂逐字等于屏上现字。
  反控那半（C1-C3）：本单**没做**的事仍在原处——两枚模块层串（要透传取词函数那一档，等号令者裁）
                     与两枚不在本单表里的兄弟串。别人做没做自己的活都不影响这三格，所以它们不会
                     被兄弟格改红（教训见账本里 laneE9 的「兄弟格做完了它自己的活，把我的反控读成了红」）。
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys

KEY = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')
KEY_CONT = re.compile(r'^\s*"([^"]+)":\s*$')

# 表里那 21 枚，逐枚：键名 / 屏上现字（照抄，不是重写）/ 改前 main.tsx 行号（现尖 7f08160743）
MOVED = [
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
    ("legacy.notAvailable", "not available", 1),
    ("legacy.unnamedCommitment", u"未命名承诺 · 服务器没给名字"),
    ("legacy.verifiedFeasible", "verified feasible"),
    ("legacy.notFeasible", "not feasible"),
    ("legacy.notPreserved", "not preserved"),
    ("legacy.verifiedEvidenceAttached", "verified evidence attached"),
    ("legacy.evidenceUnavailable", "evidence unavailable"),
]


RESIDUAL = {"legacy.notAvailable": 1}


def dicts(path):
    src = io.open(path, encoding="utf-8").read().split("\n")
    i = next(n for n, ln in enumerate(src) if ln.startswith("const en: Dict"))
    j = next(n for n, ln in enumerate(src) if ln.startswith("const zhCN: Dict"))
    k = next(n for n, ln in enumerate(src) if ln.startswith("const dictionaries"))
    return parse(src[i:j]), parse(src[j:k])


def parse(chunk):
    d = {}
    pending = None
    for line in chunk:
        s = line.strip()
        if s.startswith("//") or s.startswith("*") or s.startswith("/*"):
            continue
        m = KEY.match(line)
        if m:
            d[m.group(1)] = m.group(2)
            pending = None
            continue
        m2 = KEY_CONT.match(line)
        if m2:
            pending = m2.group(1)
            continue
        if pending and s:
            d[pending] = s.strip().rstrip(",").strip('"')
            pending = None
    return d


def residual_ok(key, literal, main_src):
    u"""这枚串在 main.tsx 里还许留几处：本单只搬表里点名的那一处，兄弟位不在单面里。

    实测到「not available」在同文件有两处同文兜底（`next_commitment_buffer_min` 与 opportunity window），
    表里只点名前者，所以后者必须原样留着——把这处也一起换掉就是越界改别人的格。
    """
    allowed = RESIDUAL.get(key, 0)
    return main_src.count(literal) == allowed


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    a = ap.parse_args(argv)
    fe = os.path.join(a.root, "frontend") if os.path.isdir(os.path.join(a.root, "frontend")) else a.root
    dic = os.path.join(fe, "src", "i18n", "LocaleContext.tsx")
    mn = os.path.join(fe, "src", "main.tsx")
    for p in (dic, mn):
        if not os.path.exists(p):
            sys.stdout.write(u"读不到 %s ⇒ 判不可得，不判通过\n" % p)
            return 2
    en, zh = dicts(dic)
    main_src = io.open(mn, encoding="utf-8").read()
    bad = []
    n = 0

    def chk(label, ok, detail=u""):
        chk.total += 1
        if not ok:
            bad.append(label + (u"｜" + detail if detail else u""))
        else:
            chk.ok += 1

    chk.total = 0
    chk.ok = 0

    for key, literal in ((e[0], e[1]) for e in MOVED):
        n += 1
        chk(u"A1 %s 在 en 字典且值逐字等于屏上现字" % key, en.get(key) == literal,
            u"en 实读 %r" % (en.get(key),))
        chk(u"A2 %s 在 zhCN 字典且值逐字等于屏上现字" % key, zh.get(key) == literal,
            u"zhCN 实读 %r" % (zh.get(key),))
        chk(u"A3 %s 两臂逐字相同（本单是搬运不是改写）" % key, en.get(key) == zh.get(key))
        chk(u"A4 main.tsx 里 %s 的字面量已不残留" % key, residual_ok(key, literal, main_src),
            u"实读命中 %d 处" % main_src.count(literal))
        chk(u"A5 main.tsx 里有 t(\"%s\") 调用" % key, ('t("%s")' % key) in main_src)

    # 反控：本单没动的那几处必须还在原处
    chk(u"C1 两枚模块层串仍在（要透传取词函数那一档，未动）",
        main_src.count(u'"CityNexus request failed"') == 1
        and main_src.count(u"`CityNexus request refused (HTTP ${status})`") == 1)
    chk(u"C2 表里没列的兄弟串仍在（opportunity window 那枚 not available、以及 preserved）",
        main_src.count(u'"not available"') == 1 and u'"preserved"' in main_src)
    chk(u"C3 既有键的文本一枚没改：bookings.commitmentUnnamed 两臂仍是原值",
        en.get("bookings.commitmentUnnamed") == "The server gave no name for this commitment"
        and zh.get("bookings.commitmentUnnamed") == u"服务器没有给这项承诺的名字")

    sys.stdout.write(u"树根 %s\n" % a.root)
    sys.stdout.write(u"en 键 %d 枚、zhCN 键 %d 枚（跨行写法已按同一正则的补形读到）\n" % (len(en), len(zh)))
    sys.stdout.write(u"本单搬走的串 %d 枚，逐枚五格；反控三格；合计判 %d 格，绿 %d 格，坏 %d 格\n"
                     % (n, chk.total, chk.ok, len(bad)))
    for b in bad:
        sys.stdout.write(u"  坏：%s\n" % b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
