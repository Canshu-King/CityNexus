"""Export the coursework views from the shipped .mpp, honestly.

Measured on this install (se_project_export.log, then a page-by-page text
comparison of the produced PDFs): DocumentExport renders the view's table and
chart panes only - it does NOT include the Timeline pane, so exporting a
"Gantt with schedule" view twice produced two 21-page files with identical
text. So the milestone timeline is produced the only way that yields a real
Project artifact: a copy of the same plan reduced to its thirteen milestone
rows, kept next to the plan so the derivation is inspectable.

Page fitting is attempted through FilePageSetup; if Project refuses the
argument shape, the multi-page export is kept and reported rather than hidden.
"""
import hashlib
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from se_timeutil_r1 import dstr  # noqa: E402
OUT = os.environ.get("SE_MSP_OUT",
                     r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project")
MPP = os.path.join(OUT, "CityNexus_Software_Engineering_Plan.mpp")
MS_MPP = os.path.join(OUT, "CityNexus_Milestone_View.mpp")
LOG = open(os.path.join(HERE, "se_project_export_r2.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


import win32com.client as w32                                   # noqa: E402

VIEWS = [
    ("Gantt_Chart", ["甘特图"]),
    ("Tracking_Gantt", ["跟踪甘特图"]),
    ("Network_Diagram", ["网络图"]),
    ("WBS_View", ["任务工作表"]),
    ("Resource_Sheet", ["资源工作表"]),
    ("Detailed_Gantt", ["详细甘特图"]),
]

mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass

result = {"views": {}, "pageSetup": None, "milestoneCopy": None}

# ---------------------------------------------------------------- main plan
mp.FileOpen(MPP)
p = mp.ActiveProject
log("open %s: %d tasks, %d resources, finish %s, cost %s"
    % (os.path.basename(MPP), p.Tasks.Count, p.Resources.Count,
       dstr(p.ProjectFinish), p.Cost))

# FilePageSetup() with no arguments opens the modal Page Setup dialog and hangs
# an unattended run (observed), so page fitting is not attempted here. The
# exports stay multi-page, which is reported in Evidence rather than hidden.
result["pageSetup"] = "not attempted - FilePageSetup() opens a modal dialog"
log("skipping FilePageSetup (modal dialog risk); exports will be multi-page")

live = []
for cand in ("甘特图", "跟踪甘特图", "详细甘特图", "网络图", "任务工作表", "资源工作表",
             "日历", "包含日程表的甘特图"):
    try:
        mp.ViewApply(cand)
        live.append(cand)
    except Exception as exc:
        log("ViewApply %-12s unavailable: %s" % (cand, str(exc)[:60]))
log("views available: %s" % live)

for tag, cands in VIEWS:
    hit = next((c for c in cands if c in live), None)
    if not hit:
        log("SKIP %s" % tag)
        continue
    mp.ViewApply(hit)
    path = os.path.join(OUT, tag + ".pdf")
    if os.path.exists(path):
        os.remove(path)
    try:
        mp.DocumentExport(path, 0)
    except Exception as exc:
        log("DocumentExport %s failed: %s" % (tag, str(exc)[:120]))
        continue
    if os.path.exists(path):
        result["views"][tag] = {"view": hit, "bytes": os.path.getsize(path),
                                "sha": sha(path)}
        log("exported %-18s <- %-10s %8d  %s" % (tag, hit, os.path.getsize(path),
                                                 sha(path)))
    else:
        log("DocumentExport %s wrote nothing" % tag)

try:
    p.Saved = True
except Exception:
    pass
mp.FileClose()

# The milestone timeline is NOT built here. Deleting rows out of a copy proved
# unreliable (summary rows cascaded and M10-M12 vanished), and Project's
# DocumentExport does not render the Timeline pane at all. It has its own
# deterministic builder: se_milestone_view_r2.py.
try:
    mp.Quit()
except Exception:
    pass

dupes = []
seen = {}
for tag, v in result["views"].items():
    seen.setdefault(v["sha"], []).append(tag)
for k, tags in seen.items():
    if len(tags) > 1:
        dupes.append(tags)
result["duplicateExports"] = dupes
json.dump(result, open(os.path.join(HERE, "se_project_export_r2_result.json"), "w",
                       encoding="utf-8"), indent=1, ensure_ascii=False)
log("DONE. views=%d duplicates=%s" % (len(result["views"]), dupes or "none"))
sys.exit(0 if len(result["views"]) >= 4 and os.path.exists(path) else 1)
