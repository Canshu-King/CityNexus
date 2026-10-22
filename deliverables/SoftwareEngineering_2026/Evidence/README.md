# CityNexus - Software Engineering 2026 coursework pack

Generated 2026-10-22 on the machine that also runs the product, by Microsoft Visio
Professional 2024 and Microsoft Project 2024 driven through their own COM
automation. Nothing in here is a screenshot pretending to be a source file:
the four `.vsdx` and the `.mpp` are the native documents and they open,
edit and re-save in the real applications.

Source tree: CityNexus, branch `review/se-coursework-deliverables-r1` at `21aa16e68a 2026-10-22 璇剧▼浜や粯淇�璁�浜屾敹灏句簩锛氳�″垝鏂囦欢鎸囩汗鍓嶅悗涓�鑷村寲`
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
| 9 | `Briefing/CityNexus_Plan_Briefing_A3.pdf` | The whole plan on one A3 landscape page for a tablet: eleven phase bars, thirteen milestones, the status date, and the figures Project computed. |
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
