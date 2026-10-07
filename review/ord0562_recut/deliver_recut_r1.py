# -*- coding: utf-8 -*-
"""Deliver the ORD-0562 re-cut product change (tonight's hard goal: one product-byte change per domain)."""

import io
import os
import shutil
import subprocess
import sys
import time

REPO = "D:/moodle/CityNexus"
GATE = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r7.py"
CLOSING = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
EVID = r"D:/moodle/_ord0562_recut"


def sh(*a):
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True)
    assert p.returncode == 0, p.stderr.decode()[:200]
    return p.stdout.decode("utf-8", "replace").strip()


CAND = "121fadbee3324f0a9be758bd7ae40ed3855ce413"
TIP = "90f002b74b68eff7401084a166d22e52e84c758c"
BRANCH = "refs/heads/review/cff87c64-ord0562-count-nouns-recut-r1"
assert sh("cat-file", "-t", CAND) == "commit"
assert sh("cat-file", "-t", TIP) == "commit"
assert sh("rev-parse", "%s^" % CAND) == TIP

# anchors: lines read out of the candidate blobs, right now
def blob_lines(sha, path, needles):
    body = sh("show", "%s:%s" % (sha, path)).split("\n")
    out = {}
    for n in needles:
        for i, l in enumerate(body):
            if n in l:
                out[n] = i + 1
                break
        assert n in out, "missing needle %r" % n
    return out

fixed = blob_lines(CAND, "frontend/src/app/V8Experience.tsx",
                   ['import { englishCountNoun }', 'hub.budgetLine', 'hub.todayDaysUnknown',
                    'hub.todayDays", { n: tripDayCount }', 'englishCountNoun(disruptions.length'])
tip_lines = blob_lines(TIP, "frontend/src/app/V8Experience.tsx",
                       ['${tripDayCount} days', '${days} days · ${people} people', 'change(s)'])

def a(sha, path, line):
    return "%s@%s:%s:%d" % (path, sha[:12], path, line) if False else "%s:%d" % (path, line)

P = "frontend/src/app/V8Experience.tsx"
d = {
    "tip": TIP, "cand": CAND, "branch": BRANCH,
    "tipday": "%s:%d" % (P, tip_lines['${tripDayCount} days']),
    "tipbud": "%s:%d" % (P, tip_lines['${days} days · ${people} people']),
    "tipchg": "%s:%d" % (P, tip_lines['change(s)']),
    "fiximp": "%s:%d" % (P, fixed['import { englishCountNoun }']),
    "fixbud": "%s:%d" % (P, fixed['hub.budgetLine']),
    "fixday1": "%s:%d" % (P, fixed['hub.todayDaysUnknown']),
    "fixday2": "%s:%d" % (P, fixed['hub.todayDays", { n: tripDayCount }']),
    "fixchg": "%s:%d" % (P, fixed['englishCountNoun(disruptions.length']),
}

TPL = """### cff87c64 · 认领领域「断言可信」· 今晚硬目标第一件：hub 三处被计数的英文不再自己拼字（产品字节）

候选 {cand}（可 cat-file 解析为 commit），父提 {tip} 就是现尖 ⇒ 可直接快进。枝 {branch}。

一、这一件动的产品字节（一枚文件）
- 现尖上三处仍是内联模板，正是当年屏上印出「1 days」「1 people」「1 change(s)」的那三处：天数行 {tipday}、预算行 {tipbud}、注意行 {tipchg}
- 词典键（hub.todayDays / hub.todayDaysUnknown / hub.budgetLine）与 helper（englishCountNoun）**已在现尖上**，缺的只是这枚组件还在自己拼：现已改成三处各问词典/helper —— 天数行 {fixday1}、{fixday2}，预算行 {fixbud}，注意行 {fixchg}，helper 引入 {fiximp}
- 中文臂同槽位未动（改的是英文臂拼字方式，不是结论）

二、反控臂（撤掉改动必须红）
- 把该组件按现尖字节还原 ⇒ 那格的尺（第 3 臂「hub 不再内联拼被计数的名词」）当场红、整趟 rc=1；改回去即绿。反控不红就等于没改到东西，所以这一条是这一件的判据
- 五臂全绿、两制类型 rc=0 零诊断

三、本轮新扫范围 / 新发现处数 / 新修处数与新增回归臂
- 新扫范围：现尖 {tip} 的 hub 屏英文臂被计数名词的全部内联拼字点（即上面三处）
- 新发现处数：1 枚文件、3 处（词典与 helper 已在尖上，未计入新修）
- 新修处数：3 处；新增回归臂：0 枚新臂（沿用现尖上已有的第 3 臂，它的反控就是这一件的反控）

四、下一轮要扫的新范围（自派，不等点单）
- 往外扩一层：同一问法（"这句被计数的名词是不是还在内联拼"）扫到 hub 之外的屏——恢复面板、模拟面板、行前检查那三处历史上用过的同类写法，看现尖上它们还在不在；在则按同一形制收敛并各带反控臂
"""
BODY = TPL.format(**d)
assert "�" not in BODY, "replacement char in block"
closing = io.open(CLOSING, encoding="utf-8").read().rstrip("\n")
stage = "D:/moodle/_qoder_cff87c64_scratch/block_stage_recut.md"
os.makedirs(os.path.dirname(stage), exist_ok=True)
io.open(stage, "w", encoding="utf-8", newline="\n").write(BODY.rstrip("\n") + "\n\n" + closing + "\n")
p = subprocess.run([sys.executable, GATE, "--text", stage, "--expect-clean"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print("gate rc=%d" % p.returncode)
print(((p.stdout or "") + (p.stderr or ""))[-1300:])
if p.returncode != 0:
    raise SystemExit("not delivered")
t = os.path.join("D:/moodle/_qoder_ledger_inbox", "cff87c64_%s.md" % time.strftime("%H%M"))
shutil.copyfile(stage, t)
print("delivered", t, os.path.getsize(t), "bytes")