"""Measure, do not guess: what Microsoft Project actually stores for link types,
percent complete, work/cost and deadlines.

Builds a throwaway project in memory, reads every answer back out of the object
model, and closes WITHOUT saving. The numbers printed here are what the new
builder and its link audit are written against.
"""
import datetime
import os
import time

import win32com.client as w32

LOG = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "se_proj_probe_r5.log"), "w", encoding="utf-8", buffering=1)
T0 = time.time()
D = datetime.datetime


def p(m):
    LOG.write("[%6.1fs] %s\n" % (time.time() - T0, m))
    LOG.flush()
    print(m, flush=True)


def show(label, fn):
    try:
        p("%-40s %r" % (label, fn()))
    except Exception as exc:
        p("%-40s ERROR %s: %s" % (label, type(exc).__name__, str(exc)[:150]))


mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
mp.FileNew()
prj = mp.ActiveProject
prj.ProjectStart = D(2026, 9, 7)          # a Monday
p("new project %s start=%s finish=%s status=%s" % (prj.Name, prj.ProjectStart,
                                                   prj.ProjectFinish, prj.StatusDate))

res = prj.Resources.Add("Probe Worker")
res.Type = 1
res.StandardRate = 40.0
p("resource id=%s std=%s readback=%s" % (res.ID, res.StandardRate, res.StandardRate))


def new(name, dur, preds=None, pct=None, deadline=None, assign=False):
    t = prj.Tasks.Add(name)
    t.SetField(1280, 0)                    # auto scheduled
    t.Duration = dur
    if preds:
        t.Predecessors = preds
    if deadline:
        t.Deadline = D.strptime(deadline, "%Y-%m-%d")
    if pct is not None:
        t.PercentComplete = pct
    if assign:
        t.Assignments.Add(t.ID, res.ID, 1.0)
    return t


A = new("A base 2d", "2d", assign=True)
B = new("B after A (FS)", "2d", "%dFS" % A.ID)
C = new("C with A (SS)", "2d", "%dSS" % A.ID)
E = new("E ends with A (FF)", "2d", "%dFF" % A.ID)
F = new("F starts when A starts (SF)", "2d", "%dSF" % A.ID)
mp.CalculateAll()

p("=== dates")
for t in (A, B, C, E, F):
    p("  %-26s start=%s finish=%s preds=%r" % (t.Name, str(t.Start)[:16],
                                               str(t.Finish)[:16], str(t.Predecessors)))

p("=== TaskDependency.Type as written by the Predecessors text form")
for t in (A, B, C, E, F):
    deps = []
    for k in range(1, t.TaskDependencies.Count + 1):
        d = t.TaskDependencies.Item(k)
        deps.append({"from": d.From.Name.split()[0], "to": d.To.Name.split()[0],
                     "type": d.Type, "lag": d.Lag, "lagType": d.LagType})
    p("  %-26s count=%d %s" % (t.Name, t.TaskDependencies.Count, deps))

p("=== PredecessorTasks / Successors (names only, to see direction)")
show("B.PredecessorTasks", lambda: [t.Name.split()[0] for t in B.PredecessorTasks])
show("A.Successors", lambda: [t.Name.split()[0] for t in A.Successors])
show("A.PredecessorTasks", lambda: [t.Name.split()[0] for t in A.PredecessorTasks])

p("=== percent complete / actuals / work / cost")
G = new("G complete 1d 100pct", "1d", pct=100, assign=True)
H = new("H half 2d 50pct", "2d", pct=50, assign=True)
mp.CalculateAll()
for t in (G, H):
    p("  %s" % t.Name)
    show("    PercentComplete", lambda t=t: t.PercentComplete)
    show("    Work (hours?)", lambda t=t: t.Work)
    show("    ActualWork", lambda t=t: t.ActualWork)
    show("    RemainingWork", lambda t=t: t.RemainingWork)
    show("    Cost", lambda t=t: t.Cost)
    show("    ActualCost", lambda t=t: t.ActualCost)
    show("    ActualStart", lambda t=t: str(t.ActualStart))
    show("    ActualFinish", lambda t=t: str(t.ActualFinish))
    show("    Start/Finish", lambda t=t: (str(t.Start)[:16], str(t.Finish)[:16]))
    show("    ConstraintType", lambda t=t: t.ConstraintType)

p("=== status date behaviour: work not yet done after the status date")
show("project statusDate", lambda: str(prj.StatusDate))
show("project finish", lambda: str(prj.ProjectFinish))

p("=== milestone + deadline + link")
M = new("M milestone 0d", "0d", "%dFS" % B.ID)
M.Deadline = D(2026, 9, 30)
mp.CalculateAll()
show("Milestone flag", lambda: M.Milestone)
show("M start/finish", lambda: (str(M.Start)[:16], str(M.Finish)[:16]))
show("M duration", lambda: M.Duration)
show("M Deadline", lambda: str(M.Deadline))
show("M ConstraintType", lambda: M.ConstraintType)
show("M deps", lambda: [(d.From.Name.split()[0], d.To.Name.split()[0], d.Type)
                        for k in range(1, M.TaskDependencies.Count + 1)
                        for d in [M.TaskDependencies.Item(k)]])

p("=== what a forced Start does to the constraint (the defect being fixed)")
X = new("X forced start", "3d")
try:
    X.Start = D(2026, 10, 5)
    mp.CalculateAll()
    show("X ConstraintType after t.Start=", lambda: X.ConstraintType)
    show("X ConstraintDate", lambda: str(X.ConstraintDate))
    show("X start/finish", lambda: (str(X.Start)[:16], str(X.Finish)[:16]))
except Exception as exc:
    p("X.Start refused: %s: %s" % (type(exc).__name__, str(exc)[:120]))
Y = new("Y as late as possible? n/a", "1d", "%dFF" % X.ID)
mp.CalculateAll()
show("Y start/finish", lambda: (str(Y.Start)[:16], str(Y.Finish)[:16]))

p("=== critical path + slack fields")
show("A.Critical", lambda: A.Critical)
show("B.TotalSlack", lambda: B.TotalSlack)
show("prj.CriticalPathSlackLimit?", lambda: getattr(prj, "CriticalPathSlack", None))
show("rows critical", lambda: [prj.Tasks.Item(i).Name.split()[0]
                               for i in range(1, prj.Tasks.Count + 1)
                               if not prj.Tasks.Item(i).Summary
                               and prj.Tasks.Item(i).Critical])

mp.FileClose()
mp.Quit()
p("probe finished (nothing saved)")
LOG.close()
