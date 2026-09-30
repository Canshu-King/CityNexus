# CODEX START HERE — Revolution R14

Read the mission before changing code:

`revolution/R14_FACT_DRIVEN_PLANNER_MISSION.md`

Required startup receipt:
- `TASKBOOK_READ`
- task title: `Revolution R14 — Fact-Driven Planner`
- current working branch and SHA
- one-sentence mission summary

Then implement immediately. Do not wait for another approval turn.

Key finding from GPT review:
- real-city AUTO currently sorts eligible Places by earliest opening + place.id;
- it greedily packs and rotates up to three variants;
- real-city score dimensions still come from static `metrics_list` constants;
- operator-supplied fact URLs are an approval binding, not independent autonomous identity proof;
- `d075a4cd` is a valid narrow fix but the Japanese price parser still needs audience-aware edge handling.

No micro-ORDs. One capability branch, one result report.
