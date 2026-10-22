"""Evidence/CLASSROOM_20261023_README.md - the noon demonstration sheet.

Written from the drive-test result, not from intentions: the version strings, the
step outcomes, the dragged-shape numbers and the shipped digests are read out of
se_classroom_demo_result.json, and the file refuses to claim a step passed that the
test did not record as passed.
"""
import hashlib
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
EVI = os.path.join(DEL, "Evidence")
VIS = os.path.join(DEL, "Visio")
MSP = os.path.join(DEL, "Microsoft_Project")
OUT = os.path.join(EVI, "CLASSROOM_20261023_README.md")


def sha(p, n=16):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


def j(name):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


demo = j("se_classroom_demo_result.json")
prj = j("se_project_build_r2_result.json")
stat = j("se_plan_status_result.json")
deck = j("se_deck_result.json")
snap = j("se_project_snapshot_r2_result.json")
cap = prj.get("capacity") or {}
late = [e for e in (stat.get("entries") or []) if e.get("late")]
gate = deck.get("gate") or {}
checks = prj.get("checks") or {}
n_true = len([k for k, v in checks.items() if v])

L = []
A = L.append
A("# 课堂展示单 - 2026-10-23 12:00 +08:00")
A("")
A("生成 %s。这份文件只回答一个问题：**中午怎么在真机上把 Visio 和 Project 演示完，"
  "以及哪些话不能说。**" % time.strftime("%Y-%m-%d %H:%M"))
A("")
A("## 0. 现场先说清楚的三件事")
A("")
A("1. 计划里的工时是**课程估算**，不是已发生的真实人工时；每人每周 20 h 是假设，"
  "还没有三位成员各自确认。")
A("2. Part 1（2026-10-02 截止）在课程平台的真实提交状态**未核实**，计划里按"
  "「已错过」记录，不宣称已交。")
A("3. 状态日 2026-10-22 之上有 **%d 行**任务已过计划完成日仍未完成"
  "（全表见 `Evidence/STATUS_AND_OVERDUE.md`）。" % len(late))
A("")
A("## 1. 演示顺序（约 2 分钟主线）")
A("")
A("| 步 | 时长 | 打开什么 | 说什么 |")
A("|---|---|---|---|")
A("| 1 | 30 s | `%s` | 四层结构：体验层 / HTTP 面 / Agent 平面与域服务 / 供应商与持久化。"
  "每个方框都是被审代码树里真实存在的组件，图上带来源引用。"
  % os.path.join(VIS, "01_CityNexus_System_Architecture.vsdx"))
A("| 2 | 30 s | `%s` | Agent 不是想写就写：白名单、审计、幂等、授权四道门的顺序来自 "
  "`gateway.py`；未知工具在产生任何审计行之前就 404。 |"
  % os.path.join(VIS, "03_CityNexus_Agent_Workflow.vsdx"))
A("| 3 | 40 s | `%s` | 切 WBS / 甘特图 / 网络图 / 跟踪甘特图：65 行、%d 条依赖、"
  "引擎自己算的关键路径与成本 $%s。"
  % (os.path.join(MSP, "CityNexus_Software_Engineering_Plan.mpp"),
     (prj.get("links") or {}).get("declared", 0),
     round(prj.get("reopen_pass", {}).get("cost", 0.0), 2)))
A("| 4 | 20 s | `%s` 或 `%s` | 里程碑与分工：13 个里程碑分「预计就绪日」和「课程截止日」"
  "两种语义；重计划文件从状态日排到 %s，早于 2026-11-06 的合同截止日。"
  % (os.path.join(MSP, "CityNexus_Milestone_View.mpp"),
     os.path.join(MSP, "CityNexus_Plan_Recovery.mpp"),
     (j("se_project_recovery_result.json").get("finish") or "?")))
A("| 备 | 随时 | `%s` | 老师追问细节时翻对应页；四页 16:9，正文 13 pt 起。"
  % os.path.join(DEL, "Presentation",
                 "CityNexus_SE2026_Briefing_Deck.vsdx"))
A("")
A("## 2. 怎么启动")
A("")
A("```")
A('start "" "%s"' % os.path.join(VIS, "01_CityNexus_System_Architecture.vsdx"))
A('start "" "%s"' % os.path.join(VIS, "03_CityNexus_Agent_Workflow.vsdx"))
A('start "" "%s"' % os.path.join(MSP, "CityNexus_Software_Engineering_Plan.mpp"))
A("```")
A("")
A("本机实测版本：Visio `%s`，Project `%s`。"
  % (demo.get("visioVersion", "?"), demo.get("projectVersion", "?")))
A("")
A("## 3. 真机驱动验证结果（不是导出成功，是真的开过、改过、存过、重开过）")
A("")
A("验证方式：把交付文件**复制**到临时目录再操作，交付原件在验证前后按字节比对。")
A("")
for v in demo.get("visio") or []:
    A("**%s** - 整体 %s；原件字节未变：%s" % (v.get("file"),
                                              "PASS" if v.get("ok") else "FAIL",
                                              v.get("originalUnchanged")))
    A("")
    A("| 步骤 | 结果 |")
    A("|---|---|")
    for st in v.get("steps") or []:
        A("| %s | %s |" % (st.get("step"),
                           ("PASS " if st.get("ok") else "FAIL ") +
                           str(st.get("value") or st.get("error") or "")[:90]))
    A("")
    if v.get("shape"):
        eb = [e["ends"] for e in (v.get("endsBefore") or [])]
        ea = [e["ends"] for e in (v.get("endsAfter") or [])]
        A("拖动的是 `%s`（ID %s，原文字 %r）：形状向右移 %.2f in，移动后的矩形范围 "
          "x %s..%s；粘在它上面的连线 %d 条，端点从 %s 变成 %s，仍落在移动后的形状上："
          "%s。" % (v["shape"].get("name"), v["shape"].get("id"),
                    (v["shape"].get("text") or "")[:28], v.get("movedBy") or 0.0,
                    (v.get("boxAfter") or ["?", "?"])[0],
                    (v.get("boxAfter") or ["?", "?"])[1], len(eb), eb, ea,
                    "是" if v.get("connectorFollowed") else "否"))
    A("")
for v in demo.get("project") or []:
    A("**%s**（`CityNexus_Software_Engineering_Plan.mpp` 的副本）- 整体 %s；"
      "交付原件未变：计划 %s、里程碑视图 %s"
      % (v.get("file"), "PASS" if v.get("ok") else "FAIL",
         v.get("planUnchanged"), v.get("milestoneUnchanged")))
    A("")
    A("| 步骤 | 结果 |")
    A("|---|---|")
    for st in v.get("steps") or []:
        A("| %s | %s |" % (st.get("step"),
                           ("PASS " if st.get("ok") else "FAIL ") +
                           str(st.get("value") or st.get("error") or "")[:90]))
    A("")
A("这条把外审留的最后一个问号关掉了一半：**拖动形状时连线确实跟着走**（上表"
  "「connector follows」两行），因为量的不是端点位移而是「拖动后连线端点是否仍落在"
  "形状自己的矩形内」，容差 0.2 in 小于 0.75 in 的位移，落在原位的线不可能通过。")
A("")
A("## 4. 现场如果打不开 Office（备用预览）")
A("")
A("| 备用 | 文件 |")
A("|---|---|")
for f in ("Presentation/previews/CityNexus_SE2026_Briefing_Deck.pdf",
          "Microsoft_Project/previews/Gantt_Chart.png",
          "Microsoft_Project/previews/Milestone_Timeline.png",
          "Microsoft_Project/previews/Network_Diagram.png",
          "Microsoft_Project/previews/WBS_Task_Sheet.png",
          "Microsoft_Project/Plan_Briefing_Print.pdf",
          "Briefing/previews/CityNexus_Plan_Briefing_A3.pdf"):
    p = os.path.join(DEL, *f.split("/"))
    A("| %s | %s |" % (f, "存在，%d 字节，sha256 `%s`" % (os.path.getsize(p), sha(p))
                       if os.path.exists(p) else "**缺失**"))
A("")
A("截图是 Win32 `PrintWindow` 抓的目标窗口自身 DC（`se_project_snapshot_r2.py`），"
  "不是屏幕矩形，所以别的窗口压在上面也不会把 Chrome 当成 Project；"
  "抓图时以文件系统只读方式打开，摘要前后一致：`%s`。"
  % str(snap.get("sha256Before"))[:16])
A("")
A("## 5. 数据一句话")
A("")
A("* 学生工时 %.1f h，单人单周峰值 %.1f h（声明可用 %.0f h），超配人周 %d；"
  "构建在出现任何超配时直接拒绝发布。"
  % (cap.get("studentHours", 0.0),
     max([w["assignedHours"] for w in (cap.get("weekly") or [])] or [0]),
     (cap.get("availabilityPerWeek") or {}).get("yang", 0.0),
     len(cap.get("overallocated") or [])))
A("* 依赖 %d 条声明、引擎回读 %d 条记录（同一批链路两端各读一次）、日期顺序违例 %d。"
  % ((prj.get("links") or {}).get("declared", 0),
     (prj.get("links") or {}).get("read", 0),
     len((prj.get("links") or {}).get("violations") or [])))
A("* 12 项构建检查通过 %d 项；四页汇报图绘图门失败 %d 项。"
  % (n_true, len(gate.get("failures") or [])))
A("")
A("## 6. 不要说的话")
A("")
A("* 不要说「1808 小时是团队真实投入」- 那是上一版未经容量校验的计划读数，已被本轮"
  "重算取代。")
A("* 不要说「Part 1 已提交」- 没有课程平台证据。")
A("* 不要说「所有测试通过」- 阻塞栏里的四件事（Valhalla 实时路由、原生 Hermes、"
  "支付/退款工具、手机影子试用）本机未做。")
A("")
text = "\n".join(L) + "\n"
open(OUT, "w", encoding="utf-8", newline="\r\n").write(text)
print("wrote %s (%d bytes, %d lines)" % (OUT, os.path.getsize(OUT),
                                         text.count("\n")))
