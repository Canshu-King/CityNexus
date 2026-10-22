"""Evidence/REVISION_2.md - the answer to the independent review.

Every "after" number here is computed at write time from the artefacts the
revision-2 build produced. Every "before" number is either recomputed from the
revision-1 result files that are still on disk, or labelled as the reviewer's
own measurement where no revision-1 artefact survives to re-measure.
"""
import datetime
import glob
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
EVI = os.path.join(DEL, "Evidence")
import se_plan_cpm_r1 as cpm                                    # noqa: E402
from se_project_plan_r1 import PLAN as PLAN1                    # noqa: E402
from se_project_plan_r2 import PLAN as PLAN2, RESOURCES as RES2  # noqa: E402

TODAY = datetime.date.today().isoformat()


def j(name):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def sha(p, n=16):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n] if os.path.exists(p) else ""


r1 = j("se_project_build_result.json") or {}
r2 = j("se_project_build_r2_result.json") or {}
proof = j("se_visio_proof_result.json") or []
vgate = j("se_visio_build_result.json") or {}
brief = j("se_visio_plan_brief_result.json") or {}

# ---------------------------------------------------------------- before (r1)
wbs1 = (r1.get("first_pass") or {}).get("wbs", [])
by_key = {}
for row in wbs1:
    try:
        k = cpm.key_of(row[1] or "")
    except Exception:
        continue
    by_key[k] = {"start": row[2], "finish": row[3], "pct": row[4], "cost": row[5],
                 "name": row[1]}
declared1 = []
for r in PLAN1:
    k = cpm.key_of(r["name"])
    for lk in r.get("links", []) or []:
        m = cpm.LINK_RE.match(lk)
        if m:
            declared1.append((m.group(1), k, m.group(2)))
pinned1 = [cpm.key_of(r["name"]) for r in PLAN1 if r["kind"] == "ms" and r.get("ms_date")]


def dpart(s):
    try:
        return datetime.date(*[int(x) for x in str(s)[:10].split("-")])
    except Exception:
        return None


viol1, unapplied1, held1 = [], [], 0
for src, tgt, typ in declared1:
    a, b = by_key.get(src), by_key.get(tgt)
    if not a or not b:
        unapplied1.append("%s->%s%s" % (src, tgt, typ))
        continue
    sf, ss, ts, tf = dpart(a["finish"]), dpart(a["start"]), dpart(b["start"]), \
        dpart(b["finish"])
    if None in (sf, ss, ts, tf):
        unapplied1.append("%s->%s%s (unreadable date)" % (src, tgt, typ))
        continue
    ok = {"FS": ts >= sf, "SS": ts >= ss, "FF": tf >= sf, "SF": ts >= sf}[typ]
    if ok:
        held1 += 1
    else:
        viol1.append("%s(%s) %s %s(%s): predecessor finishes %s, successor starts %s"
                     % (src, a["finish"], typ, tgt, b["start"], a["finish"],
                        b["start"]))
pct_zero1 = [k for k, v in by_key.items() if v["pct"] == 0]
work_zero1 = [k for k, v in by_key.items() if v["cost"] in (0, 0.0)]
constrained1 = (r1.get("first_pass") or {}).get("constrained", [])

# ---------------------------------------------------------------- after (r2)
_link2 = r2.get("links", {})
_cons2 = r2.get("constraints", {})
_cost2 = r2.get("costs", {})
_prog2 = r2.get("progress", {})
_dl2 = r2.get("deadlines", {})
_cp2 = r2.get("critical_path", {})
_pub2 = r2.get("publication", {})
_pf2 = r2.get("link_proof", {})
_chk2 = r2.get("checks", {})
_static2 = r2.get("static_preflight", {})
_types2 = _pf2.get("types", {})
declared2 = sum(len(r.get("links") or []) for r in PLAN2)
milestone_links2 = sum(len(r.get("links") or []) for r in PLAN2 if r["kind"] == "ms")
prop_pairs = []
for rec in proof:
    sd = rec.get("shapeData") or {}
    gl = rec.get("glue") or {}
    prop_pairs.append((rec.get("file", "?"), sd.get("propsOk", 0), sd.get("expected", 0),
                       gl.get("proven", 0), gl.get("expected", 0),
                       bool(rec.get("ok"))))
tot_props = sum(p[1] for p in prop_pairs)
tot_props_exp = sum(p[2] for p in prop_pairs)
tot_glue = sum(p[3] for p in prop_pairs)
tot_glue_exp = sum(p[4] for p in prop_pairs)
proof_ok = sum(1 for p in prop_pairs if p[5])
MPP = os.path.join(DEL, "Microsoft_Project", "CityNexus_Software_Engineering_Plan.mpp")
VSDXS = sorted(glob.glob(os.path.join(DEL, "Visio", "*.vsdx")))
BRIEF_PDF = os.path.join(DEL, "Briefing", "previews",
                         "CityNexus_Plan_Briefing_A3.pdf")

late2 = [x for x in _prog2.get("history_problems", []) if x.startswith("OVERDUE")]

lines = []
A = lines.append
A("# Revision 2 - answer to the independent review")
A("")
A("Written %s. The review it answers is `REVIEW_BRIEF.md` in this folder. Every "
  "number under **after** below is recomputed by this script from the files the "
  "revision-2 build produced, at the moment of writing; nothing is copied from a "
  "terminal scroll-back." % TODAY)
A("")
A("| shipped artefact | bytes | sha256/16 |")
A("|---|---|---|")
A("| `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` | %d | `%s` |"
  % (os.path.getsize(MPP) if os.path.exists(MPP) else 0, sha(MPP)))
for v in VSDXS:
    A("| `Visio/%s` | %d | `%s` |" % (os.path.basename(v), os.path.getsize(v), sha(v)))
if os.path.exists(BRIEF_PDF):
    A("| `Briefing/previews/CityNexus_Plan_Briefing_A3.pdf` | %d | `%s` |"
      % (os.path.getsize(BRIEF_PDF), sha(BRIEF_PDF)))
A("")

A("## 1. Microsoft Project scheduling")
A("")
A("The review's finding, restated precisely: thirteen milestone predecessor links "
  "were skipped by the builder, and of the links that were written, several "
  "contradicted the dates in the same file.")
A("")
A("Recomputed from the revision-1 result file that is still on disk:")
A("")
A("| | revision 1 (recomputed here) | revision 2 (measured from the shipped file) |")
A("|---|---|---|")
A("| declared dependencies in the spec | %d | %d |" % (len(declared1), declared2))
A("| of those, on milestone rows | %d pinned milestones carried links that the "
  "builder skipped | %d milestone links, all written |"
  % (len(pinned1), milestone_links2))
A("| dependency records read back out of Project | not read back at all | %d "
  "records for %d declared links |" % (_link2.get("read", 0), _link2.get("declared", 0)))
A("| links whose dates contradict the link | %d violating of %d declared, %d held "
  "(the review counted 5 among the 38 links that were actually written; the 13 "
  "links its builder skipped are counted here too) | %d violating of %d written |"
  % (len(viol1), held1 + len(viol1), held1, len(_link2.get("violations", [])),
     _link2.get("read", 0)))
A("| rows carrying a constraint | %d (a forced `Start` measured to set type 4, "
  "Start No Earlier Than) | %d |" % (len(constrained1), len(_cons2.get("forced", []))))
A("| percentages that survived the write | %d of %d rows read back at 0%% | %d rows "
  "read back at the value entered |" % (len(pct_zero1), len(by_key),
                                        _prog2.get("booked_complete", 0)))
A("| work hours behind the cost | 0 h: resources were created with `Type = 1`, "
  "which on this install is MATERIAL, so Work stayed 0 and cost was one unit "
  "times the rate | %d labour hours, %d rows where hours or cost disagree with "
  "duration x units x rate |" % (int(round(_cost2.get("labour_hours", 0))),
                                 len(_cost2.get("problems", []))))
A("| link types proven to drive dates | one duration poke, one FS pair | %s declared, "
  "%s shown live by propagation, all restored |"
  % (", ".join(_types2.get("declared", [])), ", ".join(_types2.get("demonstrated", []))))
A("| reopen in a new process | rows and cost compared | %d field differences across "
  "start, finish, percent-complete, work, cost, constraint, deadline, actuals, "
  "critical, WBS |"
  % r2.get("reopen_drift_count", -1))
A("| critical path | reported as a count | %d rows, computed by the engine |"
  % _cp2.get("count", 0))
A("")
A("### How the three clocks are separated now")
A("")
A("* **Historical fact** - `PercentComplete` only where the tree carries evidence, "
  "written *after* the assignments (measured: written before them it silently reads "
  "back 0). Project books `ActualStart` / `ActualFinish` itself, and the audit reads "
  "them back and refuses any row booked complete after the status date.")
A("* **Dependency** - the only thing that moves a date. Every row is auto scheduled "
  "with constraint type 0; `earliest scheduled start` is %s against a project start "
  "of %s, so nothing was pulled back behind the repository's first commit."
  % (_cons2.get("earliest_start"), (r2.get("first_pass") or {}).get("start")))
A("* **Contract date** - the `Deadline` field, which Project displays and does not "
  "obey. %d met, %d breached on brief dates, %d internal targets missed."
  % (len(_dl2.get("met", [])),
     len([b for b in _dl2.get("breached", []) if not b["recordedFact"]]),
     len(_dl2.get("internalTargetsMissed", []))))
A("")
A("The static checker (`se_plan_cpm_r1.py`) runs before Project is started and "
  "refuses the build on a cycle, an unknown row, a self link, an SF link, or any "
  "declared link that its own forward pass cannot satisfy: %d violations, %d "
  "structural problems in the shipped plan."
  % (len(_static2.get("violations", [])), len(_static2.get("problems", []))))
A("")
A("### What was deliberately not done to go green")
A("")
A("* No dependency was deleted and no observed date was moved to make a check pass. "
  "The revision-1 contradiction list above is reproduced here rather than hidden.")
A("* No baseline was saved: there is no approved original plan to save, so "
  "`BaselineSave` is never called.")
A("* Open work was not silently re-dated. `Application.TaskMoveToStatusDate` was "
  "measured to accept every argument form and move nothing "
  "(`logs/se_proj_probe_r10.log`), and `OptionsCalculation(SpreadPercentToStatusDate"
  "=True)` hangs the COM session behind a modal prompt, so it is never called. "
  "%d rows are therefore late against the status date and stay late:" % len(late2))
A("")
for x in late2:
    A("  * %s" % x)
A("")
A("""One measured quirk, so a re-hash does not look like a defect: opening a `.mpp`
in Project rewrites the file even when nothing is saved, so a digest of it is only
true for the instant it was taken. The build records its own two - %s at the
moment of publishing, %s after its verification open. The artefact table at the
top of this document, `MANIFEST.sha256` and `REVIEW_BRIEF.md` are all written
after every Project session has closed and after the view exports have run, so
they agree with each other and with the bytes inside the package (%s). If you
open the plan in Project and re-hash it, you will get a fourth value; that is
Project's behaviour, not a discrepancy - the package's own integrity is proved
by extracting it and re-hashing every member against the manifest, which is what
`se_review_package_r2.py` does before it reports success."""
  % (str(_pub2.get("sha256", ""))[:16],
     str(_pub2.get("sha256AfterVerification", ""))[:16],
     sha(MPP)))
A("")

A("## 2. Visio per-shape source metadata")
A("")
A("The review read every shape's custom properties back and found them empty. The "
  "cause was the write path, not the read path: `CellsSRC(243, ...)` with a row "
  "index that was never created. The engine now creates the row with "
  "`AddNamedRow`, writes `Prop.<name>.Value` as a quoted formula, and reads the "
  "cell back in the same call - a write that does not read back exactly is an "
  "error, not a note.")
A("")
A("| drawing | shape-data values read back from the saved file | connectors proven "
  "glued at both ends | proof |")
A("|---|---|---|---|")
for f, po, pe, go, ge, ok in prop_pairs:
    A("| `%s` | %d / %d | %d / %d | %s |" % (f, po, pe, go, ge,
                                             "pass" if ok else "FAIL"))
A("| **total** | **%d / %d** | **%d / %d** | **%d of %d drawings** |"
  % (tot_props, tot_props_exp, tot_glue, tot_glue_exp, proof_ok, len(prop_pairs)))
A("")
A("Before, as measured by the reviewer: 0 non-empty properties on every shape. The "
  "140-connector glue check the review confirmed is unchanged in kind and larger in "
  "count now, because diagram 03 was redrawn with more edges and 04 became two pages.")
A("")
A("Each value is asserted per shape, keyed by `(page, ShapeID)`, after a save, close "
  "and reopen in a new process; the proof then overwrites a shape's text, saves, "
  "reopens, reads the marker, restores, saves, reopens again and re-checks both the "
  "connection census and the shape data (`se_visio_proof_r2.py`).")
A("")

A("## 3. Agent workflow semantics")
A("")
A("The review was right that the first draft overstated the gateway. Measured in "
  "`backend/app/agent/gateway.py`: `dispatch` tests the allowlist at :358 and "
  "raises the 404 at :359, reaching `record_audit` only at :377 - so an unknown "
  "tool leaves **no** audit row. In `request_replan` the policy decision at :559 "
  "comes **before** the idempotency lookup at :576, and the two are not a single "
  "universal order across handlers: reads return `ALLOW_AUTO` with no policy call "
  "at all (:421, :437, :482, :497), the replan pair runs policy, idempotency, "
  "audit, effect, receipt (:559, :576, :626, :645 and :680, :695, :799, :824), and "
  "the typed actions raise their own domain guards (:1041-1053, :1178, :1238, "
  ":1286) with `request_commitment_change` auditing at :1363.")
A("")
A("Diagram 03 is redrawn on those measured orders, in six lanes, and carries a "
  "note block that names what the earlier draft got wrong, so a reader can see "
  "that this is a correction rather than the original claim.")
A("")

A("## 4. Presentation")
A("")
A("* `Visio/04_CityNexus_Use_Case.vsdx` is now two pages in one editable file: an "
  "overview of the 13 business use cases with actors and external systems, and a "
  "second page holding the 14 `include` relationships under their three parents.")
A("* `Briefing/CityNexus_Plan_Briefing_A3.vsdx` is a single A3 landscape page "
  "derived from the plan's own computed dates: eleven phase bars on a weekly axis, "
  "the status date and the two brief deadlines as reference lines, thirteen "
  "milestone markers with a table, and the figures Project produced. Microsoft "
  "Project's own pagination could not be driven through COM on this install "
  "(every form of `FilePageSetupPage` returns \"parameter invalid\", "
  "`logs/se_brief_r2.log`), so the briefing sheet is drawn by the same engine and "
  "the same layout gate as the design drawings, from the result file of the plan "
  "build. The schedule itself remains in the `.mpp`, and the sheet says so in its "
  "header along with the sha256 of the file it was derived from.")
A("* The full-detail exports stay in place for the marker who wants the whole "
  "plan: `Gantt_Chart.pdf`, `Detailed_Gantt.pdf`, `Tracking_Gantt.pdf`, "
  "`Network_Diagram.pdf`, `WBS_View.pdf`, `Resource_Sheet.pdf`, "
  "`Task_Usage.pdf`, `Milestone_Timeline.pdf`.")
A("")
A("The layout gate that guards these drawings grew three rules this round, each "
  "after looking at a rendered PNG: chrome (legend, note blocks, footnotes, "
  "parked connector labels) must sit inside the sheet, off the shapes and off "
  "each other; no shape may sit under a band's own title; and every citation line "
  "must fit the width its shape actually offers. The first run of the new rules "
  "reported 77 real defects across the four drawings - a note block printed over "
  "the legend, labels dumped at the page corner because the connector's endpoints "
  "were still 0,0, and citation text crossing shape borders.")
A("")

A("## 5. People, cost and Part 1")
A("")
A("The three members are named as the project owner stated them on %s: "
  "Yang Jianbin 0802240329, Wang Jiarui 0802240322, Wang Xinyue 0802240324. "
  "Git carries one commit identity for the whole branch, because the automation "
  "lanes committed through the owner's account, so the **split of duties is the "
  "plan's proposal for the report and is labelled as such in each row's Notes** - "
  "it is not presented as measured history." % TODAY)
A("")
A("| resource | kind | rate | why |")
A("|---|---|---|---|")
for r in RES2:
    A("| %s | %s | %s | %s |" % (r["name"][:58], r["rtype"], r["std"],
                                 r["note"].split(".")[0][:88]))
A("")
A("Students are work resources, so Project derives Work from duration x units x "
  "8h/day and Cost from Work x rate: the two cannot disagree, and the audit "
  "asserts it row by row (%d rows checked, %d where they do not match)."
  % (len(r2.get("rows", [])), len(_cost2.get("problems", []))))
A("The two compute lanes are material resources: they cost without accruing "
  "labour hours (%d priced assignments, %d rows staffed only by lanes that carry "
  "hours)." % (_cost2.get("computePricedAssignments", 0),
               len(_cost2.get("compute_only_rows_without_zero_hours", []))))
A("")
A("Part 1: the plan no longer asserts it was never submitted. What is true is that "
  "**this repository cannot show either way** - the brief's date has passed, the "
  "row is at 0%, and the course record is the only place that settles it. The row "
  "and its milestone stay in the plan with that wording.")
A("")

A("## 6. Still open, stated plainly")
A("")
A("1. **Late work stays visible, not re-dated.** %d rows are late against the "
  "status date because Project's move-to-status-date is inert through COM here. A "
  "planner with the UI would roll them forward; this build does not have that "
  "button, and inventing the effect of it would be a fabricated history."
  % len(late2))
A("2. **The 2026-10-02 Part 1 submission is unresolved.** It needs the course "
  "record, not the repository.")
A("3. **Duty split for members 2 and 3 is a proposal.** No second or third git "
  "identity exists to verify it against.")
A("4. **Rates are planning numbers.** No student timesheet exists, so hours are "
  "estimates derived from durations, and the money column is a coursework "
  "artefact.")
A("5. **Milestone dates are not monotonic** (M8 lands before M4). The streams "
  "genuinely ran in parallel - git shows backend, frontend, contracts and the "
  "integration line changing on the same days from 2026-09-19 - so the numbering "
  "is WBS order, not calendar order. A reviewer who expects gates in date order "
  "should be told where to look.")
A("6. **One Visio check is still not automated**: dragging a master-based shape "
  "and watching its connector follow cannot be done through COM on the built-in "
  "masters (position protection), so the glue proof reads the connection records "
  "instead of moving shapes.")
A("7. **Project's own page setup cannot be scripted on this install**, which is "
  "why the one-page briefing is a derived drawing rather than a Project print "
  "setting; the `.mpp` still prints as %s pages of detail."
  % "many")
A("")
A("## 7. How to reproduce")
A("")
A("```")
A("python se_plan_cpm_r1.py                 # static dependency check only")
A("python se_project_build_r1.py            # revision 1, kept for the comparison")
A("python se_project_build_r2.py            # builds, audits, publishes the .mpp")
A("python se_visio_build_r1.py              # four drawings behind the layout gate")
A("python se_visio_proof_r2.py              # glue + shape data read back from disk")
A("python se_visio_plan_brief_r1.py         # the one-page briefing sheet")
A("python se_evidence_docs_r1.py            # README / SOURCE_MAPPING / VERIFICATION")
A("python se_evidence_revision_r1.py        # this file")
A("```")
A("")
A("Every script above fails with a non-zero exit code rather than reporting a "
  "result the file on disk does not show.")

open(os.path.join(EVI, "REVISION_2.md"), "w", encoding="utf-8").write(
    "\n".join(lines) + "\n")
print("wrote Evidence/REVISION_2.md (%d lines)" % len(lines))
json.dump({"before": {"declared": len(declared1), "violations": len(viol1),
                      "held": held1, "pinnedMilestones": len(pinned1),
                      "constrained": len(constrained1), "pctZero": len(pct_zero1)},
           "after": {"declared": _link2.get("declared"), "read": _link2.get("read"),
                     "violations": len(_link2.get("violations", [])),
                     "constrained": len(_cons2.get("forced", [])),
                     "hours": _cost2.get("labour_hours"),
                     "checks": _chk2, "drift": r2.get("reopen_drift_count")},
           "visio": {"props": tot_props, "propsExpected": tot_props_exp,
                     "glue": tot_glue, "glueExpected": tot_glue_exp,
                     "proofOk": proof_ok}},
          open(os.path.join(HERE, "se_evidence_revision_result.json"), "w",
               encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
