"""Probe 10 - how to make Project roll unfinished work past the status date.

The plan has rows at 40-85 percent whose planned finish sits before the status
date, and rows at 0 percent that were simply never done. Both read as an
internally inconsistent schedule. This measures the two real mechanisms -
OptionsCalculation(SpreadPercentToStatusDate) and TaskMoveToStatusDate - with
every argument form, and reports which one actually moves a date.
Nothing is saved.
"""
import datetime
import os
import time

import win32com.client as w32

LOG = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "se_proj_probe_r10.log"), "w", encoding="utf-8", buffering=1)
T0 = time.time()
D = datetime.datetime


def p(m):
    LOG.write("[%5.1fs] %s\n" % (time.time() - T0, m))
    LOG.flush()
    print(m, flush=True)


def attempt(label, fn):
    try:
        v = fn()
        p("%-52s OK   %r" % (label, v))
        return True
    except Exception as exc:
        p("%-52s ERR  %s: %s" % (label, type(exc).__name__, str(exc)[:120]))
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
prj.StatusDate = D(2026, 10, 22)
p("start=%s status=%s" % (prj.ProjectStart, prj.StatusDate))

r = prj.Resources.Add("Worker")
r.Type = 0
r.MaxUnits = 1.0
r.StandardRate = 20.0


def t_(name, dur, pct=0, preds=None):
    t = prj.Tasks.Add(name)
    t.SetField(1280, 0)
    t.Duration = dur
    if preds:
        t.Predecessors = preds
    t.Assignments.Add(t.ID, r.ID, 1.0)
    if pct:
        t.PercentComplete = pct
    return t


anchor = t_("anchor 1d", "1d", 100)
half = t_("half 10d 50", "10d", 50, "%dFS" % anchor.ID)
zero = t_("zero 5d 0", "5d", 0, "%dFS" % half.ID)
mp.CalculateAll()


def snap(tag):
    p("%-24s anchor %s..%s | half %s..%s (%s%% rem %s) | zero %s..%s (%s%%)"
      % (tag, str(anchor.Start)[:10], str(anchor.Finish)[:10],
         str(half.Start)[:10], str(half.Finish)[:10], half.PercentComplete,
         round(half.RemainingWork / 60.0, 1),
         str(zero.Start)[:10], str(zero.Finish)[:10], zero.PercentComplete))


snap("as entered")

p("=== A) OptionsCalculation was measured to hang the session (modal), skipped here")

p("=== B) TaskMoveToStatusDate argument forms")
for label, kwargs in (("MoveCompleted=False MoveIncomplete=True",
                       {"MoveCompleted": False, "MoveIncomplete": True}),
                      ("both True", {"MoveCompleted": True, "MoveIncomplete": True}),
                      ("ints 0/3", {"MoveCompleted": 0, "MoveIncomplete": 3}),
                      ("ints 2/3", {"MoveCompleted": 2, "MoveIncomplete": 3}),
                      ("no args", {})):
    moved = attempt("TaskMoveToStatusDate(%s)" % label,
                    lambda kw=kwargs: mp.TaskMoveToStatusDate(**kw))
    mp.CalculateAll()
    snap("  -> %s" % label)

p("=== C) does a status date in the past change anything by itself")
attempt("StatusDate back to 2026-09-15", lambda: setattr(prj, "StatusDate",
                                                         D(2026, 9, 15)))
mp.CalculateAll()
snap("status 09-15")
attempt("StatusDate to 2026-10-22", lambda: setattr(prj, "StatusDate",
                                                   D(2026, 10, 22)))
mp.CalculateAll()
snap("status 10-22 again")

p("=== D) ReportDaysAfterStatus / critical path options")
attempt("prj.ReportDaysAfterStatus?", lambda: getattr(prj, "ReportDaysAfterStatus",
                                                      "absent"))
attempt("mp.MoveCompletedTasksToStatus?", lambda: getattr(mp,
                                                          "MoveCompletedTasksToStatus",
                                                          "absent"))
p("project finish: %s" % prj.ProjectFinish)
mp.FileCloseEx(0)
mp.Quit(0)
p("probe done (no save)")
LOG.close()
