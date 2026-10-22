"""Probe 9 - the resource type was the bug.

PjResourceTypes on this install is pjResourceTypeWork=0, Material=1, Cost=2.
The shipped builder set Type=1, i.e. a MATERIAL resource, which is exactly why
Work came back 0 and Cost was one unit times the rate. Here a WORK resource is
created and the hours/cost/progress chain is read back. Nothing is saved.
"""
import datetime
import os
import time

import win32com.client as w32

LOG = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "se_proj_probe_r9.log"), "w", encoding="utf-8", buffering=1)
T0 = time.time()
D = datetime.datetime
PJ_WORK = 188743680
PJ_COST = 188743685
PJ_PCT = 188743712
PJ_RES_MAXUNITS = 205520900
PJ_RES_TYPE = 205521196


def p(m):
    LOG.write("[%5.1fs] %s\n" % (time.time() - T0, m))
    LOG.flush()
    print(m, flush=True)


def try_(label, fn):
    try:
        v = fn()
        p("%-46s OK  %r" % (label, v))
        return v
    except Exception as exc:
        p("%-46s ERR %s: %s" % (label, type(exc).__name__, str(exc)[:110]))
        return None


mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
mp.FileNew()
prj = mp.ActiveProject
prj.ProjectStart = D(2026, 9, 7)
prj.CurrencySymbol = "$"
try:
    prj.StatusDate = D(2026, 10, 22)
except Exception as exc:
    p("StatusDate refused: %s" % type(exc).__name__)

p("=== work resource created the right way")
r1 = prj.Resources.Add("Member one")
try_("r1.Type = 0 (work)", lambda: setattr(r1, "Type", 0))
try_("r1.GetField(pjResourceType)", lambda: r1.GetField(PJ_RES_TYPE))
try_("r1.MaxUnits = 1.0", lambda: setattr(r1, "MaxUnits", 1.0))
try_("r1.MaxUnits read", lambda: r1.MaxUnits)
try_("r1.StandardRate = 20", lambda: setattr(r1, "StandardRate", 20.0))
try_("r1.OvertimeRate = 30", lambda: setattr(r1, "OvertimeRate", 30.0))
try_("r1.GetField(maxUnits)", lambda: r1.GetField(PJ_RES_MAXUNITS))
r2 = prj.Resources.Add("Member two")
try_("r2.Type = 0", lambda: setattr(r2, "Type", 0))
try_("r2.MaxUnits = 0.5", lambda: setattr(r2, "MaxUnits", 0.5))
try_("r2.StandardRate = 20", lambda: setattr(r2, "StandardRate", 20.0))


def snap(tag, t):
    try:
        a = [(t.Assignments.Item(i).Units, round(t.Assignments.Item(i).Work, 1),
              round(t.Assignments.Item(i).Cost, 2))
             for i in range(1, t.Assignments.Count + 1)]
        p("  %-20s Work=%s Cost=%.2f pct=%s AWork=%s Rem=%s assigns=%s"
          % (tag, t.GetField(PJ_WORK), t.Cost, t.PercentComplete,
             round(t.ActualWork, 1), round(t.RemainingWork, 1), a))
    except Exception as exc:
        p("  %-20s read ERR %s: %s" % (tag, type(exc).__name__, str(exc)[:110]))


def task(name, dur):
    t = prj.Tasks.Add(name)
    t.SetField(1280, 0)
    t.Duration = dur
    return t


p("=== A1 2d, one work resource at 1.0 units")
a1 = task("A1 2d", "2d")
try_("A1 assign", lambda: a1.Assignments.Add(a1.ID, r1.ID, 1.0))
mp.CalculateAll()
snap("A1 after assign", a1)
a1.PercentComplete = 100
mp.CalculateAll()
snap("A1 pct=100", a1)
try_("A1 actual dates", lambda: (str(a1.ActualStart)[:16], str(a1.ActualFinish)[:16]))

p("=== A2 2d at 50 percent")
a2 = task("A2 2d 50", "2d")
try_("A2 assign", lambda: a2.Assignments.Add(a2.ID, r1.ID, 0.5))
mp.CalculateAll()
a2.PercentComplete = 50
mp.CalculateAll()
snap("A2", a2)

p("=== A3 4d with two resources 0.5 + 0.5")
a3 = task("A3 4d two", "4d")
try_("A3 assign 1", lambda: a3.Assignments.Add(a3.ID, r1.ID, 0.5))
try_("A3 assign 2", lambda: a3.Assignments.Add(a3.ID, r2.ID, 0.5))
mp.CalculateAll()
snap("A3", a3)

p("=== A4 explicit work hours on a work resource")
a4 = task("A4 3d work20h", "3d")
try_("A4 assign", lambda: a4.Assignments.Add(a4.ID, r1.ID, 1.0))
mp.CalculateAll()
try_("A4 Work = '20h' after assign", lambda: setattr(a4, "Work", "20h"))
mp.CalculateAll()
snap("A4", a4)
try_("A4 Duration after", lambda: a4.DurationText)

p("=== A5 material resource for AI compute (cost per use, no hours)")
r5 = prj.Resources.Add("Compute lane")
try_("r5.Type = 1 (material)", lambda: setattr(r5, "Type", 1))
try_("r5.StdRate = 6", lambda: setattr(r5, "StandardRate", 6.0))
try_("r5.CostPerUse = 12", lambda: setattr(r5, "CostPerUse", 12.0))
a5 = task("A5 material 1d", "1d")
try_("A5 assign material", lambda: a5.Assignments.Add(a5.ID, r5.ID, 3.0))
mp.CalculateAll()
snap("A5", a5)

p("=== totals")
try_("prj.Work", lambda: prj.Tasks.Item(1).GetField(PJ_WORK))
try_("prj.Cost", lambda: prj.Cost)
try_("rows", lambda: [(prj.Tasks.Item(i).Name.split()[0],
                       prj.Tasks.Item(i).GetField(PJ_WORK),
                       round(prj.Tasks.Item(i).Cost, 2))
                      for i in range(1, prj.Tasks.Count + 1)
                      if not prj.Tasks.Item(i).Summary])
mp.FileCloseEx(0)
mp.Quit(0)
p("probe done (no save)")
LOG.close()
