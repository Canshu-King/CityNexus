"""Probe v6 - resolve the last unknowns, then stop probing and build.

Unknowns this must answer:
  P1 localized view names + whether views switch
  P2 how to make tasks AUTO SCHEDULED (r4 proved new tasks are manual:
     a successor did not move when its driver's duration grew)
  P3 real dependency-driven recalculation (successor must move)
  P4 Project.Assignments.Add(TaskID, ResourceID, Units) + cost from rates
  P5 resource standard rate: direct setter was silently ignored (readback 0)
  P6 DocumentExport PDF per view
  V1 Drop with localized masters (flowchart / UML / CFF / server)
  V2 glued dynamic connector that follows a moved shape
"""
import datetime
import os
import time

D = datetime.datetime
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_se_smoke")
os.makedirs(OUT, exist_ok=True)
STENCIL = r"C:\Program Files\Microsoft Office\root\Office16\Visio Content\2052"
_fh = open(os.path.join(HERE, "se_probe_r6.log"), "w", encoding="utf-8", buffering=1)
_t0 = time.time()


def log(m):
    _fh.write("[%6.1fs] %s\n" % (time.time() - _t0, m))
    _fh.flush()


def attempt(label, fn):
    try:
        r = fn()
        txt = "<comobj>" if hasattr(r, "_oleobj_") else r
        log("OK   %s -> %s" % (label, str(txt)[:400]))
        return r
    except Exception as exc:
        log("FAIL %s -> %s: %s" % (label, type(exc).__name__, str(exc)[:230]))
        return None


import win32com.client as w32

log("################ VISIO ################")
vis = attempt("Dispatch Visio", lambda: w32.Dispatch("Visio.Application"))
doc = attempt("Documents.Add", lambda: vis.Documents.Add(""))
page = doc.Pages.Item(1)
attempt("A3 landscape", lambda: [setattr(page.PageSheet.Cells(c), "FormulaU", f)
                                 for c, f in (("PrintPageOrientation", "1"),
                                              ("PageWidth", "420mm"),
                                              ("PageHeight", "297mm"))])

stef = {}
for name, f in (("FLOW", "BASFLO_M.VSSX"), ("BASIC", "BASIC_M.VSSX"),
               ("UML", "UUSEME_M.VSSX"), ("CFF", "XFUNC_M.VSSX"),
               ("CONN", "CONNEC_M.VSSX"), ("SRV", "SERVER_M.VSSX")):
    def op(name=name, f=f):
        d = vis.Documents.OpenEx(os.path.join(STENCIL, f), 16)
        stef[name] = d
        return [d.Masters.Item(i).Name for i in range(1, d.Masters.Count + 1)]
    attempt("stencil %s" % name, op)


def M(sn, *names):
    d = stef[sn]
    for i in range(1, d.Masters.Count + 1):
        if d.Masters.Item(i).Name in names:
            return d.Masters.Item(i)
    raise KeyError("no master %s in %s" % (names, sn))


shapes = {}
SPECS = [
    ("term", "FLOW", ("开始/结束",), 2.5, 10.6, "START"),
    ("proc", "FLOW", ("流程",), 2.5, 9.2, "PROCESS"),
    ("dec", "FLOW", ("判定",), 2.5, 7.6, "DECIDE?"),
    ("data", "FLOW", ("数据",), 5.5, 9.2, "I/O"),
    ("db", "FLOW", ("数据库",), 5.5, 7.6, "SQLITE"),
    ("ext", "FLOW", ("外部数据",), 8.0, 7.6, "PROVIDER"),
    ("cyl", "BASIC", ("圆柱形",), 8.0, 9.2, "CYL"),
    ("rect", "BASIC", ("矩形",), 10.5, 9.2, "RECT"),
    ("roundrect", "BASIC", ("圆角矩形",), 10.5, 7.6, "ROUNDED"),
    ("actor", "UML", ("参与者",), 2.0, 4.5, "TRAVELER"),
    ("uc", "UML", ("用例",), 5.0, 4.5, "USE CASE"),
    ("sys", "UML", ("子系统",), 8.0, 4.5, "SYSTEM"),
    ("web", "SRV", ("Web 服务器", "服务器"), 12.5, 4.5, "FASTAPI"),
]
for tag, sn, names, x, y, txt in SPECS:
    def op(tag=tag, sn=sn, names=names, x=x, y=y, txt=txt):
        m = M(sn, *names)
        s = page.Drop(m, x, y)
        s.Text = txt
        shapes[tag] = s
        return "%s <- master=%r shape=%r id=%s w=%.2f h=%.2f connSec=%s" % (
            tag, m.Name, s.Name, s.ID, s.Cells("Width").ResultIU,
            s.Cells("Height").ResultIU, s.SectionExists(7, 0))
    attempt("drop", op)

log("--- UML relationships: include / extend / dependency / association ---")
for tag, sn, names, x, y in (("incl", "UML", ("包含",), 4.0, 3.2),
                             ("ext_rel", "UML", ("扩展",), 6.0, 3.2),
                             ("dep", "UML", ("依赖关系",), 8.0, 3.2),
                             ("assoc", "UML", ("关联",), 10.0, 3.2)):
    def op(tag=tag, sn=sn, names=names, x=x, y=y):
        s = page.Drop(M(sn, *names), x, y)
        shapes[tag] = s
        return "%s ok name=%s" % (tag, s.Name)
    attempt("drop rel", op)

log("--- CFF pool/lane ---")
for tag, sn, names, x, y in (("pool", "CFF", ("泳道列表",), 6.0, 1.5),
                            ("lane", "CFF", ("泳道",), 12.0, 1.5),
                            ("phase", "CFF", ("阶段列表",), 14.5, 1.5)):
    def op(tag=tag, sn=sn, names=names, x=x, y=y):
        s = page.Drop(M(sn, *names), x, y)
        shapes[tag] = s
        return "%s ok w=%.2f h=%.2f name=%s" % (tag, s.Cells("Width").ResultIU,
                                                s.Cells("Height").ResultIU, s.Name)
    attempt("drop cff", op)

log("--- glued dynamic connectors ---")
made = {}
for a, b, lab in (("term", "proc", "go"), ("proc", "dec", ""), ("dec", "data", "YES"),
                  ("dec", "db", "NO"), ("web", "uc", "sends")):
    def op(a=a, b=b, lab=lab):
        c = page.Drop(vis.ConnectorToolDataObject, 0.0, 0.0)
        c.Cells("BeginX").GlueTo(shapes[a].Cells("PinX"))
        c.Cells("EndX").GlueTo(shapes[b].Cells("PinX"))
        if lab:
            c.Text = lab
        made[(a, b)] = c
        try:
            bs = c.Cells("BeginX").ConnectedShape.ID
            es = c.Cells("EndX").ConnectedShape.ID
        except Exception as exc:
            bs = es = "readfail:%s" % type(exc).__name__
        return "%s->%s conn=%r beginShape=%s endShape=%s connects=%s" % (
            a, b, c.Name, bs, es, page.Connects.Count)
    attempt("glue", op)

log("--- does the connector follow a moved shape? ---")
attempt("record pin", lambda: made[("term", "proc")].Cells("BeginX").ResultIU)
attempt("move term", lambda: setattr(shapes["term"].Cells("PinX"), "FormulaU", "4.5in"))
attempt("beginx after move", lambda: made[("term", "proc")].Cells("BeginX").ResultIU)
attempt("style connector", lambda: (
    setattr(made[("term", "proc")].Cells("Weight"), "FormulaU", "0.02in"),
    setattr(made[("term", "proc")].Cells("LineColor"), "FormulaU", "RGB(31,73,125)"),
    setattr(made[("term", "proc")].Cells("EndArrowSize"), "FormulaU", "2"),
    setattr(made[("dec", "db")].Cells("Pattern"), "FormulaU", "6"),
    made[("dec", "db")].Cells("Pattern").ResultIU))
attempt("reset move", lambda: setattr(shapes["term"].Cells("PinX"), "FormulaU", "2.5in"))

log("--- text formatting on a master shape ---")
attempt("multi-line text + font", lambda: (
    setattr(shapes["proc"].Cells("Char.Size"), "FormulaU", "9pt"),
    setattr(shapes["proc"].Cells("VerticalAlign"), "FormulaU", "1"),
    shapes["proc"].Text))
attempt("add second line", lambda: (
    setattr(shapes["proc"], "Text", "line one\rgline two"), shapes["proc"].Text))

log("--- page 2 in the same document ---")
p2 = attempt("Pages.Add", lambda: doc.Pages.AddAfter(doc.Pages.Item(1)))
log("  pages now=%s" % attempt("count", lambda: doc.Pages.Count))

v6 = os.path.join(OUT, "v6.vsdx")
attempt("save", lambda: doc.SaveAs(v6))
attempt("export png", lambda: (page.Export(os.path.join(OUT, "v6.png")),
                               os.path.getsize(os.path.join(OUT, "v6.png")))[1])
attempt("export pdf", lambda: (doc.ExportAsFixedFormat(1, os.path.join(OUT, "v6.pdf"), 1, 0),
                               os.path.getsize(os.path.join(OUT, "v6.pdf")))[1])
attempt("close quit", lambda: (doc.Close(), vis.Quit()))

log("################ PROJECT ################")
mp = attempt("Dispatch Project", lambda: w32.Dispatch("MSProject.Application"))
attempt("visible", lambda: setattr(mp, "Visible", True))
attempt("alerts", lambda: setattr(mp, "DisplayAlerts", 0))
attempt("FileNew", lambda: mp.FileNew())
p = attempt("ActiveProject", lambda: mp.ActiveProject)
attempt("ProjectStart", lambda: setattr(p, "ProjectStart", D(2026, 9, 4, 9, 0)))

P1 = attempt("views count", lambda: p.Views.Count)
vnames = attempt("view names", lambda: [p.Views.Item(i).Name for i in range(1, P1 + 1)])
log("P1 ALL VIEW NAMES (%s): %s" % (P1, vnames))

log("P2/P3 scheduling mode - leaf dependency test")
A = attempt("add A", lambda: p.Tasks.Add("A LEAF"))
B = attempt("add B", lambda: p.Tasks.Add("B LEAF"))
attempt("A dur 3d", lambda: setattr(A, "Duration", "3d"))
attempt("B dur 2d", lambda: setattr(B, "Duration", "2d"))
attempt("B pred A", lambda: setattr(B, "Predecessors", "%dFS" % A.ID))
attempt("calc", lambda: mp.CalculateAll())
log("  A=%s..%s  B=%s..%s" % (A.Start, A.Finish, B.Start, B.Finish))
attempt("A dur 3d->8d", lambda: setattr(A, "Duration", "8d"))
attempt("calc2", lambda: mp.CalculateAll())
log("  after: A=%s..%s  B=%s..%s   (B must shift if auto)" % (
    A.Start, A.Finish, B.Start, B.Finish))

log("P2 field scan for a scheduling-mode field")
hits = []
named = []
for i in list(range(0, 40)) + list(range(700, 1400)):
    try:
        v = A.GetField(i)
    except Exception:
        continue
    try:
        nm = A.FieldNames(i)
    except Exception:
        nm = "?"
    sv, sn = str(v), str(nm)
    if sn and any(k in sn for k in ("日程", "计划", "Schedule", "schedule")):
        named.append((i, sn, sv))
    if sv and any(k in sv for k in ("手动", "自动", "Manual", "Auto")):
        hits.append((i, sn, sv))
log("  fields whose NAME mentions schedule: %s" % named[:30])
log("  fields whose VALUE looks like manual/auto: %s" % hits[:30])
for i, sn, sv in (hits + named)[:8]:
    attempt("SetField(%d)->自动" % i, lambda ii=i: A.SetField(ii, "自动"))
attempt("calc3", lambda: mp.CalculateAll())
log("  after SetField loop: A=%s..%s B=%s..%s" % (A.Start, A.Finish, B.Start, B.Finish))
attempt("A dur 8d->13d", lambda: setattr(A, "Duration", "13d"))
attempt("calc4", lambda: mp.CalculateAll())
log("  decisive: A=%s..%s B=%s..%s" % (A.Start, A.Finish, B.Start, B.Finish))

log("P5 resource rates")
R1 = attempt("res add", lambda: p.Resources.Add("DEV ONE"))
for way in (
    ("direct StandardRate", lambda: setattr(R1, "StandardRate", 180)),
    ("PayRates.Add", lambda: R1.CostRateTables.Item("A").PayRates.Add(D(2026, 1, 1), 180, 270, 0)),
):
    attempt("rate %s" % way[0], way[1])
attempt("res type work", lambda: setattr(R1, "Type", 1))
attempt("res accrue prorated", lambda: setattr(R1, "AccrueAt", 3))
attempt("res maxunits", lambda: setattr(R1, "MaxUnits", 1.0))
log("  readback StdRate=%s CostPerUse=%s PayRate1Std=%s" % (
    attempt("std", lambda: R1.StandardRate),
    attempt("cpu", lambda: R1.CostPerUse),
    attempt("pr", lambda: R1.CostRateTables.Item("A").PayRates.Item(1).StandardRate)))

log("P4 assignment + cost")
att = attempt("p.Assignments.Add(A,R)", lambda: p.Assignments.Add(A.ID, R1.ID, 1.0))
attempt("work", lambda: setattr(A, "RegularWork", "40h"))
attempt("calc5", lambda: mp.CalculateAll())
log("  A.Work=%s A.RegularWork=%s A.Cost=%s ; R1.Cost=%s ; projCost=%s ; assns=%s" % (
    attempt("w", lambda: A.Work), attempt("rw", lambda: A.RegularWork),
    attempt("cost", lambda: A.Cost), attempt("rcost", lambda: R1.Cost),
    attempt("pcost", lambda: p.Cost), attempt("ac", lambda: p.Assignments.Count)))

log("P6 export views to PDF")
if isinstance(vnames, list):
    pairs = []
    for tag, keys in (("Gantt", ("甘特", "Gantt")), ("Network", ("网络", "Network")),
                      ("TaskSheet", ("任务工作表", "Task Sheet")),
                      ("ResSheet", ("资源工作表", "Resource Sheet")),
                      ("Timeline", ("时间表", "Timeline")), ("Calendar", ("日历", "Calendar"))):
        for k in keys:
            hit = [n for n in vnames if k.lower() in n.lower()]
            if hit:
                pairs.append((tag, hit[0]))
                break
    log("  resolved: %s" % pairs)
    for tag, vn in pairs:
        ok = attempt("ViewApply %s" % tag, lambda v=vn: mp.ViewApply(v))
        if ok is not None:
            fp = os.path.join(OUT, "v6_%s.pdf" % tag)
            attempt("DocumentExport %s" % tag, lambda f=fp: (
                mp.DocumentExport(f, 0), os.path.getsize(f))[1])

attempt("SaveAs mpp", lambda: p.SaveAs(os.path.join(OUT, "v6.mpp")))
attempt("quit", lambda: (mp.FileClose(), mp.Quit()))
log("################ DONE ################")
log("artifacts: " + ", ".join("%s=%d" % (f, os.path.getsize(os.path.join(OUT, f)))
                              for f in sorted(os.listdir(OUT)) if f.startswith("v6")))
_fh.close()
