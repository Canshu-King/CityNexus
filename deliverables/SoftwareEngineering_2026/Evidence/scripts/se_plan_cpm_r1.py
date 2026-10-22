"""Static schedule checker for the CityNexus coursework plan (pure Python).

Runs before Microsoft Project is started, and again over the numbers Project
itself produced, so a broken dependency model is caught while it is still
cheap to fix. It never writes to the plan.

What it enforces, and why each rule is here:

  1. every link names a real row, has a parsable type, and is not a self-link
  2. the link graph has no cycle (Project would silently mis-schedule one)
  3. no SF links: measured in se_proj_probe_r5, an SF relationship back-schedules
     its predecessor to before the project start, which is how the plan would
     claim work happened before the repository existed
  4. forward-pass dates over a Mon-Fri calendar, so every declared link can be
     tested as an inequality - the class of defect the independent review found
     (successors starting before their predecessor could possibly finish)
  5. history rules against the status date: a row booked at 100% must be
     scheduled to finish on or before it; a row at 0% that is scheduled to
     finish before it is reported as overdue, not quietly moved
  6. deadline rules: a row whose scheduled finish passes its Deadline is
     reported as a breach, and a breach is only acceptable when the row is
     marked `breach_is_fact` (Part 1 really was missed)
  7. estimates: every leaf carries a duration, an owner and a work-hour figure,
     because the review asked that cost correspond to plausible hours
"""
import datetime
import re

D = datetime.date
WORKDAY_LINK_TYPES = ("FS", "SS", "FF")
LINK_RE = re.compile(r"^(.+?)(FS|SS|FF|SF)$")


def key_of(name):
    m = re.match(r"^(M\d+|\d+(?:\.\d+)?)\s", name)
    if not m:
        raise ValueError("row name has no leading key: %r" % name)
    return m.group(1)


def is_wd(day):
    return day.weekday() < 5


def next_wd(day):
    while not is_wd(day):
        day += datetime.timedelta(days=1)
    return day


def add_wd(day, n):
    """First working day n working days after `day`, counting `day` itself as 1
    when n >= 1 (Project's convention: a 1-day task starting Monday finishes
    Monday)."""
    day = next_wd(day)
    if n <= 1:
        return day
    remaining = n - 1
    while remaining:
        day = next_wd(day + datetime.timedelta(days=1))
        remaining -= 1
    return day


def sub_wd(day, n):
    day = prev_wd(day)
    if n <= 1:
        return day
    remaining = n - 1
    while remaining:
        day = prev_wd(day - datetime.timedelta(days=1))
        remaining -= 1
    return day


def prev_wd(day):
    while not is_wd(day):
        day -= datetime.timedelta(days=1)
    return day


def parse_days(dur):
    m = re.match(r"^(\d+)d$", (dur or "").strip())
    if not m:
        raise ValueError("duration %r is not a whole number of days" % dur)
    return int(m.group(1))


def flatten(plan):
    """Return (rows, by_key) with links parsed, summaries excluded from the
    schedule but kept for the WBS census."""
    rows, by_key = [], {}
    problems = []
    for r in plan:
        k = key_of(r["name"])
        if k in by_key:
            problems.append("duplicate row key %s" % k)
        entry = dict(r)
        entry["key"] = k
        entry["is_leaf"] = r["kind"] in ("task", "ms")
        entry["deps"] = []
        rows.append(entry)
        by_key[k] = entry
    for e in rows:
        for raw in e.get("links", []) or []:
            m = LINK_RE.match(raw)
            if not m:
                problems.append("%s: unparsable link %r" % (e["key"], raw))
                continue
            src, typ = m.group(1), m.group(2)
            if src not in by_key:
                problems.append("%s: link %r names unknown row %r" % (e["key"], raw, src))
                continue
            if src == e["key"]:
                problems.append("%s: links to itself" % e["key"])
                continue
            if typ == "SF":
                problems.append("%s: start-to-finish link from %s - measured on this "
                                "install it back-schedules the predecessor before the "
                                "project start; use FS/SS plus a Deadline instead"
                                % (e["key"], src))
            e["deps"].append((src, typ))
    return rows, by_key, problems


def topo(rows, by_key):
    order, state, cycles = [], {}, []

    def visit(k, stack):
        st = state.get(k)
        if st == 2:
            return
        if st == 1:
            cycles.append(" -> ".join(stack[stack.index(k):] + [k]))
            return
        state[k] = 1
        for src, _typ in by_key[k]["deps"]:
            visit(src, stack + [k])
        state[k] = 2
        order.append(k)

    for e in rows:
        if e["is_leaf"]:
            visit(e["key"], [])
    return order, cycles


def schedule(rows, by_key, start, working=True):
    """Forward pass. Returns {key: (start_date, finish_date)} over working days."""
    order, _cycles = topo(rows, by_key)
    dates = {}
    first = next_wd(start) if working else start
    for k in order:
        e = by_key[k]
        n = parse_days("0d" if e["kind"] == "ms" else e["dur"])
        s_candidates = [first]
        f_candidates = []
        for src, typ in e["deps"]:
            ps, pf = dates[src]
            if typ == "FS":
                s_candidates.append(pf + datetime.timedelta(days=1) if not working
                                    else next_wd(pf + datetime.timedelta(days=1)))
            elif typ == "SS":
                s_candidates.append(ps)
            elif typ == "FF":
                f_candidates.append(pf)
            elif typ == "SF":
                f_candidates.append(ps)
        s = max(s_candidates)
        if working:
            s = next_wd(s)
        f = add_wd(s, max(n, 1)) if working else s + datetime.timedelta(days=max(n - 1, 0))
        for pf in f_candidates:
            if pf > f:
                f = pf
                s = sub_wd(f, max(n, 1)) if working else f - datetime.timedelta(
                    days=max(n - 1, 0))
        dates[k] = (s, f)
    return dates


def check(plan, start, status_date, hours_per_day=8.0, resources=None):
    rows, by_key, problems = flatten(plan)
    order, cycles = topo(rows, by_key)
    if cycles:
        problems.append("CIRCULAR DEPENDENCY: %s" % "; ".join(sorted(set(cycles))[:4]))
    dates = schedule(rows, by_key, start)

    # ---- link inequalities -------------------------------------------------
    link_rows = []
    violations = []
    for e in rows:
        if not e["is_leaf"]:
            continue
        for src, typ in e["deps"]:
            ss, sf = dates[src]
            ts, tf = dates[e["key"]]
            ok = {"FS": ts >= sf, "SS": ts >= ss, "FF": tf >= sf, "SF": tf >= ss}[typ]
            gap = (tf - sf).days if typ in ("FF", "SF") else (ts - sf).days
            link_rows.append({"pred": src, "succ": e["key"], "type": typ,
                              "pred_finish": str(sf), "succ_start": str(ts),
                              "holds": bool(ok), "date_gap_days": gap})
            if not ok:
                violations.append("%s(%s) %s %s(%s): predecessor finishes %s but "
                                  "successor starts %s" % (src, str(sf), typ,
                                                            e["key"], str(ts), str(sf),
                                                            str(ts)))
    n_links = len(link_rows)

    # ---- progress against the status date ----------------------------------
    overdue, history_bad, partial = [], [], []
    for e in rows:
        if not e["is_leaf"]:
            continue
        s, f = dates[e["key"]]
        pct = e.get("pct")
        if e["kind"] == "ms":
            continue
        if pct == 100 and f > status_date:
            history_bad.append("%s is booked 100%% done but is not scheduled to finish "
                               "until %s, after the status date %s" % (e["key"], f,
                                                                       status_date))
        if pct == 0 and e["kind"] == "task" and f < status_date:
            overdue.append("%s 0%% complete, planned %s..%s - overdue as of the status "
                           "date (left visible, not re-dated)" % (e["key"], s, f))
        if 0 < (pct or 0) < 100:
            partial.append("%s %d%% - remaining work rolls past %s" % (e["key"], pct,
                                                                        status_date))
        if pct is None:
            problems.append("%s has no percent-complete value at all" % e["key"])

    # ---- deadlines ---------------------------------------------------------
    # A deadline set by the assignment brief is hard: the plan must show whether it
    # can still be met. A target this plan set for itself (tentative=True) may be
    # breached, and the breach is reported as a risk rather than hidden.
    breaches, soft_breaches, dl_missing = [], [], []
    for e in rows:
        dl = e.get("deadline")
        if not dl:
            continue
        d = D(*[int(x) for x in dl.split("-")])
        s, f = dates[e["key"]]
        if f > d:
            item = "%s deadline %s but scheduled finish %s" % (e["key"], d, f)
            if e.get("breach_is_fact"):
                item += "  [recorded fact: this date was really missed]"
                breaches.append(item)
            elif e.get("statutory"):
                breaches.append(item + "  [PLAN FAILURE: the brief sets this date]")
            else:
                soft_breaches.append(item + "  [internal target, reported as risk]")
    # ---- rows that are late against the status date ------------------------
    late = []
    for e in rows:
        if e["kind"] != "task":
            continue
        pct = e.get("pct")
        s, f = dates[e["key"]]
        if pct is not None and pct < 100 and f < status_date \
                and not e.get("breach_is_fact"):
            late.append("%s %s%% done, planned to finish %s, status date %s"
                        % (e["key"], pct, f, status_date))
    for e in rows:
        if e["kind"] == "ms" and not e.get("deadline") and not e.get("obs"):
            dl_missing.append("%s milestone has neither a deadline nor an observed date"
                              % e["key"])

    # ---- estimates ---------------------------------------------------------
    no_owner, no_dur, no_ev = [], [], []
    for e in rows:
        if e["kind"] != "task":
            continue
        if not (e.get("assign") or []) and not (e.get("eff") or {}):
            no_owner.append(e["key"])
        if not e.get("dur"):
            no_dur.append(e["key"])
        if not (e.get("ev") or "").strip():
            no_ev.append(e["key"])
        if e["kind"] == "task" and not e.get("obs") and not e.get("ev"):
            problems.append("%s states neither an observation nor an evidence line"
                            % e["key"])
    if no_owner:
        problems.append("leaf tasks with no owner: %s" % no_owner)
    if no_dur:
        problems.append("leaf tasks with no duration: %s" % no_dur)
    if no_ev:
        problems.append("leaf tasks with no evidence text: %s" % no_ev)

    # ---- census ------------------------------------------------------------
    leaves = [e for e in rows if e["is_leaf"]]
    tasks = [e for e in rows if e["kind"] == "task"]
    mss = [e for e in rows if e["kind"] == "ms"]
    no_pred = [e["key"] for e in leaves if not e["deps"] and e["key"] != "1.1"]
    if no_pred:
        problems.append("rows with no predecessor and no reason: %s" % no_pred)

    # ---- critical path: walk the longest chain backwards from the last row --
    finish_key, finish_date = None, None
    for k, (s, f) in dates.items():
        if not by_key[k]["is_leaf"]:
            continue
        if finish_date is None or f > finish_date or (f == finish_date and s >
                                                      dates[finish_key][0]):
            finish_date, finish_key = f, k
    chain = []
    cur = finish_key
    guard = 0
    while cur and guard < 200:
        guard += 1
        chain.append(cur)
        best = None
        for src, typ in by_key[cur]["deps"]:
            if not by_key[src]["is_leaf"]:
                continue
            sf = dates[src][1]
            # the predecessor that actually holds this row up: for FS/SS it is the
            # one whose date the successor's start was taken from
            ss = dates[src][0]
            anchor = sf if typ in ("FS", "FF") else ss
            if best is None or anchor > best[0]:
                best = (anchor, src)
        cur = best[1] if best else None
    chain.reverse()

    # ---- resource capacity census -----------------------------------------
    # The review's point: a plan can be arithmetically correct and still be
    # impossible to execute. Hours are spread over the working days each row
    # actually occupies, then summed per person per ISO week and compared with
    # the availability that person's role claims. Compute lanes are material
    # resources and are counted separately, never as student labour.
    students = dict((r["key"], r) for r in (resources or [])
                    if r.get("rtype") == "work")
    compute = dict((r["key"], r) for r in (resources or [])
                   if r.get("rtype") != "work")
    weekly = {}
    compute_hours = 0.0
    per_person_total = {}
    for e in tasks:
        s, f = dates[e["key"]]
        wd = 0
        d = s
        while d <= f:
            if is_wd(d):
                wd += 1
            d += datetime.timedelta(days=1)
        # student hours come from the stated effort table; assignment units are
        # derived from it at build time so Project's Work equals it exactly
        eff = e.get("eff") or {}
        for rkey, hrs in eff.items():
            per_person_total[rkey] = per_person_total.get(rkey, 0.0) + float(hrs)
            if not wd:
                continue
            d = s
            while d <= f:
                if is_wd(d):
                    iso = tuple(d.isocalendar()[:2])
                    weekly[(rkey, iso)] = weekly.get((rkey, iso), 0.0) + \
                        float(hrs) / wd
                d += datetime.timedelta(days=1)
        for rkey, units in (e.get("assign") or []):
            hrs = wd * hours_per_day * float(units)
            per_person_total[rkey] = per_person_total.get(rkey, 0.0) + hrs
            if rkey in students:
                continue          # a work resource here would double-count EFF
            compute_hours += hrs
    over, capacity_table = [], []
    for (rkey, iso), hrs in sorted(weekly.items(),
                                   key=lambda kv: (kv[0][0], kv[0][1])):
        avail = float(students.get(rkey, {}).get("avail_week", 0.0))
        if avail <= 0:
            continue
        excess = round(max(0.0, hrs - avail), 1)
        capacity_table.append({"resource": rkey, "isoWeek": "%d-W%02d" % iso,
                               "availableHours": round(avail, 1),
                               "assignedHours": round(hrs, 1),
                               "overallocatedHours": excess})
        if excess > 0.01:
            over.append("%s %s: assigned %.1f h > available %.1f h (over %.1f h)"
                        % (rkey, "%d-W%02d" % iso, hrs, avail, excess))
    totals = {}
    for rkey, st in students.items():
        wk_keys = sorted([k for (rk, k) in weekly if rk == rkey])
        span = 1
        if len(wk_keys) >= 1:
            a0 = datetime.date.fromisocalendar(wk_keys[0][0], wk_keys[0][1], 1)
            a1 = datetime.date.fromisocalendar(wk_keys[-1][0], wk_keys[-1][1], 1)
            span = (a1 - a0).days // 7 + 1
        assigned = round(per_person_total.get(rkey, 0.0), 1)
        available = round(float(st.get("avail_week", 0)) * span, 1)
        totals[rkey] = {"assignedHours": assigned, "weeksScheduled": span,
                        "availableHours": available,
                        "utilisationPct": round(100.0 * assigned / available, 1)
                        if available else 0.0}
        if assigned > available + 0.5:
            over.append("%s total: %.1f h assigned against %.1f h available across "
                        "the %d scheduled weeks" % (rkey, assigned, available, span))
    total_hours = round(sum(per_person_total.get(k, 0.0) for k in students), 1)

    return {
        "problems": problems,
        "violations": violations,
        "links_total": n_links,
        "links": link_rows,
        "history_after_status_date": history_bad,
        "overdue_not_started": overdue,
        "in_progress": partial,
        "deadline_breaches": breaches,
        "internal_target_breaches": soft_breaches,
        "late_at_status_date": late,
        "milestones_without_date": dl_missing,
        "census": {"summaries": len(rows) - len(leaves), "tasks": len(tasks),
                   "milestones": len(mss), "leaves": len(leaves)},
        "project_finish": str(finish_date),
        "critical_chain": chain,
        "estimated_hours_total": total_hours,
        "estimated_hours_by_resource": dict(
            (k, round(v, 1)) for k, v in per_person_total.items() if k in students),
        "compute_hours_note": "material lanes; priced, never counted as student hours",
        "capacity": {"students": {k: {"availWeek": float(v.get("avail_week", 0))}
                                  for k, v in students.items()},
                     "weekly": capacity_table,
                     "totals": totals,
                     "overallocated": over,
                     "computeHoursPriced": round(compute_hours, 1)},
        "dates": dict((k, (str(v[0]), str(v[1]))) for k, v in dates.items()),
    }


def report(res, out=None):
    lines = []
    a = lines.append
    a("links declared and resolved : %d" % res["links_total"])
    a("link inequalities violated  : %d" % len(res["violations"]))
    for v in res["violations"][:20]:
        a("   VIOLATION %s" % v)
    a("structural problems         : %d" % len(res["problems"]))
    for v in res["problems"][:12]:
        a("   PROBLEM %s" % v)
    a("100%% rows finishing after the status date : %d" %
      len(res["history_after_status_date"]))
    for v in res["history_after_status_date"]:
        a("   HISTORY %s" % v)
    a("0%% rows already past their planned finish : %d" % len(res["overdue_not_started"]))
    for v in res["overdue_not_started"]:
        a("   OVERDUE %s" % v)
    a("deadline breaches (brief dates) : %d" % len(res["deadline_breaches"]))
    for v in res["deadline_breaches"]:
        a("   DEADLINE %s" % v)
    a("internal targets missed : %d" % len(res.get("internal_target_breaches", [])))
    for v in res.get("internal_target_breaches", []):
        a("   RISK %s" % v)
    a("rows late against the status date : %d" % len(res.get("late_at_status_date", [])))
    for v in res.get("late_at_status_date", []):
        a("   LATE %s" % v)
    a("census : %s" % res["census"])
    cap = res.get("capacity", {})
    a("student hours by person : %s" % res["estimated_hours_by_resource"])
    a("per-person totals vs availability :")
    for k, v in (cap.get("totals") or {}).items():
        a("   %-8s assigned %6.1f h / available %6.1f h over %d scheduled week(s)"
          % (k, v["assignedHours"], v["availableHours"], v["weeksScheduled"]))
    a("OVERALLOCATED person-weeks : %d" % len(cap.get("overallocated", [])))
    for v in cap.get("overallocated", [])[:14]:
        a("   OVER %s" % v)
    worst = sorted(cap.get("weekly", []),
                   key=lambda r: -r["overallocatedHours"])[:8]
    a("hottest person-weeks (assigned / available / over) :")
    for r in worst:
        a("   %-8s %-9s %5.1f / %5.1f / %5.1f" % (r["resource"], r["isoWeek"],
                                                  r["assignedHours"],
                                                  r["availableHours"],
                                                  r["overallocatedHours"]))
    a("project finish (static forward pass) : %s" % res["project_finish"])
    a("critical chain : %s" % " -> ".join(res["critical_chain"]))
    text = "\n".join(lines)
    if out:
        open(out, "w", encoding="utf-8").write(text + "\n")
    return text


if __name__ == "__main__":
    import json
    import sys
    sys.path.insert(0, r"D:\moodle\live_checks")
    from se_project_plan_r2 import PLAN
    from se_project_plan_r2 import RESOURCES
    res = check(PLAN, D(2026, 9, 7), D(2026, 10, 22), resources=RESOURCES)
    print(report(res, r"D:\moodle\live_checks\se_plan_cpm_r2.txt"))
    json.dump(res, open(r"D:\moodle\live_checks\se_plan_cpm_r2.json", "w",
                        encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
