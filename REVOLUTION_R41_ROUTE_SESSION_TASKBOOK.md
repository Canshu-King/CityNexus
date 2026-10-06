# REVOLUTION R41 — Route Session & On-Demand Mobility Edge

## Starting truth

R40 is complete and immutable.

Accepted facts:
- commit: `dea17424a149ffcd4e62b7da5bffae2d323b4390`
- outcome: `LAUNCH_SETUP_GROUNDED_EDGE_UNAVAILABLE`
- a fresh Journey first returned `NEEDS_ORIGIN`
- a real provider-backed Place was confirmed through the product API as `USER_CONFIRMED_PLANNED_ORIGIN`
- `JourneyLaunchContext` persisted successfully and fed R39/R38
- there was still no exact launch-origin -> first-target provider route
- no duration or `must_leave_by` was fabricated
- active plan / execution truth / Event / AgentRun / proposal / mutation all remained unchanged
- focused backend 37 passed; Python compile and TypeScript passed
- Playwright was stopped by the existing demo reset token precondition before R40 assertions
- R33-R40 live closures must not be rerun

R40 solved missing origin input.

R41 must solve the next product gap: **obtaining one exact route as a first-class, durable product operation**.

## Code-level finding

The repository already has capable mobility primitives:

`capture_runtime_mobility_snapshot(session, journey, pairs, operation_key, ...)`

and Valhalla-backed provider capture.

But they are currently consumed by plan/replan/stay workflows.

There is no product contract for:

> “For this Journey, acquire exactly this grounded origin -> exact target route, once, persist what happened, let clients poll/read it, and let readiness consume it.”

A read projection must not secretly call a provider. A transient provider call must not live only inside one HTTP request. Two user taps must not double-call the provider.

R41 introduces that missing operation.

## Revolution objective

Build a durable **Route Session** for one exact mobility edge.

The lifecycle should be:

`GROUNDED_ORIGIN + EXACT_TARGET -> ROUTE_SESSION -> PROVIDER_CAPTURE -> FROZEN MOBILITY FACT -> READINESS`

The same product primitive should later be reusable for:
- first-trip launch;
- current-location reroute;
- activity-to-activity refresh;
- offline last-known route;
- provider degradation;
- future execution navigation.

R41 is not a “Valhalla retry endpoint.”

## A. Durable operation

Introduce a named durable model such as:

`RouteAcquisitionOperation`

Suggested fields:
- id
- journey_id
- fingerprint
- origin_key
- target_key
- target_activity_id nullable
- requested_mode
- status
- phase
- outcome nullable
- request_json
- result_json
- error_json
- queued_at
- started_at nullable
- finished_at nullable
- updated_at

Reuse the proven operation principles from:
- StayGenerationOperation
- CatalogHydrationOperation

Do not invent progress percentages.

Suggested states:
- QUEUED
- RUNNING
- COMPLETED
- UNAVAILABLE
- FAILED

If product scope warrants abandonment, use the existing operation-state conventions rather than a special route-only race model.

Suggested outcomes:
- ROUTE_READY
- ROUTE_PROVIDER_DEGRADED
- ROUTE_UNAVAILABLE
- ROUTE_PROVIDER_FAILURE
- ROUTE_INPUT_INVALID

`UNAVAILABLE` is not the same thing as `FAILED`.

Provider answered “no usable route” / no explicit fact:
- UNAVAILABLE

Runtime/provider crashed:
- FAILED

## B. Stable fingerprint / idempotency

One semantic route request should converge.

Fingerprint inputs must include at least:
- journey id;
- grounded origin identity;
- exact target Place identity;
- target activity id when route meaning depends on it;
- requested mode / mode policy;
- provider policy version;
- route truth policy version.

Do not fingerprint:
- random operation id;
- UI text;
- request timestamp;
- mutable display name.

Two concurrent submissions for the same semantic request must not double-call the provider.

Use a durable uniqueness rule, not only an in-process lock.

A terminal stale/expired result may permit a new operation according to an explicit refresh policy. Do not silently join forever to a dead route.

## C. Exact endpoint contract

Add an explicit operation endpoint, for example:

`POST /api/v1/journeys/{journey_id}/routes/acquire`

The caller should normally provide the target activity / route intent, not arbitrary coordinates.

Server resolves:
- grounded launch/current origin from the authoritative R39/R40 projection;
- exact target Place from the active plan;
- exact semantic pair.

GET/read endpoints remain read-only.

Suggested response:
- operation id;
- reused;
- status;
- phase;
- outcome;
- exact origin/target keys;
- provider result if terminal;
- poll URL.

Do not call a provider from:
- GET readiness;
- GET launch-setup;
- GET Guardian status;
- offline snapshot generation.

## D. Provider capture

Use the existing mobility runtime.

For this product path:
- exactly one semantic pair;
- live provider when configured;
- no deterministic mock laundering into live route truth;
- no nearest-edge fallback;
- no aggregate fallback.

Prefer explicit/hard capture semantics when the result will drive `must_leave_by`.

A mock/synthetic fallback may exist for explicit demo/offline modes only if provenance remains non-live and readiness does not present it as live provider truth.

Do not retry within one operation to make the answer prettier.

Provider-specific fallback between genuinely live supported costings may remain if the existing runtime already treats it as live provider behavior and records that provenance.

## E. Freeze the successful edge

A successful Route Session must persist/reuse one exact `MobilityFact` or equivalent frozen route record.

It must bind:
- journey;
- origin key;
- target key;
- mode;
- duration;
- distance;
- provider;
- provenance;
- geometry when supplied;
- captured_at;
- expires_at / freshness semantics.

Do not mutate the active PlanVersion merely to store this route.

This is operational evidence, not a replan.

If uniqueness of `MobilityFact(journey, from_key, to_key, mode)` requires update-vs-insert policy, make that policy explicit:
- preserve latest captured provider truth;
- audit replacement or versioning;
- never overwrite a stronger live fact with synthetic fallback.

## F. Readiness integration

R39/R38 should consume terminal Route Session facts through the same exact edge projection.

When a live exact route becomes available:
- route kind = LAUNCH_EDGE or relevant exact edge;
- readiness may compute `must_leave_by`;
- receipt must explain duration + safety buffer + target start.

When operation is:
- QUEUED/RUNNING -> readiness remains uncertain, copy “Route check in progress.”
- UNAVAILABLE -> readiness remains uncertain/action-needed depending on time horizon.
- FAILED -> expose provider failure honestly; do not call that “no route exists.”
- COMPLETED but expired -> label frozen/stale according to policy.

No operation outcome itself creates a material Event.

## G. User experience

When origin is grounded but exact route is missing:

> “Starting point saved. Check the route to your first stop.”

CTA:
**Check route**

During operation:
> “Checking the route from [origin] to [target]…”

Success:
> “About 18 min · leave around 08:32.”

Unavailable:
> “CityNexus could not get a reliable route for this leg.”

Provider failure:
> “The route provider is unavailable right now.”

Do not display:
- operation fingerprint;
- raw provider stack trace;
- internal state names.

Do not automatically spam route checks on every render.

## H. Guardian interaction

R41 does not turn route acquisition into a recovery Agent.

Guardian may later decide a route fact is stale and recommend refresh, but:
- no hidden provider loop;
- no AgentRun just because route is missing;
- no Event just because route acquisition failed.

A genuine provider-verified traffic disruption can still enter the existing Event path separately.

## I. Offline continuity

Offline snapshot may include the last terminal route session:
- route status;
- source/target display;
- duration;
- provider/provenance;
- capture/expiry;
- must_leave_by derived at capture;
- clear last-known semantics.

Never show a RUNNING cloud operation as if it completed offline.

## J. Authority invariants

Route Session may write:
- operation state;
- ProviderCall / provider receipt if existing infrastructure does so;
- exact MobilityFact;
- audit records.

It must not:
- mutate PlanVersion;
- change Activity.status;
- set current_activity_id;
- create execution truth;
- create Event merely for absence/failure;
- start Hermes;
- create AgentRun;
- create proposal;
- change booking/commitment.

Keep `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` for live proving.

## Tests before live closure

At minimum:

1. grounded origin + exact target creates one semantic fingerprint;
2. duplicate concurrent/serial submit reuses same open operation;
3. different origin or target creates a different fingerprint;
4. display-name/timestamp changes do not change fingerprint;
5. GET projections perform zero provider calls;
6. successful exact capture freezes a matching MobilityFact;
7. unrelated provider fact cannot satisfy the operation;
8. missing explicit provider fact -> UNAVAILABLE, not fake READY;
9. provider exception -> FAILED, distinguishable from UNAVAILABLE;
10. synthetic/mock fallback cannot become live provider truth;
11. completed exact route feeds R39 launch edge;
12. exact live duration feeds R38 `must_leave_by`;
13. RUNNING operation does not fabricate duration;
14. route operation creates zero Event/AgentRun/proposal/mutation;
15. R40 launch setup tests stay green;
16. R39 launch edge tests stay green;
17. R38 readiness tests stay green;
18. TypeScript and focused route/readiness Playwright pass.

Do not run broad verifier loops.

## One bounded R41 live closure

Do not rerun R33-R40.

Use a new fresh Journey.

Required shape:
- real provider-backed first target;
- a real user-confirmed planned launch origin through R40 product API;
- submit one Route Session through the real R41 API;
- allow that operation one provider acquisition lifecycle;
- read terminal result;
- recompute readiness once.

Do not call the provider manually from the harness.
Do not issue a second Route Session because the first answer is unattractive.

Valid truthful outcomes:
- `ROUTE_SESSION_READY`
- `ROUTE_SESSION_UNAVAILABLE`
- `ROUTE_SESSION_PROVIDER_DEGRADED`
- `ROUTE_SESSION_FAILED`

If READY:
- exact MobilityFact must exist;
- R39 must consume it;
- R38 may produce grounded `must_leave_by`.

If UNAVAILABLE/FAILED:
- no duration;
- no `must_leave_by`;
- origin remains grounded;
- failure/unavailable semantics remain distinct.

Receipt must include:
- source HEAD;
- Journey / active plan;
- launch contract;
- origin key / target key;
- operation id + fingerprint;
- reused flag;
- status/phase/outcome;
- provider attempt count;
- provider key/provenance;
- exact MobilityFact id if any;
- duration/distance/mode;
- captured_at/expires_at;
- readiness after terminal operation;
- must_leave_by + buffer or absence reason;
- Event/AgentRun/proposal/mutation counts;
- active plan before/after.

## Required artifacts

- `REVOLUTION_R41_ROUTE_SESSION_RESULT.md`
- `backend/output/r41-route-session-v1.json`

## Stop condition

After the single R41 live Route Session:
- write receipt;
- commit;
- push;
- stop.

R41 succeeds when CityNexus stops treating route acquisition as an incidental side effect of plan generation and turns it into a reusable operational capability:

**“You told me where you are starting. I can now request exactly one real route to the next stop, remember the result, explain whether it succeeded, and use it to tell you when to leave—without changing your trip or inventing an ETA.”**
