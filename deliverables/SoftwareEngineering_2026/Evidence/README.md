# CityNexus - Software Engineering 2026 coursework pack

Generated 2026-10-22 on the machine that also runs the product, by Microsoft Visio
Professional 2024 and Microsoft Project 2024 driven through their own COM
automation. Nothing in here is a screenshot pretending to be a source file:
the four `.vsdx` and the `.mpp` are the native documents and they open,
edit and re-save in the real applications.

Source tree: `review/se-coursework-deliverables-r1` at `cca117cf1a 2026-10-08 鐜荤拑宸ラ�栨牸 路 娣诲姞鍥炲綊鑷� v2锛堣皟鍑芥暟瀹炵畻锛�`
Repository root: `D:\moodle\CityNexus`

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

Open the `.vsdx` files in Visio and the `.mpp` in Project; the PDFs and PNGs in
`previews/` are for slides and for anyone who does not have Office.

## Layout

```
Visio/                 4 native .vsdx drawings
  previews/            PNG + PDF of each, plus the per-drawing gate report
  specs/               the JSON that describes each drawing
Microsoft_Project/     the native .mpp, the milestone view, 6 view PDFs
  previews/            full-window PNG of each Project view
Evidence/              README, SOURCE_MAPPING, AUTOMATION_VERIFICATION,
                       result JSON, and every script that produced the above
```

## Honest limits, stated up front

* Part 1 of the coursework was due **2026-10-02** and was not submitted. That
  row sits in the plan at 0% rather than being back-dated.
* The brief requires a **group of three** with a named responsibility each. No
  second or third member exists anywhere in the repository, so two resources
  are placeholders at zero cost and the task that would resolve them is at 0%.
* Resource rates are **coursework planning estimates**, not payroll.
* No baseline was saved into the `.mpp`, because there is no original approved
  plan to save as one.
* The two documents that need a human - the customer-approved requirement
  statement and the ten-slide Part 1 - are not produced here and are not
  claimed as done.

See `AUTOMATION_VERIFICATION.md` for what was actually executed and
`SOURCE_MAPPING.md` for which file and line each shape came from.
