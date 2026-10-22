"""Build Milestone_Timeline.pdf from a copy of the plan reduced to its
milestone rows. Deleting top-down leaves stale row references and wiped the
whole copy on the first attempt, so this walks the rows bottom-up."""
import hashlib
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
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


import win32com.client as w32                                   # noqa: E402

if os.path.exists(MS_MPP):
    os.remove(MS_MPP)
shutil.copyfile(MPP, MS_MPP)
mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
mp.FileOpen(MS_MPP)
p = mp.ActiveProject
n0 = p.Tasks.Count
log("copy opened with %d rows" % n0)

deleted, kept = 0, []
for i in range(n0, 0, -1):
    try:
        t = p.Tasks.Item(i)
        name = t.Name
    except Exception as exc:
        log("  row %d unreadable: %s" % (i, type(exc).__name__))
        continue
    try:
        is_ms = bool(t.Milestone)
    except Exception:
        is_ms = name.strip().startswith("M")
    if is_ms:
        kept.append((i, name, str(t.Finish)[:10]))
        continue
    try:
        t.Delete()
        deleted += 1
    except Exception as exc:
        log("  could not delete %-40s %s" % (name[:40], str(exc)[:70]))
mp.CalculateAll()
log("deleted %d rows, kept %d milestones, %d rows remain" % (deleted, len(kept), p.Tasks.Count))

rows = []
for i in range(1, p.Tasks.Count + 1):
    t = p.Tasks.Item(i)
    try:
        rows.append({"wbs": t.WBS, "name": t.Name, "start": str(t.Start)[:10],
                     "finish": str(t.Finish)[:10], "ms": bool(t.Milestone)})
    except Exception:
        continue
for r in rows:
    log("   %-5s %-52s %s -> %s" % (r["wbs"], r["name"][:52], r["start"], r["finish"]))

view = None
for cand in ("甘特图", "详细甘特图", "日历", "任务工作表"):
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
if ok:
    log("wrote Milestone_Timeline.pdf %d bytes %s"
        % (os.path.getsize(path),
           hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]))
else:
    log("STILL NOT PRODUCED")
try:
    p.Saved = True
except Exception:
    pass
mp.FileClose()
mp.Quit()
json.dump({"rows": rows, "view": view, "pdf": path if ok else None},
          open(os.path.join(HERE, "se_milestone_view_result.json"), "w",
               encoding="utf-8"), indent=1, ensure_ascii=False)
sys.exit(0 if ok else 1)
