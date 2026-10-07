# -*- coding: utf-8 -*-
"""Deliver ORD-0562 cell 4 (widen the arm from the (s) dodge to hardcoded plurals; six sites fixed)."""

import io
import os
import shutil
import subprocess
import sys
import time

REPO = "D:/moodle/CityNexus"
SELFCHECK = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/block_selfcheck_r1.py"
GATE = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r7.py"
CLOSING = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"


def sh(*a):
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True)
    assert p.returncode == 0, p.stderr.decode()[:200]
    return p.stdout.decode("utf-8", "replace").strip()


CAND = "669d69ca8bd7fcb38938a021564239deb0ee3d6e"
PARENT = "38f276b94fca01ecfe6dafd414127b5990ae5087"
BRANCH = "refs/heads/review/cff87c64-ord0562-inline-202c-r1"
TIP = "3f63337ae261fa81e60fcaf35fca6eb550049b2f"
assert sh("cat-file", "-t", CAND) == "commit"
assert sh("rev-parse", "%s^" % CAND) == PARENT


def find(sha, path, needle):
    for i, l in enumerate(sh("show", "%s:%s" % (sha, path)).split("\n")):
        if needle in l:
            return i + 1
    raise SystemExit("missing %r in %s" % (needle, path))


PROG = "frontend/src/features/progress/journeyProgress.ts"
HUB = "frontend/src/app/V8Experience.tsx"
CMP = "frontend/src/features/planning/PlanComparison.tsx"
AIS = "frontend/src/features/planning/PlanWithAiSheet.tsx"
ITIN = "frontend/src/features/trip/TripItinerary.tsx"
SPEC = "frontend/e2e/qoder-cff87c64-ord0562-english-count-nouns-r1.spec.ts"

d = {
    "cand": CAND, "parent": PARENT, "branch": BRANCH, "tip": TIP,
    "olddays": "%s:%d" % (PROG, find(PARENT, PROG, "${p.day_total} days.")),
    "oldstops": "%s:%d" % (PROG, find(PARENT, PROG, "none of the ${p.planned_total} stops is walked yet")),
    "newday": "%s:%d" % (PROG, find(CAND, PROG, 'englishCountNoun(p.day_total, "day")')),
    "newstop": "%s:%d" % (PROG, find(CAND, PROG, 'englishCountNoun(p.planned_total, "stop")')),
    "hubtoday": "%s:%d" % (HUB, find(CAND, HUB, 'englishCountNoun(todayStops.length, "stop")')),
    "cmp": "%s:%d" % (CMP, find(CAND, CMP, 'englishCountNoun(candidates.length, "option")')),
    "ais": "%s:%d" % (AIS, find(CAND, AIS, 'englishCountNoun(planCount, "option")')),
    "itin": "%s:%d" % (ITIN, find(CAND, ITIN, 'englishCountNoun(day.activities.length, "stop")')),
    "arm": "%s:%d" % (SPEC, find(CAND, SPEC, "no screen spells a counted plural out by hand beside the count")),
}

TPL = """### cff87c64 · 认领领域「断言可信」· 第四件：把全树尺的判据从「(s)」扩到「拼出来的复数」，新臂一次抓出六处

候选 {cand}（可 cat-file 解析为 commit），父提 {parent}，现尖读得 {tip} ⇒ 快进。枝 {branch}（这枚远端 ref 同时带着上一格预算提示那一笔，可一起落）。

一、这一件动的产品字节（五枚产品文件 + 一枚尺）
- 扩法：第 6 臂只拦 `(s)` 这一种躲法；这一格加第 8 臂拦更安静的那种——**被计数的复数就写在计数旁边**，于是一天的行程会印成 "1 days." 这一句
- 新臂 {arm} 一上来就抓出六处、第 6 臂看不见的：进度行的 {olddays}（"N days."）与 {oldstops}、hub 的两行 stops、PlanComparison 与 PlanWithAiSheet 的 options、行程日的 stops
- 六处现在都走已在尖上的 englishCountNoun（今天是格 §86 那一处：{newday}、{newstop}、{hubtoday}、{cmp}、{ais}、{itin}）；计数为一的两处另外对齐了动词（is/are、was/were），中文臂同槽位未动

二、反控臂（撤掉改动必须红）
- 新第 8 臂 {arm}：走遍 frontend/src，判"计数表达式后面跟一个手写复数名词"（词典标记不在此列，因为标记本就该带在词典里）
- 判别性实测：把五枚产品文件按**现尖 sha** 还原 ⇒ 第 7 臂与第 8 臂当场红、整趟 rc=1；换回本块字节即绿（八臂全绿、两制类型各 rc=0 零诊断）

三、本轮新扫范围 / 新发现处数 / 新修处数与新增回归臂 / 下一轮范围
- 新扫范围：从「模板串里的 (s)」扩到「拼出来的复数」，全树 frontend/src
- 新发现处数：六处（本段第二行那六枚 文件.tsx:行 锚，逐处可取回）
- 新修处数：六处（同上六枚锚）；新增回归臂：一条，其 文件.ts:行 锚已给在本段第一、二行
- 下一轮要扫的新范围：同一族里还有**中文臂自己把复数写死**的形制（如 `$ {{n}} 天`／`$ {{n}} 站`，英文侧已对但中文侧还按复数拼），把判据扩到中文臂；并在 `backend/app` 侧扫同一形制，看服务端有没有把复数拼进给屏上的字串
"""
BODY = TPL.format(**d)
assert "�" not in BODY, "replacement char in block"
closing = io.open(CLOSING, encoding="utf-8").read().rstrip("\n")
stage = "D:/moodle/_qoder_cff87c64_scratch/block_stage_plural.md"
os.makedirs(os.path.dirname(stage), exist_ok=True)
io.open(stage, "w", encoding="utf-8", newline="\n").write(BODY.rstrip("\n") + "\n\n" + closing + "\n")

p = subprocess.run([sys.executable, SELFCHECK, "--text", stage],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print("selfcheck rc=%d" % p.returncode)
print(((p.stdout or "") + (p.stderr or ""))[-900:])
if p.returncode != 0:
    raise SystemExit("not delivered: selfcheck red")

q = subprocess.run([sys.executable, GATE, "--text", stage, "--expect-clean"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print("Q43 rc=%d" % q.returncode)
print(((q.stdout or "") + (q.stderr or ""))[-900:])
if q.returncode != 0:
    raise SystemExit("not delivered: Q43 red")

t = os.path.join("D:/moodle/_qoder_ledger_inbox", "cff87c64_%s.md" % time.strftime("%H%M"))
shutil.copyfile(stage, t)
print("delivered", t, os.path.getsize(t), "bytes")