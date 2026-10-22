"""Probe v7 - the last gaps.

Carried in from v6:
  Visio: masters + GlueTo + follow-on-move + PNG/PDF export all PROVEN.
  Project: field 1280 is the Schedule field, value '手动计划'; the allowed
  values named by Project itself are 自动排定计划 / 手动排定计划.
Open gaps proven here:
  G1 global view names (Project.Views only exposed 3)
  G2 auto-schedule flip makes a successor move
  G3 resource assignment (p.Assignments missing; Task.Assignments.Add arg shape)
  G4 resource standard rate actually sticks and produces cost
  G5 PDF export of Gantt / Network / Task Sheet / Resource Sheet
  G6 Visio line-style cells individually (EndArrowSize / Pattern / Weight)
"""
import datetime
import os
import time

D = datetime.datetime
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_se_smoke")
STENCIL = r"C:\Program Files\Microsoft Office\root\Office16\Visio Content\2052"
_fh = open(os.path.join(HERE, "se_probe_r7.log"), "w", encoding="utf-8", buffering=1)
_t0 = time.time()


def log(m):
    _fh.write("[%6.1fs] %s\n" % (time.time() - _t0, m))
    _fh.flush()


def attempt(label, fn):
    try:
        r = fn()
        log("OK   %s -> %s" % (label, "<comobj>" if hasattr(r, "_oleobj_") else str(r)[:400]))
        return r
    except Exception as exc:
        log("FAIL %s -> %s: %s" % (label, type(exc).__name__, str(exc)[:240]))
        return None


import win32com.client as w32
import win32com.client.dynamic as dyn

log("################ PROJECT ################")
mp = attempt("Dispatch", lambda: w32.Dispatch("MSProject.Application"))
attempt("visible", lambda: setattr(mp, "Visible", True))
attempt("alerts", lambda: setattr(mp, "DisplayAlerts", 0))
attempt("FileNew", lambda: mp.FileNew())
p = mp.ActiveProject
attempt("ProjectStart", lambda: setattr(p, "ProjectStart", D(2026, 9, 4, 9, 0)))

log("--- G1 view name sources ---")
attempt("Project.Views count", lambda: p.Views.Count)
appviews = attempt("Application.Views count", lambda: len(mp.Views))
names = attempt("Application.Views names", lambda: [mp.Views.Item(i).Name for i in range(1, len(mp.Views) + 1)])
if names:
    log("  total=%d" % len(names))
    for probe in ("甘特", "网络", "工作表", "资源", "时间", "日历", "里程碑", "跟踪", "详细"):
        log("   %-8s -> %s" % (probe, [n for n in names if probe in n][:10]))
    log("  ALL: %s" % names)

log("--- G2 auto schedule ---")
A = attempt("add A", lambda: p.Tasks.Add("A DRIVER"))
B = attempt("add B", lambda: p.Tasks.Add("B FOLLOWER"))
C = attempt("add C", lambda: p.Tasks.Add("C MILESTONE"))
attempt("durs", lambda: (setattr(A, "Duration", "3d"), setattr(B, "Duration", "2d"),
                          setattr(C, "Duration", "0d")))
attempt("links", lambda: (setattr(B, "Predecessors", "%dFS" % A.ID),
                          setattr(C, "Predecessors", "%dFS" % B.ID)))
log("  A sched field(1280) before = %s" % attempt("read 1280", lambda: A.GetField(1280)))
for val in ("自动排定计划", "自动计划", 0):
    ok = attempt("A.SetField(1280,%r)" % val, lambda v=val: A.SetField(1280, v))
    if ok is not None:
        break
for t in (A, B, C):
    attempt("set all auto", lambda x=t: x.SetField(1280, "自动排定计划"))
attempt("calc", lambda: mp.CalculateAll())
log("  sched after = %s" % attempt("read 1280", lambda: A.GetField(1280)))
log("  A=%s..%s B=%s..%s C=%s" % (A.Finish, B.Start, B.Finish, C.Finish, ""))
attempt("A 3d->9d", lambda: setattr(A, "Duration", "9d"))
attempt("calc2", lambda: mp.CalculateAll())
log("  DECISIVE after A=9d: A finish=%s  B start=%s  B finish=%s  C finish=%s"
    % (A.Finish, B.Start, B.Finish, C.Finish))
log("  Critical A=%s B=%s C=%s" % (A.Critical, B.Critical, C.Critical))

log("--- G3/G4 resources, rates, assignments ---")
R1 = attempt("res add", lambda: p.Resources.Add("DEV ONE"))
attempt("res type FIRST", lambda: setattr(R1, "Type", 1))
for way in (
    ("StandardRate float", lambda: setattr(R1, "StandardRate", 180)),
    ("StandardRate str", lambda: setattr(R1, "StandardRate", "180")),
    ("StandardRate str/h", lambda: setattr(R1, "StandardRate", "180/h")),
    ("SetField scan", lambda: [R1.SetField(i, 180) for i in []]),
    ("PayRates.Add", lambda: R1.CostRateTables.Item("A").PayRates.Add(D(2026, 1, 1), 180, 270, 0)),
    ("PayRates.Item(2) read", lambda: R1.CostRateTables.Item("A").PayRates.Item(2).StandardRate),
    ("PayRates.Item(1).StdRate=", lambda: setattr(
        R1.CostRateTables.Item("A").PayRates.Item(1), "StandardRate", 180)),
):
    attempt("rate %s" % way[0], way[1])
attempt("res MaxUnits after type", lambda: setattr(R1, "MaxUnits", 1.0))
attempt("res StdRate readback", lambda: R1.StandardRate)
attempt("res CostPerUse readback", lambda: R1.CostPerUse)
attempt("payrate rows", lambda: [(i, str(R1.CostRateTables.Item("A").PayRates.Item(i).StandardRate),
                                  str(R1.CostRateTables.Item("A").PayRates.Item(i).EffectiveDate))
                                 for i in range(1, 4)])
log("  resource field scan for rate fields:")
for i in list(range(0, 40)) + list(range(1100, 1400)):
    try:
        v = R1.GetField(i)
    except Exception:
        continue
    sv = str(v)
    if "¥" in sv or "费" in sv or "率" in sv:
        log("    id=%s value=%s" % (i, sv))

dyn_p = attempt("dynamic p", lambda: dyn.Dispatch(p._oleobj_))
for shape in (
    ("p.Assignments.Add(A.ID,R.ID,1)", lambda: p.Assignments.Add(A.ID, R1.ID, 1)),
    ("dyn.Assignments.Add(A.ID,R1.ID,1)", lambda: dyn_p.Assignments.Add(A.ID, R1.ID, 1)),
    ("A.Assignments.Add(A.ID,R1.ID,1)", lambda: A.Assignments.Add(A.ID, R1.ID, 1)),
    ("A.Assignments.Add(R1.ID)", lambda: A.Assignments.Add(R1.ID)),
    ("A.Assignments.Add(R1)", lambda: A.Assignments.Add(R1)),
    ("mp.ResourceAssignment", lambda: mp.ResourceAssignment(A.ID, R1.ID)),
    ("mp.AssignResource", lambda: mp.AssignResource(A, 0, -1, R1)),
    ("A.SetField(74,R1.Name)", lambda: A.SetField(74, R1.Name)),
):
    got = attempt(shape[0], shape[1])
    if got is not None:
        log("  >>> first assignment shape that worked: %s" % shape[0])
        break
attempt("calc3", lambda: mp.CalculateAll())
log("  A.Assignments.Count=%s A.ResourceNames=%r A.Work=%s A.Cost=%s R1.Cost=%s projCost=%s"
    % (attempt("ac", lambda: A.Assignments.Count), attempt("rn", lambda: A.ResourceNames),
       attempt("aw", lambda: A.Work), attempt("acost", lambda: A.Cost),
       attempt("rc", lambda: R1.Cost), attempt("pc", lambda: p.Cost)))

log("--- percent / milestone / deadline / wbs ---")
attempt("B percent", lambda: setattr(B, "PercentComplete", 50))
attempt("B actual start", lambda: setattr(B, "ActualStart", D(2026, 9, 9, 9, 0)))
attempt("C deadline", lambda: setattr(C, "Deadline", D(2026, 10, 9)))
log("  C.Milestone=%s C.WBS=%s B.WBS=%s B.Percent=%s" % (C.Milestone, C.WBS, B.WBS, B.PercentComplete))
attempt("outline B under A", lambda: setattr(B, "OutlineLevel", 2))
log("  after outline: A.Summary=%s A.WBS=%s B.WBS=%s" % (A.Summary, A.WBS, B.WBS))

log("--- G5 export views ---")
if names:
    picks = {}
    for tag, key in (("Gantt", "甘特图"), ("Network", "网络图"), ("TaskSheet", "任务工作表"),
                     ("ResSheet", "资源工作表"), ("Timeline", "时间表"), ("Tracking", "跟踪")):
        exact = [n for n in names if n == key]
        loose = [n for n in names if key in n]
        picks[tag] = (exact or loose or [None])[0]
    log("  picks=%s" % picks)
    for tag, vn in picks.items():
        if not vn:
            log("  SKIP %s (no such view)" % tag)
            continue
        ok = attempt("ViewApply %s=%s" % (tag, vn), lambda v=vn: mp.ViewApply(v))
        if ok is not None:
            fp = os.path.join(OUT, "v7_%s.pdf" % tag)
            attempt("DocumentExport %s" % tag, lambda f=fp: (
                mp.DocumentExport(f, 0), os.path.getsize(f))[1])
            png = os.path.join(OUT, "v7_%s.png" % tag)
            attempt("EditCopyPicture %s" % tag, lambda f=png: mp.EditCopyPicture(1, 1, 1, "", "", f))

attempt("FileSave as", lambda: p.SaveAs(os.path.join(OUT, "v7.mpp")))
attempt("quit", lambda: (mp.FileClose(), mp.Quit()))

log("################ VISIO line cells ################")
vis = attempt("Dispatch visio", lambda: w32.Dispatch("Visio.Application"))
doc = attempt("doc add", lambda: vis.Documents.Add(""))
pg = doc.Pages.Item(1)
st = vis.Documents.OpenEx(os.path.join(STENCIL, "BASFLO_M.VSSX"), 16)
sa = pg.Drop(st.Masters.Item(1), 3.0, 9.0)
sb = pg.Drop(st.Masters.Item(1), 6.0, 9.0)
con = pg.Drop(vis.ConnectorToolDataObject, 0, 0)
con.Cells("BeginX").GlueTo(sa.Cells("PinX"))
con.Cells("EndX").GlueTo(sb.Cells("PinX"))
for cell, formula in (("Weight", "0.02in"), ("LineColor", "RGB(31,73,125)"),
                      ("EndArrowSize", "3"), ("Pattern", "1"), ("BeginArrow", "0"),
                      ("EndArrow", "4"), ("LineJumpCode", "0")):
    attempt("conn.Cells(%s)" % cell, lambda c=cell, f=formula: setattr(con.Cells(c), "FormulaU", f))
for cell, formula in (("FillForegnd", "RGB(226,236,250)"), ("LineColor", "RGB(31,73,125)"),
                      ("LineWeight", "0.016in"), ("Rounding", "0.05in"),
                      ("Char.Size", "9pt"), ("VerticalAlign", "1"),
                      ("LeftAngle", "0"), ("RightAngle", "0")):
    attempt("box.Cells(%s)" % cell, lambda c=cell, f=formula: setattr(sa.Cells(c), "FormulaU", f))
attempt("connector label", lambda: (setattr(con, "Text", "label"), con.Text))
attempt("page.Add second", lambda: doc.Pages.Add())
log("  pages=%s" % doc.Pages.Count)
attempt("save+close", lambda: (doc.SaveAs(os.path.join(OUT, "v7.vsdx")), doc.Close(), vis.Quit()))
log("################ DONE ################")
log("artifacts: " + ", ".join("%s=%d" % (f, os.path.getsize(os.path.join(OUT, f)))
                              for f in sorted(os.listdir(OUT)) if f.startswith("v7")))
_fh.close()
