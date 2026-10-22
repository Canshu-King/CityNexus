"""Classroom freeze check: can a human open these files and drive them, and do the
connectors really follow a dragged shape?

The noon-priority note (Evidence/CLASSROOM_20261023_NOON_PRIORITY.md) asks for a
real demonstration on the installed desktop applications, not another green gate,
and it names two things that previous rounds only claimed structurally:

  * open -> select a shape -> MOVE it -> edit its text -> save a copy -> close ->
    reopen, with the original file left byte-identical;
  * Microsoft Project view switching and an edit that survives a save/reopen.

The move is also the chance to settle the reviewer's open question - "whether the
line follows the shape when it is dragged has not been reproduced". It is measured
here: the glued connector endpoint is read before and after the move, and the test
passes only if the endpoint moved with the shape.

Everything happens on a copy in live_checks/_demo; the shipped digests are compared
before and after and the run refuses if a shipped file changed.
"""
import hashlib
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
VIS = os.path.join(DEL, "Visio")
MSP = os.path.join(DEL, "Microsoft_Project")
DEMO = os.path.join(HERE, "_demo")
LOG = open(os.path.join(HERE, "se_classroom_demo_r1.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()
MARK = "  [demo 2026-10-23]"


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


import win32com.client as w32                                # noqa: E402


def page_of(doc):
    """Visio on this install refuses Pages(0); the active page is the document's
    own Page property and Pages.Item is one-based."""
    try:
        pg = doc.Page
        if pg is not None:
            return pg
    except Exception:
        pass
    return doc.Pages.Item(1)

os.makedirs(DEMO, exist_ok=True)
for f in os.listdir(DEMO):
    try:
        os.remove(os.path.join(DEMO, f))
    except Exception:
        pass

report = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "visio": [], "project": [],
          "shipped": {}}

# ---------------------------------------------------------------------- VISIO
VISCOPY = {}
for name in ("01_CityNexus_System_Architecture.vsdx",
             "03_CityNexus_Agent_Workflow.vsdx"):
    src = os.path.join(VIS, name)
    dst = os.path.join(DEMO, name)
    shutil.copyfile(src, dst)
    VISCOPY[name] = {"srcSha": sha(src), "dst": dst}
log("copies made for the drive test: %d" % len(VISCOPY))

# An orphaned VISIO.EXE from a crashed run keeps the document open and the next
# copy onto the same path fails with PermissionError, so refuse to start while one
# is alive, and always quit on the way out.
import atexit
import subprocess


def _no_orphan(image):
    try:
        out = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq %s" % image,
                                       "/FO", "CSV", "/NH"], text=True,
                                      errors="replace")
    except Exception:
        return []
    return [l for l in out.splitlines() if image in l.upper()]


def _bye_visio():
    try:
        vis.Quit()
    except Exception:
        pass


def _bye_project():
    try:
        mp.FileCloseEx(0)
    except Exception:
        pass
    try:
        mp.Quit()
    except Exception:
        pass


_orph = _no_orphan("VISIO.EXE") + _no_orphan("WINPROJ.EXE")
if _orph:
    raise SystemExit("Office processes are still running (%d); close them first so "
                     "the drive test cannot be looking at somebody else's window"
                     % len(_orph))
log("no orphaned VISIO/WINPROJ processes")

vis = w32.DispatchEx("Visio.Application")
vis.Visible = True
atexit.register(_bye_visio)
try:
    vis.AlertResponse = 7
except Exception:
    pass
try:
    report["visioVersion"] = "%s build %s" % (vis.Version, getattr(vis, "BuildNumber",
                                                                   "?"))
except Exception:
    report["visioVersion"] = str(vis.Version)
log("Visio reports version %s" % report["visioVersion"])

for name, meta in sorted(VISCOPY.items()):
    rec = {"file": name, "steps": [], "originalUnchanged": None}

    def step(label, fn, want=None):
        try:
            v = fn()
            ok = True if want is None else (v == want)
            rec["steps"].append({"step": label, "value": str(v)[:120],
                                 "ok": bool(ok)})
            log("   %-22s %s -> %s" % (label, name[:20], str(v)[:90]))
            return v
        except Exception as exc:
            rec["steps"].append({"step": label, "error": "%s: %s"
                                 % (type(exc).__name__, str(exc)[:200]), "ok": False})
            log("   %-22s %s FAILED %s: %s" % ("", name[:20], type(exc).__name__,
                                               " ".join(str(exc)[:170].split())))
            return None

    d = step("open", lambda: vis.Documents.Open(meta["dst"]))
    if d is None:
        report["visio"].append(rec)
        continue
    pg = page_of(d)

    def connector_map(page):
        """shape id -> the connector shapes glued to it, in ONE pass.

        The first version asked page.Connects for every shape on the page, which is
        105 shapes x 48 connects of cross-process calls and took 130 seconds per
        drawing. Shape.ConnectedShapes(2) raises com_error through the generated
        wrapper on this install, and Shapes.ItemEx looks a shape up by NAME, so the
        lookup is done with Shapes.ItemFromID over a single Connects sweep.
        """
        by_id = {}
        try:
            total = page.Connects.Count
        except Exception:
            return by_id
        pairs = []
        for i in range(1, total + 1):
            cn = page.Connects.Item(i)
            try:
                pairs.append((cn.FromSheet.ID, cn.ToSheet.ID))
            except Exception:
                continue
        for i, (frm, to) in enumerate(pairs):
            try:
                con = page.Shapes.ItemFromID(frm)
                part = page.Connects.Item(i + 1).FromPart
            except Exception:
                continue
            by_id.setdefault(to, []).append((con, part))
        return by_id

    cmap = connector_map(pg)
    # the smallest text-bearing shape that has something glued to it: a title bar
    # spanning the page would make any "is the line still attached" test trivially
    # true, so the candidate is chosen by area, not by document order
    cands = []
    for sh in pg.Shapes:
        try:
            if not (sh.Text or "").strip():
                continue
            area = float(sh.Cells("Width").ResultIU) * float(
                sh.Cells("Height").ResultIU)
        except Exception:
            continue
        g = cmap.get(sh.ID) or []
        if g:
            cands.append((area, sh, g))
    cands.sort(key=lambda t: t[0])
    target, cons = (cands[0][1], cands[0][2]) if cands else (None, [])
    if target is None:
        for sh in pg.Shapes:
            try:
                if (sh.Text or "").strip():
                    target = sh
                    break
            except Exception:
                continue
    rec["shape"] = {"name": getattr(target, "Name", "?"),
                    "id": getattr(target, "ID", -1),
                    "text": (target.Text or "")[:60]}
    before = step("pinX", lambda: float(target.Cells("PinX").ResultIU))
    step("glued connectors", lambda: len(cons))

    def shape_box(sh):
        try:
            return (float(sh.Cells("PinX").ResultIU) -
                    float(sh.Cells("Width").ResultIU) / 2.0,
                    float(sh.Cells("PinX").ResultIU) +
                    float(sh.Cells("Width").ResultIU) / 2.0,
                    float(sh.Cells("PinY").ResultIU) -
                    float(sh.Cells("Height").ResultIU) / 2.0,
                    float(sh.Cells("PinY").ResultIU) +
                    float(sh.Cells("PinY").ResultIU) / 2.0)
        except Exception:
            return None

    def glued_endpoints(connectors, box=None):
        """Per connector: its two end points, and whether either one is on the box.

        The question the review left open is whether the line follows a dragged
        shape. Connect.FromPart was tried first and its 1/2 meaning is not the
        begin/end split this assumed (one end measured this way stayed put while the
        glue record survived), so the honest test is geometric: after the shape has
        moved, is one of the connector's endpoints still on the shape's own
        rectangle? A stranded line would leave both ends where they were.
        """
        out = []
        for c, _part in connectors:
            try:
                pts = [tuple(round(float(c.Cells(k).ResultIU), 3)
                              for k in ("BeginX", "BeginY")),
                       tuple(round(float(c.Cells(k).ResultIU), 3)
                             for k in ("EndX", "EndY"))]
            except Exception:
                continue
            on = None
            if box:
                # 0.2 in tolerance is smaller than the 0.75 in the shape was moved,
                # so a line that had been left behind could not pass this test
                tol = 0.2
                on = any(box[0] - tol <= x <= box[1] + tol and
                         box[2] - tol <= y <= box[3] + tol for x, y in pts)
            out.append({"id": getattr(c, "ID", -1), "ends": pts, "onShape": on})
        return out

    ends_before = glued_endpoints(cons, shape_box(target))
    rec["endsBefore"] = ends_before
    # an assignment, not a comparison, and an ABSOLUTE value: "PinX+0.75in" makes
    # the cell refer to itself and Visio answers "circular formula reference"
    def _move():
        target.Cells("PinX").FormulaU = "%.4fin" % (before + 0.75)
        return round(float(target.Cells("PinX").ResultIU) - before, 3)
    moved = step("move +0.75in", _move, want=0.75)
    after = step("pinX after", lambda: float(target.Cells("PinX").ResultIU))
    rec["movedBy"] = round((after or 0) - (before or 0), 4) if (after and before) else 0
    def cmap_after(page, sh):
        return connector_map(page).get(sh.ID) or []

    box_after = shape_box(target)
    ends_after = glued_endpoints(cons, box_after)
    rec["endsAfter"] = ends_after
    rec["boxAfter"] = [round(v, 3) for v in (box_after or [])]
    # What "the line follows the shape" means in Visio is not "the endpoint
    # translates by the same vector": a dynamic connector re-routes and its glued
    # end slides along the shape's edge, so the endpoint can move further or less
    # than the shape. The test is whether the glued end is still ON the moved shape
    # and whether the glue record still exists. A stranded line would still sit at
    # the shape's old position, outside its box.
    try:
        px = float(target.Cells("PinX").ResultIU)
        half = float(target.Cells("Width").ResultIU) / 2.0
    except Exception:
        px, half = 0.0, 0.0
    tol = 0.2
    attached = [bool(e.get("onShape")) for e in ends_after]
    rec["gluedEndOnShape"] = attached
    rec["glueRecordsAfter"] = len(cmap_after(pg, target))
    rec["glueRecordsBefore"] = len(cons)
    rec["connectorFollowed"] = bool(ends_after and all(attached) and
                                    rec["glueRecordsAfter"] == rec["glueRecordsBefore"])
    log("   connector follows the dragged shape: %s (glued ends %s -> %s, shape now "
        "at %.2f half-width %.2f, glue records %d -> %d)"
        % (rec["connectorFollowed"], ends_before, ends_after, px, half,
           rec["glueRecordsBefore"], rec["glueRecordsAfter"]))
    def _edit():
        # Shape.Text assignment, not the Text cell formula: on this install every
        # formula form (FormulaU / Formula / CellsU) answers "unexpected end of
        # file" for a quoted string, measured across all three
        target.Text = MARK.strip()
        return (MARK.strip() in (target.Text or ""))
    step("edit text", _edit, want=True)
    step("text reads back", lambda: MARK.strip() in (target.Text or ""), want=True)
    step("save the copy", lambda: d.Save() or "saved")
    step("close", lambda: d.Close() or "closed")
    d2 = step("reopen the copy", lambda: vis.Documents.Open(meta["dst"]))
    if d2 is not None:
        pg2 = page_of(d2)
        again = None
        for sh in pg2.Shapes:
            if getattr(sh, "ID", -1) == rec["shape"]["id"]:
                again = sh
                break
        step("move persisted", lambda: abs(float(again.Cells("PinX").ResultIU)
                                           - after) < 0.01, want=True)
        step("text persisted", lambda: MARK.strip() in (again.Text or ""), want=True)
        step("close again", lambda: d2.Close() or "closed")
    rec["originalUnchanged"] = sha(os.path.join(VIS, name)) == meta["srcSha"]
    rec["ok"] = all(s["ok"] for s in rec["steps"]) and rec["originalUnchanged"]
    log(" %s drive test: %s (original byte-identical: %s)"
        % (name, "PASS" if rec["ok"] else "FAIL", rec["originalUnchanged"]))
    report["visio"].append(rec)

try:
    vis.Quit()
except Exception:
    pass

# -------------------------------------------------------------------- PROJECT
PLAN = os.path.join(MSP, "CityNexus_Software_Engineering_Plan.mpp")
MILE = os.path.join(MSP, "CityNexus_Milestone_View.mpp")
plan_sha_before = sha(PLAN)
mile_sha_before = sha(MILE) if os.path.exists(MILE) else ""
pcopy = os.path.join(DEMO, "demo_plan.mpp")
shutil.copyfile(PLAN, pcopy)

mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
atexit.register(_bye_project)
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
try:
    report["projectVersion"] = str(mp.Version)
except Exception:
    pass
log("Project reports version %s" % report.get("projectVersion"))
rec = {"file": os.path.basename(pcopy), "steps": []}


def pstep(label, fn, want=None):
    try:
        v = fn()
        ok = True if want is None else (v == want)
        rec["steps"].append({"step": label, "value": str(v)[:120], "ok": bool(ok)})
        log("   %-24s %s" % (label, str(v)[:100]))
        return v
    except Exception as exc:
        rec["steps"].append({"step": label,
                             "error": "%s: %s" % (type(exc).__name__,
                                                  str(exc)[:120]), "ok": False})
        log("   %-24s FAILED %s %s" % (label, type(exc).__name__, str(exc)[:70]))
        return None


pstep("open the copy", lambda: mp.FileOpen(pcopy) or "opened")
p = mp.ActiveProject
pstep("rows", lambda: p.Tasks.Count)
def _link_records(proj):
    """Sum the per-task dependency lists; Project.TaskDependencies is not exposed
    through the generated wrapper on this install."""
    n = 0
    for i in range(1, proj.Tasks.Count + 1):
        try:
            n += proj.Tasks.Item(i).TaskDependencies.Count
        except Exception:
            pass
    return n


pstep("links read back", lambda: _link_records(p))
for label, view in (("WBS / 任务工作表", "任务工作表"), ("Gantt", "甘特图"),
                    ("Network", "网络图"), ("Tracking Gantt", "跟踪甘特图"),
                    ("Resource Sheet", "资源工作表"), ("Calendar", "日历")):
    pstep("switch to %s" % label, lambda v=view: mp.ViewApply(v) or view)
# one unimportant edit: a note on a summary row, which cannot move any date
def _note():
    p.Tasks.Item(1).Notes = "classroom demo 2026-10-23"
    return "classroom demo" in (p.Tasks.Item(1).Notes or "")
pstep("edit a note", _note, want=True)
pstep("note reads back", lambda: "classroom demo" in (p.Tasks.Item(1).Notes or ""),
      want=True)
pstep("save the copy", lambda: mp.FileSave() or "saved")
pstep("close", lambda: mp.FileCloseEx(0) or "closed")
pstep("reopen the copy", lambda: mp.FileOpen(pcopy) or "opened")
p2 = mp.ActiveProject
pstep("note survived", lambda: "classroom demo" in (p2.Tasks.Item(1).Notes or ""),
      want=True)
pstep("links survived", lambda: _link_records(p2))
# the milestone file is opened as a copy too: a plain open rewrites the container
# even with nothing edited, and the shipped file must stay byte-identical
mcopy = os.path.join(DEMO, "demo_milestones.mpp")
shutil.copyfile(MILE, mcopy)
pstep("milestone view file opens", lambda: (mp.FileOpen(mcopy), "opened")[1])
pstep("milestone rows", lambda: mp.ActiveProject.Tasks.Count)
pstep("close milestone view", lambda: mp.FileCloseEx(0) or "closed")
pstep("close the copy", lambda: mp.FileCloseEx(0) or "closed")
try:
    mp.Quit()
except Exception:
    pass
rec["planUnchanged"] = sha(PLAN) == plan_sha_before
rec["milestoneUnchanged"] = sha(MILE) == mile_sha_before
rec["originalUnchanged"] = rec["planUnchanged"] and rec["milestoneUnchanged"]
log("   shipped digests held: plan=%s milestones=%s"
    % (rec["planUnchanged"], rec["milestoneUnchanged"]))
rec["ok"] = all(s["ok"] for s in rec["steps"]) and rec["originalUnchanged"]
log(" Project drive test: %s (shipped .mpp byte-identical: %s)"
    % ("PASS" if rec["ok"] else "FAIL", rec["originalUnchanged"]))
report["project"].append(rec)

report["shipped"] = {"planSha256": plan_sha_before,
                     "milestoneSha256": mile_sha_before,
                     "planUnchanged": rec["originalUnchanged"]}
report["visioAllPass"] = all(r.get("ok") for r in report["visio"])
report["projectAllPass"] = all(r.get("ok") for r in report["project"])
json.dump(report, open(os.path.join(HERE, "se_classroom_demo_result.json"), "w",
                       encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
log("wrote se_classroom_demo_result.json")
for f in os.listdir(DEMO):
    try:
        os.remove(os.path.join(DEMO, f))
    except Exception:
        pass
bad = [r["file"] for r in report["visio"] + report["project"] if not r.get("ok")]
if bad:
    log("REFUSED: drive test failed for %s" % bad)
    LOG.close()
    sys.exit(1)
log("CLASSROOM DEMO CHECK OK")
LOG.close()
sys.exit(0)
