"""两张真正给老师看的中文 Visio 图（原生 .vsdx，16:9 横向一页一张）。

用户实机打开详细工程图后的结论是对的：那些图是取证用的，方框里写着
`main.py:14169`、`gateway.py:359`，五条泳道互相穿线，讲台上根本念不出来。
这两张不一样：

  Teacher_01_System_Overview  8 个框两行 S 形，一条主线走完，框内只有两行中文；
  Teacher_02_Agent_User_Flow  9 个框三排，一个菱形判定，是/否两条出口和一条回环。

两张图每一条连线都只连同一列或相邻列的两个框，行间留 1.5 英寸以上的空廊，
连线没有可斜穿的对手，所以 Visio 自动布线不会交叉；`labelStrict` 让「是/否」
这类连线文字必须落在空白处，落不下就整张图拒绝出片——上一版那个压在
「需要修改吗？」上的「否」字，就是这条没设才印上去的。

框架版本、接口数、工具数、文件与行号一律放进形状数据（Shape Data），
选中框才能看到，投影上不占一个字符。图上只留一句
"根据 CityNexus 当前已验证架构整理"。

字体是微软雅黑，正文 18pt、标题 26pt，都高于任务书要求的 16/22pt；
文字换行与溢出检查用的是引擎里新加的按字宽算法（中文字符按 1.02 em 计），
不是原来那套只适合拉丁字母的 0.58 em 估算——否则中文会"测量通过、实际溢出"。
"""
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from se_visio_lib_r1 import Builder, GateError                     # noqa: E402

CLS = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Classroom"
LOG = open(os.path.join(HERE, "se_teacher_diagrams_r1.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()
PW, PH = 13.333, 7.5
BODY = 18.0
TITLE = 26.0
SUB = 12.0


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def box(nid, x, y, w, h, text, state, size=BODY, kind="rect", role="node", src=None):
    """A shape. `src` goes into Shape Data only: hideSrc keeps it off the page."""
    n = {"id": nid, "x": x, "y": y, "w": w, "h": h, "text": text, "state": state,
         "size": size, "kind": kind, "role": role, "hideSrc": True}
    if src:
        n["src"] = src
    return n


def edge(a, b, label=None, state="verified", route="orthogonal", **extra):
    e = {"from": a, "to": b, "state": state, "route": route, "labelSize": 14.0,
         "arrowSize": "2"}
    e.update(extra)
    if label:
        e["label"] = label
    return e


# --------------------------------------------------------------- Teacher_01
# 八框两行，走 S 形：第一行从左到右，末端垂直落到第二行，第二行从右到左。
# 七条连线全部落在同一列或相邻列的两个框之间，没有一条需要斜穿画面，
# 所以 Visio 的自动布线无从交叉。行与行之间留 1.75 英寸空廊，
# 唯一带字的连线（用户确认后）就放在那条廊里。
CW, CH = 2.67, 1.25
X4 = [0.50, 3.72, 6.94, 10.16]
RA, RB = 1.60, 4.60
n01 = [
    box("t1n1", X4[0], RA, CW, CH, "旅行者\n提出出行需求", "user", role="start"),
    box("t1n2", X4[1], RA, CW, CH, "前端\n地图与对话", "verified"),
    box("t1n3", X4[2], RA, CW, CH, "后端\n统一接口", "verified"),
    box("t1n4", X4[3], RA, CW, CH, "Agent\n规划与调用工具", "agent"),
    box("t1n5", X4[3], RB, CW, CH, "地点与路线数据\n外部服务", "external"),
    box("t1n6", X4[2], RB, CW, CH, "生成行程方案\n可对比多套", "built"),
    box("t1n7", X4[1], RB, CW, CH, "展示方案\n等待用户确认", "verified"),
    box("t1n8", X4[0], RB, CW, CH, "保存行程与状态\n写入并留审计", "data",
        role="end"),
]
e01 = [
    edge("t1n1", "t1n2"), edge("t1n2", "t1n3"), edge("t1n3", "t1n4"),
    edge("t1n4", "t1n5"),
    edge("t1n5", "t1n6"), edge("t1n6", "t1n7"),
    edge("t1n7", "t1n8", "用户确认后"),
]
SRC01 = {
    "t1n1": "frontend/src/app 路由与体验壳；journey 状态",
    "t1n2": "frontend/src 15 个路由面板、MapLibre 地图、Copilot 面板",
    "t1n3": "backend/app/main.py FastAPI /api/v1，175 个端点",
    "t1n4": "backend/app/agent/gateway.py 与 mission 循环，11 个白名单工具",
    "t1n5": "integrations/discovery、Photon/Nominatim/Open-Meteo；默认 mock",
    "t1n6": "plan 生成与 replan 提案，proposal 表",
    "t1n7": "前端方案对比与 Trip Studio；确认前不写库",
    "t1n8": "SQLite 60 张表：journey、proposal、audit、idempotency",
}
for n in n01:
    n["src"] = SRC01[n["id"]]

spec01 = {
    "file": "Teacher_01_System_Overview.vsdx",
    "pageName": "系统总览",
    "pageW": PW, "pageH": PH,
    "font": "Microsoft YaHei",
    "minBodySize": BODY,
    "edgeRule": "none",
    "labelStrict": True,
    "title": "CityNexus 城市出行助手   |   系统总览",
    "subtitle": "一句话：用户提需求，Agent 只做规划和提案，真正写入必须经过用户确认。",
    "subtitleSize": 14.0,
    "docid": "课堂演示图 · 根据 CityNexus 当前已验证架构整理",
    "revline": "generated %s" % time.strftime("%Y-%m-%d %H:%M"),
    "bodySize": BODY, "subSize": SUB, "titleSize": TITLE,
    "nodes": n01, "edges": e01, "bands": [], "legend": [],
    "notes": ["怎么核对这张图：在 Visio 里选中任意方框，按 Ctrl+1 打开「形状与特殊格式」窗口，"
              "Shape Data 里写着它对应的源码文件、端点数或表数；图面上一个行号都没有。",
              "数据来源：本图按 2026-10-23 当天 CityNexus 开发分支的实际代码整理，"
              "详细取证版（带文件与行号）在 Visio/01_CityNexus_System_Architecture.vsdx。"],
    "notesOrigin": (X4[0], 6.35), "notesWidth": 11.9, "notesSize": 12.0,
}

# --------------------------------------------------------------- Teacher_02
# 上排五框是主干；判定框落在第五列正下方，「否」沿第五列垂直落到下排、再垂直
# 落到最下排；「是」沿中排一条水平线往左进调整框，回环写进框里那句话，
# 不再画一条会判定框抢出口边的长线。
# 两条支路各占一条空廊：水平的「是」在判定框左侧、垂直的「否」在判定框正下方，
# 中间隔着整整一列空格。上一版把「是」「否」都从判定框引出且先画「是」，
# Visio 让「是」占了底顶点、「否」占了左顶点，两条线在 (10.47, 3.39) 打了个叉
# ——这个坐标是 `se_visio_cross_check_r1.py` 读回连线端点算出来的，不是猜的。
# R4.2: the loop back to step 3 is now a real connector, not a promise inside the
# box. It is a short vertical in the 调用地点 column, and that column is the only
# one that keeps the arrow honest: with 继续调整方案 in the Agent column instead,
# `se_visio_cross_check_r1.py` read the ends back as (5.20,3.90)->(6.62,5.13) -
# Visio left through the RIGHT edge, so the return leg ran on exactly the same
# y as the 是 branch and read as that branch passing through the box and carrying
# on. Levelled in the same column, the connector has one candidate exit (top) and
# one candidate entry (bottom), so the arrow can only point back up into step 3.
AW = 2.25
AX = [0.40, 2.95, 5.50, 8.05, 10.60]
AH = 0.92
DH = 1.10
ROW_TOP, ROW_MID, ROW_C, ROW_D = 1.45, 3.05, 4.75, 6.05
# 继续调整方案 sits (DH-AH)/2 lower than the row line on purpose: its centre has
# to be exactly level with the diamond's centre. Measured on the built file, a
# 0.09in miss makes Visio route the 是 branch over the TOP of both boxes
# (begin 11.725,4.45 -> end 6.625,4.45, i.e. the two top edges), which reads as
# one straight line continuing from 地图展示方案 into 继续调整方案 instead of a
# branch leaving the decision. Levelled, the same connector lands on
# begin 10.425,3.90 -> end 7.75,3.90: the diamond's left vertex into the box's
# right edge, and the 是 label parks on that segment. `RoutingStyle` and
# connection-point glue are both unwritable on this install (see
# Classroom/TEACHER_READABILITY_VERIFICATION.md), so geometry is the only lever.
# R4.2: 继续调整方案 moved off the 调用地点 column onto the Agent column, so the
# loop back to step 3 is a two-segment elbow through empty space instead of a
# 0.77in stub that reads as nothing but inter-row padding. Elbow geometry is
# forced by the boxes: t2n7 (2.95..5.20, 3.14..4.06) and t2n3 (5.50..7.75,
# 1.45..2.37) overlap in neither axis, so an orthogonal connector has to turn
# inside the 0.68in corridor under the top row, where no shape lives.
n02 = [
    box("t2n1", AX[0], ROW_TOP, AW, AH, "用户提出需求", "user", role="start"),
    box("t2n2", AX[1], ROW_TOP, AW, AH, "Agent 理解需求", "agent"),
    box("t2n3", AX[2], ROW_TOP, AW, AH, "调用地点\n与路线工具", "agent"),
    box("t2n4", AX[3], ROW_TOP, AW, AH, "生成行程方案", "built"),
    box("t2n5", AX[4], ROW_TOP, AW, AH, "地图展示方案", "verified"),
    # 继续调整方案 is not a plan: request_replan is a registered gateway tool
    # (gateway.py:545), it is scheduled inside the mission plan
    # (mission_plan.py:118) and the guardian calls it deterministically
    # (guardian.py:418). Drawing it in the grey dashed "not built yet" style would
    # understate the code just as much as the missing arrow overstated it.
    box("t2n7", AX[2], ROW_MID + (DH - AH) / 2.0, AW, AH,
        "继续调整方案\n（回到第 3 步）", "agent"),
    box("t2n6", 10.425, ROW_MID, 2.60, DH, "需要修改吗？", "agent",
        kind="decision"),
    box("t2n8", AX[4], ROW_C, AW, AH, "用户确认方案", "verified"),
    box("t2n9", AX[4], ROW_D, AW, AH, "保存并留下审计", "data", role="end"),
]
e02 = [
    edge("t2n1", "t2n2"), edge("t2n2", "t2n3"), edge("t2n3", "t2n4"),
    edge("t2n4", "t2n5"),
    edge("t2n5", "t2n6", route="straight"),
    edge("t2n6", "t2n8", "否", route="straight"),
    edge("t2n8", "t2n9", route="straight"),
    edge("t2n6", "t2n7", "是", route="straight"),
    # the return leg the teacher could only read as a promise before: a real,
    # arrow-headed connector from 继续调整方案 back into 调用地点与路线工具. No
    # label - the 0.77in gutter between the two boxes is the whole line, and a
    # white-backed caption there would cover the arrow it is meant to explain.
    edge("t2n7", "t2n3", arrowSize="3"),
]
SRC02 = {
    "t2n1": "前端对话入口与向导；journey 会话",
    "t2n2": "backend/app/agent mission 循环，最多 12 步",
    "t2n3": "gateway.py:365 白名单注册（含 request_replan），runtime.py:486 派发；"
            "未知工具在写审计之前 404",
    "t2n4": "plan 生成；供应商默认 mock，Photon/Nominatim/Open-Meteo 需显式开启",
    "t2n5": "MapLibre 地图与方案对比面板",
    "t2n6": "replan 判定：是否改动行程",
    "t2n7": "mission_plan.py:118 request_replan → 回到 runtime.py:405 的循环重新派发"
            "工具；main.py:12460 落 PlanVersion(CANDIDATE, source=REPLAN)，不切活动计划",
    "t2n8": "确认门：main.py:13098 accept_replan 要求 Idempotency-Key；未确认只留提案",
    "t2n9": "域服务写入 + audit + receipt；SQLite 60 张表",
}
for n in n02:
    n["src"] = SRC02[n["id"]]

spec02 = {
    "file": "Teacher_02_Agent_User_Flow.vsdx",
    "pageName": "用户流程",
    "pageW": PW, "pageH": PH,
    "font": "Microsoft YaHei",
    "minBodySize": BODY,
    "edgeRule": "none",
    "labelStrict": True,
    "title": "CityNexus   |   一次出行请求怎么走完",
    "subtitle": "Agent 只会提方案；要改行程，必须由用户点确认，之后才写入并留审计。",
    "subtitleSize": 14.0,
    "docid": "课堂演示图 · 根据 CityNexus 当前已验证架构整理",
    "revline": "generated %s" % time.strftime("%Y-%m-%d %H:%M"),
    "bodySize": BODY, "subSize": SUB, "titleSize": TITLE,
    "nodes": n02, "edges": e02, "bands": [], "legend": [],
    "notes": ["走到底只有两条出口。",
              "「否」才会写入并留下审计。",
              "「是」只出新提案：那条回环箭头把流程送回「调用地点与路线工具」，"
              "行程表一行都不动。",
              "回环依据真实代码：request_replan 是网关白名单里的工具，提案落成 "
              "CANDIDATE 版本，切换活动计划必须走带 Idempotency-Key 的 accept。",
              "带文件与行号的取证版见 Visio/03_CityNexus_Agent_Workflow.vsdx。"],
    "notesOrigin": (AX[0], 4.85), "notesWidth": 7.0, "notesSize": 12.5,
}

os.makedirs(CLS, exist_ok=True)
os.makedirs(os.path.join(CLS, "previews"), exist_ok=True)


def writable(path):
    """False when another Visio instance owns the file.

    A probe of mine crashed with an uncaught COM error and left an invisible
    `/Automation` instance holding this .vsdx open read-only; the builder then
    died on `SaveAs` with "DOS 无效句柄", which reads like a Visio bug and is
    really a lock. Say which, before spending 25s of Visio time.
    """
    if not os.path.exists(path):
        return True
    try:
        os.chmod(path, 0o644)
        fd = os.open(path, os.O_WRONLY)
    except OSError:
        return False
    os.close(fd)
    return True


results = []
specs = (spec01, spec02)
only = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--only=")]
if only:
    specs = tuple(s for s in specs if any(k in s["file"] for k in only[0].split(",")))
    log("building only: %s" % ", ".join(s["file"] for s in specs))
for spec in specs:
    stem = spec["file"].replace(".vsdx", "")
    paths = {"vsdx": os.path.join(CLS, spec["file"]),
             "png": os.path.join(CLS, "previews", stem + ".png"),
             "pdf": os.path.join(CLS, "previews", stem + ".pdf"),
             "gate": os.path.join(CLS, "previews", stem + ".gate.json")}
    if not writable(paths["vsdx"]):
        log("%s REFUSED: %s is open in another Visio instance - close it or kill "
            "the automation one, then re-run" % (stem, paths["vsdx"]))
        results.append({"file": spec["file"], "failures": ["target locked"],
                        "nodes": 0, "edges": 0})
        continue
    try:
        rep = Builder(spec, paths, log).build()
    except GateError as exc:
        log("%s GATE REFUSED: %s" % (stem, str(exc)[:400]))
        results.append({"file": spec["file"], "failures": [str(exc)], "nodes": 0,
                        "edges": 0})
        continue
    log("%s: %d failures, %d nodes, %d edges" % (stem, len(rep["failures"]),
                                                 rep.get("nodes", 0),
                                                 rep.get("edges", 0)))
    for f in rep["failures"][:20]:
        log("   %s" % f[:200])
    results.append({"file": spec["file"], "failures": rep["failures"],
                    "nodes": rep.get("nodes", 0), "edges": rep.get("edges", 0),
                    "png": paths["png"], "pdf": paths["pdf"],
                    "pngBytes": os.path.getsize(paths["png"])
                    if os.path.exists(paths["png"]) else 0,
                    "sha256_16": hashlib.sha256(open(paths["vsdx"], "rb").read())
                    .hexdigest()[:16] if os.path.exists(paths["vsdx"]) else ""})
result_path = os.path.join(HERE, "se_teacher_diagrams_result.json")
if only:
    result_path = os.path.join(HERE, "se_teacher_diagrams_result_%s.json"
                               % only[0].replace(",", "-"))
json.dump(results, open(result_path, "w", encoding="utf-8"), indent=1,
          ensure_ascii=False, default=str)
bad = [r for r in results if r.get("failures")]
log("TEACHER DIAGRAMS %s (%d built, %d refused)"
    % ("OK" if not bad else "REFUSED", len(results) - len(bad), len(bad)))
LOG.close()
sys.exit(0 if not bad else 1)
