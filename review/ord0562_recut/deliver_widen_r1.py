# -*- coding: utf-8 -*-
"""Deliver ORD-0562 cell 2 (widened coverage beyond the hub): three softened counted nouns on three other
screens now go through englishCountNoun, with a new tree-wide arm as the counter-arm."""

import io
import os
import shutil
import subprocess
import sys
import time

REPO = "D:/moodle/CityNexus"
GATE = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r7.py"
SELFCHECK = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/block_selfcheck_r1.py"
CLOSING = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"


def sh(*a):
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True)
    assert p.returncode == 0, p.stderr.decode()[:200]
    return p.stdout.decode("utf-8", "replace").strip()


CAND = "37d5fdd9ac8a23c8ff588790b77d290abf1df53d"
TIP = "0c64ad4a1153d543ef197d79435a2d6a7146466e"
BRANCH = "refs/heads/review/cff87c64-ord0562-widen-r1"
assert sh("cat-file", "-t", CAND) == "commit"
assert sh("rev-parse", "%s^" % CAND) == TIP, "candidate parent is not the tip"


def anchors(sha, path, needles):
    body = sh("show", "%s:%s" % (sha, path)).split("\n")
    out = {}
    for n in needles:
        for i, l in enumerate(body):
            if n in l:
                out[n] = i + 1
                break
        assert n in out, "missing needle %r in %s" % (n, path)
    return out


LIVE = "frontend/src/features/execution/LiveRecovery.tsx"
PRE = "frontend/src/lib/pretripChecklist.ts"
SIM = "frontend/src/features/simulation/simulationAdapter.ts"
SPEC = "frontend/e2e/qoder-cff87c64-ord0562-english-count-nouns-r1.spec.ts"

old = {LIVE: sh("show", "%s:%s" % (TIP, LIVE)).split("\n"),
       PRE: sh("show", "%s:%s" % (TIP, PRE)).split("\n"),
       SIM: sh("show", "%s:%s" % (TIP, SIM)).split("\n")}
new_live = anchors(CAND, LIVE, ['englishCountNoun(duplicateCount, "suggestion")'])
new_pre = anchors(CAND, PRE, ['englishCountNoun(failures.length, "failure")'])
new_sim = anchors(CAND, SIM, ['englishCountNoun(mobility.legs, "leg")'])
new_spec = anchors(CAND, SPEC, ["no screen under frontend/src softens a counted English noun"])

def line_of(sha_path_lines, needle):
    for i, l in enumerate(sha_path_lines):
        if needle in l:
            return i + 1
    raise SystemExit("missing old needle %r" % needle)

d = {
    "tip": TIP, "cand": CAND, "branch": BRANCH,
    "oldlive": "%s:%d" % (LIVE, line_of(old[LIVE], "suggestion(s)")),
    "oldpre": "%s:%d" % (PRE, line_of(old[PRE], "failure(s)")),
    "oldsim": "%s:%d" % (SIM, line_of(old[SIM], "leg(s)")),
    "newlive": "%s:%d" % (LIVE, new_live['englishCountNoun(duplicateCount, "suggestion")']),
    "newpre": "%s:%d" % (PRE, new_pre['englishCountNoun(failures.length, "failure")']),
    "newsim": "%s:%d" % (SIM, new_sim['englishCountNoun(mobility.legs, "leg")']),
    "arm": "%s:%d" % (SPEC, new_spec["no screen under frontend/src softens a counted English noun"]),
}

TPL = """### cff87c64 · 认领领域「断言可信」· 今晚硬目标第二件：hub 之外三处被计数的英文也不再自己拼字（产品字节）

候选 {cand}（可 cat-file 解析为 commit），父提 {tip} = 现尖 ⇒ 快进。枝 {branch}。

一、这一件动的产品字节（三枚文件）
- 上一件只覆盖了 hub。这一件把覆盖面往外扩一层：现尖上 hub 之外还有三处被计数的名词在软化 —— 恢复面板 {oldlive}（suggestion(s)）、行前检查 {oldpre}（failure(s)）、模拟面板 {oldsim}（leg(s)）
- 三处现在都走已在现尖上的 englishCountNoun：{newlive}、{newpre}、{newsim}。中文臂同槽位未动
- 其中两处是我上一块用 grep 漏掉的 —— 它们写在模板串里、我那次的 grep 只抓到了一处。是扩了尺才把它们抓出来，不是又扫了一遍源码

二、新增的反控臂（撤掉改动必须红）
- 新第 6 臂 {arm}：走遍 frontend/src 下每个 .ts/.tsx，逐**处**（不是逐行——逐行会把箭头参数 `s` 误判成屏上字串，我上一版就踩过）判有没有 `(s)` 软化，断言清单为空
- 判别性实测：把这三枚文件按现尖字节还原 ⇒ 第 6 臂当场红、整趟 rc=1；改回去即绿。撤掉不红就等于没改到东西

三、本轮新扫范围 / 新发现处数 / 新修处数与新增回归臂 / 下一轮范围
- 新扫范围：frontend/src 全树（上一件只扫 hub 一枚文件）
- 新发现处数：三处（上一行那三枚 file:行 锚，即逐处可取回）
- 新修处数：三处（同上三枚锚）；新增回归臂：全树那一条，其 file:行 锚已给在本段第二行
- 下一轮要扫的新范围：把同一把全树尺的判据从「模板串里的 (s)」扩到「拼出来的复数」——即 `${{n}} day` / `${{n}} person` 这类不带 (s) 却仍把复数写死的内联拼字，按同一形制收敛并各带反控臂

四、闸
- 六臂全绿；两制类型各 rc=0、零诊断
"""
BODY = TPL.format(**d)
assert "�" not in BODY, "replacement char in block"
closing = io.open(CLOSING, encoding="utf-8").read().rstrip("\n")
stage = "D:/moodle/_qoder_cff87c64_scratch/block_stage_widen.md"
os.makedirs(os.path.dirname(stage), exist_ok=True)
io.open(stage, "w", encoding="utf-8", newline="\n").write(BODY.rstrip("\n") + "\n\n" + closing + "\n")

for name, script in (("selfcheck", SELFCHECK), ("Q43", GATE)):
    if os.path.exists(script):
        args = [sys.executable, script, "--text", stage]
        if name == "Q43":
            args.append("--expect-clean")
        p = subprocess.run(args,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        print("%s rc=%d" % (name, p.returncode))
        print(((p.stdout or "") + (p.stderr or ""))[-900:])
        if p.returncode != 0:
            raise SystemExit("not delivered: %s red" % name)

t = os.path.join("D:/moodle/_qoder_ledger_inbox", "cff87c64_%s.md" % time.strftime("%H%M"))
shutil.copyfile(stage, t)
print("delivered", t, os.path.getsize(t), "bytes")