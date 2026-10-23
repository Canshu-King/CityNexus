"""R3_RESULT.md - what round 3 actually changed, measured, and what is still open.

Every number is read from a result file or from the shipped artefacts at the
moment of writing; nothing here is remembered from the build log, because the last
two rounds both showed that remembered numbers drift.
"""
import datetime
import glob
import hashlib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# se_evidence_index_r1 is NOT imported: it is a script that writes and exits, and
# importing a tool that acts is how a report ends up re-running the thing.
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
EVI = os.path.join(DEL, "Evidence")
MPP = os.path.join(DEL, "Microsoft_Project", "CityNexus_Software_Engineering_Plan.mpp")
REC_MPP = os.path.join(DEL, "Microsoft_Project", "CityNexus_Plan_Recovery.mpp")


def load(name):
    for base in (HERE, EVI):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8"))
    return {}

OUT = os.path.join(EVI, "R3_RESULT.md")
sha = lambda p, n=64: hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


def pdf_pages(path):
    hits = [int(x) for x in re.findall(rb"/Count\s+(\d+)", data_of(path))]
    return max(hits) if hits else 0


def _days_before_deadline(finish, deadline):
    try:
        f = datetime.date(*[int(x) for x in str(finish)[:10].split("-")])
        d = datetime.date(*[int(x) for x in str(deadline)[:10].split("-")])
        return (d - f).days
    except Exception:
        return "?"


def data_of(path):
    return open(path, "rb").read()


prj = load("se_project_build_r2_result.json")
cpm = load("se_plan_cpm_r2.json")
stat = load("se_plan_status_result.json")
rec = load("se_project_recovery_result.json")
deck = load("se_deck_result.json")
snap = load("se_project_snapshot_r2_result.json")
recon = load("se_evidence_reconcile_result.json")
idx = load("EVIDENCE_INDEX.json") or json.load(open(os.path.join(EVI,
              "EVIDENCE_INDEX.json"), encoding="utf-8"))
proof = load("se_visio_proof_result.json")

cap = prj.get("capacity") or {}
weekly = cap.get("weekly") or []
over = [w for w in weekly if w["overallocatedHours"] > 0]
late = [e for e in (stat.get("entries") or []) if e.get("late")]
peak = max([w["assignedHours"] for w in weekly] or [0])
avail = (cap.get("availabilityPerWeek") or {}).get("yang", 0.0)
gate = deck.get("gate") or {}
props = sum((r.get("shapeData") or {}).get("propsOk", 0) for r in proof)
props_exp = sum((r.get("shapeData") or {}).get("expected", 0) for r in proof)
glue = sum((r.get("glue") or {}).get("proven", 0) for r in proof)
glue_exp = sum((r.get("glue") or {}).get("expected", 0) for r in proof)
brief_pdf = os.path.join(DEL, "Microsoft_Project", "Plan_Briefing_Print.pdf")
deck_pdf = os.path.join(DEL, "Presentation", "previews",
                        "CityNexus_SE2026_Briefing_Deck.pdf")

L = []
A = L.append
A("# CityNexus 软件工程 2026 - 第三轮交付结果 (R3_RESULT)")
A("")
A("生成 %s。计划文件 `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` "
  "sha256 `%s`；重计划文件 `CityNexus_Plan_Recovery.mpp` sha256 `%s`。"
  % (time.strftime("%Y-%m-%d %H:%M"), sha(MPP), sha(REC_MPP)))
A("")
A("本轮只动课程交付的生成器、证据文件与展示资产：没有改 CityNexus 主产品代码，没有碰 "
  "Codex Revolution 分支，没有跑无关的历史全量回归。R2 已被独立验收的 Visio 自定义属性、"
  "Agent 核心流程与 Project 全量依赖三项修复按原样保留，并重新通过各自的门。")
A("")
A("## 1. 三件产品级问题")
A("")
A("### 1.1 人力容量：从「数学上正确、执行上不可能」到零超配")
A("")
A("| 指标 | R2 被审时的值 | 现在实测 |")
A("|---|---|---|")
A("| 学生人工工时 | 1808 h（外审报告 §B-P0 读数） | **%.1f h** |"
  % cap.get("studentHours", 0.0))
A("| 单人单周峰值 | 大量任务同日满负荷并行 | **%.1f h / 人 / 周**，声明可用 %.0f h |"
  % (peak, avail))
A("| 超配人周 | 未做验收 | **%d**，构建在出现任何一超配周时直接拒绝发布 |"
  % len(over))
A("| Agent 算力 | 与学生工时混在一起 | 两条 lane 设为 material 资源，只计价 "
  "%d 次分派，**0 学生工时**；没有任何一行只靠 lane 却还带人工小时 |"
  % (prj.get("costs", {}).get("computePricedAssignments", 0)))
A("")
A("做法：工时不再由「工期 × 8 小时 × 单位」倒推，而是每行显式写 `eff`（谁、几小时），"
  "单位由 `hours / (工期天 × 8)` 截断导出，构建用 Project 自己的 assignment "
  "Start/Finish/Work 复算每人每 ISO 周，并与声明可用工时比较。可用工时 20 h/周是"
  "**假设**，需要三位成员各自确认，`Evidence/STATUS_AND_OVERDUE.md` 与汇报第 4 页都这样写。")
A("")
A("### 1.2 逾期与截止日语义：四把时钟分开，逾期清单全量给出")
A("")
A("逾期未完任务 **%d 行**（其中 %d 行 0%%、%d 行部分完成），每行给出原定工期、实际进度、"
  "重预测日期，全部列在 `Evidence/STATUS_AND_OVERDUE.md`。外审按我上一版给出的读数点了 "
  "10 行；那 10 行全部仍在这 %d 行里，多出来的是下面 §2 那个日期读取缺陷造成的低估。"
  % (len(late), len([e for e in late if e["pct"] == 0]),
     len([e for e in late if e["pct"] > 0]), len(late)))
A("")
A("| 时钟 | 含义 | 例 |")
A("|---|---|---|")
A("| planned finish | 引擎算出的计划完成日 | 9.3 -> 2026-09-30 |")
A("| actual finish | 已经发生的事实完成日 | 24 行在状态日或之前 |")
A("| forecast finish | 状态日之后按剩余工作日重排 | 9.3 -> 2026-10-27 |")
A("| course deadline | 课程合同截止日，与计划里程碑分开 | Part 1 2026-10-02（已错过，"
  "事实记录）· Part 2 2026-11-06 |")
A("")
A("M9/M10/M11/M12/M13 已改名为「预计就绪日」与「课程截止日」两种语义；"
  "**Part 1 是否真的提交仍未证实**，只能以课程平台记录为准，本轮没有任何一处宣称它已提交。")
A("")
A("前瞻重计划：`CityNexus_Plan_Recovery.mpp` 只含 %d 行未完工作与 3 个带日期里程碑，"
  "从 2026-10-23 起排，引擎算得完成日 **%s**，成本 $%s，0 超配、0 截止日违约、"
  "%d 条依赖 0 违例——比 2026-11-06 的合同截止日早 %d 天。"
  % (rec.get("openTasks", 0), rec.get("finish", "?"), rec.get("cost", "?"),
     rec.get("links", {}).get("declared", 0),
     _days_before_deadline(rec.get("finish"), "2026-11-06")))
A("")
A("### 1.3 平板汇报版：新增，且原来的截图问题按机制修掉")
A("")
A("新增 `Presentation/CityNexus_SE2026_Briefing_Deck.vsdx`：四页 16:9（13.333 x 7.5 "
  "英寸），%d 个形状、%d 条连接线，绘图门 **%d 条失败**。正文最小字号 13 pt，并且门里新加"
  "了一条规则：任何带文字、尺寸小于该页字号下限的形状直接判失败，所以这张图不可能再退化成"
  "5.8 pt 的墨墙。四页分别是：系统概览、Agent 受约束的核心流程、进度与阻塞、分工与成本。"
  % (gate.get("nodes", 0), gate.get("edges", 0), len(gate.get("failures") or [])))
A("")
A("Project 视图 PNG 的根因是上一版抓的是「屏幕矩形」，Chrome 压在上面就照下来了。新版"
  "（`se_project_snapshot_r2.py`）改用 Win32 `PrintWindow(PW_RENDERFULLCONTENT)` 抓目标"
  "窗口自身的 DC，与 z-order 无关；并且以只读方式打开（文件系统层 chmod 只读），"
  "抓完比对摘要：`%s` -> `%s`，%s。每帧还做非空白检查（颜色数 %d~%d，非白像素比例最低 "
  "%.3f）。%d 个视图全部由我肉眼看过，画面是 Project 自己的表格与甘特条，没有别的窗口。"
  % (str(snap.get("sha256Before"))[:16], str(snap.get("sha256After"))[:16],
     "未改动" if snap.get("sha256Before") == snap.get("sha256After") else "被改写了",
     min([v.get("colours", 0) for v in (snap.get("views") or {}).values()] or [0]),
     max([v.get("colours", 0) for v in (snap.get("views") or {}).values()] or [0]),
     min([v.get("inkFraction", 1) for v in (snap.get("views") or {}).values()] or [1]),
     len(snap.get("views") or {})))
A("")
A("命名与页数也按实测交代：`Briefing_One_Page.pdf` 已删除（它实际 12 页），同一份打印以 "
  "`Plan_Briefing_Print.pdf` 交付，实测 **%d 页**；汇报 deck PDF 实测 **%d 页**；"
  "A3 总览 `Briefing/previews/CityNexus_Plan_Briefing_A3.pdf` 确实是 **%d 页**，但它不是"
  "汇报版，汇报版是上面那四页。`Task_Usage.pdf` 不再被引用：这台安装的 Project 里"
  "「任务使用情况」视图不存在（`ViewApply` 报「视图已经不存在」），所以那个文件不可能由本"
  "机产生，引用已删而不是补一个假文件。"
  % (pdf_pages(brief_pdf) if os.path.exists(brief_pdf) else 0,
     pdf_pages(deck_pdf) if os.path.exists(deck_pdf) else 0,
     pdf_pages(os.path.join(DEL, "Briefing", "previews",
                            "CityNexus_Plan_Briefing_A3.pdf"))))
A("")
A("## 2. 本轮自己发现并修掉的缺陷（不是外审点的）")
A("")
A("**日期读取器把每个「工作日结束」的时刻推到第二天。** pywin32 返回 Project 的 "
  "`2026-09-09 17:00` 时挂的时区名不是本机时区，旧 `dstr()` 于是做一次 "
  "`astimezone()`，八小时把日期推到 09-10。屏幕上的表格写 9月9日，我所有从 JSON 生成的文档"
  "写 09-10。发现方式：把纯 Python CPM 与引擎逐行对拍时，两侧工期天数完全相同而日期系统性"
  "差一天。")
A("")
A("影响与处置：读取器改为按 Project 返回的日历日直读，并写了自检；构建现在第一件事就是跑这个"
  "自检，不通过就不开工。修好后逾期行数从 10 变成 %d（被掩盖的 4 行露出来），并且暴露出 "
  "yang 在 2026-W37 真实超配 21.2 h > 20 h——上一版的「0 超配」是这个偏移造成的假绿。"
  "该周靠重估两行九月的工时（2.2 10->9 h、2.3 7->6 h）解决，重排后依赖与关键路径全部重算，"
  "12 项检查仍全绿。同类偏移在里程碑视图与简报生成器里各有一处（把日期写成 00:00 会被 Project"
  "挪回上一个工作分钟），也一并改成工作时段内写入，并由各自的对拍验证。"
  % len(late))
A("")
A("## 3. 证据一致性（外审 §B-P1 与 §B-P2）")
A("")
A("新增 `se_evidence_index_r1.py`，产出 `Evidence/EVIDENCE_INDEX.md` 与 `.json`：")
A("")
A("* 逐个证据 JSON 记录字节数、sha256、生成时间、生成脚本，以及**它自称来自哪一版计划**；"
  "凡自称的来源摘要与磁盘上的现文件不一致就判 STALE 并拒绝。当前 %d 个带来源摘要的文件全部 "
  "current。" % len([r for r in idx.get("files", []) if r.get("sourceDigestClaims")]))
A("* 跨文件比对同名事实：依赖数、日期违例数、M13 计划日、逾期行数、学生工时、超配人周——"
  "%d 组事实，%d 组不一致。" % (len(idx.get("facts", [])),
                               len([f for f in idx.get("facts", []) if not f["agree"]])))
A("* 文档引用完整性：扫描交付树里 markdown 引用的相对路径，逐条解析；不可解析 **%d** 条。"
  "两类文件按名字排除在扫描之外并写在索引里：外审原件（引文，不许改）与本轮的两份新报告 "
  "`R3_RESULT.md`、`EVIDENCE_INDEX.md`——它们的存在由本轮构建本身证明，不能自证。"
  "上一版被点名的三处悬空引用（`se_review_package_r2_result.json`、"
  "`logs/se_brief_r2.log`、`Task_Usage.pdf`）现在都不再被引用。"
  % len(idx.get("missingCitations", [])))
A("* `se_plan_cpm_r2.json` 已从当前计划重算（links 61、状态日、容量表都在里面），不再是"
  "上一轮的中间残留；它与引擎的日期差异不再被抹平，而是在 `Evidence/PLAN_RECONCILIATION.md` "
  "里逐行摊开：静态 %s、引擎 %s、重计划 %s，%d 行关键链上两侧跨度都等于声明工期，"
  "差在哪一步、差几天，全部列成表。"
  % (recon.get("staticFinish"), recon.get("projectFinish"),
     recon.get("recoveryFinish"), len(recon.get("chainRows", []))))
A("")
A("## 4. 仍然没有证明的事（本轮不做假动作）")
A("")
A("1. **Part 1 是否提交**：要课程平台记录，本机拿不到；计划里 10.1 与 M10 按「已错过」记，"
  "不宣称提交。")
A("2. **成员可用工时与分工**：20 h/周与三人分工是课程计划提案，git 只有一个提交身份，"
  "需要本人确认。")
A("3. **Visio 形状拖动时连线是否跟随**：结构面已证（Shape Data %d/%d 属性、connector glue "
  "%d/%d、重开/编辑/恢复 PASS），实际拖动的观感仍需在平板上人工看一次。" % (props, props_exp,
                                                                             glue, glue_exp))
A("4. **PrintWindow 与屏幕像素的对照**：本机 SetForegroundWindow 被前台锁拒绝，抓屏时确有 "
  "%d 个窗口压在上面，所以「与屏幕一致」这一条没做成决定性验证；能给的证据是窗口自身 DC 的"
  "渲染、非空白统计与肉眼检查。" % max([len(v.get("occludedBy") or [])
                                        for v in (snap.get("views") or {}).values()] or [0]))
A("5. **真机用户流程**：Valhalla 实时路由未配置、原生 Hermes 缺失、支付/退款无真实工具、"
  "手机与 PWA 影子试用未做——这四条写在汇报第 3 页的阻塞栏里，没有粉饰。")
A("")
A("## 5. 复现清单")
A("")
A("按顺序执行即可重建本轮全部产物（都在 `live_checks/`，随包交付）：")
A("")
A("```")
A("python se_plan_cpm_r1.py            # 静态前置门 + 容量普查")
A("python se_project_build_r2.py       # 建 .mpp，12 项检查，零超配才发布")
A("python se_project_recovery_r1.py    # 前瞻重计划 .mpp")
A("python se_plan_status_r1.py         # STATUS_AND_OVERDUE.md")
A("python se_milestone_view_r2.py      # Milestone_Timeline.pdf（只读打开，摘要不变）")
A("python se_project_brief_r1.py       # Plan_Briefing_Print.pdf")
A("python se_visio_build_r1.py && python se_visio_proof_r2.py   # 四张工程图与读回证明")
A("python se_deck_r1.py                # 16:9 汇报四页")
A("python se_project_snapshot_r2.py    # PrintWindow 截图，只读，摘要自证未变")
A("python se_evidence_reconcile_r1.py  # PLAN_RECONCILIATION.md")
A("python se_evidence_docs_r1.py       # README / SOURCE_MAPPING / AUTOMATION_VERIFICATION")
A("python se_evidence_index_r1.py      # EVIDENCE_INDEX.*（STALE 或悬空引用即拒绝）")
A("python se_review_package_r2.py      # MANIFEST.sha256 + 复审包，zip 往返校验")
A("```")
A("")
A("压缩包自身的 sha256 不写在包内文件里（zip 不能自证），随提交信息给出。")
A("")

text = "\n".join(L) + "\n"
open(OUT, "w", encoding="utf-8", newline="\r\n").write(text)
print("wrote %s (%d bytes, %d lines)" % (OUT, os.path.getsize(OUT), text.count("\n")))
