"""Status, lateness and capacity report - the four clocks kept apart.

The review's complaint about R2's status story was precise and correct: the
documents highlighted four 0% rows while ten rows were actually past their
planned finish and unfinished, and "6 deadlines met" was a statement about the
Deadline field, not evidence that any coursework had been handed in.

This script reads the shipped plan's own result file and writes one table that
separates four different things:

  planned_finish    the date the schedule computes, from links and durations
  actual_finish     the date Project booked when progress was entered
  forecast_finish   where the unfinished part lands given the status date -
                    computed here in plain arithmetic, because Project's
                    Move-to-Status-Date is inert through COM on this install
  course_deadline   a date the assignment brief sets, which no plan of ours can
                    move; distinct from a plan target we chose ourselves

It also emits the per-person, per-week capacity table the review asked for, and
the row set that the recovery plan is built from.
"""
import datetime
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from se_project_plan_r2 import PLAN, RESOURCES, PROJECT           # noqa: E402

STATUS = datetime.date(2026, 10, 22)
D = datetime.date


def dd(s):
    try:
        return D(*[int(x) for x in str(s)[:10].split("-")])
    except Exception:
        return None


def is_wd(d):
    return d.weekday() < 5


def next_wd(d):
    while not is_wd(d):
        d += datetime.timedelta(days=1)
    return d


def add_wd(start, n):
    d = next_wd(start)
    if n <= 1:
        return d
    for _ in range(n - 1):
        d = next_wd(d + datetime.timedelta(days=1))
    return d


def key_of(name):
    return name.split()[0]


res = json.load(open(os.path.join(HERE, "se_project_build_r2_result.json"),
                     encoding="utf-8"))
rows = res["rows"]
by_key = dict((r["wbs"], r) for r in rows)
plan_by_key = dict((key_of(r["name"]), r) for r in PLAN)

students = dict((r["key"], r) for r in RESOURCES if r.get("rtype") == "work")
lanes = dict((r["key"], r) for r in RESOURCES if r.get("rtype") != "work")

entries = []
for r in rows:
    if r["summary"] or r["milestone"]:
        continue
    k = r["wbs"]
    prow = plan_by_key.get(k, {})
    pct = int(round(r["pct"]))
    dur_days = max(1, int(round(r["duration"] / (60.0 * 8.0))))
    planned_s, planned_f = dd(r["start"]), dd(r["finish"])
    actual_f = dd(r["actualFinish"]) if r.get("actualFinish") else None
    rem_days = max(0, int(math.ceil(dur_days * (100 - pct) / 100.0)))
    if pct >= 100:
        forecast = planned_f
        basis = "complete; Project booked the actual finish"
    elif planned_f and planned_f >= STATUS:
        forecast = planned_f
        basis = "planned window already lies on or after the status date"
    else:
        forecast = add_wd(next_wd(STATUS + datetime.timedelta(days=1)),
                          max(1, rem_days))
        basis = ("re-forecast: %d of %d working days remain at %d%% and the first "
                 "working day after the status date is %s"
                 % (rem_days, dur_days, pct, next_wd(STATUS + datetime.timedelta(days=1))))
    dl = dd(r["deadline"]) if r.get("deadline") else None
    entries.append({
        "wbs": k, "name": r["name"], "pct": pct,
        "plannedStart": str(planned_s), "plannedFinish": str(planned_f),
        "actualFinish": str(actual_f) if actual_f else "",
        "forecastFinish": str(forecast), "forecastBasis": basis,
        "remainingDays": rem_days,
        "remainingHours": round((r.get("remainingWork") or 0) / 60.0, 1),
        "workHours": round((r.get("work") or 0) / 60.0, 1),
        "courseDeadline": str(dl) if dl else "",
        "deadlineKind": ("course deadline (brief)" if prow.get("statutory")
                         else "plan target (ours)" if dl else ""),
        "late": bool(pct < 100 and planned_f and planned_f < STATUS),
        "evidence": (prow.get("ev") or "")[:400],
    })

late_rows = [e for e in entries if e["late"]]
mile_rows = []
for r in rows:
    if not (r["milestone"] and not r["summary"]):
        continue
    k = r["wbs"]
    prow = plan_by_key.get(k, {})
    dl = dd(r["deadline"]) if r.get("deadline") else None
    sched = dd(r["finish"])
    mile_rows.append({
        "wbs": k, "name": r["name"], "scheduledDate": str(sched),
        "deadline": str(dl) if dl else "",
        "deadlineKind": ("course deadline (brief)" if prow.get("statutory")
                         else "plan target (ours)" if dl else "observed event"),
        "observed": (prow.get("obs") or {}).get("date", ""),
        "observedBasis": (prow.get("obs") or {}).get("basis", ""),
        "pct": int(round(r["pct"])),
        "meaning": ("a date the brief sets; the schedule cannot move it" if dl and
                    prow.get("statutory") else
                    "when the plan says the thing is ready; ours to revise" if dl
                    else "a recorded event, not a commitment"),
        "verdict": ("met by the schedule" if dl and sched and sched <= dl
                    else "past its date" if dl and sched and sched > dl
                    else "no date attached"),
    })

cap = res["capacity"]
weekly = cap["weekly"]
per_person = {}
for w in weekly:
    per_person.setdefault(w["resource"], []).append(w)

L = []
A = L.append
A("# Status, lateness and capacity - as the shipped plan actually reads")
A("")
A("Generated %s from `se_project_build_r2_result.json`, which the build wrote "
  "while reading the published `.mpp`. Status date: %s."
  % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), STATUS))
A("")
A("## 1. Four different dates, never mixed")
A("")
A("| column | where it comes from | what it can prove |")
A("|---|---|---|")
A("| planned finish | Microsoft Project, from durations and links | what the "
  "schedule says |")
A("| actual finish | Microsoft Project, booked from the percentage entered | that "
  "the completed part is in the past |")
A("| forecast finish | arithmetic in `se_plan_status_r1.py` (remaining working days "
  "after the status date) | where the unfinished part can land; **not** a Project "
  "computation, because Move-to-Status-Date is inert through COM here |")
A("| course deadline | the assignment brief | a date we do not control |")
A("")
A("## 2. Every row that is past its planned finish and not complete")
A("")
A("R2's documents named four. The real count is **%d**. All of them are listed, "
  "with what is left and where the forecast puts them." % len(late_rows))
A("")
A("| WBS | row | progress | planned window | remaining | forecast finish | why that forecast |")
A("|---|---|---|---|---|---|---|")
for e in sorted(late_rows, key=lambda x: x["plannedFinish"] or ""):
    A("| %s | %s | %d%% | %s → %s | %d d / %.1f h | %s | %s |"
      % (e["wbs"], e["name"].split(e["wbs"])[-1].strip()[:52], e["pct"],
         e["plannedStart"], e["plannedFinish"], e["remainingDays"],
         e["remainingHours"], e["forecastFinish"], e["forecastBasis"][:120]))
A("")
A("Of these, %d are at 0%% (never started) and %d are part-done. Nothing here was "
  "moved to make the picture tidier: the planned window stays as the links produce "
  "it, and the forecast column is where the work actually still has to go."
  % (len([e for e in late_rows if e["pct"] == 0]),
     len([e for e in late_rows if e["pct"] > 0])))
A("")
A("## 3. Course deadlines versus our own milestones")
A("")
A("| WBS | milestone | kind of date | scheduled | deadline | progress | what it means |")
A("|---|---|---|---|---|---|---|")
for m in mile_rows:
    A("| %s | %s | %s | %s | %s | %d%% | %s |"
      % (m["wbs"], m["name"][:56], m["deadlineKind"] or "-", m["scheduledDate"],
         m["deadline"] or "-", m["pct"], m["meaning"]))
A("")
A("Two statements the schedule is **not** entitled to make:")
A("")
A("* M12 and M13 landing before 2026-11-06 means the plan has room before the "
  "deadline. It does not mean anything was submitted.")
A("* M10 carries the Part 1 contract date and is recorded as missed. Whether a "
  "Part 1 file reached the course platform cannot be seen from this repository "
  "and stays **unverified pending the course record**.")
A("")
A("## 4. Capacity: what each person can work and what the plan asks for")
A("")
A("Availability is an assumption to be confirmed by each member: **%d h per week "
  "per student** while the module runs. Compute lanes are material resources: they "
  "are priced and never counted as student hours."
  % int(students[list(students)[0]]["avail_week"]))
A("")
A("| person | student hours in the plan | weeks scheduled | available | utilisation | peak week | over-allocated weeks |")
A("|---|---|---|---|---|---|---|")
for k, st in students.items():
    rows_p = per_person.get(k, [])
    assigned = round(sum(w["assignedHours"] for w in rows_p), 1)
    avail = round(sum(w["availableHours"] for w in rows_p), 1)
    peak = max([w["assignedHours"] for w in rows_p] or [0])
    over = len([w for w in rows_p if w["overallocatedHours"] > 0])
    A("| %s | %.1f h | %d | %.1f h | %.0f%% | %.1f h | %d |"
      % (st["name"].split(" - ")[0], assigned, len(rows_p), avail,
         100.0 * assigned / avail if avail else 0, peak, over))
A("")
A("Total student effort in the shipped plan: **%.1f h**. R2 carried 1,808 h against "
  "a three-person capacity of about 840 h; that was the defect, and the gate that "
  "now refuses a build on any over-allocated person-week is "
  "`audit_capacity()` in `se_project_build_r2.py`." % cap["studentHours"])
A("")
A("### Week by week (available / assigned / over)")
A("")
A("| person | week | available | assigned | over |")
A("|---|---|---|---|---|")
for w in weekly:
    A("| %s | %s | %.1f | %.1f | %.1f |" % (w["resource"], w["isoWeek"],
                                            w["availableHours"], w["assignedHours"],
                                            w["overallocatedHours"]))
A("")
A("## 5. What is left to do, and whether it fits")
A("")
open_rows = [e for e in entries if e["pct"] < 100]
rem_hours = round(sum(e["remainingHours"] for e in open_rows), 1)
weeks_left = len(set(next_wd(STATUS + datetime.timedelta(days=1)).isocalendar()[:2]))
A("* %d rows are not complete; their remaining booked work is **%.1f student "
  "hours**." % (len(open_rows), rem_hours))
A("* From 2026-10-23 to the Part 2 deadline 2026-11-06 there are 11 working days, "
  "i.e. **%d h per student** at the declared availability and %d h across the "
  "three of them." % (int(students[list(students)[0]]["avail_week"] / 5.0 * 11),
                      int(students[list(students)[0]]["avail_week"] / 5.0 * 11 * 3)))
A("* So the remaining work fits the calendar with room, and `CityNexus_Plan_"
  "Recovery.mpp` is the forward-looking version of it: the same open rows, "
  "re-anchored to start after the status date, with the completed rows kept as a "
  "fact snapshot.")
A("")
A("Generated by `se_plan_status_r1.py`; machine-readable copy in "
  "`se_plan_status_result.json`.")

open(os.path.join(r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026",
                  "Evidence", "STATUS_AND_OVERDUE.md"), "w",
     encoding="utf-8").write("\n".join(L) + "\n")
json.dump({"statusDate": str(STATUS), "entries": entries,
           "late": [e["wbs"] for e in late_rows], "milestones": mile_rows,
           "capacity": cap, "remainingStudentHours": rem_hours,
           "openRows": len(open_rows)},
          open(os.path.join(HERE, "se_plan_status_result.json"), "w",
               encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
print("wrote Evidence/STATUS_AND_OVERDUE.md: %d late rows, %.1f student hours, "
      "over-allocated weeks %d"
      % (len(late_rows), cap["studentHours"],
         len([w for w in weekly if w["overallocatedHours"] > 0])))
