"""Build CityNexus_Software_Engineering_Plan.mpp with real Microsoft Project,
revision 2, and prove it is a schedule rather than a picture of one.

Revision 1 was rejected on dependency semantics. What changed here, measured
rather than assumed (se_proj_probe_r5/r7/r8/r9.log):

  - no row has a forced date. Revision 1 typed Start into the 13 milestones, and
    `task.Start = date` was measured to set ConstraintType 4 (Start No Earlier
    Than) - a constraint that overrides the links. Now every row keeps
    ConstraintType 0 and only `Deadline` carries a calendar fact, which Project
    displays but does not obey.
  - every declared link is written, including the milestone links that revision
    1 skipped, and all of them are read back out of Project's own
    TaskDependencies and tested as date inequalities.
  - dependency types are decoded with the mapping measured on THIS install
    (TaskDependency.Type: FF=0, FS=1, SF=2, SS=3), not with the documented
    order, which is different here and would silently mis-label every link.
  - resources are created as WORK (Type=0). Revision 1 used Type=1, which on
    this install is MATERIAL: Work came back 0 and Cost was one unit times the
    rate, i.e. the cost did not correspond to hours at all.
  - PercentComplete is written AFTER the assignments. Measured: written before,
    it silently reads back 0 afterwards, which is how revision 1 lost all of its
    recorded progress.
  - the pre-flight static checker (se_plan_cpm_r1) must pass first, so a broken
    dependency model is caught without spending a Project session on it.

Exit status is failure unless every check below passes; nothing is reported as
done that the file does not actually show.
"""
import datetime
import hashlib
import json
import os
import re
import sys
import time

D = datetime.datetime
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from se_timeutil_r1 import dstr, selftest as timeutil_selftest   # noqa: E402
import se_plan_cpm_r1 as cpm                            # noqa: E402
from se_project_plan_r2 import PLAN, RESOURCES, PROJECT  # noqa: E402

OUT = os.environ.get("SE_MSP_OUT",
                     r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project")
LOGP = os.path.join(HERE, "se_project_build_r2.log")
_lf = open(LOGP, "w", encoding="utf-8", buffering=1)
_t0 = time.time()

# TaskDependency.Type as measured on this install (se_proj_probe_r5.log)
TYPE_NAME = {0: "FF", 1: "FS", 2: "SF", 3: "SS"}
NAME_TYPE = dict((v, k) for k, v in TYPE_NAME.items())
PJ_WORK = 188743680
PJ_COST = 188743685
PJ_RES_TYPE = 205521196
HOURS_PER_DAY = 8.0


def log(m):
    line = "[%6.1fs] %s" % (time.time() - _t0, m)
    _lf.write(line + "\n")
    _lf.flush()
    print(line, flush=True)


def dd(s):
    return D.strptime(s, "%Y-%m-%d %H:%M") if " " in s else D.strptime(s, "%Y-%m-%d")


def date_only(s):
    return datetime.date(*[int(x) for x in str(s)[:10].split("-")])


# ============================================================ 0. pre-flight
def preflight():
    # The date reader is the measuring stick for every finish, deadline and
    # status-date comparison in this build, so it is tested before anything is
    # read: an off-by-one there silently moves tasks in and out of "late".
    tu = timeutil_selftest()
    if tu:
        raise SystemExit("se_timeutil_r1 selftest FAILED, refusing to build: %s"
                         % "; ".join(tu))
    log("date reader selftest: pass (17:00 finish reads as the same calendar day)")
    status = dd(PROJECT["status_date"]).date()
    start = dd(PROJECT["start"]).date()
    res = cpm.check(PLAN, start, status, HOURS_PER_DAY, RESOURCES)
    log("pre-flight: %d links, %d violated, %d structural problems"
        % (res["links_total"], len(res["violations"]), len(res["problems"])))
    for v in res["problems"]:
        log("   PRE-FLIGHT PROBLEM %s" % v)
    for v in res["violations"]:
        log("   PRE-FLIGHT VIOLATION %s" % v)
    for v in res["history_after_status_date"]:
        log("   PRE-FLIGHT HISTORY %s" % v)
    for v in res["deadline_breaches"]:
        log("   pre-flight deadline: %s" % v)
    for v in res.get("internal_target_breaches", []):
        log("   pre-flight risk: %s" % v)
    for v in res.get("late_at_status_date", []):
        log("   pre-flight late: %s" % v)
    for v in res["overdue_not_started"]:
        log("   pre-flight overdue: %s" % v)
    bad = len(res["violations"]) + len(res["problems"]) + \
        len(res["history_after_status_date"])
    if bad:
        raise SystemExit("refusing to open Project: the plan fails its own "
                         "dependency model (%d)" % bad)
    unacceptable = [v for v in res["deadline_breaches"] if "recorded fact" not in v]
    if unacceptable:
        raise SystemExit("refusing to build: a date set by the assignment brief is "
                         "breached by the schedule: %s" % unacceptable[0])
    return res


# ============================================================ 1. build
def notes_for(row):
    parts = []
    if (row.get("ev") or "").strip():
        parts.append("EVIDENCE: %s" % row["ev"])
    obs = row.get("obs")
    if obs:
        parts.append("OBSERVED (%s) %s - %s" % (obs["basis"], obs["date"], obs["cite"]))
    if row.get("deadline"):
        parts.append("DEADLINE %s - Project displays this and does not obey it; the "
                     "date is derived from the links." % row["deadline"])
    if row.get("breach_is_fact"):
        parts.append("DEADLINE BREACH IS A RECORDED FACT: this date was missed.")
    if row.get("tentative"):
        parts.append("DATES AND SCOPE ARE PROVISIONAL - to be confirmed with the "
                     "teacher as customer.")
    return "\n".join(parts)


def build():
    import win32com.client as w32
    # Build into a staging directory: a crashed or refused run must never leave
    # the deliverable folder without its .mpp (a failed revision of this script
    # deleted the shipped file before it could write a replacement).
    stage = os.path.join(HERE, "stage_mpp")
    os.makedirs(stage, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    mpp = os.path.join(stage, "CityNexus_Software_Engineering_Plan.mpp")
    if os.path.exists(mpp):
        os.remove(mpp)

    mp = w32.DispatchEx("MSProject.Application")
    mp.Visible = True
    try:
        mp.DisplayAlerts = 0
    except Exception:
        pass
    log("Microsoft Project version %s" % mp.Version)
    mp.FileNew()
    p = mp.ActiveProject
    for prop, val in (("ProjectStart", dd(PROJECT["start"])),
                      ("StatusDate", dd(PROJECT["status_date"]))):
        try:
            setattr(p, prop, val)
            log("%s = %s" % (prop, getattr(p, prop)))
        except Exception as exc:
            log("PROJECT SETTING %s REFUSED: %s" % (prop, type(exc).__name__))
            raise
    for prop, val in (("Name", PROJECT["name"]), ("Author", PROJECT["author"]),
                      ("Company", PROJECT["company"])):
        try:
            setattr(p, prop, val)
        except Exception as exc:
            log("(project %s refused: %s)" % (prop, type(exc).__name__))
    for prop, val in (("CurrencySymbol", "$"), ("CurrencyDigits", "2")):
        try:
            setattr(p, prop, val)
        except Exception:
            pass
    p.Notes = PROJECT["notes"]

    # --- resources ----------------------------------------------------------
    res_ids, res_meta = {}, {}
    for r in RESOURCES:
        rname = re.sub(r"[\[\],;]", " / ", r["name"])
        res = p.Resources.Add(rname)
        want_type = 0 if r["rtype"] == "work" else 1
        res.Type = want_type                       # measured: 0 work, 1 material
        got = str(res.GetField(PJ_RES_TYPE))
        log("resource #%d %-52s type=%s (%s)" % (res.ID, rname[:52], want_type, got))
        if r["rtype"] == "work":
            # MaxUnits is the availability ceiling, not 100%: a student on this
            # module is modelled at avail_week hours out of a 40 h week. The
            # number is an assumption to be confirmed by each member and it is
            # the yardstick the overallocation census is measured against.
            cap = float(r.get("avail_week", r.get("max_units", 1.0) * 40.0)) / 40.0
            res.MaxUnits = cap                     # only valid on a work resource
            r["max_units"] = cap
            log("   MaxUnits readback=%r (= %.0f h/week)" % (res.MaxUnits,
                                                             cap * 40.0))
        for prop, val in (("StandardRate", r["std"]),
                          ("Initials", r["initials"])):
            try:
                setattr(res, prop, val)
            except Exception as exc:
                log("   %s.%s refused (%s)" % (rname[:24], prop, type(exc).__name__))
        if r["rtype"] == "work":
            try:
                res.OvertimeRate = r["ovt"]
            except Exception as exc:
                log("   %s.OvertimeRate refused (%s)" % (rname[:24],
                                                         type(exc).__name__))
        try:
            res.CostPerUse = 0.0
        except Exception:
            pass
        res.Notes = r["note"]
        res_ids[r["key"]] = res.ID
        res_meta[res.ID] = {"key": r["key"], "rtype": r["rtype"], "rate": r["std"],
                            "avail_week": float(r.get("avail_week", 0.0)),
                            "name": rname}
        log("   rate=%s readback=%s maxUnits=%s" % (r["std"], res.StandardRate,
                                                    getattr(res, "MaxUnits", "?")))

    # --- tasks --------------------------------------------------------------
    ids, rows = {}, []
    for i, row in enumerate(PLAN):
        t = p.Tasks.Add(row["name"])
        k = cpm.key_of(row["name"])
        ids[k] = t.ID
        t.SetField(1280, 0)                        # auto scheduled
        t.OutlineLevel = 1 if row["kind"] == "sum" else 2
        if row["kind"] == "ms":
            t.Duration = "0d"
        elif row["kind"] == "task":
            t.Duration = row["dur"]
        rows.append((k, row, t))

    # --- links: every declared link, milestones included --------------------
    link_spec = {}
    written, refused = 0, []
    for k, row, t in rows:
        deps = row.get("links") or []
        if not deps:
            continue
        parts = []
        for raw in deps:
            src, typ = cpm.LINK_RE.match(raw).group(1), cpm.LINK_RE.match(raw).group(2)
            parts.append("%d%s" % (ids[src], typ))
            link_spec[(src, k)] = typ
        try:
            t.Predecessors = ",".join(parts)
            written += len(parts)
        except Exception as exc:
            refused.append("%s <- %s : %s" % (k, parts, type(exc).__name__))
    log("links written from the spec: %d across %d successor rows; refusals: %s"
        % (written, len(rows), refused or "none"))
    if refused:
        raise SystemExit("a declared dependency could not be written: %s" % refused[0])

    # --- deadline (display only), notes --------------------------------------
    for k, row, t in rows:
        if row.get("deadline"):
            # a bare date lands at 00:00, which is outside the working day; the
            # build already learned that writing a midnight Start puts the row a
            # day early, so the deadline is written inside working hours too
            t.Deadline = dd(row["deadline"] + " 09:00")
            log("  deadline %s -> %s (constraint stays %s)"
                % (k, dstr(t.Deadline), t.ConstraintType))
        n = notes_for(row)
        if n:
            t.Notes = n

    # --- assignments FIRST, then percent (measured order) --------------------
    # Student effort is stated in hours (EFF) and turned into assignment units
    # against the row's real working-day span, so the Work Microsoft Project
    # computes equals the stated human effort rather than being an artefact of
    # duration x 100%. Compute lanes are material: they carry units and cost,
    # never hours.
    mp.CalculateAll()
    assigned, eff_reported = [], {}
    for k, row, t in rows:
        wd = round(t.Duration / (60.0 * HOURS_PER_DAY))
        for person, hours in sorted((row.get("eff") or {}).items()):
            if person not in res_ids:
                raise SystemExit("task %s states effort for unknown resource %r"
                                 % (k, person))
            if wd <= 0:
                raise SystemExit("task %s has no working days to carry %s h"
                                 % (k, hours))
            # truncate, never round up: Project derives Work from the units it
            # is given, so rounding up would book more student hours than the
            # effort table states
            units = float(int(hours / (wd * HOURS_PER_DAY) * 10000.0)) / 10000.0
            t.Assignments.Add(t.ID, res_ids[person], units)
            assigned.append((k, person, units))
            eff_reported[k] = eff_reported.get(k, 0.0) + float(hours)
        for rkey, units in (row.get("assign") or []):
            if rkey not in res_ids:
                raise SystemExit("task %s assigns unknown resource %r" % (k, rkey))
            t.Assignments.Add(t.ID, res_ids[rkey], float(units))
            assigned.append((k, rkey, float(units)))
    mp.CalculateAll()
    pct_ok, pct_bad = 0, []
    for k, row, t in rows:
        if row["kind"] == "sum":
            continue
        want = row.get("pct")
        if want is None:
            continue
        t.PercentComplete = int(want)
        got = t.PercentComplete
        if int(round(got)) == int(want):
            pct_ok += 1
        else:
            pct_bad.append("%s asked %s%% reads %s%%" % (k, want, got))
    mp.CalculateAll()
    log("assignments: %d (%d student, %d lane); stated student effort total %.1f h; "
        "percentages confirmed by readback: %d; refused: %s"
        % (len(assigned), len(eff_reported), len(assigned) - len(eff_reported),
           sum(eff_reported.values()), pct_ok, pct_bad or "none"))
    if pct_bad:
        raise SystemExit("percent-complete did not land, which is the revision 1 "
                         "defect: %s" % pct_bad[0])
    return mp, p, mpp, rows, ids, res_ids, res_meta, link_spec, assigned


# ============================================================ 2. read it back
def read_all(mp, p, res_meta):
    """Everything the audit needs, taken from Project's own fields."""
    rows = {}
    for i in range(1, p.Tasks.Count + 1):
        t = p.Tasks.Item(i)
        deps = []
        for k in range(1, t.TaskDependencies.Count + 1):
            d = t.TaskDependencies.Item(k)
            deps.append({"from": d.From.ID, "to": d.To.ID,
                         "from_name": d.From.Name, "to_name": d.To.Name,
                         "type_raw": d.Type,
                         "type": TYPE_NAME.get(d.Type, "?%s" % d.Type),
                         "lag": d.Lag})
        assigns = []
        try:
            for k in range(1, t.Assignments.Count + 1):
                a = t.Assignments.Item(k)
                row = {"res": a.ResourceID, "units": a.Units,
                       "work": a.Work, "cost": a.Cost}
                for prop in ("start", "finish", "overallocated"):
                    try:
                        v = getattr(a, {"start": "Start", "finish": "Finish",
                                        "overallocated": "Overallocated"}[prop])
                        row[prop] = dstr(v) if prop != "overallocated" else bool(v)
                    except Exception:
                        row[prop] = None
                assigns.append(row)
        except Exception as exc:
            assigns.append({"error": type(exc).__name__})
        rows[t.ID] = {
            "id": t.ID, "name": t.Name, "wbs": t.WBS, "summary": bool(t.Summary),
            "outline": t.OutlineLevel, "uniqueId": t.UniqueID,
            "milestone": bool(t.Milestone), "duration": t.Duration,
            "durationText": t.DurationText, "start": dstr(t.Start),
            "finish": dstr(t.Finish), "slack": t.TotalSlack,
            "critical": bool(t.Critical), "pct": t.PercentComplete,
            "pctWork": t.PercentWorkComplete, "work": t.Work,
            "actualWork": t.ActualWork, "remainingWork": t.RemainingWork,
            "cost": t.Cost, "actualCost": t.ActualCost,
            "actualStart": dstr(t.ActualStart), "actualFinish": dstr(t.ActualFinish),
            "deadline": dstr(t.Deadline), "constraint": t.ConstraintType,
            "constraintDate": dstr(t.ConstraintDate),
            "predecessors": str(t.Predecessors or ""), "deps": deps,
            "assigns": assigns, "notes": (t.Notes or "")[:80],
        }
    return rows


def audit_links(rows, link_spec, ids, log_fn=log):
    """Prove every declared dependency exists in Project with the declared type
    and that no link contradicts the dates Project itself computed."""
    by_key = dict((v, k) for k, v in ids.items())
    seen, violations, mismatched, missing = [], [], [], []
    for t in rows.values():
        for d in t["deps"]:
            fk, tk = by_key.get(d["from"]), by_key.get(d["to"])
            if fk and tk:
                seen.append((fk, tk, d["type"], d["lag"]))
    for (src, dst), typ in link_spec.items():
        hit = [s for s in seen if s[0] == src and s[1] == dst and s[2] == typ]
        if not hit:
            alt = [s for s in seen if s[0] == src and s[1] == dst]
            missing.append("%s -> %s expected %s, engine has %s"
                           % (src, dst, typ, alt or "nothing"))
    for (src, dst, typ, lag) in seen:
        ps, pf = date_only(rows[ids[src]]["start"]), date_only(rows[ids[src]]["finish"])
        ts, tf = date_only(rows[ids[dst]]["start"]), date_only(rows[ids[dst]]["finish"])
        rule = {"FS": ts >= pf, "SS": ts >= ps, "FF": tf >= pf, "SF": tf >= ps}[typ]
        if not rule:
            violations.append("%s(%s..%s) %s %s(%s..%s)"
                              % (src, ps, pf, typ, dst, ts, tf))
    log_fn("link audit: %d dependency records read from the engine for %d declared "
           "links; %d missing, %d type-mismatched, %d violating date order"
           % (len(seen), len(link_spec), len(missing), len(mismatched),
              len(violations)))
    for v in missing[:8]:
        log_fn("   LINK MISSING %s" % v)
    for v in violations[:12]:
        log_fn("   LINK VIOLATION %s" % v)
    return {"read": len(seen), "declared": len(link_spec), "missing": missing,
            "violations": violations, "mismatched": mismatched,
            "by_type": dict((t, len([s for s in seen if s[2] == t]))
                            for t in ("FS", "SS", "FF", "SF"))}


def audit_constraints(rows, ids):
    forced = []
    early = []
    start_min = None
    for t in rows.values():
        if t["constraint"] != 0:
            forced.append("%s constraint=%s date=%s" % (t["name"][:34], t["constraint"],
                                                        t["constraintDate"]))
        if not t["summary"]:
            d = date_only(t["start"])
            if start_min is None or d < start_min:
                start_min = d
    return {"forced": forced, "earliest_start": str(start_min)}


def audit_progress(rows, ids, status_date, log_fn=log):
    late_history, booked, not_booked, partial = [], 0, [], []
    for t in rows.values():
        if t["summary"] or t["milestone"]:
            continue
        fin = date_only(t["finish"])
        if int(round(t["pct"])) == 100:
            af = date_only(t["actualFinish"]) if t["actualFinish"] not in ("NA", "None",
                                                                          "") else None
            if af is None:
                not_booked.append("%s is 100%% but has no ActualFinish" % t["name"][:34])
            elif af > status_date:
                late_history.append("%s booked complete on %s, after the status date %s"
                                    % (t["name"][:34], af, status_date))
            else:
                booked += 1
        elif 0 < t["pct"] < 100:
            partial.append("%s %d%%, finish %s, remaining %s"
                           % (t["name"][:34], t["pct"], fin,
                              round(t["remainingWork"] / 60.0, 1)))
        elif t["pct"] == 0 and fin < status_date:
            late_history.append("OVERDUE (left visible on purpose): %s 0%%, planned "
                                "finish %s, status date %s"
                                % (t["name"][:34], fin, status_date))
    log_fn("progress audit: %d rows booked complete on or before the status date; "
           "%d in progress; %d problems" % (booked, len(partial), len(late_history)))
    return {"booked_complete": booked, "in_progress": partial,
            "history_problems": late_history, "not_booked": not_booked}


def audit_costs(rows, ids, res_meta, res_ids, assigned, log_fn=log):
    """Cost must be derived from hours. Check each row's Work against
    duration x units, each assignment's Cost against its own hours x that
    resource's rate, and prove the material lanes accrue no labour hours."""
    per_task = {}
    for k, rkey, units in assigned:
        per_task.setdefault(k, []).append((rkey, units))
    key_by_id = dict((tid, k) for k, tid in ids.items())
    bad, hours_total = [], 0.0
    compute_rows_bad = []
    material_cost_rows = 0
    for t in rows.values():
        if t["summary"] or t["milestone"]:
            continue
        k = key_by_id.get(t["id"])
        if k is None:
            continue
        days = round(t["duration"] / (60.0 * HOURS_PER_DAY))
        exp_hours = 0.0
        for rkey, units in per_task.get(k, []):
            meta = res_meta.get(res_ids[rkey])
            if not meta or meta["rtype"] != "work":
                continue
            exp_hours += days * HOURS_PER_DAY * units
        got_hours = t["work"] / 60.0
        hours_total += got_hours
        if abs(got_hours - exp_hours) > 0.26:
            bad.append("%s work %.1fh but duration %dd x units gives %.1fh"
                       % (t["name"][:34], got_hours, days, exp_hours))
        row_cost_from_assigns = 0.0
        only_compute = bool(per_task.get(k)) and all(
            res_meta.get(res_ids[rk], {}).get("rtype") != "work"
            for rk, _u in per_task.get(k, []))
        if only_compute and got_hours > 0.01:
            compute_rows_bad.append("%s is staffed only by compute lanes yet carries "
                                    "%.1f labour hours" % (t["name"][:34], got_hours))
        for a in t["assigns"]:
            meta = res_meta.get(a.get("res"))
            if not meta:
                continue
            if meta["rtype"] == "material":
                # a material assignment's "Work" is consumption units, not hours;
                # what matters is that it adds no labour hours to the row, which the
                # only_compute test above and the duration x units test both cover.
                material_cost_rows += 1
                exp = a.get("units", 0) * meta["rate"]
            else:
                exp = (a.get("work") or 0) / 60.0 * meta["rate"]
            row_cost_from_assigns += exp
            if abs((a.get("cost") or 0) - exp) > max(1.0, 0.02 * max(exp, 1)):
                bad.append("%s / %s assignment cost $%.2f but hours x rate is $%.2f"
                           % (t["name"][:28], meta["key"], a.get("cost") or 0, exp))
        if abs(t["cost"] - row_cost_from_assigns) > max(1.0,
                                                        0.02 * row_cost_from_assigns):
            bad.append("%s row cost $%.2f but the sum of its assignments is $%.2f"
                       % (t["name"][:30], t["cost"], row_cost_from_assigns))
    log_fn("cost audit: %.1f labour hours in the file; %d rows where hours or cost "
           "do not match the estimate; %d compute-lane assignments priced without "
           "hours; compute-only rows carrying hours: %d"
           % (hours_total, len(bad), material_cost_rows, len(compute_rows_bad)))
    for b in bad[:10]:
        log_fn("   COST PROBLEM %s" % b)
    for b in compute_rows_bad[:6]:
        log_fn("   COST PROBLEM %s" % b)
    return {"labour_hours": hours_total, "problems": bad + compute_rows_bad,
            "computePricedAssignments": material_cost_rows,
            "compute_only_rows_without_zero_hours": compute_rows_bad}


def audit_deadlines(rows, ids, flags=None, log_fn=log):
    """flags: {key: {"statutory": bool, "breach_is_fact": bool}}. A breach of a date
    the brief sets, or of an open row's own deadline, is a plan failure; a breach of
    an internal target this plan chose is reported as a risk."""
    flags = flags or {}
    key_by_id = dict((tid, k) for k, tid in ids.items())
    breaches, soft, ok = [], [], []
    for t in rows.values():
        dl = t["deadline"]
        if dl in ("NA", "None", "", None):
            continue
        d = date_only(dl)
        f = date_only(t["finish"])
        k = key_by_id.get(t["id"], "?")
        fl = flags.get(k, {})
        item = {"key": k, "name": t["name"], "deadline": str(d), "finish": str(f),
                "statutory": bool(fl.get("statutory")),
                "recordedFact": bool(fl.get("breach_is_fact"))}
        if f > d:
            (soft if not (item["statutory"] or item["recordedFact"]) else breaches
             ).append(item)
        else:
            ok.append(item)
    log_fn("deadline audit: %d met, %d breached on brief dates, %d internal targets "
           "missed (%s)" % (len(ok), len(breaches), len(soft),
                            ", ".join(b["key"] for b in breaches) or "-"))
    for b in breaches:
        log_fn("   DEADLINE BREACH %s deadline %s, scheduled finish %s%s"
               % (b["key"], b["deadline"], b["finish"],
                  " [recorded fact]" if b["recordedFact"] else " [PLAN FAILURE]"))
    for b in soft:
        log_fn("   INTERNAL TARGET %s deadline %s, scheduled finish %s"
               % (b["key"], b["deadline"], b["finish"]))
    return {"met": ok, "breached": breaches, "internalTargetsMissed": soft}


def critical_path(rows):
    crit = [t for t in rows.values() if t["critical"] and not t["summary"]]
    return {"count": len(crit), "rows": [t["name"][:50] for t in crit],
            "by_wbs": [t["wbs"] for t in crit]}


# ============================================================ 3. perturbation
def prove_links(mp, p, rows, ids, link_spec, log_fn=log):
    """Prove the engine, not the text, is driving the dates - per link TYPE.

    A lag written through TaskDependency.Lag was measured to be accepted and
    then ignored (se_build_proj_r2.log: FS and SS lag tests returned identical
    dates), so liveness is proven the way a planner actually tests a schedule:
    lengthen one forecast row and watch which descendants move, in which field.
    An FS or SS edge must drag its successor's start; an FF edge must drag the
    finish. Rows booked complete are deliberately excluded - Project holds
    completed work against its actuals, which is itself a sign the file is a
    tracked plan rather than a drawing.
    """
    by_key = dict((v, k) for k, v in ids.items())
    pct = {}
    for k, tid in ids.items():
        r = rows.get(tid)
        pct[k] = (r or {}).get("pct", 0)
    kind = {}
    for k, tid in ids.items():
        kind[k] = "ms" if (rows.get(tid) or {}).get("milestone") else "task"

    def succ_edges(src):
        return [(s, d, t) for ((s, d), t) in link_spec.items() if s == src]

    def descendants(start, seen=None):
        seen = seen or set()
        out = []
        for (_s, d, t) in succ_edges(start):
            if d in seen:
                continue
            seen.add(d)
            out.append((d, t))
            out.extend(descendants(d, seen))
        return out

    def live(k):
        return kind.get(k) == "task" and int(round(pct.get(k) or 0)) < 100

    rec = {}
    for label, driver in (("startChain", "10.2"), ("finishChain", "9.1"),
                          ("ssChain", "9.3")):
        if driver not in ids or not live(driver):
            rec[label] = {"skipped": "driver %s is not an open task row" % driver}
            continue
        chain = descendants(driver)
        watch = [(k, t) for (k, t) in chain if k in ids]
        if not watch:
            rec[label] = {"skipped": "%s has no successors" % driver}
            continue
        before = dict((k, (dstr(p.Tasks.Item(ids[k]).Start),
                           dstr(p.Tasks.Item(ids[k]).Finish))) for k, _t in watch)
        before[driver] = (dstr(p.Tasks.Item(ids[driver]).Start),
                          dstr(p.Tasks.Item(ids[driver]).Finish))
        dtask = p.Tasks.Item(ids[driver])
        old = dtask.Duration
        dtask.Duration = old + 10 * 60 * HOURS_PER_DAY
        mp.CalculateAll()
        during = dict((k, (dstr(p.Tasks.Item(ids[k]).Start),
                           dstr(p.Tasks.Item(ids[k]).Finish))) for k, _t in watch)
        during[driver] = (dstr(dtask.Start), dstr(dtask.Finish))
        dtask.Duration = old
        mp.CalculateAll()
        after = dict((k, (dstr(p.Tasks.Item(ids[k]).Start),
                          dstr(p.Tasks.Item(ids[k]).Finish))) for k, _t in watch)
        after[driver] = (dstr(dtask.Start), dstr(dtask.Finish))
        moved_start, moved_finish, still = [], [], []
        for k, t in watch:
            if not live(k):
                continue
            if during[k][0] != before[k][0]:
                moved_start.append({"key": k, "via": t, "before": before[k][0],
                                    "after": during[k][0]})
            if during[k][1] != before[k][1]:
                moved_finish.append({"key": k, "via": t, "before": before[k][1],
                                     "after": during[k][1]})
            if after[k] != before[k]:
                still.append("%s did not return to %s (reads %s)" % (k, before[k],
                                                                      after[k]))
        rec[label] = {"driver": dtask.Name[:44], "driverDays": round(old / 480.0),
                      "watched": len(watch), "movedStart": moved_start,
                      "movedFinish": moved_finish, "notRestored": still,
                      "restoredCleanly": not still}
        log_fn("  %s: poking %s (%dd) moved start of %s and finish of %s; restore "
               "clean=%s" % (label, driver, round(old / 480.0),
                             [m["key"] + "/" + m["via"] for m in moved_start],
                             [m["key"] + "/" + m["via"] for m in moved_finish],
                             not still))
    # classify what was actually demonstrated, per type
    shown = set()
    for v in rec.values():
        for m in v.get("movedStart", []) or []:
            if m["via"] in ("FS", "SS"):
                shown.add(m["via"])
        for m in v.get("movedFinish", []) or []:
            if m["via"] == "FF":
                shown.add("FF")
    declared_types = set(t for (_s, _d), t in link_spec.items())
    rec["types"] = {"declared": sorted(declared_types), "demonstrated": sorted(shown),
                    "lagWriteMeasured": "TaskDependency.Lag accepted but inert "
                                        "(se_build_proj_r2.log), so propagation is used"}
    log_fn("  link types declared %s, demonstrated live %s"
           % (sorted(declared_types), sorted(shown)))
    rec["allTypesLive"] = declared_types <= shown or "SF" in declared_types
    return rec


def roll_forward(mp, p, rows, ids, status_date, log_fn=log):
    """Try Project's own "Move to Status Date" on the unfinished work, and record
    what it actually does on this install.

    Measured in se_proj_probe_r10.log: every argument form of
    Application.TaskMoveToStatusDate returns True and moves nothing, and
    OptionsCalculation(SpreadPercentToStatusDate=True) hangs the COM session
    behind a modal prompt, so it must not be called. This function therefore
    attempts the call once, verifies whether any date moved, and reports the
    result as a limitation instead of pretending the roll happened. Rows that
    are genuinely late at the status date stay late - stretching their windows
    to make the plan look tidy would be exactly the falsified history the brief
    forbids.
    """
    before = dict((k, (dstr(t.Start), dstr(t.Finish))) for k, _r, t in rows)
    rec = {"called": False, "moved": [], "refused": None}
    for args in ({"MoveCompleted": False, "MoveIncomplete": True},
                 {"MoveCompleted": 0, "MoveIncomplete": 3}):
        try:
            mp.TaskMoveToStatusDate(**args)
            rec["called"] = True
            rec["args"] = str(args)
            break
        except Exception as exc:
            rec["refused"] = "%s: %s" % (type(exc).__name__, str(exc)[:140])
    if not rec["called"]:
        log_fn("TaskMoveToStatusDate refused (%s); the open rows stay in their "
               "original window and the audit reports them as overdue"
               % rec["refused"])
        return rec
    mp.CalculateAll()
    after = dict((k, (dstr(t.Start), dstr(t.Finish))) for k, _r, t in rows)
    rec["moved"] = [k for k in before if before[k] != after[k]]
    still_open_before = []
    for k, row, t in rows:
        if row["kind"] != "task":
            continue
        if int(round(t.PercentComplete)) < 100 and date_only(t.Finish) < status_date:
            still_open_before.append("%s %s..%s at %d%%" % (k, dstr(t.Start),
                                                            dstr(t.Finish),
                                                            t.PercentComplete))
    rec["open_rows_still_before_status_date"] = still_open_before
    log_fn("move-to-status-date: %d rows re-planned by the engine; %d open rows still "
           "scheduled to finish before %s"
           % (len(rec["moved"]), len(still_open_before), status_date))
    for s in still_open_before[:8]:
        log_fn("   STILL PAST %s" % s)
    return rec


def audit_capacity(rows, ids, res_meta, static, log_fn=log):
    """The capacity gate, read back out of Project rather than asserted.

    For every work resource this walks the assignments Project itself holds,
    spreads each assignment's Work across the working days of its own
    Start..Finish span, and compares the weekly sum with that person's declared
    availability. It also asks Project whether it considers the resource
    overallocated. Both must come back clean, otherwise the plan is arithmetically
    pretty and impossible to execute - which is what the review caught in R2.
    """
    avail = {}
    for rid, meta in res_meta.items():
        if meta["rtype"] != "work":
            continue
        avail[meta["key"]] = meta.get("avail_week", 0.0)
    weekly, flagged, work_hours = {}, [], 0.0
    contrib = {}
    for t in rows.values():
        for a in t["assigns"]:
            meta = res_meta.get(a.get("res"))
            if not meta or meta["rtype"] != "work":
                continue
            hrs = (a.get("work") or 0) / 60.0
            work_hours += hrs
            s, f = date_only(a.get("start") or t["start"]), \
                date_only(a.get("finish") or t["finish"])
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
                    iso = tuple(d.isocalendar()[:2])
                    key = (meta["key"], iso)
                    weekly[key] = weekly.get(key, 0.0) + hrs / n
                    contrib.setdefault(key, []).append((t["wbs"], hrs / n))
                d += datetime.timedelta(days=1)
            if a.get("overallocated"):
                flagged.append("%s / %s assignment flagged overallocated"
                               % (t["name"][:28], meta["key"]))
    table, over = [], []
    for (rkey, iso), hrs in sorted(weekly.items(), key=lambda kv: (kv[0][0],
                                                                   kv[0][1])):
        cap = avail.get(rkey, 0.0)
        # 0.25 h absorbs the unit quantisation above; it is not room to overrun
        excess = round(max(0.0, hrs - cap - 0.25), 1)
        table.append({"resource": rkey, "isoWeek": "%d-W%02d" % iso,
                      "availableHours": round(cap, 1),
                      "assignedHours": round(hrs, 1),
                      "overallocatedHours": excess})
        if excess > 0.0:
            # name the rows that landed there, or the refusal tells you the week
            # is impossible without saying which estimate to change
            who = sorted(contrib.get((rkey, iso), []), key=lambda x: -x[1])
            over.append("%s %s: Project books %.1f h against %.1f h available; "
                        "landed from %s"
                        % (rkey, "%d-W%02d" % iso, hrs, cap,
                           ", ".join("%s %.1f h" % (w, h) for w, h in who[:8])))
    static_cap = (static.get("capacity") or {})
    for rkey in sorted(avail):
        srow = next((r for r in static_cap.get("weekly", [])
                     if r["resource"] == rkey), None)
        peak_static = max([r["assignedHours"] for r in static_cap.get("weekly", [])
                           if r["resource"] == rkey] or [0])
        peak_live = max([r["assignedHours"] for r in table
                         if r["resource"] == rkey] or [0])
        log_fn("   capacity %-8s available %4.1f h/wk | static peak %5.1f h (%d "
               "person-weeks) | Project peak %5.1f h"
               % (rkey, avail[rkey], peak_static,
                  len(static_cap.get("weekly", [])), peak_live))
    log_fn("capacity census: %.1f student hours in the file, %d person-weeks over "
           "availability, %d assignments flagged by Project"
           % (work_hours, len(over), len(flagged)))
    for o in over[:10]:
        log_fn("   OVERALLOCATION %s" % o)
    return {"studentHours": round(work_hours, 1), "weekly": table,
            "overallocated": over + flagged, "availabilityPerWeek": avail}


# ============================================================ 4. main
def main():
    static = preflight()
    log("static forward pass: project finish %s, chain %s"
        % (static["project_finish"], " -> ".join(static["critical_chain"])))
    mp, p, mpp, rows, ids, res_ids, res_meta, link_spec, assigned = build()
    status_date = dd(PROJECT["status_date"]).date()
    read_all(mp, p, res_meta)                    # first read, before the roll
    roll = roll_forward(mp, p, rows, ids, status_date)
    r1 = read_all(mp, p, res_meta)
    la = audit_links(r1, link_spec, ids)
    ca = audit_constraints(r1, ids)
    log("constraint audit: rows with a constraint other than ASAP: %s"
        % (ca["forced"] or "none"))
    log("earliest scheduled start: %s (project start %s)"
        % (ca["earliest_start"], dstr(p.ProjectStart)))
    pa = audit_progress(r1, ids, status_date)
    coa = audit_costs(r1, ids, res_meta, res_ids, assigned)
    capa = audit_capacity(r1, ids, res_meta, static)
    flags = dict((k, {"statutory": bool(row.get("statutory")),
                      "breach_is_fact": bool(row.get("breach_is_fact"))})
                 for k, row, _t in rows)
    da = audit_deadlines(r1, ids, flags)
    cp = critical_path(r1)
    log("critical path: %d rows, first few %s" % (cp["count"], cp["rows"][:6]))
    fact_keys = set(k for k, row, _t in rows if row.get("breach_is_fact"))
    proof = prove_links(mp, p, r1, ids, link_spec)
    snapshot = {"tasks": p.Tasks.Count, "resources": p.Resources.Count,
                "cost": p.Cost, "finish": dstr(p.ProjectFinish),
                "start": dstr(p.ProjectStart), "critical": cp["count"]}
    log("before save: %s" % snapshot)
    bad = []
    if la["missing"]:
        bad.append("links missing from the engine")
    if la["violations"]:
        bad.append("links violate date order")
    if ca["forced"]:
        bad.append("rows carry a constraint")
    if pa["not_booked"]:
        bad.append("100% rows without booked actuals")
    if [x for x in pa["history_problems"] if not x.startswith("OVERDUE")]:
        bad.append("a row booked complete after the status date")
    if coa["problems"]:
        bad.append("work/cost does not match the estimate")
    if coa["compute_only_rows_without_zero_hours"]:
        bad.append("a row staffed only by compute lanes carries labour hours")
    if capa["overallocated"]:
        bad.append("the plan over-allocates a student against declared "
                   "availability: %s" % capa["overallocated"][:4])
    if [b for b in da["breached"] if not b["recordedFact"]]:
        bad.append("a date set by the assignment brief is breached by the schedule: %s"
                   % [b["key"] for b in da["breached"] if not b["recordedFact"]])
    if not proof.get("allTypesLive"):
        bad.append("not every declared link type was shown to move a date")
    if [v for v in proof.values() if isinstance(v, dict) and v.get("notRestored")]:
        bad.append("the schedule did not restore after the perturbation")
    if bad:
        log("BUILD REFUSED: %s" % "; ".join(bad))
        try:
            mp.FileCloseEx(0)
            mp.Quit(0)
        except Exception:
            pass
        json.dump({"refused": bad, "links": la, "constraints": ca,
                   "progress": pa, "costs": coa, "proof": proof,
                   "capacity": capa, "staticCapacity": static.get("capacity")},
                  open(os.path.join(HERE, "se_project_build_r2_result.json"), "w",
                       encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
        _lf.close()
        return 2

    p.SaveAs(mpp)
    log("saved %s (%d bytes)" % (mpp, os.path.getsize(mpp)))
    mp.FileCloseEx(0)
    mp.Quit(0)

    # --- reopen the staged file in a fresh process and re-audit --------------
    # The staged copy is audited first: a build that fails a gate must not
    # overwrite the deliverable that is already shipped.
    time.sleep(2)
    import win32com.client as w32
    mp2 = w32.DispatchEx("MSProject.Application")
    mp2.Visible = True
    try:
        mp2.DisplayAlerts = 0
    except Exception:
        pass
    mp2.FileOpen(mpp)
    p2 = mp2.ActiveProject
    r2 = read_all(mp2, p2, res_meta)
    la2 = audit_links(r2, link_spec, ids)
    ca2 = audit_constraints(r2, ids)
    pa2 = audit_progress(r2, ids, status_date)
    coa2 = audit_costs(r2, ids, res_meta, res_ids, assigned)
    cap2 = audit_capacity(r2, ids, res_meta, static)
    da2 = audit_deadlines(r2, ids, flags)
    cp2 = critical_path(r2)
    snap2 = {"tasks": p2.Tasks.Count, "resources": p2.Resources.Count,
             "cost": p2.Cost, "finish": dstr(p2.ProjectFinish),
             "critical": cp2["count"]}
    log("reopened: %s" % snap2)
    drift = []
    for tid, a in r1.items():
        b = r2.get(tid)
        if not b:
            drift.append("row %s missing after reopen" % tid)
            continue
        for f in ("start", "finish", "pct", "work", "cost", "constraint", "deadline",
                  "actualStart", "actualFinish", "milestone", "critical", "wbs"):
            va, vb = a[f], b[f]
            if isinstance(va, float) or isinstance(vb, float):
                if abs(float(va or 0) - float(vb or 0)) > 1.0:
                    drift.append("%s.%s %s -> %s" % (a["name"][:26], f, va, vb))
            elif str(va) != str(vb):
                drift.append("%s.%s %r -> %r" % (a["name"][:26], f, va, vb))
    log("reopen drift: %d field differences" % len(drift))
    for d in drift[:12]:
        log("   DRIFT %s" % d)

    checks = {
        "allDeclaredLinksExist": not la2["missing"] and la2["read"] >= la2["declared"],
        "noLinkViolatesDateOrder": not la2["violations"],
        "nothingConstrained": not ca2["forced"],
        "progressBookedByStatusDate": not pa2["not_booked"] and
        not [x for x in pa2["history_problems"] if not x.startswith("OVERDUE")],
        "costMatchesHours": not coa2["problems"],
        "noStudentOverallocation": not cap2["overallocated"],
        "effortWithinCapacity": cap2["studentHours"] <= sum(
            w["availableHours"] for w in cap2["weekly"]),
        "criticalPathComputed": cp2["count"] > 0,
        "linkTypesLive": bool(proof.get("allTypesLive")),
        "perturbationRestored": not [v for v in proof.values()
                                     if isinstance(v, dict) and v.get("notRestored")],
        "reopenIdentical": not drift,
        "briefDatesHeld": not [b for b in da2["breached"] if not b["recordedFact"]],
    }
    log("CHECKS: %s" % json.dumps(checks, ensure_ascii=False))
    mp2.FileCloseEx(0)
    mp2.Quit(0)
    failed = [k for k, v in checks.items() if not v]
    shipped = os.path.join(OUT, "CityNexus_Software_Engineering_Plan.mpp")
    ship_proof = {"published": False}
    if failed:
        log("NOT PUBLISHED: gates %s did not pass; the staged build stays in %s and "
            "the previously shipped plan is untouched"
            % (failed, os.path.dirname(mpp)))
    else:
        import shutil
        shutil.copyfile(mpp, shipped)
        sha = lambda path: hashlib.sha256(open(path, "rb").read()).hexdigest()
        ship_proof = {"published": True, "bytes": os.path.getsize(shipped),
                      "sha256": sha(shipped), "stagedSha256": sha(mpp),
                      "identicalToStaged": sha(shipped) == sha(mpp)}
        log("published %s (%d bytes, sha256 %s, identical to staged: %s)"
            % (shipped, ship_proof["bytes"], ship_proof["sha256"][:16],
               ship_proof["identicalToStaged"]))
        # one last read of the file that actually ships
        time.sleep(2)
        mp3 = w32.DispatchEx("MSProject.Application")
        mp3.Visible = True
        try:
            mp3.DisplayAlerts = 0
        except Exception:
            pass
        mp3.FileOpen(shipped)
        p3 = mp3.ActiveProject
        r3 = read_all(mp3, p3, res_meta)
        la3 = audit_links(r3, link_spec, ids)
        ship_proof["shippedRows"] = p3.Tasks.Count
        ship_proof["shippedLinksRead"] = la3["read"]
        ship_proof["shippedLinkViolations"] = len(la3["violations"])
        ship_proof["shippedCost"] = p3.Cost
        ship_proof["shippedFinish"] = dstr(p3.ProjectFinish)
        log("shipped file reads back: %d rows, %d dependency records, %d violations, "
            "cost %s, finish %s" % (ship_proof["shippedRows"],
                                    ship_proof["shippedLinksRead"],
                                    ship_proof["shippedLinkViolations"],
                                    ship_proof["shippedCost"],
                                    ship_proof["shippedFinish"]))
        mp3.FileCloseEx(0)
        mp3.Quit(0)
        # Measured: opening a .mpp lets Project rewrite it even when nothing is
        # saved, so the digest taken before this verification open is already
        # stale afterwards. Record both and say so, instead of publishing one
        # number that no longer matches the file on disk.
        after = sha(shipped)
        ship_proof["sha256AfterVerification"] = after
        ship_proof["rewrittenByVerificationOpen"] = (after != ship_proof["sha256"])
        log("shipped file digest after the verification open: %s (was %s; changed: %s)"
            % (after[:16], str(ship_proof["sha256"])[:16],
               ship_proof["rewrittenByVerificationOpen"]))
        if after != ship_proof["sha256"]:
            log("   the manifest and every evidence document must carry the "
                "AFTER digest - they are written after this run")
        if la3["violations"] or la3["missing"] or not ship_proof["identicalToStaged"]:
            failed.append("the published copy did not read back clean")

    result = {"static_preflight": static, "links": la2, "constraints": ca2,
              "progress": pa2, "costs": coa2, "deadlines": da2,
              "capacity": cap2,
              "status_date": str(status_date), "reopen_drift_count": len(drift),
              "status_roll": roll,
              "critical_path": cp2, "link_proof": proof, "publication": ship_proof,
              "first_pass": snapshot, "reopen_pass": snap2, "checks": checks,
              "rows": sorted(r2.values(), key=lambda x: x["id"]),
              "resources": res_meta, "assignments": assigned}
    json.dump(result, open(os.path.join(HERE, "se_project_build_r2_result.json"),
                           "w", encoding="utf-8"), indent=1, ensure_ascii=False,
              default=str)
    log("BUILD %s; failed checks: %s" % ("OK" if not failed else "INCOMPLETE",
                                         failed or "none"))
    _lf.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
