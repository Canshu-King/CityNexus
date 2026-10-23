"""Milestone_Timeline.pdf, built deterministically.

The first attempt deleted rows out of a copy of the plan and bottom-up deletion
cascaded through summary rows, silently dropping M10-M12. So instead: read the
thirteen milestone rows and their computed dates straight out of the shipped
.mpp, then build a small Project file that carries exactly those dates, and
export its Gantt. The dates are copied from the plan, not retyped, so the
timeline cannot disagree with the schedule.
"""
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from se_timeutil_r1 import dstr  # noqa: E402
OUT = os.environ.get("SE_MSP_OUT",
                     r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project")
MPP = os.path.join(OUT, "CityNexus_Software_Engineering_Plan.mpp")
MS_MPP = os.path.join(OUT, "CityNexus_Milestone_View.mpp")
LOG = open(os.path.join(HERE, "se_milestone_view.log"), "w", encoding="utf-8", buffering=1)
T0 = time.time()


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


import datetime
import win32com.client as w32                                   # noqa: E402

D = datetime.datetime

# ---- 1. read the milestones out of the shipped plan ----------------------
mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
# A plain open lets Project rewrite the container on close even with nothing
# edited, so the shipped plan is held read-only for this read and its digest is
# compared afterwards; FileClose() without an argument can raise a save prompt.
import stat
os.chmod(MPP, stat.S_IREAD)
plan_before = hashlib.sha256(open(MPP, "rb").read()).hexdigest()
mp.FileOpen(MPP)
p = mp.ActiveProject
found = []
for i in range(1, p.Tasks.Count + 1):
    t = p.Tasks.Item(i)
    try:
        if t.Summary or not t.Milestone:
            continue
        found.append({"name": t.Name, "finish": dstr(t.Finish),
                      "deadline": dstr(t.Deadline) if t.Deadline else "",
                      "wbs": t.WBS, "cost": t.Cost})
    except Exception:
        continue
log("milestones read from the plan: %d" % len(found))
for f in found:
    log("   %-6s %-56s finish=%s deadline=%s" % (f["wbs"], f["name"][:56],
                                                 f["finish"], f["deadline"]))
try:
    p.Saved = True
except Exception:
    pass
mp.FileClose()

# ---- 2. build the timeline file from exactly those dates -----------------
if os.path.exists(MS_MPP):
    os.remove(MS_MPP)
mp.FileNew()
q = mp.ActiveProject
q.Name = "CityNexus milestone timeline"
for prop, val in (("Author", "CityNexus coursework build"),
                  ("Company", "TUTE - Software Engineering module 2026"),
                  ("Manager", "CityNexus coursework build"),
                  ("Title", "CityNexus milestone timeline"),
                  ("Subject", "Software Engineering 2026 Part 2"),
                  ("Keywords", "CityNexus; milestones; coursework"),
                  ("Comments", "Derived from CityNexus_Software_Engineering_Plan.mpp")):
    try:
        setattr(q, prop, val)
    except Exception as exc:
        log("  summary property %s refused: %s" % (prop, type(exc).__name__))
q.ProjectStart = D.strptime(found[0]["finish"] + " 09:00", "%Y-%m-%d %H:%M")
try:
    q.CurrencySymbol = "$"
except Exception:
    pass
made = []
for f in found:
    t = q.Tasks.Add(f["name"])
    try:
        t.SetField(1280, 0)
    except Exception:
        pass
    t.Duration = "0d"
    # 00:00 is outside the working day, and Project moves a milestone written at
    # midnight back to the previous working minute: every row came out one day
    # early against the plan it was copied from. Write it inside working hours.
    t.Start = D.strptime(f["finish"] + " 09:00", "%Y-%m-%d %H:%M")
    if f["deadline"] and f["deadline"] != "NaT":
        try:
            t.Deadline = D.strptime(f["deadline"] + " 09:00", "%Y-%m-%d %H:%M")
        except Exception:
            pass
    t.Notes = ("Copied from CityNexus_Software_Engineering_Plan.mpp by "
               "se_milestone_view_r1.py on %s. The date is the schedule's own "
               "computed milestone date, not a retyped value."
               % time.strftime("%Y-%m-%d %H:%M"))
    made.append((t.Name, dstr(t.Finish)))
mp.CalculateAll()
log("timeline file rows: %d" % len(made))
for n, dt in made:
    log("   %-56s %s" % (n[:56], dt))
mismatch = [(a[0], a[1], b["finish"]) for a, b in zip(made, found) if a[1] != b["finish"]]
log("date mismatches against the plan: %s" % (mismatch or "none"))

view = None
for cand in ("甘特图", "详细甘特图", "任务工作表"):
    try:
        mp.ViewApply(cand)
        view = cand
        break
    except Exception as exc:
        log("ViewApply %s failed: %s" % (cand, str(exc)[:70]))
path = os.path.join(OUT, "Milestone_Timeline.pdf")
if os.path.exists(path):
    os.remove(path)
ok = False
try:
    mp.DocumentExport(path, 0)
    ok = os.path.exists(path)
except Exception as exc:
    log("DocumentExport failed: %s" % str(exc)[:140])
q.SaveAs(MS_MPP)
try:
    q.Saved = True
except Exception:
    pass
mp.FileCloseEx(0)
mp.Quit()
os.chmod(MPP, stat.S_IWRITE)
plan_after = hashlib.sha256(open(MPP, "rb").read()).hexdigest()
log("plan digest %s before, %s after (%s)" % (plan_before[:16], plan_after[:16],
                                              "held" if plan_after == plan_before
                                              else "CHANGED BY A READ"))
ok = ok and plan_after == plan_before
if ok:
    log("wrote Milestone_Timeline.pdf %d bytes %s from view %r"
        % (os.path.getsize(path),
           hashlib.sha256(open(path, "rb").read()).hexdigest()[:16], view))
json.dump({"milestones": found, "timelineRows": made, "mismatches": mismatch,
           "view": view, "pdf": path if ok else None,
           "source": os.path.basename(MPP)},
          open(os.path.join(HERE, "se_milestone_view_result.json"), "w",
               encoding="utf-8"), indent=1, ensure_ascii=False)
sys.exit(0 if (ok and not mismatch) else 1)
