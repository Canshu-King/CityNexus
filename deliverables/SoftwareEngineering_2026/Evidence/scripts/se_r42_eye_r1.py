"""R4.2 eye check: open the corrected drawing in a real, visible Visio and grab
the whole window, so the return arrow is judged as a person sees it.

`se_visio_cross_check_r1.py` proves no line collides and `se_r42_loop_proof_r1.py`
proves the arrow head lands on 调用地点与路线工具. Neither of those says the page is
legible. This script only looks: it opens the delivered file read-only (chmod, and
the digest is compared afterwards), maximises the window, fits the page to the
window, and PrintWindows the frame.

Nothing here may raise on the way out - a crashed reader left an
`/Automation -Embedding` Visio holding the drawing open once already, and the next
builder then died on SaveAs with "DOS 无效句柄".
"""
import ctypes
import hashlib
import json
import os
import sys
import time

import win32com.client as w

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _grab_window import frame, grab  # noqa: E402  my eye: PrintWindow, no occlusion

CLS = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Classroom"
VSDX = os.path.join(CLS, "Teacher_02_Agent_User_Flow.vsdx")
SHOTS = [r"E:\r42_review\01_Teacher_02_window.png",
         os.path.join(CLS, "previews", "Teacher_02_Agent_User_Flow_window.png")]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "se_r42_eye.json")
T0 = time.time()
rec = {"vsdx": os.path.basename(VSDX), "shots": [], "notes": []}


def log(msg):
    print("[%5.1fs] %s" % (time.time() - T0, msg), flush=True)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


before = sha(VSDX)
os.chmod(VSDX, 0o444)
app = None
doc = None
try:
    app = w.DispatchEx("Visio.Application")
    app.Visible = True
    try:
        app.AlertResponse = 7
    except Exception:
        pass
    # flag 2, not 16: measured on this install, 16 (visOpenBudget) renames the
    # document 绘图1 and then no window title identifies the file
    doc = app.Documents.OpenEx(VSDX, 2)
    time.sleep(2.0)
    win = app.ActiveWindow
    rec["documentName"] = doc.Name
    log("opened %r, page has %d shapes" % (doc.Name, win.Page.Shapes.Count))
    try:
        rec["windowRectBefore"] = list(app.ActiveWindow.GetWindowRect()
                                       if hasattr(win, "GetWindowRect") else [])
    except Exception:
        pass
    for label, fn in (("WindowState=max", lambda: setattr(win, "WindowState", 1)),
                      ("ViewFit=page", lambda: setattr(win, "ViewFit", 1)),
                      ("Zoom=0.62", lambda: setattr(win, "Zoom", 0.62))):
        try:
            fn()
            log("%s accepted, Zoom now %.3f" % (label, float(win.Zoom)))
            rec.setdefault("zoomSteps", []).append(label)
        except Exception as exc:
            log("%s failed: %s" % (label, type(exc).__name__))
    # the 形状 task pane eats a third of the frame, which makes the page read
    # smaller than a teacher will see it; docked task windows are closable, and
    # a failure here only means the screenshot keeps the pane.
    try:
        closed = []
        try:
            ds = win.DockedStencils
            for i in range(ds.Count, 0, -1):
                st = ds.Item(i)
                try:
                    st.Close()
                    closed.append(str(st.Name))
                except Exception:
                    pass
        except Exception as exc:
            log("DockedStencils: %s" % type(exc).__name__)
        try:
            for i in range(app.TaskWindows.Count, 0, -1):
                tw = app.TaskWindows.Item(i)
                if tw.Docked and int(tw.Visible):
                    tw.Close()
                    closed.append(tw.Name)
        except Exception as exc:
            log("TaskWindows: %s" % type(exc).__name__)
        log("shape panes closed: %s" % (", ".join(closed) or "none"))
        rec["taskPanesClosed"] = closed
    except Exception as exc:
        log("task pane sweep: %s" % type(exc).__name__)
    try:
        win.Zoom = 0.78
        log("re-fit after pane close, Zoom %.3f" % float(win.Zoom))
    except Exception:
        pass
    time.sleep(1.2)
    hits = frame("Visio")
    if not hits:
        raise RuntimeError("no visible Visio window found to capture")
    hwnd, title, rect = sorted(hits, key=lambda x: (x[2][2] - x[2][0]) *
                               (x[2][3] - x[2][1]))[-1]
    rec["window"] = {"hwnd": hwnd, "title": title, "rect": list(rect)}
    log("capturing %r %s" % (title, rect))
    for out in SHOTS:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        ok, pw, ph, size = grab(hwnd, out)
        rec["shots"].append({"path": out, "printwindow": ok, "px": list(size),
                             "bytes": os.path.getsize(out)})
        log("wrote %s %s %d bytes" % (out, size, os.path.getsize(out)))
finally:
    for label, fn in (("doc.Saved=True", lambda: setattr(doc, "Saved", True)),
                      ("doc.Close", lambda: doc.Close()),
                      ("app.Quit", lambda: app.Quit())):
        try:
            fn()
        except Exception as exc:
            log("%s: %s" % (label, type(exc).__name__))
    os.chmod(VSDX, 0o644)

after = sha(VSDX)
rec["digestBefore"] = before[:16]
rec["digestAfter"] = after[:16]
rec["unchanged"] = before == after
if not rec["unchanged"]:
    rec["notes"].append("the eye check rewrote the delivered file")
json.dump(rec, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
log("%s unchanged=%s zoom=%s" % ("EYE OK" if rec["shots"] and rec["unchanged"]
                                 else "EYE INCOMPLETE", rec["unchanged"],
                                 rec.get("window", {}).get("title", "")[:40]))
sys.exit(0 if rec["shots"] and rec["unchanged"] else 1)
