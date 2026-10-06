# -*- coding: utf-8 -*-
"""Deliver ORD main-exec-path cell 4 (report_disruption crosses the main path). Anchors located at
delivery time; gate with Q43 r7, then land in the inbox."""

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
d["v1"] = anch("catalog_shape_r2.txt", "V1 size 6")
d["v2"] = anch("catalog_shape_r2.txt", "V2 size 12")
d["inv2"] = anch("catalog_shape_r2.txt", "report_disruption in V2: True")
d["clean"] = anch("cell4_note.md", "| clean tip e9b231b8 |")
d["mine"] = anch("cell4_note.md", "| this branch |")
d["gate"] = anch("cell4_note.md", "test_agt10_19_catalog_contains_only_v1_allowlist")
d["arm"] = anch("cell4_note.md", "test_v15_disruption_report_crosses_the_main_path_as_a_tool_call")
d["flaky"] = anch("cell4_note.md", "it is load-flaky")
d["head"] = subprocess.run(["git", "-C", REPO, "ls-remote", "--refs", "origin",
                            "refs/heads/review/cff87c64-main-exec-path-r2"],
                           capture_output=True).stdout.decode().split()[0]
d["tip"] = "e9b231b876c777bc592923bc41d8c397a577e691"

TPL = """### cff87c64 · 主执行路那栋楼·第四格：上报扰动那行现在也过主路了（它原本是网关旁边的一条侧门）

一、这一格把第一到第三格具名上报的那一处收掉
- 前三格验完：适配器 / 运行时 / 守护 / 两条 HTTP 工具入口 / 前端都过网关。唯一没让 agent 写域真值过闸的，就是"上报扰动→Event"这行——两条自然语言入口各自建它，不经 dispatch
- 现在它是 V2 的一枚 typed 工具 report_disruption，两条入口改成 dispatch 它。所以这次写入第一次拿到了 allowlist、agent_tool_requested 审计与策略评估

二、契约面我压到最小（这是我自报，请你复核）
- V1 钉死的六枚工具一个字没动：{{v1}}
- report_disruption 只进 V2（十二枚）：{{v2}}、{{inv2}}
- 策略档位与 request_replan 同级（ALLOW_AUTO，proposal-only，不动钱、不动 C4）：旅人陈述事实、服务端推导事实。这两条入口在成为工具之前本来就是这样被默认 ADVISORY 档放行的（聚焦测试就压着这条：默认档下一个扰动上报仍要落成 Event）
- provider_key / source 由工具内部一张两枚的固定表推出，调用方不能写任意 provenance；两条入口各自存自己那枚键，逐字不变

三、行为不变怎么证的（整跑，两侧同一尖）
- 干净尖：{{clean}} ；本枝：{{mine}} —— 本枝的红是干净尖红的子集，零新增（比干净尖还多两格绿，是我新增的那一臂）；catalog_hydration 是负载抖动，两侧单跑都过，不算我修的（{{flaky}}）
- 第一版我把它放进 V1 的 TOOLS，被闸 {{gate}} 咬住——这正是"V1 不能动"那条纪律在起作用，已改成只进 V2

四、这一臂会咬（反件）
- 新增的 {{arm}}：读 agent_tool_requested 审计行、断它点了 report_disruption。它在改前的产品代码上真跑过一次是红的（那行根本不存在），改后才绿——不是恒真

五、待你裁的一句
- 加一枚 V2 工具=MCP 面与目录各多一枚（虽小但是契约变更）。我压到最小（V1 不动、策略最保守档）并把全套证据摆在这，只等你一个字才落；我没动权威尖
- 枝 refs/heads/review/cff87c64-main-exec-path-r2 @ {head}（自尖 {tip} 切出）
"""
BODY = TPL.format(**d)
assert "�" not in BODY, "block contains a replacement character"
closing = io.open(CLOSING, encoding="utf-8").read().rstrip("\n")
stage = "D:/moodle/_qoder_cff87c64_scratch/block_stage_exec4.md"
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