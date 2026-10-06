# -*- coding: utf-8 -*-
"""Deliver ORD main-exec-path cell 3 (frontend sweep). Anchors located at delivery time; gate, then land."""

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
E = "review/ord/mainexec_path_r1/"


def anch(n, sub):
    ls = io.open(os.path.join(WT, E, n), encoding="utf-8").read().split("\n")
    for i, l in enumerate(ls):
        if sub in l:
            return E + n + ":" + str(i + 1)
    raise SystemExit("missing " + sub)


d = {}
d["tool"] = anch("cell3_sweep_r1.txt", "/agent/tools/{tool}")
d["cmd"] = anch("cell3_sweep_r1.txt", "/agent/commands")
d["dock"] = anch("cell3_sweep_r1.txt", "accept_replan: { en")
d["policy"] = anch("cell3_sweep_r1.txt", "auto_accept_replan: true")
d["head"] = subprocess.run(["git", "-C", REPO, "ls-remote", "--refs", "origin",
                            "refs/heads/review/cff87c64-main-exec-path-r1"],
                           capture_output=True).stdout.decode().split()[0]
d["tip"] = "2e2ddbaf72eed9565fd8b18ea9b8216061269f57"

TPL = """### cff87c64 · 主执行路那栋楼·第三格（收口）：前端也跑在主路上——这栋楼的判据在我权限内走完了

一、前端这一面（整棵树的最后一面；图纸说的是"全树"）
- 前端调 agent 工具走 {{tool}}，与 MCP 适配器同一个 HTTP 面，没有绕开网关
- /agent/commands 与 /copilot/messages 两条自然语言入口，正是第一格收敛的那两条（{{cmd}}）
- CopilotDock 里的 accept_replan / create_booking 等名字只是工具清单的显示文案（{{dock}}），不是调用
- auto_accept_replan 看着像绕过，其实是 PUT /travelers/{{id}}/agent-policy 设用户自主档（{{policy}}）；网关在 dispatch 时仍按它裁，不是第二条执行路

二、所以这栋楼的判据走完了（在我权限内）
- 图纸判据：全树扫执行入口、逐条判该不该收敛、收敛完跑一遍证明行为不变
  · 扫完：适配器 / 运行时 / 守护 / 两条 HTTP 工具入口 / 前端 callAgentTool，每个消费者都过网关（第二、三格件）
  · 收敛：一处真重复——上报扰动落成 Event，两条入口原本各造各的，现同调一个函数（第一格）
  · 跑一遍证行为不变：后端整套两侧同一批红（9 处同 id、零新增，第一格件）
- 剩下唯一没让 agent 主动写域真值过闸的那一处（上报扰动那行），要过闸得往钉死的十一枚工具目录加一枚 report_disruption = 改契约，已在前两格具名上报、等你裁，我不擅自做

三、纪律
- 本格零产品字节；零写库、零移动权威线、强推零次、未碰他人进程与他人文件
- 枝 refs/heads/review/cff87c64-main-exec-path-r1 @ {head}（自尖 {tip} 切出；三格收在一根枝上）
"""
BODY = TPL.format(**d)
assert "�" not in BODY, "block contains a replacement character"
closing = io.open(CLOSING, encoding="utf-8").read().rstrip("\n")
stage = "D:/moodle/_qoder_cff87c64_scratch/block_stage_exec3.md"
io.open(stage, "w", encoding="utf-8", newline="\n").write(BODY.rstrip("\n") + "\n\n" + closing + "\n")

proc = subprocess.run([sys.executable, GATE, "--text", stage, "--expect-clean"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print("gate rc=%d" % proc.returncode)
print(((proc.stdout or "") + (proc.stderr or ""))[-1200:])
if proc.returncode != 0:
    raise SystemExit("not delivered")
target = os.path.join("D:/moodle/_qoder_ledger_inbox", "cff87c64_%s.md" % time.strftime("%H%M"))
shutil.copyfile(stage, target)
print("delivered", target, os.path.getsize(target), "bytes")