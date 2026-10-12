# REVOLUTION R58 — Split-Group Recovery Negotiator

## Product-direction gate

Governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

Keep this product sentence visible while implementing:

> **When a shared Journey splits and one member can no longer reach the next shared commitment safely, CityNexus can now turn member-specific presence + grounded ETAs into a governed group recovery choice: wait, let that member catch up later, or adapt the remaining Journey through the existing Hermes/collective authority path — without exposing raw coordinates, inventing live truth, or letting one traveller silently rewrite everybody else's plan.**

If this becomes another verifier campaign, a location-table cleanup, a map-redesign round, or a deterministic "always wait/skip" heuristic, stop and correct course.

---

## Starting truth

Use the current branch:

`gpt/revolution-r33-open-world-journey-adaptation`

R56 already provides in-transit rerouting.
R57 already provides member-bound location truth, privacy-preserving group presence, a grounded rendezvous stop, member-specific route acquisition, and member-risk -> Guardian handoff for genuinely trusted material risk.

Do **not** rerun R33-R56 historical closures.

R57 focused tests and the R57 Playwright may be run once as preflight. Then move directly to R58.

---

# 0. Two narrow R57 seams to close before R58

Do not reopen R57 design. Fix these narrowly, add focused tests, then continue.

### Seam A — projection authority must reflect the actual observation source

Current `group_presence_projection()` reports `ADVISORY_FOREGROUND_WEB` whenever a row exists.

That is wrong for a genuine `DEVICE_ATTESTED` / `LOCATION_ATTESTED` row.

Required:
- FOREGROUND_WEB -> advisory authority;
- DEVICE_ATTESTED / LOCATION_ATTESTED -> trusted/attested authority;
- no row -> no-bound-location;
- unknown source -> unknown/unsupported, never silently upgraded.

The normal UI still must not expose raw coordinates.

Add one focused test proving a real trusted-source row is not projected as browser advisory.

### Seam B — route provenance must stay visible without laundering replay into live

Current group ETA lookup only returns an ETA for `LIVE_PROVIDER_CAPTURE`.

R57 explicitly allows an honest captured replay/degraded closure.

Required:
- a completed provider-backed route may expose ETA together with its exact provenance;
- `CAPTURED_REPLAY` / `SEALED_REAL_REPLAY` stay visibly replay, never live;
- fixtures/mock routes must not become product truth;
- if product policy intentionally refuses replay ETA, represent that explicitly as a degraded state rather than silently making a completed route disappear.

Add a focused test for this boundary.

These are preflight seams, not the R58 product goal.

---

# 1. Product gap

R57 answers:

> "Who is apart, where is the shared rendezvous, and can you guide me there?"

But if a member-specific grounded ETA shows that one person cannot safely reach the next shared protected stop, the group still has to manually reason about what to do.

The product does not yet connect:
- per-member presence;
- per-member route ETA;
- shared protected commitments;
- the existing Guardian/Hermes recovery machinery;
- the existing collective decision/approval authority.

R58 closes that loop.

---

# 2. First-class group recovery projection

Add an Operator section, suggested name:

`group_recovery`

Suggested states:
- `INACTIVE`
- `GROUP_TOGETHER`
- `INSUFFICIENT_MEMBER_TRUTH`
- `NO_SHARED_RISK`
- `ADVISORY_MEMBER_LATE`
- `VERIFIED_MEMBER_RISK`
- `RECOVERY_OPTIONS_READY`
- `COLLECTIVE_DECISION_REQUIRED`
- `RECOVERY_PROPOSAL_READY`
- `RECOVERY_EXTERNAL_AGENT_BLOCKED`
- `RECOVERY_APPLIED`

Example shape:

```json
{
  "state": "RECOVERY_OPTIONS_READY",
  "headline": "Sam is unlikely to reach the museum before the protected entry time.",
  "affected_member": {
    "member_id": "...",
    "display_name": "Sam",
    "authority": "ADVISORY_FOREGROUND",
    "eta_minutes": 26
  },
  "shared_commitment": {
    "activity_id": "...",
    "title": "Nara Craft Museum",
    "slack_after_buffer_min": -9
  },
  "options": [
    {"kind": "KEEP_PLAN_MEMBER_CATCH_UP", "mutates_plan": false},
    {"kind": "WAIT_AS_GROUP", "mutates_plan": true},
    {"kind": "ADAPT_REMAINING_JOURNEY", "mutates_plan": true}
  ],
  "decision_authority": "COLLECTIVE_IF_PLAN_CHANGES"
}
```

Do not expose raw coordinates or observation ids in normal projection.

---

# 3. Authority split: advisory fact vs governed mutation

This boundary is mandatory.

## FOREGROUND_WEB

May support:
- advisory member lateness;
- visible ETA/slack;
- deterministic non-mutating option: "keep plan; member catches up";
- user-requested escalation to Hermes for planning.

Must **not**:
- create authoritative disruption solely from browser GPS;
- auto-mutate the group Journey;
- silently skip or move activities;
- auto-accept a proposal.

## DEVICE_ATTESTED / LOCATION_ATTESTED

May support:
- verified member-specific risk;
- one durable incident;
- Guardian/Hermes handoff;
- governed collective recovery proposal.

Still must not auto-accept a plan-changing proposal beyond existing authority policy.

Evidence strength decides what may be claimed; it does not grant unilateral plan authority.

---

# 4. Recovery option semantics

R58 should present a small set of semantically distinct options.

### A. KEEP_PLAN_MEMBER_CATCH_UP

Meaning:
- shared active plan remains unchanged;
- affected member receives route/rendezvous guidance;
- no PlanVersion mutation;
- no collective vote required because shared itinerary does not change.

This must remain available when grounded rendezvous guidance exists.

### B. WAIT_AS_GROUP

Meaning:
- shift one or more remaining activities later while respecting protected commitments.

This is a plan mutation.

Do not implement this as a fixed time-shift heuristic that bypasses the existing plan/replan authority stack.

It must become a proposal through existing planning/recovery semantics.

### C. ADAPT_REMAINING_JOURNEY

Meaning:
- Hermes may search existing grounded alternatives:
  - reorder flexible stops;
  - skip a low-priority flexible stop;
  - choose a later shared rendezvous already grounded in Journey/place truth;
  - otherwise return NO_ACTION/BLOCKED.

Do not invent arbitrary meetup points.
Do not invent provider facts.
Do not create a second "GroupRecoveryAgent".

---

# 5. Reuse existing Hermes + collective authority

R58 must compose existing systems rather than create a parallel stack.

Use:
- existing Guardian;
- existing Hermes native MCP mission/runtime;
- existing proposal / PlanVersion machinery;
- existing collective mediation / approval semantics from the earlier Revolution collective work;
- existing protected commitment enforcement.

For a plan-changing group recovery:

1. material risk becomes an existing normal recovery trigger;
2. Hermes inspects Journey/Twin/member-risk context;
3. Hermes may produce one bounded PLAN_ONLY recovery proposal;
4. proposal is marked as group-impacting;
5. existing collective authority determines whether approval is required;
6. only the normal accepted path may mutate the active plan.

Do not call an LLM merely to restate deterministic ETA math.

---

# 6. Group-impact classification

A proposed recovery is group-impacting if it changes shared itinerary truth, including:
- activity order;
- activity inclusion/removal;
- shared start time;
- shared rendezvous activity;
- protected commitment interaction.

A route only for one member is **not** group-impacting.

Keep this classification server-owned.

The browser must not declare a proposal "personal" to evade collective approval.

---

# 7. Member-specific causal context

When Hermes is invoked for R58, provide privacy-minimized structured context.

Allowed:
- affected traveler/member id;
- display name;
- coarse location authority class;
- member route ETA;
- route provenance;
- shared rendezvous activity id/title;
- commitment slack/risk;
- group-presence state;
- active plan id;
- relevant protected commitment ids.

Do not provide another member's raw latitude/longitude unless an existing explicitly authorized tool contract already requires it.

Prefer derived facts over raw coordinates.

---

# 8. One continuous incident

A member who remains late across multiple samples/routes should not create:
- one Event per GPS point;
- one AgentRun per refresh;
- one proposal per tap.

Stable incident identity should include:
- Journey;
- affected member/traveler;
- active plan / recovery epoch;
- shared commitment/rendezvous.

Observation ids and route operation ids are evidence, not incident identity.

If the incident is resolved and later genuinely recurs, a new incident is valid.

---

# 9. Advisory escalation is user-driven

For browser-only presence:
- product may show `ADVISORY_MEMBER_LATE`;
- it may offer "Help us decide" / "帮我们调整";
- pressing it may start one bounded Hermes PLAN_ONLY mission;
- the mission must carry the authority label that source presence is advisory.

Hermes may recommend:
- KEEP_PLAN_MEMBER_CATCH_UP;
- WAIT_AS_GROUP proposal;
- ADAPT_REMAINING_JOURNEY proposal;
- NO_ACTION / insufficient evidence.

It must not reinterpret browser GPS as verified physical presence.

---

# 10. Verified risk may wake Guardian once

For genuine trusted member location + grounded route + material shared commitment risk:

- reuse the existing R57 incident Event;
- wake the same Guardian once;
- do not create a duplicate R58 disruption solely to start planning;
- R58 consumes the R57 member-risk incident as causal truth.

If external Hermes is unavailable:
- `RECOVERY_EXTERNAL_AGENT_BLOCKED`;
- keep deterministic guidance available;
- no fallback itinerary mutation.

---

# 11. Collective decision UX

Normal shared-Journey UI should answer four things:

1. What changed?
2. Who is affected?
3. What happens if we keep the plan?
4. Which options would change everyone's plan?

Suggested copy:

> Sam may reach the museum about 9 min after the safe entry buffer.
>
> **Keep the plan** — Sam follows the regroup route. No one else's itinerary changes.
>
> **Adjust together** — CityNexus can prepare a group recovery plan for everyone to review.

If a proposal is ready:
- show the meaningful itinerary diff;
- show protected commitments preserved/affected;
- show who must approve under existing policy;
- never claim "everyone agreed" unless collective authority actually says so.

---

# 12. No fake consensus

Hard boundary:

- OWNER is not automatically "the whole group" unless current authority policy explicitly grants unilateral authority for this mutation.
- absence of another member's response is not approval;
- stale membership must not count;
- withdrawn/expired members must not be asked;
- do not auto-create approvals in tests/live runs.

If collective decision cannot close, keep the proposal pending.

That is a valid outcome, not a failure.

---

# 13. Privacy

R58 normal UI and Agent context should avoid unnecessary precise member location.

Do not expose:
- latitude/longitude;
- observation ids to other members;
- edge device tokens;
- traveler bearer tokens;
- raw provider payloads.

Retain only evidence needed for audit and authority.

---

# 14. Focused tests

Only add tests that prove the new capability.

Preflight seam tests:
1. trusted R57 observation projects trusted authority, not browser advisory.
2. replay route provenance remains replay and is either visible or explicitly degraded.

R58 tests:
3. together/no risk -> group recovery quiet.
4. browser member late -> ADVISORY_MEMBER_LATE, no Event/Guardian.
5. KEEP_PLAN_MEMBER_CATCH_UP -> no PlanVersion mutation.
6. browser user explicitly asks for help -> one PLAN_ONLY Hermes mission maximum for incident.
7. Hermes context contains derived member risk, not another member's raw coordinates.
8. plan-changing recovery is classified group-impacting server-side.
9. group-impacting proposal enters existing collective authority path.
10. no fake approvals are created.
11. trusted R57 member-risk Event -> one Guardian handoff, R58 reuses it instead of creating duplicate incident.
12. repeated samples in same incident do not fan out AgentRuns/proposals.
13. external Agent unavailable -> BLOCKED + no mutation.
14. accepted collective proposal mutates only through normal governed accept path.
15. protected commitments remain enforced.
16. member removal/expiry updates required voters correctly.
17. TypeScript.
18. one focused Playwright showing the difference between "Keep plan" and "Adjust together".

Do not rerun old campaigns.

---

# 15. One bounded R58 product experiment

Use one fresh shared Journey with two authenticated active members.

Preferred honest closure:

1. create/select/start one fresh shared Journey;
2. both members explicitly share one FOREGROUND_WEB location;
3. obtain a grounded route for the affected member to the existing shared protected stop;
4. make the route/slack honestly show that member is late;
5. Operator shows `ADVISORY_MEMBER_LATE`;
6. verify no authoritative Event/Guardian was created solely from browser GPS;
7. user chooses **Adjust together** exactly once;
8. start exactly one Hermes PLAN_ONLY recovery mission;
9. Hermes returns one of:
   - a governed group-impacting proposal;
   - KEEP_PLAN_MEMBER_CATCH_UP / NO_ACTION;
   - honest external BLOCKED;
10. if a plan-changing proposal exists, prove it requires the existing collective authority path;
11. do **not** auto-approve merely to get a mutation;
12. if approvals genuinely exist through the normal product path, one accepted proposal may mutate the plan;
13. otherwise stop with proposal pending;
14. verify active plan unchanged unless normal authority accepted it;
15. stop.

Valid outcomes:
- `GROUP_RECOVERY_PROPOSAL_READY`
- `GROUP_RECOVERY_COLLECTIVE_APPROVAL_REQUIRED`
- `GROUP_RECOVERY_KEEP_PLAN`
- `GROUP_RECOVERY_NO_ACTION`
- `GROUP_RECOVERY_EXTERNAL_AGENT_BLOCKED`

All are legitimate if truthful.

Do not retry just to force a mutation.

---

# 16. Result requirements

At completion, write one concise R58 result document containing:

- exact commit SHA;
- focused test counts;
- TypeScript result;
- Playwright result;
- fresh Journey id;
- member ids (non-secret identifiers only);
- group-presence authority;
- route provenance;
- computed slack/risk;
- whether an Event existed;
- whether Guardian ran;
- AgentRun id/status if started;
- proposal id/status if created;
- collective decision status;
- mutation count;
- active PlanVersion before/after;
- explicit limitations.

Do not call replay live.
Do not call advisory presence verified.
Do not call a pending collective proposal "applied".

---

# Stop condition

Stop when CityNexus can truthfully answer:

> **"One person is going to miss the next shared stop. Can we keep everyone else's plan intact, or should the group adapt — and who actually has authority to approve that change?"**

End-user capability:

> **"When our group gets separated, CityNexus no longer only tells us where to regroup. It can understand who is running late, preserve the plan when that is enough, and when the shared itinerary really needs to change, prepare one governed recovery choice for the group instead of letting one person's GPS silently rewrite everybody's trip."**
