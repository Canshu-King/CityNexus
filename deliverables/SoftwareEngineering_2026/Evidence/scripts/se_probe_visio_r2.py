"""Capability probe for Visio + MS Project COM automation.

Writes a flushed line to the log after EVERY step so a hang is bisectable.
Run:  python se_probe_r2.py  (background, then poll se_probe_r2.log)
"""
import os
import sys
import time
import traceback

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "se_probe_r2.log")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_se_smoke")
os.makedirs(OUT, exist_ok=True)

_fh = open(LOG, "w", encoding="utf-8", buffering=1)


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    _fh.write(line + "\n")
    _fh.flush()
    try:
        print(line)
    except Exception:
        pass


def step(name, fn):
    log("STEP %s ... start" % name)
    t0 = time.time()
    try:
        r = fn()
        log("STEP %s ... ok in %.1fs -> %s" % (name, time.time() - t0, r))
        return r
    except Exception as exc:
        log("STEP %s ... FAIL in %.1fs :: %s :: %s"
            % (name, time.time() - t0, type(exc).__name__, exc))
        log("   TRACE " + traceback.format_exc().replace("\n", " | ")[:900])
        return None


log("=== VISIO PROBE ===")
import win32com.client as w32

log("trying gencache EnsureDispatch Visio.Application")
try:
    vis = w32.gencache.EnsureDispatch("Visio.Application")
    log("EnsureDispatch OK (early-bound)")
except Exception as exc:
    log("EnsureDispatch FAIL %s -> falling back to DispatchEx" % exc)
    vis = w32.DispatchEx("Visio.Application")
    log("DispatchEx OK (late-bound)")

log("Visio.Version=%s Build=%s Visible=%s" % (vis.Version, vis.BuildNumber, vis.Visible))

# ---- member discovery (only if early-bound it's cheap) ----
def list_members():
    names = [m for m in dir(vis)]
    hits = [n for n in names if any(k in n.lower() for k in
            ("draw", "stencil", "master", "export", "print", "snapshot", "picture", "open"))]
    return "total=%d hits=%s" % (len(names), sorted(hits))

step("visio.app members", list_members)

doc = step("Documents.Add('')", lambda: vis.Documents.Add(""))
page = step("Pages.Item(1)", lambda: doc.Pages.Item(1))
step("rename page", lambda: setattr(page, "Name", "Smoke"))


def strat_window_draw():
    win = vis.ActiveWindow
    mm = [m for m in dir(win) if "draw" in m.lower() or "print" in m.lower() or "snapshot" in m.lower()]
    drawing = win.Draw
    s1 = drawing.DrawRectangle(1.0, 3.0, 4.0, 2.0)
    s1.Text = "S1-DRAWING"
    return "win members draw/print/snapshot=%s ; rect id=%s width=%s" % (
        mm, s1.ID, s1.Cells("Width").ResultIU)


step("strategy Window.Draw.DrawRectangle", strat_window_draw)


def strat_page_drop_master():
    # find a stencil on disk
    cands = []
    for root in (r"C:\Users\Public\Documents\Microsoft Visio",
                 os.path.expandvars(r"%APPDATA%\Microsoft\Visio")):
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                if f.lower().endswith(".vssx") or f.lower().endswith(".vss"):
                    cands.append(os.path.join(dirpath, f))
    log("   stencils found on disk: %d ; sample=%s" % (len(cands), cands[:6]))
    fav = [c for c in cands if "Flowchart" in c or "flowchr" in c.lower()]
    path = fav[0] if fav else (cands[0] if cands else None)
    if path is None:
        return "NO STENCIL ON DISK"
    sd = vis.Documents.OpenEx(path, 0x0020 | 0x0004)
    nm = [sd.Masters.Item(i).Name for i in range(1, min(sd.Masters.Count, 6) + 1)]
    sh = page.Drop(sd.Masters.Item(1), 6.0, 4.0)
    sh.Text = "S2-DROP"
    return "stencil=%s masters=%d first5=%s dropped name=%s" % (
        os.path.basename(path), sd.Masters.Count, nm, sh.Name)


step("strategy Page.Drop(stencil master)", strat_page_drop_master)


def strat_connect():
    shapes = page.Shapes
    n = shapes.Count
    a, b = shapes.Item(1), shapes.Item(n)
    made = None
    try:
        made = page.NewConnect(a, b, a.Connects(1))
    except Exception as exc:
        log("   NewConnect failed: %s" % exc)
    if made is None:
        drawing = vis.ActiveWindow.Draw
        con = drawing.DrawLine(1, 2, 3, 4)
        made = con
    return "shapes=%d connect made=%s connects_on_page=%s" % (
        n, made is not None, page.Connects.Count)


step("strategy page.NewConnect", strat_connect)


def strat_cells():
    sh = page.Shapes.Item(1)
    sh.Cells("FillForegnd").FormulaU = "THEMEGUARD(RGB(180,200,225))"
    sh.Cells("LineColor").FormulaU = "RGB(40,60,90)"
    sh.Cells("LineWeight").FormulaU = "0.02pt"
    sh.Cells("Char.Font").FormulaU = "='" + "Arial" + "'"
    sh.Cells("Char.Size").FormulaU = "10pt"
    out = sh.Text
    return "cells set ok, text back=%r" % out


step("strategy ShapeSheet cells", strat_cells)

vsdx = os.path.join(OUT, "smoke.vsdx")
if os.path.exists(vsdx):
    os.remove(vsdx)
step("SaveAs vsdx", lambda: doc.SaveAs(vsdx))
log("   saved size=%d" % (os.path.getsize(vsdx) if os.path.exists(vsdx) else -1))


def export_page():
    png = os.path.join(OUT, "smoke.png")
    if os.path.exists(png):
        os.remove(png)
    pm = [m for m in dir(page) if "export" in m.lower() or "print" in m.lower() or "snap" in m.lower()]
    pd = [m for m in dir(doc) if "export" in m.lower() or "print" in m.lower() or "save" in m.lower()]
    log("   page members=%s" % pm)
    log("   doc members=%s" % pd)
    try:
        page.Export(png, 150, 150, "")
    except Exception as exc:
        log("   page.Export(4 args) failed: %s" % exc)
        page.Export(png)
    return "png size=%d" % os.path.getsize(png)


step("export PNG", export_page)


def export_pdf():
    pdf = os.path.join(OUT, "smoke.pdf")
    if os.path.exists(pdf):
        os.remove(pdf)
    po = vis.PrintOptions
    pmm = [m for m in dir(po) if "print" in m.lower() or "file" in m.lower() or "name" in m.lower()]
    log("   PrintOptions members=%s" % pmm)
    try:
        po.PrintPrinter = "Microsoft Print to PDF"
        po.PrintFileName = pdf
    except Exception as exc:
        log("   set printer/filename failed: %s" % exc)
    try:
        doc.PrintOut()
        return "doc.PrintOut rc"
    except Exception as exc:
        log("   doc.PrintOut failed: %s" % exc)
    try:
        vis.PrintOut()
        return "app.PrintOut rc"
    except Exception as exc:
        log("   app.PrintOut failed: %s" % exc)
    return "pdf exists=%s" % os.path.exists(pdf)


step("export PDF via print", export_pdf)

step("close doc", lambda: doc.Close())
step("visio quit", lambda: vis.Quit())
time.sleep(2)

log("=== VISIO REOPEN ===")
vis2 = step("relaunch visio", lambda: w32.DispatchEx("Visio.Application"))
d2 = step("open vsdx", lambda: vis2.Documents.Open(vsdx))
step("read back", lambda: log(
    "   pages=%s shapes=%s shape1.Text=%r shape1.isDynamic=%s"
    % (d2.PageCount, d2.Pages.Item(1).Shapes.Count,
       d2.Pages.Item(1).Shapes.Item(1).Text,
       getattr(d2.Pages.Item(1).Shapes.Item(1), "Type", "?"))))
step("edit+save", lambda: (setattr(d2.Pages.Item(1).Shapes.Item(1), "Text", "EDITED-REOPEN"), d2.Save()))
step("close", lambda: d2.Close())
step("quit2", lambda: vis2.Quit())
time.sleep(2)
vis3 = step("relaunch3", lambda: w32.DispatchEx("Visio.Application"))
d3 = step("open3", lambda: vis3.Documents.Open(vsdx))
step("verify edit persisted", lambda: log("   text now=%r" % d3.Pages.Item(1).Shapes.Item(1).Text))
d3.Close()
vis3.Quit()

log("=== VISIO PROBE DONE ===")
_fh.write("EOF\n")
_fh.close()
