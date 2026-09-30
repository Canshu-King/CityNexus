# Revolution R12 — Zero-Seed Autonomous Trip

## Why this is the next move

R7-R11 proved that a provider-backed selected plan can execute all the way to Journey COMPLETED on the Suzhou winter scenario. That proof is sufficient. Do not spend another round deepening the same fixed journey.

The next Revolution milestone is not more evidence on the existing Suzhou case. It is to prove that CityNexus can create, adapt, and complete a real trip from a fresh natural-language request for a city that has no pre-seeded Journey or golden itinerary.

## Step 0 — publish the living branch, then move

Before new feature work, publish the local experimental branch `codex/revolution-realtrip-recovery` to the remote with its current source history. The 12-hour delivery package references local commits `365ed420...`, `520e9b44...`, `10c383d5...`, and report commit `6d79b683...`; as of 2026-09-30 they are not present on the GitHub remote. Do not re-review them first. Push the coherent branch so the work cannot disappear, then continue.

If remote push is blocked by environment/auth, create one portable git bundle or source patch archive immediately and continue. Do not spend hours diagnosing the publishing path.

## Mission

Close one end-to-end capability chain from a completely fresh state:

```text
natural-language user intent
  -> create fresh Journey
  -> resolve an unseeded city
  -> discover real provider Places
  -> acquire/verifiably classify used facts
  -> generate persisted PlanVersion
  -> select real plan
  -> start execution
  -> inject a real or controlled external disruption
  -> agent inspects current state
  -> agent requests/proposes a replan
  -> explicit authority approves the replan
  -> execute the revised trip
  -> Journey COMPLETED
```

This is one mission, one branch, one report. No micro-ORD forest.

## Non-negotiable product rules

- Do not use Beijing, Gongshan, or the existing Suzhou journey as the success scenario.
- Do not clone an existing Journey row or reuse an already selected plan.
- No synthetic POIs may be counted as success.
- Used route edges must have real provider provenance or remain explicitly degraded/non-authoritative.
- UNKNOWN opening/cost must stay UNKNOWN. Never coerce to FREE or OPEN.
- Search snippets may discover candidate sources but cannot promote authority alone.
- The product must persist the Journey, Places, PlanVersion, used edges, AgentRun/tool steps, and final completion state.
- The agent may reason about preferences and recovery, but authority facts come from CityNexus tools/providers, not model prose.
- Do not replace the current agent runtime with an older R77 runtime.
- Do not build a new harness unless a missing harness blocks the actual user path.

## City choice

Use a fresh city with enough public provider coverage to make the experiment meaningful. The first attempt should be a city absent from golden fixtures and absent from the R7-R11 evidence chain.

Timebox a city-specific dead end. If the chosen city cannot produce enough verifiable provider facts after a bounded attempt, pivot to another unseeded city. The milestone is a general capability proof, not loyalty to one city.

## Aggressive implementation order

### A. Fresh-trip creation
Start from an empty/disposable DB or a DB with no row for the chosen user trip. Create the Journey through the product API/UI from natural-language intent.

### B. Discovery + facts
Run the existing real discovery path. Materialize real Places, exact provider identity, coordinates, source class, timestamps, and usable opening/cost facts when genuinely available.

Do not stop merely because some Places remain UNKNOWN. The plan may stay provisional until used facts are sufficient.

### C. Plan + select
Generate a plan using the actual discovered Places. Prove the selected plan only uses eligible facts and real route evidence. Call the real select endpoint. Read back the active plan.

### D. Begin real execution
Start the Journey and advance at least one activity through depart/arrive/begin/complete.

### E. Force the product to think
Inject one disruption after execution has started. Examples:
- selected Place becomes unavailable/closed;
- weather constraint changes;
- user says “I am tired; reduce walking and keep the core cultural stops”;
- a commitment becomes infeasible.

The disruption must affect the current plan. Do not use an unrelated advisory that leaves the plan untouched.

### F. Real agent step
Use the current configured runtime. Require a persisted PLAN_ONLY AgentRun with actual tool calls.

Minimum tool behavior:
1. inspect current Journey/Twin first;
2. inspect relevant facts/constraints;
3. request/propose a replan grounded in those facts;
4. return the proposed change and reason codes.

If Hermes remains unavailable, record that exact fact once. Do not pause the mission to rebuild Hermes. Use the supported configured agent path instead.

### G. Authority crossing
The agent does not silently mutate the selected plan. Cross the existing authority boundary explicitly:
- present the replan candidate;
- approve/select through the real product authority path;
- persist the new active plan/version.

### H. Finish the revised journey
Continue the real state machine on the revised plan until Journey COMPLETED.

## Inline fixes only

Any defect discovered on this path is fixed inline if it blocks the mission. Examples:
- completed Journey still exposing an irrelevant recovery proposal;
- active plan projection conflicting with completed Journey state;
- stale provider-mesh facts;
- route/UI truth mismatch.

Do not create a separate review branch for each defect. Fix, regression-test, continue.

## Stop doing these

- no R12a/R12b/R12c recut carousel;
- no branch-per-defect;
- no repeated proof of the existing Suzhou zero-minute edge;
- no “23 tests passed” as the main outcome;
- no report-only round after the product path is already proven;
- no broad-suite archaeology unless candidate introduces a new failure;
- no spending half the run comparing SHA trees before coding.

## Success grades

### REVOLUTION_A — minimum acceptable
Fresh unseeded city -> real provider plan -> selected -> execution starts.

### REVOLUTION_B — target
REVOLUTION_A + persisted real AgentRun -> fact-grounded replan proposal -> authority-approved replacement plan.

### REVOLUTION_C — desired
REVOLUTION_B + revised plan executed to Journey COMPLETED with live provider/mobility truth preserved.

Do not declare B or C from mocks or prose.

## Final deliverable

One report only: `REVOLUTION_R12_ZERO_SEED_AUTONOMOUS_RESULT.md`.

It must contain:
- base SHA and final SHA;
- remote branch name;
- natural-language user request;
- fresh Journey ID;
- chosen city and resolver/provider identity;
- used Place IDs + exact source provenance;
- used mobility edges + provider provenance;
- initial select receipt;
- disruption;
- persisted AgentRun ID + ordered tool calls;
- replan candidate and authority-crossing receipt;
- revised active plan ID;
- final execution state;
- focused tests and candidate-vs-base broad-suite delta;
- remaining blockers only if they truly prevented the next grade.

The main success criterion is not evidence volume. It is this sentence becoming true:

> A fresh user can ask CityNexus for a real trip in an unseeded city, begin that trip, encounter a change, have the agent reason over live product state, approve a grounded replan, and finish the revised journey.
