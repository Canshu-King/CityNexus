"""Fit the classroom copies: scroll to the project start with a real key press,
then zoom one step in, save that view, and photograph it.

Why a key press and not the object model: every scripted scroll on this install is
missing (TaskScrollTo, SelectTaskRow, Goto, Window.Scroll, ScrollBar, FirstTask,
ScrollLeft, ScrollItem - all AttributeError, measured), and TimescaleStart /
TimescaleFinish refuse assignment while ZoomOut only widens the tiers. Ctrl+Home in
the chart pane is what the "Entire Project" button does, and the resulting viewport
is saved into the .mpp, so the teacher who opens this copy sees it without pressing
anything.

Keys are sent only after the foreground window has been read back and compared with
the target handle; if the foreground lock refuses, no keystroke is sent at all and
the run says so, rather than typing into whatever window happens to be on top.
"""
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import stat
import sys
import time
import win32con
import win32gui
import win32ui
import win32process
import win32com.client as w32
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
CLS = os.path.join(DEL, "Classroom")
PICS = os.path.join(CLS, "previews")
LOG = open(os.path.join(HERE, "se_classroom_fit_r1.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()
u = ctypes.windll.user32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
# zoomSteps = 0 on purpose. ZoomOut walks the tiers to years and ZoomIn walks them to
# quarter-hours; both were measured and both destroy the bars. The only thing that
# helps is Ctrl+Home in the chart pane, which moves the viewport to the project start
# and is saved into the copy, so a teacher who opens it sees September without
# pressing anything.
COPIES = (("CityNexus_Plan_Classroom", "Gantt_Visible.png", 0),
          ("CityNexus_Milestones_Classroom", "Milestones_Visible.png", 0))


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def sha(p, n=64):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


def frame(stem):
    out = []

    def cb(h, _l):
        if not win32gui.IsWindowVisible(h):
            return True
        buf = ctypes.create_unicode_buffer(256)
        u.GetWindowTextW(int(h), buf, 256)
        t = buf.value or ""
        if stem not in t:
            return True
        r = win32gui.GetWindowRect(h)
        if r[2] - r[0] < 600 or r[3] - r[1] < 400:
            return True
        out.append((h, buf.value or ""))
        return True

    win32gui.EnumWindows(cb, None)
    return out


def grab(h):
    l, t, r, b = win32gui.GetWindowRect(h)
    dc0 = win32gui.GetWindowDC(h)
    mfc = win32ui.CreateDCFromHandle(dc0)
    dc = mfc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mfc, r - l, b - t)
    dc.SelectObject(bmp)
    ok = u.PrintWindow(int(h), dc.GetSafeHdc(), 2)
    img = Image.frombuffer("RGB", (r - l, b - t), bmp.GetBitmapBits(True), "raw",
                           "BGRX", 0, 1)
    win32gui.DeleteObject(bmp.GetHandle())
    dc.DeleteDC()
    mfc.DeleteDC()
    win32gui.ReleaseDC(h, dc0)
    return img, bool(ok)


def chart_ink(img):
    w, h = img.size
    im = img.convert("L").crop((int(w * 0.40), int(h * 0.24), w, int(h * 0.92)))
    hist = im.histogram()
    return round(sum(hist[:245]) / float(im.size[0] * im.size[1]), 4)


def ctrl_home_into_chart(h):
    """Bring the window forward, click the chart pane, press Ctrl+Home.

    Returns a short string saying what actually happened; the keystroke is skipped
    unless the target is provably the foreground window afterwards.
    """
    target = int(h)
    fg = int(u.GetForegroundWindow())
    tid_fg = u.GetWindowThreadProcessId(fg, 0)
    tid_me = ctypes.windll.kernel32.GetCurrentThreadId()
    u.AttachThreadInput(tid_me, tid_fg, True)
    u.BringWindowToTop(target)
    u.ShowWindow(target, win32con.SW_MAXIMIZE)
    u.SetForegroundWindow(target)
    u.SetActiveWindow(target)
    u.AttachThreadInput(tid_me, tid_fg, False)
    time.sleep(0.8)
    now = int(u.GetForegroundWindow())
    if now != target:
        return "foreground refused (foreground is %d, target %d); NO keys sent" % (
            now, target)
    l, t, r, b = win32gui.GetWindowRect(h)
    x = l + int((r - l) * 0.70)
    y = t + int((b - t) * 0.35)
    u.SetCursorPos(x, y)
    u.mouse_event(0x0002, 0, 0, 0, 0)
    u.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.4)
    for vk, down in ((0x11, 1), (0x24, 1), (0x24, 0), (0x11, 0)):
        u.keybd_event(vk, 0, 0 if down else 2, 0)
        time.sleep(0.08)
    return "Ctrl+Home sent into the chart pane at %d,%d" % (x, y)


src = {"plan": os.path.join(DEL, "Microsoft_Project",
                            "CityNexus_Software_Engineering_Plan.mpp"),
       "mile": os.path.join(DEL, "Microsoft_Project", "CityNexus_Milestone_View.mpp")}
before = dict((k, sha(v)) for k, v in src.items())
mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
import atexit


def _bye():
    try:
        mp.FileCloseEx(0)
    except Exception:
        pass
    try:
        mp.Quit()
    except Exception:
        pass


atexit.register(_bye)
def scrollbar_to_start(h):
    """Drag the bottom horizontal scrollbar thumb to the far left.

    Ctrl+Home moves the current row, not the timescale, so the chart still opened on
    early October. Dragging the thumb is the only thing that actually brings 2026-09-07
    on screen; the drag is done inside this window's own rectangle after the same
    foreground check, and the coordinates are derived from the window rect rather than
    hard-coded.
    """
    l, t, r, b = win32gui.GetWindowRect(h)
    y = b - int((b - t) * 0.022)
    x0 = l + int((r - l) * 0.55)
    x1 = l + int((r - l) * 0.02)
    if int(u.GetForegroundWindow()) != int(h):
        return "foreground lost before the drag; NO mouse events sent"
    u.SetCursorPos(x0, y)
    u.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.15)
    for frac in (0.8, 0.6, 0.4, 0.2, 0.0):
        u.SetCursorPos(int(x0 - (x0 - x1) * frac) if frac else x1, y)
        time.sleep(0.12)
    u.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.4)
    return "scrollbar dragged %d,%d -> %d,%d" % (x0, y, x1, y)


made = {}
for stem, png, zooms in COPIES:
    p = os.path.join(CLS, stem + ".mpp")
    if not os.path.exists(p):
        log("missing %s" % p)
        continue
    os.chmod(p, stat.S_IWRITE)
    mp.FileOpen(p)
    time.sleep(2.2)
    mp.ViewApply("甘特图")
    f = frame(stem)
    if not f:
        raise SystemExit("no window for %s" % stem)
    h = f[0][0]
    log("%s: %s" % (stem, ctrl_home_into_chart(h)))
    log("%s: %s" % (stem, scrollbar_to_start(h)))
    for _i in range(zooms):
        try:
            mp.ZoomIn()
        except Exception as exc:
            log("  ZoomIn refused: %s" % type(exc).__name__)
            break
    try:
        mp.FileSave()
    except Exception as exc:
        log("  FileSave refused: %s" % type(exc).__name__)
    mp.FileCloseEx(0)
    os.chmod(p, stat.S_IREAD)
    mp.FileOpen(p)
    time.sleep(2.2)
    f = frame(stem)
    if not f:
        raise SystemExit("classroom copy %s did not reopen" % stem)
    u.ShowWindow(int(f[0][0]), win32con.SW_MAXIMIZE)
    time.sleep(1.0)
    img, ok = grab(f[0][0])
    out = os.path.join(PICS, png)
    os.makedirs(PICS, exist_ok=True)
    img.save(out)
    made[stem] = {"png": "Classroom/previews/" + png, "bytes": os.path.getsize(out),
                  "px": list(img.size), "chartInk": chart_ink(img),
                  "printWindowReturned": ok, "windowTitle": f[0][1] if f else "",
                  "sha256_16": sha(out, 16), "zoomSteps": zooms}
    log("  %s  %dx%d  chart ink %.4f" % (png, img.size[0], img.size[1],
                                         chart_ink(img)))
    mp.FileCloseEx(0)
    os.chmod(p, stat.S_IWRITE)
try:
    mp.Quit()
except Exception:
    pass
bad = [k for k, v in before.items() if sha(src[k]) != v]
if bad:
    raise SystemExit("shipped files changed: %s" % bad)
log("shipped plan and milestone files unchanged")
json.dump(made, open(os.path.join(HERE, "se_classroom_fit_result.json"), "w",
                     encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
log("CLASSROOM FIT DONE")
LOG.close()
sys.exit(0)
