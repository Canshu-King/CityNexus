"""Scroll the Gantt chart pane with a real key press, then save and photograph it.

No scripted scroll exists on this install: TaskScrollTo, SelectTaskRow, Goto,
Window.Scroll, ScrollBar, FirstTask, ScrollLeft and ScrollItem were all tried and all
raised AttributeError (_probe_scroll_panes.py), and TimescaleStart / TimescaleFinish
refuse assignment while ZoomOut only widens the tier, not the viewport. The one thing
that does move the view is the keyboard, so this opens the display copy, reports the
window rectangle so a real Ctrl+Home can be aimed at it, waits while that key is
sent, saves the resulting view state into the classroom copy, then reopens it
read-only and photographs it with PrintWindow.

The shipped plan is never opened here; only the copy under Classroom/.
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
import win32com.client as w32
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
CLS = os.path.join(DEL, "Classroom")
PICS = os.path.join(CLS, "previews")
DST = os.path.join(CLS, "CityNexus_Plan_Classroom.mpp")
SRC = os.path.join(DEL, "Microsoft_Project", "CityNexus_Software_Engineering_Plan.mpp")
WAIT = int(sys.argv[1]) if len(sys.argv) > 1 else 75
PW_RENDERFULLCONTENT = 2
user32 = ctypes.windll.user32
LOG = open(os.path.join(HERE, "se_classroom_scroll_r1.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()


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
        if not user32.IsWindowVisible(h):
            return True
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(h, buf, 256)
        if stem not in (buf.value or ""):
            return True
        try:
            r = win32gui.GetWindowRect(h)
        except Exception:
            return True
        if r[2] - r[0] < 600 or r[3] - r[1] < 400:
            return True
        out.append((h, buf.value, r))
        return True

    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    user32.EnumWindows(EnumProc(cb), 0)
    return out


def grab(h):
    l, t, r, b = win32gui.GetWindowRect(h)
    hwnd_dc = win32gui.GetWindowDC(h)
    mfc = win32ui.CreateDCFromHandle(hwnd_dc)
    dc = mfc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mfc, r - l, b - t)
    dc.SelectObject(bmp)
    ok = user32.PrintWindow(h, dc.GetSafeHdc(), PW_RENDERFULLCONTENT)
    img = Image.frombuffer("RGB", (r - l, b - t), bmp.GetBitmapBits(True), "raw",
                           "BGRX", 0, 1)
    win32gui.DeleteObject(bmp.GetHandle())
    dc.DeleteDC()
    mfc.DeleteDC()
    win32gui.ReleaseDC(h, hwnd_dc)
    return img, bool(ok)


def chart_ink(img):
    w, h = img.size
    im = img.convert("L").crop((int(w * 0.40), int(h * 0.24), w, int(h * 0.92)))
    hist = im.histogram()
    return round(sum(hist[:245]) / float(im.size[0] * im.size[1]), 4)


src_sha = sha(SRC)
if os.path.exists(DST):
    os.chmod(DST, stat.S_IWRITE)
    os.remove(DST)
import shutil
shutil.copyfile(SRC, DST)
mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
mp.FileOpen(DST)
time.sleep(2.0)
mp.ViewApply("甘特图")
try:
    mp.OutlineShowAllTasks()
except Exception:
    pass
win32gui.ShowWindow(frame("CityNexus_Plan_Classroom")[0][0], win32con.SW_MAXIMIZE)
time.sleep(1.0)
f = frame("CityNexus_Plan_Classroom")
if not f:
    raise SystemExit("classroom window not found")
hwnd, title, rect = f[0]
log("window %r rect %s" % (title[:60], rect))
log("HINT click inside the right-hand chart pane then press Ctrl+Home; waiting %ds"
    % WAIT)
log("chart ink before: %.4f" % chart_ink(grab(hwnd)[0]))
left = time.time()
while time.time() - left < WAIT:
    time.sleep(2.0)
    if os.path.exists(os.path.join(HERE, "_scroll_done")):
        break
try:
    mp.FileSave()
    log("saved the scrolled view into the classroom copy")
except Exception as exc:
    log("FileSave failed: %s" % str(exc)[:80])
mp.FileCloseEx(0)
after = chart_ink(grab(hwnd)[0]) if frame("CityNexus_Plan_Classroom") else 0.0
os.chmod(DST, stat.S_IREAD)
mp.FileOpen(DST)
time.sleep(2.0)
f = frame("CityNexus_Plan_Classroom")
img = None
if f:
    win32gui.ShowWindow(f[0], win32con.SW_MAXIMIZE)
    time.sleep(1.0)
    img, ok = grab(f[0])
    img.save(os.path.join(PICS, "Gantt_Visible.png"))
    log("reopened read-only and photographed: ink %.4f, printWindow returned %s"
        % (chart_ink(img), ok))
mp.FileCloseEx(0)
mp.Quit()
os.chmod(DST, stat.S_IWRITE)
if sha(SRC) != src_sha:
    raise SystemExit("the shipped plan changed")
json.dump({"copy": os.path.basename(DST), "rect": list(rect),
           "inkAfter": chart_ink(img) if img else None},
          open(os.path.join(HERE, "se_classroom_scroll_result.json"), "w",
               encoding="utf-8"), indent=1)
log("SCROLL RUN DONE")
LOG.close()
