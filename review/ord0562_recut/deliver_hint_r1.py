# -*- coding: utf-8 -*-
"""Deliver ORD-0562 cell 3 (the budget hint's two inline bilingual branches -> dictionary)."""

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


CAND = "cf3d2d31ba745178c6f5bfd424af25a3c7e75ffa"
TIP = "588680a602123b39b4b16699f4ced2fa2d2ae79a"
BRANCH = "refs/heads/review/cff87c64-ord0562-inline-202c-r1"
assert sh("cat-file", "-t", CAND) == "commit"
assert sh("rev-parse", "%s^" % CAND) == TIP, "candidate parent is not the tip"


def find(sha, path, needle):
    for i, l in enumerate(sh("show", "%s:%s" % (sha, path)).split("\n")):
        if needle in l:
            return i + 1
    raise SystemExit("missing %r in %s@%s" % (needle, path, sha[:8]))


HUB = "frontend/src/app/V8Experience.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
SPEC = "frontend/e2e/qoder-cff87c64-ord0562-english-count-nouns-r1.spec.ts"

d = {
    "tip": TIP, "cand": CAND, "branch": BRANCH,
    "oldplain": "%s:%d" % (HUB, find(TIP, HUB, '这是按你的预算平均下来的参考值，不是最终花费')),
    "oldcur": "%s:%d" % (HUB, find(TIP, HUB, '（以 ${currency} 计）')),
    "newplain": "%s:%d" % (HUB, find(CAND, HUB, 't("hub.budgetHint")')),
    "newcur": "%s:%d" % (HUB, find(CAND, HUB, 't("hub.budgetHintCurrency", { currency })')),
    "keyen": "%s:%d" % (DICT, find(CAND, DICT, '"hub.budgetHint": "This is your own budget')),
    "arm": "%s:%d" % (SPEC, find(CAND, SPEC, "the budget hint reads the dictionary on BOTH of its branches")),
}

TPL = """### cff87c64 · 认领领域「断言可信」· 第三件：预算提示那两句"两臂各写一遍"改成走词典（同一串在一枚文件里出现两次，按行号改）

候选 {cand}（可 cat-file 解析为 commit），父提 {tip} = 现尖 ⇒ 快进。枝 {branch}。

一、这一件动的产品字节（两枚产品文件 + 一枚尺）
- 现尖上预算提示在 hub 里各写了两臂两遍：{oldplain}（无货币）与 {oldcur}（带货币）。两句**是同一串中文**，只差一个尾注
- 现在两句各问词典：{newplain}、{newcur}；词典加四枚键（zh/en × 无货币/带货币），例如 {keyen}
- 按交接总账的规矩：同串出现两次就不能只判"内联还在吗"（那一分支一旦动了就成空判据），所以这一格的判据是**两处都动 + 两串字面都不许留**

二、反控臂（撤掉改动必须红）
- 新第 7 臂 {arm}：断言两处分支都问词典、两串内联字面都不留、两枚键在英文侧与中文侧都在
- 判别性实测：把两枚产品文件按**现尖 sha** 还原 ⇒ 第 7 臂当场红、整趟 rc=1；换回本块字节即绿（七臂全绿、两制类型各 rc=0 零诊断）

三、本轮新扫范围 / 新发现处数 / 新修处数与新增回归臂 / 下一轮范围
- 新扫范围：hub 里两臂内联双语的"预算提示"这一族（同串两处的形制）
- 新发现处数：两处（上一段两枚 file:行 锚，逐处可取回）
- 新修处数：两处（同上两枚锚）；新增回归臂：一条，其 file:行 锚已给在本段第二行
- 下一轮要扫的新范围：同一族（两臂各写一遍的内联双语）在 hub 里还有约二十七处（现读 `zh ?` 三元共二十九枚），挑下一处同形制收敛；优先挑"同一串在一枚文件出现两次"的，因为那是空判据的高发处
"""
BODY = TPL.format(**d)
assert "�" not in BODY, "replacement char in block"
closing = io.open(CLOSING, encoding="utf-8").read().rstrip("\n")
stage = "D:/moodle/_qoder_cff87c64_scratch/block_stage_hint.md"
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