"""Export the full task dataset from both classroom mpps for the
drawn-from-data presentation Gantt (the COM bar-colour road is closed with
three-API evidence; a drawn chart is the only carrier whose every pixel is
controllable).
"""
import json
import os
import sys
import time

import win32com.client as w32

DEL = (r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026")
TARGETS = {
    "zh": os.path.join(DEL, "Classroom", "Teacher_03_Project_Overview_R4.mpp"),
    "en": os.path.join(DEL, "Classroom", "Teacher_03_Project_Overview_R4_EN.mpp"),
}
OUTP = r"D:\moodle\_se_gantt_data.json"
LOGP = r"D:\moodle\_se_gantt_data.log"

LOG = open(LOGP, "w", encoding="utf-8", buffering=1)
T0 = time.time()


def log(m):
    LOG.write("[%6.1fs] %s" % (time.time() - T0, m) + chr(10))
    print("[%6.1fs] %s" % (time.time() - T0, m), flush=True)


def dstr(v):
    try:
        return v.strftime("%Y-%m-%d")
    except Exception:
        return str(v)[:10]


try:
    mp = w32.gencache.EnsureDispatch("MSProject.Application")
except Exception:
    mp = w32.DispatchEx("MSProject.Application")
mp.Visible = False
try:
    mp.DisplayAlerts = 0
except Exception:
    pass

data = {}
for tag, path in TARGETS.items():
    os.chmod(path, 0o644)
    mp.FileOpen(path, True)
    q = mp.ActiveProject
    tasks = []
    for i in range(1, q.Tasks.Count + 1):
        t = q.Tasks.Item(i)
        try:
            pred = str(t.Predecessors or "").strip()
            tasks.append({
                "id": int(t.ID),
                "name": str(t.Name),
                "outline": int(t.OutlineLevel),
                "summary": bool(t.Summary),
                "milestone": bool(t.Milestone),
                "start": dstr(t.Start),
                "finish": dstr(t.Finish),
                "pct": int(t.PercentComplete),
                "pred": [p.strip() for p in pred.split(",") if p.strip()],
                "work": round(float(t.Work), 1),
            })
        except Exception:
            pass
    data[tag] = {"title": str(q.Title), "tasks": tasks}
    log("%s: %d tasks" % (tag, len(tasks)))
    mp.FileCloseEx(0)

mp.Quit()
json.dump(data, open(OUTP, "w", encoding="utf-8"), indent=1,
          ensure_ascii=False)
log("exported -> %s" % OUTP)
LOG.close()
sys.exit(0)
