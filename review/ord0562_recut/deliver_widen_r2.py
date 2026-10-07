# -*- coding: utf-8 -*-
"""Deliver ORD-0562 cell 2 re-cut onto the newest tip (same three sites, new base)."""

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


CAND = "147e0c54ddca501d9e96a983cfc61a1e36dd8616"
TIP = "96e5bef6dd43f61aeefe7deda4c4f5b5dadd0ba9"
BRANCH = "refs/heads/review/cff87c64-ord0562-widen-r2"
assert sh("cat-file", "-t", CAND) == "commit"
assert sh("rev-parse", "%s^" % CAND) == TIP, "candidate parent is not the tip"


def find(sha, path, needle):
    for i, l in enumerate(sh("show", "%s:%s" % (sha, path)).split("\n")):
        if needle in l:
            return i + 1
    raise SystemExit("missing %r in %s@%s" % (needle, path, sha[:8]))


LIVE = "frontend/src/features/execution/LiveRecovery.tsx"
PRE = "frontend/src/lib/pretripChecklist.ts"
SIM = "frontend/src/features/simulation/simulationAdapter.ts"
SPEC = "frontend/e2e/qoder-cff87c64-ord0562-english-count-nouns-r1.spec.ts"

d = {
    "tip": TIP, "cand": CAND, "branch": BRANCH,
    "oldlive": "%s:%d" % (LIVE, find(TIP, LIVE, "suggestion(s)")),
    "oldpre": "%s:%d" % (PRE, find(TIP, PRE, "failure(s)")),
    "oldsim": "%s:%d" % (SIM, find(TIP, SIM, "leg(s)")),
    "newlive": "%s:%d" % (LIVE, find(CAND, LIVE, 'englishCountNoun(duplicateCount, "suggestion")')),
    "newpre": "%s:%d" % (PRE, find(CAND, PRE, 'englishCountNoun(failures.length, "failure")')),
    "newsim": "%s:%d" % (SIM, find(CAND, SIM, 'englishCountNoun(mobility.legs, "leg")')),
    "arm": "%s:%d" % (SPEC, find(CAND, SPEC, "no screen under frontend/src softens a counted English noun")),
}

TPL = """### cff87c64 · 认领领域「断言可信」· 第二件重投（基座换到最新现尖，父提即现尖⇒快进）

候选 {cand}（可 cat-file 解析为 commit），父提 {tip} = 现尖。枝 {branch}。

一、这一件动的产品字节（三枚文件，与上一块同一处改动、换基座）
- 现尖上 hub 之外三处被计数的英文仍在软化：恢复面板 {oldlive}（suggestion(s)）、行前检查 {oldpre}（failure(s)）、模拟面板 {oldsim}（leg(s)）
- 三处都走已在现尖上的 englishCountNoun：{newlive}、{newpre}、{newsim}。中文臂同槽位未动
- 上一块（候选 37d5fdd9a，父提是上一代现尖）因基座落后一代被落地门退；本块以最新现尖为父重切，同一处改动、同一把反控臂

二、反控臂（撤掉改动必须红）
- 新第 6 臂 {arm}：走遍 frontend/src 下每个 .ts/.tsx，逐**处**判有没有 `(s)` 软化，断言清单为空
- 本块基座上的判别性实测：把这三枚文件按**现尖字节**还原 ⇒ 第 6 臂当场红、整趟 rc=1；换回本块字节即绿（六臂全绿）
- 一次读数纠错（我自己的）：第一遍我用 `git checkout --` 还原，它取的是本块提交而不是现尖，所以那次"撤掉仍绿"是量错了还原对象，不是臂不咬；改成按现尖 sha 还原后即红

三、本轮新扫范围 / 新发现处数 / 新修处数与新增回归臂 / 下一轮范围
- 新扫范围：frontend/src 全树（hub 之外三屏）
- 新发现处数：三处（上一行三枚 file:行 锚，逐处可取回）
- 新修处数：三处（同上三枚锚）；新增回归臂：全树那一条，其 file:行 锚已给在本段第二行
- 下一轮要扫的新范围：把同一把全树尺的判据从「模板串里的 (s)」扩到「拼出来的复数」——`${{n}} day` / `${{n}} person` 这类不带 (s) 却仍把复数写死的内联拼字，按同一形制收敛并各带反控臂
"""
BODY = TPL.format(**d)
assert "�" not in BODY, "replacement char in block"
closing = io.open(CLOSING, encoding="utf-8").read().rstrip("\n")
stage = "D:/moodle/_qoder_cff87c64_scratch/block_stage_widen_r2.md"
os.makedirs(os.path.dirname(stage), exist_ok=True)
io.open(stage, "w", encoding="utf-8", newline="\n").write(BODY.rstrip("\n") + "\n\n" + closing + "\n")

p = subprocess.run([sys.executable, SELFCHECK, "--text", stage],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print("selfcheck rc=%d" % p.returncode)
print(((p.stdout or "") + (p.stderr or ""))[-800:])
if p.returncode != 0:
    raise SystemExit("not delivered: selfcheck red")

q = subprocess.run([sys.executable, GATE, "--text", stage, "--expect-clean"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print("Q43 rc=%d" % q.returncode)
print(((q.stdout or "") + (q.stderr or ""))[-800:])
if q.returncode != 0:
    raise SystemExit("not delivered: Q43 red")

t = os.path.join("D:/moodle/_qoder_ledger_inbox", "cff87c64_%s.md" % time.strftime("%H%M"))
shutil.copyfile(stage, t)
print("delivered", t, os.path.getsize(t), "bytes")