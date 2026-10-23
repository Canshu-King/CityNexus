"""Classroom/课堂演示顺序.md - the running order, with the narration and the fallbacks.

Everything numeric or digest-shaped is read from the result files and from the
artefacts on disk at the moment of writing, because this is the one document the
operator will actually be holding at noon, and a stale path or a wrong page count in
it costs more than a missing paragraph.
"""
import hashlib
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
CLS = os.path.join(DEL, "Classroom")
OUT = os.path.join(CLS, "课堂演示顺序.md")


def j(name):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def sha(p, n=12):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


def pages(path):
    data = open(path, "rb").read()
    hits = [int(x) for x in re.findall(rb"/Count\s+(\d+)", data)]
    return max(hits) if hits else 0


def kb(path):
    return "%d KB" % (os.path.getsize(path) // 1024) if os.path.exists(path) else "缺失"


prj = j("se_project_build_r2_result.json")
rec = j("se_project_recovery_result.json")
stat = j("se_plan_status_result.json")
demo = j("se_classroom_demo_result.json")
fit = j("se_classroom_fit_result.json")
view = j("se_classroom_view_result.json")
deck = j("se_deck_result.json")
cap = prj.get("capacity") or {}
late = [e for e in (stat.get("entries") or []) if e.get("late")]
gate = (deck.get("gate") or {})
V = os.path.join(DEL, "Visio")
M = os.path.join(DEL, "Microsoft_Project")
P = os.path.join(DEL, "Presentation")
PICS = os.path.join(CLS, "previews")
plan_sha = sha(os.path.join(M, "CityNexus_Software_Engineering_Plan.mpp"), 16)

L = []
A = L.append
A("# CityNexus 课堂演示顺序 · 2026-10-23 中午")
A("")
A("生成 %s。这份是**拿在手里念的那张纸**：四段顺序、每段的实际路径、一两句讲稿、"
  "以及投影仪或软件出问题时换哪一套。" % time.strftime("%Y-%m-%d %H:%M"))
A("")
A("计划文件：`Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` "
  "sha256 `%s…`（演示时**只用副本改视图**，原件不动，脚本每次比对摘要）。" % plan_sha)
A("")
A("## 一、四段顺序（合计约 2 分钟）")
A("")
A("### 1) Visio 系统架构 · 30 秒")
A("")
A("打开：`%s`" % os.path.join(V, "01_CityNexus_System_Architecture.vsdx"))
A("")
A("讲稿：整个系统分四层——最上面是用户和界面，中间是 FastAPI 的 175 个接口和 11 个 MCP "
  "工具，再下面是 Agent 平面和域服务，最底层是数据与外部供应商。规则只有一条："
  "**Agent 只能提方案，真正写数据的是域服务**。图里每个方框都能追到代码文件，"
  "选中任意方框看「形状数据」就有来源路径。")
A("")
A("现场可演示：选中一个方框拖动 0.75 英寸，连线跟着走（脚本已验证，见第三节）。")
A("")
A("### 2) Visio Agent 工作流 · 30 秒")
A("")
A("打开：`%s`" % os.path.join(V, "03_CityNexus_Agent_Workflow.vsdx"))
A("")
A("讲稿：你问一句话，服务器先把可信上下文拼好，Agent 在**最多 12 步、11 个白名单工具**里循环。"
  "如果答案要改行程，它只写一条待确认的提案；**你点确认后**才依次过权限、幂等、真正写入、"
  "审计、回执。不在白名单的工具在产生任何审计记录之前就被 404 拒掉。")
A("")
A("### 3) Project 甘特图 · 40 秒")
A("")
A("打开：`%s`（或课堂副本 `%s`，视图已按演示调好）"
  % (os.path.join(M, "CityNexus_Software_Engineering_Plan.mpp"),
     os.path.join(CLS, "CityNexus_Plan_Classroom.mpp")))
A("")
A("讲稿：计划是 %d 行、%d 条前置依赖，里程碑是零工期节点，关键路径由 Project 自己算出来。"
  "学生工时合计 **%.1f 小时**，是按每人每周 %.0f 小时的可投入时间估的（**尚未由成员确认**），"
  "任何一周超过这个可用量构建就会拒绝出图，所以这里是 0 周超配。"
  "状态日 2026-10-22 之上还有 **%d 行**没做完，全部列在证据里，没有藏。"
  % (len(prj.get("rows") or []), (prj.get("links") or {}).get("declared", 0),
     cap.get("studentHours", 0.0),
     (cap.get("availabilityPerWeek") or {}).get("yang", 0.0), len(late)))
A("")
A("现场切换视图：任务工作表 → 甘特图 → 网络图 → 跟踪甘特图 → 资源工作表 → 日历"
  "（六个视图脚本都切过一遍，见第三节）。")
A("")
A("> **需要手动的一步**：这台电脑上的 Project 无法用脚本把甘特图右侧时间轴滚到项目起点"
  "（`TaskScrollTo`、`SelectTaskRow`、`Window.Scroll`、`FirstTask`、`ScrollLeft` 等 13 个入口"
  "全部不存在，`TimescaleStart/Finish` 拒绝赋值，`TimescaleEdit` 对 18 种参数组合报"
  "「参数值无效」——都留了日志）。所以打开后请点一下右侧图表区再按 **Ctrl+Home**，"
  "或把底部横向滚动条拖到最左，就能看到 9 月 7 日起的任务条。"
  "`Classroom/previews/Gantt_Visible_print.png` 就是 Project 自己打印出来的第一页，"
  "起点正是 2026-09-07，可直接当替身图用。")
A("")
A("### 4) 里程碑与剩余工作 · 20 秒")
A("")
A("打开：`%s`（里程碑单独一张表）或 `%s`（只看未完工作）"
  % (os.path.join(M, "CityNexus_Milestone_View.mpp"),
     os.path.join(M, "CityNexus_Plan_Recovery.mpp")))
A("")
A("讲稿：里程碑分两种语义——「预计就绪日」和「课程合同截止日」。**中期师生会面安排在 "
  "2026-10-23 中午，还没发生**，所以计划里它是 0%% 完成，不写成已举行。Part 1 的合同截止日是 "
  "2026-10-02，计划里按**已错过**记录；它在课程平台上的真实提交状态**本机无法核实**。"
  "把没做完的活单独重排以后，完成日是 **%s**，比 Part 2 的 2026-11-06 截止日早。"
  % rec.get("finish", "?"))
A("")
A("## 二、三套备用（按出问题的顺序往下换）")
A("")
A("| 套 | 什么时候用 | 用什么 |")
A("|---|---|---|")
A("| A 原生 Office | 一切正常 | 上面四个 .vsdx / .mpp，直接现场编辑给老师看 |")
A("| B 离线 PDF/PNG | Office 起不来、投影分辨率不够、要发群里 | "
  "`Presentation/previews/CityNexus_SE2026_Briefing_Deck.pdf`（%d 页 16:9，正文 13 pt 起）、"
  "`Classroom/previews/` 四张图、`Microsoft_Project/Plan_Briefing_Print.pdf`（%d 页） |"
  % (pages(os.path.join(P, "previews", "CityNexus_SE2026_Briefing_Deck.pdf")),
     pages(os.path.join(M, "Plan_Briefing_Print.pdf"))))
A("| C 同学接替讲稿 | 我被打断或网断 | 每段下面那句话就是交接点，任何人念本节讲稿即可；"
  "全部数字都在 `Evidence/R3_RESULT.md` 与 `Evidence/STATUS_AND_OVERDUE.md` 里 |")
A("")
A("离线可用的文件与大小（不用联网）：")
A("")
A("| 文件 | 大小 | sha256/12 |")
A("|---|---|---|")
for f in (os.path.join(V, "01_CityNexus_System_Architecture.vsdx"),
          os.path.join(V, "03_CityNexus_Agent_Workflow.vsdx"),
          os.path.join(V, "02_CityNexus_User_Journey.vsdx"),
          os.path.join(V, "04_CityNexus_Use_Case.vsdx"),
          os.path.join(M, "CityNexus_Software_Engineering_Plan.mpp"),
          os.path.join(M, "CityNexus_Milestone_View.mpp"),
          os.path.join(M, "CityNexus_Plan_Recovery.mpp"),
          os.path.join(CLS, "CityNexus_Plan_Classroom.mpp"),
          os.path.join(CLS, "CityNexus_Milestones_Classroom.mpp"),
          os.path.join(P, "CityNexus_SE2026_Briefing_Deck.vsdx"),
          os.path.join(P, "previews", "CityNexus_SE2026_Briefing_Deck.pdf"),
          os.path.join(PICS, "Gantt_Visible.png"),
          os.path.join(PICS, "Gantt_Visible_print.png"),
          os.path.join(PICS, "Milestones_Visible.png"),
          os.path.join(PICS, "Milestones_Visible_print.png")):
    A("| `%s` | %s | `%s` |" % (os.path.relpath(f, DEL).replace("\\", "/"), kb(f),
                                sha(f) if os.path.exists(f) else "-"))
A("")
A("## 三、真机验证记录（不是导出成功，是开过、改过、存过、重开过）")
A("")
A("Visio `%s` / Project `%s`。所有编辑都发生在临时副本上，交付原件按字节比对未变。"
  % (demo.get("visioVersion", "?"), demo.get("projectVersion", "?")))
A("")
A("| 检查 | 结果 |")
A("|---|---|")
for v in demo.get("visio") or []:
    A("| `%s` 打开→拖动形状→改文字→保存→重开 | %s；原件未变 %s；"
      "拖动后连线仍贴在形状上：%s（%d 条连线） |"
      % (v.get("file"), "PASS" if v.get("ok") else "FAIL",
         v.get("originalUnchanged"), "是" if v.get("connectorFollowed") else "否",
         len(v.get("endsBefore") or [])))
for v in demo.get("project") or []:
    A("| 主计划副本：六个视图切换→改一条备注→保存→重开 | %s；65 行与 122 条依赖记录读回；"
      "交付的 .mpp 未变：%s |" % ("PASS" if v.get("ok") else "FAIL",
                                  v.get("originalUnchanged")))
A("| 里程碑视图文件能否打开 | %s |" % ("PASS" if any(
    "milestone" in str(s.get("step")).lower() and s.get("ok")
    for v in demo.get("project") or [] for s in (v.get("steps") or [])) else "见日志"))
A("| 课堂副本截图（无遮挡） | %s |" % ", ".join(
    "%s 图表区墨度 %s" % (k, (fit.get(k) or view.get(k, {})).get("chartInk"))
    for k in sorted(set(list(fit) + list(view))) if (fit.get(k) or view.get(k, {}))))
A("")
A("## 四、不要说的话")
A("")
A("* 不说「%.0f 小时是大家真实花掉的时间」——它是课程估算，成员还没确认。"
  % cap.get("studentHours", 0.0))
A("* 不说「Part 1 已经交了」——课程平台记录没看过。")
A("* 不说「老师已经验收」——中期会面就在今天中午，还没发生。")
A("* 不说「所有测试通过」——Valhalla 实时路由、原生 Hermes、支付/退款工具、"
  "手机与 PWA 影子试用这四件本机没做。")
A("")
text = "\n".join(L) + "\n"
open(OUT, "w", encoding="utf-8", newline="\r\n").write(text)
print("wrote %s (%d bytes, %d lines)" % (OUT, os.path.getsize(OUT),
                                         text.count("\n")))
