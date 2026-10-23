"""A real teacher-readable Project overview: 11 phase rows, bars on screen.

The complaint is fair and it is about the *view*, not the data: 65 rows all
expanded, the resource column printing "王… 0802240322 - data integration / backend
scopes / testing[13%]" across the table into the chart, and the timescale parked on a
fortnight the work had already left.

This builds `Teacher_03_Project_Overview.mpp` from the audited plan with data-only
reads:

  * rows: the 11 top-level phases, with the dates, percentage, work and cost that the
    engine computed for that phase - read out of the plan, never retyped;
  * milestones: the 5 dated course/statutory milestones (M9..M13), so the contract
    dates 2026-10-02 / 10-23 / 11-02 / 11-06 sit on the same screen as the bars;
  * no dependency arrows: measured on the plan of record, not one of the 11 phase
    rows carries a predecessor, so a phase network could only be invented - and an
    invented FS arrow between phases that really overlap (2..8 all start on or
    before 2026-09-16) moves a bar off its planned date. Every row here is pinned
    to the plan's own start + duration, all 16 rows are compared against the plan
    on read-back, and the network - with the critical path that falls out of it -
    stays in CityNexus_Software_Engineering_Plan.mpp;
  * the resource column is simply not used here: no assignments means nothing can
    spill across the chart, and the plan of record keeps every assignment.

Nothing in `Microsoft_Project/` is opened for writing; the digests are compared
before and after.
"""
import hashlib
import json
import os
import re
import sys
import time
import win32com.client as w32

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import se_project_plan_r2 as PM                                   # noqa: E402
from se_timeutil_r1 import dstr                                   # noqa: E402

DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
MSP = os.path.join(DEL, "Microsoft_Project")
CLS = os.path.join(DEL, "Classroom")
PLAN_MPP = os.path.join(MSP, "CityNexus_Software_Engineering_Plan.mpp")
OUT_MPP = os.path.join(CLS, "Teacher_03_Project_Overview.mpp")
LOG = open(os.path.join(HERE, "se_teacher_project_r1.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()
HOURS_PER_DAY = 8.0


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def sha(p, n=64):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


def dd(text):
    """A date, optionally with a working-hour time.

    A bare date parses to 00:00, which is outside the working day, and Project
    then clamps the row back to the previous working minute: every date in the
    file reads one day early. The plan of record learned this already
    (se_project_build_r2.py:67), so callers pass 09:00 / 16:00 explicitly.
    """
    import datetime
    s = str(text)
    if " " in s[:17]:
        return datetime.datetime.strptime(s[:16], "%Y-%m-%d %H:%M")
    return datetime.datetime.strptime(s[:10], "%Y-%m-%d")


def mnum(name):
    """The M-number a milestone row is called, or '' for an ordinary task."""
    m = re.match(r"^\s*(M\d+)\b", str(name))
    return m.group(1) if m else ""


plan_before = sha(PLAN_MPP)
log("plan of record sha256/16 %s (read-only source, must not change)" % plan_before)

# 屏幕上的名字。原来的行名是英文，在 130 px 宽的任务名列里折成四五行，
# 十行就占满整屏，甘特条被挤到看不见——用户点名的"密密麻麻"就是这个。
# 中文名只是同一行的展示名：日期、工期、完成度、工时、成本全部照抄原行，
# 英文原名与 WBS 一起写进该行备注，逐行核对时仍能一一对上。
NAME_ZH = {
    "1": "选题与开题",
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
    "9.7": "M9  系统测试就绪（计划目标）",
    "10.5": "M10  Part 1 截止 10-02（已错过）",
    "10.6": "M11  中期师生检查 10-23 中午",
    "10.7": "M12  Part 2 截止 11-06",
    "11.3": "M13  课程交付完成（计划）",
}


def zh(wbs, r):
    return NAME_ZH.get(str(wbs)) or r["name"]

prj = json.load(open(os.path.join(HERE, "se_project_build_r2_result.json"),
                     encoding="utf-8"))
rows = dict((r["wbs"], r) for r in prj["rows"])
# Measured on the plan of record: not one of the 11 summary rows carries a
# predecessor - the dependencies live between the leaf tasks, not between the
# phases. So there is no phase network to copy, and inventing one would move
# the bars: a folded FS arrow between phases that really run in parallel (2,
# 3, 4, 5, 6, 7 and 8 all start on or before 2026-09-16) pushes the successor
# past its planned date, and the dates are the one thing this sheet must not
# get wrong. The arrows stay where they are true: in the plan of record.
phase_pred = {w: str(r.get("predecessors") or "").strip()
              for w, r in rows.items() if r.get("summary")}
log("phase rows carrying predecessors in the plan of record: %d of %d -> "
    "no phase network exists to copy"
    % (sum(1 for v in phase_pred.values() if v), len(phase_pred)))

phases = [(w, r) for w, r in rows.items() if r.get("summary")]
phases.sort(key=lambda t: [int(x) for x in t[0].split(".")])
milestones = [(w, r) for w, r in rows.items()
              if r.get("milestone") and r.get("deadline")]
milestones.sort(key=lambda t: str(t[1]["finish"]))
log("rows for the classroom file: %d phases + %d dated milestones (%s)"
    % (len(phases), len(milestones),
       " ".join("%s@%s" % (mnum(r["name"]), r["deadline"])
                for _w, r in milestones)))

if os.path.exists(OUT_MPP):
    os.remove(OUT_MPP)
mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
import atexit


def _bye():
    try:
        mp.FileCloseEx(0)
    except Exception:
        pass
    try:
        mp.Quit()
    except Exception:
        pass


atexit.register(_bye)
# FileNew() takes no argument here. Measured: FileNew(1) makes Project open a
# blank project and raise its modal "Project Information" dialog, which blocks
# every later COM call - the run sat at a flat CPU until the process was killed.
mp.FileNew()
p = mp.ActiveProject
# ProjectStart / StatusDate are set on the Project object: measured, the same
# names on the Application raise "Property ... can not be set" (and a refusal
# here is fatal, because a sheet that starts today would show no September bar).
for prop, val in (("ProjectStart",
                   dd(min(str(row["start"]) for _w, row in phases) + " 09:00")),
                  ("StatusDate",
                   dd(str(prj.get("status_date") or "2026-10-22")[:10] + " 17:00"))):
    try:
        setattr(p, prop, val)
        log("%s = %s" % (prop, dstr(getattr(p, prop))))
    except Exception as exc:
        log("PROJECT SETTING %s REFUSED: %s %s" % (
            prop, type(exc).__name__, str(exc).splitlines()[0][:80]))
        _bye()
        sys.exit(1)
try:
    p.CurrencySymbol = "$"
except Exception:
    pass
p.Title = "CityNexus 软件工程 2026 · 课堂演示计划总览"
p.Author = "杨建斌 0802240329 / 王嘉睿 0802240322 / 王芯玥 0802240324"
p.Notes = ("课堂演示用文件。11 个阶段行 + 5 个带截止日期的里程碑，每一行的日期、完成度、"
           "工时与成本都取自 CityNexus_Software_Engineering_Plan.mpp 中同一行的引擎计算值"
           "（se_project_build_r2_result.json），没有重新排程。原计划 65 行的依赖、资源分配"
           "与关键路径都在那个文件里；本文件不画依赖箭头，也不要在本文件里读关键路径。")

ids = {}
made = []
for wbs, r in phases:
    t = p.Tasks.Add(zh(wbs, r))
    try:
        t.SetField(1280, 0)
    except Exception:
        pass
    ids[wbs] = t.ID
    made.append((wbs, t, r))
for wbs, r in milestones:
    t = p.Tasks.Add(zh(wbs, r))
    try:
        t.SetField(1280, 0)
    except Exception:
        pass
    ids[wbs] = t.ID
    made.append((wbs, t, r))
mp.CalculateAll()

for wbs, t, r in made:
    # the plan's own duration text, so a milestone stays a 0-duration diamond
    # instead of being floored to a one-day bar
    t.Duration = r.get("durationText") or ("0d" if r.get("milestone") else "1d")
    # Start is written, Finish is NOT: writing both measures as two constraints
    # that fight each other. With the plan's duration the finish falls out of
    # start+duration, and the audit below compares it against the plan row by
    # row instead of trusting it.
    t.Start = dd(r["start"] + " 09:00")
    t.PercentComplete = int(r["pct"])
    if r.get("deadline"):
        try:
            t.Deadline = dd(r["deadline"] + " 09:00")
        except Exception:
            pass
    t.Notes = ("课堂演示行（原计划 WBS %s，原名 %r）。数据来自已核对的 "
               "CityNexus_Software_Engineering_Plan.mpp 中同一行的引擎计算值："
               "开始 %s、完成 %s、完成度 %d%%、工时 %.1f h、成本 $%.2f。"
               "该阶段下每一笔任务、依赖与资源分配都在原计划里，本文件只是把它折成一行；"
               "本行日期是按原计划钉住的约束（不是重新排出来的），所以这里不画依赖箭头，"
               "也不要在本文件里读关键路径。"
               % (wbs, r["name"], r["start"], r["finish"], int(r["pct"]),
                  float(r.get("work") or 0.0), float(r.get("cost") or 0.0)))
mp.CalculateAll()

# view state that the object model does expose, and that matters on screen
try:
    mp.ViewApply("甘特图")
except Exception as exc:
    log("ViewApply: %s" % str(exc)[:60])
# The Entry table on this install carries 标识号/任务模式/任务名称/工期/开始/完成/
# 前置任务/资源名称 - four of those columns are empty here (no links, no
# assignments), and the empty columns are what push the chart pane off screen on
# the first screen and onto 12 printed pages. The Summary table is the built-in
# narrow one; if this install does not have that name it raises and the run says
# so instead of shipping a silently unchanged view.
for tname in ("摘要", "Summary", "Entry", "项"):
    try:
        mp.TableApply(tname)
        log("TableApply(%r) applied -> active table %r" % (
            tname, str(mp.ActiveWindow.Table)))
        break
    except Exception as exc:
        log("TableApply(%r) refused: %s %s"
            % (tname, type(exc).__name__, str(exc).splitlines()[0][:60]))
try:
    mp.ColumnBestFit()
    log("ColumnBestFit applied")
except Exception as exc:
    log("ColumnBestFit refused: %s" % type(exc).__name__)
try:
    mp.ActiveWindow.TopPane = 1
except Exception:
    pass
for _i in range(6):
    try:
        mp.OutlineHideSubTasks()
    except Exception:
        break
try:
    mp.TimelineViewToggle()
    mp.TimelineViewToggle()
    log("timeline pane toggled off twice (back to hidden)")
except Exception as exc:
    log("TimelineViewToggle: %s" % type(exc).__name__)
# 首屏最要命的不是滚动条，是刻度：日刻度下两个月的工期要 1600 px，
# 图表半屏只有 700 px，所以无论滚到哪儿都只能看见十几天。缩到周／月档位后
# 整段 2026-09-07..11-06 落在一屏里，滚动位置就不再重要。ZoomOut 在这台机器上
# 只改档位（不改百分比），所以按档位估次数，效果由照片判定。
for i in range(3):
    try:
        mp.ZoomOut()
        log("ZoomOut %d applied" % (i + 1))
    except Exception as exc:
        log("ZoomOut %d refused: %s %s"
            % (i + 1, type(exc).__name__, str(exc).splitlines()[0][:60]))
        break
try:
    mp.FileSaveAs(OUT_MPP)
    log("saved %s (%d bytes)" % (OUT_MPP, os.path.getsize(OUT_MPP)))
except Exception as exc:
    log("FileSaveAs failed: %s" % str(exc)[:120])

# ---- read it back and audit it, then reopen read-only for the photograph
mp.FileCloseEx(0)
mp.FileOpen(OUT_MPP)
q = mp.ActiveProject
rows_back = [q.Tasks.Item(i) for i in range(1, q.Tasks.Count + 1)]
# `Task.Deleted` is invisible to pywin32 late binding on this install (it raises
# AttributeError, same family as Shape.PinX), and this file is built from
# scratch in the same run, so nothing can be soft-deleted in it: take every row.
vis = list(rows_back)
# `Task.TaskDependencies` does not exist on this install, and zipping the saved
# rows against the in-memory list assumes the order survived; match by name and
# require exactly one row, so a duplicated or dropped row cannot pass as a
# matching date.
by_name = {}
for t in vis:
    by_name.setdefault(str(t.Name), []).append(t)
drift, links_back, constraints = [], 0, {}
for wbs, _t0, r in made:
    same = by_name.get(str(zh(wbs, r))) or []
    if len(same) != 1:
        drift.append("%s: %d rows carry this name in the saved file"
                     % (wbs, len(same)))
        continue
    t = same[0]
    if dstr(t.Start) != r["start"][:10] or dstr(t.Finish) != r["finish"][:10]:
        drift.append("%s: file %s->%s, plan %s->%s"
                     % (wbs, dstr(t.Start), dstr(t.Finish),
                        r["start"][:10], r["finish"][:10]))
    links_back += len([x for x in str(t.Predecessors or "").split(",")
                       if x.strip()])
    key = str(t.ConstraintType)
    constraints[key] = constraints.get(key, 0) + 1
crit = [t.WBS for t in vis if t.Critical]
aud = {
    "rows": len(vis),
    "phases": len(phases), "milestones": len(milestones),
    "linkRecords": links_back,
    "start": dstr(q.Start), "finish": dstr(q.Finish),
    "cost": round(float(q.Cost), 2), "work": round(float(q.Work) / 60.0, 1),
    "critical": len(crit),
    "datesAgree": not drift, "dateDrift": drift[:8],
    "constraintTypes": constraints,
    "noResourceAssignments": sum(t.Assignments.Count for t in vis) == 0,
}
# read back off the reopened file, not off what the script asked for: this is
# the only place the table/view claim can be proved
try:
    aud["table"] = str(mp.ActiveWindow.Table)
    aud["view"] = str(mp.ActiveWindow.View)
except Exception as exc:
    aud["table"] = "unreadable: %s" % type(exc).__name__
log("read back: %s" % json.dumps(aud, ensure_ascii=False))
try:
    mp.ViewApply("甘特图")
except Exception:
    pass
mp.FileCloseEx(0)
mp.Quit()

plan_after = sha(PLAN_MPP)
result = {"file": os.path.basename(OUT_MPP), "bytes": os.path.getsize(OUT_MPP),
          "sha256_16": sha(OUT_MPP, 16), "audit": aud,
          "sourcePlanSha256_16": plan_before, "planUnchanged": plan_after == plan_before}
json.dump(result, open(os.path.join(HERE, "se_teacher_project_result.json"), "w",
                       encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
log("plan of record unchanged: %s" % result["planUnchanged"])
bad = []
if not result["planUnchanged"]:
    bad.append("plan digest changed")
if aud["rows"] != len(phases) + len(milestones):
    bad.append("row count")
if not aud["datesAgree"]:
    bad.append("dates do not match the plan: %s" % " | ".join(aud["dateDrift"]))
if not aud["noResourceAssignments"]:
    bad.append("assignments leaked into the classroom file")
if bad:
    log("REFUSED: %s" % "; ".join(bad))
    LOG.close()
    sys.exit(1)
log("TEACHER PROJECT OK: %d rows, %d link records, finish %s"
    % (aud["rows"], aud["linkRecords"], aud["finish"]))
LOG.close()
sys.exit(0)
