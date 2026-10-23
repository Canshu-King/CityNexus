# CityNexus SE2026 - one plan, three clocks

Generated 2026-10-23 04:37 by `live_checks/se_evidence_reconcile_r1.py`. Source plan: `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp`, sha256 `6398e58f9b4c...`.

The R2 review found three different finish dates being quoted as if they were one fact. They are three different questions, and this page says which is which and why the two schedulers disagree.

## 1. The three clocks

| clock | question it answers | finish | produced by |
|---|---|---|---|
| static CPM (`Evidence/se_plan_cpm_r2.json`) | what the declared network of links implies, computed in pure Python with a Mon-Fri 8 h calendar and no resource limits | **2026-10-30** | `live_checks/se_plan_cpm_r1.py` |
| Project engine (the shipped `.mpp`) | what Microsoft Project's own scheduler produces for the same network once per-week resource availability, calendars and constraints are applied | **2026-10-23** | `live_checks/se_project_build_r2.py`, read back after reopen |
| recovery plan (`CityNexus_Plan_Recovery.mpp`) | what is still open from the status date 2026-10-22 onward, and when it can finish | **2026-11-04** | `live_checks/se_project_recovery_r1.py` |

Only the second is the plan of record. The first is a pre-flight gate that refuses a network with a cycle or a date-order violation; the third is the forward-looking proposal. No document in this delivery quotes the first or the third as the plan's finish date.

## 2. Where the two schedulers part company, row by row

Both were run against the same plan data on the same day. Comparing the static critical chain with the engine's own dates: **2 of 17 chain rows agree to the day; the first divergence is row M1.**

| WBS | row | static start..finish (working days) | Project start..finish (working days) | declared duration | effort (h) | why it differs |
|---|---|---|---|---|---|---|
| 1.1 | 1.1  Read the assignment brief and fix the d | 2026-09-07..2026-09-07 (1) | 2026-09-07..2026-09-07 (1) | 1d | 3 | same |
| 1.2 | 1.2  Select the project: smart city traveler | 2026-09-08..2026-09-08 (1) | 2026-09-08..2026-09-08 (1) | 1d | 2 | same |
| M1 | M1  Topic and scope agreed | 2026-09-09..2026-09-09 (1) | 2026-09-08..2026-09-08 (1) | 0 d (milestone) | 0 | milestone placement: the static pass puts a milestone the working day after its predecessor finishes, Project puts it on that finish day |
| 2.1 | 2.1  Research the software needed, library a | 2026-09-10..2026-09-15 (4) | 2026-09-09..2026-09-14 (4) | 4d | 4 | same declared duration, different start (the chain ahead of it differs by the milestone rule) |
| 2.2 | 2.2  Write the requirement baseline: 8 goals | 2026-09-10..2026-09-16 (5) | 2026-09-09..2026-09-15 (5) | 5d | 9 | same declared duration, different start (the chain ahead of it differs by the milestone rule) |
| M2 | M2  Requirements baseline drafted | 2026-09-17..2026-09-17 (1) | 2026-09-15..2026-09-15 (1) | 0 d (milestone) | 0 | milestone placement: the static pass puts a milestone the working day after its predecessor finishes, Project puts it on that finish day |
| 3.1 | 3.1  Layered architecture and agent runtime  | 2026-09-18..2026-09-24 (5) | 2026-09-16..2026-09-22 (5) | 5d | 6 | same declared duration, different start (the chain ahead of it differs by the milestone rule) |
| 4.1 | 4.1  FastAPI service and the /api/v1 surface | 2026-09-18..2026-10-01 (10) | 2026-09-16..2026-09-29 (10) | 10d | 3 | same declared duration, different start (the chain ahead of it differs by the milestone rule) |
| 7.1 | 7.1  V8Experience shell and the fifteen rout | 2026-09-18..2026-09-29 (8) | 2026-09-16..2026-09-25 (8) | 8d | 5 | same declared duration, different start (the chain ahead of it differs by the milestone rule) |
| 7.2 | 7.2  MapLibre map, plan comparison and Trip  | 2026-09-18..2026-09-25 (6) | 2026-09-16..2026-09-23 (6) | 6d | 5 | same declared duration, different start (the chain ahead of it differs by the milestone rule) |
| 7.3 | 7.3  Copilot dock, agent rail, check-ins and | 2026-09-28..2026-10-05 (6) | 2026-09-24..2026-10-01 (6) | 6d | 6 | same declared duration, different start (the chain ahead of it differs by the milestone rule) |
| M7 | M7  Frontend running against the real backen | 2026-10-06..2026-10-06 (1) | 2026-10-01..2026-10-01 (1) | 0 d (milestone) | 0 | milestone placement: the static pass puts a milestone the working day after its predecessor finishes, Project puts it on that finish day |
| 10.2 | 10.2  Mid-term review pack: architecture, jo | 2026-10-07..2026-10-21 (11) | 2026-10-02..2026-10-16 (11) | 11d | 13 | same declared duration, different start (the chain ahead of it differs by the milestone rule) |
| 10.3 | 10.3  Part 2: project plan with WBS, links,  | 2026-10-22..2026-10-27 (4) | 2026-10-19..2026-10-22 (4) | 4d | 6 | same declared duration, different start (the chain ahead of it differs by the milestone rule) |
| 10.4 | 10.4  Part 2: detailed requirement specifica | 2026-10-22..2026-10-28 (5) | 2026-10-19..2026-10-23 (5) | 5d | 11 | same declared duration, different start (the chain ahead of it differs by the milestone rule) |
| M12 | M12  Part 2 course deadline (contract 2026-1 | 2026-10-29..2026-10-29 (1) | 2026-10-23..2026-10-23 (1) | 0 d (milestone) | 0 | milestone placement: the static pass puts a milestone the working day after its predecessor finishes, Project puts it on that finish day |
| M13 | M13  Coursework delivery (plan) | 2026-10-30..2026-10-30 (1) | 2026-10-23..2026-10-23 (1) | 0 d (milestone) | 0 | milestone placement: the static pass puts a milestone the working day after its predecessor finishes, Project puts it on that finish day |

Read the two date columns together with the duration column: on **every** row the two schedulers span the same number of working days, which is the declared duration. A machine gate proves it (`se_evidence_reconcile_r1.py` refuses if any row's span differs from its declared duration in either scheduler), so the difference below is not one scheduler shortening the work.

What differs is where a row starts, and the offset is introduced in 7 named steps:

* at **M1** the gap moves by +1 day - zero-duration milestone (the two passes disagree on which side of the predecessor's finish it sits)
* at **M2** the gap moves by +1 day - zero-duration milestone (the two passes disagree on which side of the predecessor's finish it sits)
* at **7.3** the gap moves by +2 days - the gap widens at a task row, not a milestone, and the same caution applies: no cause is claimed here
* at **M7** the gap moves by +1 day - zero-duration milestone (the two passes disagree on which side of the predecessor's finish it sits)
* at **10.3** the gap moves by -2 days - Project places this task earlier than the network pass does. This page does not claim to know why from the numbers alone; settling it needs the engine's own scheduling log for the row
* at **M12** the gap moves by +3 days - zero-duration milestone (the two passes disagree on which side of the predecessor's finish it sits)
* at **M13** the gap moves by +1 day - zero-duration milestone (the two passes disagree on which side of the predecessor's finish it sits)

The milestone steps are a convention difference, not a contradiction: the static pass puts a zero-duration milestone on the working day **after** its predecessor finishes, Microsoft Project puts it **on** that finish day. The two counter-steps are where Project's resource-driven schedule pulls a row earlier than a pure network pass does, because it is fitting a person's declared weekly availability, which the static model does not see at all.

Net effect: the static chain ends **2026-10-30**, the shipped plan ends **2026-10-23**, a difference of 7 working days, and the recovery plan (open work only, from the status date) ends **2026-11-04**. The plan of record is the shipped file; the other two answer different questions and are never quoted as its finish date.

## 3. Capacity, computed twice

| person | static total h | Project total h | static peak week | Project peak week | weeks over, static | weeks over, Project |
|---|---|---|---|---|---|---|
| wangjr | 75.0 | 74.9 | 18.5 | 17.2 | 0 | 0 |
| wangxy | 68.0 | 68.0 | 19.5 | 19.6 | 0 | 0 |
| yang | 78.1 | 78.0 | 17.2 | 19.9 | 0 | 0 |

Both schedulers now report **zero** over-allocated person-weeks against the declared 20 h per week, and the two totals are the same hours counted two ways. The peaks differ because the two calendars place the same hours on different days; the gate that matters - no week over availability - passes on both sides.

## 4. Dependencies

| measure | value |
|---|---|
| links declared in the plan data | 61 |
| links the static checker parsed | 61 |
| dependency records read back from the engine (both ends) | 122 |
| links violating date order | 0 |

The read-back count is double the declared count because the engine is asked for each link from both ends (predecessor view and successor view); 61 + 61 = 122 is the same 61 links seen twice, not 122 links.

