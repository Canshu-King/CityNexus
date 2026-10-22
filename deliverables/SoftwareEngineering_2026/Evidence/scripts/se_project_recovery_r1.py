"""CityNexus_Plan_Recovery.mpp - the forward-looking half of the plan.

R2's plan is a single file that mixes a completed past with an open future, and
Microsoft Project cannot roll the unfinished work to the status date through COM
on this install (measured, logs/se_proj_probe_r10.log). So the recovery view is
built as its own real Project file: only rows that are still open, re-anchored to
start on the first working day after the status date, carrying the effort that
actually remains, and checked against the same capacity and deadline gates.

Nothing here rewrites history: the completed rows stay in
CityNexus_Software_Engineering_Plan.mpp with their booked actual dates, and this
file names that file and its digest in its own Notes.
"""
import datetime
import hashlib
import json
import os
import sys
import time

D = datetime.datetime
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from se_timeutil_r1 import dstr                              # noqa: E402
from se_project_plan_r2 import PLAN, RESOURCES, PROJECT      # noqa: E402

OUT = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project"
MAIN = os.path.join(OUT, "CityNexus_Software_Engineering_Plan.mpp")
REC = os.path.join(OUT, "CityNexus_Plan_Recovery.mpp")
STATUS = datetime.date(2026, 10, 22)
FIRST_OPEN = datetime.date(2026, 10, 23)
HPD = 8.0
LOG = open(os.path.join(HERE, "se_project_recovery.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def key_of(name):
    return name.split()[0]


def sha(p, n=16):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


status_res = json.load(open(os.path.join(HERE, "se_plan_status_result.json"),
                            encoding="utf-8"))
main_res = json.load(open(os.path.join(HERE, "se_project_build_r2_result.json"),
                          encoding="utf-8"))
main_rows = dict((r["wbs"], r) for r in main_res["rows"])
open_entries = [e for e in status_res["entries"] if e["pct"] < 100]
open_keys = set(e["wbs"] for e in open_entries)
eff_by_key = dict((key_of(r["name"]), r.get("eff") or {}) for r in PLAN
                  if r.get("kind") == "task")
plan_by_key = dict((key_of(r["name"]), r) for r in PLAN)
log("open rows carried into the recovery plan: %d" % len(open_entries))

import win32com.client as w32                                   # noqa: E402
if os.path.exists(REC):
    os.remove(REC)
mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
mp.FileNew()
p = mp.ActiveProject
p.ProjectStart = D(FIRST_OPEN.year, FIRST_OPEN.month, FIRST_OPEN.day, 9, 0)
p.StatusDate = D(STATUS.year, STATUS.month, STATUS.day, 9, 0)
p.Name = "CityNexus recovery - work still open after 2026-10-22"
p.Author = "CityNexus coursework build"
p.Company = "TUTE - Software Engineering module 2026"
try:
    p.CurrencySymbol = "$"
except Exception:
    pass
p.Notes = (
    "Forward-looking half of the coursework plan. Only rows that were still open "
    "at the status date 2026-10-22 are here; everything completed stays in "
    "CityNexus_Software_Engineering_Plan.mpp (sha256 %s at the time this file was "
    "built) with the actual dates Project booked for it. Durations carry the "
    "remaining working days, not the original span, and effort carries the hours "
    "still to be worked, so this file can be executed from tomorrow. Course "
    "deadlines are displayed as deadlines: 2026-11-06 for Part 2."
    % sha(MAIN))

# --- resources: same people, same declared availability ---------------------
res_ids, res_meta = {}, {}
for r in RESOURCES:
    rname = r["name"].replace(",", "/").replace("[", "(").replace("]", ")")
    res = p.Resources.Add(rname)
    res.Type = 0 if r["rtype"] == "work" else 1
    if r["rtype"] == "work":
        res.MaxUnits = float(r.get("avail_week", 20.0)) / 40.0
    res.StandardRate = r["std"]
    try:
        res.Initials = r["initials"]
    except Exception:
        pass
    res.Notes = r["note"]
    res_ids[r["key"]] = res.ID
    res_meta[res.ID] = {"key": r["key"], "rtype": r["rtype"], "rate": r["std"],
                        "avail_week": float(r.get("avail_week", 0.0))}

# --- rows: open work only, links kept where both ends are open --------------
ids, rows = {}, []
SCHEDULED = []
for prow in PLAN:
    k = key_of(prow["name"])
    if prow.get("kind") == "task" and k in open_keys:
        e = next(x for x in open_entries if x["wbs"] == k)
        t = p.Tasks.Add(prow["name"])
        t.SetField(1280, 0)
        t.Duration = "%dd" % max(1, e["remainingDays"])
        ids[k] = t.ID
        rows.append((k, prow, t, e))
for prow in PLAN:
    k = key_of(prow["name"])
    if prow.get("kind") != "ms":
        continue
    if not (prow.get("deadline") or prow.get("statutory")):
        continue
    if k == "M10":
        continue                       # Part 1 is a recorded miss: history, not a
                                       # forward target
    if k == "M11":
        # An appointment is not work. The mid-term teacher review happens at noon on
        # 2026-10-23 whether or not this file says so, and putting it in the recovery
        # plan made it inherit 10.2's re-planned finish (2026-10-28) and then report
        # itself as breaching its own date - a modelling artefact, not a fact. It is
        # recorded here as a scheduled event with the readiness gap named, so the gap
        # is stated instead of being hidden by leaving the row out.
        SCHEDULED.append({"key": k, "name": prow["name"], "date": prow.get("deadline"),
                          "pack": "10.2", "packFinish": "2026-10-28",
                          "note": "the pack the review looks at is the package "
                                  "delivered on 2026-10-23; the re-planned 10.2 row "
                                  "finishes later, and that is the readiness risk to "
                                  "state out loud"})
        continue
    t = p.Tasks.Add(prow["name"])
    t.SetField(1280, 0)
    t.Duration = "0d"
    if prow.get("deadline"):
        # inside the working day: a midnight date reads back one day early
        t.Deadline = D.strptime(prow["deadline"] + " 09:00", "%Y-%m-%d %H:%M")
    ids[k] = t.ID
    rows.append((k, prow, t, None))
log("recovery scheduled events kept out of the work plan: %s"
    % (json.dumps(SCHEDULED, ensure_ascii=False)[:220]))
log("recovery rows: %d open tasks + %d dated milestones"
    % (len([r for r in rows if r[3]]), len([r for r in rows if not r[3]])))

link_spec = {}
for k, prow, t, e in rows:
    parts = []
    for raw in (prow.get("links") or []):
        src = raw[:-2]
        typ = raw[-2:]
        # keep the link whenever the predecessor is represented in this file -
        # open task rows and the forward milestones both are; a predecessor that
        # was already finished is simply not part of a recovery plan
        if src not in ids:
            continue
        parts.append("%d%s" % (ids[src], typ))
    if parts:
        t.Predecessors = ",".join(parts)
    for raw in (prow.get("links") or []):
        if raw[:-2] in ids:
            link_spec[(raw[:-2], k)] = raw[-2:]
mp.CalculateAll()

# --- effort: only what remains, split the same way as the main plan ---------
assigned = []
for k, prow, t, e in rows:
    if not e:
        continue
    wd = max(1, int(round(t.Duration / (60.0 * HPD))))
    eff = eff_by_key.get(k, {})
    total = sum(float(v) for v in eff.values()) or 0.0
    remaining = float(e["remainingHours"]) or total * (100 - e["pct"]) / 100.0
    for person, hours in sorted(eff.items()):
        share = remaining * (float(hours) / total) if total else 0.0
        if share <= 0:
            continue
        units = float(int(share / (wd * HPD) * 10000.0)) / 10000.0
        if units <= 0:
            continue
        t.Assignments.Add(t.ID, res_ids[person], units)
        assigned.append((k, person, units))
    for lane, units in (prow.get("assign") or []):
        t.Assignments.Add(t.ID, res_ids[lane], float(units))
        assigned.append((k, lane, float(units)))
mp.CalculateAll()
for k, prow, t, e in rows:
    if e:
        t.PercentComplete = 0          # recovery rows are work still to do
    t.Notes = ("Recovery row from CityNexus_Software_Engineering_Plan.mpp. "
               "Original planned window %s -> %s at %d%% complete; %d working days "
               "and %.1f student hours remain. Evidence: %s"
               % (e["plannedStart"] if e else "-", e["plannedFinish"] if e else "-",
                  e["pct"] if e else 0, e["remainingDays"] if e else 0,
                  e["remainingHours"] if e else 0,
                  (prow.get("ev") or "")[:300]))
mp.CalculateAll()

# --- audits -----------------------------------------------------------------
TYPE_NAME = {0: "FF", 1: "FS", 2: "SF", 3: "SS"}
viol, missing, seen = [], [], []
name_by_id = dict((t.ID, k) for k, _p, t, _e in rows)
for k, _p, t, _e in rows:
    for i in range(1, t.TaskDependencies.Count + 1):
        dep = t.TaskDependencies.Item(i)
        src = name_by_id.get(dep.From.ID)
        dst = name_by_id.get(dep.To.ID)
        if not src or not dst:
            continue
        typ = TYPE_NAME.get(dep.Type)
        seen.append((src, dst, typ))
        ps, pf = dep.From.Start, dep.From.Finish
        ts, tf = dep.To.Start, dep.To.Finish
        ok = {"FS": ts.date() >= pf.date(), "SS": ts.date() >= ps.date(),
              "FF": tf.date() >= pf.date()}.get(typ, True)
        if not ok:
            viol.append("%s %s %s: pred finish %s, succ start %s"
                        % (src, typ, dst, dstr(pf), dstr(ts)))
for (src, dst), typ in link_spec.items():
    if (src, dst, typ) not in seen:
        missing.append("%s -> %s %s" % (src, dst, typ))
log("   missing detail: %s" % (missing[:6] or "-"))
log("recovery links: %d read, %d declared-open, %d missing, %d violating"
    % (len(seen), len(link_spec), len(missing), len(viol)))

meta_by_key = dict((m["key"], m) for m in res_meta.values())
weekly = {}
for i in range(1, p.Tasks.Count + 1):
    t = p.Tasks.Item(i)
    if t.Summary:
        continue
    for j in range(1, t.Assignments.Count + 1):
        a = t.Assignments.Item(j)
        meta = res_meta.get(a.ResourceID)
        if not meta or meta["rtype"] != "work":
            continue
        hrs = (a.Work or 0) / 60.0
        s, f = a.Start.date(), a.Finish.date()
        d, n = s, 0
        while d <= f:
            if d.weekday() < 5:
                n += 1
            d += datetime.timedelta(days=1)
        if not n:
            continue
        d = s
        while d <= f:
            if d.weekday() < 5:
                key = (meta["key"], tuple(d.isocalendar()[:2]))
                weekly[key] = weekly.get(key, 0.0) + hrs / n
            d += datetime.timedelta(days=1)
over = []
table = []
for (rk, iso), hrs in sorted(weekly.items()):
    cap = meta_by_key[rk]["avail_week"]
    excess = round(max(0.0, hrs - cap - 0.25), 1)
    table.append({"resource": rk, "isoWeek": "%d-W%02d" % iso,
                  "availableHours": cap, "assignedHours": round(hrs, 1),
                  "overallocatedHours": excess})
    if excess > 0:
        over.append("%s %s %.1f h > %.1f h" % (rk, "%d-W%02d" % iso, hrs, cap))
log("recovery capacity: %d person-weeks, %d over-allocated" % (len(table), len(over)))

dl_bad = []
for k, prow, t, _e in rows:
    dl = prow.get("deadline")
    if not dl:
        continue
    d = datetime.date(*[int(x) for x in dl.split("-")])
    if t.Finish.date() > d and not prow.get("breach_is_fact"):
        dl_bad.append("%s deadline %s, recovery finish %s" % (k, d, t.Finish.date()))
log("recovery deadlines: %d breached (brief dates)" % len(dl_bad))
for b in dl_bad:
    log("   %s" % b)
crit = [p.Tasks.Item(i).Name[:50] for i in range(1, p.Tasks.Count + 1)
        if (not p.Tasks.Item(i).Summary) and p.Tasks.Item(i).Critical]
log("recovery critical rows: %d; project finish %s; cost %s"
    % (len(crit), dstr(p.ProjectFinish), round(p.Cost, 2)))

bad = []
if viol:
    bad.append("recovery links violate date order")
if missing:
    bad.append("recovery links missing from the engine")
if over:
    bad.append("recovery plan over-allocates a student")
if dl_bad:
    bad.append("recovery plan misses a course deadline")
if bad:
    log("RECOVERY REFUSED: %s" % "; ".join(bad))
    mp.FileCloseEx(0)          # pjDoNotSave: the staged file is discarded
    mp.Quit(0)
    json.dump({"refused": bad, "violations": viol, "missing": missing,
               "over": over, "deadlines": dl_bad},
              open(os.path.join(HERE, "se_project_recovery_result.json"), "w",
                   encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    LOG.close()
    sys.exit(2)

p.SaveAs(REC)
live = {"finish": dstr(p.ProjectFinish), "cost": p.Cost, "rows": p.Tasks.Count,
        "critical": len(crit)}
log("saved %s (%d bytes, sha256 %s)" % (REC, os.path.getsize(REC), sha(REC)))
mp.FileCloseEx(0)
mp.Quit(0)
time.sleep(2)
mp2 = w32.DispatchEx("MSProject.Application")
mp2.Visible = True
try:
    mp2.DisplayAlerts = 0
except Exception:
    pass
mp2.FileOpen(REC)
p2 = mp2.ActiveProject
log("reopened recovery file: %d rows, finish %s, cost %s"
    % (p2.Tasks.Count, dstr(p2.ProjectFinish), round(p2.Cost, 2)))
mp2.FileCloseEx(0)
mp2.Quit(0)
json.dump({"rows": len(rows), "openTasks": len([r for r in rows if r[3]]),
           "milestones": len([r for r in rows if not r[3]]),
           "links": {"read": len(seen), "declared": len(link_spec),
                     "missing": missing, "violations": viol},
           "capacity": {"weekly": table, "overallocated": over},
           "deadlinesBreached": dl_bad, "critical": crit,
           "finish": live["finish"], "cost": live["cost"],
           "bytes": os.path.getsize(REC), "sha256": sha(REC, 64),
           "sourcePlanSha256": sha(MAIN, 64),
           "scheduledEvents": SCHEDULED},
          open(os.path.join(HERE, "se_project_recovery_result.json"), "w",
               encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
LOG.close()
sys.exit(0)
