# Status, lateness and capacity - as the shipped plan actually reads

Generated 2026-10-23 04:37 from `se_project_build_r2_result.json`, which the build wrote while reading the published `.mpp`. Status date: 2026-10-22.

## 1. Four different dates, never mixed

| column | where it comes from | what it can prove |
|---|---|---|
| planned finish | Microsoft Project, from durations and links | what the schedule says |
| actual finish | Microsoft Project, booked from the percentage entered | that the completed part is in the past |
| forecast finish | arithmetic in `se_plan_status_r1.py` (remaining working days after the status date) | where the unfinished part can land; **not** a Project computation, because Move-to-Status-Date is inert through COM here |
| course deadline | the assignment brief | a date we do not control |

## 2. Every row that is past its planned finish and not complete

R2's documents named four. The real count is **14**. All of them are listed, with what is left and where the forecast puts them.

| WBS | row | progress | planned window | remaining | forecast finish | why that forecast |
|---|---|---|---|---|---|---|
| 5.2 | Context providers: Open-Meteo weather and time | 70% | 2026-09-16 → 2026-09-18 | 1 d / 0.9 h | 2026-10-23 | re-forecast: 1 of 3 working days remain at 70% and the first working day after the status date is 2026-10-23 |
| 5.3 | Mobility: Valhalla routing behind a live URL | 0% | 2026-09-16 → 2026-09-21 | 4 d / 4.0 h | 2026-10-28 | re-forecast: 4 of 4 working days remain at 0% and the first working day after the status date is 2026-10-23 |
| 8.2 | Backport the frontend onto the current capability co | 50% | 2026-09-16 → 2026-09-23 | 3 d / 1.5 h | 2026-10-27 | re-forecast: 3 of 6 working days remain at 50% and the first working day after the status date is 2026-10-23 |
| 10.1 | Part 1: ten-slide report with the Visio model and ta | 0% | 2026-09-23 → 2026-09-29 | 5 d / 9.0 h | 2026-10-29 | re-forecast: 5 of 5 working days remain at 0% and the first working day after the status date is 2026-10-23 |
| 9.3 | Close the four P0 defects from the bug report | 50% | 2026-09-24 → 2026-09-30 | 3 d / 3.0 h | 2026-10-27 | re-forecast: 3 of 5 working days remain at 50% and the first working day after the status date is 2026-10-23 |
| 9.6 | Final regression re-run and defect count for the rep | 0% | 2026-10-01 → 2026-10-02 | 2 d / 3.0 h | 2026-10-26 | re-forecast: 2 of 2 working days remain at 0% and the first working day after the status date is 2026-10-23 |
| 9.4 | Physical phone and PWA shadow trial | 0% | 2026-10-01 → 2026-10-06 | 4 d / 5.0 h | 2026-10-28 | re-forecast: 4 of 4 working days remain at 0% and the first working day after the status date is 2026-10-23 |
| 6.5 | Native Hermes runtime | 20% | 2026-09-30 → 2026-10-07 | 5 d / 1.6 h | 2026-10-29 | re-forecast: 5 of 6 working days remain at 20% and the first working day after the status date is 2026-10-23 |
| 10.2 | Mid-term review pack: architecture, journey, agent l | 70% | 2026-10-02 → 2026-10-16 | 4 d / 3.9 h | 2026-10-28 | re-forecast: 4 of 11 working days remain at 70% and the first working day after the status date is 2026-10-23 |
| 11.2 | Publish the deliverables to the repository | 50% | 2026-10-20 → 2026-10-20 | 1 d / 1.0 h | 2026-10-23 | re-forecast: 1 of 1 working days remain at 50% and the first working day after the status date is 2026-10-23 |
| 2.5 | 2.4  Get the requirement baseline agreed with the te | 0% | 2026-10-19 → 2026-10-21 | 3 d / 4.0 h | 2026-10-27 | re-forecast: 3 of 3 working days remain at 0% and the first working day after the status date is 2026-10-23 |
| 9.1 | Backend regression suite | 85% | 2026-09-24 → 2026-10-21 | 3 d / 1.0 h | 2026-10-27 | re-forecast: 3 of 20 working days remain at 85% and the first working day after the status date is 2026-10-23 |
| 9.2 | Frontend end-to-end suite | 60% | 2026-09-24 → 2026-10-21 | 8 d / 2.8 h | 2026-11-03 | re-forecast: 8 of 20 working days remain at 60% and the first working day after the status date is 2026-10-23 |
| 9.5 | Verification evidence pack and defect triage report | 0% | 2026-10-19 → 2026-10-21 | 3 d / 6.0 h | 2026-10-27 | re-forecast: 3 of 3 working days remain at 0% and the first working day after the status date is 2026-10-23 |

Of these, 6 are at 0% (never started) and 8 are part-done. Nothing here was moved to make the picture tidier: the planned window stays as the links produce it, and the forecast column is where the work actually still has to go.

## 3. Course deadlines versus our own milestones

| WBS | milestone | kind of date | scheduled | deadline | progress | what it means |
|---|---|---|---|---|---|---|
| 1.4 | M1  Topic and scope agreed | observed event | 2026-09-08 | - | 100% | a recorded event, not a commitment |
| 2.4 | M2  Requirements baseline drafted | observed event | 2026-09-15 | - | 100% | a recorded event, not a commitment |
| 3.4 | M3  Architecture design complete | observed event | 2026-09-22 | - | 100% | a recorded event, not a commitment |
| 4.6 | M4  Core backend running end to end | observed event | 2026-10-05 | - | 100% | a recorded event, not a commitment |
| 5.5 | M5  Provider mesh integrated behind one interface | observed event | 2026-09-28 | - | 100% | a recorded event, not a commitment |
| 6.6 | M6  Agent surface proven against a live model | observed event | 2026-10-05 | - | 100% | a recorded event, not a commitment |
| 7.4 | M7  Frontend running against the real backend | observed event | 2026-10-01 | - | 100% | a recorded event, not a commitment |
| 8.3 | M8  Integration line stable | observed event | 2026-09-23 | - | 100% | a recorded event, not a commitment |
| 9.7 | M9  System test ready (plan target) | plan target (ours) | 2026-10-06 | 2026-11-02 | 0% | when the plan says the thing is ready; ours to revise |
| 10.5 | M10  Part 1 course deadline (contract 2026-10-02, missed | plan target (ours) | 2026-09-29 | 2026-10-02 | 0% | when the plan says the thing is ready; ours to revise |
| 10.6 | M11  Mid-term teacher review (scheduled 2026-10-23 noon) | plan target (ours) | 2026-10-16 | 2026-10-23 | 0% | when the plan says the thing is ready; ours to revise |
| 10.7 | M12  Part 2 course deadline (contract 2026-11-06) | plan target (ours) | 2026-10-23 | 2026-11-06 | 0% | when the plan says the thing is ready; ours to revise |
| 11.3 | M13  Coursework delivery (plan) | plan target (ours) | 2026-10-23 | 2026-11-06 | 0% | when the plan says the thing is ready; ours to revise |

Two statements the schedule is **not** entitled to make:

* M12 and M13 landing before 2026-11-06 means the plan has room before the deadline. It does not mean anything was submitted.
* M10 carries the Part 1 contract date and is recorded as missed. Whether a Part 1 file reached the course platform cannot be seen from this repository and stays **unverified pending the course record**.

## 4. Capacity: what each person can work and what the plan asks for

Availability is an assumption to be confirmed by each member: **20 h per week per student** while the module runs. Compute lanes are material resources: they are priced and never counted as student hours.

| person | student hours in the plan | weeks scheduled | available | utilisation | peak week | over-allocated weeks |
|---|---|---|---|---|---|---|
| Yang Jianbin 0802240329 | 78.0 h | 7 | 140.0 h | 56% | 19.9 h | 0 |
| Wang Jiarui 0802240322 | 74.9 h | 7 | 140.0 h | 54% | 17.2 h | 0 |
| Wang Xinyue 0802240324 | 68.0 h | 7 | 140.0 h | 49% | 19.6 h | 0 |

Total student effort in the shipped plan: **220.9 h**. R2 carried 1,808 h against a three-person capacity of about 840 h; that was the defect, and the gate that now refuses a build on any over-allocated person-week is `audit_capacity()` in `se_project_build_r2.py`.

### Week by week (available / assigned / over)

| person | week | available | assigned | over |
|---|---|---|---|---|
| wangjr | 2026-W37 | 20.0 | 2.0 | 0.0 |
| wangjr | 2026-W38 | 20.0 | 17.2 | 0.0 |
| wangjr | 2026-W39 | 20.0 | 14.2 | 0.0 |
| wangjr | 2026-W40 | 20.0 | 16.4 | 0.0 |
| wangjr | 2026-W41 | 20.0 | 6.7 | 0.0 |
| wangjr | 2026-W42 | 20.0 | 6.1 | 0.0 |
| wangjr | 2026-W43 | 20.0 | 12.3 | 0.0 |
| wangxy | 2026-W37 | 20.0 | 2.0 | 0.0 |
| wangxy | 2026-W38 | 20.0 | 11.1 | 0.0 |
| wangxy | 2026-W39 | 20.0 | 19.6 | 0.0 |
| wangxy | 2026-W40 | 20.0 | 17.6 | 0.0 |
| wangxy | 2026-W41 | 20.0 | 7.3 | 0.0 |
| wangxy | 2026-W42 | 20.0 | 2.8 | 0.0 |
| wangxy | 2026-W43 | 20.0 | 7.6 | 0.0 |
| yang | 2026-W37 | 20.0 | 19.9 | 0.0 |
| yang | 2026-W38 | 20.0 | 18.3 | 0.0 |
| yang | 2026-W39 | 20.0 | 13.2 | 0.0 |
| yang | 2026-W40 | 20.0 | 4.0 | 0.0 |
| yang | 2026-W41 | 20.0 | 2.3 | 0.0 |
| yang | 2026-W42 | 20.0 | 2.3 | 0.0 |
| yang | 2026-W43 | 20.0 | 18.0 | 0.0 |

## 5. What is left to do, and whether it fits

* 17 rows are not complete; their remaining booked work is **57.5 student hours**.
* From 2026-10-23 to the Part 2 deadline 2026-11-06 there are 11 working days, i.e. **44 h per student** at the declared availability and 132 h across the three of them.
* So the remaining work fits the calendar with room, and `CityNexus_Plan_Recovery.mpp` is the forward-looking version of it: the same open rows, re-anchored to start after the status date, with the completed rows kept as a fact snapshot.

Generated by `se_plan_status_r1.py`; machine-readable copy in `se_plan_status_result.json`.
