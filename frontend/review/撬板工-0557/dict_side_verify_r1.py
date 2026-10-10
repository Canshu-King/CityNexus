# -*- coding: utf-8 -*-
u"""逐枚复核 ORD-0557 块给 main.tsx 那 21 枚的「字典侧」判定，并验新键名不撞名。

两眼都要现读，不抄块里的话：
  一、needs_new_key 成不成立：把那枚串在**现尖**那本字典里数命中（`git show <尖>:frontend/src/i18n/LocaleContext.tsx`）。
  二、键名撞不撞：把拟用的键名在 `frontend/src/i18n/` 整目录里数命中（现尖与工作树各数一次）。
退出码：0 = 二十一枚判定与十九枚键名都复核过且结论一致；1 = 有对不上的，逐枚点名。
"""
from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys

REPO = r"D:\moodle\CityNexus"
TIP = "7f08160743b3b46e600c2c05e6863eaabd722f54"
I18N_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src", "i18n")

PAIRS = [
    (u"legacy.persistedOperationUpdate", u"Persisted operation update"),
    (u"legacy.generalRecovery", u"general recovery"),
    (u"legacy.standingMissionHint", u"Activate a standing mission once; subsequent city signals can launch recovery without a new chat message."),
    (u"legacy.noDominantFailureMode", u"No dominant failure mode"),
    (u"legacy.notEvaluated", u"not evaluated"),
    (u"legacy.validatedActivity", u"validated Activity"),
    (u"legacy.noActionableTarget", u"no actionable target"),
    (u"legacy.outcomeEvidence", u"outcome evidence"),
    (u"legacy.explicitWins", u"explicit wins"),
    (u"legacy.notReported", u"not reported"),
    (u"legacy.noUpcomingActivity", u"no upcoming activity"),
    (u"legacy.noActiveC4", u"No active C4"),
    (u"legacy.notAvailable", u"not available"),
    (u"legacy.unnamedCommitment", u"未命名承诺 · 服务器没给名字"),
    (u"legacy.verifiedFeasible", u"verified feasible"),
    (u"legacy.notFeasible", u"not feasible"),
    (u"legacy.notPreserved", u"not preserved"),
    (u"legacy.verifiedEvidenceAttached", u"verified evidence attached"),
    (u"legacy.evidenceUnavailable", u"evidence unavailable"),
    # 表里另两枚：本单没搬（模块层无钩子），但也照样复核「字典无此文本」这句成不成立
    (None, u"CityNexus request failed"),
    (None, u"CityNexus request refused (HTTP ${status})"),
]


def tip_dict():
    p = subprocess.run(["git", "-C", REPO, "show", "%s:frontend/src/i18n/LocaleContext.tsx" % TIP],
                       capture_output=True)
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace")


def dir_hits(direc, needle):
    n = 0
    where = []
    for name in sorted(os.listdir(direc)):
        if not name.endswith((".ts", ".tsx")):
            continue
        path = os.path.join(direc, name)
        for i, ln in enumerate(io.open(path, encoding="utf-8", errors="replace").read().split("\n"), 1):
            if needle in ln:
                n += 1
                where.append("%s:%d" % (name, i))
    return n, where


def dict_values(text):
    u"""把现尖那本字典的**值**逐枚取出来（与共享闸同一枚单行正则），判「字典有没有这段文本」只能整值比。

    为什么不能子串比：这轮我先用子串数，`not available` 被 `Price not available` 顶出一枚假命中——
    尺看不见「整句」与「句子里的一个词」的分别，那种红会把好单判成坏单。
    """
    key_re = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')
    vals = []
    for line in text.split("\n"):
        m = key_re.match(line)
        if m:
            vals.append(m.group(2))
    return vals


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--i18n-dir", default=I18N_DIR)
    a = ap.parse_args(argv)
    text = tip_dict()
    if text is None:
        sys.stdout.write(u"现尖字典对象取不到 ⇒ 不报数\n")
        return 2
    if not os.path.isdir(a.i18n_dir):
        sys.stdout.write(u"读不到 i18n 目录 %s ⇒ 不报数\n" % a.i18n_dir)
        return 2
    values = dict_values(text)
    bad = []
    n_kept = 0
    for key, literal in PAIRS:
        loose = sum(1 for v in values if v == literal)
        if loose:
            bad.append(u"%s：块里判 needs_new_key，可现尖字典整值命中 %d 枚" % (literal[:40], loose))
        if key:
            hits_now, where = dir_hits(a.i18n_dir, '"%s":' % key)
            if hits_now != 2:
                bad.append(u"%s：本枝字典两侧应各一枚，实读 %d 处 %s" % (key, hits_now, where))
            else:
                n_kept += 1
    sys.stdout.write(u"复核面：串 %d 枚（含表里没搬的模块层 2 枚）｜键名两臂齐的 %d 枚（分母 19 枚）\n"
                     % (len(PAIRS), n_kept))
    sys.stdout.write(u"现尖字典整值命中：逐枚均为 0 枚 = %s（字典值总数 %d 枚）\n"
                     % (u"是" if not any(u"整值命中" in b for b in bad) else u"否", len(values)))
    for b in bad:
        sys.stdout.write(u"  坏：%s\n" % b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
