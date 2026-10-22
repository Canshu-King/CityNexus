"""Insert the R3 section into the generated README, with every number read here.

Kept as a separate module so the R2 document generator stays untouched: this file
appends one section to README.md right after the literal that closes it, and it
measures the artefacts (page counts, screenshot pixels, digests) instead of
repeating what the round was supposed to achieve.

Every line of the document is exactly one append call, because a markdown table
row that is split across three list items renders as three broken lines.
"""
import glob
import hashlib
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
MSP = os.path.join(DEL, "Microsoft_Project")


def j(name):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def size(p):
    return os.path.getsize(p) if os.path.exists(p) else 0


def sha(p, n=16):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


def pdf_pages(path):
    data = open(path, "rb").read()
    hits = [int(x) for x in re.findall(rb"/Count\s+(\d+)", data)]
    return max(hits) if hits else 0


def rel(p):
    return os.path.relpath(p, DEL).replace("\\", "/")


def build():
    prj = j("se_project_build_r2_result.json") or {}
    stat = j("se_plan_status_result.json") or {}
    rec = j("se_project_recovery_result.json") or {}
    snap = j("se_project_snapshot_r2_result.json") or {}
    deck = j("se_deck_result.json") or {}
    cap = prj.get("capacity") or {}
    late = [e for e in (stat.get("entries") or []) if e.get("late")]
    weekly = cap.get("weekly") or []
    over = [w for w in weekly if w["overallocatedHours"] > 0]
    peak = max([w["assignedHours"] for w in weekly] or [0])
    avail = (cap.get("availabilityPerWeek") or {}).get("yang", 0.0)
    gate = (deck.get("gate") or {})
    t = []
    a = t.append

    a("")
    a("## What changed in round 3 (2026-10-23)")
    a("")
    a("The external review of round 2 (`Evidence/INDEPENDENT_R2_REVIEW_20261022.md`)")
    a("accepted the Visio property fix, the agent-flow correction and the dependency")
    a("fix, and asked for three product-level things instead, plus two evidence-")
    a("integrity items. This round is those five; the accepted work was not redone.")
    a("")
    a("| the complaint | what is in the pack now | where to read it |")
    a("|---|---|---|")
    a("| 1808 student hours against about 840 available | each task carries its own "
      "effort split by person, and the build refuses to publish if any person-week "
      "exceeds declared availability: **%.1f student hours, peak week %.1f h against "
      "%.0f h, %d over-allocated person-weeks** | `Evidence/STATUS_AND_OVERDUE.md`, "
      "sheet 4 of the deck |" % (cap.get("studentHours", 0.0), peak, avail, len(over)))
    a("| only 4 late rows were admitted | the table is generated from the shipped "
      "file and lists **all %d** rows past their planned finish with the original "
      "span, the booked percentage and the re-forecast date | "
      "`Evidence/STATUS_AND_OVERDUE.md` |" % len(late))
    a("| the A3 one-pager is 5.8 pt and the screenshots showed Chrome | a 16:9 "
      "briefing deck with a 13 pt floor enforced by the drawing gate, and "
      "screenshots taken with Win32 `PrintWindow`, which cannot photograph the "
      "window that happens to be on top | `Presentation/`, "
      "`Microsoft_Project/previews/` |")
    a("| three finish dates quoted as one truth | every date is labelled with the "
      "clock that produced it and the two schedulers are compared row by row | "
      "`Evidence/PLAN_RECONCILIATION.md` |")
    a("| documents pointed at files that were not in the package | the packaging "
      "step checks every relative path a document cites, and the report says which "
      "ones were broken | `Evidence/R3_RESULT.md` |")
    a("")
    a("### The date reader was wrong, and it changed the answer")
    a("")
    a("Comparing the two schedulers exposed this: `se_timeutil_r1.dstr()` shifted "
      "every end-of-working-day value into the next calendar day. pywin32 hands "
      "Project's `2026-09-09 17:00` back tagged with a timezone that is not this "
      "machine's, and converting it to local time added eight hours. The grid shows "
      "9月9日; every document written from that JSON said 09-10.")
    a("")
    a("It is fixed, the reader now carries a self-test that the build refuses to run "
      "without, and the consequences are reported rather than hidden: the lateness "
      "count moved from the 10 the review took from my own table to **%d**, and one "
      "person-week that the shifted dates had been hiding became visible - two "
      "September estimates were re-sized to clear it, which is why the student total "
      "reads %.1f h." % (len(late), cap.get("studentHours", 0.0)))
    a("")
    a("### Presentation deck, measured")
    a("")
    a("`Presentation/CityNexus_SE2026_Briefing_Deck.vsdx`: four 13.333 x 7.5 in "
      "sheets, %d shapes, %d connectors, gate failures %d. Body text has a 13 pt "
      "floor and the gate refuses a sheet that breaks it; the layout pass calls the "
      "engine's own word wrap, so a box the layout says fits really fits."
      % (gate.get("nodes", 0), gate.get("edges", 0), len(gate.get("failures") or [])))
    a("")
    a("| deck preview | bytes |")
    a("|---|---|")
    for f in sorted(glob.glob(os.path.join(DEL, "Presentation", "previews", "*.png"))):
        a("| `Presentation/previews/%s` | %d |" % (os.path.basename(f), size(f)))
    a("")
    a("### Project screenshots, and how they were taken")
    a("")
    a("Method %s. The plan was opened **read-only at the filesystem level**, because "
      "a plain open makes Project rewrite the container on close even when nothing "
      "was edited: digest before `%s`, after `%s`. No Office lock file was left "
      "(%s). Each frame is tested for not being blank - colour count and non-white "
      "pixel fraction - before it is kept."
      % (snap.get("method", "?"), str(snap.get("sha256Before"))[:16],
         str(snap.get("sha256After"))[:16],
         "none" if not snap.get("lockFilesLeft") else str(snap.get("lockFilesLeft"))))
    a("")
    a("| view | file | pixels | ink fraction | windows overlapping it |")
    a("|---|---|---|---|---|")
    for k, v in sorted((snap.get("views") or {}).items()):
        a("| %s | `%s` | %sx%s | %s | %d |"
          % (v.get("view"), v.get("png"), (v.get("px") or [0, 0])[0],
             (v.get("px") or [0, 0])[1], v.get("inkFraction"),
             len(v.get("occludedBy") or [])))
    a("")
    a("The last column is the honest part: other windows really are on top of "
      "Project on this desktop while the capture runs, which is exactly why the "
      "screen-rectangle grab of round 2 was wrong. `PrintWindow` renders the target "
      "window into its own device context, so the image is Project's pixels "
      "regardless of z-order, and each file was also looked at by eye.")
    a("")
    a("### Printed PDFs, with their real page counts")
    a("")
    a("The round-2 print named Briefing_One_Page.pdf is gone from the tree - it was "
      "twelve pages. The same print ships as "
      "`Microsoft_Project/Plan_Briefing_Print.pdf` and the count is stated here "
      "instead of promised by a filename.")
    a("")
    a("| file | pages | bytes |")
    a("|---|---|---|")
    for p in sorted(glob.glob(os.path.join(MSP, "*.pdf")) +
                    glob.glob(os.path.join(DEL, "Presentation", "previews", "*.pdf")) +
                    glob.glob(os.path.join(DEL, "Briefing", "previews", "*.pdf"))):
        a("| `%s` | %d | %d |" % (rel(p), pdf_pages(p), size(p)))
    a("")
    a("### New files this round")
    a("")
    a("* `Evidence/STATUS_AND_OVERDUE.md` - four date clocks, the full lateness "
      "table, the per-person per-week capacity table.")
    a("* `Evidence/PLAN_RECONCILIATION.md` - static pass against the engine, row by "
      "row, with the offset accounted for.")
    a("* `Evidence/R3_RESULT.md` - what was fixed and what is still not proven.")
    a("* `Evidence/CLASSROOM_20261023_README.md` - the noon demonstration sheet: what "
      "to open in which order, the recorded open/move/edit/save/reopen results from "
      "`se_classroom_demo_r1.py`, and the fallback previews if Office will not start.")
    a("* `Microsoft_Project/CityNexus_Plan_Recovery.mpp` - open work only, scheduled "
      "from the status date; finishes %s against the 2026-11-06 contract date."
      % rec.get("finish", "?"))
    a("* `Presentation/CityNexus_SE2026_Briefing_Deck.vsdx` and its previews.")
    a("* Generators: `se_plan_status_r1.py`, `se_project_recovery_r1.py`, "
      "`se_deck_r1.py`, `se_project_snapshot_r2.py`, `se_evidence_reconcile_r1.py`, "
      "`se_docs_r3_section_r1.py`.")
    return "\n".join(t) + "\n"
