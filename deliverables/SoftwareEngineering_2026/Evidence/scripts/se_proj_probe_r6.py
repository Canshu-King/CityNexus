"""Probe 6 - why the shipped plan has Work = 0 and PercentComplete = 0.

Measures the project-level hour settings, then tries every write path for work
hours and progress and reads each one back. Nothing is saved.
"""
import datetime
import os
import time

import win32com.client as w32

LOG = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "se_proj_probe_r6.log"), "w", encoding="utf-8", buffering=1)
T0 = time.time()
D = datetime.datetime
PJ_WORK = 188743680
PJ_PCT = 188743712
PJ_PCTWORK = 188743713
PJ_ACTWORK = 188743682


def p(m):
    LOG.write("[%5.1fs] %s\n" % (time.time() - T0, m))
    LOG.flush()
    print(m, flush=True)


def show(label, fn):
    try:
        p("%-38s %r" % (label, fn()))
    except Exception as exc:
        p("%-38s ERROR %s: %s" % (label, type(exc).__name__, str(exc)[:130]))


mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
show("mp.DisplayAlerts =", lambda: setattr(mp, "DisplayAlerts", 0))
mp.FileNew()
prj = mp.ActiveProject
prj.ProjectStart = D(2026, 9, 7)

p("=== project level calendar settings")
for prop in ("HoursPerDay", "HoursPerWeek", "DaysPerMonth"):
    show("prj.%s" % prop, lambda prj=prj, prop=prop: getattr(prj, prop))

res = prj.Resources.Add("Worker")
res.Type = 1
res.StandardRate = 40.0
show("res.MaxUnits", lambda: res.MaxUnits)
show("res.StandardRate", lambda: res.StandardRate)
show("res.CostPerUse", lambda: res.CostPerUse)
show("res.AccrueAt", lambda: res.AccrueAt)

p("=== A: duration only, then assign")
A = prj.Tasks.Add("A 2d")
A.SetField(1280, 0)
A.Duration = "2d"
mp.CalculateAll()
show("A Work after duration", lambda: A.Work)
show("A Duration", lambda: A.Duration)
show("A DurationText", lambda: A.DurationText)
A.Assignments.Add(A.ID, res.ID, 1.0)
mp.CalculateAll()
show("A Work after assign", lambda: A.Work)
show("A Cost after assign", lambda: A.Cost)
show("assignment Units", lambda: A.Assignments.Item(1).Units)
show("assignment Work", lambda: A.Assignments.Item(1).Work)
show("assignment Cost", lambda: A.Assignments.Item(1).Cost)

p("=== B: set Work explicitly, then assign")
B = prj.Tasks.Add("B work 16h")
B.SetField(1280, 0)
B.Duration = "2d"
try:
    B.Work = "16h"
except Exception as exc:
    p("B.Work='16h' refused: %s" % type(exc).__name__)
mp.CalculateAll()
show("B Work", lambda: B.Work)
show("B GetField(pjTaskWork)", lambda: B.GetField(PJ_WORK))
B.Assignments.Add(B.ID, res.ID, 1.0)
mp.CalculateAll()
show("B Work after assign", lambda: B.Work)
show("B Cost", lambda: B.Cost)
show("B Duration after assign", lambda: B.DurationText)

p("=== C: progress write paths (100%)")
C = prj.Tasks.Add("C pct paths")
C.SetField(1280, 0)
C.Duration = "1d"
C.Work = "8h"
C.Assignments.Add(C.ID, res.ID, 1.0)
mp.CalculateAll()
show("C before: Work/Cost", lambda: (C.Work, C.Cost))
C.PercentComplete = 100
mp.CalculateAll()
show("C after PercentComplete=100", lambda: C.PercentComplete)
show("C PercentWorkComplete", lambda: C.PercentWorkComplete)
show("C ActualWork", lambda: C.ActualWork)
show("C ActualStart", lambda: str(C.ActualStart))
show("C ActualFinish", lambda: str(C.ActualFinish))
show("C RemainingWork", lambda: C.RemainingWork)
show("C Cost / ActualCost", lambda: (C.Cost, C.ActualCost))
D2 = prj.Tasks.Add("D SetField pct")
D2.SetField(1280, 0)
D2.Duration = "1d"
D2.Work = "8h"
D2.Assignments.Add(D2.ID, res.ID, 1.0)
mp.CalculateAll()
try:
    D2.SetField(PJ_PCT, 100)
    p("D2 SetField(pjTaskPercentComplete,100) accepted")
except Exception as exc:
    p("D2 SetField pct refused: %s" % type(exc).__name__)
mp.CalculateAll()
show("D2 PercentComplete", lambda: D2.PercentComplete)
show("D2 PercentWorkComplete", lambda: D2.PercentWorkComplete)
show("D2 ActualWork", lambda: D2.ActualWork)
show("D2 ActualStart/Finish", lambda: (str(D2.ActualStart), str(D2.ActualFinish)))
show("D2 RemainingWork", lambda: D2.RemainingWork)
show("D2 Cost/ActualCost", lambda: (D2.Cost, D2.ActualCost))
E = prj.Tasks.Add("E pctWork path")
E.SetField(1280, 0)
E.Duration = "2d"
E.Work = "16h"
E.Assignments.Add(E.ID, res.ID, 1.0)
mp.CalculateAll()
try:
    E.PercentWorkComplete = 50
    p("E PercentWorkComplete=50 accepted")
except Exception as exc:
    p("E PercentWorkComplete refused: %s" % type(exc).__name__)
mp.CalculateAll()
show("E PercentComplete", lambda: E.PercentComplete)
show("E PercentWorkComplete", lambda: E.PercentWorkComplete)
show("E ActualWork/Remaining", lambda: (E.ActualWork, E.RemainingWork))
show("E ActualStart/Finish", lambda: (str(E.ActualStart), str(E.ActualFinish)))
show("E Cost/ActualCost", lambda: (E.Cost, E.ActualCost))
show("E Start/Finish", lambda: (str(E.Start)[:16], str(E.Finish)[:16]))

p("=== status date effect")
show("prj.StatusDate (unset)", lambda: str(prj.StatusDate))
try:
    prj.StatusDate = D(2026, 9, 8)
    p("StatusDate set to 2026-09-08")
except Exception as exc:
    p("StatusDate refused: %s" % type(exc).__name__)
mp.CalculateAll()
show("E Start/Finish after status date", lambda: (str(E.Start)[:16], str(E.Finish)[:16]))
show("E ActualFinish after status date", lambda: str(E.ActualFinish))
show("C Start/Finish after status date", lambda: (str(C.Start)[:16], str(C.Finish)[:16]))

p("=== summary rollup check")
show("prj.Work (total)", lambda: prj.Work)
show("prj.Cost (total)", lambda: prj.Cost)
show("prj.GetField(pjTaskWork) row1", lambda: prj.Tasks.Item(1).GetField(PJ_WORK))

try:
    prj.Saved = True
    p("prj.Saved = True accepted")
except Exception as exc:
    p("prj.Saved refused: %s: %s" % (type(exc).__name__, str(exc)[:120]))
mp.FileClose()
mp.Quit()
p("probe done (closed without saving; Saved flag forced)")
LOG.close()
