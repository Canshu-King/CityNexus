# CODEX START HERE — Revolution R14

Read this mission before changing code:

`revolution/R14_FACT_DRIVEN_PLANNER_MISSION.md`

The mission title is now:

`Revolution R14 — Autonomous Strategy Engine`

Required startup receipt:
- `TASKBOOK_READ`
- current task-book blob SHA
- current working branch and SHA
- one-sentence mission summary

Then implement immediately. Do not wait for another approval turn.

The key Revolution shift:
- fact-driven ranking is only a subproblem;
- the agent must gain strategy-level freedom to decide what evidence to acquire, which Places/sources to investigate, when to pivot, and which planning/replan strategy to pursue;
- deterministic CityNexus remains the truth/persistence/authority boundary;
- real-city static `metrics_list` and earliest-opening/place-id greedy planning are demo-era scaffolding to remove;
- prove at least one self-directed evidence/strategy pivot;
- target a live disruption -> agent strategy -> authority-approved replan -> completed revised journey;
- push for a second unseeded city without city-specific planner logic.

No micro-ORDs. One capability branch, one result report. Do not stop at a nicer planner.
