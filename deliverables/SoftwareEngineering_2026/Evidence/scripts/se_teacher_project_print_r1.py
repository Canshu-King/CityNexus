"""Project's own print output for the classroom plan sheet, and the numbers on it.

The chart pane of a Gantt view opens parked near the status date, and on this
install the timescale start cannot be written by any API that is reachable from
COM (TimescaleStart/TimescaleFinish: type mismatch; TimescaleEdit: refused for
18 argument shapes; ViewWhole / SplitBestFit / GoTo / Window.Scroll: do not
exist; WM_HSCROLL to a grid pane scrolls the wrong pane and the state it leaves
behind is worse). Ctrl+Home in the chart pane was tried with the foreground
verified - the frame is byte-identical before and after.

So the "all bars on one screen" picture is taken from the one thing Project
does control: FilePrint / DocumentExport. The page kept is the FIRST page that
carries chart ink, because a demo image has to start at the beginning of the
project, not at its densest. Nothing here is drawn by hand.
"""
import hashlib
import json
import os
import stat
import sys
import time

CLS = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Classroom"
PICS = os.path.join(CLS, "previews")
HERE = os.path.dirname(os.path.abspath(__file__))
MPP = os.path.join(CLS, "Teacher_03_Project_Overview.mpp")
PDF = os.path.join(PICS, "Teacher_03_Project_Overview_print.pdf")
OUT = "Teacher_03_Project_Overview_bars.png"
LOG = open(os.path.join(HERE, "se_teacher_project_print_r1.log"), "w",
           encoding="utf-8", buffering=1)
T0 = time.time()


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def sha(p, n=64):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


def ink(im, box=None):
    img = im.convert("L")
    if box:
        img = img.crop(box)
    hist = img.histogram()
    return round(sum(hist[:245]) / float(img.size[0] * img.size[1]), 4)


def main():
    import win32com.client as w32
    from PIL import Image
    os.makedirs(PICS, exist_ok=True)
    before = sha(MPP, 16)
    os.chmod(MPP, stat.S_IREAD)
    mp = w32.DispatchEx("MSProject.Application")
    mp.Visible = True
    try:
        mp.DisplayAlerts = 0
    except Exception:
        pass
    try:
        mp.FileOpen(MPP, True)
        time.sleep(2.0)
        try:
            mp.DocumentExport(PDF, 0)      # pjExFileType pdf, 0 = whole project
            log("DocumentExport -> %s (%d bytes)" % (os.path.basename(PDF),
                                                    os.path.getsize(PDF)))
        except Exception as exc:
            log("DocumentExport refused: %s %s" % (
                type(exc).__name__, str(exc).splitlines()[0][:90]))
            raise SystemExit(1)
        mp.FileCloseEx(0)
    finally:
        try:
            mp.Quit()
        except Exception:
            log("WARN: Project did not Quit")
        os.chmod(MPP, stat.S_IWRITE | stat.S_IREAD)
        after = sha(MPP, 16)
        log("classroom .mpp digest %s -> %s (unchanged=%s)" % (before, after,
                                                              before == after))
    try:
        import pymupdf
    except Exception:
        import fitz as pymupdf
    doc = pymupdf.open(PDF)
    log("Project printed %d page(s)" % doc.page_count)
    picked = None
    for i in range(doc.page_count):
        pix = doc.load_page(i).get_pixmap(dpi=140)
        tmp = os.path.join(PICS, "_t3page%d.png" % (i + 1))
        pix.save(tmp)
        im = Image.open(tmp)
        w, h = im.size
        v = ink(im, (int(w * 0.30), int(h * 0.10), w, int(h * 0.95)))
        log("  page %d: %dx%d chart ink %.4f" % (i + 1, w, h, v))
        if picked is None and v >= 0.02:
            keep = os.path.join(PICS, OUT)
            im.save(keep)
            picked = {"page": i + 1, "pages": doc.page_count, "chartInk": v,
                      "png": "Classroom/previews/" + OUT,
                      "bytes": os.path.getsize(keep), "px": [w, h],
                      "sha256_16": sha(keep, 16)}
        try:
            os.remove(tmp)
        except Exception:
            pass
    json.dump({"pdf": "Classroom/previews/" + os.path.basename(PDF),
               "pdfBytes": os.path.getsize(PDF), "pdfSha256_16": sha(PDF, 16),
               "picked": picked, "mppSha256_16": before},
              open(os.path.join(HERE, "se_teacher_project_print_result.json"), "w",
                   encoding="utf-8"), indent=1, ensure_ascii=False)
    if not picked:
        log("REFUSED: no printed page carries a chart - the print view is empty")
        LOG.close()
        return 1
    log("KEPT page %d of %d -> %s (chart ink %.4f, sha16 %s)" % (
        picked["page"], picked["pages"], picked["png"], picked["chartInk"],
        picked["sha256_16"]))
    LOG.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
