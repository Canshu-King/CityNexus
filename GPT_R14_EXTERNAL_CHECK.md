# GPT external check — R14 -> R15

Base inspected: `c9e3a2aa254e25ccdbac1818ef443bdfe1956f64`

## What R14 genuinely proved

R14 is a real Revolution step, not an ORD loop. Machine evidence in the delivery package shows:
- multiple fresh unseeded cities, not one fixture replay;
- persisted AgentRuns using domestic WB2api models;
- live OSM/Overpass discovery;
- exact-entity secondary checks;
- strategy pivots after real product gates/search saturation;
- live Valhalla used-edge evidence;
- real select/start/activity state transitions;
- real replan proposals and Gateway acceptance;
- revised Journeys reaching COMPLETED.

This is materially beyond R11/R13.

## The lab estimate envelope has now served its purpose

`COURSEWORK_ESTIMATED_FACTS` is explicitly isolated:
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY` defaults false;
- canonical Place opening/cost remain UNKNOWN;
- estimates remain `ESTIMATED_AGENT` / `authority_eligible=false`;
- with the envelope disabled, the same unresolved plan is non-selectable and select returns `UNRESOLVED_ACTIVITY_FACTS`.

Therefore it is not silent truth corruption.

However, it must NOT become the next success criterion. A normal select returning 200 for a plan whose canonical facts remain UNKNOWN is acceptable only as a temporary Lab experiment. Continuing to close city after city this way would turn the Revolution into an estimate-powered demo.

R15 should use estimates only for strategy/value-of-information decisions. Production-like success must be achieved with the estimate-authority envelope OFF.

## c9 domestic-model fix: reasonable, but not fully closed

The `c9e3a2aa` repair correctly distinguishes a likely reasoning-budget exhaustion from a normal fallback event and retries the same model with a larger non-stream budget.

The package proves:
- focused tests: 47 passed;
- WB2api small-budget probe reproduced empty content + reasoning + `finish_reason=length`;
- the code retries 1200 -> 2400 on the same model before fallback.

But the package explicitly does NOT contain a post-c9 restarted real Agent run. Do one short live preflight, then move on.

Two follow-up runtime concerns should be fixed inline if they bite the R15 mission:
1. streamed parsing currently discards `finish_reason`, so any empty stream is treated as retryable; preserve stream finish metadata so content-filter/provider-empty cases are not misclassified as budget exhaustion;
2. there is no clear mission-level wall-clock budget. Historical failed AgentRuns consumed ~137-242 s and an outer synchronous PowerShell wait lasted hours. Add a bounded total runtime/deadline around the user-facing Agent command if the R15 run can still hang.

Do not turn either concern into a separate runtime project.

## Revolution frontier

R14 demonstrated:
Agent can inspect -> search -> estimate -> pivot -> plan -> select under Lab envelope -> execute/replan.

R15 must demonstrate:
Agent can inspect -> decide which missing truth matters -> find/corroborate real sources -> promote canonical facts -> pivot when evidence is unavailable -> select with the estimate envelope OFF -> execute/replan -> complete.

That is the next capability boundary.
