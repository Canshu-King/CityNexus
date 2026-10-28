"""Per-Task.ID fidelity: the 65-row plan of record vs the classroom copy."""
import hashlib
import json
import os

import win32com.client as w

DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
SRC = os.path.join(DEL, "Microsoft_Project", "CityNexus_Software_Engineering_Plan.mpp")
R4 = os.path.join(DEL, "Classroom", "Teacher_03_Project_Overview_R4_EN.mpp")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def dump(path):
    os.chmod(path, 0o444)
    m = w.DispatchEx("MSProject.Application")
    m.Visible = False
    m.DisplayAlerts = 0
    m.FileOpen(path, True)
    p = m.ActiveProject
    rows = {}
    for i in range(1, p.Tasks.Count + 1):
        t = p.Tasks.Item(i)
        res = []
        for k in range(1, t.Assignments.Count + 1):
            a = t.Assignments.Item(k)
            try:
                name = str(a.ResourceName)
            except Exception:
                name = ""
            try:
                units = round(float(a.Units), 2)
            except Exception:
                units = None
            res.append((name, units))
        rows[int(t.ID)] = {
            "start": t.Start.strftime("%Y-%m-%d %H:%M"),
            "finish": t.Finish.strftime("%Y-%m-%d %H:%M"),
            "dur": int(t.Duration), "work": round(float(t.Work), 2),
            "pct": int(t.PercentComplete), "milestone": bool(t.Milestone),
            "summary": bool(t.Summary), "level": int(t.OutlineLevel),
            "pred": str(t.Predecessors or "").strip(),
            "res": sorted(res),
        }
    m.FileCloseEx(0)
    m.Quit()
    os.chmod(path, 0o644)
    return rows


before = sha(SRC)
src = dump(SRC)
r4 = dump(R4)

diff = []
for tid in sorted(set(src) | set(r4)):
    a, b = src.get(tid), r4.get(tid)
    if a is None or b is None:
        diff.append("ID %d missing on one side" % tid)
        continue
    for k in ("start", "finish", "dur", "work", "pct", "milestone", "summary",
              "level", "pred", "res"):
        if a[k] != b[k]:
            diff.append("ID %d %s: plan=%r r4=%r" % (tid, k, a[k], b[k]))

out = {"ids": len(src), "fields": ["start", "finish", "dur", "work", "pct",
                                   "milestone", "summary", "level", "pred", "res"],
       "differences": len(diff), "sample": diff[:10],
       "sourceUnchanged": sha(SRC) == before,
       "r4_bytes": os.path.getsize(R4), "r4_sha16": sha(R4)}
print(json.dumps(out, ensure_ascii=False, indent=1))
json.dump(out, open(r"D:\moodle\live_checks\se_r41_fidelity.json", "w",
                    encoding="utf-8"), ensure_ascii=False, indent=1)
