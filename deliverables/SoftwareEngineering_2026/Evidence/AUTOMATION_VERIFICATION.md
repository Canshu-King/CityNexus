# Automation verification

Written 2026-10-23. Every number below was read back out of the produced files or
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
| `03_CityNexus_Agent_Workflow.vsdx` | 38 | 43 | 43 / 43 | marker written and read back: True | True | PASS |
| `04_CityNexus_Use_Case.vsdx` | 39 | 47 | 47 / 47 | marker written and read back: True | True | PASS |

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
| static pre-flight, before Project is even started: cycles, unknown rows, self links, SF links, every declared link tested as a date inequality | 0 violated of 61 declared, 0 structural problems |
| every declared dependency present in the file, read back through `Task.TaskDependencies` | 122 dependency records for 61 declared links, 0 missing |
| no link contradicts the dates Project computed | 0 violations |
| no row carries a constraint (a forced date would override the links) | 0 constrained rows; earliest scheduled start 2026-09-07 |
| percentages land and completed work is booked on or before the status date | 24 rows booked, 0 at 100% without actuals |
| work hours and cost correspond | 221 labour hours, 0 rows where hours or cost disagree with duration x units x rate |
| compute lanes priced without inventing hours | 7 material assignments priced, 0 carrying hours |
| each declared link TYPE demonstrably drives a date, then returns | declared FF, FS, SS, shown live FF, FS, SS, restored cleanly: True |
| critical path computed by the engine | 4 rows |
| dates set by the assignment brief | 6 met, 0 breached, 0 internal targets missed |
| save, close, reopen in a new process, every field of every row | 0 field differences |
| published copy | published yes, 386048 bytes, sha256 6398e58f9b4cd3b3 at that instant (note below); re-read 65 rows, 122 dependency records, 0 violations |

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

**What the plan admits about itself.** 6 rows are late against the status
date and stay late. Project's Move-to-Status-Date is inert through COM on this
install, and stretching those windows to hide the lateness would be a false
statement about the project. Part 1 is one of them, and its submission can be
neither confirmed nor denied from this repository - only from the course record.

### Plan, as Project computed it

| | |
|---|---|
| rows | 65 (11 summary groups, 54 leaf rows including milestones) |
| milestones | 13 |
| resources | 5 - three named students as work resources, two compute lanes as material resources |
| project start | 2026-09-07 |
| status date | 2026-10-22 |
| project finish | 2026-10-23 |
| total cost | 4460.688 |
| critical path | 4 rows |
| link types used | FF, FS, SS |

### What the review found, and what this revision changed

| review finding | revision 1 | shipped now |
|---|---|---|
| 13 milestone predecessor links were skipped by the builder | the builder `continue`d past any milestone carrying a date, so none of the 13 links was written | every declared link is written, including all milestone links; 61 in the plan |
| 5 of the applied FS links contradicted their own dates | forced `Start` on milestones set constraint type 4 (SNET), which overrides the schedule | 0 constrained rows, 0 link violations, read back from `Task.TaskDependencies` |
| history, dependency and deadline were one thing | a date field carried all three | percentage carries history, links carry dependency, `Deadline` carries the contract date |
| per-shape source metadata read back empty | Shape Data written with a cell path that never stored anything | NodeId / State / SourceRef written through `AddNamedRow` + `Prop.<name>.Value` and read back per shape: 01 93/93; 02 118/118; 03 157/157; 04 211/211 |
| cost did not correspond to hours | resources created with `Type = 1`, which on this install is MATERIAL, so Work stayed 0 and cost was one unit times the rate | students are work resources (`Type = 0`), so Project derives Work from duration x units x 8h; 221 hours priced against the rates, 0 mismatches |
| progress was not in the file | `PercentComplete` written before the assignment, which silently reads back 0 | assignments first, then percentage, and every row's percentage is read back and asserted |
| the agent diagram claimed a universal gateway order | one door drawn for every handler, unknown tools shown as audited | three handler families drawn separately, with the measured line numbers, and the correction named on the sheet |
| the use-case sheet was one dense page | 39 shapes on one page | two pages in the same editable file: overview and include detail |
| no tablet-readable plan view | 21-page Gantt PDFs only | `Briefing/CityNexus_Plan_Briefing_A3.vsdx` and `Briefing/previews/CityNexus_Plan_Briefing_A3.pdf`, one A3 landscape page drawn from the plan's own computed dates |
| members unknown, Part 1 asserted never submitted | placeholder resources at zero and a claim the repository cannot support | three named members with work resources and hours; Part 1 now says what is true: not verifiable from this repository, awaiting the course record |
| `Detailed_Gantt.pdf` | 详细甘特图 | 454510 |
| `Gantt_Chart.pdf` | 甘特图 | 842537 |
| `Milestone_Timeline.pdf` | - | 441384 |
| `Network_Diagram.pdf` | 网络图 | 171583 |
| `Plan_Briefing_Print.pdf` | - | 450847 |
| `Resource_Sheet.pdf` | 资源工作表 | 147059 |
| `Tracking_Gantt.pdf` | 跟踪甘特图 | 601735 |
| `WBS_View.pdf` | 任务工作表 | 196387 |

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
| `Microsoft_Project/previews/Gantt_Chart.png` | 甘特图 | 237847 |
| `Microsoft_Project/previews/Tracking_Gantt.png` | 跟踪甘特图 | 268064 |
| `Microsoft_Project/previews/Network_Diagram.png` | 网络图 | 198188 |
| `Microsoft_Project/previews/WBS_Task_Sheet.png` | 任务工作表 | 258762 |
| `Microsoft_Project/previews/Resource_Sheet.png` | 资源工作表 | 224045 |
| `Microsoft_Project/previews/Calendar.png` | 日历 | 305890 |

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
