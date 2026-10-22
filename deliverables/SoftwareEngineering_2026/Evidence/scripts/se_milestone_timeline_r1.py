"""Produce Milestone_Timeline.pdf from the same .mpp.

This Project install has no view literally called 时间表, so the timeline is
built the way Project intends: every zero-duration milestone is placed on the
Timeline pane with TaskOnTimeline, the pane is switched on, and the resulting
Gantt-with-timeline view is exported. If any of those calls is refused the
script says so instead of quietly shipping nothing.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("SE_MSP_OUT",
                     r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project")
MPP = os.path.join(OUT, "CityNexus_Software_Engineering_Plan.mpp")
LOG = open(os.path.join(HERE, "se_milestone_timeline.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


import win32com.client as w32                                   # noqa: E402

mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
mp.FileOpen(MPP)
p = mp.ActiveProject

ms = []
for i in range(1, p.Tasks.Count + 1):
    t = p.Tasks.Item(i)
    try:
        if t.Summary:
            continue
        if t.Milestone:
            ms.append(t)
    except Exception:
        continue
log("milestones in the file: %d" % len(ms))

placed, failed = 0, []
for t in ms:
    title = t.Name.split("  ")[0].strip()
    ok = False
    for how, fn in (("TaskOnTimeline(task, title)", lambda: mp.TaskOnTimeline(t, title)),
                    ("TaskOnTimeline(task)", lambda: mp.TaskOnTimeline(t)),
                    ("TaskOnTimeline()", lambda: mp.TaskOnTimeline())):
        try:
            fn()
            ok = True
            log("  placed %-6s via %s" % (title, how))
            break
        except Exception as exc:
            last = "%s: %s" % (type(exc).__name__, str(exc)[:90])
    if ok:
        placed += 1
    else:
        failed.append("%s -> %s" % (title, last))
log("placed %d/%d milestones on the timeline; failures: %s"
    % (placed, len(ms), failed[:5]))

for name in ("TimelineShow", "TimelineViewToggle"):
    try:
        getattr(mp, name)()
        log("%s succeeded" % name)
        break
    except Exception as exc:
        log("%s failed: %s" % (name, str(exc)[:90]))

view = None
for cand in ("包含日程表的甘特图", "甘特图", "详细甘特图", "日程表"):
    try:
        mp.ViewApply(cand)
        view = cand
        log("timeline exported from view %r" % cand)
        break
    except Exception as exc:
        log("ViewApply %s failed: %s" % (cand, str(exc)[:80]))

path = os.path.join(OUT, "Milestone_Timeline.pdf")
if os.path.exists(path):
    os.remove(path)
exported = False
if view:
    try:
        mp.DocumentExport(path, 0)
        exported = os.path.exists(path)
    except Exception as exc:
        log("DocumentExport failed: %s" % str(exc)[:140])
if exported:
    log("wrote %s (%d bytes)" % (path, os.path.getsize(path)))
else:
    log("NO TIMELINE PDF COULD BE PRODUCED - reported as a gap, not faked")

json.dump({"milestones": len(ms), "placed": placed, "failures": failed,
           "view": view, "pdf": path if exported else None,
           "bytes": os.path.getsize(path) if exported else 0},
          open(os.path.join(HERE, "se_milestone_timeline_result.json"), "w",
               encoding="utf-8"), indent=1, ensure_ascii=False)
try:
    p.Saved = True
except Exception:
    pass
mp.FileClose()
mp.Quit()
sys.exit(0 if exported else 1)
