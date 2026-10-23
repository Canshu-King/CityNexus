"""Probe the Project object model for the pieces the dependency rework needs.

Nothing is written to the plan: the file is opened read-only in the sense that
the session ends with FileClose without Save. Every answer is printed so the new
builder can be written against measured behaviour instead of guesses.
"""
import os
import sys
import time

import win32com.client as w32

MPP = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project\CityNexus_Software_Engineering_Plan.mpp"
LOG = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "se_proj_probe_r4.log"), "w", encoding="utf-8", buffering=1)
T0 = time.time()


def p(m):
    LOG.write("[%6.1fs] %s\n" % (time.time() - T0, m))
    LOG.flush()
    print(m, flush=True)


def show(label, fn):
    try:
        p("%-34s %r" % (label, fn()))
    except Exception as exc:
        p("%-34s ERROR %s: %s" % (label, type(exc).__name__, str(exc)[:140]))


mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
mp.FileOpen(MPP, ReadOnly=True)
prj = mp.ActiveProject
p("project %s  rows=%d  start=%s  finish=%s  statusDate=%s"
  % (prj.Name, prj.Tasks.Count, prj.ProjectStart, prj.ProjectFinish, prj.StatusDate))

# --- 1. task level fields we plan to use ------------------------------------
picked = []
for i in range(1, prj.Tasks.Count + 1):
    t = prj.Tasks.Item(i)
    if not t.Summary:
        picked.append(t)
    if len(picked) == 3:
        break
for t in picked:
    p("--- task %d %s" % (t.ID, t.Name[:44]))
    show("  PercentComplete", lambda t=t: t.PercentComplete)
    show("  ActualStart", lambda t=t: t.ActualStart)
    show("  ActualFinish", lambda t=t: t.ActualFinish)
    show("  ActualWork", lambda t=t: t.ActualWork)
    show("  RemainingWork", lambda t=t: t.RemainingWork)
    show("  Work", lambda t=t: t.Work)
    show("  Cost", lambda t=t: t.Cost)
    show("  Deadline", lambda t=t: t.Deadline)
    show("  ConstraintType", lambda t=t: t.ConstraintType)
    show("  Milestone", lambda t=t: t.Milestone)
    show("  Critical", lambda t=t: t.Critical)
    show("  TotalSlack", lambda t=t: t.TotalSlack)
    show("  Start/Finish", lambda t=t: (str(t.Start), str(t.Finish)))
    show("  TaskDependencies.Count", lambda t=t: t.TaskDependencies.Count)
    show("  dep[0] From/To/Type/Lag", lambda t=t: (
        t.TaskDependencies.Item(1).From.Name[:20],
        t.TaskDependencies.Item(1).To.Name[:20],
        t.TaskDependencies.Item(1).Type,
        t.TaskDependencies.Item(1).Lag))

# --- 2. field tables ---------------------------------------------------------
p("=== field / custom column probes")
show("FieldIndices('Text1')", lambda: prj.FieldIndices("Text1"))
show("FieldIndices('Text 1')", lambda: prj.FieldIndices("Text 1"))
show("FieldDefinitions.Count", lambda: prj.FieldDefinitions.Count)


def add_fielddef():
    fd = prj.FieldDefinitions.Add(prj.FieldIndices("Text1"), 1)   # 1 = pfTaskField
    try:
        fd.Alias = "Observed date (evidence)"
    except Exception as exc:
        p("   alias refused: %s" % type(exc).__name__)
    return (fd.ID, getattr(fd, "Alias", None), fd.Name)


show("FieldDefinitions.Add(Text1)", add_fielddef)

# --- 3. how Project stores a link type constant -----------------------------
show("constants pfFinishToStart", lambda: w32.constants.pfFinishToStart)
show("constants pfStartToStart", lambda: w32.constants.pfStartToStart)
show("constants pfFinishToFinish", lambda: w32.constants.pfFinishToFinish)
show("constants pfStartToFinish", lambda: w32.constants.pfStartToFinish)
show("constraint asSoonAsPossible", lambda: w32.constants.asSoonAsPossible)
show("prjDeadlineDisplay?", lambda: prj.DeadelinesPresent)

# --- 4. baseline / calendar facts -------------------------------------------
show("Baselines saved (BaselineStart of row1)", lambda: str(picked[0].BaselineStart))
show("Calendar.Standard.WorkWeeks?", lambda: prj.Calendar.Name)
show("MinutesPerDay", lambda: prj.MinutePerDay)
show("HoursPerDay?", lambda: getattr(prj, "DayHour", None))
show("WeekStartDay", lambda: prj.WeekStartDay)
show("DefaultStandardRate display", lambda: prj.DefaultStandardRate)

mp.FileClose()
mp.Quit()
p("probe done (file not saved)")
LOG.close()
