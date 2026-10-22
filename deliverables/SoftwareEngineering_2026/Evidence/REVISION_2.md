# Revision 2 - answer to the independent review

Written 2026-10-22. The review it answers is `REVIEW_BRIEF.md` in this folder. Every number under **after** below is recomputed by this script from the files the revision-2 build produced, at the moment of writing; nothing is copied from a terminal scroll-back.

| shipped artefact | bytes | sha256/16 |
|---|---|---|
| `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` | 517120 | `4add419bd2f33ef1` |
| `Visio/01_CityNexus_System_Architecture.vsdx` | 62156 | `2869450c0f1d4e2d` |
| `Visio/02_CityNexus_User_Journey.vsdx` | 62749 | `d9c88139e7d82304` |
| `Visio/03_CityNexus_Agent_Workflow.vsdx` | 66526 | `3f7c57410bf6abfd` |
| `Visio/04_CityNexus_Use_Case.vsdx` | 84933 | `6d77427c4c085ca6` |
| `Briefing/previews/CityNexus_Plan_Briefing_A3.pdf` | 45713 | `3d2a8b1155b5dfc7` |

## 1. Microsoft Project scheduling

The review's finding, restated precisely: thirteen milestone predecessor links were skipped by the builder, and of the links that were written, several contradicted the dates in the same file.

Recomputed from the revision-1 result file that is still on disk:

| | revision 1 (recomputed here) | revision 2 (measured from the shipped file) |
|---|---|---|
| declared dependencies in the spec | 51 | 61 |
| of those, on milestone rows | 13 pinned milestones carried links that the builder skipped | 20 milestone links, all written |
| dependency records read back out of Project | not read back at all | 122 records for 61 declared links |
| links whose dates contradict the link | 12 violating of 51 declared, 39 held (the review counted 5 among the 38 links that were actually written; the 13 links its builder skipped are counted here too) | 0 violating of 122 written |
| rows carrying a constraint | 13 (a forced `Start` measured to set type 4, Start No Earlier Than) | 0 |
| percentages that survived the write | 63 of 63 rows read back at 0% | 24 rows read back at the value entered |
| work hours behind the cost | 0 h: resources were created with `Type = 1`, which on this install is MATERIAL, so Work stayed 0 and cost was one unit times the rate | 1808 labour hours, 0 rows where hours or cost disagree with duration x units x rate |
| link types proven to drive dates | one duration poke, one FS pair | FF, FS, SS declared, FF, FS, SS shown live by propagation, all restored |
| reopen in a new process | rows and cost compared | 0 field differences across start, finish, percent-complete, work, cost, constraint, deadline, actuals, critical, WBS |
| critical path | reported as a count | 4 rows, computed by the engine |

### How the three clocks are separated now

* **Historical fact** - `PercentComplete` only where the tree carries evidence, written *after* the assignments (measured: written before them it silently reads back 0). Project books `ActualStart` / `ActualFinish` itself, and the audit reads them back and refuses any row booked complete after the status date.
* **Dependency** - the only thing that moves a date. Every row is auto scheduled with constraint type 0; `earliest scheduled start` is 2026-09-07 against a project start of 2026-09-07, so nothing was pulled back behind the repository's first commit.
* **Contract date** - the `Deadline` field, which Project displays and does not obey. 6 met, 0 breached on brief dates, 0 internal targets missed.

The static checker (`se_plan_cpm_r1.py`) runs before Project is started and refuses the build on a cycle, an unknown row, a self link, an SF link, or any declared link that its own forward pass cannot satisfy: 0 violations, 0 structural problems in the shipped plan.

### What was deliberately not done to go green

* No dependency was deleted and no observed date was moved to make a check pass. The revision-1 contradiction list above is reproduced here rather than hidden.
* No baseline was saved: there is no approved original plan to save, so `BaselineSave` is never called.
* Open work was not silently re-dated. `Application.TaskMoveToStatusDate` was measured to accept every argument form and move nothing (`logs/se_proj_probe_r10.log`), and `OptionsCalculation(SpreadPercentToStatusDate=True)` hangs the COM session behind a modal prompt, so it is never called. 4 rows are therefore late against the status date and stay late:

  * OVERDUE (left visible on purpose): 5.3  Mobility: Valhalla routing be 0%, planned finish 2026-09-22, status date 2026-10-22
  * OVERDUE (left visible on purpose): 9.4  Physical phone and PWA shadow 0%, planned finish 2026-10-07, status date 2026-10-22
  * OVERDUE (left visible on purpose): 9.6  Final regression re-run and d 0%, planned finish 2026-10-03, status date 2026-10-22
  * OVERDUE (left visible on purpose): 10.1  Part 1: ten-slide report wit 0%, planned finish 2026-09-30, status date 2026-10-22

One measured quirk, so a re-hash does not look like a defect: opening a `.mpp`
in Project rewrites the file even when nothing is saved, so a digest of it is only
true for the instant it was taken. The build records its own two - d51641bbdeade0aa at the
moment of publishing, ef005c12bec6ee94 after its verification open. The artefact table at the
top of this document, `MANIFEST.sha256` and `REVIEW_BRIEF.md` are all written
after every Project session has closed and after the view exports have run, so
they agree with each other and with the bytes inside the package (4add419bd2f33ef1). If you
open the plan in Project and re-hash it, you will get a fourth value; that is
Project's behaviour, not a discrepancy - the package's own integrity is proved
by extracting it and re-hashing every member against the manifest, which is what
`se_review_package_r2.py` does before it reports success.

## 2. Visio per-shape source metadata

The review read every shape's custom properties back and found them empty. The cause was the write path, not the read path: `CellsSRC(243, ...)` with a row index that was never created. The engine now creates the row with `AddNamedRow`, writes `Prop.<name>.Value` as a quoted formula, and reads the cell back in the same call - a write that does not read back exactly is an error, not a note.

| drawing | shape-data values read back from the saved file | connectors proven glued at both ends | proof |
|---|---|---|---|
| `01_CityNexus_System_Architecture.vsdx` | 93 / 93 | 24 / 24 | pass |
| `02_CityNexus_User_Journey.vsdx` | 118 / 118 | 34 / 34 | pass |
| `03_CityNexus_Agent_Workflow.vsdx` | 157 / 157 | 43 / 43 | pass |
| `04_CityNexus_Use_Case.vsdx` | 211 / 211 | 47 / 47 | pass |
| **total** | **579 / 579** | **148 / 148** | **4 of 4 drawings** |

Before, as measured by the reviewer: 0 non-empty properties on every shape. The 140-connector glue check the review confirmed is unchanged in kind and larger in count now, because diagram 03 was redrawn with more edges and 04 became two pages.

Each value is asserted per shape, keyed by `(page, ShapeID)`, after a save, close and reopen in a new process; the proof then overwrites a shape's text, saves, reopens, reads the marker, restores, saves, reopens again and re-checks both the connection census and the shape data (`se_visio_proof_r2.py`).

## 3. Agent workflow semantics

The review was right that the first draft overstated the gateway. Measured in `backend/app/agent/gateway.py`: `dispatch` tests the allowlist at :358 and raises the 404 at :359, reaching `record_audit` only at :377 - so an unknown tool leaves **no** audit row. In `request_replan` the policy decision at :559 comes **before** the idempotency lookup at :576, and the two are not a single universal order across handlers: reads return `ALLOW_AUTO` with no policy call at all (:421, :437, :482, :497), the replan pair runs policy, idempotency, audit, effect, receipt (:559, :576, :626, :645 and :680, :695, :799, :824), and the typed actions raise their own domain guards (:1041-1053, :1178, :1238, :1286) with `request_commitment_change` auditing at :1363.

Diagram 03 is redrawn on those measured orders, in six lanes, and carries a note block that names what the earlier draft got wrong, so a reader can see that this is a correction rather than the original claim.

## 4. Presentation

* `Visio/04_CityNexus_Use_Case.vsdx` is now two pages in one editable file: an overview of the 13 business use cases with actors and external systems, and a second page holding the 14 `include` relationships under their three parents.
* `Briefing/CityNexus_Plan_Briefing_A3.vsdx` is a single A3 landscape page derived from the plan's own computed dates: eleven phase bars on a weekly axis, the status date and the two brief deadlines as reference lines, thirteen milestone markers with a table, and the figures Project produced. Microsoft Project's own pagination could not be driven through COM on this install (every form of `FilePageSetupPage` returns "parameter invalid", `logs/se_brief_r2.log`), so the briefing sheet is drawn by the same engine and the same layout gate as the design drawings, from the result file of the plan build. The schedule itself remains in the `.mpp`, and the sheet says so in its header along with the sha256 of the file it was derived from.
* The full-detail exports stay in place for the marker who wants the whole plan: `Gantt_Chart.pdf`, `Detailed_Gantt.pdf`, `Tracking_Gantt.pdf`, `Network_Diagram.pdf`, `WBS_View.pdf`, `Resource_Sheet.pdf`, `Task_Usage.pdf`, `Milestone_Timeline.pdf`.

The layout gate that guards these drawings grew three rules this round, each after looking at a rendered PNG: chrome (legend, note blocks, footnotes, parked connector labels) must sit inside the sheet, off the shapes and off each other; no shape may sit under a band's own title; and every citation line must fit the width its shape actually offers. The first run of the new rules reported 77 real defects across the four drawings - a note block printed over the legend, labels dumped at the page corner because the connector's endpoints were still 0,0, and citation text crossing shape borders.

## 5. People, cost and Part 1

The three members are named as the project owner stated them on 2026-10-22: Yang Jianbin 0802240329, Wang Jiarui 0802240322, Wang Xinyue 0802240324. Git carries one commit identity for the whole branch, because the automation lanes committed through the owner's account, so the **split of duties is the plan's proposal for the report and is labelled as such in each row's Notes** - it is not presented as measured history.

| resource | kind | rate | why |
|---|---|---|---|
| Yang Jianbin 0802240329 - requirements, architecture, inte | work | 20.0 | MEMBER 1 OF 3, named to this build on 2026-10-22 |
| Wang Jiarui 0802240322 - data integration, backend scopes, | work | 20.0 | MEMBER 2 OF 3, named to this build on 2026-10-22 |
| Wang Xinyue 0802240324 - frontend, agent surface, SRS writ | work | 20.0 | MEMBER 3 OF 3, named to this build on 2026-10-22 |
| Qoder agent lanes - automated build and test compute | material | 6.0 | EVIDENCED in git by the qoder-ai-lane, Qoder and lane-* author identities |
| Codex co-development - compute | material | 6.0 | EVIDENCED in git by the Codex and Codex Local Integration author identities |

Students are work resources, so Project derives Work from duration x units x 8h/day and Cost from Work x rate: the two cannot disagree, and the audit asserts it row by row (65 rows checked, 0 where they do not match).
The two compute lanes are material resources: they cost without accruing labour hours (7 priced assignments, 0 rows staffed only by lanes that carry hours).

Part 1: the plan no longer asserts it was never submitted. What is true is that **this repository cannot show either way** - the brief's date has passed, the row is at 0%, and the course record is the only place that settles it. The row and its milestone stay in the plan with that wording.

## 6. Still open, stated plainly

1. **Late work stays visible, not re-dated.** 4 rows are late against the status date because Project's move-to-status-date is inert through COM here. A planner with the UI would roll them forward; this build does not have that button, and inventing the effect of it would be a fabricated history.
2. **The 2026-10-02 Part 1 submission is unresolved.** It needs the course record, not the repository.
3. **Duty split for members 2 and 3 is a proposal.** No second or third git identity exists to verify it against.
4. **Rates are planning numbers.** No student timesheet exists, so hours are estimates derived from durations, and the money column is a coursework artefact.
5. **Milestone dates are not monotonic** (M8 lands before M4). The streams genuinely ran in parallel - git shows backend, frontend, contracts and the integration line changing on the same days from 2026-09-19 - so the numbering is WBS order, not calendar order. A reviewer who expects gates in date order should be told where to look.
6. **One Visio check is still not automated**: dragging a master-based shape and watching its connector follow cannot be done through COM on the built-in masters (position protection), so the glue proof reads the connection records instead of moving shapes.
7. **Project's own page setup cannot be scripted on this install**, which is why the one-page briefing is a derived drawing rather than a Project print setting; the `.mpp` still prints as many pages of detail.

## 7. How to reproduce

```
python se_plan_cpm_r1.py                 # static dependency check only
python se_project_build_r1.py            # revision 1, kept for the comparison
python se_project_build_r2.py            # builds, audits, publishes the .mpp
python se_visio_build_r1.py              # four drawings behind the layout gate
python se_visio_proof_r2.py              # glue + shape data read back from disk
python se_visio_plan_brief_r1.py         # the one-page briefing sheet
python se_evidence_docs_r1.py            # README / SOURCE_MAPPING / VERIFICATION
python se_evidence_revision_r1.py        # this file
```

Every script above fails with a non-zero exit code rather than reporting a result the file on disk does not show.
