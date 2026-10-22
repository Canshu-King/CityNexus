"""Probe 7 - the two write-order defects that reached the shipped .mpp.

R6 showed: adding an assignment leaves Task.Work at 0 and Cost at exactly one
hour of the rate, and setting PercentComplete BEFORE the assignment reads back 0
while setting it AFTER reads back 100. This measures the variants needed to get
honest work hours, cost and progress into the plan. Nothing is saved.
"""
import datetime
import os
import time

import win32com.client as w32

LOG = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "se_proj_probe_r7.log"), "w", encoding="utf-8", buffering=1)
T0 = time.time()
D = datetime.datetime
PJ_WORK = 188743680
PJ_COST = 188743685
PJ_PCT = 188743712
PJ_AWORK = 188743682


def p(m):
    LOG.write("[%5.1fs] %s\n" % (time.time() - T0, m))
    LOG.flush()
    print(m, flush=True)


def show(label, fn):
    try:
        p("%-44s %r" % (label, fn()))
    except Exception as exc:
        p("%-44s ERROR %s: %s" % (label, type(exc).__name__, str(exc)[:130]))


mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
mp.FileNew()
prj = mp.ActiveProject
prj.ProjectStart = D(2026, 9, 7)
try:
    prj.StatusDate = D(2026, 10, 22)
except Exception as exc:
    p("StatusDate refused: %s" % type(exc).__name__)
prj.CurrencySymbol = "$"

r_full = prj.Resources.Add("Full time member")
r_full.Type = 1
for form in (("float 1.0", 1.0), ("int 1", 1), ("str 100%", "100%"),
             ("str 1", "1")):
    try:
        r_full.MaxUnits = form[1]
        p("MaxUnits via %-10s accepted -> reads back %r" % (form[0], r_full.MaxUnits))
        break
    except Exception as exc:
        p("MaxUnits via %-10s refused: %s" % (form[0], type(exc).__name__))
r_full.StandardRate = 20.0
r_half = prj.Resources.Add("Part time member")
r_half.Type = 1
try:
    r_half.MaxUnits = r_full.MaxUnits if isinstance(r_full.MaxUnits, (int, float)) else 1.0
except Exception as exc:
    p("r_half MaxUnits refused: %s" % type(exc).__name__)
try:
    r_half.SetField(1213, 0.5)          # pjResourceMaxUnits? measured below
    p("r_half SetField(1213,0.5) accepted -> %r" % (r_half.MaxUnits,))
except Exception as exc:
    p("r_half SetField(1213) refused: %s" % type(exc).__name__)
r_half.StandardRate = 20.0
show("r_full MaxUnits/Std", lambda: (r_full.MaxUnits, str(r_full.StandardRate)))
show("r_half MaxUnits/Std", lambda: (r_half.MaxUnits, str(r_half.StandardRate)))
show("r_full.Peak / AvailableFrom", lambda: (str(getattr(r_full, "Peak", None)),
                                             str(getattr(r_full, "AvailableFrom", None))))


def task(name, dur):
    t = prj.Tasks.Add(name)
    t.SetField(1280, 0)
    t.Duration = dur
    return t


def read(tag, t):
    try:
        vals = (t.Work, t.GetField(PJ_WORK), t.Cost, t.GetField(PJ_COST),
                t.PercentComplete, t.ActualWork, t.RemainingWork)
    except Exception as exc:
        p("  %s: read ERROR %s: %s" % (tag, type(exc).__name__, str(exc)[:120]))
        return
    p("  %s: Work=%s GetField Work=%r Cost=%.2f GetField Cost=%r pct=%s "
      "ActualWork=%s RemainingWork=%s" % ((tag,) + vals))


p("=== V1 duration only, assign 100% after (MaxUnits set this time)")
t1 = task("V1 2d assign100", "2d")
t1.Assignments.Add(t1.ID, r_full.ID, 1.0)
mp.CalculateAll()
read("V1 after assign", t1)
t1.PercentComplete = 100
mp.CalculateAll()
read("V1 pct AFTER assign", t1)
show("V1 ActualStart/Finish", lambda: (str(t1.ActualStart)[:16], str(t1.ActualFinish)[:16]))

p("=== V2 Work set explicitly after the assignment")
t2 = task("V2 2d work16h", "2d")
t2.Assignments.Add(t2.ID, r_full.ID, 1.0)
mp.CalculateAll()
t2.Work = "16h"
mp.CalculateAll()
read("V2", t2)
show("V2 Duration after Work forced", lambda: t2.DurationText)
show("V2 assignment Units/Work", lambda: (t2.Assignments.Item(1).Units,
                                          t2.Assignments.Item(1).Work))

p("=== V3 Units as a percentage-style number (100)")
t3 = task("V3 2d units100", "2d")
t3.Assignments.Add(t3.ID, r_full.ID, 100.0)
mp.CalculateAll()
read("V3", t3)

p("=== V4 keyword Units argument")
t4 = task("V4 2d keyword", "2d")
try:
    t4.Assignments.Add(TaskID=t4.ID, ResourceID=r_full.ID, Units=1.0)
    p("  keyword form accepted")
except Exception as exc:
    p("  keyword form refused: %s" % type(exc).__name__)
mp.CalculateAll()
read("V4", t4)

p("=== V5 two resources, 0.5 + 0.5 units on a 4d task")
t5 = task("V5 4d half+half", "4d")
t5.Assignments.Add(t5.ID, r_full.ID, 0.5)
t5.Assignments.Add(t5.ID, r_half.ID, 0.5)
mp.CalculateAll()
read("V5", t5)
show("V5 assignment count", lambda: t5.Assignments.Count)
show("V5 each assignment Work", lambda: [t5.Assignments.Item(i).Work
                                         for i in range(1, t5.Assignments.Count + 1)])

p("=== V6 percent set before assign (the shipped defect)")
t6 = task("V6 pct then assign", "2d")
t6.PercentComplete = 100
read("V6 pct set, not assigned yet", t6)
t6.Assignments.Add(t6.ID, r_full.ID, 1.0)
mp.CalculateAll()
read("V6 after assign", t6)

p("=== V7 0-duration milestone carrying an assignment? (should stay cost-free)")
t7 = task("V7 milestone", "0d")
t7.Assignments.Add(t7.ID, r_full.ID, 1.0)
mp.CalculateAll()
read("V7", t7)
show("V7 Milestone flag", lambda: t7.Milestone)

p("=== totals")
show("prj.Work via GetField row 1", lambda: prj.Tasks.Item(1).GetField(PJ_WORK))
show("rows and their work", lambda: [(prj.Tasks.Item(i).Name.split()[0],
                                      prj.Tasks.Item(i).GetField(PJ_WORK),
                                      round(prj.Tasks.Item(i).Cost, 2))
                                     for i in range(1, prj.Tasks.Count + 1)
                                     if not prj.Tasks.Item(i).Summary])
show("project cost", lambda: prj.Cost)
show("project finish", lambda: str(prj.ProjectFinish))
mp.FileCloseEx(0)          # pjDoNotSave = 0
mp.Quit(0)
p("probe done, closed without saving via FileCloseEx(0)")
LOG.close()
