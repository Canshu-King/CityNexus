"""Probe 8 - get real work hours and cost into assigned tasks.

MaxUnits cannot be set through the Resource.MaxUnits property on this install,
so this measures the field-id route and every order of writing Work / Units /
PercentComplete, and reads back what Project really charges for it.
Nothing is saved.
"""
import datetime
import os
import time

import win32com.client as w32

LOG = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "se_proj_probe_r8.log"), "w", encoding="utf-8", buffering=1)
T0 = time.time()
D = datetime.datetime
PJ_WORK = 188743680
PJ_COST = 188743685
PJ_PCT = 188743712
PJ_RES_MAXUNITS = 205520900
PJ_ASSIGN_WORK = 255852552


def p(m):
    LOG.write("[%5.1fs] %s\n" % (time.time() - T0, m))
    LOG.flush()
    print(m, flush=True)


def try_(label, fn):
    try:
        p("%-46s OK  %r" % (label, fn()))
        return True
    except Exception as exc:
        p("%-46s ERR %s: %s" % (label, type(exc).__name__, str(exc)[:110]))
        return False


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

r1 = prj.Resources.Add("Member one")
r1.Type = 1
r1.StandardRate = 20.0
try_("r1.SetField(pjResourceMaxUnits, 1.0)", lambda: r1.SetField(PJ_RES_MAXUNITS, 1.0))
try_("r1.SetField(pjResourceMaxUnits, '100%')", lambda: r1.SetField(PJ_RES_MAXUNITS, "100%"))
try_("r1.GetField(pjResourceMaxUnits)", lambda: r1.GetField(PJ_RES_MAXUNITS))
try_("r1.MaxUnits read", lambda: r1.MaxUnits)
try_("r1.GetField(pjResourceStandardRate)", lambda: r1.GetField(205520902))

r2 = prj.Resources.Add("Member two")
r2.Type = 1
r2.StandardRate = 20.0
try_("r2.SetField(maxUnits, 0.5)", lambda: r2.SetField(PJ_RES_MAXUNITS, 0.5))


def task(name, dur):
    t = prj.Tasks.Add(name)
    t.SetField(1280, 0)
    t.Duration = dur
    return t


def snap(tag, t):
    try:
        p("  %-22s Work=%r (%s)  Cost=%.2f  pct=%s  AWork=%s  Rem=%s  assignWork=%s"
          % (tag, t.Work, t.GetField(PJ_WORK), t.Cost, t.PercentComplete,
             t.ActualWork, t.RemainingWork,
             [t.Assignments.Item(i).GetField(PJ_ASSIGN_WORK)
              for i in range(1, t.Assignments.Count + 1)]))
    except Exception as exc:
        p("  %-22s read ERR %s: %s" % (tag, type(exc).__name__, str(exc)[:90]))


p("=== W1 Work written by SetField before the assignment")
w1 = task("W1 2d", "2d")
try_("W1 SetField(PJ_WORK,'16h')", lambda: w1.SetField(PJ_WORK, "16h"))
snap("W1 before assign", w1)
w1.Assignments.Add(w1.ID, r1.ID, 1.0)
mp.CalculateAll()
snap("W1 after assign", w1)
w1.PercentComplete = 100
mp.CalculateAll()
snap("W1 pct=100", w1)

p("=== W2 Work written by property after the assignment")
w2 = task("W2 2d", "2d")
w2.Assignments.Add(w2.ID, r1.ID, 1.0)
mp.CalculateAll()
snap("W2 after assign", w2)
try_("W2 .Work='16h' after assign", lambda: setattr(w2, "Work", "16h"))
try_("W2 SetField(PJ_WORK,'16h') after assign", lambda: w2.SetField(PJ_WORK, "16h"))
mp.CalculateAll()
snap("W2 after work write", w2)

p("=== W3 assignment-level Work")
w3 = task("W3 2d", "2d")
w3.Assignments.Add(w3.ID, r1.ID, 1.0)
mp.CalculateAll()
try_("W3 assignment SetField(work,'16h')",
     lambda: w3.Assignments.Item(1).SetField(PJ_ASSIGN_WORK, "16h"))
mp.CalculateAll()
snap("W3", w3)

p("=== W4 two resources 1.0 + 1.0 units on a 4d task")
w4 = task("W4 4d", "4d")
try_("W4 SetField(PJ_WORK,'32h')", lambda: w4.SetField(PJ_WORK, "32h"))
w4.Assignments.Add(w4.ID, r1.ID, 1.0)
w4.Assignments.Add(w4.ID, r2.ID, 1.0)
mp.CalculateAll()
snap("W4", w4)
try_("W4 units read back", lambda: [w4.Assignments.Item(i).Units
                                    for i in range(1, w4.Assignments.Count + 1)])

p("=== W5 nothing but duration, no assignment (cost must be zero)")
w5 = task("W5 3d", "3d")
mp.CalculateAll()
snap("W5", w5)

p("=== W6 milestone with a deadline and a link")
w6 = task("W6 milestone", "0d")
w6.Predecessors = "%dFS" % w4.ID
try_("W6 Deadline", lambda: setattr(w6, "Deadline", D(2026, 11, 6)))
mp.CalculateAll()
snap("W6", w6)
try_("W6 start/finish/constraint", lambda: (str(w6.Start)[:16], str(w6.Finish)[:16],
                                            w6.ConstraintType, w6.Milestone))

p("=== totals")
try_("project cost", lambda: prj.Cost)
try_("project finish", lambda: str(prj.ProjectFinish))
try_("rows", lambda: [(prj.Tasks.Item(i).Name.split()[0],
                       prj.Tasks.Item(i).GetField(PJ_WORK),
                       round(prj.Tasks.Item(i).Cost, 2))
                      for i in range(1, prj.Tasks.Count + 1)])
mp.FileCloseEx(0)
mp.Quit(0)
p("probe done, closed with FileCloseEx(pjDoNotSave)")
LOG.close()
