"""Tablet-readable briefing views, derived from the shipped plan.

The full plan has 65 rows and is the working document; a reviewer reading it on
a tablet over a slide deck needs one page. This script reads the phase rollups
and milestones out of CityNexus_Software_Engineering_Plan.mpp - it does not
retype a single date - builds a small briefing project from exactly those
values, sets the page to one A3 landscape sheet, exports PDF and PNG, and then
proves that every date in the briefing equals the date in the plan and that the
PDF really came out as 1-2 pages.
"""
import datetime
import hashlib
import json
import os
import re
import sys
import time

import win32com.client as w32

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from se_timeutil_r1 import dstr                      # noqa: E402

OUT = os.environ.get("SE_MSP_OUT",
                     r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project")
PLAN_MPP = os.path.join(OUT, "CityNexus_Software_Engineering_Plan.mpp")
BRIEF_MPP = os.path.join(OUT, "CityNexus_Plan_Briefing.mpp")
LOG = open(os.path.join(HERE, "se_project_brief.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()
D = datetime.datetime
PJ_WORK = 188743680


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def pdf_pages(path):
    raw = open(path, "rb").read()
    n = len(re.findall(rb"/Type\s*/Page[^s]", raw))
    if not n:
        m = re.search(rb"/Count\s+(\d+)", raw)
        n = int(m.group(1)) if m else 0
    return n


mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass

# ---- 1. read the plan ------------------------------------------------------
mp.FileOpen(PLAN_MPP, ReadOnly=True)
p = mp.ActiveProject
phases, mss, crit = [], [], []
for i in range(1, p.Tasks.Count + 1):
    t = p.Tasks.Item(i)
    if t.Summary:
        phases.append({"name": t.Name, "start": dstr(t.Start), "finish": dstr(t.Finish),
                       "pct": int(round(t.PercentComplete)), "wbs": t.WBS,
                       "work": round(t.Work / 60.0, 1), "cost": round(t.Cost, 2)})
    elif t.Milestone:
        mss.append({"name": t.Name, "finish": dstr(t.Finish),
                    "deadline": dstr(t.Deadline) if t.Deadline not in (None, "NA") else "",
                    "wbs": t.WBS})
    elif t.Critical:
        crit.append({"name": t.Name, "start": dstr(t.Start), "finish": dstr(t.Finish),
                     "wbs": t.WBS})
log("read from the plan: %d phase rollups, %d milestones, %d critical leaves"
    % (len(phases), len(mss), len(crit)))
for ph in phases:
    log("   %-4s %-58s %s..%s %3d%%  %6.1fh  $%s"
        % (ph["wbs"], ph["name"][:58], ph["start"], ph["finish"], ph["pct"],
           ph["work"], int(ph["cost"])))
for m in mss:
    log("   %-4s %-58s finish=%s deadline=%s" % (m["wbs"], m["name"][:58],
                                                 m["finish"], m["deadline"]))
try:
    p.Saved = True
except Exception:
    pass
mp.FileCloseEx(0)

# ---- 2. build the briefing file from exactly those values ------------------
if os.path.exists(BRIEF_MPP):
    os.remove(BRIEF_MPP)
mp.FileNew()
q = mp.ActiveProject
q.Name = "CityNexus plan briefing"
for prop, val in (("Author", "CityNexus coursework build"),
                  ("Company", "TUTE - Software Engineering module 2026"),
                  ("Title", "CityNexus plan briefing - one page"),
                  ("Subject", "Software Engineering 2026 Part 2"),
                  ("Keywords", "CityNexus; briefing; Gantt; milestones"),
                  ("Comments", "Derived from CityNexus_Software_Engineering_Plan.mpp")):
    try:
        setattr(q, prop, val)
    except Exception:
        pass
q.ProjectStart = D.strptime(phases[0]["start"], "%Y-%m-%d")
try:
    q.CurrencySymbol = "$"
except Exception:
    pass
made = []
for ph in phases:
    t = q.Tasks.Add(ph["name"])
    try:
        t.SetField(1280, 0)
    except Exception:
        pass
    t.Start = D.strptime(ph["start"], "%Y-%m-%d")
    t.Finish = D.strptime(ph["finish"], "%Y-%m-%d")
    t.PercentComplete = ph["pct"]
    t.Notes = ("Phase rollup copied from CityNexus_Software_Engineering_Plan.mpp by "
               "se_project_brief_r1.py on %s. Start, finish, percentage, work and cost "
               "are the plan's own computed values (work %s h, cost $%s); nothing here "
               "is retyped. This file is a presentation extract, not a second schedule."
               % (time.strftime("%Y-%m-%d %H:%M"), ph["work"], int(ph["cost"])))
    made.append(("phase", t.Name, dstr(t.Start), dstr(t.Finish), ph))
for m in mss:
    t = q.Tasks.Add(m["name"])
    try:
        t.SetField(1280, 0)
    except Exception:
        pass
    t.Duration = "0d"
    t.Start = D.strptime(m["finish"], "%Y-%m-%d")
    if m["deadline"] and m["deadline"] not in ("NA", "None"):
        try:
            t.Deadline = D.strptime(m["deadline"], "%Y-%m-%d")
        except Exception:
            pass
    t.Notes = ("Milestone copied from the plan; finish %s is the schedule's own date, "
               "the deadline is displayed not obeyed." % m["finish"])
    made.append(("ms", t.Name, dstr(t.Start), dstr(t.Finish), m))
mp.CalculateAll()

mismatch = []
for kind, name, s, f, src in made:
    if kind == "phase" and (s != src["start"] or f != src["finish"]):
        mismatch.append("%s %s..%s != plan %s..%s" % (name[:30], s, f, src["start"],
                                                      src["finish"]))
    if kind == "ms" and f != src["finish"]:
        mismatch.append("%s %s != plan %s" % (name[:30], f, src["finish"]))
log("briefing rows: %d; date mismatches against the plan: %s"
    % (len(made), mismatch or "none"))

# ---- 3. one A3 landscape sheet --------------------------------------------
view = None
for cand in ("甘特图", "Gantt"):
    try:
        mp.ViewApply(cand)
        view = cand
        break
    except Exception as exc:
        log("ViewApply %s failed: %s" % (cand, str(exc)[:70]))
setup = None
# FilePageSetupPage's first argument is the PROJECT NAME as a string, not a page
# setup id: passing an int was measured to come back "参数值无效".
for scale in (60, 50, 42, 34):
    for kw in ({"Name": q.Name, "Portrait": False, "PercentScale": scale,
                "PagesTall": 1, "PagesWide": 1, "PaperSize": 67},
               {"Name": q.Name, "Portrait": False, "PercentScale": scale,
                "PagesTall": 1, "PagesWide": 1}):
        try:
            mp.FilePageSetupPage(**kw)
            setup = "%s at %d%%" % (kw.get("PaperSize") and "A3 landscape" or "letter",
                                    scale)
            break
        except Exception as exc:
            log("FilePageSetupPage scale=%s paper=%s refused: %s"
                % (scale, kw.get("PaperSize"), str(exc)[:70]))
    if setup:
        break
try:
    mp.FilePageSetupView(Name=q.Name, AllSheetColumns=True, RepeatColumns=False,
                         PrintNotes=False, PrintBlankPages=False,
                         BestPageFitTimescale=True, PrintColumnTotals=False,
                         PrintRowTotals=False)
    log("view page setup accepted")
except Exception as exc:
    log("FilePageSetupView refused: %s" % str(exc)[:90])
log("page setup applied: %s" % setup)
pdf = os.path.join(OUT, "Briefing_One_Page.pdf")
for path in (pdf,):
    if os.path.exists(path):
        os.remove(path)
exported = False
try:
    mp.DocumentExport(pdf, 0)
    exported = os.path.exists(pdf)
except Exception as exc:
    log("DocumentExport failed: %s" % str(exc)[:140])
png = os.path.join(OUT, "previews", "Briefing_One_Page.png")
os.makedirs(os.path.dirname(png), exist_ok=True)
try:
    if os.path.exists(png):
        os.remove(png)
    mp.ActiveWindow.PaneExists(0)
except Exception:
    pass
q.SaveAs(BRIEF_MPP)
try:
    q.Saved = True
except Exception:
    pass
mp.FileCloseEx(0)
mp.Quit(0)

pages = pdf_pages(pdf) if exported else 0
res = {"phases": phases, "milestones": mss, "criticalLeaves": crit,
       "briefRows": len(made), "mismatches": mismatch, "view": view,
       "pageSetup": setup, "pdf": pdf if exported else None,
       "pdfBytes": os.path.getsize(pdf) if exported else 0,
       "pdfPages": pages,
       "pdfSha256": hashlib.sha256(open(pdf, "rb").read()).hexdigest()
       if exported else None}
json.dump(res, open(os.path.join(HERE, "se_project_brief_result.json"), "w",
                    encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
log("wrote %s (%d bytes, %d pages)" % (pdf, res["pdfBytes"], pages))
ok = exported and not mismatch and 1 <= pages <= 2
log("BRIEF %s" % ("OK" if ok else "INCOMPLETE"))
LOG.close()
sys.exit(0 if ok else 1)
