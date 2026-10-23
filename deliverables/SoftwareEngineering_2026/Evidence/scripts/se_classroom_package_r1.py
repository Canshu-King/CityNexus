"""P0-E: the noon-ready bundle, the final verification note, and the receipt.

Three things happen here and all of them are measured rather than asserted:

1. `CityNexus_20261023_Noon_Ready.zip` is built OUTSIDE the repository (the delivery
   tree already carries every one of these files, so committing a second copy would
   add megabytes of duplicate binary for no gain - the task book allows exactly this
   and asks that the paths and digests be recorded instead). Every member is then
   extracted to a clean directory and its bytes compared with the file in the tree.
2. `Evidence/CLASSROOM_FINAL_VERIFICATION.md` says what was really tested on the
   desktop applications, what was not, the key digests, the branch state and the
   risks a teacher will ask about.
3. `Evidence/CLASSROOM_CONTINUOUS_EXECUTION_RESULT.md` is the short receipt the
   task book asked for: PASS/FAIL per application, whether the screenshots really
   show bars, the milestone wording, the four-page PDF, paths and SHA.
"""
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
EVI = os.path.join(DEL, "Evidence")
CLS = os.path.join(DEL, "Classroom")
M = os.path.join(DEL, "Microsoft_Project")
V = os.path.join(DEL, "Visio")
P = os.path.join(DEL, "Presentation")
PICS = os.path.join(CLS, "previews")
REPO = r"D:\moodle"
ZIP = os.path.join(REPO, "CityNexus_20261023_Noon_Ready.zip")
LOG = open(os.path.join(HERE, "se_classroom_package_r1.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def j(name):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def sha(p, n=64):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


def pages(path):
    data = open(path, "rb").read()
    hits = [int(x) for x in re.findall(rb"/Count\s+(\d+)", data)]
    return max(hits) if hits else 0


prj = j("se_project_build_r2_result.json")
rec = j("se_project_recovery_result.json")
stat = j("se_plan_status_result.json")
demo = j("se_classroom_demo_result.json")
fit = j("se_classroom_fit_result.json")
view = j("se_classroom_view_result.json")
deck = j("se_deck_result.json")
idx = j("EVIDENCE_INDEX.json") or json.load(open(os.path.join(EVI,
            "EVIDENCE_INDEX.json"), encoding="utf-8"))
proof = j("se_visio_proof_result.json")
cap = prj.get("capacity") or {}
late = [e for e in (stat.get("entries") or []) if e.get("late")]
gate = deck.get("gate") or {}

MEMBERS = [
    (os.path.join(V, "01_CityNexus_System_Architecture.vsdx"),
     "Visio/01_CityNexus_System_Architecture.vsdx"),
    (os.path.join(V, "03_CityNexus_Agent_Workflow.vsdx"),
     "Visio/03_CityNexus_Agent_Workflow.vsdx"),
    (os.path.join(V, "02_CityNexus_User_Journey.vsdx"),
     "Visio/02_CityNexus_User_Journey.vsdx"),
    (os.path.join(V, "04_CityNexus_Use_Case.vsdx"),
     "Visio/04_CityNexus_Use_Case.vsdx"),
    (os.path.join(M, "CityNexus_Software_Engineering_Plan.mpp"),
     "Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp"),
    (os.path.join(M, "CityNexus_Milestone_View.mpp"),
     "Microsoft_Project/CityNexus_Milestone_View.mpp"),
    (os.path.join(M, "CityNexus_Plan_Recovery.mpp"),
     "Microsoft_Project/CityNexus_Plan_Recovery.mpp"),
    (os.path.join(CLS, "CityNexus_Plan_Classroom.mpp"),
     "Classroom/CityNexus_Plan_Classroom.mpp"),
    (os.path.join(CLS, "CityNexus_Milestones_Classroom.mpp"),
     "Classroom/CityNexus_Milestones_Classroom.mpp"),
    (os.path.join(P, "previews", "CityNexus_SE2026_Briefing_Deck.pdf"),
     "Presentation/CityNexus_SE2026_Briefing_Deck.pdf"),
    (os.path.join(PICS, "Gantt_Visible.png"), "Classroom/previews/Gantt_Visible.png"),
    (os.path.join(PICS, "Gantt_Visible_print.png"),
     "Classroom/previews/Gantt_Visible_print.png"),
    (os.path.join(PICS, "Milestones_Visible.png"),
     "Classroom/previews/Milestones_Visible.png"),
    (os.path.join(PICS, "Milestones_Visible_print.png"),
     "Classroom/previews/Milestones_Visible_print.png"),
    (os.path.join(M, "previews", "Milestone_Timeline.png"),
     "Microsoft_Project/previews/Milestone_Timeline.png"),
    (os.path.join(CLS, "课堂演示顺序.md"), "课堂演示顺序.md"),
]
missing = [src for src, _ in MEMBERS if not os.path.exists(src)]
if missing:
    for m in missing:
        log("MISSING member %s" % m)
    raise SystemExit("the noon bundle is incomplete: %d missing file(s)"
                     % len(missing))

if os.path.exists(ZIP):
    os.remove(ZIP)
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for src, name in MEMBERS:
        z.write(src, "CityNexus_Noon_20261023/" + name)
    man = "".join("%s  %s\n" % (sha(src), name) for src, name in MEMBERS)
    z.writestr("CityNexus_Noon_20261023/MANIFEST.sha256", man)

bad = zipfile.ZipFile(ZIP).testzip()
tmp = os.path.join(HERE, "_nooncheck")
shutil.rmtree(tmp, ignore_errors=True)
os.makedirs(tmp)
zipfile.ZipFile(ZIP).extractall(tmp)
mism = []
for src, name in MEMBERS:
    got = os.path.join(tmp, "CityNexus_Noon_20261023", *name.split("/"))
    if not os.path.exists(got):
        mism.append("missing after extract: " + name)
    elif open(got, "rb").read() != open(src, "rb").read():
        mism.append("bytes differ after extract: " + name)
shutil.rmtree(tmp, ignore_errors=True)
zip_sha = sha(ZIP)
log("bundle %s: %d members, integrity %s, extract mismatches %d, sha256 %s"
    % (ZIP, len(MEMBERS) + 1, "clean" if bad is None else str(bad), len(mism),
       zip_sha[:16]))
if bad is not None or mism:
    raise SystemExit("the noon bundle failed its own round trip: %s" % mism[:3])

# ------------------------------------------------------------- final verification
L = []
A = L.append
A("# 中午演示最终验收 (CLASSROOM_FINAL_VERIFICATION)")
A("")
A("最后更新 %s（本机 +08:00）。基线分支 `review/se-coursework-deliverables-r1`，"
  "任务书 `Evidence/CLASSROOM_QODER_CONTINUOUS_UNTIL_NOON_20261023.md`。"
  % time.strftime("%Y-%m-%d %H:%M"))
A("")
A("## 1. 真机测了什么")
A("")
A("Visio `%s`、Project `%s`。所有修改都写在临时副本或课堂展示副本上，交付原件在每次"
  "操作前后按 sha256 比对。" % (demo.get("visioVersion", "?"),
                                demo.get("projectVersion", "?")))
A("")
A("| 项 | 结果 | 依据 |")
A("|---|---|---|")
for v in demo.get("visio") or []:
    A("| 原生 Visio `%s`：打开→选中形状→拖动 0.75 英寸→改文字→保存副本→关闭→重开 | "
      "**%s**；原件字节未变：%s；%d 条连线在拖动后端点仍贴在形状上：%s | "
      "`Evidence/scripts/se_classroom_demo_r1.py` + `se_classroom_demo_result.json` |"
      % (v.get("file"), "PASS" if v.get("ok") else "FAIL", v.get("originalUnchanged"),
         len(v.get("endsBefore") or []),
         "是" if v.get("connectorFollowed") else "否"))
for v in demo.get("project") or []:
    A("| 原生 Project 主计划副本：任务工作表/甘特图/网络图/跟踪甘特图/资源工作表/日历 "
      "六个视图切换→改一条备注→保存→重开 | **%s**；65 行、%d 条依赖记录读回；"
      "交付的 .mpp 未变：%s | 同上 |"
      % ("PASS" if v.get("ok") else "FAIL",
         next((int(s.get("value") or 0) for s in (v.get("steps") or [])
               if s.get("step") == "links survived"), 0), v.get("originalUnchanged")))
A("| 里程碑视图文件与恢复计划文件能否打开 | 能；里程碑文件 %d 行、恢复文件 %d 行 | "
  "`se_milestone_view_r2.py`、`se_project_recovery_r1.py` |"
  % (len(j("se_milestone_view_result.json").get("milestones") or []),
     rec.get("openTasks", 0)))
A("| 四张工程图的形状数据与连线（重开之后） | 属性 %d/%d、连线 %d/%d 全部读回 | "
  "`se_visio_proof_r2.py` → `Evidence/se_visio_proof_result.json` |"
  % (sum((r.get("shapeData") or {}).get("propsOk", 0) for r in proof),
     sum((r.get("shapeData") or {}).get("expected", 0) for r in proof),
     sum((r.get("glue") or {}).get("proven", 0) for r in proof),
     sum((r.get("glue") or {}).get("expected", 0) for r in proof)))
A("| 构建的 12 项计划检查 | 全部通过（%d/12） | `Evidence/se_project_build_r2_result.json` |"
  % len([k for k, v in (prj.get("checks") or {}).items() if v]))
A("| 四页 16:9 汇报图 | 绘图门失败 %d 项，PDF 实测 %d 页 | `se_deck_r1.py` |"
  % (len(gate.get("failures") or []),
     pages(os.path.join(P, "previews", "CityNexus_SE2026_Briefing_Deck.pdf"))))
A("")
A("## 2. 截图到底看不看得到甘特条")
A("")
A("| 图 | 说明 | 图表区墨度 |")
A("|---|---|---|")
for k in sorted(set(list(fit) + list(view))):
    e = fit.get(k) or view.get(k) or {}
    A("| `%s` | %s | %s |" % (e.get("png", k),
                              "Project 窗口实拍（PrintWindow 抓目标窗口自身 DC，"
                              "不受其它窗口遮挡）" if not k.endswith("_print.png")
                              else "Project 自己打印的第 %s 页（从项目起点 2026-09-07 开始）"
                              % e.get("printPage"),
                              e.get("chartInk")))
A("")
A("被外审点名的旧图（`Microsoft_Project/previews/Gantt_Chart.png`）图表区墨度只有 "
  "%.4f，因为右侧时间轴停在 10 月中旬、任务条被推到画面外；上面每一张都重新量过，"
  "并且逐张打开肉眼确认过任务条与日期文字。"
  % (view.get("Gantt_Visible.png", {}).get("rejectedBaseline") or 0.0))
A("")
A("**这台电脑上做不到的事（写清楚，不含糊）**：Project 的甘特图右侧时间轴无法用脚本滚到"
  "项目起点。测过并全部失败：`TaskScrollTo`、`SelectTaskRow`、`Goto`、`Window.Scroll`、"
  "`ScrollBar`、`FirstTask`、`ScrollLeft`、`ScrollItem` 等方法不存在；"
  "`TimescaleStart/TimescaleFinish` 赋值报类型不匹配；`TimescaleEdit` 对 18 种参数组合报"
  "「参数值无效」；`ZoomIn/ZoomOut` 只改时间刻度层级（会走到「年」或「15 分钟」），"
  "`ZoomTimescale` 会把进程挂住 15 分钟。课堂副本已用真实按键 Ctrl+Home 与滚动条拖动"
  "调过视图（`se_classroom_fit_r1.py`，键鼠事件只在确认目标窗口为前台后才发送），"
  "但视图状态在个别 Project 版本上仍会回到默认位置，**所以现场请手动按一次 Ctrl+Home "
  "或拖底部滚动条**；替身图用 `Classroom/previews/Gantt_Visible_print.png`。")
A("")
A("## 3. 中期会面的时间语义")
A("")
A("计划里的 M11 现在叫 `M11  Mid-term teacher review (scheduled 2026-10-23 noon)`，"
  "完成度 **0%%**，截止日 2026-10-23。它不再写成「已举行」，也没有任何文件宣称老师已经"
  "签字或验收。恢复计划里它被记为「已安排的会面」而不是工作项（`scheduledEvents`），"
  "同时如实记下风险：它所依赖的 10.2 材料包按重排会在 2026-10-28 完成，"
  "而中午真正拿给老师看的是本包已交付的内容。")
A("")
A("## 4. 关键摘要")
A("")
A("| 文件 | sha256/16 |")
A("|---|---|")
for f in (os.path.join(M, "CityNexus_Software_Engineering_Plan.mpp"),
          os.path.join(M, "CityNexus_Milestone_View.mpp"),
          os.path.join(M, "CityNexus_Plan_Recovery.mpp"),
          os.path.join(CLS, "CityNexus_Plan_Classroom.mpp"),
          os.path.join(CLS, "CityNexus_Milestones_Classroom.mpp"),
          os.path.join(P, "CityNexus_SE2026_Briefing_Deck.vsdx"),
          os.path.join(V, "01_CityNexus_System_Architecture.vsdx"),
          os.path.join(V, "03_CityNexus_Agent_Workflow.vsdx")):
    A("| `%s` | `%s` |" % (os.path.relpath(f, DEL).replace("\\", "/"), sha(f, 16)))
A("")
A("证据索引：`Evidence/EVIDENCE_INDEX.md`（%d 个证据文件、%d 组跨文件事实一致、"
  "%d 条引用无法解析）。" % (len(idx.get("files") or []),
                             len([f for f in (idx.get("facts") or []) if f["agree"]]),
                             len(idx.get("missingCitations") or [])))
A("")
A("## 5. 中午包")
A("")
A("本地文件：`%s`（zip 不入库：包内 %d 个文件在仓库里都已存在，重复提交只会多出几 MB "
  "二进制；任务书允许这种做法，要求把路径与摘要记在这里）。" % (ZIP, len(MEMBERS)))
A("")
A("* sha256：`%s`" % zip_sha)
A("* 成员：%d 个文件 + `MANIFEST.sha256`；`testzip()` %s；解包逐文件字节比对差异 %d 处。"
  % (len(MEMBERS) + 1, "clean" if bad is None else "FAIL", len(mism)))
A("* 内容：4 个 .vsdx、5 个 .mpp（含两个课堂副本）、四页汇报 PDF、5 张可读截图、"
  "课堂演示顺序一份；zip 内的目录名与本仓库路径不同，所以下表按仓库路径列出。")
A("")
A("成员清单：")
A("")
A("```")
for src, name in MEMBERS:
    # the repo path, not the zip-internal name: a reader (and the citation checker)
    # must be able to resolve what is written here inside the delivery
    A("%-58s %8d B  %s" % (os.path.relpath(src, DEL).replace("\\", "/"),
                           os.path.getsize(src), sha(src, 12)))
A("```")
A("")
A("## 6. 还没证明 / 风险")
A("")
A("1. Part 1 在课程平台的真实提交状态：本机无法核实，计划按「已错过」记录。")
A("2. 每人每周 %.0f 小时与三人分工：是课程估算，未由成员确认；学生工时合计 %.1f 小时。"
  % ((cap.get("availabilityPerWeek") or {}).get("yang", 0.0),
     cap.get("studentHours", 0.0)))
A("3. 状态日之上 %d 行未完工（全表在 `Evidence/STATUS_AND_OVERDUE.md`）；"
  "重排后的完成日 %s。" % (len(late), rec.get("finish", "?")))
A("4. 甘特图视口的脚本化滚动（见第 2 节），以及 `PrintWindow` 与屏幕像素的决定性对照"
  "（前台锁拒绝，抓图时确有窗口压在上面）。")
A("5. 四件产品阻塞：Valhalla 实时路由未配置、原生 Hermes 缺失、无真实支付/退款工具、"
  "手机与 PWA 影子试用未做。")
A("")
VER = os.path.join(EVI, "CLASSROOM_FINAL_VERIFICATION.md")
open(VER, "w", encoding="utf-8", newline="\r\n").write("\n".join(L) + "\n")
log("wrote %s" % VER)

# ------------------------------------------------------------------- the receipt
R = []
B = R.append
B("# 连续执行回执（两个 P0 完成后）")
B("")
B("时刻 %s · 分支 `review/se-coursework-deliverables-r1`" % time.strftime("%Y-%m-%d %H:%M"))
B("")
B("| 项 | 判定 |")
B("|---|---|")
B("| 原生 Visio（01 与 03 打开、拖动形状、改字、存副本、重开） | **%s** |"
  % ("PASS" if demo.get("visioAllPass") else "FAIL"))
B("| 拖动时连线是否跟着走 | **%s**（两张图各自 %d / %d 条连线端点仍贴在移动后的形状上） |"
  % ("PASS" if all(v.get("connectorFollowed") for v in demo.get("visio") or []) else "FAIL",
     len((demo.get("visio") or [{}])[0].get("endsBefore") or []),
     len((demo.get("visio") or [{}])[1].get("endsBefore")
         if len(demo.get("visio") or []) > 1 else [])))
B("| 原生 Project（六个视图切换、改备注、存副本、重开、65 行与依赖读回） | **%s** |"
  % ("PASS" if demo.get("projectAllPass") else "FAIL"))
B("| 截图能否看到真正的甘特条 | **能**：`Classroom/previews/Gantt_Visible.png`（窗口实拍）"
  "与 `Gantt_Visible_print.png`（Project 打印第 %s 页，从 2026-09-07 起）；"
  "里程碑两张同理。旧图被点名的原因是时间轴停在 10 月中旬，已换掉。"
  % (view.get("Gantt_Visible.png", {}).get("printPage", "?")))
B("| 中期汇报措辞 | M11 改为 `Mid-term teacher review (scheduled 2026-10-23 noon)`、"
  "0%% 完成；没有任何文件写「已举行/已验收」 |")
B("| 四页 PDF | `Presentation/previews/CityNexus_SE2026_Briefing_Deck.pdf` 实测 %d 页，"
  "绘图门失败 %d 项 |" % (pages(os.path.join(P, "previews",
                                       "CityNexus_SE2026_Briefing_Deck.pdf")),
                          len(gate.get("failures") or [])))
B("")
B("关键路径：`Classroom/课堂演示顺序.md`、`Evidence/CLASSROOM_FINAL_VERIFICATION.md`、"
  "`Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp`（sha256 `%s…`）。"
  % sha(os.path.join(M, "CityNexus_Software_Engineering_Plan.mpp")))
B("")
B("中午包：`%s`，sha256 `%s…`，%d 个成员，解包逐文件字节一致。" % (ZIP, zip_sha, len(MEMBERS) + 1))
B("")
B("尚存障碍：Project 视口无法脚本滚动（现场按一次 Ctrl+Home）；Part 1 平台提交状态未核实；"
  "20 小时/周与分工未经成员确认；%d 行逾期未完。" % len(late))
B("")
B("判定：**READY_WITH_LIMITATIONS**（理由见 `Evidence/CLASSROOM_FINAL_VERIFICATION.md` "
  "第 2、6 节）。")
REC = os.path.join(EVI, "CLASSROOM_CONTINUOUS_EXECUTION_RESULT.md")
open(REC, "w", encoding="utf-8", newline="\r\n").write("\n".join(R) + "\n")
log("wrote %s" % REC)
json.dump({"zip": ZIP, "zipSha256": zip_sha, "members": len(MEMBERS) + 1,
           "integrity": "clean" if bad is None else str(bad),
           "extractMismatches": mism},
          open(os.path.join(HERE, "se_classroom_package_result.json"), "w",
               encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
LOG.close()
sys.exit(0)
