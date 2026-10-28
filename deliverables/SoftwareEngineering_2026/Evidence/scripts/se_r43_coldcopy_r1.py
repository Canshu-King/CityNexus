"""R5 cold-boot readiness: the classroom set must open from a directory it has
never lived in.

The noon-era checkpoint (CHECKPOINT.md P0) ran exactly this against the R3 set:
copy every native deliverable to a fresh directory, open each one read-only,
and require success - a file that only opens in place carries a hidden absolute
reference and fails on the teacher's machine. The R5 bilingual set changed every
Visio file and added two, so the check runs again. Opening uses the same
read-only discipline as se_r43_eye_r2.py (chmod 0444 + digest before/after,
because a plain Project open rewrites the .mpp container even without a save).
"""
import hashlib
import json
import os
import shutil
import sys
import time

import win32com.client as w32

HERE = os.path.dirname(os.path.abspath(__file__))
CLS = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Classroom"
FRESH = r"E:\r43_review\coldboot_1029"
FILES = ["Teacher_01_System_Overview.vsdx",
         "Teacher_02_Agent_User_Flow.vsdx",
         "Teacher_01_System_Overview_EN.vsdx",
         "Teacher_02_Agent_User_Flow_EN.vsdx",
         "Teacher_03_Project_Overview_R4.mpp",
         "Teacher_03_Project_Overview_R4_EN.mpp"]
OUT = os.path.join(HERE, "se_r43_coldcopy_r1.json")
T0 = time.time()


def log(m):
    print("[%5.1fs] %s" % (time.time() - T0, m), flush=True)


def sha(p, n=64):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


results = []
if os.path.exists(FRESH):
    shutil.rmtree(FRESH)
os.makedirs(FRESH)
for f in FILES:
    src = os.path.join(CLS, f)
    dst = os.path.join(FRESH, f)
    shutil.copy2(src, dst)
    os.chmod(dst, 0o444)
    before = sha(dst)

vis = None
prj = None
try:
    for f in FILES:
        dst = os.path.join(FRESH, f)
        rec = {"file": f, "opened": False}
        try:
            if f.endswith(".vsdx"):
                if vis is None:
                    vis = w32.DispatchEx("Visio.Application")
                    vis.Visible = False
                    try:
                        vis.AlertResponse = 7
                    except Exception:
                        pass
                d = vis.Documents.OpenEx(dst, 2)
                rec["opened"] = True
                rec["pages"] = int(d.Pages.Count)
                rec["shapesPage1"] = int(d.Pages.Item(1).Shapes.Count)
                rec["activePage"] = vis.ActiveWindow.Page.Name
                d.Close()
            else:
                if prj is None:
                    prj = w32.DispatchEx("MSProject.Application")
                    prj.Visible = False
                    try:
                        prj.DisplayAlerts = 0
                    except Exception:
                        pass
                prj.FileOpen(dst, True)
                rec["opened"] = True
                rec["tasks"] = int(prj.ActiveProject.Tasks.Count)
                prj.FileCloseEx(0)
        except Exception as exc:
            rec["error"] = "%s: %s" % (type(exc).__name__,
                                       str(exc).splitlines()[0][:120])
        after = sha(dst)
        rec["unchanged"] = (after == before)
        rec["sha16"] = after
        log("%-42s opened=%s pages/tasks=%s active=%s unchanged=%s"
            % (f, rec.get("opened"), rec.get("pages", rec.get("tasks")),
               rec.get("activePage", "-"), rec["unchanged"]))
        results.append(rec)
finally:
    try:
        if vis is not None:
            vis.Quit()
    except Exception:
        pass
    try:
        if prj is not None:
            prj.Quit()
    except Exception:
        pass
    for f in FILES:
        try:
            os.chmod(os.path.join(FRESH, f), 0o644)
        except Exception:
            pass

json.dump(results, open(OUT, "w", encoding="utf-8"), indent=1,
          ensure_ascii=False)
bad = [r for r in results if not r.get("opened") or not r.get("unchanged")]
log("COLD BOOT %s (%d/%d opened+unchanged)"
    % ("OK" if not bad else "REFUSED", len(results) - len(bad), len(results)))
sys.exit(1 if bad else 0)
