# REVOLUTION R34 — Live Context Watch and Venue Reality Adaptation

## Why this round exists

R33-1 is honestly **BLOCKED** and must remain so.

The single authorized R33-1 live closure already proved that CityNexus can:
- call Open-Meteo successfully;
- persist a real `LIVE_PROVIDER` observation;
- refuse to manufacture a `PROVIDER_VERIFIED` disruption when the provider evidence does not justify one;
- stop before Hermes, proposal, authority, and mutation when there is no material world change.

That is correct product behavior. Do **not** rerun R33-1, reopen R32, create a verifier-only loop, lower the Open-Meteo risk threshold, or wait for convenient weather.

The exposed product gap is broader: CityNexus currently has multiple real-world acquisition capabilities, but Journey adaptation is still coupled too tightly to one exceptional weather-risk trigger.

R34 turns external reality into a product capability rather than a lucky test condition.

## Revolution objective

Build one honest **Live Context Watch** path for active Journey activities.

The watch must acquire fresh server-owned external facts for the current Journey and distinguish:

1. **NO_MATERIAL_CHANGE** — fresh reality was observed but does not make the current Journey worse or infeasible; no Agent and no mutation are required.
2. **MATERIAL_CONFLICT** — fresh qualified evidence conflicts with the scheduled activity; CityNexus may open recovery and let the existing WB2api/Hermes Agent choose a response.
3. **UNKNOWN / DEGRADED** — evidence is unavailable, ambiguous, stale, or provider access failed; do not convert uncertainty into a hard fact.

The immediate R34 proving domain is **venue/opening-hours reality**, because the branch already contains real source acquisition infrastructure in:
- `backend/app/fact_acquisition.py`
- `backend/app/integrations/discovery/real_city.py`
- `backend/app/integrations/web/research_service.py`
- `backend/app/integrations/web/searxng.py`

Use those boundaries. Do not invent a parallel scraper merely for R34.

## Non-negotiable inherited truth

Keep:
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`;
- current WB2api/Hermes selection;
- server-owned AgentRun / RecoveryEpoch / authority semantics;
- exact proposal provenance exposed by R33;
- stale-run and stale-authority rejection;
- at most one legal Journey mutation per live closure.

R33-1 result and `backend/output/r33-live-strike-v1.json` are immutable historical evidence. Do not edit them to make R34 look green.

## Product behavior to implement

### A. Fresh venue reality capture

For one or more non-terminal activities in the active plan, use the existing fact-acquisition path to refresh the exact provider-bound Place.

Acceptable evidence may include:
- live Overpass/Nominatim provider tags carrying opening-hours state;
- an operator-approved exact official source binding already supported by the product;
- captured official-page structured evidence already accepted by the existing authority model.

The live capture must persist its normal WebObservation / provider evidence trail.

Do not let an Agent:
- choose the source URL;
- upgrade its own source candidate into official authority;
- hand-write opening hours;
- hand-write a closure.

### B. Deterministic plan-vs-reality impact

Add a server-owned evaluator that compares the current activity interval against the newest qualified opening-hours evidence for the exact Place.

The evaluator must be able to return at least:
- `OPEN_COMPATIBLE`
- `CLOSED_CONFLICT`
- `OUTSIDE_VERIFIED_HOURS`
- `UNKNOWN`
- `PROVIDER_DEGRADED`

A hard recovery trigger may be emitted only for a qualified conflict. Unknown/unparsed/weak evidence is not a closure.

The persisted trigger must identify:
- Journey id;
- Activity id;
- Place id / exact provider entity;
- evidence observation id(s);
- source class / provider key;
- capture time;
- planned local interval;
- verified opening-hours interval or explicit closed state;
- deterministic reason code.

Use a server-owned event/provenance class consistent with the existing model. Do not relabel web/provider evidence as `PROVIDER_VERIFIED` unless the existing trust rules actually grant that provenance.

### C. Context watch result is first-class

Expose one compact runtime result/receipt for the watch containing:
- checked activities;
- refreshed observations;
- material conflicts;
- no-op facts;
- unknown/degraded facts;
- recovery event ids created;
- whether an Agent was started.

A successful no-op is valid product behavior and should be observable as such.

Do not define R34 success as “must mutate something.”

### D. Agent starts only after material conflict

If and only if the live context watch finds a qualified material conflict:
- open/use the current RecoveryEpoch path;
- start the existing external WB2api/Hermes Agent;
- present goals/constraints and current product truth, not a prescribed replacement;
- let Hermes inspect/search/propose autonomously;
- bind the proposal to the exact AgentRun + current RecoveryEpoch;
- use current legal authority;
- execute at most one mutation.

Do not preselect the exact replacement, proposal id, tool sequence, or mutation result.

### E. Traveller-facing explanation

For a material conflict, Live Recovery should let the traveller understand:
- what external reality changed or was newly verified;
- which planned activity is affected;
- what the Agent proposes to change;
- Agent-origin provenance already introduced in R33;
- the final visible Journey delta after legal mutation.

For `NO_MATERIAL_CHANGE`, do not manufacture an alarming recovery card.

## Local verification before any live closure

Keep this narrow and product-focused.

At minimum add/repair tests for:
- exact Place/source binding;
- verified opening-hours interval comparison in Journey timezone;
- explicit CLOSED handling;
- UNKNOWN / RAW_UNPARSED cannot trigger hard recovery;
- stale observation cannot override a fresher qualified observation;
- no Agent start for `NO_MATERIAL_CHANGE`;
- Agent start is gated behind a persisted material-conflict event;
- existing R33 proposal provenance remains intact;
- existing authority tests touched by the new trigger remain green.

Run frontend typecheck only if UI code changes.

Do not rerun the historical R32 suite unless a directly touched authority invariant requires the narrow relevant test.

## One live closure only

After focused verification, execute **one** R34 live closure against a new/clean Journey.

This is not a retry of R33-1.

The closure must:
1. create/select/start a real Journey with at least one discretionary venue activity;
2. record the initial active strategy before the new fact capture;
3. refresh current venue facts through the existing live acquisition boundary;
4. persist the returned external evidence honestly;
5. run the server-owned impact evaluator.

Then branch on reality:

### If no material conflict is found

Record:
- `status = NO_MATERIAL_CHANGE`;
- the exact live observation ids and evidence;
- zero AgentRuns caused by R34;
- zero R34 mutations.

This is a valid R34 product result. Do not rerun looking for a “better” venue.

### If a qualified material conflict is found

Continue exactly once through the existing Hermes recovery path and record:
- material-conflict Event id;
- exact AgentRun id;
- exact RecoveryEpoch id;
- proposal id / proposed plan id;
- authority mode and receipt if applicable;
- final active plan id;
- semantic old-vs-new strategy delta;
- mutation count;
- public replan `source_agent_run_id` equality;
- `live-agent-origin` rendering if UI was exercised.

If the provider/source boundary fails or evidence remains unknown, report `BLOCKED` or `PARTIAL` with the exact boundary. Do not downgrade provenance.

## Required artifacts

Create:
- `REVOLUTION_R34_LIVE_CONTEXT_WATCH_RESULT.md`
- `backend/output/r34-live-context-watch-v1.json`

The JSON should be a factual causal receipt, not a synthetic verdict framework.

Include:
- source head;
- Journey / initial plan ids;
- initial human-readable strategy;
- checked activity/place ids;
- provider/source observations and capture times;
- impact classifications;
- created recovery event ids;
- Agent/epoch/proposal/authority ids only when they actually exist;
- final active plan id;
- mutation count;
- limitations.

## Stop conditions

Stop after the one live R34 closure.

Do not:
- run R33-1 again;
- create R33-2;
- run repeated R34 live attempts until one conflicts;
- lower evidence thresholds for convenience;
- use simulated/public client Events as proving facts;
- edit the DB by hand;
- copy an old artifact;
- add deterministic Agent fallback;
- prescribe Hermes' answer;
- claim physical travel.

## Codex handoff

Continue in the **same local Codex thread**.

Work only on:
`gpt/revolution-r33-open-world-journey-adaptation`

First:
1. fetch the branch;
2. verify that HEAD includes this R34 taskbook after `804aaf3a8594a05c39bb5965fa174e9f67f67fb9`;
3. read the immutable R33 result and live artifact;
4. inspect the existing fact-acquisition and opening-hours authority code before changing anything.

Then implement the smallest coherent Live Context Watch product slice, test it narrowly, run exactly one live R34 closure, write the two required artifacts, commit, and push.

The target is not “green.” The target is a product that can observe reality, know when nothing needs changing, and autonomously recover only when the evidence really demands it.
