"""把跨进程那把门的三批日志算成一枚收据（数字全部从日志解析，不手抄）。"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

CAND = Path("D:/moodle/_qoder_f_ord253_20260923")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # cp936 会在这里把我自己的收据打崩
GATE = CAND / "backend/tests/test_qoder_agent_command_idempotency_xproc.py"
LOG = Path("D:/moodle/_qoder_f_run/o225_receipts/xproc_three_runs_0923_r2.txt")
OUT = Path("D:/moodle/_qoder_f_run/o225_receipts/ord0253_xproc_receipt_r2.json")
REF = "agent/f-ord253-candidates"


def git(*a: str) -> str:
    return subprocess.run(["git", "-C", str(CAND), *a], capture_output=True,
                          text=True).stdout.strip()


text = LOG.read_text(encoding="utf-8", errors="replace")
runs = []
for blk in re.split(r"=== RUN \d ===", text)[1:]:
    tallies = re.findall(r"\{([^{}]*?(?:GHOST|UNNAMED)[^{}]*)\}", blk)
    counts: dict[str, int] = {}
    if tallies:
        counts = {m.group(1).split("(")[0]: int(m.group(2))
                  for m in re.finditer(r"'([A-Z_0-9]+)[^']*?': (\d+)", tallies[-1])}
    runs.append({"summary": blk.strip().splitlines()[-1].strip(),
                 "shape_counts": counts,
                 "red_cells": re.findall(r"FAILED \S+::(\w+)", blk)})

rounds = 5 * len(runs)
shape_totals: dict[str, int] = {}
for r in runs:
    for k, v in r["shape_counts"].items():
        shape_totals[k] = shape_totals.get(k, 0) + v
red_rounds = sum(sum(r["shape_counts"].values()) for r in runs)

def _cell_green(name: str) -> bool:
    """'这一格在这三批里全绿吗' —— 只从每批的 FAILED 行派生，不写字面量。"""
    return bool(runs) and all(name not in r["red_cells"] for r in runs)


ALL_CELLS = ["test_0_the_two_faces_are_mine_and_offline",
             "test_1_two_processes_one_key_persist_exactly_one_mission",
             "test_2_cross_process_different_intent_fails_closed",
             "test_3_the_loser_reads_the_winners_durable_receipt",
             "test_4_no_key_cross_process_stays_independent"]

receipt = {
    "what": "ORD-0253 跨进程同键：commander 2026-09-23 点头要补的那一格，交**实测**而不是 NOT_MEASURED",
    "lane": "F 8ccd71d8",
    "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    "scope": {"repo": str(CAND), "branch": REF, "candidate_sha": git("rev-parse", REF),
              "tree": git("rev-parse", f"{REF}^{{tree}}"),
              "parents": git("log", "--format=%h", "-3", REF).split(),
              "pushed": False,
              "product_code_changed": "0（这一笔只加测试文件）"},
    "instrument": {"gate": str(GATE), "bytes": GATE.stat().st_size,
                   "git_blob_sha1": git("hash-object", "--no-filters", str(GATE))},
    "run_shape": {"command": f"{sys.executable!r} -m pytest backend/tests/"
                             "test_qoder_agent_command_idempotency_xproc.py -q",
                  "interpreter": subprocess.run(
                      [r"D:/moodle/CityNexus/.venv/Scripts/python.exe", "-V"],
                      capture_output=True, text=True).stdout.strip(),
                  "rounds_per_batch": 5, "batches": len(runs),
                  "faces": "我自己起的两个 uvicorn（各自端口、共享我自己临时 sqlite、跑完 taskkill + 等 netstat 消失 + rmtree）",
                  "source_log": {"path": str(LOG), "bytes": LOG.stat().st_size,
                                 "sha256_12": hashlib.sha256(LOG.read_bytes()).hexdigest()[:12]}},
    "ownership_proof": {
        "asserted_by": "test_0_the_two_faces_are_mine_and_offline",
        "green_batches": sum(1 for r in runs if _cell_green(ALL_CELLS[0])),
        "batches": len(runs),
        "the_four_proofs": ["面自报 uvicorn PID == netstat LISTENING 归属",
                           "该 PID 的父进程 == 我起的句柄（venv 启动器会 re-exec ⇒ 允许一跳）",
                           "A 面回显我的 run id 与它打开的库文件名",
                           "只存在于我临时库里的唯一 journey，能从**对面**读回来"],
        "note": "四证任何一条缺 ⇒ test_0 红并且我不报任何数（这一格不允许变成'看起来通过'）"},
    "per_batch": runs,
    "derived": {"rounds_total": rounds, "rounds_red": red_rounds,
                "rounds_clean": rounds - red_rounds, "shape_totals": shape_totals,
                "green_cells": [c for c in ALL_CELLS if _cell_green(c)],
                "red_cells": [c for c in ALL_CELLS if not _cell_green(c)],
                "named_unique_index_in_the_500": sorted(
                    set(re.findall(r"UNIQUE constraint failed: ([a-z_.]+)", text)))},
    "verdict": (f"CROSS_PROCESS_MEASURED_RED（{red_rounds}/{rounds} 轮红；"
                f"不是 NOT_MEASURED，也不是通过）" if red_rounds else
                "CROSS_PROCESS_GREEN"),
    "two_causes": {
        "UNNAMED_500": "两进程同时给同一 traveler 插 `traveler_agent_policies` 行 ⇒ 败者拿裸 500。"
                       "这**不是**我幂等包装的代码：impl 里那枚 per-traveler policy 写入没有 "
                       "ON CONFLICT / 先读后写，也没走产品现成的 409/503 词汇。",
        "GHOST_MISSION_ROW": "两边都 200、都回赢家的 mission，库里却留下败者那枚 mission。"
                            "这**是我的半件**：我在 impl（它自己会 commit）之后才写收据行，"
                            "唯一索引撞车时回滚已经来不及。"},
    "proposed_fix_needs_a_ruling": (
        "把我那半改成**先占键再执行**（claim → impl → 回填 response），与产品 `_replay_committed_accept`"
        " '等已落库的回执行' 同一条先例；但这会引入'占位行永不回填 ⇒ 409'的新语义，"
        "而这条语义正是 ORD-0262 第二半要裁的东西 ⇒ 我不在裁之前单方面改写入次序。"),
    "print_policy": "只印计数/形态/约束名/摘要；不印 key、不印 env 值",
}
body = json.dumps(receipt, ensure_ascii=False, indent=1)
out = OUT
out.write_text(body, encoding="utf-8", newline="\n")
print(body)
print(f"\nWROTE {out} ({out.stat().st_size} B, sha256[:12]="
      f"{hashlib.sha256(out.read_bytes()).hexdigest()[:12]})")
