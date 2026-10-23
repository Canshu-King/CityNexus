"""Runtime probe v3: prove the exact COM calls the generators will use.

Every candidate is tried in its own try/except and logged, so a hang is
bisectable and a failed shape of an API is visible rather than silent.
Log: se_probe_r3.log  (line-flushed)
"""
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "se_probe_r3.log")
OUT = os.path.join(HERE, "_se_smoke")
os.makedirs(OUT, exist_ok=True)
STENCIL = r"C:\Program Files\Microsoft Office\root\Office16\Visio Content\2052"

_fh = open(LOG, "w", encoding="utf-8", buffering=1)
_t0 = time.time()


def log(msg):
    _fh.write("[%6.1fs] %s\n" % (time.time() - _t0, msg))
    _fh.flush()


def attempt(label, fn):
    try:
        r = fn()
        log("OK   %s -> %s" % (label, r))
        return r
    except Exception as exc:
        log("FAIL %s -> %s: %s" % (label, type(exc).__name__, str(exc)[:200]))
        return None


log("############ VISIO ############")
import win32com.client as w32

vis = attempt("DispatchEx Visio", lambda: w32.DispatchEx("Visio.Application"))
if vis is None:
    log("FATAL: cannot start Visio")
    _fh.close()
    sys.exit(1)
log("Visio Version=%s Build=%s" % (vis.Version, vis.BuildNumber))

doc = attempt("Documents.Add('')", lambda: vis.Documents.Add(""))
page = attempt("Pages.Item(1)", lambda: doc.Pages.Item(1))

# --- page setup: A3 landscape ---
for cell, formula in (("PrintPageOrientation", "1"), ("PageWidth", "420mm"),
                      ("PageHeight", "297mm"), ("PrintGridPrint", "0"),
                      ("PrintColor", "2"), ("LockWidthToGuide", "1"),
                      ("LockHeightToGuide", "1")):
    attempt("page.PageSheet.Cells(%s)" % cell,
            lambda c=cell, f=formula: setattr(page.PageSheet.Cells(c), "FormulaU", f))
log("page size now = %s x %s in" % (page.PageSheet.Cells("PageWidth").ResultIU,
                                    page.PageSheet.Cells("PageHeight").ResultIU))

# --- stencil masters ---
found = {}
for stf in ("BASFLO_M.VSSX", "BASIC_M.VSSX", "UUSEME_M.VSSX", "XFUNC_M.VSSX",
            "CONNEC_M.VSSX", "SERVER_M.VSSX", "GANTT_M.VSSX"):
    p = os.path.join(STENCIL, stf)

    def op(p=p, stf=stf):
        if not os.path.exists(p):
            return "FILE MISSING"
        sd = vis.Documents.OpenEx(p, 16)  # visOpenROI
        names = [sd.Masters.Item(i).Name for i in range(1, sd.Masters.Count + 1)]
        found[stf] = sd
        return "masters=%d names=%s" % (sd.Masters.Count, names[:24])
    attempt("open stencil %s" % stf, op)

# --- drop a flowchart shape ---
box = None
if "BASFLO_M.VSSX" in found:
    st = found["BASFLO_M.VSSX"]

    def drop_process():
        master = None
        for i in range(1, st.Masters.Count + 1):
            if st.Masters.Item(i).Name.lower().startswith("process"):
                master = st.Masters.Item(i)
                break
        master = master or st.Masters.Item(1)
        s = page.Drop(master, 4.0, 8.0)
        s.Text = "PROBE PROCESS"
        return "master=%s shape id=%s name=%s w=%.2f h=%.2f connpts=%s" % (
            master.Name, s.ID, s.Name, s.Cells("Width").ResultIU,
            s.Cells("Height").ResultIU, s.SectionExists(7, 0))
    box = attempt("page.Drop(process master)", drop_process)

diamond = None
if "BASFLO_M.VSSX" in found:
    def drop_decision():
        st = found["BASFLO_M.VSSX"]
        master = None
        for i in range(1, st.Masters.Count + 1):
            if "decision" in st.Masters.Item(i).Name.lower():
                master = st.Masters.Item(i)
                break
        if master is None:
            return "no decision master; names=%s" % [st.Masters.Item(i).Name for i in range(1, st.Masters.Count + 1)]
        s = page.Drop(master, 4.0, 6.0)
        s.Text = "YES?"
        return "dropped %s id=%s" % (master.Name, s.ID)
    diamond = attempt("page.Drop(decision master)", drop_decision)

# --- UML actor + use case ---
if "UUSEME_M.VSSX" in found:
    def drop_uml():
        st = found["UUSEME_M.VSSX"]
        names = [st.Masters.Item(i).Name for i in range(1, st.Masters.Count + 1)]
        s = page.Drop(st.Masters.Item(1), 2.0, 5.0)
        return "uml masters=%s ; dropped first=%s -> %s" % (names[:12], names[0], s.Name)
    attempt("page.Drop(UML master)", drop_uml)

# --- connectors ---
def connect_by_dropconnected():
    shapes = page.Shapes
    if shapes.Count < 2:
        return "need >=2 shapes, have %d" % shapes.Count
    a = shapes.Item(1)
    st = found.get("BASFLO_M.VSSX")
    m = st.Masters.Item(1)
    newsh = page.DropConnected(m, a, 3)  # placement dir down
    return "DropConnected ok newid=%s connects=%s" % (newsh.ID, page.Connects.Count)
attempt("page.DropConnected", connect_by_dropconnected)


def connect_by_autoconnect():
    shapes = page.Shapes
    a = shapes.Item(1)
    b = shapes.Item(2)
    c = a.AutoConnect(b, 3)
    return "AutoConnect ok connector=%s connects=%s" % (c.Name, page.Connects.Count)
attempt("shape.AutoConnect", connect_by_autoconnect)


def connect_by_toolobject():
    c = page.Drop(vis.ConnectorToolDataObject, 5.0, 7.0)
    return "ConnectorToolDataObject drop ok name=%s" % c.Name
attempt("page.Drop(ConnectorToolDataObject)", connect_by_toolobject)

# --- legend / text / group boxes ---
attempt("page.DrawRectangle bg", lambda: (
    lambda r: (setattr(r, "Text", "LAYER BAND"),
               setattr(r.Cells("FillForegnd"), "FormulaU", "RGB(238,242,248)"),
               setattr(r.Cells("LineColor"), "FormulaU", "RGB(120,130,150)"),
               setattr(r.Cells("GeomFormat"), "FormulaU", "0"))(r)
)(page.DrawRectangle(1.0, 9.0, 3.0, 12.0)))

attempt("font on shape", lambda: (
    lambda s: (setattr(s.Cells("Char.Size"), "FormulaU", "9pt"),
               s.Cells("Char.Font").ResultIU)(0))(page.Shapes.Item(1)))

vsdx = os.path.join(OUT, "p3.vsdx")
if os.path.exists(vsdx):
    os.remove(vsdx)
attempt("SaveAs vsdx", lambda: doc.SaveAs(vsdx))
log("vsdx size=%s" % (os.path.getsize(vsdx) if os.path.exists(vsdx) else "none"))

png = os.path.join(OUT, "p3.png")
attempt("page.Export PNG", lambda: (os.path.exists(png) and os.remove(png),
                                    page.Export(png), os.path.getsize(png))[2])

pdf = os.path.join(OUT, "p3.pdf")
attempt("ExportAsFixedFormat PDF",
        lambda: (doc.ExportAsFixedFormat(1, pdf, 1, 0), os.path.getsize(pdf))[1])

attempt("close+quit", lambda: (doc.Close(), vis.Quit()))
time.sleep(2)

vis2 = attempt("relaunch", lambda: w32.DispatchEx("Visio.Application"))
d2 = attempt("reopen", lambda: vis2.Documents.Open(vsdx))
log("reopen pages=%s shapes=%s" % (d2.PageCount, d2.Pages.Item(1).Shapes.Count))
attempt("edit text", lambda: (setattr(d2.Pages.Item(1).Shapes.Item(1), "Text", "EDITED-3"), d2.Save()))
attempt("close quit 2", lambda: (d2.Close(), vis2.Quit()))
time.sleep(1)
vis3 = attempt("relaunch3", lambda: w32.DispatchEx("Visio.Application"))
d3 = attempt("reopen3", lambda: vis3.Documents.Open(vsdx))
log("after edit+reopen shape1 text=%r  connects=%s"
    % (d3.Pages.Item(1).Shapes.Item(1).Text, d3.Pages.Item(1).Connects.Count))
attempt("cleanup visio", lambda: (d3.Close(), vis3.Quit()))

log("############ PROJECT ############")
mp = attempt("DispatchEx MSProject", lambda: w32.DispatchEx("MSProject.Application"))
if mp is None:
    log("FATAL cannot start Project")
    _fh.close(); sys.exit(1)
attempt("make visible", lambda: setattr(mp, "Visible", True))
attempt("DisplayAlerts=0", lambda: setattr(mp, "DisplayAlerts", 0))
log("Project Version=%s Build=%s Edition=%s" % (mp.Version, mp.Build, mp.Edition))

attempt("FileNew()", lambda: mp.FileNew())
p = mp.ActiveProject
attempt("FileNew(1) fallback", lambda: (p is None and mp.FileNew(1)))
p = mp.ActiveProject
log("Project name=%s Start=%s" % (p.Name, p.ProjectStart))

attempt("ProjectStart", lambda: setattr(p, "ProjectStart", time.mktime(
    time.strptime("2026-09-04 09:00", "%Y-%m-%d %H:%M")) and __import__("datetime").datetime(2026, 9, 4, 9, 0)))
for prop in ("DefaultTaskScheduled", "TaskDefaultScheduled"):
    attempt("app.%s" % prop, lambda pr=prop: setattr(mp, pr, 0))
attempt("app.Settings.DefaultTaskScheduled", lambda: setattr(mp.Settings, "DefaultTaskScheduled", 0))

t1 = attempt("Tasks.Add summary", lambda: p.Tasks.Add("1 PROBE PHASE"))
t2 = attempt("Tasks.Add child", lambda: p.Tasks.Add("1.1 PROBE TASK"))
t3 = attempt("Tasks.Add milestone", lambda: p.Tasks.Add("1.2 PROBE MILESTONE"))
log("tasks count=%s" % p.Tasks.Count)

import datetime
D = datetime.datetime


def set_dur():
    t2.Duration = "5d"
    return t2.Duration
attempt("t2.Duration='5d'", set_dur)
attempt("t3.Duration='0d'", lambda: setattr(t3, "Duration", "0d"))
attempt("t2.OutlineLevel=2", lambda: setattr(t2, "OutlineLevel", 2))
attempt("t3.OutlineLevel=2", lambda: setattr(t3, "OutlineLevel", 2))
attempt("t2.Start", lambda: setattr(t2, "Start", D(2026, 9, 7, 9, 0)))
attempt("t3.ConstraintType", lambda: setattr(t3, "ConstraintType", 4))  # finish no earlier than
attempt("t3.ConstraintDate", lambda: setattr(t3, "ConstraintDate", D(2026, 9, 20, 9, 0)))
attempt("t2.Predecessors", lambda: setattr(t2, "Predecessors", "1FS"))
attempt("t2.Deadline", lambda: setattr(t2, "Deadline", D(2026, 9, 18)))
attempt("t2.PercentComplete", lambda: setattr(t2, "PercentComplete", 40))
attempt("t2.Notes", lambda: setattr(t2, "Notes", "probe note"))
log("t1 WBS=%s t2 WBS=%s t2 ScheduledStart=%s t2 ScheduledFinish=%s t3 Finish=%s"
    % (t1.WBS, t2.WBS, t2.ScheduledStart, t2.ScheduledFinish, t3.Finish))
log("t2 Manual? Active=%s ; t3 Milestone=%s" % (getattr(t2, "Active", "?"), t3.Milestone))

attempt("CalculateAll", lambda: mp.CalculateAll())
log("critical t1=%s t2=%s t3=%s  Slack(t2)=%s" % (t1.Critical, t2.Critical, t3.Critical, t2.StartSlack))

r1 = attempt("Resources.Add", lambda: p.Resources.Add("PROBE DEV"))
for prop, val in (("StandardRate", 180.0), ("CostPerUse", 0.0), ("PeakUnits", 1.0),
                  ("OvertimeRate", 270.0), ("Initials", "PD"), ("Type", 1)):
    attempt("resource.%s" % prop, lambda pr=prop, v=val: setattr(r1, pr, v))
log("resource readback StandardRate=%s CostPerUse=%s" % (r1.StandardRate, r1.CostPerUse))
attempt("r1.Rates table", lambda: r1.CostRateTables.Count)

attempt("Assignments.Add", lambda: t2.Assignments.Add(r1))
attempt("app.AssignResource", lambda: mp.AssignResource(t2, True, -1, r1))
mp.CalculateAll()
log("t2.Assignments=%s t2.Cost=%s t2.RegularWork=%s proj.Cost=%s"
    % (t2.Assignments.Count, t2.Cost, t2.RegularWork, p.Cost))

attempt("BaselineSave", lambda: mp.BaselineSave(True, 1, 1, True))
attempt("baseline readback", lambda: (t2.BaselineStart, t2.BaselineFinish))

mpp = os.path.join(OUT, "p3.mpp")
if os.path.exists(mpp):
    os.remove(mpp)
attempt("SaveAs mpp", lambda: p.SaveAs(mpp))
log("mpp size=%s" % (os.path.getsize(mpp) if os.path.exists(mpp) else "none"))

views = ["Gantt Chart", "Network Diagram", "Task Sheet", "Resource Sheet", "Timeline", "Calendar"]
for v in views:
    attempt("ViewApply %s" % v, lambda vv=v: mp.ViewApply(vv))

pdf1 = os.path.join(OUT, "p3_gantt.pdf")
attempt("DocumentExport PDF (active view)",
        lambda: (mp.ViewApply("Gantt Chart"), mp.DocumentExport(pdf1, 0), os.path.getsize(pdf1))[2])

attempt("close+quit project", lambda: (mp.FileClose(), mp.Quit()))
time.sleep(2)

mp2 = attempt("relaunch project", lambda: w32.DispatchEx("MSProject.Application"))
attempt("visible2", lambda: setattr(mp2, "Visible", True))
attempt("DisplayAlerts0", lambda: setattr(mp2, "DisplayAlerts", 0))
attempt("FileOpen mpp", lambda: mp2.FileOpen(mpp))
p2 = mp2.ActiveProject
log("reopen tasks=%s resources=%s cost=%s" % (p2.Tasks.Count, p2.Resources.Count, p2.Cost))
log("reopen t2 name=%s dur=%s pred=%s wbs=%s" % (
    p2.Tasks.Item(2).Name, p2.Tasks.Item(2).Duration, p2.Tasks.Item(2).Predecessors,
    p2.Tasks.Item(2).WBS))
before = str(p2.Tasks.Item(2).Start)
attempt("edit duration 5d->12d", lambda: setattr(p2.Tasks.Item(2), "Duration", "12d"))
mp2.CalculateAll()
log("recalc: t2 dur=%s finish=%s ; milestone t3 finish=%s (was %s)"
    % (p2.Tasks.Item(2).Duration, p2.Tasks.Item(2).Finish, p2.Tasks.Item(3).Finish,
       p2.Tasks.Item(3).BaselineFinish))
attempt("save2", lambda: p2.Save())
attempt("close+quit2", lambda: (mp2.FileClose(), mp2.Quit()))

log("############ PROBE DONE ############")
log("files: " + ", ".join("%s=%d" % (f, os.path.getsize(os.path.join(OUT, f)))
                          for f in sorted(os.listdir(OUT))))
_fh.close()
