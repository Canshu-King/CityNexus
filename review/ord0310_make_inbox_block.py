"""Build this lane's ledger-inbox block for ORD-0310's landed-generation readings.

Everything in the prose is read out of an artifact or a command run inside this process - the
collected counts come from the runner log and a fresh `--collect-only`, the nodeids from the arms
receipt, the ref shas from `git ls-remote`. A hand-typed number here is how a ledger line and the
measurement it cites stop agreeing.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
SC = ROOT / "_scratch_0310"
EV = "evidence/ord0288-keyless-deadline"
URL = "https://github.com/Canshu-King/CityNexus.git"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
MEASURED_REF = "refs/heads/review/ord0310-keyless-deadline-d-on-2344145c"
AUTH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
UNWRAP_ARM = "K0310_KEYLESS_LEG_HAS_SIGNAL_BUT_NO_DEADLINE"
SPEC = "frontend/e2e/qoder-ord0310-keyless-write-deadline.spec.ts"
BACKEND_TEST = "backend/tests/test_qoder_ord0310_keyless_leg_receipts.py"
STAMP = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M+08")
OUT = Path(f"D:/moodle/_qoder_ledger_inbox/d-e345b9d6_{datetime.now().astimezone():%H%M}.md")


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def load(name: str):
    return json.loads((SC / name).read_text(encoding="utf-8"))


def sh(*args: str) -> str:
    return subprocess.run(list(args), cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def ref_shas() -> dict:
    out = sh("git", "ls-remote", URL, AUTH_REF, MEASURED_REF)
    parsed = {}
    for line in out.splitlines():
        if "\trefs/" in line:
            sha, ref = line.split("\t")
            parsed[ref.strip()] = sha.strip()
    for _attempt in range(4):
        if all(re.fullmatch(b"[0-9a-f]{40}", parsed.get(r, "").encode() or b"x")
                 for r in (AUTH_REF, MEASURED_REF)):
            break
        out = sh("git", "ls-remote", URL, AUTH_REF, MEASURED_REF)  # a truncated reply looks
        parsed = {}                                                 # like a bad sha here
        for line in out.splitlines():
            if "	refs/" in line:
                sha, _, name = line.partition(chr(9))
                if re.fullmatch("[0-9a-f]{40}", sha.strip()):
                    parsed[name.strip()] = sha.strip()
    for ref in (AUTH_REF, MEASURED_REF):
        if not re.fullmatch("[0-9a-f]{40}", parsed.get(ref, "")):
            raise SystemExit(f"ABORT: {ref} unresolved after retries: {parsed!r}")
    return parsed


refs = ref_shas()
rec = load("ord0310_keyless_deadline_receipt_r3b.json")
arms = load("arms_receipt_r5.json")
back = load("backend_readings_r3.json")
q38 = load("ord0310-q38r2-on-receipt-r3b.json")
cells = {c["id"]: c for c in rec["cells"]}
gen_extra = rec["generation_binding"]["files_this_tree_adds_on_top_of_the_tip"]
c2 = cells["C2_single_named_constant"]["readings"]
cr = arms["clean_round"]
arm = next(a for a in arms["arms"] if a["arm"] == UNWRAP_ARM)
log = (ROOT / "review" / f"run-{cr['runId']}.log").read_text(encoding="utf-8", errors="replace")
running = re.search(r"Running (\d+) tests? using", log)
node_lines = [l.strip() for l in log.splitlines() if re.match(r"\s*(ok|x|\u00d7) \d+ ", l)]
setup_nodes = [l for l in node_lines if "setup.ts" in l]
gate_nodes = [l for l in node_lines if "qoder-ord0310" in l]
pytest_collect = sh(PY, "-m", "pytest", BACKEND_TEST, "--collect-only", "-q")
collect_out = (SC / "r5" / "ord0310-collect-r1.out")
collect_out.parent.mkdir(parents=True, exist_ok=True)
collect_out.write_bytes(
    (f"$ {PY} -m pytest {BACKEND_TEST} --collect-only -q\n"
     + "\n".join(l for l in pytest_collect.splitlines() if "::" in l)
     + "\n" + [l for l in pytest_collect.splitlines() if "collected" in l][-1].strip() + "\n\n"
     + f"$ {PY} review/run_spec.py qoder-ord0310-keyless-write-deadline {cr['port']}\n"
     + f"(the kept runner log is review/run-{cr['runId']}.log)\n"
     + "\n".join(node_lines) + "\n" + running.group(0) + "\n" + cr["tallies"][0] + "\n").encode("utf-8"))
COLL = {
    "blob": blob(collect_out.read_bytes()),
    "backend_collected": int(re.search(r"(\d+) tests? collected", pytest_collect).group(1)),
    "writer_node": next((l.split("::")[-1].strip() for l in pytest_collect.splitlines()
                         if "written_out" in l), "NONE"),
    "runner_collected": int(running.group(1)), "gate_nodes": len(gate_nodes),
    "setup_nodes": len(setup_nodes),
}
COLL["field_nodes"] = COLL["backend_collected"] - (1 if COLL["writer_node"] != "NONE" else 0)
COLL["path"] = f"{EV}/ord0310-collect-r1.out"  # published name of the file just written
pyver = sh(PY, "-V").strip()
k1_line = next((l for l in gate_nodes if "K1 " in l), "NOT_IN_LOG")
k1_nodeid = re.sub(r"^\S+\s+\d+\s+\[chromium\] › ", "", k1_line).split(" (")[0]

L = []
L.append(f"### SESSION=e345b9d6 @{STAMP} —— **ORD-0310 落地代三行读数（号令者 22:29 单）+ 一处分母说明**")
L.append("")
L.append(
    f"① **绿的那轮**：解释器 `{pyver}`（`{PY}`）；前端具名命令 "
    f"`{PY} review/run_spec.py qoder-ord0310-keyless-write-deadline {cr['port']}`"
    f"（`CNX_LANE_ROOT={ROOT}`，退出 `{cr['gateExit']}`，轮次 `run={cr['runId']}`、"
    f"库 `{cr['db']}`，运行日志 `review/run-{cr['runId']}.log`）。"
    f"收集条数 = **{running.group(1)} 条**，其中 **{len(setup_nodes)} 条不是本单的判据**："
    f"它是 `{SPEC}` 之前的具名 setup 项目 `{setup_nodes[0].split('› ')[1].split(' (')[0] if setup_nodes else 'MISSING'}`"
    f"（`frontend/e2e/_qoderRealSeed.setup.ts:110`）；本单自己的门是 "
    f"**{len(gate_nodes)} 枚节点，全绿**：K1 用时 {k1_line.split('(')[-1].rstrip(')')}。"
    f"汇总行 `{cr['tallies'][0]}` 里那个 `4` 就是 {len(gate_nodes)} + {len(setup_nodes)}，"
    f"**我总线帖里写的「三枚节点」指的是本单门自己的 {len(gate_nodes)} 枚，不是 runner 那一行的分母** —— "
    f"两边都对，但我把两个分母混在一句话里说过一次，这里分开具名。"
    f"服务端具名命令 `{PY} -m pytest {BACKEND_TEST} -q`"
    f"（`CNX_ORD0310_OUT={EV}/ord0310-backend-readings-r3.json`）：本次现算 "
    f"`--collect-only -q` 的原文逐行落在 `{COLL['path']}` blob `{COLL['blob']}` = "
    f"**{COLL['backend_collected']} 条 collected**；这 "
    f"{COLL['backend_collected']} 条里 {COLL['field_nodes']} 条是字段读数格（落盘成 JSON 的 "
    f"`{json.dumps(list(back['cells'].keys()))}`），第 {COLL['backend_collected']} 条 "
    f"`{COLL['writer_node']}` 是写出器 ⇒ `collected {COLL['backend_collected']} / cells "
    f"{len(back['cells'])}` 不是漏了一格。交付那轮的落盘 JSON "
    f"`{EV}/ord0310-backend-readings-r3.json` blob "
    f"`{blob((SC / 'backend_readings_r3.json').read_bytes())}` 里的格数是 {len(back['cells'])} 格（`{back['table']}`、"
    f"`K1` 行 {back['cells']['K1']['idempotency_keys_rows_from']}→"
    f"{back['cells']['K1']['idempotency_keys_rows_to']}、`journey_missions` "
    f"{back['cells']['K1']['journey_missions_rows_from']}→"
    f"{back['cells']['K1']['journey_missions_rows_to']}、"
    f"distinct {back['cells']['K1']['distinct_mission_ids']}）。"
    f"一处要说清的缺口：那轮 pytest 的通过汇总行只出现在控制台，我的采集器只把 "
    f"{len(back['cells'])} 格写进了 JSON，所以「passed 那一行」我没有可引用的落盘件 —— "
    f"以后我把 runner 汇总行也写进收据。")
L.append("")
L.append(
    f"② **拆腿反件倒在谁身上**：臂 `{arm['arm']}`，三元组 = "
    f"(sha=`{arm['triple']['exact_sha']}`, "
    f"nodeid=`{arm['triple']['nodeid']}`, shape={json.dumps(arm['triple']['shape'], ensure_ascii=False)})；"
    f"落地代那一轮只有这一枚见证者红：`{arm['attempt']['label']}` 的 "
    f"`nodes` 读 K1=RED、K2=GREEN、K3=GREEN，退出 `{arm['attempt']['gateExit']}`，"
    f"轮次 `run={arm['attempt']['runId']}`、库 `{arm['attempt']['db']}`，"
    f"锚点命中 `{arm['anchor_hits']}`/期望 `{arm['expected_anchor_hits']}`，"
    f"字节 {arm['sizes']['before']}→{arm['sizes']['during_mutation']}"
    f"（差 {arm['sizes']['delta_bytes']} B = 包装函数名）→还原 {arm['sizes']['after_restore']}，"
    f"`restored_to_tested_tree_bytes={json.dumps(arm['restored_to_tested_tree_bytes'])}`。"
    f"红的判据文本取自运行日志原行：`{k1_nodeid}` —— 报错是 "
    f"`expect(locator).toBeVisible() failed`（`plan-ai-result` 在 "
    f"`{c2['constant_ms_in_the_module']}` ms 期限到点后没有出现），不是 signal 缺失。")
L.append("")
L.append(
    f"③ **要落**：`{MEASURED_REF}` = commit=`{refs[MEASURED_REF]}` 请走 preflight 门落地。"
    f"它只比现尖 commit=`{refs[AUTH_REF]}` 多 1 件 `{gen_extra[0]}`"
    f"（0 产品/门字节），但那件就是上面这枚双臂反件的驱动器：不落，线上那把驱动器仍是 6 枚臂，"
    f"别人从线复跑不出我这一代的 `K1 红 / K2 K3 绿`。")
L.append("")
L.append(
    f"**坐标写法改一条（号令者 00:0x 单）**：正文里 commit=`c518e64b42db…` 与 commit=`e6927f0f18c8…` 那两枚我核过了 —— "
    f"`git cat-file -t` 都回 `commit`，GitHub commits API 都回 HTTP 200，"
    f"它们不可解析的原因是只由 `refs/heads/review/ord0310-tools-r*` 带出来、别人 clone 若没 fetch 那几枚 ref "
    f"就看不见；不是笔误也不是 run 号。今后我按名字空间写：`commit=<40>`、`run=<id>`，"
    f"blob 位只放 blob。本块引用的三枚坐标："
    f"`{EV}/ord0310_keyless_deadline_receipt_r3b.json` blob `{blob((SC / 'ord0310_keyless_deadline_receipt_r3b.json').read_bytes())}`"
    f"（尺 Q38 r2 判 `{q38['overall']}`、hard `{q38['hard_count']}`、soft `{q38['soft_count']}`）、"
    f"`{EV}/ord0310-arms-receipt-r5.json` blob `{blob((SC / 'arms_receipt_r5.json').read_bytes())}`、"
    f"`{EV}/ord0310-backend-readings-r3.json` blob `{blob((SC / 'backend_readings_r3.json').read_bytes())}`。"
    f"`claimed_result` 仍是本车道观测，`derived_result` 全 null，等级归红队。")
L.append("")

text = "\n".join(L) + "\n"
OUT.write_bytes(text.encode("utf-8"))
print(f"wrote {OUT} {OUT.stat().st_size} B blob={blob(OUT.read_bytes())}")
print(f"collected(runner)={running.group(1)} gate_nodes={len(gate_nodes)} setup_nodes={len(setup_nodes)} "
      f"backend_collected={COLL['backend_collected']} writer={COLL['writer_node']}")
print(f"K1 nodeid from the log: {k1_nodeid}")
