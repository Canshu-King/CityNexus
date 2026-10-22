"""One-image previews of the Project views, for slides.

The PDF exports paginate (the Gantt alone is 21 pages at Project's default
scaling), which is right for printing and wrong for a slide. This opens the
shipped .mpp, fits each view to the window, and grabs the Project window as a
PNG. The screenshots are labelled as screenshots in the README - they are not
passed off as exports.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("SE_MSP_OUT",
                     r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project")
PICS = os.path.join(OUT, "previews")
MPP = os.path.join(OUT, "CityNexus_Software_Engineering_Plan.mpp")
LOG = open(os.path.join(HERE, "se_project_snapshot.log"), "w", encoding="utf-8", buffering=1)
T0 = time.time()


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


os.makedirs(PICS, exist_ok=True)
import ctypes                                                     # noqa: E402
import ctypes.wintypes as wt                                      # noqa: E402
import win32gui                                                   # noqa: E402
import win32process                                               # noqa: E402
import win32con                                                   # noqa: E402
import win32com.client as w32                                     # noqa: E402
from PIL import ImageGrab                                         # noqa: E402

user32 = ctypes.windll.user32

mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
mp.FileOpen(MPP)
p = mp.ActiveProject
log("opened %s (%d tasks)" % (os.path.basename(MPP), p.Tasks.Count))

# put every milestone on the plan's own Timeline pane first, so the shipped
# .mpp really carries a milestone timeline instead of only the PDFs claiming one
placed = 0
for i in range(1, p.Tasks.Count + 1):
    t = p.Tasks.Item(i)
    try:
        if t.Summary or not t.Milestone:
            continue
        ok = False
        last = "?"
        for how, fn in (("one arg", lambda tt=t: mp.TaskOnTimeline(tt)),
                        ("two args", lambda tt=t, lab=t.Name.split("  ")[0].strip():
                         mp.TaskOnTimeline(tt, lab))):
            try:
                fn()
                ok = True
                break
            except Exception as exc:
                last = str(exc)[:70]
        if ok:
            placed += 1
        else:
            log("  row %d could not be placed: %s" % (i, last))
    except Exception as exc:
        log("  row %d unreadable: %s" % (i, str(exc)[:70]))
log("milestones placed on the plan's Timeline pane: %d" % placed)
try:
    mp.TimelineViewToggle()
    log("TimelineViewToggle ok")
except Exception as exc:
    log("TimelineViewToggle failed: %s" % str(exc)[:80])
try:
    mp.FileSave()
    log("plan saved with the timeline populated")
except Exception as exc:
    log("FileSave failed: %s" % str(exc)[:80])


def find_win():
    hits = []

    def cb(h, l):
        if not user32.IsWindowVisible(h):
            return True
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(h, buf, 256)
        t = buf.value or ""
        if "Project" in t or "CityNexus" in t or "Microsoft Project" in t:
            try:
                pid = wt.DWORD()
                user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
                _, tid = win32process.GetWindowThreadProcessId(h)
            except Exception:
                pid = None
            if "Project" in t and (".mpp" in t or "Microsoft Project" in t):
                hits.append((h, t))
        return True

    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    user32.EnumWindows(EnumProc(cb), 0)
    return hits


VIEWS = [("Gantt_Chart", "甘特图"), ("Tracking_Gantt", "跟踪甘特图"),
         ("Network_Diagram", "网络图"), ("WBS_Task_Sheet", "任务工作表"),
         ("Resource_Sheet", "资源工作表"), ("Calendar", "日历")]
made = {}
for tag, vname in VIEWS:
    try:
        mp.ViewApply(vname)
    except Exception as exc:
        log("ViewApply %s failed: %s" % (vname, str(exc)[:90]))
        continue
    try:
        aw = mp.ActiveWindow
        aw.Zoom = 40
        log("  window zoom set to 40%")
    except Exception as exc:
        try:
            mp.ActiveWindow.ViewWhole()
        except Exception:
            log("  zoom not adjustable (%s); captured at the current scale"
                % type(exc).__name__)
    time.sleep(1.2)
    wins = find_win()
    if not wins:
        log("  no Project window found for %s" % tag)
        continue
    h, title = wins[0]
    try:
        win32gui.ShowWindow(h, win32con.SW_MAXIMIZE)
        win32gui.SetForegroundWindow(h)
    except Exception as exc:
        log("  foreground failed: %s" % type(exc).__name__)
    time.sleep(1.0)
    r = win32gui.GetWindowRect(h)
    img = ImageGrab.grab(bbox=r, all_screens=True)
    path = os.path.join(PICS, tag + ".png")
    img.save(path)
    made[tag] = {"view": vname, "png": os.path.basename(path),
                 "bytes": os.path.getsize(path), "size": list(img.size),
                 "windowTitle": title}
    log("  captured %-16s %dx%d  %d bytes" % (tag, img.size[0], img.size[1],
                                              os.path.getsize(path)))

try:
    mp.FileClose()
except Exception:
    pass
try:
    mp.Quit()
except Exception:
    pass
json.dump(made, open(os.path.join(HERE, "se_project_snapshot_result.json"), "w",
                     encoding="utf-8"), indent=1, ensure_ascii=False)
log("SNAPSHOT DONE: %d images" % len(made))
sys.exit(0 if len(made) >= 4 else 1)
