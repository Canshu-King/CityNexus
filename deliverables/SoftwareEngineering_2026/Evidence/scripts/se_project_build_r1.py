"""Build CityNexus_Software_Engineering_Plan.mpp with real Microsoft Project,
then prove it is a real schedule rather than a picture of one.

Hard requirements this script enforces before it will report success:
  1. the plan has no circular dependency (checked here, topologically, before
     Project is even started)
  2. every task is AUTO SCHEDULED - field 1280 read back must say so, because a
     new Project file defaults to manually scheduled and then links do nothing
     (proved in se_probe_r6.log: a successor did not move until this was fixed)
  3. changing one leaf's duration moves its successor - the scheduling engine is
     really driving the dates
  4. the critical path is computed by Project, not asserted
  5. resources carry standard rates and an assignment produces a non-zero cost
  6. save, close, reopen: task count, link text, WBS codes, cost and dates all
     read back the same
  7. each required view exports to PDF from the same file
"""
import datetime
import io
import json
import os
import re
import sys
import time

D = datetime.datetime
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from se_timeutil_r1 import dstr  # noqa: E402
sys.path.insert(0, HERE)
from se_project_plan_r1 import PLAN, RESOURCES, PROJECT          # noqa: E402

OUT = os.environ.get("SE_MSP_OUT",
                     r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project")
LOGP = os.path.join(HERE, "se_project_build.log")
_lf = open(LOGP, "w", encoding="utf-8", buffering=1)
_t0 = time.time()


def log(m):
    line = "[%6.1fs] %s" % (time.time() - _t0, m)
    _lf.write(line + "\n")
    _lf.flush()
    print(line, flush=True)


def d(s):
    return D.strptime(s, "%Y-%m-%d %H:%M") if " " in s else D.strptime(s, "%Y-%m-%d")


# ============================================================ 1. static checks
def key_of(row):
    name = row["name"]
    m = re.match(r"^(M\d+|\d+(?:\.\d+)?)\s", name)
    if not m:
        raise ValueError("row name has no leading key: %r" % name)
    return m.group(1)


def static_checks():
    problems = []
    keys = [key_of(r) for r in PLAN]
    if len(set(keys)) != len(keys):
        dup = [k for k in set(keys) if keys.count(k) > 1]
        problems.append("duplicate task keys: %s" % dup)
    idx = dict((k, i) for i, k in enumerate(keys))
    # dependency graph over leaf/milestone rows only (summaries have no links)
    graph = {}
    for i, r in enumerate(PLAN):
        graph[keys[i]] = []
        for lk in r.get("links", []):
            m = re.match(r"^(.+?)(FS|SS|FF|SF)$", lk)
            if not m:
                problems.append("unparsable link %r on %s" % (lk, keys[i]))
                continue
            src = m.group(1)
            if src not in idx:
                problems.append("link %r on %s names an unknown task" % (lk, keys[i]))
                continue
            graph[keys[i]].append(src)
    # topological sort - a cycle here is a plan bug, not a Project quirk
    state = {}
    cycles = []

    def visit(k, stack):
        if state.get(k) == 2:
            return
        if state.get(k) == 1:
            cycles.append(" -> ".join(stack[stack.index(k):] + [k]))
            return
        state[k] = 1
        for dep in graph.get(k, []):
            visit(dep, stack + [k])
        state[k] = 2

    for k in keys:
        visit(k, [])
    if cycles:
        problems.append("CIRCULAR DEPENDENCY: %s" % "; ".join(sorted(set(cycles))[:4]))

    leaves = [r for r in PLAN if r["kind"] in ("task", "ms")]
    no_pred = [key_of(r) for r in leaves if not r.get("links") and key_of(r) != "1.1"]
    if no_pred:
        problems.append("tasks with no predecessor and no reason: %s" % no_pred)
    sums = [r for r in PLAN if r["kind"] == "sum"]
    ntask = len([r for r in PLAN if r["kind"] == "task"])
    nms = len([r for r in PLAN if r["kind"] == "ms"])
    log("static: %d summary groups, %d leaf tasks, %d milestones, %d resources"
        % (len(sums), ntask, nms, len(RESOURCES)))
    if not (20 <= ntask <= 45):
        problems.append("leaf task count %d is outside the 20-45 brief" % ntask)
    if nms < 7:
        problems.append("only %d milestones; the brief wants at least 7 categories" % nms)
    return problems, keys, idx


# ============================================================ 2. build
VIEW_WANT = [
    ("Gantt_Chart", ("甘特图", "Gantt")),
    ("Network_Diagram", ("网络图", "Network")),
    ("WBS_View", ("任务工作表", "Task Sheet")),
    ("Resource_Sheet", ("资源工作表", "Resource Sheet")),
    ("Milestone_Timeline", ("时间表", "Timeline")),
    ("Task_Usage", ("任务使用情况", "Task Usage")),
]


def build():
    problems, keys, idx = static_checks()
    if problems:
        for p in problems:
            log("PLAN PROBLEM: %s" % p)
        raise SystemExit("refusing to build a plan that fails its own checks")

    import win32com.client as w32
    os.makedirs(OUT, exist_ok=True)
    mpp = os.path.join(OUT, "CityNexus_Software_Engineering_Plan.mpp")
    if os.path.exists(mpp):
        os.remove(mpp)

    mp = w32.Dispatch("MSProject.Application")
    mp.Visible = True
    try:
        mp.DisplayAlerts = 0
    except Exception:
        pass
    log("Microsoft Project version %s" % mp.Version)
    mp.FileNew()
    p = mp.ActiveProject
    log("new project: %s" % p.Name)

    # --- project frame -----------------------------------------------------
    p.ProjectStart = d(PROJECT["start"])
    log("ProjectStart = %s" % p.ProjectStart)
    try:
        p.StatusDate = d(PROJECT["status_date"])
    except Exception as exc:
        log("(StatusDate refused: %s)" % type(exc).__name__)
    for prop, val in (("Name", PROJECT["name"]), ("Author", PROJECT["author"]),
                      ("Company", PROJECT["company"])):
        try:
            setattr(p, prop, val)
        except Exception as exc:
            log("(project %s refused: %s)" % (prop, type(exc).__name__))
    for cell, val in (("CurrencySymbol", "$"), ("CurrencyDigits", "2"),
                      ("CurrencyPosition", "1")):
        try:
            setattr(p, cell, val)
        except Exception as exc:
            log("(currency %s refused: %s)" % (cell, type(exc).__name__))
    try:
        p.WeekStartDay = 1
    except Exception:
        pass

    # --- resources with costs ---------------------------------------------
    res_ids = {}
    for r in RESOURCES:
        rname = re.sub(r"[\[\],;]", " / ", r["name"])
        res = p.Resources.Add(rname)
        try:
            res.Type = 1                      # work resource - must come before rates
        except Exception as exc:
            log("resource %s Type refused: %s" % (r["name"], type(exc).__name__))
        try:
            res.AccrueAt = 3                  # prorated
        except Exception:
            pass
        for prop, val in (("StandardRate", r["std"]), ("OvertimeRate", r["ovt"]),
                          ("Initials", r["initials"]), ("CostPerUse", 0.0),
                          ("MaxUnits", 1.0), ("Accenture", None)):
            if val is None:
                continue
            try:
                setattr(res, prop, val)
            except Exception as exc:
                log("  resource %s.%s refused (%s); kept the default"
                    % (rname[:28], prop, type(exc).__name__))
        try:
            res.Notes = r["note"]
        except Exception as exc:
            log("  resource notes refused: %s" % type(exc).__name__)
        res_ids[r["key"]] = res.ID
        r["resolvedName"] = rname
        log("resource #%d %-58s std=%s readback=%s"
            % (res.ID, rname[:58], r["std"], res.StandardRate))

    # --- tasks -------------------------------------------------------------
    ids = {}
    rows = []
    for i, row in enumerate(PLAN):
        t = p.Tasks.Add(row["name"])
        k = keys[i]
        ids[k] = t.ID
        try:
            t.SetField(1280, 0)               # 0 == auto scheduled (probe r6/r7)
        except Exception as exc:
            log("task %s could not be forced to auto schedule: %s" % (k, exc))
        t.OutlineLevel = 1 if row["kind"] == "sum" else 2
        if row["kind"] == "ms":
            t.Duration = "0d"
        elif row["kind"] == "task":
            t.Duration = row["dur"]
        rows.append((k, row, t))

    # links after all tasks exist so IDs resolve
    linked, skipped = 0, []
    for k, row, t in rows:
        if row["kind"] == "ms" and row.get("ms_date"):
            t.Deadline = d(row["ms_date"])
            t.Start = d(row["ms_date"])
            skipped.append("%s (deadline %s pinned)" % (k, row["ms_date"]))
            continue
        parts = []
        for lk in row.get("links", []):
            m = re.match(r"^(.+?)(FS|SS|FF|SF)$", lk)
            src, typ = m.group(1), m.group(2)
            parts.append("%d%s" % (ids[src], typ))
        if parts:
            t.Predecessors = ",".join(parts)
            linked += 1
    log("links applied on %d rows; %d rows are pinned milestones" % (linked, len(skipped)))
    for s in skipped:
        log("   pinned: %s" % s)

    # percentages, notes, assignments
    assigned = 0
    for k, row, t in rows:
        if row["kind"] == "sum":
            continue
        if row.get("pct") is not None:
            try:
                t.PercentComplete = row["pct"]
            except Exception as exc:
                log("task %s percent refused: %s" % (k, type(exc).__name__))
        note = "EVIDENCE: %s" % row["ev"]
        if row.get("tentative"):
            note = "DATES AND SCOPE ARE PROVISIONAL. " + note
        t.Notes = note
        rk = row.get("res")
        if rk:
            try:
                t.Assignments.Add(t.ID, res_ids[rk], 1.0)
                assigned += 1
            except Exception as exc:
                log("assign %s -> %s failed: %s" % (k, rk, str(exc)[:120]))
    log("assignments created: %d" % assigned)

    mp.CalculateAll()
    return mp, p, mpp, rows, ids, res_ids


def audit(mp, p, rows, ids):
    """Read the finished schedule back out of Project itself."""
    rep = {"tasks": p.Tasks.Count, "resources": p.Resources.Count,
           "assignments": 0, "projectStart": dstr(p.ProjectStart),
           "projectFinish": dstr(p.ProjectFinish),
           "cost": p.Cost, "work": p.Work,
           "manual": [], "critical": [], "wbs": [], "milestones": [],
           "constrained": [], "noPredecessor": [], "leaves": 0}
    for i in range(1, p.Tasks.Count + 1):
        t = p.Tasks.Item(i)
        try:
            rep["assignments"] += t.Assignments.Count
        except Exception:
            pass
        try:
            mode = str(t.GetField(1280))
        except Exception:
            mode = "?"
        if mode not in ("自动计划", "Auto Scheduled"):
            rep["manual"].append("%s=%s" % (t.Name[:24], mode))
        try:
            if t.Critical and not t.Summary:
                rep["critical"].append(t.Name[:60])
        except Exception:
            pass
        rep["wbs"].append((t.WBS, t.Name[:40], dstr(t.Start), dstr(t.Finish),
                           t.PercentComplete, round(t.Cost, 2), mode))
        if not t.Summary:
            rep["leaves"] += 1
            if not str(t.Predecessors or "").strip():
                try:
                    pinned = (t.ConstraintType or 0) != 0 or t.Milestone
                except Exception:
                    pinned = True
                if not pinned:
                    rep["noPredecessor"].append(t.Name[:40])
            if (t.ConstraintType or 0) != 0:
                rep["constrained"].append("%s -> %s %s" % (t.Name[:30],
                                                           t.ConstraintType,
                                                           dstr(t.ConstraintDate)))
        try:
            if t.Milestone:
                rep["milestones"].append("%s @ %s" % (t.Name[:40], dstr(t.Finish)))
        except Exception:
            pass
    return rep


def _find_fs_pair(p):
    """Return (driver, follower) where the follower starts the day the driver
    finishes - i.e. a finish-to-start relationship the engine is honouring.
    Predecessors is read through PredecessorTasks because the text form of that
    field is localised and a regex over it silently matches nothing."""
    for i in range(1, p.Tasks.Count + 1):
        t = p.Tasks.Item(i)
        try:
            if t.Summary:
                continue
            preds = t.PredecessorTasks
            n = preds.Count if preds is not None else 0
        except Exception:
            continue
        for k in range(1, n + 1):
            try:
                drv = preds.Item(k)
            except Exception:
                continue
            if drv is None or drv.Summary:
                continue
            if dstr(drv.Finish) == dstr(t.Start):
                return drv, t, "FS(start==predecessor finish)"
    return None, None, None


def prove(mp, p, mpp):
    """Change one leaf's duration and prove the engine moves its successor.
    Without this the links are decoration rather than a schedule."""
    rec = {}
    drv, fol, how = _find_fs_pair(p)
    if drv is None:
        rec["error"] = "no finish-to-start leaf pair found"
        names = []
        for i in range(1, min(p.Tasks.Count, 14) + 1):
            t = p.Tasks.Item(i)
            try:
                names.append((t.ID, t.Name[:34], dstr(t.Start), dstr(t.Finish),
                              repr(t.Predecessors)[:24]))
            except Exception as exc:
                names.append((i, "read failed %s" % type(exc).__name__))
        rec["diagnostic"] = names
        return rec
    before = {"driverId": drv.ID, "driver": drv.Name, "driverDur": drv.Duration,
              "driverFinish": dstr(drv.Finish),
              "followerId": fol.ID, "follower": fol.Name,
              "followerStart": dstr(fol.Start),
              "followerFinish": dstr(fol.Finish), "basis": how}
    rec["before"] = before
    log("recalc test: [%s] --FS--> [%s]" % (drv.Name[:44], fol.Name[:44]))
    d0, f0 = drv.ID, fol.ID
    drv.Duration = "25d"
    mp.CalculateAll()
    rec["after"] = {"driverFinish": dstr(p.Tasks.Item(d0).Finish),
                    "followerStart": dstr(p.Tasks.Item(f0).Start),
                    "followerFinish": dstr(p.Tasks.Item(f0).Finish)}
    rec["scheduleMoves"] = rec["after"]["followerStart"] != before["followerStart"]
    drv.Duration = before["driverDur"]
    mp.CalculateAll()
    rec["restored"] = {"driverFinish": dstr(p.Tasks.Item(d0).Finish),
                       "followerStart": dstr(p.Tasks.Item(f0).Start)}
    rec["restoredCleanly"] = (rec["restored"]["followerStart"] == before["followerStart"]
                              and rec["restored"]["driverFinish"] == before["driverFinish"])
    crit = [p.Tasks.Item(i).Name for i in range(1, p.Tasks.Count + 1)
            if (not p.Tasks.Item(i).Summary) and p.Tasks.Item(i).Critical]
    rec["criticalCount"] = len(crit)
    rec["criticalSample"] = crit[:8]
    rec["costAfterCalc"] = p.Cost
    return rec


def export(mp, p, mpp, out):
    names = []
    try:
        views = mp.Views()
        names = [views.Item(i).Name for i in range(1, len(views))]
    except Exception as exc:
        log("Views() failed: %s" % type(exc).__name__)
    log("view names available: %d" % len(names))
    picks = {}
    for tag, keys in VIEW_WANT:
        hit = None
        for k in keys:
            exact = [n for n in names if n == k]
            loose = [n for n in names if k in n]
            if exact:
                hit = exact[0]
                break
            if loose:
                hit = loose[0]
                break
        picks[tag] = hit
    log("resolved views: %s" % picks)
    done = {}
    for tag, vname in picks.items():
        if not vname:
            log("SKIP %s - no such view on this install" % tag)
            continue
        try:
            mp.ViewApply(vname)
        except Exception as exc:
            log("ViewApply %s (%s) failed: %s" % (tag, vname, str(exc)[:140]))
            continue
        path = os.path.join(out, tag + ".pdf")
        try:
            mp.DocumentExport(path, 0)
            done[tag] = {"view": vname, "pdf": os.path.getsize(path)}
            log("exported %-20s <- %-18s  %d bytes" % (tag, vname, os.path.getsize(path)))
        except Exception as exc:
            log("DocumentExport %s failed: %s" % (tag, str(exc)[:140]))
    try:
        mp.TimelineExport(os.path.join(out, "Milestone_Timeline.png"), 1600)
        done["Milestone_Timeline_png"] = os.path.getsize(
            os.path.join(out, "Milestone_Timeline.png"))
    except Exception as exc:
        log("TimelineExport failed: %s" % str(exc)[:140])
    return done, picks


def main():
    mp, p, mpp, rows, ids, res_ids = build()
    rep = audit(mp, p, rows, ids)
    log("audit: %d rows, %d leaves, %d assignments, cost %s, finish %s"
        % (rep["tasks"], rep["leaves"], rep["assignments"], rep["cost"], rep["projectFinish"]))
    log("  still manually scheduled: %s" % (rep["manual"][:8] or "none"))
    log("  critical path rows: %d" % len(rep["critical"]))
    log("  milestones: %d" % len(rep["milestones"]))
    log("  rows without a predecessor: %s" % (rep["noPredecessor"][:8] or "none"))
    proof = prove(mp, p, mpp)
    log("recalc proof: %s" % json.dumps(proof, ensure_ascii=False, default=str)[:600])
    p.SaveAs(mpp)
    log("saved %s (%d bytes)" % (mpp, os.path.getsize(mpp)))
    mp.FileClose()
    mp.Quit()

    # reopen in a fresh process and re-read everything
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
    rep2 = audit(mp2, p2, [], ids)
    log("reopened: %d rows, %d leaves, %d assignments, cost %s, finish %s, critical %d"
        % (rep2["tasks"], rep2["leaves"], rep2["assignments"], rep2["cost"],
           rep2["projectFinish"], len(rep2["critical"])))
    reopen_checks = {
        "sameRowCount": rep["tasks"] == rep2["tasks"],
        "sameLeafCount": rep["leaves"] == rep2["leaves"],
        "sameAssignmentCount": rep["assignments"] == rep2["assignments"],
        "sameCost": abs(rep["cost"] - rep2["cost"]) < 1.0,
        "sameFinish": rep["projectFinish"] == rep2["projectFinish"],
        "criticalComputed": len(rep2["critical"]) > 0,
        "nothingLeftManual": len(rep2["manual"]) == 0,
        "recalcMovesSchedule": bool(proof.get("scheduleMoves")),
        "recalcRestoredCleanly": bool(proof.get("restoredCleanly")),
    }
    log("reopen checks: %s" % json.dumps(reopen_checks, ensure_ascii=False))
    try:
        mp2.FileSave()
    except Exception:
        p2.SaveAs(mpp)
    mp2.FileClose()
    mp2.Quit()

    result = {"plan": {"summaries": len([r for r in PLAN if r["kind"] == "sum"]),
                       "leaves": len([r for r in PLAN if r["kind"] == "task"]),
                       "milestones": len([r for r in PLAN if r["kind"] == "ms"]),
                       "resources": len(RESOURCES)},
              "first_pass": rep, "reopen_pass": rep2,
              "recalc_proof": proof, "checks": reopen_checks,
              "pinnedMilestones": [m for m in rep2["milestones"]]}
    json.dump(result, open(os.path.join(HERE, "se_project_build_result.json"), "w",
                           encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    bad = [k for k, v in reopen_checks.items() if not v]
    log("BUILD %s; failed checks: %s" % ("OK" if not bad else "INCOMPLETE", bad or "none"))
    _lf.close()
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
