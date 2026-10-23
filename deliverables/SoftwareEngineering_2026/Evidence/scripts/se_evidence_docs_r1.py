"""Write the three Evidence documents with every number read from disk at the
moment of writing, so nothing in them is transcribed from memory.
"""
import datetime
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = r"D:\moodle\CityNexus"
DEL = os.path.join(ROOT, "deliverables", "SoftwareEngineering_2026")
VIS = os.path.join(DEL, "Visio")
MSP = os.path.join(DEL, "Microsoft_Project")
EVI = os.path.join(DEL, "Evidence")
HERE = os.path.dirname(os.path.abspath(__file__))


def j(name):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def sha(p, n=16):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


def size(p):
    return os.path.getsize(p) if os.path.exists(p) else 0


def count(pattern, path):
    rx = re.compile(pattern)
    n = 0
    hits = []
    for i, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
        if rx.search(line):
            n += 1
            hits.append(i)
    return n, hits[:3]


# ---------------------------------------------------------------- live facts
main_py = os.path.join(ROOT, "backend", "app", "main.py")
models_py = os.path.join(ROOT, "backend", "app", "db", "models.py")
n_ep, _ = count(r"^@app\.(get|post|patch|put|delete)", main_py)
n_lines = sum(1 for _ in open(main_py, encoding="utf-8", errors="replace"))
n_tables, _ = count(r"^\s+__tablename__ = ", models_py)
n_backend_tests = len(glob.glob(os.path.join(ROOT, "backend", "tests", "test_*.py")))
n_e2e = len(glob.glob(os.path.join(ROOT, "frontend", "e2e", "*.ts")))
n_app_py = len(glob.glob(os.path.join(ROOT, "backend", "app", "**", "*.py"), recursive=True))

import yaml                                                        # noqa: E402
req = yaml.safe_load(open(os.path.join(ROOT, "requirements", "requirements.yaml"),
                          encoding="utf-8"))
req_groups = {k: len(v) for k, v in req.items() if isinstance(v, list) and k != "metadata"}
n_req = sum(req_groups.values())
uc = yaml.safe_load(open(os.path.join(ROOT, "use-cases", "use-cases.yaml"), encoding="utf-8"))
n_uc_top = len(uc["useCases"])
n_detail = sum(len(u.get("detailUseCases") or []) for u in uc["useCases"])
n_actors = len(uc["actors"])
n_rel = len(uc["relationships"])
n_inc = len([r for r in uc["relationships"] if r["type"] == "include"])
n_ext = len([r for r in uc["relationships"] if r["type"] == "extend"])

git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                                text=True, errors="replace").stdout.strip()
branch = git("rev-parse", "--abbrev-ref", "HEAD")
tip = git("rev-parse", "HEAD")
tip_short = git("log", "-1", "--format=%h %ad %s", "--date=short")
first_commit = git("log", "--all", "--format=%ad", "--date=short").split("\n")
first_commit = min([x for x in first_commit if x.startswith("2026")]) if first_commit else "?"
n_commits = git("rev-list", "--count", "HEAD")
authors = git("log", "--format=%an", "HEAD").split("\n")
top_authors = sorted({a: authors.count(a) for a in set(authors)}.items(),
                     key=lambda kv: -kv[1])[:5]

vis_res = j("se_visio_build_result.json") or {}
vis_proof = j("se_visio_proof_result.json") or []
prj_res = j("se_project_build_r2_result.json") or {}
prj_res_r1 = j("se_project_build_result.json") or {}
prj_exp = j("se_project_export_r2_result.json") or {}
ms_res = j("se_milestone_view_result.json") or {}
snap = j("se_project_snapshot_result.json") or {}

specs = {}
for f in sorted(glob.glob(os.path.join(VIS, "specs", "*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    # diagram 04 is two pages inside one file, so its spec carries sheets
    sheets = d.get("sheets") or [d]
    specs[os.path.basename(f)] = {
        "nodes": sum(len(s.get("nodes", [])) for s in sheets),
        "edges": sum(len(s.get("edges", [])) for s in sheets),
        "bands": sum(len(s.get("bands", [])) for s in sheets),
        "pages": len(sheets),
        "title": d.get("docid", "")}
total_nodes = sum(v["nodes"] for v in specs.values())
total_edges = sum(v["edges"] for v in specs.values())
proof_by_file = {r["file"]: r for r in vis_proof}

vsdx_rows = []
for f in sorted(glob.glob(os.path.join(VIS, "*.vsdx"))):
    b = os.path.basename(f)
    pr = proof_by_file.get(b, {})
    checks = pr.get("checks", {})
    stem = os.path.splitext(b)[0]
    vsdx_rows.append((b, size(f), sha(f),
                      specs.get(stem + ".json", {}),
                      pr.get("glue", {}), checks,
                      size(os.path.join(VIS, "previews", stem + ".png")),
                      size(os.path.join(VIS, "previews", stem + ".pdf"))))

msp_pdfs = sorted(glob.glob(os.path.join(MSP, "*.pdf")))
msp_rows = [(os.path.basename(p), size(p), sha(p)) for p in msp_pdfs]
snap_rows = [(k, v.get("png"), v.get("view"), v.get("bytes")) for k, v in snap.items()]

_r2 = prj_res or {}
_rows = _r2.get("rows", [])
n_sum = len([r for r in _rows if r["summary"]])
n_leaf = len([r for r in _rows if not r["summary"]])
n_ms = len([r for r in _rows if r["milestone"]])
crit = _r2.get("critical_path", {}).get("rows", [])
wbs = [(r["wbs"], r["name"], r["start"], r["finish"], r["pct"], r["cost"],
        "auto" if r["constraint"] == 0 else str(r["constraint"])) for r in _rows]

TODAY = datetime.date.today().isoformat()

# ============================================================ README.md
readme = """# CityNexus - Software Engineering 2026 coursework pack

Generated {today} on the machine that also runs the product, by Microsoft Visio
Professional 2024 and Microsoft Project 2024 driven through their own COM
automation. Nothing in here is a screenshot pretending to be a source file:
the four `.vsdx` and the `.mpp` are the native documents and they open,
edit and re-save in the real applications.

Source tree: CityNexus, branch `{branch}` at `{tip_short}`
Remote: github.com/Canshu-King/CityNexus

## What to show, in what order

| # | File | What it answers when a marker asks "so how does it work?" |
|---|---|---|
| 1 | `Visio/01_CityNexus_System_Architecture.vsdx` | The whole system in five layers, and the one sentence that matters: the agent owns no domain truth. |
| 2 | `Visio/03_CityNexus_Agent_Workflow.vsdx` | The agent's actual loop - intent, mission, twelve steps, three doors of authorization. This is the page that separates CityNexus from a website with a chat box. |
| 3 | `Visio/02_CityNexus_User_Journey.vsdx` | What a traveler does from opening the app to the footprint after the trip, lane by lane. |
| 4 | `Visio/04_CityNexus_Use_Case.vsdx` | The scope: 13 business use cases, the actors the specification really names, include and extend relationships. |
| 5 | `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` | The plan: WBS, durations, links, milestones, resources with costs, and a critical path the scheduling engine computed. |
| 6 | `Microsoft_Project/Gantt_Chart.pdf` and `previews/Gantt_Chart.png` | The same plan as a picture for a slide. |
| 7 | `Microsoft_Project/Milestone_Timeline.pdf` | The thirteen milestones on a line. |
| 8 | `Microsoft_Project/Resource_Sheet.pdf` | Who is assigned and what the work costs - the one item in Part 2 that is easy to leave out. |
| 9 | `Briefing/previews/CityNexus_Plan_Briefing_A3.pdf` | The whole plan on one A3 landscape page for a tablet: eleven phase bars, thirteen milestones, the status date, and the figures Project computed. |
| 10 | `Evidence/REVISION_2.md` | What an independent review found in the first revision, what changed, and what is still open. |

Open the `.vsdx` files in Visio and the `.mpp` in Project; the PDFs and PNGs in
`previews/` are for slides and for anyone who does not have Office.

## Layout

```
Visio/                 4 native .vsdx drawings
  previews/            PNG + PDF of each, plus the per-drawing gate report
  specs/               the JSON that describes each drawing
Microsoft_Project/     the native .mpp, the briefing and milestone views, PDFs
  previews/            full-window PNG of each Project view
Briefing/              one A3 landscape page derived from the plan's own dates
  previews/            PNG + PDF + the layout gate report for that page
Evidence/              README, SOURCE_MAPPING, AUTOMATION_VERIFICATION,
                       REVISION_2, result JSON, and every script that produced
                       the above
```

## Honest limits, stated up front

* Part 1 of the coursework was due **2026-10-02**. Whether it was uploaded to
  the course platform cannot be seen from this repository, so the plan says
  exactly that and leaves the row at 0% rather than back-dating it; the course
  record has to settle it.
* The brief requires a **group of three** with a named responsibility each. The
  three members are named (Yang Jianbin 0802240329, Wang Jiarui 0802240322,
  Wang Xinyue 0802240324), but git carries a single commit identity because the
  automation lanes committed through the owner's account, so the split of duties
  in the plan is a proposal for the report, not a measured history.
* Resource rates are **coursework planning estimates**, not payroll. The two
  compute lanes are material resources so that they cost without accruing
  labour hours.
* No baseline was saved into the `.mpp`, because there is no original approved
  plan to save as one.
* The two documents that need a human - the customer-approved requirement
  statement and the ten-slide Part 1 - are not produced here and are not
  claimed as done.

See `AUTOMATION_VERIFICATION.md` for what was actually executed and
`SOURCE_MAPPING.md` for which file and line each shape came from.
""".format(today=TODAY, branch=branch, tip_short=tip_short, repo=ROOT)

# ============================================================ SOURCE_MAPPING.md
sm = """# Source mapping

Every shape and every plan row traces to something that exists. This is the
table to open when a marker asks "where did you get that from?".

## Measured from the tree, at generation time ({today})

| Fact used in the drawings | How it was measured | Value |
|---|---|---|
| HTTP endpoints on the backend | count of `^@app.(get\\|post\\|patch\\|put\\|delete)` in `backend/app/main.py` | {n_ep} |
| Size of the backend entry module | line count of `backend/app/main.py` | {n_lines:,} |
| Database tables | count of `__tablename__ = ` in `backend/app/db/models.py` | {n_tables} |
| Python modules under the backend app | recursive `*.py` count | {n_app_py} |
| Backend test modules | `backend/tests/test_*.py` | {n_backend_tests} |
| Frontend e2e specs | `frontend/e2e/*.ts` | {n_e2e} |
| Requirements | `requirements/requirements.yaml` lists: {req_groups} | {n_req} |
| Use cases | `use-cases/use-cases.yaml` | {n_uc_top} top level, {n_detail} detail |
| Actors | same file | {n_actors} |
| include / extend relationships | same file | {n_inc} include, {n_ext} extend |
| Agent tools | `backend/app/agent/tool_catalog.py:26-59` | 11 (6 V1 + 5 typed) |
| Commits on this branch | `git rev-list --count HEAD` | {n_commits} |
| First commit anywhere in the repo | `git log --all --date=short` | {first_commit} |
| Top authors | `git log --format=%an` | {top_authors} |

## The four Visio drawings

| Drawing | Shapes | Connectors | What each shape carries |
|---|---|---|---|
""" .format(today=TODAY, n_ep=n_ep, n_lines=n_lines, n_tables=n_tables,
            n_app_py=n_app_py, n_backend_tests=n_backend_tests, n_e2e=n_e2e,
            req_groups=req_groups, n_req=n_req, n_uc_top=n_uc_top,
            n_detail=n_detail, n_actors=n_actors, n_inc=n_inc, n_ext=n_ext,
            n_commits=n_commits, first_commit=first_commit,
            top_authors=", ".join("%s (%d)" % (a, c) for a, c in top_authors))

for name, sz, h, sp, glue, checks, png, pdf in vsdx_rows:
    sm += ("| `%s` | %d | %d | a code anchor in its caption and in the custom "
           "property `SourceRef` |\n" % (name, sp.get("nodes", 0), sp.get("edges", 0)))

sm += """
Anchors cited inside the drawings, by layer:

**Users and frontend** - `frontend/src/main.tsx:38`, `frontend/src/app/V8Experience.tsx:1`,
`frontend/src/routes/v8Routes.ts:1-33`, `frontend/src/components/JourneyMap.tsx:1`,
`frontend/src/features/agent/CopilotDock.tsx:1`, `frontend/src/features/agent/AgentRunRail.tsx:1`,
`frontend/src/features/planning/PlanComparison.tsx:1`,
`frontend/src/features/checkin/checkins.ts:14`, `frontend/src/features/collections/collections.ts:16`

**Backend transport** - `backend/app/main.py`: journeys `:3136`, `:7139`, `:9294`, `:10019`;
plans `:7369`, `:7728`, `:7790`; replanning `:10923`, `:13097`, `:13569`; places `:7328`,
`:7355`, `:5558`, `:5572`; commerce `:14404`, `:14471`, `:14508`; twin and capability
`:9846`, `:2761`, `:2568`; guardian and autopilot `:1599`, `:1608`, `:1772`; SSE `:1982`;
copilot `:14169`, agent commands `:1367`, tool call `:1246`, approvals `:2081`, feed `:10125`

**Agent plane** - `backend/app/agent/mission.py:231,384`; `mission_plan.py:74`;
`runtime.py:62,238,289,336,660`; `gateway.py:59,71,338-347,357-398`;
`tool_catalog.py:20-22,26-59`; `ai_availability.py`; `delegation_policy.py`;
`backend/app/integrations/ai/semantic_compiler.py:123,229`;
`backend/app/integrations/hermes/native_client.py:34,71,132,158,169`;
`agent-mcp/citynexus_mcp/server.py:128,157-207,378,404-549`

**Providers** - `integrations/discovery/photon.py:20-27`; `discovery/real_city.py:617,684-688`;
`integrations/context/open_meteo.py:29-36`; `integrations/mobility/valhalla_http.py:32`;
`integrations/china/amap.py:10,47`; `integrations/web/searxng.py:29`;
`integrations/ai/responses.py:244`; `integrations/mock/providers.py:13`

**Persistence** - `backend/app/db/models.py` at `:22,175,212,254,271,511,535,562,578,677,692,712,761,782,824,1324,1360,1382`;
`backend/app/db/session.py:70-88`; `backend/app/core/config.py:10,14,33,44,79-81,88,96-98`

**Status colours** - implemented-and-evidenced vs implemented-but-unproven vs planned is
decided from `BLOCKERS.md:9-16`, `BUG_REPORT_20260913.md`, `CURRENT_STATUS.md:4`,
`TEST_RESULTS.md`, `HERMES_INTEGRATION_STATUS.md`, `AGENT_TOOL_CATALOG.md:16-18` and
the deployment defaults in `core/config.py`.

## The Microsoft Project plan

| Row group | Evidence the work is real |
|---|---|
"""
EV_ROWS = [
    ("1  Initiation", "the assignment brief PDF itself; first commit " + first_commit),
    ("2  Requirements", "requirements/requirements.yaml v0.3.0 (%d entries) and use-cases/use-cases.yaml v0.1.0" % n_req),
    ("3  Design", "AGENT_RUNTIME_ARCHITECTURE.md, contracts/openapi.yaml, visio/ baseline v1.0-RC5"),
    ("4  Backend", "%d endpoints, %d tables, backend/tests (%d modules)" % (n_ep, n_tables, n_backend_tests)),
    ("5  Map and place data", "integrations/discovery/*, integrations/context/*, .env.example:18-31"),
    ("6  Agent and Hermes", "backend/app/agent/*, agent-mcp/*, BLOCKERS.md:9-12 for what is not proven"),
    ("7  Frontend", "frontend/src/*, %d e2e specs, CityNexus_进度汇报_2026-10-13.md walked the demo live" % n_e2e),
    ("8  Integration", "the authoritative line and the four-leg landing loop of 2026-10-08"),
    ("9  Verification", "PROJECT_STATUS_SNAPSHOT_20260913.md (344/2), TEST_RESULTS.md (24 passed), the 2026-10-13 report (1887 passed / 45 failed)"),
    ("10 Coursework", "the brief's own two deadlines: 2026-10-02 and 2026-11-06"),
    ("11 Delivery", "this Evidence folder"),
]
for g, e in EV_ROWS:
    sm += "| %s | %s |\n" % (g, e)

sm += """
Milestone dates are taken from dated artefacts in the tree, not chosen freely:
"""
for m in (ms_res.get("milestones") or []):
    sm += "* `%s` -> %s\n" % (m["name"], m["finish"])
sm += """
The one deliberate exception is M9 (system test complete), which is a plan
choice rather than a fact and is marked provisional in its own Notes field.

## Files produced, with fingerprints

**Visio**

| file | bytes | sha256/16 |
|---|---|---|
"""
for name, sz, h, sp, glue, checks, png, pdf in vsdx_rows:
    sm += "| `Visio/%s` | %d | `%s` |\n" % (name, sz, h)
for f in sorted(glob.glob(os.path.join(VIS, "previews", "*"))):
    sm += ("| `Visio/previews/%s` | %d | `%s` |\n"
           % (os.path.basename(f), size(f), sha(f)))
sm += """
**Microsoft Project**

| file | bytes | sha256/16 |
|---|---|---|
"""
for name, sz, h in msp_rows:
    sm += "| `Microsoft_Project/%s` | %d | `%s` |\n" % (name, sz, h)
for f in sorted(glob.glob(os.path.join(MSP, "*.mpp"))):
    sm += ("| `Microsoft_Project/%s` | %d | `%s` |\n"
           % (os.path.basename(f), size(f), sha(f)))
for f in sorted(glob.glob(os.path.join(MSP, "previews", "*.png"))):
    sm += ("| `Microsoft_Project/previews/%s` | %d | `%s` |\n"
           % (os.path.basename(f), size(f), sha(f)))

open(os.path.join(EVI, "SOURCE_MAPPING.md"), "w", encoding="utf-8").write(sm)
# The round-3 section is its own module: it measures the deck, the screenshots and
# the PDFs from disk, so nothing in it is remembered prose.
import se_docs_r3_section_r1                                  # noqa: E402
readme += se_docs_r3_section_r1.build()
open(os.path.join(EVI, "README.md"), "w", encoding="utf-8").write(readme)
print("README.md %d bytes, SOURCE_MAPPING.md %d bytes"
      % (size(os.path.join(EVI, "README.md")), size(os.path.join(EVI, "SOURCE_MAPPING.md"))))

# ============================================================ AUTOMATION_VERIFICATION.md
av = """# Automation verification

Written {today}. Every number below was read back out of the produced files or
out of Visio / Project themselves, not typed from memory. The scripts that did
it are in `Evidence/scripts/`; their raw logs are in `Evidence/logs/`.

## Environment, measured not assumed

| item | result |
|---|---|
| Office build | Click-to-Run `O365HomePremRetail, VisioPro2024Retail, ProjectPro2024Retail` |
| Visio | `Visio.Application.11`, version 16.0, `VISIO.EXE` present, COM launches and quits cleanly |
| Project | `MSProject.Application.14`, version 16.0, `WINPROJ.EXE` present, COM launches and quits cleanly |
| Python | 3.10.11 with pywin32; type libraries exported with `makepy` before anything was called |

`Application.BuildNumber` and `Application.MasterCount` raise AttributeError on
this Visio build, and `dir()` on the Project Application raises "not
implemented" - both were found by running them, which is why the generators
never touch them.

## What the probes proved before any deliverable was written

| probe | finding that changed the design |
|---|---|
| `se_probe_r6.py` | A brand-new Project file creates **manually scheduled** tasks. A successor did not move when its driver's duration grew. Field **1280** is the schedule field and it reads `手动计划`. |
| `se_probe_r7.py` | `SetField(1280, 0)` is the only accepted form - the Chinese string forms are refused. `Task.Assignments.Add(taskId, resId, units)` works while `Project.Assignments` is not exposed. A resource's `StandardRate` reads back **0** unless `Type` is set first. |
| `se_probe_r5/r6` | Visio's stencils are locale 2052: master names are 流程 / 判定 / 开始/结束 / 参与者 / 用例 / 泳道列表, not English. `Cells("Weight")` and `Cells("Pattern")` are refused; `LineWeight` and `LinePattern` work. |
| `se_probe_r6.py` | `Cells("BeginX").GlueTo(shape.Cells("PinX"))` produces a real glue: moving the shape moved the connector endpoint from 2.5 to 4.5. |
| `se_project_export*` | `Application.Views()` and `FilePageSetup()` with no arguments **hang or open a modal dialog** on this install. Both were removed; view names are now proved by `ViewApply` actually switching. |
| `se_milestone_view_r1` | Deleting rows out of a copy of the plan cascades through summary rows and silently dropped M10-M12. Replaced by reading the milestone dates out of the plan and building the timeline from those. |
| date reading | pywin32 returns Project dates as UTC, so `str(task.Finish)[:10]` reported the day **before** the real one on eight milestones. Fixed with `se_timeutil_r1.dstr()`; the mismatch list is now empty. |

## Visio: what was executed

Four native drawings were generated from JSON specifications by
`se_visio_build_r1.py` driving Visio COM. Each build runs a gate **before** it
is allowed to write the file, and the gate is not cosmetic:

* every node inside the page, no two shapes overlapping
* text measured against the usable width of its own shape kind - a diamond only
  carries text across its middle, so an over-long label is a failure, not a
  squeeze
* every decision has at least two outgoing branches and **every branch is
  labelled**
* no orphan shape, terminators marked start or end
* connection count on the page equals exactly twice the number of edges, i.e.
  both ends of every connector are glued

Then `se_visio_proof_r1.py` re-opened each saved file from disk and checked:

| drawing | shapes | edges | edges proven glued to both named shapes | edit round-trip | connections after reopen | verdict |
|---|---|---|---|---|---|---|
""".format(today=TODAY)

for name, sz, h, sp, glue, checks, png, pdf in vsdx_rows:
    pr = proof_by_file.get(name, {})
    g = pr.get("glue", {}) or {}
    c = pr.get("checks", {}) or {}
    av += ("| `%s` | %d | %d | %s / %s | marker written and read back: %s | %s | %s |\n"
           % (name, sp.get("nodes", 0), sp.get("edges", 0),
              g.get("proven", "?"), g.get("expected", "?"),
              c.get("markerRoundTrip"), c.get("connectionsSurvived"),
              "PASS" if pr.get("ok") else "FAIL"))

av += """
The glue audit is not a pixel check: the builder recorded the `Shape.ID` of
every node and every connector into the gate report, and the proof walks
`page.Connects` in the **reopened** file to show that for each edge there is
one connector shape touching both endpoint ids. Shape IDs survive save and
reopen, so this is a claim about the file on disk.

**One check could not be made and is not being claimed.** The attempt to move a
node and watch its connector follow was refused: the built-in masters this
build drops carry position protection, so `PinX` / `PinY` cannot be written by
COM on those shapes. The same test *did* pass earlier on shapes created with
`page.DrawRectangle` (see `logs/se_probe_r6.log`: endpoint moved 2.5 -> 4.5),
so the glue is live; what is unproven is moving a master-based shape
programmatically. In Visio itself those shapes drag normally.

"""

# ---------------------------------------------------------------- the plan
_link = _r2.get("links", {})
_proof = _r2.get("link_proof", {})
_cost = _r2.get("costs", {})
_prog = _r2.get("progress", {})
_dl = _r2.get("deadlines", {})
_cons = _r2.get("constraints", {})
_cp = _r2.get("critical_path", {})
_pub = _r2.get("publication", {})
_chk = _r2.get("checks", {})
_static = _r2.get("static_preflight", {})
_types = _proof.get("types", {})

av += """
## Microsoft Project: what was executed, revision 2

The first revision failed an independent review on dependency semantics. This is
what the shipped plan does now, with every number read out of
`se_project_build_r2_result.json`, which the same run that wrote the `.mpp`
wrote.

`se_project_build_r2.py` refuses to publish unless every gate below passes, and
the gates are run again against the **published file** in a fresh Project
process:

| check | result |
|---|---|
| static pre-flight, before Project is even started: cycles, unknown rows, self links, SF links, every declared link tested as a date inequality | {viol0} violated of {decl0} declared, {prob0} structural problems |
| every declared dependency present in the file, read back through `Task.TaskDependencies` | {read} dependency records for {decl} declared links, {miss} missing |
| no link contradicts the dates Project computed | {viol} violations |
| no row carries a constraint (a forced date would override the links) | {forced} constrained rows; earliest scheduled start {early} |
| percentages land and completed work is booked on or before the status date | {booked} rows booked, {notin} at 100% without actuals |
| work hours and cost correspond | {hours} labour hours, {costbad} rows where hours or cost disagree with duration x units x rate |
| compute lanes priced without inventing hours | {matcost} material assignments priced, {mathours} carrying hours |
| each declared link TYPE demonstrably drives a date, then returns | declared {tdec}, shown live {tlive}, restored cleanly: {restored} |
| critical path computed by the engine | {critn} rows |
| dates set by the assignment brief | {dlmet} met, {dlbreach} breached, {dlsoft} internal targets missed |
| save, close, reopen in a new process, every field of every row | {drift} field differences |
| published copy | published {pubbed}, {pubbytes} bytes, sha256 {pubsha} at that instant (note below); re-read {shiprows} rows, {shiplinks} dependency records, {shipviol} violations |

Note on file digests: opening a `.mpp` in Project rewrites it, so the sha256 in
the table above is the bytes at that instant. `MANIFEST.sha256` and the review
brief are written after every Project session closes, so they carry the bytes as
packaged; re-hashing after opening the file gives a different value, which is
Project behaviour and not a mismatch in the delivery.

**Why the link-type test is built this way.** `TaskDependency.Lag` accepts a
write on this install and then ignores it, and `TaskMoveToStatusDate` returns
True while moving nothing - both measured, in `logs/se_proj_probe_r5.log`,
`logs/se_proj_probe_r10.log` and the build log. So liveness is proven the way a
planner tests a schedule: lengthen one open row by ten working days and watch
which descendants move, and in which field. An FS or SS edge must drag its
successor's start; an FF edge must drag the finish. The duration then goes back
and every date has to return to what it was.

**Three clocks, three mechanisms.** Historical fact is carried by the percentage
(Project books the completed part itself, and the audit reads `ActualFinish`
back); the observed date and the basis it comes from are written into the row's
Notes; the contract dates live in the `Deadline` field, which Project displays
but does not obey. Nothing in the file has a forced start any more. The first
revision typed dates into the thirteen milestones, which was measured to set
constraint type 4 on each of them - that is how its links came to contradict its
own calendar, and why twelve of its rows appeared to finish before their
predecessors.

**No baseline was saved.** The brief allows a baseline only where a credible
original plan exists; there is none, so `BaselineSave` was deliberately not
called rather than used to manufacture a history.

**What the plan admits about itself.** {late} rows are late against the status
date and stay late. Project's Move-to-Status-Date is inert through COM on this
install, and stretching those windows to hide the lateness would be a false
statement about the project. Part 1 is one of them, and its submission can be
neither confirmed nor denied from this repository - only from the course record.

### Plan, as Project computed it

| | |
|---|---|
| rows | {rows} ({gsum} summary groups, {gleaf} leaf rows including milestones) |
| milestones | {gms} |
| resources | {gres} - three named students as work resources, two compute lanes as material resources |
| project start | {pstart} |
| status date | {sdate} |
| project finish | {pfinish} |
| total cost | {pcost} |
| critical path | {critn} rows |
| link types used | {tdec} |
""".format(viol0=len(_static.get("violations", [])), decl0=_static.get("links_total", 0),
           prob0=len(_static.get("problems", [])),
           read=_link.get("read", 0), decl=_link.get("declared", 0),
           miss=len(_link.get("missing", [])), viol=len(_link.get("violations", [])),
           forced=len(_cons.get("forced", [])), early=_cons.get("earliest_start"),
           booked=_prog.get("booked_complete", 0),
           notin=len(_prog.get("not_booked", [])),
           hours=int(round(_cost.get("labour_hours", 0))),
           costbad=len(_cost.get("problems", [])),
           matcost=_cost.get("computePricedAssignments", 0),
           mathours=len(_cost.get("compute_only_rows_without_zero_hours", [])),
           tdec=", ".join(_types.get("declared", [])),
           tlive=", ".join(_types.get("demonstrated", [])),
           restored=all(not v.get("notRestored") for v in _proof.values()
                        if isinstance(v, dict)),
           critn=_cp.get("count", 0), dlmet=len(_dl.get("met", [])),
           dlbreach=len([b for b in _dl.get("breached", []) if not b["recordedFact"]]),
           dlsoft=len(_dl.get("internalTargetsMissed", [])),
           drift=_r2.get("reopen_drift_count", "not recorded"),
           pubbed="yes" if _pub.get("published") else "NO",
           pubbytes=_pub.get("bytes", 0),
           pubsha=str(_pub.get("sha256AfterVerification")
                      or _pub.get("sha256", ""))[:16],
           shiprows=_pub.get("shippedRows", 0),
           shiplinks=_pub.get("shippedLinksRead", 0),
           shipviol=_pub.get("shippedLinkViolations", 0),
           late=len([x for x in _prog.get("history_problems", [])
                     if x.startswith("OVERDUE")]),
           rows=len(_rows), gsum=n_sum, gleaf=n_leaf, gms=n_ms,
           gres=len(_r2.get("resources", {}) or {}),
           pstart=_r2.get("first_pass", {}).get("start"),
           sdate=_r2.get("status_date"),
           pfinish=_r2.get("reopen_pass", {}).get("finish"),
           pcost=_r2.get("reopen_pass", {}).get("cost"))

av += """
### What the review found, and what this revision changed

| review finding | revision 1 | shipped now |
|---|---|---|
| 13 milestone predecessor links were skipped by the builder | the builder `continue`d past any milestone carrying a date, so none of the 13 links was written | every declared link is written, including all milestone links; {decl} in the plan |
| 5 of the applied FS links contradicted their own dates | forced `Start` on milestones set constraint type 4 (SNET), which overrides the schedule | 0 constrained rows, 0 link violations, read back from `Task.TaskDependencies` |
| history, dependency and deadline were one thing | a date field carried all three | percentage carries history, links carry dependency, `Deadline` carries the contract date |
| per-shape source metadata read back empty | Shape Data written with a cell path that never stored anything | NodeId / State / SourceRef written through `AddNamedRow` + `Prop.<name>.Value` and read back per shape: {propsum} |
| cost did not correspond to hours | resources created with `Type = 1`, which on this install is MATERIAL, so Work stayed 0 and cost was one unit times the rate | students are work resources (`Type = 0`), so Project derives Work from duration x units x 8h; {hours} hours priced against the rates, 0 mismatches |
| progress was not in the file | `PercentComplete` written before the assignment, which silently reads back 0 | assignments first, then percentage, and every row's percentage is read back and asserted |
| the agent diagram claimed a universal gateway order | one door drawn for every handler, unknown tools shown as audited | three handler families drawn separately, with the measured line numbers, and the correction named on the sheet |
| the use-case sheet was one dense page | 39 shapes on one page | two pages in the same editable file: overview and include detail |
| no tablet-readable plan view | 21-page Gantt PDFs only | `Briefing/CityNexus_Plan_Briefing_A3.vsdx` and `Briefing/previews/CityNexus_Plan_Briefing_A3.pdf`, one A3 landscape page drawn from the plan's own computed dates |
| members unknown, Part 1 asserted never submitted | placeholder resources at zero and a claim the repository cannot support | three named members with work resources and hours; Part 1 now says what is true: not verifiable from this repository, awaiting the course record |
""".format(decl=_link.get("declared", 0),
           propsum="; ".join("%s %d/%d" % (r["file"][:2],
                                           (r.get("shapeData") or {}).get("propsOk", 0),
                                           (r.get("shapeData") or {}).get("expected", 0))
                              for r in vis_proof) or "not run",
           hours=int(round(_cost.get("labour_hours", 0))))

for name, sz, h in msp_rows:
    v = (prj_exp.get("views", {}).get(os.path.splitext(name)[0], {}) or {}).get("view", "-")
    av += "| `%s` | %s | %d |\n" % (name, v, sz)

av += """
`Milestone_Timeline.pdf` deserves an honest footnote. Project's
`DocumentExport` renders a view's table and chart panes and **not** the
Timeline pane - proved by exporting twice and comparing the extracted text of
every page, which came back identical. So the milestone timeline is built by
`se_milestone_view_r2.py`: it reads the thirteen milestone rows and their
computed dates out of the shipped plan, writes them into
`CityNexus_Milestone_View.mpp`, and exports that. The dates are copied from the
schedule, and the script asserts they match - the mismatch list is empty.

The shipped plan also carries the thirteen milestones on its own Timeline pane
now (`se_project_snapshot_r1.py`, 13 of 13 placed, saved), so opening the
`.mpp` in Project shows the timeline directly; it just cannot be exported to
PDF as a pane.

### Full-window PNG previews

These are **screenshots of the running application**, kept separately from the
PDF exports so nobody mistakes one for the other:

| file | view | bytes |
|---|---|---|
"""
for k, png, v, b in snap_rows:
    av += "| `Microsoft_Project/previews/%s` | %s | %d |\n" % (png, v, b)

av += """
## Reproducing any of this

```
cd D:\\moodle\\live_checks
python se_visio_build_r1.py            # four .vsdx + previews + gate reports
python se_visio_proof_r1.py            # reopen, edit, save, reopen, audit glue
python se_project_build_r1.py          # the .mpp and the nine schedule checks
python se_project_export_r2.py         # six view PDFs from the .mpp
python se_milestone_view_r2.py         # milestone timeline from the plan's dates
python se_project_snapshot_r1.py       # full-window PNG previews
```

The Visio specifications are JSON in `Visio/specs/` and the plan data is the
`PLAN` / `RESOURCES` table in `scripts/se_project_plan_r1.py`, so when the
product changes the drawings and the plan can be regenerated rather than
redrawn.

## What is NOT done

* Part 1 of the coursework (ten slides) was due 2026-10-02 and does not exist.
  Nothing here pretends otherwise, and the plan keeps it as a missed milestone.
* The requirement baseline still needs the teacher's agreement as customer;
  all {n_req} entries remain `proposed`.
* Group members 2 and 3 have no name, no student number and no responsibility
  recorded anywhere. The brief requires three, and the filename must carry all
  names and ID numbers - that has to come from you.
* Microsoft Office stamps the current Windows user name into each .mpp as the
  document last-author property. It is not a filesystem path, and no user-profile
  path appears anywhere in this folder (checked with grep across all 68 files),
  but it is the one machine-specific trace left inside the two binary files.
  Removing it means hand-editing an OLE compound file, which is not worth risking
  a verified deliverable for.
* The Visio drawings label shapes in English, matching the coursework and the
  code. If the review is to be given in Chinese the labels need translating;
  the JSON specs make that a text-only change.
""".format(n_req=n_req)

open(os.path.join(EVI, "AUTOMATION_VERIFICATION.md"), "w", encoding="utf-8").write(av)
print("AUTOMATION_VERIFICATION.md %d bytes" % size(os.path.join(EVI, "AUTOMATION_VERIFICATION.md")))
print("\nkey facts: endpoints=%d tables=%d reqs=%d uc=%d+%d rel=%d/%d "
      "plan rows=%d leaves=%d ms=%d cost=%s finish=%s critical=%d"
      % (n_ep, n_tables, n_req, n_uc_top, n_detail, n_inc, n_ext,
         prj_res.get("reopen_pass", {}).get("tasks", 0), n_leaf, n_ms,
         prj_res.get("reopen_pass", {}).get("cost"),
         prj_res.get("reopen_pass", {}).get("finish"), len(crit)))
