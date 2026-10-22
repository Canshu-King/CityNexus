# Automation verification

Written 2026-10-22. Every number below was read back out of the produced files or
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
| `01_CityNexus_System_Architecture.vsdx` | 23 | 24 | 24 / 24 | marker written and read back: True | True | PASS |
| `02_CityNexus_User_Journey.vsdx` | 28 | 34 | 34 / 34 | marker written and read back: True | True | PASS |
| `03_CityNexus_Agent_Workflow.vsdx` | 29 | 35 | 35 / 35 | marker written and read back: True | True | PASS |
| `04_CityNexus_Use_Case.vsdx` | 36 | 47 | 47 / 47 | marker written and read back: True | True | PASS |

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

## Microsoft Project: what was executed

`se_project_build_r1.py` created the plan, and refuses to call itself finished
without these nine checks, run again after a full close and reopen in a **new
process**:

| check | result |
|---|---|
| no circular dependency (topological sort of the spec, before Project starts) | pass |
| leaf task count inside the 20-45 range the brief asks for | 52 leaves |
| milestone count at least 7 categories | 13 milestones |
| every task auto scheduled (field 1280 read back) | pass - nothing left manual |
| changing one duration moves its successor | True |
| the schedule returns to its original dates afterwards | True |
| critical path computed by Project, not asserted | 28 rows |
| resources carry rates and an assignment produces cost | total cost 1278.3 |
| save, close, reopen in a fresh process: rows, leaves, assignments, cost, finish | {"sameRowCount": true, "sameLeafCount": true, "sameAssignmentCount": true, "sameCost": true, "sameFinish": true, "criticalComputed": true, "nothingLeftManual": true, "recalcMovesSchedule": true, "recalcRestoredCleanly": true} |

The recalculation test is the one that matters for "is this a real schedule".
It took `1.2  Select the project: smart city traveler system`, grew its
duration, and watched `1.3  Confirm the group of three` move; then restored it
and confirmed the dates came back. A Gantt drawn by hand cannot pass that.

**No baseline was saved.** The brief allows a baseline only where a credible
original plan exists; there is none, so `BaselineSave` was deliberately not
called rather than used to manufacture a history.

Percent-complete values were entered only where the tree carries evidence.
Two rows sit at zero percent because the work was genuinely not done: the group of three
was never recorded anywhere, and Part 1 was never submitted.

### Plan, as Project computed it

| | |
|---|---|
| rows | 63 (11 summary groups, 52 leaf rows including milestones) |
| milestones | 13 |
| resources | 5, with standard rates and one assignment each where the work is real |
| project start | 2026-09-04 |
| project finish | 2026-11-06 |
| total cost | 1278.3 |
| critical path | 28 rows |
| rows with no predecessor | ['1.1  Read the assignment brief and fix t'] |

### Views exported from the shipped .mpp

| PDF | Project view | bytes |
|---|---|---|
| `Detailed_Gantt.pdf` | 详细甘特图 | 468403 |
| `Gantt_Chart.pdf` | 甘特图 | 775484 |
| `Milestone_Timeline.pdf` | - | 385816 |
| `Network_Diagram.pdf` | 网络图 | 150871 |
| `Resource_Sheet.pdf` | 资源工作表 | 126924 |
| `Tracking_Gantt.pdf` | 跟踪甘特图 | 543591 |
| `WBS_View.pdf` | 任务工作表 | 194261 |

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
| `Microsoft_Project/previews/Gantt_Chart.png` | 甘特图 | 159451 |
| `Microsoft_Project/previews/Tracking_Gantt.png` | 跟踪甘特图 | 247812 |
| `Microsoft_Project/previews/Network_Diagram.png` | 网络图 | 178837 |
| `Microsoft_Project/previews/WBS_Task_Sheet.png` | 任务工作表 | 237177 |
| `Microsoft_Project/previews/Resource_Sheet.png` | 资源工作表 | 127135 |
| `Microsoft_Project/previews/Calendar.png` | 日历 | 200761 |

## Reproducing any of this

```
cd D:\moodle\live_checks
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
  all 138 entries remain `proposed`.
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
