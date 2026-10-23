"""Probe v5 - final API resolution before writing the generators.

Answers, with logged evidence:
  PROJECT: which Application attrs exist (dir), localized view names,
           how to force Auto Scheduled, Project.Assignments.Add shape,
           resource rate via PayRates.Add, successor movement on recalc,
           DocumentExport PDF per view.
  VISIO  : Drop with localized masters, connector gluing (GlueProj),
           lane/pool + UML masters, connector text, dashed style.
"""
import datetime
import os
import time

D = datetime.datetime
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_se_smoke")
os.makedirs(OUT, exist_ok=True)
STENCIL = r"C:\Program Files\Microsoft Office\root\Office16\Visio Content\2052"
_fh = open(os.path.join(HERE, "se_probe_r5.log"), "w", encoding="utf-8", buffering=1)
_t0 = time.time()


def log(m):
    _fh.write("[%6.1fs] %s\n" % (time.time() - _t0, m))
    _fh.flush()


def attempt(label, fn):
    try:
        r = fn()
        log("OK   %s -> %s" % (label, r if not hasattr(r, "_oleobj_") else "<comobj>"))
        return r
    except Exception as exc:
        log("FAIL %s -> %s: %s" % (label, type(exc).__name__, str(exc)[:230]))
        return None


import win32com.client as w32

log("################ PROJECT ################")
mp = attempt("Dispatch", lambda: w32.Dispatch("MSProject.Application"))
attempt("Visible", lambda: setattr(mp, "Visible", True))
attempt("Alerts", lambda: setattr(mp, "DisplayAlerts", 0))
attrs = sorted([a for a in dir(mp)])
log("APP ATTRS count=%d" % len(attrs))
log("  Default*: %s" % [a for a in attrs if "Default" in a])
log("  *Schedul*: %s" % [a for a in attrs if "Schedul" in a.lower()])
log("  View*: %s" % [a for a in attrs if a.lower().startswith("view") or "View" in a][:30])
log("  *Calc*: %s" % [a for a in attrs if "Calc" in a])
log("  *Assign/Res*: %s" % [a for a in attrs if "Assign" in a or "Resourc" in a][:25])
log("  Options*: %s" % [a for a in attrs if "Option" in a])

attempt("FileNew", lambda: mp.FileNew())
p = mp.ActiveProject
attempt("ProjectStart", lambda: setattr(p, "ProjectStart", D(2026, 9, 4, 9, 0)))

views = attempt("Views count", lambda: p.Views.Count)
vnames = attempt("view names", lambda: [p.Views.Item(i).Name for i in range(1, views + 1)])
if isinstance(vnames, list):
    want = ("Gantt", "Network", "Task Sheet", "Resource Sheet", "Timeline", "Calendar", "Milestone")
    log("  views matching english hints:")
    for w in want:
        hits = [n for n in vnames if w.lower() in n.lower()]
        log("    %-16s -> %s" % (w, hits))
    log("  ALL VIEW NAMES: %s" % vnames)

log("--- build a small honest hierarchy ---")
# 1 summary + 2 children + 1 leaf successor chain
s1 = attempt("add S1", lambda: p.Tasks.Add("S1 ALPHA"))
c1 = attempt("add C1", lambda: p.Tasks.Add("C1 ONE"))
c2 = attempt("add C2", lambda: p.Tasks.Add("C2 TWO"))
l1 = attempt("add L1", lambda: p.Tasks.Add("L1 AFTER"))
m1 = attempt("add M1", lambda: p.Tasks.Add("M1 MS"))
attempt("outline children", lambda: (setattr(c1, "OutlineLevel", 2),
                                     setattr(c2, "OutlineLevel", 2)))
attempt("c1 dur 3d", lambda: setattr(c1, "Duration", "3d"))
attempt("c2 dur 4d", lambda: setattr(c2, "Duration", "4d"))
attempt("l1 dur 5d", lambda: setattr(l1, "Duration", "5d"))
attempt("m1 dur 0d", lambda: setattr(m1, "Duration", "0d"))
attempt("l1 pred c1", lambda: setattr(l1, "Predecessors", "%dFS" % c1.ID))
attempt("m1 pred l1", lambda: setattr(m1, "Predecessors", "%dFS" % l1.ID))
attempt("calc", lambda: mp.CalculateAll())
log("  before: c1 finish=%s l1 start=%s l1 finish=%s m1 finish=%s"
    % (c1.Finish, l1.Start, l1.Finish, m1.Finish))
log("  scheduling-mode probes:")
for cand in ("Scheduled", "TaskSchedulingSlider", "ScheduleMode"):
    log("    t.%s = %s" % (cand, attempt("read t.%s" % cand, lambda cd=cand: getattr(c1, cd))))
log("  critical: c1=%s l1=%s m1=%s ; l1 slack=%s" % (c1.Critical, l1.Critical, m1.Critical, l1.StartSlack))
attempt("c1 dur 3d->9d", lambda: setattr(c1, "Duration", "9d"))
attempt("calc2", lambda: mp.CalculateAll())
log("  after : c1 finish=%s l1 start=%s l1 finish=%s m1 finish=%s"
    % (c1.Finish, l1.Start, l1.Finish, m1.Finish))

log("--- forcing Auto Scheduled (if links did not drive) ---")
for setter in (
    ("mp.InsertScheduledTask()", lambda: mp.InsertScheduledTask()),
    ("t.SetField(1106, 0)", lambda: c1.SetField(1106, 0)),
    ("mp.DefaultTaskScheduled=0", lambda: setattr(mp, "DefaultTaskScheduled", 0)),
):
    attempt(setter[0], setter[1])
log("  prjScheduled-ish field ids tried; check again:")
attempt("calc3", lambda: mp.CalculateAll())
log("  after force: c1 finish=%s l1 start=%s" % (c1.Finish, l1.Start))

log("--- resources and real assignment ---")
r1 = attempt("res add", lambda: p.Resources.Add("DEV ONE"))
r2 = attempt("res add2", lambda: p.Resources.Add("PM TWO"))
for rl, rate, ovt, cpu in ((r1, 180, 270, 0), (r2, 220, 330, 0)):
    attempt("res %s type" % rl.Name, lambda x=rl: setattr(x, "Type", 1))
    attempt("res %s AccrueAt" % rl.Name, lambda x=rl: setattr(x, "AccrueAt", 3))
    attempt("res %s StdRate=direct" % rl.Name, lambda x=rl, v=rate: setattr(x, "StandardRate", v))
    attempt("res %s PayRates.Add" % rl.Name,
            lambda x=rl, v=rate, o=ovt, c=cpu: x.CostRateTables.Item("A").PayRates.Add(
                D(2026, 9, 4), v, o, c))
    attempt("res %s readback" % rl.Name, lambda x=rl: "Std=%s CPU=%s PayRate1=%s" % (
        x.StandardRate, x.CostPerUse, x.CostRateTables.Item("A").PayRates.Item(1).StandardRate))
attempt("MaxUnits", lambda: [setattr(x, "MaxUnits", 1.0) for x in (r1, r2)])
log("  assignments collection on project: %s" % attempt("p.Assignments count", lambda: p.Assignments.Count))
a1 = attempt("p.Assignments.Add(c1,r1)", lambda: p.Assignments.Add(c1.ID, r1.ID, 1.0))
a2 = attempt("p.Assignments.Add(l1,r2)", lambda: p.Assignments.Add(l1.ID, r2.ID, 1.0))
attempt("set work", lambda: setattr(c1, "RegularWork", "24h"))
attempt("calc4", lambda: mp.CalculateAll())
log("  c1 work=%s cost=%s ; r1 cost=%s ; proj cost=%s ; proj work=%s"
    % (c1.RegularWork, c1.Cost, r1.Cost, p.Cost, p.Work))
log("  proj.CostPer100WorkCurrencyUnits=%s ; p.FinancialRates?" % attempt(
    "read rates", lambda: len(p.FinancialRates)))

log("--- WBS / milestone / percent / notes ---")
log("  c1 WBS=%s  s1 WBS=%s  m1 WBS=%s m1.Milestone=%s" % (c1.WBS, s1.WBS, m1.WBS, m1.Milestone))
attempt("m1 Deadline", lambda: setattr(m1, "Deadline", D(2026, 10, 9)))
attempt("c1 percent", lambda: setattr(c1, "PercentComplete", 60))
attempt("c1 note", lambda: setattr(c1, "Notes", "verified note"))
attempt("wbs default children", lambda: setattr(p, "WBSEnabled", 2))

log("--- export each view to PDF ---")
view_candidates = []
if isinstance(vnames, list):
    for w, keys in (("Gantt", ("甘特", "Gantt")), ("Network", ("网络", "Network")),
                    ("TaskSheet", ("任务工作表", "Task Sheet")),
                    ("ResourceSheet", ("资源工作表", "Resource Sheet")),
                    ("Timeline", ("时间表", "Timeline")),
                    ("Calendar", ("日历", "Calendar"))):
        for k in keys:
            hit = [n for n in vnames if k.lower() in n.lower()]
            if hit:
                view_candidates.append((w, hit[0]))
                break
log("  resolved view map: %s" % view_candidates)
for tag, vname in view_candidates:
    ok = attempt("ViewApply %s (%s)" % (tag, vname), lambda v=vname: mp.ViewApply(v))
    if ok is not None:
        fp = os.path.join(OUT, "p5_%s.pdf" % tag)
        attempt("DocumentExport %s" % tag,
                lambda f=fp: (mp.DocumentExport(f, 0), os.path.getsize(f))[1])

attempt("save mpp", lambda: p.SaveAs(os.path.join(OUT, "p5.mpp")))
attempt("close quit", lambda: (mp.FileClose(), mp.Quit()))
time.sleep(2)

log("################ VISIO ################")
vis = attempt("Dispatch Visio", lambda: w32.Dispatch("Visio.Application"))
doc = attempt("doc add", lambda: vis.Documents.Add(""))
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
        return "%s=%s" % (name, [d.Masters.Item(i).Name for i in range(1, d.Masters.Count + 1)])
    attempt("stencil", op)


def M(set_name, *names):
    d = stef[set_name]
    for i in range(1, d.Masters.Count + 1):
        if d.Masters.Item(i).Name in names:
            return d.Masters.Item(i)
    raise KeyError("%s not in %s" % (names, set_name))


log("--- drop localized masters ---")
shapes = {}
for tag, (sn, names, x, y, txt) in {
    "proc": ("FLOW", ("流程",), 3.0, 9.5, "PROCESS NODE"),
    "dec": ("FLOW", ("判定",), 3.0, 7.5, "DECISION"),
    "term": ("FLOW", ("开始/结束",), 3.0, 11.0, "START"),
    "data": ("FLOW", ("数据",), 7.0, 9.5, "I/O"),
    "db": ("FLOW", ("数据库",), 7.0, 7.5, "SQLITE"),
    "cyl": ("BASIC", ("圆柱形",), 11.0, 9.5, "CYL"),
    "rect": ("BASIC", ("矩形",), 11.0, 7.5, "RECT"),
    "actor": ("UML", ("参与者",), 2.0, 4.5, "TRAVELER"),
    "uc": ("UML", ("用例",), 6.0, 4.5, "USE CASE"),
    "subsys": ("UML", ("子系统",), 9.0, 4.5, "SYSTEM BOUNDARY"),
    "srv": ("SRV", ("Web 服务器", "服务器"), 13.0, 9.5, "FASTAPI"),
}.items():
    def op(sn=sn, names=names, x=x, y=y, txt=txt):
        m = M(sn, *names)
        s = page.Drop(m, x, y)
        s.Text = txt
        shapes[tag] = s
        return "%s master=%r shape=%r id=%s w=%.2f h=%.2f" % (
            tag, m.Name, s.Name, s.ID, s.Cells("Width").ResultIU, s.Cells("Height").ResultIU)
    attempt("drop", op)

log("--- resize / reposition ---")
attempt("resize proc", lambda: (setattr(shapes["proc"].Cells("Width"), "FormulaU", "2.6in"),
                                setattr(shapes["proc"].Cells("Height"), "FormulaU", "0.8in"),
                                shapes["proc"].Cells("Width").ResultIU))
attempt("round corner box", lambda: (
    lambda s: (setattr(s.Cells("Rounding"), "FormulaU", "0.06in"), s.Cells("Rounding").ResultIU)
)(shapes["rect"]))

log("--- connect: GlueProj dynamic connector ---")
def glue(a, b, label=""):
    c = page.Drop(vis.ConnectorToolDataObject, 0.0, 0.0)
    c.Cells("BeginX").GlueTo(shapes[a].Cells("PinX"))
    c.Cells("EndX").GlueTo(shapes[b].Cells("PinX"))
    if label:
        c.Text = label
    beg = end = "?"
    try:
        beg = c.Cells("BeginX").ConnectedShape.ID
        end = c.Cells("EndX").ConnectedShape.ID
    except Exception as exc:
        beg = end = "readfail:%s" % type(exc).__name__
    return "connector=%r begin=%s end=%s pageConnects=%s" % (c.Name, beg, end, page.Connects.Count)


for pair, lab in ((("term", "proc"), "go"), (("proc", "dec"), ""), (("dec", "data"), "YES")):
    attempt("glue %s->%s" % pair, lambda pr=pair, lb=lab: glue(pr[0], pr[1], lb))

attempt("arrowhead style", lambda: (
    setattr(shapes["proc"].Cells("LineColor"), "FormulaU", "RGB(30,60,100)"),
    (lambda c: (setattr(c.Cells("EndArrowSize"), "FormulaU", "2"),
               setattr(c.Cells("LineColor"), "FormulaU", "RGB(30,60,100)"),
               setattr(c.Cells("Weight"), "FormulaU", "0.014in"))
     )(page.Shapes.Item(page.Shapes.Count))))
attempt("dashed connector", lambda: (
    lambda c: (setattr(c.Cells("Pattern"), "FormulaU", "6"), c.Cells("Pattern").ResultIU)
)(page.Shapes.Item(page.Shapes.Count)))
attempt("connector label text", lambda: page.Shapes.Item(page.Shapes.Count).Text)

log("--- swimlane pool from CFF ---")
attempt("drop pool", lambda: (
    lambda s: (setattr(s, "Text", "USER LANE"), s.Cells("Width").ResultIU)
)(page.Drop(M("CFF", "泳道列表", "泳道"), 6.0, 2.5)))

log("--- legend + title ---")
attempt("title text", lambda: (
    lambda t: (setattr(t, "Text", "CityNexus - PROBE TITLE"),
               setattr(t.Cells("Char.Size"), "FormulaU", "16pt"), t.Text)
)(page.DrawRectangle(0.6, 11.0, 6.0, 11.5)))

v5 = os.path.join(OUT, "p5.vsdx")
attempt("save", lambda: doc.SaveAs(v5))
log("vsdx=%s" % os.path.getsize(v5))
attempt("export png", lambda: (page.Export(os.path.join(OUT, "p5.png")),
                               os.path.getsize(os.path.join(OUT, "p5.png")))[1])
attempt("export pdf", lambda: (doc.ExportAsFixedFormat(1, os.path.join(OUT, "p5.pdf"), 1, 0),
                               os.path.getsize(os.path.join(OUT, "p5.pdf")))[1])
attempt("close quit", lambda: (doc.Close(), vis.Quit()))

log("################ DONE ################")
log("artifacts: " + ", ".join("%s=%d" % (f, os.path.getsize(os.path.join(OUT, f)))
                              for f in sorted(os.listdir(OUT)) if f.startswith("p5")))
_fh.close()
