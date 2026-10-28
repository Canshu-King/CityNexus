"""Open the three classroom files the way a teacher double-clicks them, and
photograph the application window - not a hand-made picture of the data.

The R3 rejection was about exactly this: the automation gates were green while
the sheet was unreadable on screen. A page exported by Visio's own renderer
proves the page; it does not prove that the file opens, that the window shows
the drawing, or that Project lands on a Gantt with bars inside the first
screen. So each file is opened read-only (chmod 0444 + digest compared before
and after, because a plain Project open rewrites the .mpp container), the frame
is maximised, and PrintWindow(PW_RENDERFULLCONTENT) photographs it even if
another window is on top.

The frames are then measured, not just kept: ink fraction of the whole frame
and, for the .mpp, of the chart half only. A blank or occluded frame reads as
near-zero ink and fails the run.
"""
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import stat
import sys
import time

import win32gui
import win32ui
import win32com.client as w32
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CLS = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Classroom"
PICS = os.path.join(CLS, "previews")
LOG = open(os.path.join(HERE, "se_r43_eye_r2.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()
PW_RENDERFULLCONTENT = 2
SW_MAXIMIZE = 3
VSDX = ["Teacher_01_System_Overview", "Teacher_02_Agent_User_Flow",
        "Teacher_01_System_Overview_EN", "Teacher_02_Agent_User_Flow_EN"]
MPPS = ["Teacher_03_Project_Overview_R4",
        "Teacher_03_Project_Overview_R4_EN"]

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def sha(p, n=64):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


def lock_ro(p):
    os.chmod(p, stat.S_IREAD)


def unlock(p):
    os.chmod(p, stat.S_IWRITE | stat.S_IREAD)


def frame(stem, cls=None):
    """The visible Office frame showing this document.

    Project titles its frame after the file ("Project Professional - x.mpp");
    Visio's frame title is just "Visio Professional" on this install, so the
    caller passes the window class to match instead (measured: 'VISIOA').
    """
    user32 = ctypes.windll.user32
    out = []

    def cb(h, _l):
        if not user32.IsWindowVisible(h):
            return True
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(h, buf, 256)
        t = buf.value or ""
        c = win32gui.GetClassName(h)
        if stem not in t and not (cls and c == cls):
            return True
        try:
            r = win32gui.GetWindowRect(h)
        except Exception:
            return True
        if r[2] - r[0] < 600 or r[3] - r[1] < 400:
            return True
        out.append((h, t, r))
        return True

    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    user32.EnumWindows(EnumProc(cb), 0)
    return out


def grab(h):
    user32 = ctypes.windll.user32
    l, t, r, b = win32gui.GetWindowRect(h)
    if (r - l) * (b - t) > 40000000:
        raise SystemExit("window rect is %.0f megapixels; refusing to allocate"
                         % ((r - l) * (b - t) / 1e6))
    hwnd_dc = win32gui.GetWindowDC(h)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mfc_dc, r - l, b - t)
    save_dc.SelectObject(bmp)
    ok = user32.PrintWindow(h, save_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)
    img = Image.frombuffer("RGB", (r - l, b - t), bmp.GetBitmapBits(True), "raw",
                           "BGRX", 0, 1)
    win32gui.DeleteObject(bmp.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(h, hwnd_dc)
    return img, bool(ok)


def ink(img, box=None):
    im = img.convert("L")
    if box:
        im = im.crop(box)
    hist = im.histogram()
    return round(sum(hist[:245]) / float(im.size[0] * im.size[1]), 4)


def shoot(stem, app_kind):
    """Photograph the maximised frame of one open document. Returns a record."""
    frames = frame(stem, "VISIOA" if app_kind == "visio" else None)
    if not frames:
        return {"file": stem, "opened": False, "reason": "no visible frame titled "
                "after %r (the app may have opened it in an existing window)" % stem}
    h, title, rect = frames[0]
    ctypes.windll.user32.ShowWindow(h, SW_MAXIMIZE)
    time.sleep(1.6)
    img, ok = grab(h)
    out = os.path.join(PICS, stem + "_window.png")
    img.save(out)
    w, hh = img.size
    rec = {"file": stem, "app": app_kind, "title": title, "printwindow_ok": ok,
           "frame_px": [w, hh], "bytes": os.path.getsize(out),
           "ink_whole": ink(img), "ink_body": ink(img, (int(w * 0.05), int(hh * 0.16),
                                                        int(w * 0.97), int(hh * 0.97)))}
    if app_kind == "project":
        rec["ink_chart_half"] = ink(img, (int(w * 0.52), int(hh * 0.28), w, hh))
        rec["ink_table_half"] = ink(img, (0, int(hh * 0.28), int(w * 0.5), hh))
    log("%s frame %dx%d ink whole=%.4f body=%.4f %s" % (
        stem, w, hh, rec["ink_whole"], rec["ink_body"],
        ("chart=%.4f table=%.4f" % (rec["ink_chart_half"], rec["ink_table_half"])
         if "ink_chart_half" in rec else "")))
    return rec


def do_visio(recs):
    vis = w32.DispatchEx("Visio.Application")
    vis.Visible = True
    try:
        vis.AlertResponse = 7
    except Exception:
        pass
    docs = []
    try:
        for stem in VSDX:
            p = os.path.join(CLS, stem + ".vsdx")
            before = sha(p)
            lock_ro(p)
            try:
                # Measured on this install: flag 16 (visOpenBudget) opens the
                # right page but renames the document "绘图1", so nothing in the
                # UI identifies the file any more; flag 2 keeps the real name.
                # Read-only is enforced by the chmod above and proved by the
                # digest comparison afterwards, not by a flag.
                d = vis.Documents.OpenEx(p, 2)
                log("%s opened as %r, page has %d shapes"
                    % (stem, d.Name, d.Pages.Item(1).Shapes.Count))
            except Exception as exc:
                unlock(p)
                recs.append({"file": stem, "opened": False,
                             "reason": "%s: %s" % (type(exc).__name__,
                                                   str(exc).splitlines()[0][:90])})
                continue
            docs.append((stem, p, before))
            time.sleep(1.2)
            recs.append(shoot(stem, "visio"))
    finally:
        for stem, p, before in docs:
            try:
                for i in range(vis.Documents.Count, 0, -1):
                    if vis.Documents.Item(i).Name.startswith(stem):
                        # Visio's Document.Close() takes no argument (Project's
                        # FileCloseEx does); calling it with one raised TypeError
                        # and left both drawings open in the instance.
                        vis.Documents.Item(i).Close()
            except Exception as exc:
                log("close %s: %s" % (stem, type(exc).__name__))
            unlock(p)
            after = sha(p)
            if after != before:
                log("DIGEST CHANGED on %s (%s -> %s)" % (stem, before[:12], after[:12]))
        try:
            vis.Quit()
        except Exception:
            log("WARN: Visio did not Quit")
    return recs


def do_project(recs, mpp):
    p = os.path.join(CLS, mpp + ".mpp")
    before = sha(p)
    lock_ro(p)
    mp = w32.DispatchEx("MSProject.Application")
    mp.Visible = True
    try:
        mp.DisplayAlerts = 0
    except Exception:
        pass
    try:
        # positional: pywin32 late binding does not always carry the keyword
        # names of Project's FileOpen, and a TypeError here would read as "the
        # file does not open"
        mp.FileOpen(p, True)
        time.sleep(2.5)
        recs.append(shoot(mpp, "project"))
    except Exception as exc:
        recs.append({"file": mpp, "opened": False,
                     "reason": "%s: %s" % (type(exc).__name__,
                                           str(exc).splitlines()[0][:90])})
    finally:
        try:
            mp.FileCloseEx(0)
        except Exception:
            pass
        try:
            mp.Quit()
        except Exception:
            log("WARN: Project did not Quit")
        unlock(p)
        after = sha(p)
        log("plan copy digest %s -> %s (unchanged=%s)"
            % (before[:12], after[:12], after == before))
    return recs


def main():
    os.makedirs(PICS, exist_ok=True)
    for f in [s + ".vsdx" for s in VSDX] + [m + ".mpp" for m in MPPS]:
        p = os.path.join(CLS, f)
        if not os.path.exists(p):
            raise SystemExit("missing %s - build it first" % p)
        log("%s %d bytes sha256/16 %s" % (f, os.path.getsize(p), sha(p, 16)))
    recs = []
    do_visio(recs)
    for mpp in MPPS:
        do_project(recs, mpp)
    json.dump(recs, open(os.path.join(HERE, "se_r43_eye_result_r2.json"), "w",
                         encoding="utf-8"), indent=1, ensure_ascii=False,
              default=str)
    bad = [r for r in recs if not r.get("opened", True) or r.get("ink_body", 0) < 0.01]
    for r in recs:
        if not r.get("opened", True):
            log("NOT OPENED: %s - %s" % (r["file"], r.get("reason")))
    for r in recs:
        if r.get("opened", True) and r.get("ink_body", 0) < 0.01:
            log("BLANK FRAME: %s ink_body=%.4f" % (r["file"], r.get("ink_body", 0)))
    log("R43 EYE PASS R2 %s (%d frames)" % ("OK" if not bad else "REFUSED",
                                             len(recs) - len(bad)))
    LOG.close()
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
