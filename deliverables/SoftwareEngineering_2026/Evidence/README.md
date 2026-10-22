# CityNexus - Software Engineering 2026 coursework pack

Generated 2026-10-23 on the machine that also runs the product, by Microsoft Visio
Professional 2024 and Microsoft Project 2024 driven through their own COM
automation. Nothing in here is a screenshot pretending to be a source file:
the four `.vsdx` and the `.mpp` are the native documents and they open,
edit and re-save in the real applications.

Source tree: CityNexus, branch `review/se-coursework-deliverables-r1` at `db001c28ca 2026-10-23 docs(coursework): Qoder continuous execution to 23 Oct noon with hard demo freeze`
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

## What changed in round 3 (2026-10-23)

The external review of round 2 (`Evidence/INDEPENDENT_R2_REVIEW_20261022.md`)
accepted the Visio property fix, the agent-flow correction and the dependency
fix, and asked for three product-level things instead, plus two evidence-
integrity items. This round is those five; the accepted work was not redone.

| the complaint | what is in the pack now | where to read it |
|---|---|---|
| 1808 student hours against about 840 available | each task carries its own effort split by person, and the build refuses to publish if any person-week exceeds declared availability: **220.9 student hours, peak week 19.9 h against 20 h, 0 over-allocated person-weeks** | `Evidence/STATUS_AND_OVERDUE.md`, sheet 4 of the deck |
| only 4 late rows were admitted | the table is generated from the shipped file and lists **all 14** rows past their planned finish with the original span, the booked percentage and the re-forecast date | `Evidence/STATUS_AND_OVERDUE.md` |
| the A3 one-pager is 5.8 pt and the screenshots showed Chrome | a 16:9 briefing deck with a 13 pt floor enforced by the drawing gate, and screenshots taken with Win32 `PrintWindow`, which cannot photograph the window that happens to be on top | `Presentation/`, `Microsoft_Project/previews/` |
| three finish dates quoted as one truth | every date is labelled with the clock that produced it and the two schedulers are compared row by row | `Evidence/PLAN_RECONCILIATION.md` |
| documents pointed at files that were not in the package | the packaging step checks every relative path a document cites, and the report says which ones were broken | `Evidence/R3_RESULT.md` |

### The date reader was wrong, and it changed the answer

Comparing the two schedulers exposed this: `se_timeutil_r1.dstr()` shifted every end-of-working-day value into the next calendar day. pywin32 hands Project's `2026-09-09 17:00` back tagged with a timezone that is not this machine's, and converting it to local time added eight hours. The grid shows 9月9日; every document written from that JSON said 09-10.

It is fixed, the reader now carries a self-test that the build refuses to run without, and the consequences are reported rather than hidden: the lateness count moved from the 10 the review took from my own table to **14**, and one person-week that the shifted dates had been hiding became visible - two September estimates were re-sized to clear it, which is why the student total reads 220.9 h.

### Presentation deck, measured

`Presentation/CityNexus_SE2026_Briefing_Deck.vsdx`: four 13.333 x 7.5 in sheets, 56 shapes, 4 connectors, gate failures 0. Body text has a 13 pt floor and the gate refuses a sheet that breaks it; the layout pass calls the engine's own word wrap, so a box the layout says fits really fits.

| deck preview | bytes |
|---|---|
| `Presentation/previews/CityNexus_SE2026_Briefing_Deck.png` | 77299 |
| `Presentation/previews/CityNexus_SE2026_Briefing_Deck_p1.png` | 77299 |
| `Presentation/previews/CityNexus_SE2026_Briefing_Deck_p2.png` | 56471 |
| `Presentation/previews/CityNexus_SE2026_Briefing_Deck_p3.png` | 105235 |
| `Presentation/previews/CityNexus_SE2026_Briefing_Deck_p4.png` | 81069 |

### Project screenshots, and how they were taken

Method PrintWindow(PW_RENDERFULLCONTENT). The plan was opened **read-only at the filesystem level**, because a plain open makes Project rewrite the container on close even when nothing was edited: digest before `6398e58f9b4cd3b3`, after `6398e58f9b4cd3b3`. No Office lock file was left (none). Each frame is tested for not being blank - colour count and non-white pixel fraction - before it is kept.

| view | file | pixels | ink fraction | windows overlapping it |
|---|---|---|---|---|
| 日历 | `Calendar.png` | 3414x2350 | 0.4043 | 11 |
| 甘特图 | `Gantt_Chart.png` | 3414x2350 | 0.1347 | 11 |
| 甘特图 | `Milestone_Timeline.png` | 3414x2350 | 0.13 | 0 |
| 网络图 | `Network_Diagram.png` | 3414x2350 | 0.1558 | 11 |
| 资源工作表 | `Resource_Sheet.png` | 3414x2350 | 0.132 | 11 |
| 跟踪甘特图 | `Tracking_Gantt.png` | 3414x2350 | 0.1676 | 11 |
| 任务工作表 | `WBS_Task_Sheet.png` | 3414x2350 | 0.1626 | 11 |

The last column is the honest part: other windows really are on top of Project on this desktop while the capture runs, which is exactly why the screen-rectangle grab of round 2 was wrong. `PrintWindow` renders the target window into its own device context, so the image is Project's pixels regardless of z-order, and each file was also looked at by eye.

### Printed PDFs, with their real page counts

The round-2 print named Briefing_One_Page.pdf is gone from the tree - it was twelve pages. The same print ships as `Microsoft_Project/Plan_Briefing_Print.pdf` and the count is stated here instead of promised by a filename.

| file | pages | bytes |
|---|---|---|
| `Briefing/previews/CityNexus_Plan_Briefing_A3.pdf` | 1 | 45713 |
| `Microsoft_Project/Detailed_Gantt.pdf` | 12 | 454510 |
| `Microsoft_Project/Gantt_Chart.pdf` | 24 | 842537 |
| `Microsoft_Project/Milestone_Timeline.pdf` | 12 | 441384 |
| `Microsoft_Project/Network_Diagram.pdf` | 41 | 171583 |
| `Microsoft_Project/Plan_Briefing_Print.pdf` | 12 | 450847 |
| `Microsoft_Project/Resource_Sheet.pdf` | 3 | 147059 |
| `Microsoft_Project/Tracking_Gantt.pdf` | 15 | 601735 |
| `Microsoft_Project/WBS_View.pdf` | 6 | 196387 |
| `Presentation/previews/CityNexus_SE2026_Briefing_Deck.pdf` | 4 | 49448 |

### New files this round

* `Evidence/STATUS_AND_OVERDUE.md` - four date clocks, the full lateness table, the per-person per-week capacity table.
* `Evidence/PLAN_RECONCILIATION.md` - static pass against the engine, row by row, with the offset accounted for.
* `Evidence/R3_RESULT.md` - what was fixed and what is still not proven.
* `Evidence/CLASSROOM_20261023_README.md` - the noon demonstration sheet: what to open in which order, the recorded open/move/edit/save/reopen results from `se_classroom_demo_r1.py`, and the fallback previews if Office will not start.
* `Microsoft_Project/CityNexus_Plan_Recovery.mpp` - open work only, scheduled from the status date; finishes 2026-11-04 against the 2026-11-06 contract date.
* `Presentation/CityNexus_SE2026_Briefing_Deck.vsdx` and its previews.
* Generators: `se_plan_status_r1.py`, `se_project_recovery_r1.py`, `se_deck_r1.py`, `se_project_snapshot_r2.py`, `se_evidence_reconcile_r1.py`, `se_docs_r3_section_r1.py`.
