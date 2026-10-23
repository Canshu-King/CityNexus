"""Runtime probe v4: prove the exact COM calls the generators will use.

Findings carried in from v3: Visio Application.BuildNumber / MasterCount raise
AttributeError on this build, so never read them. Version reads fine.

Log: se_probe_r4.log (line-flushed) so a hang is bisectable.
"""
import datetime
import os
import time
import traceback

D = datetime.datetime
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "se_probe_r4.log")
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
        log("OK   %s -> %s" % (label, r if not hasattr(r, "_oleobj_") else "<comobj>"))
        return r
    except Exception as exc:
        log("FAIL %s -> %s: %s" % (label, type(exc).__name__, str(exc)[:220]))
        return None


def rd(obj, name):
    try:
        return getattr(obj, name)
    except Exception as exc:
        return "<%s>" % type(exc).__name__


def safe(fn, default="<err>"):
    try:
        return fn()
    except Exception as exc:
        return "<%s:%s>" % (type(exc).__name__, str(exc)[:80])


log("############ VISIO ############")
import win32com.client as w32

vis = attempt("Dispatch Visio", lambda: w32.Dispatch("Visio.Application"))
log("Version=%s Visible=%s" % (rd(vis, "Version"), rd(vis, "Visible")))

doc = attempt("Documents.Add", lambda: vis.Documents.Add(""))
page = attempt("Pages.Item(1)", lambda: doc.Pages.Item(1))

for cell, formula in (("PrintPageOrientation", "1"), ("PageWidth", "420mm"),
                      ("PageHeight", "297mm"), ("PrintColors", "2"),
                      ("PrintGridPrint", "0"), ("PrintDocumentPrint", "1")):
    attempt("Cells(%s)" % cell, lambda c=cell, f=formula: setattr(page.PageSheet.Cells(c), "FormulaU", f))
attempt("read page size", lambda: "PageWidth=%.2f PageHeight=%.2f in" % (
    page.PageSheet.Cells("PageWidth").ResultIU, page.PageSheet.Cells("PageHeight").ResultIU))

stencils = {}
for stf in ("BASFLO_M.VSSX", "BASIC_M.VSSX", "UUSEME_M.VSSX", "XFUNC_M.VSSX",
            "CONNEC_M.VSSX", "SERVER_M.VSSX", "FLOWCHT_M.VSSX", "GENERAL_M.VSSX",
            "OBJREL_M.VSSX", "GANTT_M.VSSX", "TIMELN_M.VSSX"):
    def op(stf=stf):
        p = os.path.join(STENCIL, stf)
        if not os.path.exists(p):
            return "FILE MISSING"
        sd = vis.Documents.OpenEx(p, 16)
        stencils[stf] = sd
        names = [sd.Masters.Item(i).Name for i in range(1, sd.Masters.Count + 1)]
        return "count=%d names=%s" % (sd.Masters.Count, names)
    attempt("stencil %s" % stf, op)


def find_master(stf, *subs):
    sd = stencils.get(stf)
    if sd is None:
        return None
    for i in range(1, sd.Masters.Count + 1):
        nm = sd.Masters.Item(i).Name.lower()
        if all(s.lower() in nm for s in subs):
            return sd.Masters.Item(i)
    return None


def drop(stf, subs, x, y, text):
    m = find_master(stf, *subs)
    if m is None:
        return "no master for %s %s" % (stf, subs)
    s = page.Drop(m, x, y)
    s.Text = text
    return "dropped master=%r shape=%r id=%s w=%.2f h=%.2f connSec=%s" % (
        m.Name, s.Name, s.ID, s.Cells("Width").ResultIU, s.Cells("Height").ResultIU,
        s.SectionExists(7, 0))


attempt("Drop process", lambda: drop("BASFLO_M.VSSX", ("process",), 4.0, 8.0, "PROBE PROCESS"))
attempt("Drop decision", lambda: drop("BASFLO_M.VSSX", ("decision",), 4.0, 6.0, "YES?"))
attempt("Drop terminator", lambda: drop("BASFLO_M.VSSX", ("terminator",), 4.0, 10.0, "START"))
attempt("Drop data", lambda: drop("BASFLO_M.VSSX", ("data",), 8.0, 8.0, "DATA"))
attempt("Drop uml actor", lambda: drop("UUSEME_M.VSSX", ("actor",), 2.0, 5.0, "USER"))
attempt("Drop uml usecase", lambda: drop("UUSEME_M.VSSX", ("use case",), 6.0, 5.0, "UC"))
attempt("Drop cylinder/db", lambda: drop("BASIC_M.VSSX", ("cylinder",), 10.0, 5.0, "DB"))

attempt("DrawRectangle band", lambda: (
    lambda r: (setattr(r, "Text", "BAND"),
               setattr(r.Cells("FillForegnd"), "FormulaU", "RGB(238,242,248)"),
               setattr(r.Cells("LineColor"), "FormulaU", "RGB(120,130,150)"),
               r.Name)(0))(page.DrawRectangle(1.0, 1.0, 4.0, 3.0)))

log("shapes on page now = %s" % safe(lambda: page.Shapes.Count))


def shape_count():
    return page.Shapes.Count


attempt("Shapes.Count", shape_count)

con1 = attempt("AutoConnect", lambda: (
    page.Shapes.Item(3).AutoConnect(page.Shapes.Item(1), 3).Name, page.Connects.Count))
attempt("DropConnected", lambda: page.DropConnected(
    find_master("BASFLO_M.VSSX", "process"), page.Shapes.Item(1), 3).Name)
attempt("Drop(ConnectorToolDataObject)", lambda: page.Drop(
    vis.ConnectorToolDataObject, 3.0, 7.0).Name)
attempt("page.Connects.Count", lambda: page.Connects.Count)

attempt("set font/size on shape", lambda: (
    setattr(page.Shapes.Item(1).Cells("Char.Size"), "FormulaU", "9pt"),
    setattr(page.Shapes.Item(1).Cells("Char.Font"), "FormulaU", '="Arial"'),
    page.Shapes.Item(1).Cells("Char.Font").ResultIU))

attempt("shape master name roundtrip", lambda: page.Shapes.Item(1).Master.Name)

vsdx = os.path.join(OUT, "p4.vsdx")
if os.path.exists(vsdx):
    os.remove(vsdx)
attempt("SaveAs", lambda: doc.SaveAs(vsdx))
log("vsdx exists=%s size=%s" % (os.path.exists(vsdx),
                               os.path.getsize(vsdx) if os.path.exists(vsdx) else 0))

png = os.path.join(OUT, "p4.png")
attempt("page.Export PNG", lambda: (os.path.exists(png) and os.remove(png),
                                    page.Export(png), os.path.getsize(png))[2])
pdf = os.path.join(OUT, "p4.pdf")
attempt("ExportAsFixedFormat PDF", lambda: (
    doc.ExportAsFixedFormat(1, pdf, 1, 0), os.path.getsize(pdf))[1])

attempt("close+quit", lambda: (doc.Close(), vis.Quit()))
time.sleep(2)

log("--- reopen cycle ---")
vis2 = attempt("relaunch", lambda: w32.Dispatch("Visio.Application"))
d2 = attempt("Open", lambda: vis2.Documents.Open(vsdx))
attempt("read back", lambda: "pages=%s shapes=%s connects=%s" % (
    d2.PageCount, d2.Pages.Item(1).Shapes.Count, d2.Pages.Item(1).Connects.Count))
attempt("edit+save", lambda: (setattr(d2.Pages.Item(1).Shapes.Item(1), "Text", "EDITED-4"), d2.Save()))
attempt("close+quit2", lambda: (d2.Close(), vis2.Quit()))
time.sleep(1)
vis3 = attempt("relaunch3", lambda: w32.Dispatch("Visio.Application"))
d3 = attempt("Open3", lambda: vis3.Documents.Open(vsdx))
attempt("verify", lambda: "text=%r connects=%s" % (
    d3.Pages.Item(1).Shapes.Item(1).Text, d3.Pages.Item(1).Connects.Count))
attempt("final close", lambda: (d3.Close(), vis3.Quit()))

log("############ PROJECT ############")
mp = attempt("Dispatch MSProject", lambda: w32.Dispatch("MSProject.Application"))
log("Version=%s Visible=%s" % (rd(mp, "Version"), rd(mp, "Visible")))
attempt("Visible=True", lambda: setattr(mp, "Visible", True))
attempt("DisplayAlerts=0", lambda: setattr(mp, "DisplayAlerts", 0))
attempt("FileNew", lambda: mp.FileNew())
p = attempt("ActiveProject", lambda: mp.ActiveProject)
if p is None:
    p = attempt("FileNew(1)", lambda: mp.FileNew(1)) or mp.ActiveProject
log("Name=%s ProjectStart=%s Finish=%s" % (rd(p, "Name"), rd(p, "ProjectStart"), rd(p, "ProjectFinish")))

attempt("ProjectStart set", lambda: setattr(p, "ProjectStart", D(2026, 9, 4, 9, 0)))
attempt("set FictitiousCurrentDate/StatusDate", lambda: setattr(p, "StatusDate", D(2026, 10, 21, 9, 0)))
for prop in ("DefaultTaskScheduled", "DefaultFixedCostAccrual", "DefaultTaskType"):
    attempt("app.%s" % prop, lambda pr=prop: setattr(mp, pr, 0))
attempt("app.Settings.DefaultTaskScheduled", lambda: setattr(mp.Settings, "DefaultTaskScheduled", 0))

t1 = attempt("Add '1 PHASE'", lambda: p.Tasks.Add("1 PROBE PHASE"))
t2 = attempt("Add '1.1 TASK'", lambda: p.Tasks.Add("1.1 PROBE TASK"))
t3 = attempt("Add MS", lambda: p.Tasks.Add("1.2 PROBE MILESTONE"))

attempt("t2 Duration", lambda: setattr(t2, "Duration", "5d"))
attempt("t3 Duration 0d", lambda: setattr(t3, "Duration", "0d"))
attempt("t2 OutlineLevel 2", lambda: setattr(t2, "OutlineLevel", 2))
attempt("t3 OutlineLevel 2", lambda: setattr(t3, "OutlineLevel", 2))
attempt("t2 Start", lambda: setattr(t2, "Start", D(2026, 9, 7, 9, 0)))
attempt("t2 Predecessors '1FS'", lambda: setattr(t2, "Predecessors", "1FS"))
attempt("t3 Predecessors '2FS'", lambda: setattr(t3, "Predecessors", "2FS"))
attempt("t3 Deadline", lambda: setattr(t3, "Deadline", D(2026, 9, 25)))
attempt("t2 PercentComplete 40", lambda: setattr(t2, "PercentComplete", 40))
attempt("t2 Notes", lambda: setattr(t2, "Notes", "probe note"))
attempt("t2 TaskText", lambda: setattr(t2, "TaskText5", "note5"))
log("t2: WBS=%s Start=%s Finish=%s Duration=%s" % (rd(t2, "WBS"), rd(t2, "Start"), rd(t2, "Finish"), rd(t2, "Duration")))
log("t2 manual fields: Scheduled=%s ScheduledStart=%s" % (rd(t2, "Scheduled"), rd(t2, "ScheduledStart")))
log("t3: Milestone=%s WBS=%s Finish=%s" % (rd(t3, "Milestone"), rd(t3, "WBS"), rd(t3, "Finish")))

attempt("CalculateAll", lambda: mp.CalculateAll())
log("Critical t1=%s t2=%s t3=%s StartSlack t2=%s" % (
    rd(t1, "Critical"), rd(t2, "Critical"), rd(t3, "Critical"), rd(t2, "StartSlack")))

r1 = attempt("Resources.Add", lambda: p.Resources.Add("PROBE DEV"))
for prop, val in (("StandardRate", 180.0), ("OvertimeRate", 270.0), ("CostPerUse", 20.0),
                  ("PeakUnits", 1.0), ("Initials", "PD"), ("Type", 1), ("AccrueAt", 1)):
    attempt("res.%s" % prop, lambda pr=prop, v=val: setattr(r1, pr, v))
log("res readback: StdRate=%s CostPerUse=%s Type=%s StandardRatePerTimeUnits=%s" % (
    rd(r1, "StandardRate"), rd(r1, "CostPerUse"), rd(r1, "Type"),
    rd(r1, "StandardRatePerTimeUnits")))
attempt("res.CostRateTables", lambda: r1.CostRateTables.Count)
attempt("res.Fields(stdrate)", lambda: r1.GetField(3))

attempt("t2.Assignments.Add", lambda: t2.Assignments.Add(r1))
attempt("mp.AssignResource", lambda: mp.AssignResource(t2, 0, -1, r1))
attempt("CalculateAll2", lambda: mp.CalculateAll())
log("t2 assignments=%s cost=%s work=%s ; project cost=%s" % (
    rd(t2, "Assignments"), rd(t2, "Cost"), rd(t2, "RegularWork"), rd(p, "Cost")))
log("res cost=%s work=%s" % (rd(r1, "Cost"), rd(r1, "Work")))

attempt("BaselineSave", lambda: mp.BaselineSave(True, 1, 1, True))
log("t2 BaselineStart=%s BaselineFinish=%s" % (rd(t2, "BaselineStart"), rd(t2, "BaselineFinish")))

mpp = os.path.join(OUT, "p4.mpp")
if os.path.exists(mpp):
    os.remove(mpp)
attempt("SaveAs mpp", lambda: p.SaveAs(mpp))
log("mpp exists=%s size=%s" % (os.path.exists(mpp),
                              os.path.getsize(mpp) if os.path.exists(mpp) else 0))

for v in ("Gantt Chart", "Network Diagram", "Task Sheet", "Resource Sheet",
          "Timeline", "Calendar", "Task Usage", "Critical"):
    attempt("ViewApply %s" % v, lambda vv=v: mp.ViewApply(vv))

gp = os.path.join(OUT, "p4_gantt.pdf")
attempt("DocumentExport PDF (FileType=0)", lambda: (
    mp.ViewApply("Gantt Chart"), mp.DocumentExport(gp, 0), os.path.getsize(gp))[2])
gpng = os.path.join(OUT, "p4_gantt.png")
attempt("DocumentExport PNG (FileType=2)", lambda: (
    mp.ViewApply("Gantt Chart"), mp.DocumentExport(gpng, 2), os.path.getsize(gpng))[2])
attempt("TimelineExport", lambda: mp.TimelineExport(False, 1200))

attempt("close+quit", lambda: (mp.FileClose(), mp.Quit()))
time.sleep(2)

log("--- mpp reopen cycle ---")
mp2 = attempt("relaunch mp", lambda: w32.Dispatch("MSProject.Application"))
attempt("visible+alerts", lambda: (setattr(mp2, "Visible", True), setattr(mp2, "DisplayAlerts", 0)))
attempt("FileOpen", lambda: mp2.FileOpen(mpp))
p2 = attempt("ActiveProject2", lambda: mp2.ActiveProject)
log("reopen tasks=%s resources=%s cost=%s start=%s" % (
    rd(p2, "Tasks"), rd(p2, "Resources"), rd(p2, "Cost"), rd(p2, "ProjectStart")))
log("reopen t2 name=%s dur=%s pred=%s wbs=%s assignments=%s" % (
    safe(lambda: p2.Tasks.Item(2).Name), rd(p2.Tasks.Item(2), "Duration"),
    rd(p2.Tasks.Item(2), "Predecessors"), rd(p2.Tasks.Item(2), "WBS"),
    safe(lambda: p2.Tasks.Item(2).Assignments.Count)))
log("before: t2 finish=%s t3 finish=%s" % (rd(p2.Tasks.Item(2), "Finish"), rd(p2.Tasks.Item(3), "Finish")))
attempt("change t2 duration 5d->15d", lambda: setattr(p2.Tasks.Item(2), "Duration", "15d"))
attempt("recalc", lambda: mp2.CalculateAll())
log("after : t2 finish=%s t3 finish=%s (dates must have moved)" % (
    rd(p2.Tasks.Item(2), "Finish"), rd(p2.Tasks.Item(3), "Finish")))
attempt("save2", lambda: p2.Save())
attempt("quit2", lambda: (mp2.FileClose(), mp2.Quit()))

log("############ DONE ############")
log("artifacts: " + ", ".join("%s=%d" % (f, os.path.getsize(os.path.join(OUT, f)))
                              for f in sorted(os.listdir(OUT)) if f.startswith("p4")))
_fh.close()
