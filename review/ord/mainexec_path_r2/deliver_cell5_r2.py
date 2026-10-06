# -*- coding: utf-8 -*-
"""Deliver ORD main-exec-path cell 5 (found and removed a fake gate in my own cell-4 tool)."""

import io
import os
import shutil
import subprocess
import sys
import time

REPO = "D:/moodle/CityNexus"
WT = "D:/moodle/_qoder_exec_r1"
GATE = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r7.py"
CLOSING = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
E = "review/ord/mainexec_path_r2/"


def anch(n, sub):
    ls = io.open(os.path.join(WT, E, n), encoding="utf-8").read().split("\n")
    for i, l in enumerate(ls):
        if sub in l:
            return E + n + ":" + str(i + 1)
    raise SystemExit("missing " + sub)


d = {}
d["adv"] = anch("policy_modes_r2.txt", "ADVISORY -> ALLOW_AUTO")
d["ass"] = anch("policy_modes_r2.txt", "ASSISTED -> ALLOW_AUTO")
d["aut"] = anch("policy_modes_r2.txt", "AUTONOMOUS -> ALLOW_AUTO")
d["arm"] = anch("cell5_note.md", "test_agt10_19b_report_disruption_is_v2_only_and_the_allowlist_is_its_real_gate")
d["red"] = anch("cell5_note.md", "removing the `ToolDescriptor`")
d["clean"] = anch("cell5_note.md", "| clean tip e9b231b8 |")
d["c4"] = anch("cell5_note.md", "| cell 4 |")
d["c5"] = anch("cell5_note.md", "| this cell |")
d["next"] = anch("cell5_note.md", "## Next cell")
d["head"] = subprocess.run(["git", "-C", REPO, "ls-remote", "--refs", "origin",
                            "refs/heads/review/cff87c64-main-exec-path-r2"],
                           capture_output=True).stdout.decode().split()[0]
d["tip"] = "e9b231b876c777bc592923bc41d8c397a577e691"

TPL = """### cff87c64 · 主执行路那栋楼·第五格：我自己上一格那枚工具装了个假闸——我自己扫出来、自己修了

一、按新常设（领域所有权）自扫：我上一格那枚工具的策略闸能不能真的响
- 第四格我给 report_disruption 写了一条 DENY 分支（策略拒绝就 403）。我量了一下它能不能触发：它被放在 request_replan 那一支旁边，而那一支在任何模式判定之前就直接放行
- 现读（最紧的信封：不开自动接受、零花费额度、零损失额度、零漂移、无可活动类型）：ADVISORY→ALLOW_AUTO（{adv}）、ASSISTED→ALLOW_AUTO（{ass}）、AUTONOMOUS→ALLOW_AUTO（{aut}）
- 所以那条 DENY 分支在三种模式里一次都不可达——它是个**假闸**：宣称有一道策略拒绝，而它不可能发生。这正是我这块领域（断言可信）要抓的东西

二、改法与它的臂
- 删掉那条死分支：不能响的检查比没有更坏（它暗示一道不存在的闸）。真正闸这枚工具的是 allowlist（不在目录里的名字被拒）与每次 dispatch 都写的 agent_tool_requested 审计；回执里仍如实报 decision
- 新臂 {arm}：压住"它在 V2、不在 V1 钉死六枚、不在目录的名字被拒"三件事。判别性我验了：把 ToolDescriptor 从 TYPED_TOOLS 拿掉，这臂当场红（{red}），随后按字节复位

三、行为不变（整跑，两侧同一尖）
- 干净尖 {clean} ；第四格 {c4} ；本格 {c5} —— 红集与干净尖逐枚相同，零新增；比第四格多一格绿（新增那臂）

四、下一格（按常设自派，往外扩一层）
- 同一问法（"这道闸真能失败吗"）逐枚套到网关其余每枚工具处理器上：扫每个 dispatch 处理器，问它的拒绝分支可不可达，逐枚出可达性回执（{next}）。只有不可达拒绝的处理器，就是本格在我自己代码里找到的同一种假闸形制

五、边界
- 产品字节：gateway.py 删一支 + 一枚测试；无新增契约变更（除第四格那枚工具）。权威尖零移动，只动本车道枝
- 枝 refs/heads/review/cff87c64-main-exec-path-r2 @ {head}（自尖 {tip} 切出）
"""
BODY = TPL.format(**d)
assert "�" not in BODY, "block contains a replacement character"
closing = io.open(CLOSING, encoding="utf-8").read().rstrip("\n")
stage = "D:/moodle/_qoder_cff87c64_scratch/block_stage_exec5.md"
io.open(stage, "w", encoding="utf-8", newline="\n").write(BODY.rstrip("\n") + "\n\n" + closing + "\n")

proc = subprocess.run([sys.executable, GATE, "--text", stage, "--expect-clean"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print("gate rc=%d" % proc.returncode)
print(((proc.stdout or "") + (proc.stderr or ""))[-1400:])
if proc.returncode != 0:
    raise SystemExit("not delivered")
target = os.path.join("D:/moodle/_qoder_ledger_inbox", "cff87c64_%s.md" % time.strftime("%H%M"))
shutil.copyfile(stage, target)
print("delivered", target, os.path.getsize(target), "bytes")