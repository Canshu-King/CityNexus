"""R4.4: an English classroom twin of the frozen R4 Project view.

The operator asked for a bilingual classroom set (2026-10-29, overnight round).
The R4 Chinese file stays frozen (GPT verdict 2026-10-25: "freeze the Project
layout"); this script builds the EN twin from a byte copy of it, so the saved
classroom view (five-column table, summary bars, timescale, collapsed outline)
carries over untouched. Only display language changes:

  * the 11 summary rows get their ENGLISH names back - not inventions: the R4
    build wrote every row's original plan name into its Notes ("计划原名："),
    so the EN twin restores exactly that string;
  * the five course milestones M9-M13 switch to the EN mirror of their Chinese
    display names (same caveats: plan date vs contract deadline are different
    things);
  * row notes, project Title and Notes switch to English; Author (the three
    students) is untouched.

Structure is audited the same way se_teacher_r4_build_r1.py audits the zh twin:
task/link/assignment counts and summary rollups (start/finish/pct/work/cost)
must not drift by one digit, milestone dates and deadlines must not move, and
the frozen zh source must stay byte-identical.
"""
import hashlib
import json
import os
import shutil
import sys
import time

import win32com.client as w32

HERE = os.path.dirname(os.path.abspath(__file__))
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
SRC = os.path.join(DEL, "Classroom", "Teacher_03_Project_Overview_R4.mpp")
OUT = os.path.join(DEL, "Classroom", "Teacher_03_Project_Overview_R4_EN.mpp")
LOG = open(os.path.join(HERE, "se_r43_project_en_r1.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()

MILESTONE_EN = {
    "M9": "M9  System test ready (plan 10-06, deadline 11-02)",
    "M10": "M10  Part 1 contract deadline 10-02 (submission record pending "
           "platform confirmation)",
    "M11": "M11  10-23 teacher-student meeting (held? unconfirmed)",
    "M12": "M12  Part 2 contract deadline 11-06",
    "M13": "M13  Course delivery complete (plan 10-23)",
}


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def sha(p, n=64):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


def dstr(v):
    try:
        return v.strftime("%Y-%m-%d")
    except Exception:
        return str(v)[:10]


def mkey(name):
    s = str(name).strip()
    return s.split()[0] if s else ""


def dl(t):
    try:
        v = t.Deadline
        return dstr(v) if v else ""
    except Exception:
        return ""


def orig_name_from_notes(notes):
    """The plan's own English name, recorded by the R4 build in every row."""
    for ln in str(notes or "").splitlines():
        ln = ln.strip()
        if ln.startswith("\u8ba1\u5212\u539f\u540d\uff1a"):  # 计划原名：
            got = ln[len("\u8ba1\u5212\u539f\u540d\uff1a"):].strip()
            if got:
                return got
    return ""


def snap(q):
    out = {"summaries": {}, "milestones": {}, "tasks": q.Tasks.Count,
           "links": 0, "assignments": 0}
    for i in range(1, q.Tasks.Count + 1):
        t = q.Tasks.Item(i)
        key = str(int(t.ID))
        pre = str(t.Predecessors or "").strip()
        out["links"] += len([x for x in pre.split(",") if x.strip()])
        out["assignments"] += t.Assignments.Count
        if t.Summary:
            out["summaries"][key] = {
                "name": str(t.Name), "start": dstr(t.Start),
                "finish": dstr(t.Finish), "pct": int(t.PercentComplete),
                "work": round(float(t.Work), 1), "cost": round(float(t.Cost), 2)}
        if t.Milestone:
            out["milestones"][key] = {
                "name": str(t.Name), "tag": mkey(t.Name),
                "start": dstr(t.Start), "finish": dstr(t.Finish),
                "deadline": dl(t)}
    return out


def drift_of(base, after):
    bad = []
    for key, a in base["summaries"].items():
        b = after["summaries"].get(key)
        if not b:
            bad.append("summary id %s missing" % key)
            continue
        for k in ("start", "finish", "pct", "work", "cost"):
            if a[k] != b[k]:
                bad.append("id %s %s: %s -> %s" % (key, k, a[k], b[k]))
    return bad


src_before = sha(SRC)
log("frozen zh twin sha256/16 %s (read-only during this run)" % src_before)
if os.path.exists(OUT):
    os.chmod(OUT, 0o644)
    os.remove(OUT)
os.chmod(SRC, 0o444)
shutil.copy2(SRC, OUT)
os.chmod(SRC, 0o644)
os.chmod(OUT, 0o644)
log("copied -> %s (%d bytes)" % (os.path.basename(OUT), os.path.getsize(OUT)))

mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
import atexit


def bye():
    try:
        mp.FileCloseEx(0)
    except Exception:
        pass
    try:
        mp.Quit()
    except Exception:
        pass


atexit.register(bye)
mp.FileOpen(OUT)
q = mp.ActiveProject
base = snap(q)
log("before: tasks=%d summaries=%d milestones=%d links=%d assignments=%d"
    % (base["tasks"], len(base["summaries"]), base["milestones"] and
       len(base["milestones"]), base["links"], base["assignments"]))

renamed_s, renamed_m, missing_orig = 0, 0, []
for i in range(1, q.Tasks.Count + 1):
    t = q.Tasks.Item(i)
    wbs = str(t.WBS)
    old = str(t.Name)
    if t.Summary:
        orig = orig_name_from_notes(t.Notes)
        if not orig:
            missing_orig.append("id %s WBS %s" % (int(t.ID), wbs))
            continue
        t.Notes = ("Classroom display name (EN): %s\nChinese classroom name: %s\n"
                   "WBS %s. Dates/percent/work/cost are this copy's own computed "
                   "values from the same 65-row plan; nothing was rescheduled."
                   % (orig, old, wbs))
        t.Name = orig
        renamed_s += 1
    elif t.Milestone:
        tag = mkey(old)
        if tag in MILESTONE_EN:
            t.Notes = ("Classroom display name (EN): %s\nChinese classroom name: "
                       "%s\nWBS %s; plan date %s, contract/check deadline %s. "
                       "A plan date is not a happened date."
                       % (MILESTONE_EN[tag], old, wbs, dstr(t.Start),
                          dl(t) or "none"))
            t.Name = MILESTONE_EN[tag]
            renamed_m += 1
log("EN display names written: %d summaries, %d milestones" % (renamed_s, renamed_m))
if missing_orig:
    log("rows without a recoverable original name: %s" % missing_orig)

q.Title = ("CityNexus Software Engineering 2026 - Classroom Gantt "
           "(a view of the same 65-row plan)")
q.Author = "\u6768\u5efa\u658c 0802240329 / \u738b\u5609\u777f 0802240322 / \u738b\u82af\u73a5 0802240324"
q.Notes = (
    "This is an English-display twin of Classroom/Teacher_03_Project_Overview_R4.mpp, "
    "which is itself a view copy of Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp: "
    "65 tasks, every dependency record, every resource assignment, work and cost are all "
    "in this file - nothing was deleted. The classroom view only renames the 11 summary "
    "rows (back to the plan's own English names; the Chinese names are kept in each "
    "row's notes), renames the 5 course milestones, and collapses the outline to level 1. "
    "Expand (Outline -> Show Subtasks) to see every detail task and predecessor. "
    "The green arrows on milestone rows are the Deadline field (contract/check dates), "
    "which is not the same thing as a plan date."
)
mp.CalculateAll()

try:
    mp.FileSave()
    log("saved (%d bytes)" % os.path.getsize(OUT))
except Exception as exc:
    log("FileSave failed: %s %s" % (type(exc).__name__,
                                    str(exc).splitlines()[0][:80]))
mp.FileCloseEx(0)
mp.Quit()

# ---- read back from disk and audit
mp2 = w32.DispatchEx("MSProject.Application")
mp2.Visible = False
mp2.DisplayAlerts = 0
mp2.FileOpen(OUT, True)
q2 = mp2.ActiveProject
back = snap(q2)
audit = {
    "tasks": back["tasks"], "summaries": len(back["summaries"]),
    "milestones": len(back["milestones"]), "links": back["links"],
    "assignments": back["assignments"],
    "summaryRollupDrift": drift_of(base, back)[:8],
    "renamedSummaries": renamed_s, "renamedMilestones": renamed_m,
    "missingOriginalNames": missing_orig,
    "summaryNamesEN": [v["name"] for k, v in sorted(back["summaries"].items(),
                                                    key=lambda kv: int(kv[0]))],
    "milestoneDatesKept": all(
        back["milestones"].get(k, {}).get("start") == v["start"]
        and back["milestones"].get(k, {}).get("finish") == v["finish"]
        and back["milestones"].get(k, {}).get("deadline") == v["deadline"]
        for k, v in base["milestones"].items()),
}
mp2.FileCloseEx(0)
mp2.Quit()
audit["frozenTwinUnchanged"] = sha(SRC) == src_before
audit["sha256_16"] = sha(OUT, 16)
audit["bytes"] = os.path.getsize(OUT)
log("read back: " + json.dumps(audit, ensure_ascii=False)[:900])
json.dump({"audit": audit, "base": base, "back": back},
          open(os.path.join(HERE, "se_r43_project_en_r1.json"), "w",
               encoding="utf-8"), indent=1, ensure_ascii=False, default=str)

bad = []
if not audit["frozenTwinUnchanged"]:
    bad.append("frozen zh twin digest changed")
if audit["tasks"] != base["tasks"]:
    bad.append("task count changed %d -> %d" % (base["tasks"], audit["tasks"]))
if audit["links"] != base["links"]:
    bad.append("dependency records changed %d -> %d"
               % (base["links"], audit["links"]))
if audit["assignments"] != base["assignments"]:
    bad.append("assignments changed %d -> %d"
               % (base["assignments"], audit["assignments"]))
if audit["summaryRollupDrift"]:
    bad.append("summary rollups drifted: %s" % audit["summaryRollupDrift"][:3])
if not audit["milestoneDatesKept"]:
    bad.append("milestone dates or deadlines moved")
if renamed_s != len(base["summaries"]):
    bad.append("only %d/%d summaries renamed" % (renamed_s, len(base["summaries"])))
if bad:
    log("REFUSED: " + "; ".join(bad))
    sys.exit(1)
log("PROJECT EN BUILD OK: %d tasks, %d summaries renamed, %d milestones renamed, "
    "%d links, %d assignments"
    % (audit["tasks"], renamed_s, renamed_m, audit["links"], audit["assignments"]))
LOG.close()
sys.exit(0)
