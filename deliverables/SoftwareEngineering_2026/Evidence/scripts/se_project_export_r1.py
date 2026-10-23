"""Open the shipped .mpp in Microsoft Project and export the four required
views to PDF, one file per view, from the same project data."""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import win32com.client as w32                                   # noqa: E402

OUT = os.environ.get("SE_MSP_OUT",
                     r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project")
MPP = os.path.join(OUT, "CityNexus_Software_Engineering_Plan.mpp")
LOG = open(os.path.join(HERE, "se_project_export.log"), "w", encoding="utf-8", buffering=1)
T0 = time.time()


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


WANT = [
    ("Gantt_Chart", ["甘特图", "Gantt"]),
    ("Network_Diagram", ["网络图", "Network"]),
    ("WBS_View", ["任务工作表", "Task Sheet", "任务分配状况表"]),
    ("Resource_Sheet", ["资源工作表", "Resource Sheet"]),
    ("Milestone_Timeline", ["时间表", "Timeline"]),
    ("Tracking_Gantt", ["跟踪甘特图", "Tracking Gantt"]),
]

mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
log("opening %s" % MPP)
mp.FileOpen(MPP)
p = mp.ActiveProject
log("project %s: %d tasks, finish %s, cost %s" % (p.Name, p.Tasks.Count,
                                                  str(p.ProjectFinish)[:10], p.Cost))
# mp.Views() hangs this install (observed: the process never returns), so the
# view names are taken from a candidate list and proved by ViewApply actually
# switching. Whatever Project accepts is what gets exported.
names = ["甘特图", "跟踪甘特图", "详细甘特图", "网络图", "关系图", "任务工作表",
         "资源工作表", "时间表", "日历", "任务使用情况", "资源使用情况",
         "包含日程表的甘特图", "里程碑日期图", "资源计划表", "任务板"]
log("candidate views: %d" % len(names))
live = []
for nm in names:
    try:
        mp.ViewApply(nm)
        live.append(nm)
        log("   ViewApply OK   %s" % nm)
    except Exception as exc:
        log("   ViewApply MISS %-18s %s" % (nm, str(exc)[:70]))
names = live
log("views this install accepts: %s" % names)

done = {}
for tag, cands in WANT:
    hit = None
    for c in cands:
        if c in names:
            hit = c
            break
        loose = [x for x in names if c in x]
        if loose:
            hit = loose[0]
            break
    if hit is None and cands[0] == "甘特图":
        hit = "包含日程表的甘特图" if "包含日程表的甘特图" in names else None
    if not hit:
        log("SKIP %-20s (no matching view)" % tag)
        continue
    try:
        mp.ViewApply(hit)
    except Exception as exc:
        log("ViewApply %s (%s) failed: %s" % (tag, hit, str(exc)[:140]))
        continue
    log("  -> on view %r" % hit)
    path = os.path.join(OUT, tag + ".pdf")
    if os.path.exists(path):
        os.remove(path)
    try:
        mp.DocumentExport(path, 0)
    except Exception as exc:
        log("DocumentExport %s failed: %s" % (tag, str(exc)[:160]))
        continue
    if os.path.exists(path):
        done[tag] = {"view": hit, "bytes": os.path.getsize(path)}
        log("exported %-20s <- %-14s %d bytes" % (tag, hit, os.path.getsize(path)))
    else:
        log("DocumentExport %s reported success but wrote nothing" % tag)

try:
    png = os.path.join(OUT, "Milestone_Timeline.png")
    mp.ViewApply("时间表")
    mp.TimelineExport(png, 1600)
    if os.path.exists(png):
        done["Milestone_Timeline_png"] = {"bytes": os.path.getsize(png)}
        log("TimelineExport wrote %d bytes" % os.path.getsize(png))
except Exception as exc:
    log("TimelineExport failed: %s" % str(exc)[:160])

json.dump({"exports": done, "viewNames": names[:80]},
          open(os.path.join(HERE, "se_project_export_result.json"), "w",
               encoding="utf-8"), indent=1, ensure_ascii=False)
try:
    p.Saved = True
except Exception:
    pass
mp.FileClose()
mp.Quit()
log("EXPORT DONE: %d views" % len([k for k in done if done[k].get("view")]))
sys.exit(0 if len([k for k in done if "pdf" in k.lower() or done[k].get("view")]) >= 4 else 1)
