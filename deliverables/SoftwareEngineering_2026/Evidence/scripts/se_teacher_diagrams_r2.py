"""双语课堂图 R5：中英四个 .vsdx，注记出画面，主图几何一个坐标不动。

GPT 2026-10-28 复验（Issue #53）留给本轮的两件事，加上操作者当夜的直接指令：

  1. 「Visio 页面左下仍有多行字号较小的技术说明」——非阻断缺点。本版把注记整块
     移到每个文件的第 2 页「附注」（lib 的 sheets 多页能力），课堂页只留图。
     注记内容一字未删，页面上反而更大（13pt），投影不讲、备查可读。
  2. 操作者指令「大胆重做改革，要做中英俩版」——同一几何出中英两套：
     *_EN.vsdx 与中文版共用全部坐标/字号/颜色/连线，只有文字是英文。
     英文串比中文长，个别框放不下 18pt，整版字号下限按课程任务书的 16pt 执行
     （中文版保持 18pt 下限不变），需要更小字号的框在 box() 里显式标注。

不变式（每一条都可被门禁复核，不是自我声明）：
  * 中文两图的节点/连线坐标与 R4.2 通过版（se_teacher_diagrams_r1.py 当前内容）
    完全一致，包括那条回环箭头（t2n7 -> t2n3，arrowSize=3）；
  * Teacher_02 的「继续调整方案」仍在调用地点列——R4.2 用检查器实测过，挪列会让
    回环从右边缘出线、与「是」支共线，比断头更误导；
  * shape data（src）随语言走，页面上一行代码都不出现；
  * Project 一律不动（R4.1 冻结是 GPT 与操作者的共同决定）。

门禁：Builder 自带（labelStrict、溢出、交叉、chrome 压盖、页界），建完另跑
se_visio_cross_check_r1.py（四份都测）与 se_r42_loop_proof_r1.py（中英两份 Teacher_02）。
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
LOG = open(os.path.join(HERE, "se_teacher_diagrams_r2.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()
PW, PH = 13.333, 7.5
BODY = 18.0
TITLE = 26.0
SUB = 12.0
# 课程任务书的字号下限是 16pt。中文版维持 18pt 自我要求；英文版串长，
# 版面下限降到任务书底线，个别仍放不下的框在节点上显式给 size。
BODY_EN_MIN = 16.0
REV = time.strftime("%Y-%m-%d %H:%M")


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


# --------------------------------------------------------------- geometry (frozen)
# Teacher_01：八框两行 S 形；Teacher_02：三排九框 + 菱形判定 + 回环。
# 坐标逐项照抄 se_teacher_diagrams_r1.py——那两版经过了 R4.0..R4.2 的实测与门禁。
CW, CH = 2.67, 1.25
X4 = [0.50, 3.72, 6.94, 10.16]
RA, RB = 1.60, 4.60
AW = 2.25
AX = [0.40, 2.95, 5.50, 8.05, 10.60]
AH = 0.92
DH = 1.10
ROW_TOP, ROW_MID, ROW_C, ROW_D = 1.45, 3.05, 4.75, 6.05


def _t1(state="zh"):
    zh = state == "zh"
    txt = {
        "t1n1": ("旅行者\n提出出行需求", "Traveller\nasks for a trip"),
        "t1n2": ("前端\n地图与对话", "Frontend\nmap & dialogue"),
        "t1n3": ("后端\n统一接口", "Backend\nunified API"),
        "t1n4": ("Agent\n规划与调用工具", "Agent\nplanning & tools"),
        "t1n5": ("地点与路线数据\n外部服务", "Places & routing\nexternal services"),
        "t1n6": ("生成行程方案\n可对比多套", "Builds trip plans\nto compare"),
        "t1n7": ("展示方案\n等待用户确认", "Presents options\nwaits for confirm"),
        "t1n8": ("保存行程与状态\n写入并留审计", "Saves trip & state\nwith audit trail"),
    }
    idx = 0 if zh else 1  # (zh_text, en_text) — booleans are 1/0, not language
    nodes = [
        box("t1n1", X4[0], RA, CW, CH, txt["t1n1"][idx], "user", role="start"),
        box("t1n2", X4[1], RA, CW, CH, txt["t1n2"][idx], "verified"),
        box("t1n3", X4[2], RA, CW, CH, txt["t1n3"][idx], "verified"),
        box("t1n4", X4[3], RA, CW, CH, txt["t1n4"][idx], "agent"),
        box("t1n5", X4[3], RB, CW, CH, txt["t1n5"][idx], "external"),
        box("t1n6", X4[2], RB, CW, CH, txt["t1n6"][idx], "built"),
        box("t1n7", X4[1], RB, CW, CH, txt["t1n7"][idx], "verified"),
        box("t1n8", X4[0], RB, CW, CH, txt["t1n8"][idx], "data", role="end"),
    ]
    edges = [
        edge("t1n1", "t1n2"), edge("t1n2", "t1n3"), edge("t1n3", "t1n4"),
        edge("t1n4", "t1n5"),
        edge("t1n5", "t1n6"), edge("t1n6", "t1n7"),
        edge("t1n7", "t1n8", "用户确认后" if zh else "once confirmed"),
    ]
    src = {
        "t1n1": "frontend/src app 路由与体验壳；journey 状态"
                if zh else "frontend/src app routes & experience shell; journey state",
        "t1n2": "frontend/src 15 个路由面板、MapLibre 地图、Copilot 面板"
                if zh else "frontend/src 15 route panels, MapLibre map, Copilot panel",
        "t1n3": "backend/app/main.py FastAPI /api/v1，175 个端点"
                if zh else "backend/app/main.py FastAPI /api/v1, 175 endpoints",
        "t1n4": "backend/app/agent/gateway.py 与 mission 循环，11 个白名单工具"
                if zh else "backend/app/agent/gateway.py & mission loop, "
                           "11 whitelisted tools",
        "t1n5": "integrations/discovery、Photon/Nominatim/Open-Meteo；默认 mock"
                if zh else "integrations/discovery, Photon/Nominatim/Open-Meteo; "
                           "mock by default",
        "t1n6": "plan 生成与 replan 提案，proposal 表"
                if zh else "plan generation & replan proposals, proposal table",
        "t1n7": "前端方案对比与 Trip Studio；确认前不写库"
                if zh else "frontend option comparison & Trip Studio; nothing "
                           "written before confirmation",
        "t1n8": "SQLite 60 张表：journey、proposal、audit、idempotency"
                if zh else "SQLite 60 tables: journey, proposal, audit, idempotency",
    }
    for n in nodes:
        n["src"] = src[n["id"]]
    return nodes, edges


def _t2(state="zh"):
    zh = state == "zh"
    nodes = [
        box("t2n1", AX[0], ROW_TOP, AW, AH,
            "用户提出需求" if zh else "User asks for\na trip", "user", role="start"),
        box("t2n2", AX[1], ROW_TOP, AW, AH,
            "Agent 理解需求" if zh else "Agent reads\nthe request", "agent"),
        box("t2n3", AX[2], ROW_TOP, AW, AH,
            "调用地点\n与路线工具" if zh else "Calls place &\nrouting tools", "agent"),
        box("t2n4", AX[3], ROW_TOP, AW, AH,
            "生成行程方案" if zh else "Builds trip\noptions", "built"),
        box("t2n5", AX[4], ROW_TOP, AW, AH,
            "地图展示方案" if zh else "Shows plan\non the map", "verified"),
        # 继续调整方案不是计划品：request_replan 是网关注册工具
        # （gateway.py:545），mission 计划会排入（mission_plan.py:118），
        # 守护流程也会确定性地直接派发（guardian.py:418）。
        # R4.2 实测：这个框必须留在调用地点列——挪去 Agent 列会让回环从
        # 右边缘出线、与「是」支共线。中英两版共用这一坐标。
        box("t2n7", AX[2], ROW_MID + (DH - AH) / 2.0, AW, AH,
            "继续调整方案\n（回到第 3 步）" if zh else "Adjusts proposal\n"
            "(back to step 3)", "agent", size=BODY if zh else 16.5),
        box("t2n6", 10.425, ROW_MID, 2.60, DH,
            "需要修改吗？" if zh else "Keep or\nchange?", "agent",
            kind="decision"),
        box("t2n8", AX[4], ROW_C, AW, AH,
            "用户确认方案" if zh else "User confirms\nthe plan", "verified"),
        box("t2n9", AX[4], ROW_D, AW, AH,
            "保存并留下审计" if zh else "Save & keep\naudit trail", "data",
            role="end"),
    ]
    edges = [
        edge("t2n1", "t2n2"), edge("t2n2", "t2n3"), edge("t2n3", "t2n4"),
        edge("t2n4", "t2n5"),
        edge("t2n5", "t2n6", route="straight"),
        edge("t2n6", "t2n8", "否" if zh else "no", route="straight"),
        edge("t2n8", "t2n9", route="straight"),
        edge("t2n6", "t2n7", "是" if zh else "yes", route="straight"),
        # R4.2 补上的真回环：箭头从「继续调整方案」顶边回到第 3 步底边。
        # 中英同坐标，loop proof（se_r42_loop_proof_r1.py）认 t2n3/t2n7 两个 ID，
        # 两份文件都能验。
        edge("t2n7", "t2n3", arrowSize="3"),
    ]
    src = {
        "t2n1": "前端对话入口与向导；journey 会话"
                if zh else "frontend conversation entry & wizard; journey session",
        "t2n2": "backend/app/agent mission 循环，最多 12 步"
                if zh else "backend/app/agent mission loop, at most 12 steps",
        "t2n3": "gateway.py:365 白名单注册（含 request_replan），runtime.py:486 派发；"
                "未知工具在写审计之前 404"
                if zh else "gateway.py:365 whitelist registration (incl. "
                           "request_replan), runtime.py:486 dispatch; unknown "
                           "tools 404 before any audit write",
        "t2n4": "plan 生成；供应商默认 mock，Photon/Nominatim/Open-Meteo 需显式开启"
                if zh else "plan generation; providers mock by default, "
                           "Photon/Nominatim/Open-Meteo need explicit opt-in",
        "t2n5": "MapLibre 地图与方案对比面板"
                if zh else "MapLibre map & plan comparison panel",
        "t2n6": "replan 判定：是否改动行程"
                if zh else "replan decision: does the itinerary need changes",
        "t2n7": "mission_plan.py:118 request_replan → 回到 runtime.py:405 的循环"
                "重新派发工具；main.py:12460 落 PlanVersion(CANDIDATE, "
                "source=REPLAN)，不切活动计划"
                if zh else "mission_plan.py:118 request_replan -> back to the "
                           "runtime.py:405 loop, tools redispatched; "
                           "main.py:12460 lands PlanVersion(CANDIDATE, "
                           "source=REPLAN), active plan unchanged",
        "t2n8": "确认门：main.py:13098 accept_replan 要求 Idempotency-Key；"
                "未确认只留提案"
                if zh else "confirmation gate: main.py:13098 accept_replan "
                           "requires Idempotency-Key; unconfirmed stays a proposal",
        "t2n9": "域服务写入 + audit + receipt；SQLite 60 张表"
                if zh else "domain services write + audit + receipt; "
                           "SQLite 60 tables",
    }
    for n in nodes:
        n["src"] = src[n["id"]]
    return nodes, edges


# --------------------------------------------------------------- notes (moved off page 1)
# 内容与 R4.2 通过版逐字一致（英文为对应译文），只是从课堂页左下搬到第 2 页。
NOTES_T1_ZH = [
    "怎么核对这张图：在 Visio 里选中任意方框，按 Ctrl+1 打开「形状与特殊格式」窗口，"
    "Shape Data 里写着它对应的源码文件、端点数或表数；图面上一个行号都没有。",
    "数据来源：本图按 2026-10-23 当天 CityNexus 开发分支的实际代码整理，"
    "详细取证版（带文件与行号）在 Visio/01_CityNexus_System_Architecture.vsdx。",
]
NOTES_T1_EN = [
    "How to check this drawing: select any box in Visio and press Ctrl+1 to open "
    "the Shape Data pane - it names the source file, endpoint count or table "
    "count behind that box; the drawing itself shows no line numbers.",
    "Data source: compiled from the actual code on the CityNexus development "
    "branch as of 2026-10-23; the forensic version (file & line references) is "
    "Visio/01_CityNexus_System_Architecture.vsdx.",
]
NOTES_T2_ZH = [
    "走到底只有两条出口。",
    "「否」才会写入并留下审计。",
    "「是」只出新提案：那条回环箭头把流程送回「调用地点与路线工具」，"
    "行程表一行都不动。",
    "回环依据真实代码：request_replan 是网关白名单里的工具，提案落成 "
    "CANDIDATE 版本，切换活动计划必须走带 Idempotency-Key 的 accept。",
    "带文件与行号的取证版见 Visio/03_CityNexus_Agent_Workflow.vsdx。",
]
NOTES_T2_EN = [
    "Only two exits exist at the end.",
    "Only 'no' writes anything and leaves an audit trail.",
    "'Yes' only produces a new proposal: the loop arrow sends the flow back to "
    "'Calls place & routing tools'; the itinerary table does not move.",
    "The loop is grounded in real code: request_replan is a whitelisted gateway "
    "tool, proposals land as CANDIDATE, and switching the active plan requires "
    "an accept carrying an Idempotency-Key.",
    "The forensic version with file & line references: "
    "Visio/03_CityNexus_Agent_Workflow.vsdx.",
]
# 附注页版式：整页只放标题块 + 注记块，13pt 起步——注记挪出画面的意义
# 就是让人不凑近也读得清。
APX_ORIGIN = (0.50, 1.70)
APX_WIDTH = 12.30
APX_SIZE = 13.5


def _spec(stem_en, state, page_name, page_title, subtitle, docid, nodes, edges,
          apx_title, apx_subtitle, notes, min_body):
    top_title, top_sub = page_title, subtitle
    return {
        "file": stem_en,
        "pageW": PW, "pageH": PH,
        "font": "Microsoft YaHei",
        "minBodySize": min_body,
        "edgeRule": "none",
        "labelStrict": True,
        "title": top_title, "subtitle": top_sub, "subtitleSize": 14.0,
        "docid": docid, "revline": "generated %s" % REV,
        "bodySize": BODY, "subSize": SUB, "titleSize": TITLE,
        "sheets": [
            {
                "name": page_name,
                "title": page_title, "subtitle": subtitle, "subtitleSize": 14.0,
                "docid": docid, "revline": "generated %s" % REV,
                "nodes": nodes, "edges": edges, "bands": [], "legend": [],
                "edgeRule": "none",
            },
            {
                "name": "附注" if state == "zh" else "Appendix",
                "title": apx_title, "subtitle": apx_subtitle,
                "subtitleSize": 14.0,
                "docid": docid, "revline": "generated %s" % REV,
                "nodes": [], "edges": [], "bands": [], "legend": [],
                "edgeRule": "none",
                "notes": notes, "notesOrigin": APX_ORIGIN,
                "notesWidth": APX_WIDTH, "notesSize": APX_SIZE,
            },
        ],
    }


n01, e01 = _t1("zh")
n01e, e01e = _t1("en")
n02, e02 = _t2("zh")
n02e, e02e = _t2("en")

spec01 = _spec(
    "Teacher_01_System_Overview.vsdx", "zh", "系统总览",
    "CityNexus 城市出行助手   |   系统总览",
    "一句话：用户提需求，Agent 只做规划和提案，真正写入必须经过用户确认。",
    "课堂演示图 · 根据 CityNexus 当前已验证架构整理",
    n01, e01,
    "CityNexus 城市出行助手   |   附注（不投屏）",
    "课堂页左下的小字技术说明移到本页；主图版面一个坐标都没动。",
    NOTES_T1_ZH, BODY)

spec01e = _spec(
    "Teacher_01_System_Overview_EN.vsdx", "en", "System Overview",
    "CityNexus   |   System Overview",
    "The Agent only proposes - the user confirms before anything is written.",
    "Classroom demo · from CityNexus verified architecture",
    n01e, e01e,
    "CityNexus   |   Appendix (not projected)",
    "Notes moved off the classroom page; the main layout is untouched.",
    NOTES_T1_EN, BODY_EN_MIN)

spec02 = _spec(
    "Teacher_02_Agent_User_Flow.vsdx", "zh", "用户流程",
    "CityNexus   |   一次出行请求怎么走完",
    "Agent 只会提方案；要改行程，必须由用户点确认，之后才写入并留审计。",
    "课堂演示图 · 根据 CityNexus 当前已验证架构整理",
    n02, e02,
    "CityNexus   |   附注（不投屏）",
    "回环与分支的代码依据原先印在课堂页左下，现在移到本页备查。",
    NOTES_T2_ZH, BODY)

spec02e = _spec(
    "Teacher_02_Agent_User_Flow_EN.vsdx", "en", "User Flow",
    "CityNexus   |   User Request Flow",
    "The Agent only proposes; the user's confirm writes - with an audit trail.",
    "Classroom demo · from CityNexus verified architecture",
    n02e, e02e,
    "CityNexus   |   Appendix (not projected)",
    "Code evidence for the loop and branches, moved off the classroom page.",
    NOTES_T2_EN, BODY_EN_MIN)

os.makedirs(CLS, exist_ok=True)
os.makedirs(os.path.join(CLS, "previews"), exist_ok=True)


def writable(path):
    """False when another Visio instance owns the file (see r1 for the history)."""
    if not os.path.exists(path):
        return True
    try:
        os.chmod(path, 0o644)
        fd = os.open(path, os.O_WRONLY)
    except OSError:
        return False
    os.close(fd)
    return True


def fix_active_page(path, logf):
    """Re-save the file with page 1 active in the drawing window.

    Setting ActiveWindow.Page inside the builder's own instance did not survive
    SaveAs for a freshly built document (probe: on an OPENED file the same
    assignment does survive save/reopen). So do exactly that proven flow as a
    post-pass: open the saved file, point the drawing window at page 1, save,
    and read the active page back from disk. Without it a teacher double-clicks
    the file and lands on the appendix page.
    """
    import win32com.client as w32c
    app = w32c.DispatchEx("Visio.Application")
    app.Visible = False
    try:
        app.AlertResponse = 7
    except Exception:
        pass
    doc = app.Documents.OpenEx(path, 2)
    try:
        want = doc.Pages.Item(1).Name
        app.ActiveWindow.Page = doc.Pages.Item(1)
        doc.SaveAs(path)
    except Exception as exc:
        logf("active-page fix FAILED on %s: %s %s" % (
            os.path.basename(path), type(exc).__name__, str(exc)[:120]))
    finally:
        doc.Close()
        app.Quit()
    time.sleep(0.8)
    app2 = w32c.DispatchEx("Visio.Application")
    app2.Visible = False
    try:
        app2.AlertResponse = 7
    except Exception:
        pass
    doc2 = app2.Documents.OpenEx(path, 2)
    got = app2.ActiveWindow.Page.Name
    doc2.Close()
    app2.Quit()
    logf("active-page fix %s: reopened on %r (%s)" % (
        os.path.basename(path), got,
        "OK" if got == want else "STILL WRONG, want %r" % want))
    return got == want


results = []
specs = (spec01, spec02, spec01e, spec02e)
only = [a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--only=")]
if only:
    keys = only[0].split(",")
    specs = tuple(s for s in specs if any(k in s["file"] for k in keys))
    log("building only: %s" % ", ".join(s["file"] for s in specs))
for spec in specs:
    stem = spec["file"].replace(".vsdx", "")
    paths = {"vsdx": os.path.join(CLS, spec["file"]),
             "png": os.path.join(CLS, "previews", stem + ".png"),
             "pdf": os.path.join(CLS, "previews", stem + ".pdf"),
             "gate": os.path.join(CLS, "previews", stem + ".gate.json")}
    if not writable(paths["vsdx"]):
        log("%s REFUSED: %s is open in another Visio instance" % (stem, paths["vsdx"]))
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
    apx_ok = fix_active_page(paths["vsdx"], log)
    log("%s: %d failures, %d nodes, %d edges, pages=%s"
        % (stem, len(rep["failures"]), rep.get("nodes", 0), rep.get("edges", 0),
           [p["name"] for p in rep.get("pages", [])]))
    for f in rep["failures"][:20]:
        log("   %s" % f[:200])
    results.append({"file": spec["file"], "failures": rep["failures"],
                    "nodes": rep.get("nodes", 0), "edges": rep.get("edges", 0),
                    "pages": rep.get("pages", []),
                    "activePageFixed": apx_ok,
                    "png": paths["png"], "pdf": paths["pdf"],
                    "pngBytes": os.path.getsize(paths["png"])
                    if os.path.exists(paths["png"]) else 0,
                    "sha256_16": hashlib.sha256(open(paths["vsdx"], "rb").read())
                    .hexdigest()[:16] if os.path.exists(paths["vsdx"]) else ""})
result_path = os.path.join(HERE, "se_teacher_diagrams_r2_result.json")
if only:
    result_path = os.path.join(HERE, "se_teacher_diagrams_r2_result_%s.json"
                               % only[0].replace(",", "-"))
json.dump(results, open(result_path, "w", encoding="utf-8"), indent=1,
          ensure_ascii=False, default=str)
bad = [r for r in results if r.get("failures")]
log("TEACHER DIAGRAMS R2 %s (%d built, %d refused)"
    % ("OK" if not bad else "REFUSED", len(results) - len(bad), len(bad)))
LOG.close()
sys.exit(0 if not bad else 1)
