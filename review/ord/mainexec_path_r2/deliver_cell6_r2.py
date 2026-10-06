# -*- coding: utf-8 -*-
"""Deliver ORD main-exec-path cell 6 (handler refusal-reachability sweep: no fake gates left)."""

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
d["rq"] = anch("handler_refusal_reachability_r2.txt", "REQUEST_REPLAN|ALLOW_AUTO")
d["rd"] = anch("handler_refusal_reachability_r2.txt", "REPORT_DISRUPTION|ALLOW_AUTO")
d["rqr"] = anch("handler_refusal_reachability_r2.txt", "request_replan               REQUEST_REPLAN")
d["rdr"] = anch("handler_refusal_reachability_r2.txt", "report_disruption            REPORT_DISRUPTION")
d["denom"] = anch("cell6_note.md", "12 of 12 handlers swept")
d["blind1"] = anch("cell6_note.md", "First pass attributed 5 typed handlers")
d["blind2"] = anch("cell6_note.md", "stopped at the")
d["next"] = anch("cell6_note.md", "## Next cell")
d["head"] = subprocess.run(["git", "-C", REPO, "ls-remote", "--refs", "origin",
                            "refs/heads/review/cff87c64-main-exec-path-r2"],
                           capture_output=True).stdout.decode().split()[0]
d["tip"] = "e9b231b876c777bc592923bc41d8c397a577e691"

TPL = """### cff87c64 · 主执行路那栋楼·第六格：把网关十二枚处理器逐枚扫过假闸形制——没有第二处（第五格那处已删）

一、按常设自派：把"这道闸真能失败吗"逐枚套到网关每个处理器上
- 仪器只读：读每枚处理器评估的 AgentAction 与它自带的拒绝分支，并用最紧信封**真跑策略**拿三种模式下的判语（件 review/ord/mainexec_path_r2/handler_refusal_reachability_r2.txt）
- 十二枚逐枚有据。两种"策略永远放行"的动作——REQUEST_REPLAN（{rq}）与 REPORT_DISRUPTION（{rd}）——它们的拒绝都不是策略拒绝，而是可达的参数校验（request_replan 的 404/422 {rqr}、report_disruption 的 422 {rdr}）；两者真正的闸是 allowlist
- 其余 typed 变更类在紧信封下判 DENY，拒绝分支可达。⇒ 假闸形制只剩第五格删掉的那一处，分母是 12/12（{denom}）

二、这一格我自己的仪器有两处盲点，当场修了（不藏）
- 第一趟把五枚 typed 处理器读成 (none)：它们的动作经 `_run_typed_mutation(action=AgentAction.X)` 到策略，不在体里直接 evaluate_action；扫法已补这一形
- 第二趟仍漏，因为取体时被处理器内层的 `def execute()` 截断；已改成只按方法级 `def` 截（{blind1}、{blind2}）
- 这两处若不修，扫法会看着 7/12 就报"全清"——正是本领域要防的那种假绿

三、下一格（按常设再往外扩一层）
- 这一格只读了处理器体里的拒绝。往外一层是**体之外**的拒绝：共享的 `_run_typed_mutation` / `_bound_authorization` 路径与 `_require_journey` / `_typed_*` 帮手。第七格问那条共享层里有没有不可达的拒绝——若有，会一次影响所有 typed 工具（{next}）

四、边界
- 本格零产品字节（只读）；权威尖零移动，只动本车道枝
- 枝 refs/heads/review/cff87c64-main-exec-path-r2 @ {head}（自尖 {tip} 切出）
"""
BODY = TPL.format(**d)
assert "�" not in BODY, "block contains a replacement character"
closing = io.open(CLOSING, encoding="utf-8").read().rstrip("\n")
stage = "D:/moodle/_qoder_cff87c64_scratch/block_stage_exec6.md"
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