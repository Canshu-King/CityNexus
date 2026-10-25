"""R4 第一棒：把「同一份 65 行计划」做成课堂能看的视图副本。

任务书（GitHub Issue #45）的硬要求：
  * 事实源 `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` 只读，
    日期/前驱/人员/资源分配/工时/完成度/成本原样保留；
  * 不许另造一份「16 行无前驱无资源」的演示表，必须是同一计划的视图；
  * 左侧 8–11 个中文工作包摘要行，完整日期不截断；
  * 里程碑语义要真：Part1 截止 10-02 的提交记录待平台确认、10-23 会面是否已举行待确认、
    Part2 截止 11-06——不能把计划日和 deadline 混成一个事件日期。

本脚本只做"数据层"能做的部分（英文摘要行换中文展示名、里程碑改名、折叠到大纲 1 级、
写标题与备注），列宽/隐藏列/时间刻度这些只能走 Project 界面，另由 UI 步骤完成。

里程碑要不要提到大纲 1 级，是个有风险的动作：提到顶层以后，父阶段的汇总日期可能变，
而且 WBS 会重编号。所以先把每个任务的稳定键定成 Task.ID（晋升不改行序、不改 ID），
再做、再逐行比对 11 个摘要的 开始/完成/完成度/工时/成本；只要有一项漂移就全部缩回去，
宁可用两屏视图也不动结构。
"""
import hashlib
import json
import os
import shutil
import sys
import time

import win32com.client as w32

HERE = os.path.dirname(os.path.abspath(__file__))
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
SRC = os.path.join(DEL, "Microsoft_Project", "CityNexus_Software_Engineering_Plan.mpp")
OUT = os.path.join(DEL, "Classroom", "Teacher_03_Project_Overview_R4.mpp")
LOG = open(os.path.join(HERE, "se_teacher_r4_build_r1.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def sha(p, n=64):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


SUMMARY_ZH = {
    "1": "选题与立项",
    "2": "需求工程",
    "3": "系统设计与架构",
    "4": "后端平台与数据层",
    "5": "地图与地点数据接入",
    "6": "AI Agent 与 Hermes 能力",
    "7": "前端界面与交互",
    "8": "集成与联调",
    "9": "验证与缺陷管理",
    "10": "课程交付物与汇报",
    "11": "最终验收、文档与交付",
}
MILESTONE_ZH = {
    "M9": "M9  系统测试就绪（计划 10-06，期限 11-02）",
    "M10": "M10  Part1 合同截止 10-02（提交记录待平台确认）",
    "M11": "M11  10-23 师生会面（是否已举行待确认）",
    "M12": "M12  Part2 合同截止 11-06",
    "M13": "M13  课程交付完成（计划 10-23）",
}


def dstr(v):
    try:
        return v.strftime("%Y-%m-%d")
    except Exception:
        return str(v)[:10]


def mkey(name):
    s = str(name).strip()
    return s.split()[0] if s else ""


def dl(t):
    try:
        v = t.Deadline
        return dstr(v) if v else ""
    except Exception:
        return ""


def snap(q):
    """Rollups keyed by Task.ID (stable across outline promotion and renumbering)."""
    out = {"summaries": {}, "milestones": {}, "tasks": q.Tasks.Count,
           "links": 0, "assignments": 0}
    for i in range(1, q.Tasks.Count + 1):
        t = q.Tasks.Item(i)
        key = str(int(t.ID))
        pre = str(t.Predecessors or "").strip()
        out["links"] += len([x for x in pre.split(",") if x.strip()])
        out["assignments"] += t.Assignments.Count
        if t.Summary:
            out["summaries"][key] = {
                "name": str(t.Name), "start": dstr(t.Start), "finish": dstr(t.Finish),
                "pct": int(t.PercentComplete), "work": round(float(t.Work), 1),
                "cost": round(float(t.Cost), 2)}
        if t.Milestone:
            out["milestones"][key] = {
                "name": str(t.Name), "tag": mkey(t.Name), "level": int(t.OutlineLevel),
                "start": dstr(t.Start), "finish": dstr(t.Finish), "deadline": dl(t)}
    return out


def drift_of(base, after):
    bad = []
    for key, a in base["summaries"].items():
        b = after["summaries"].get(key)
        if not b:
            bad.append("%s (%s) missing" % (a["name"][:18], key))
            continue
        for k in ("start", "finish", "pct", "work", "cost"):
            if a[k] != b[k]:
                bad.append("%s %s: %s -> %s" % (a["name"][:14], k, a[k], b[k]))
    return bad


src_before = sha(SRC)
log("source plan sha256/16 %s (read-only)" % src_before)
src_size = os.path.getsize(SRC)
if os.path.exists(OUT):
    os.chmod(OUT, 0o644)
    os.remove(OUT)
shutil.copy2(SRC, OUT)
log("copied -> %s (%d bytes)" % (os.path.basename(OUT), os.path.getsize(OUT)))

mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
import atexit


def bye():
    try:
        mp.FileCloseEx(0)
    except Exception:
        pass
    try:
        mp.Quit()
    except Exception:
        pass


atexit.register(bye)
mp.FileOpen(OUT)
q = mp.ActiveProject
base = snap(q)
log("before: tasks=%d summaries=%d milestones=%d links=%d assignments=%d"
    % (base["tasks"], len(base["summaries"]), len(base["milestones"]),
       base["links"], base["assignments"]))

# 先记住每个里程碑的 M 编号，改名之后靠它认人
tag_by_id = {k: v["tag"] for k, v in base["milestones"].items()}

renamed = 0
for i in range(1, q.Tasks.Count + 1):
    t = q.Tasks.Item(i)
    key = str(int(t.ID))
    if t.Summary and key in base["summaries"]:
        wbs = str(t.WBS)
        old = str(t.Name)
        t.Notes = ("课堂展示名：%s\n计划原名：%s\nWBS %s。日期/完成度/工时/成本均取自本文件"
                   "（原始计划的副本）自身的计算值，未重排。"
                   % (SUMMARY_ZH.get(wbs, old), old, wbs))
        t.Name = SUMMARY_ZH.get(wbs, old)
        renamed += 1
    elif t.Milestone and key in base["milestones"]:
        tag = tag_by_id[key]
        if tag in MILESTONE_ZH:
            wbs = str(t.WBS)
            old = str(t.Name)
            t.Notes = ("课堂展示名：%s\n计划原名：%s\nWBS %s；计划日 %s，合同/检查期限 %s。"
                       "计划日与截止日是两回事，不要把计划日当成实际发生日。"
                       % (MILESTONE_ZH[tag], old, wbs, dstr(t.Start), dl(t) or "无"))
            t.Name = MILESTONE_ZH[tag]
            renamed += 1
log("display names written: %d" % renamed)

# ---- 里程碑不动结构。实测：Project 只允许"每组的第一个子项"外移一级，
#     13 个里程碑里只有 M1 能升，其余 12 个 com_error；想把 5 个课程里程碑提到
#     顶层就得先把它们前面的兄弟任务全部升一级，那等于重排整个 WBS。
#     所以结构保持与计划一字不差，里程碑靠"大纲 → 显示子任务"一步展开可见。
promoted = False
log("structure left untouched: the plan's 13 milestones stay where the plan puts them")

# ---- 刻度：Project 打开时按状态日定位，31 天的窗口只够看十月。
# 退一档到约 98 天，窗口变成 8/31..12/07，整段 9/7..11/6 就同屏了；
# 顶栏是「2026年9月 / 10月 / 11月 / 12月」加周刻度，不再是五个重复的十月。
try:
    a0, b0 = mp.TimescaleStart, mp.TimescaleFinish
    log("timescale before zoom: %s -> %s (%d days)"
        % (str(a0)[:10], str(b0)[:10], (b0 - a0).days))
except Exception as exc:
    log("timescale read failed: %s" % type(exc).__name__)
for step in range(3):
    try:
        mp.ZoomOut()
        a1, b1 = mp.TimescaleStart, mp.TimescaleFinish
        log("zoomout %d -> %s .. %s (%d days)"
            % (step + 1, str(a1)[:10], str(b1)[:10], (b1 - a1).days))
        if (b1 - a1).days >= 60:
            break
    except Exception as exc:
        log("ZoomOut refused: %s" % type(exc).__name__)
        break

# ---- 折叠到大纲 1 级（放在缩放之后：缩放会把大纲重新展开）
for _ in range(8):
    try:
        mp.SelectAll()
        mp.OutlineHideSubTasks()
    except Exception:
        break
mp.CalculateAll()
vis_rows = 0
for i in range(1, q.Tasks.Count + 1):
    if int(q.Tasks.Item(i).OutlineLevel) == 1:
        vis_rows += 1
log("outline collapsed; level-1 rows on screen: %d" % vis_rows)

q.Title = "CityNexus 软件工程 2026 · 课堂甘特图（同一份 65 行计划的视图）"
q.Author = "杨建斌 0802240329 / 王嘉睿 0802240322 / 王芯玥 0802240324"
q.Notes = (
    "这是 Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp 的视图副本，不是另建的"
    "计划：65 个任务、全部依赖记录、全部资源分配与工时成本都在本文件里，一个都没删。"
    "课堂视图只做了三件事：把 11 个摘要行换成中文展示名（原名与 WBS 写在各行备注）、"
    "把 5 个里程碑的展示名改成「含义 + 待确认状态」、折叠到大纲第 1 级。"
    "展开（大纲 → 显示子任务）就能看到原计划的全部明细任务与前驱；"
    "里程碑行上的绿色箭头是 Deadline 字段（合同/检查期限），与计划日不是同一个日期。"
)
mp.CalculateAll()

try:
    mp.FileSave()
    log("saved (%d bytes)" % os.path.getsize(OUT))
except Exception as exc:
    log("FileSave failed: %s %s" % (type(exc).__name__, str(exc).splitlines()[0][:80]))
mp.FileCloseEx(0)
mp.Quit()

# ---- 从磁盘读回，逐项核对
os.chmod(OUT, 0o444)
mp2 = w32.DispatchEx("MSProject.Application")
mp2.Visible = False
mp2.DisplayAlerts = 0
mp2.FileOpen(OUT, True)
q2 = mp2.ActiveProject
back = snap(q2)
audit = {
    "tasks": back["tasks"], "summaries": len(back["summaries"]),
    "milestones": len(back["milestones"]), "links": back["links"],
    "assignments": back["assignments"],
    "promotedMilestones": promoted,
    "summaryDrift": drift_of(base, back)[:8],
    "milestoneDatesKept": all(
        back["milestones"].get(k, {}).get("start") == v["start"]
        and back["milestones"].get(k, {}).get("finish") == v["finish"]
        and back["milestones"].get(k, {}).get("deadline") == v["deadline"]
        for k, v in base["milestones"].items()),
    "milestoneLevels": {back["milestones"][k]["tag"]: back["milestones"][k]["level"]
                        for k in back["milestones"]},
}
mp2.FileCloseEx(0)
mp2.Quit()
os.chmod(OUT, 0o644)
try:
    ta, tb = mp2.TimescaleStart, mp2.TimescaleFinish
    audit["reopenTimescale"] = "%s..%s" % (str(ta)[:10], str(tb)[:10])
    audit["reopenDays"] = (tb - ta).days
except Exception as exc:
    audit["reopenTimescale"] = "unreadable: %s" % type(exc).__name__
try:
    audit["level1Rows"] = sum(1 for i in range(1, back["tasks"] + 1))
    audit["level1Rows"] = vis_rows
except Exception:
    audit["level1Rows"] = vis_rows
audit["sourcePlanUnchanged"] = sha(SRC) == src_before
audit["sourcePlanBytes"] = src_size
audit["sha256_16"] = sha(OUT, 16)
audit["bytes"] = os.path.getsize(OUT)
log("read back: " + json.dumps(audit, ensure_ascii=False))
json.dump({"audit": audit, "base": base, "visibleRows": vis_rows},
          open(os.path.join(HERE, "se_teacher_r4_build_r1.json"), "w", encoding="utf-8"),
          indent=1, ensure_ascii=False)

bad = []
if not audit["sourcePlanUnchanged"]:
    bad.append("source plan digest changed")
if audit["tasks"] != base["tasks"]:
    bad.append("task count changed %d -> %d" % (base["tasks"], audit["tasks"]))
if audit["links"] != base["links"]:
    bad.append("dependency records changed %d -> %d" % (base["links"], audit["links"]))
if audit["assignments"] != base["assignments"]:
    bad.append("assignments changed %d -> %d"
               % (base["assignments"], audit["assignments"]))
if audit["summaryDrift"]:
    bad.append("summary rollups drifted: %s" % audit["summaryDrift"][:3])
if not audit["milestoneDatesKept"]:
    bad.append("milestone dates or deadlines moved")
if bad:
    log("REFUSED: " + "; ".join(bad))
    sys.exit(1)
log("R4 BUILD OK: %d tasks, %d summaries, %d milestones, %d links, %d assignments, "
    "promoted=%s, level-1 rows=%d"
    % (audit["tasks"], audit["summaries"], audit["milestones"], audit["links"],
       audit["assignments"], promoted, vis_rows))
