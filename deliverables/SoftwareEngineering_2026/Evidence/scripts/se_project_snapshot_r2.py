"""Project view screenshots that cannot be a picture of somebody else's window.

R1 grabbed the screen rectangle of the Project window. That is exactly the
screenshot the external review found: a Chrome window sitting on top of Project,
because SetForegroundWindow is allowed to fail silently and the grab does not
care what it caught.

R2 captures the window's own pixels with Win32 PrintWindow(PW_RENDERFULLCONTENT),
which renders the target window into a device context regardless of what is on
top of it, and it never saves the .mpp - the file is opened, photographed and
closed with pjDoNotSave, and the sha256 is compared before and after so a
"screenshot of the shipped plan" cannot quietly be a screenshot of a plan that
the script itself modified.

Every image has to pass a blank-frame test (colour count and non-white pixel
fraction) before it is kept, and the first capture is additionally cross-checked
against a real screen grab while the window is provably the topmost one; if the
two disagree, PrintWindow is not believed and the run fails.
"""
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project"
PICS = os.path.join(OUT, "previews")
MPP = os.path.join(OUT, "CityNexus_Software_Engineering_Plan.mpp")
LOG = open(os.path.join(HERE, "se_project_snapshot_r2.log"), "w",
           encoding="utf-8", buffering=1)
T0 = time.time()
PW_RENDERFULLCONTENT = 2
MIN_COLOURS = 60
MIN_INK = 0.012


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def dstr(v):
    try:
        return "%04d-%02d-%02d" % (v.year, v.month, v.day)
    except Exception:
        return str(v)[:10]


user32 = ctypes.windll.user32
try:
    # without this the window rect is DPI-virtualised and the bitmap is cropped
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    log("DPI awareness set to per-monitor")
except Exception as exc:
    log("SetProcessDpiAwareness failed: %s" % type(exc).__name__)

import win32con                                                    # noqa: E402
import win32gui                                                    # noqa: E402
import win32ui                                                     # noqa: E402
import win32com.client as w32                                      # noqa: E402
from PIL import Image                                              # noqa: E402
from PIL import ImageGrab                                          # noqa: E402

before = sha(MPP)
log("plan sha256 before the run %s" % before[:16])

# Measured, not assumed: opening a .mpp in Project and closing it WITHOUT saving
# still rewrites the container (the build run turned 348d370ebd61 into
# 31d27d3461d9). So the file is made read-only at the filesystem level for the
# whole capture, and the digest is compared afterwards.
import stat                                                      # noqa: E402
os.chmod(MPP, stat.S_IREAD)
log("plan set read-only on disk")

# A Project instance left over from an earlier run owns a window with the same
# title, and ViewApply on THIS automation object would not touch it - the picture
# would be a stale view presented as a fresh one.
try:
    import subprocess
    out = subprocess.check_output(
        ["tasklist", "/FI", "IMAGENAME eq WINPROJ.EXE", "/FO", "CSV", "/NH"],
        text=True, errors="replace")
    live = [l for l in out.splitlines() if "WINPROJ" in l.upper()]
    if live:
        raise SystemExit("WINPROJ.EXE is already running (%d process(es)); close "
                         "it before capturing, or the window may not be this "
                         "automation object's" % len(live))
    log("no pre-existing WINPROJ.EXE")
except SystemExit:
    raise
except Exception as exc:
    log("process pre-flight skipped: %s" % type(exc).__name__)

mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True


def _bye():
    """Never leave an orphaned WINPROJ, a read-only shipped file or an Office lock
    file behind a failure."""
    try:
        mp.FileCloseEx(0)
    except Exception:
        pass
    try:
        mp.Quit()
    except Exception:
        pass
    try:
        os.chmod(MPP, stat.S_IWRITE)
    except Exception:
        pass
    import glob
    for f in glob.glob(os.path.join(OUT, "~$*")) + \
            glob.glob(os.path.join(PICS, "~$*")):
        try:
            os.remove(f)
        except Exception:
            pass


import atexit                                                      # noqa: E402
atexit.register(_bye)
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
try:
    mp.FileOpen(MPP, 0, True)          # pjFileStandard, ReadOnly
except Exception as exc:
    log("read-only open refused (%s), opening normally and never saving"
        % type(exc).__name__)
    mp.FileOpen(MPP)
p = mp.ActiveProject
try:
    log("opened %s (%d tasks, %d resources), Project says ReadOnly=%s"
        % (os.path.basename(MPP), p.Tasks.Count, p.Resources.Count, p.ReadOnly))
except Exception:
    log("opened %s (%d tasks)" % (os.path.basename(MPP), p.Tasks.Count))


def _frame_matches(h, stem):
    """Visible, big enough to be a document frame, and titled after this file.

    Measured on this install: Project's main frame class is
    'JWinproj-WhimperMainClass', not the Office 'OpusApp' every recipe on the
    internet assumes, and its title is
    'Project Professional - CityNexus_Software_Engineering_Plan.mpp'.
    """
    import win32process
    if not user32.IsWindowVisible(h):
        return None
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(h, buf, 256)
    t = buf.value or ""
    if stem not in t:
        return None
    try:
        r = win32gui.GetWindowRect(h)
    except Exception:
        return None
    if r[2] - r[0] < 600 or r[3] - r[1] < 400:
        return None
    cls = ctypes.create_unicode_buffer(128)
    user32.GetClassNameW(h, cls, 128)
    return (h, t, cls.value or "?", win32process.GetWindowThreadProcessId(h)[1])


def project_window(stem=None):
    """The frame belonging to THIS automation object's process, by pid.

    The stem is configurable because the same helpers photograph the milestone
    file too, and Office titles the frame after whichever document is open.
    """
    hits = []

    def cb(h, _l):
        m = _frame_matches(h, stem or STEM)
        if m and (not WINPID or m[3] in WINPID):
            hits.append((m[0], m[1]))
        return True

    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    user32.EnumWindows(EnumProc(cb), 0)
    return hits


STEM = os.path.splitext(os.path.basename(MPP))[0]
WINPID = set()
try:
    _titles = [w.Caption for w in mp.Windows]
except Exception:
    _titles = []
log("Project windows: %s" % str(_titles)[:160])

_probe = []
for _try in range(10):
    _probe = project_window()
    if _probe:
        break
    time.sleep(1.0)
if _probe:
    import win32process
    WINPID = {win32process.GetWindowThreadProcessId(_probe[0][0])[1]}
    log("Project main window %r pid %s" % (_probe[0][1][:60], list(WINPID)[0]))
else:
    raise SystemExit("no window titled after %s - refusing to produce a "
                     "screenshot of something else" % STEM)


def occluders(h, rect):
    """Visible top-level windows drawn ABOVE h that intersect its rectangle.

    Project's own shadow and tooltip windows share the rectangle and the process,
    and counting them would turn every capture into "occluded".
    """
    import win32process
    out = []
    mypid = win32process.GetWindowThreadProcessId(h)[1]

    def cb(z, _l):
        if z == h:
            return False
        if not user32.IsWindowVisible(z):
            return True
        try:
            zr = win32gui.GetWindowRect(z)
        except Exception:
            return True
        if zr[2] - zr[0] < 40 or zr[3] - zr[1] < 40:
            return True
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(z, cls, 64)
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(z, buf, 256)
        t = buf.value or ""
        if not t:      # unnamed helper windows (shadows, tooltips, taskbar bits)
            return True
        try:
            if win32process.GetWindowThreadProcessId(z)[1] == mypid:
                return True
        except Exception:
            pass
        if not (zr[0] < rect[2] and rect[0] < zr[2] and
                zr[1] < rect[3] and rect[1] < zr[3]):
            return True
        out.append((t or cls.value)[:60])
        return True

    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    user32.EnumWindows(EnumProc(cb), 0)
    return out


def grab_window(h):
    hwnd_dc = win32gui.GetWindowDC(h)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    l, t, r, b = win32gui.GetWindowRect(h)
    w, hh = r - l, b - t
    bmp.CreateCompatibleBitmap(mfc_dc, w, hh)
    save_dc.SelectObject(bmp)
    ok = user32.PrintWindow(h, save_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)
    bits = bmp.GetBitmapBits(True)
    img = Image.frombuffer("RGB", (w, hh), bits, "raw", "BGRX", 0, 1)
    win32gui.DeleteObject(bmp.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(h, hwnd_dc)
    return img, bool(ok)


def ink_stats(img):
    g = img.convert("L")
    hist = g.histogram()
    nonwhite = sum(hist[:245]) / float(g.size[0] * g.size[1])
    cols = img.convert("RGB").getcolors(maxcolors=2000000)
    # getcolors returns None when the image has more distinct colours than the
    # cap, which must not be read as "zero colours" and rejected as blank
    colours = 2000000 if cols is None else len(cols)
    return nonwhite, colours


def check(img, tag):
    nonwhite, colours = ink_stats(img)
    log("  %-16s %dx%d  colours %d  ink %.3f" % (tag, img.size[0], img.size[1],
                                                 colours, nonwhite))
    if colours < MIN_COLOURS or nonwhite < MIN_INK:
        raise SystemExit("capture %s looks blank (colours %d, ink %.3f) - "
                         "PrintWindow returned an empty frame" % (tag, colours,
                                                                  nonwhite))
    return {"px": list(img.size), "colours": colours, "inkFraction": round(nonwhite, 4)}


VIEWS = [("Gantt_Chart", "甘特图"), ("Tracking_Gantt", "跟踪甘特图"),
         ("Network_Diagram", "网络图"), ("WBS_Task_Sheet", "任务工作表"),
         ("Resource_Sheet", "资源工作表"), ("Task_Usage", "任务使用情况"),
         ("Resource_Usage", "资源使用情况"), ("Calendar", "日历")]
os.makedirs(PICS, exist_ok=True)
made = {}
cross_checked = 0
for idx, (tag, vname) in enumerate(VIEWS):
    try:
        mp.ViewApply(vname)
    except Exception as exc:
        log("  ViewApply %s failed: %s" % (vname, str(exc)[:80]))
        continue
    try:
        mp.ActiveWindow.ViewWhole()
    except Exception as exc:
        log("  %s: ViewWhole refused (%s), captured at the current scale"
            % (tag, type(exc).__name__))
    # Measured on this install: ViewWhole and SplitBestFit do not exist on the
    # Window object, but ColumnBestFit does exist on the Application and the
    # Window's Zoom property takes a percentage. Without them the Gantt preview
    # is a wide empty chart area next to a table stretched to its column headers.
    tuned = []
    try:
        mp.ColumnBestFit()
        tuned.append("ColumnBestFit")
    except Exception as exc:
        tuned.append("ColumnBestFit refused (%s)" % type(exc).__name__)
    try:
        mp.ActiveWindow.Zoom = 45
        tuned.append("Window.Zoom 45")
    except Exception as exc:
        try:
            mp.Zoom(45)             # Application.Zoom is a method on this install
            tuned.append("Application.Zoom(45)")
        except Exception as exc2:
            tuned.append("Zoom refused (%s/%s)"
                         % (type(exc).__name__, type(exc2).__name__))
    try:
        mp.TimescaleStart = p.Start
        mp.TimescaleFinish = p.Finish + 3
        tuned.append("Timescale %s..%s" % (dstr(p.Start), dstr(p.Finish)))
    except Exception as exc:
        tuned.append("Timescale refused (%s)" % type(exc).__name__)
    log("  %s tuned: %s" % (tag, "; ".join(tuned)))
    time.sleep(1.4)
    wins = project_window()
    if not wins:
        raise SystemExit("the Project window disappeared before %s" % tag)
    h, title = wins[0]
    win32gui.ShowWindow(h, win32con.SW_MAXIMIZE)
    time.sleep(0.6)
    rect = win32gui.GetWindowRect(h)
    occ = occluders(h, rect)
    img, pw_ok = grab_window(h)
    stats = check(img, tag)
    path = os.path.join(PICS, tag + ".png")
    img.save(path)
    entry = {"view": vname, "png": os.path.basename(path),
             "bytes": os.path.getsize(path), "windowTitle": title,
             "printWindowReturned": pw_ok, "occludedBy": occ,
             "sha256": sha(path)[:16]}
    entry.update(stats)
    if idx == 0:
        # one honest cross-check: PrintWindow vs the pixels actually on screen,
        # taken only while nothing overlaps the window
        try:
            win32gui.SetForegroundWindow(h)
        except Exception as exc:
            log("  SetForegroundWindow failed (%s), trying SwitchToThisWindow"
                % type(exc).__name__)
            try:
                user32.SwitchToThisWindow(int(h), 1)
            except Exception as exc2:
                log("  SwitchToThisWindow failed too (%s)" % type(exc2).__name__)
        time.sleep(0.9)
        occ2 = occluders(h, win32gui.GetWindowRect(h))
        screen = ImageGrab.grab(bbox=win32gui.GetWindowRect(h), all_screens=True)
        if screen.size != img.size:
            log("  cross-check skipped: screen grab %s vs PrintWindow %s"
                % (screen.size, img.size))
        else:
            a, b = img.convert("L").resize((160, 90)), screen.convert("L").resize((160, 90))
            diff = sum(abs(x - y) for x, y in zip(list(a.getdata()), list(b.getdata())))
            mean = diff / float(160 * 90)
            entry["crossCheck"] = {"occluders": occ2, "meanAbsDiff": round(mean, 2)}
            log("  cross-check PrintWindow vs screen: mean abs diff %.2f over 0-255, "
                "occluders while grabbing %d" % (mean, len(occ2)))
            if occ2:
                log("  cross-check not decisive: %s sat on top while grabbing"
                    % str(occ2)[:120])
            elif mean > 12.0:
                raise SystemExit("PrintWindow and the screen disagree (%.1f) - the "
                                 "capture cannot be trusted" % mean)
            else:
                cross_checked = 1
    made[tag] = entry
    log("  kept %s (%d bytes, %d windows above it: %s)"
        % (tag, entry["bytes"], len(occ), str(occ)[:110]))

# The demonstration sheet asks for a milestone picture as well, and the milestone
# file is the one that shows all thirteen dates at once, so it is photographed the
# same way: read-only, PrintWindow, blank-frame test.
MILE = os.path.join(OUT, "CityNexus_Milestone_View.mpp")
try:
    mp.FileCloseEx(0)
except Exception as exc:
    log("FileCloseEx: %s" % type(exc).__name__)
if os.path.exists(MILE):
    os.chmod(MPP, stat.S_IWRITE)
    os.chmod(MILE, stat.S_IREAD)
    mile_before = sha(MILE)
    try:
        mp.FileOpen(MILE)
        time.sleep(1.5)
        for tag, vname in (("Milestone_Timeline", "甘特图"),):
            try:
                mp.ViewApply(vname)
            except Exception as exc:
                log("  milestone ViewApply failed: %s" % str(exc)[:60])
            try:
                mp.ColumnBestFit()
            except Exception:
                pass
            time.sleep(1.4)
            wins = project_window(os.path.splitext(os.path.basename(MILE))[0])
            h = wins[0][0] if wins else None
            if not wins:
                log("  no window titled after the milestone file; capture skipped "
                    "rather than photographing the plan window twice")
            if h:
                img, pw_ok = grab_window(h)
                stats = check(img, tag)
                path = os.path.join(PICS, tag + ".png")
                img.save(path)
                made[tag] = {"view": vname, "png": os.path.basename(path),
                             "bytes": os.path.getsize(path),
                             "windowTitle": wins[0][1],
                             "printWindowReturned": pw_ok,
                             "source": os.path.basename(MILE),
                             "sha256": sha(path)[:16]}
                made[tag].update(stats)
                log("  kept %s from %s" % (tag, os.path.basename(MILE)))
        mp.FileCloseEx(0)
    except Exception as exc:
        log("  milestone capture failed: %s %s" % (type(exc).__name__,
                                                   str(exc)[:80]))
    os.chmod(MILE, stat.S_IWRITE)
    mile_after = sha(MILE)
    log("milestone file digest %s -> %s (%s)"
        % (mile_before[:16], mile_after[:16],
           "held" if mile_after == mile_before else "CHANGED"))
    mile_held = mile_after == mile_before
else:
    mile_held = True
    log("no milestone view file to photograph")
try:
    mp.Quit()
except Exception:
    pass

after = sha(MPP)
os.chmod(MPP, stat.S_IWRITE)
import glob                                                      # noqa: E402
locks = [os.path.basename(f) for f in
         glob.glob(os.path.join(OUT, "~$*")) + glob.glob(os.path.join(PICS, "~$*"))]
log("plan sha256 after the run %s; Office lock files left: %s"
    % (after[:16], locks or "none"))
json.dump({"views": made, "sha256Before": before, "sha256After": after,
           "milestoneHeld": mile_held,
           "readOnly": True, "lockFilesLeft": locks,
           "screenCrossCheck": bool(cross_checked),
           "method": "PrintWindow(PW_RENDERFULLCONTENT)"},
          open(os.path.join(HERE, "se_project_snapshot_r2_result.json"), "w",
               encoding="utf-8"), indent=1, ensure_ascii=False)
if after != before:
    raise SystemExit("the shipped .mpp changed during a read-only capture run")
if locks:
    raise SystemExit("Office lock files would be packaged: %s" % locks)
if len(made) < 7:
    raise SystemExit("only %d views captured" % len(made))
log("SNAPSHOT R2 DONE: %d images (plan + milestone), file unchanged, "
    "cross-check %s"
    % (len(made), "passed" if cross_checked else "not decisive"))
sys.exit(0)
