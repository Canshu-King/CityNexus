# -*- coding: utf-8 -*-
"""Re-deliver the cell-2 block clean: the first one shipped a mojibake glyph ("两??" HTTP) from the
heredoc; this file builds the same block with no corrupted glyphs, guards against U+FFFD, gates, and lands.
"""

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


adapter = anch("cell2_sweep_r1.txt", "/api/v1/agent/tools/{tool_name}")
runtime = anch("cell2_sweep_r1.txt", "runtime.py:471")
guardian = anch("cell2_sweep_r1.txt", "guardian.py:406")
catalog = anch("cell2_sweep_r1.txt", "tool_catalog.py:63")
newtool = anch("cell2_sweep_r1.txt", "report_disruption present today: False")
head = subprocess.run(["git", "-C", REPO, "ls-remote", "--refs", "origin",
                       "refs/heads/review/cff87c64-main-exec-path-r1"],
                      capture_output=True).stdout.decode().split()[0]
tip = "2e2ddbaf72eed9565fd8b18ea9b8216061269f57"

lines = [
    "### cff87c64 · 主执行路那栋楼·第二格（勘误重发）：这条主路确实只有一处说法——逐个消费者验完",
    "",
    "（上一条同名块里有一个坏字，是我生成时的乱码；这一条是干净的替代，请以这条为准。）",
    "",
    "一、这一格不动产品字节，只把「唯一说法」变成有据的判断",
    "- MCP 适配器：call() 直接 POST 到 " + adapter + "，走契约的第一跳，没有绕开",
    "- agent 运行时：经 " + runtime + " 派发",
    "- 守护：建一个网关后 dispatch inspect_twin/request_replan/accept_replan（" + guardian + " 等），自治动作走主路",
    "- 两条 HTTP 工具入口喂 AgentToolGateway.dispatch（上一格件里）",
    "",
    "二、所以「主执行路是唯一的工具执行说法」这句现在有回执支撑",
    "- 适配器、运行时、守护、HTTP 入口，每个消费者都被点名，都过网关；网关的 allowlist 与钉死的目录 " + catalog + " 是唯一那道闸",
    "",
    "三、还剩一处 agent 主动写域真值没过闸（已具名，等你裁）",
    "- 上一格收敛后的那行「上报扰动到 Event」仍由两条自然语言入口直接落，不经 dispatch。要让它也过策略边界，得在钉死的目录里加一枚工具——report_disruption 今天不在目录里（" + newtool + "），而 V2 是钉死的十一枚工具面，加它=改契约，我不擅自做",
    "",
    "四、纪律",
    "- 本格零产品字节（树差异仍只有上一格的 main.py + 两个证据目录）；零写库、零移动权威线、强推零次",
    "- 枝 refs/heads/review/cff87c64-main-exec-path-r1 @ " + head + "（自尖 " + tip + " 切出）",
]
BODY = "\n".join(lines)
assert "�" not in BODY, "block still contains a replacement character"

closing = io.open(CLOSING, encoding="utf-8").read().rstrip("\n")
stage = "D:/moodle/_qoder_cff87c64_scratch/block_stage_exec2b.md"
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