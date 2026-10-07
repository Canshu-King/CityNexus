# -*- coding: utf-8 -*-
"""Deliver ORD-0562 cell 5 (mobility refusal agrees with its own leg count)."""

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


CAND = "55290d0163fc8756b513ab7af0ea288e4d4d815e"
TIP = "ea93e6ebe6201ef3b0209da1940e69a5852195c1"
BRANCH = "refs/heads/review/cff87c64-ord0562-zh-plural-r1"
assert sh("cat-file", "-t", CAND) == "commit"
assert sh("rev-parse", "%s^" % CAND) == TIP, "candidate parent is not the tip"


def find(sha, path, needle):
    for i, l in enumerate(sh("show", "%s:%s" % (sha, path)).split("\n")):
        if needle in l:
            return i + 1
    raise SystemExit("missing %r in %s" % (needle, path))


SIM = "frontend/src/features/simulation/simulationAdapter.ts"
SPEC = "frontend/e2e/qoder-cff87c64-ord0562-english-count-nouns-r1.spec.ts"

d = {
    "cand": CAND, "tip": TIP, "branch": BRANCH,
    "oldlegs": "%s:%d" % (SIM, find(TIP, SIM, 'const legsEn = mobility.legs > 0')),
    "oldsent": "%s:%d" % (SIM, find(TIP, SIM, "The server says these${legsEn} have facts")),
    "newclause": "%s:%d" % (SIM, find(CAND, SIM, 'const legsClause =')),
    "newsent": "%s:%d" % (SIM, find(CAND, SIM, "The server says ${legsClause} facts")),
    "arm": "%s:%d" % (SPEC, find(CAND, SPEC, "the mobility refusal agrees with its own leg count")),
}

TPL = """### cff87c64 · 认领领域「断言可信」· 第五件：模拟面板那条拒绝语跟自己的腿数对不上了（产品字节）

候选 {cand}（可 cat-file 解析为 commit），父提 {tip} = 现尖 ⇒ 快进。枝 {branch}。

一、这一件动的产品字节（一枚产品文件 + 一枚尺）
- 现尖上这条句子是 `these` + 一个不带数字的名词 + `have`（{oldlegs}、{oldsent}）——所以任何腿数都印成 "these leg have facts"，零腿时更是"这些 有事实"，既没数也对不上
- 改后按数分三支、各自对齐：一支腿 "this 1 leg has"、多支腿 "these N legs have"、零支腿 "the route evidence has"（{newclause}、{newsent}）；中文臂同槽位未动

二、反控臂（撤掉改动必须红）
- 新臂 {arm} 是**行为臂**，不是读源码：它按这条分支能认的形制造出服务器错误（message=MOBILITY_DATA_UNAVAILABLE、details.gaps 一/二/零条），调 describeFailure 读它拼出的那句，逐一断言 1 腿/2 腿/0 腿各自对得上
- 判别性实测：把产品文件按**现尖 sha** 还原 ⇒ 第 7 臂当场红、整趟 rc=1（错误信息逐字是 "one leg must read 'this 1 leg has'"，收到的却是 "these leg have facts"）；换回本块字节即绿（七臂全绿、两制类型各 rc=0 零诊断）

三、本轮新扫范围 / 新发现处数 / 新修处数与新增回归臂 / 下一轮范围
- 新扫范围：先按自派扫了**中文臂把复数写死**的形制 —— 结论是**没有这种缺陷**（中文不随数变位，`$ {{n}} 天` 对任何 n 都对），所以不造改动；再把覆盖面转到**服务端**拼英文复数的地方
- 新发现处数：后端只命中一处 `backend/app/main.py:714`，但那是常量 `MAX_JOURNEY_DAYS = 7`（`backend/app/core/temporal.py:24`），恒为复数、不是缺陷 —— 具名否定；真缺陷在前端这一处
- 新修处数：一处（上一段那两枚 文件.ts:行 锚）；新增回归臂：一条行为臂，其锚已给在本段第二行
- 下一轮要扫的新范围：把"数-词一致"这一判据扩到**动词与量词**（`is/are`、`has/have`、`was/were` 与 `each/every` 这类跟数走的词），在全树 frontend/src 找"计数是 1 时动词还对不上"的句子；并在后端扫同一形制（f-string 里数+词一致）
"""
BODY = TPL.format(**d)
assert "�" not in BODY, "replacement char in block"
closing = io.open(CLOSING, encoding="utf-8").read().rstrip("\n")
stage = "D:/moodle/_qoder_cff87c64_scratch/block_stage_mobility.md"
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