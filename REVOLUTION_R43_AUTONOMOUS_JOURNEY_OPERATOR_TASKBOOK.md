# REVOLUTION R43 — Autonomous Journey Operator v1

## Product-direction gate

This task is governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

Before implementation, answer:

> **CityNexus newly learns to autonomously carry one Journey disruption from observation to decision to required human approval to execution, then return to active monitoring without asking the user to manually stitch Guardian, Agent, proposal, and approval screens together.**

If the implementation turns into a verifier campaign or a projection-only refactor, stop and correct course.

## Starting point

R42 is complete at commit `b8d3f9402151289684812a61867e49985c2266e4`.

R42 proved a real authenticated execution transition:
- DUE_NOW
- one OWNER “I’m leaving”
- OPERATOR_CONFIRMED_EXECUTION
- Activity -> EN_ROUTE
- Guardian phase -> IN_TRANSIT

Do not rerun R33-R42 historical closures.

## Existing capabilities to connect — do not reimplement

The repository already has:

- Guardian / Autopilot and World Context sensing
- material Event rows
- standing JourneyMission
- configured Hermes / DeepSeek Journey Agent
- AgentToolGateway
- request_replan
- ActionApproval
- AgentPendingAction
- approval continuation
- recovery epochs
- plan mutation authority
- JourneyTwin
- notification infrastructure
- R42 authenticated execution state
- UI surfaces for Guardian / Next Move

R43 is valuable only if these become **one operating product loop**.

## The current product gap

Today the backend can already do most of this internally:

1. Guardian detects a material Event.
2. configured model inspects Journey/Twin.
3. model requests a replan.
4. Gateway may return REQUIRE_CONFIRMATION.
5. runtime persists an AgentPendingAction.
6. user may separately approve.
7. continuation resumes the exact Agent-selected action without another model call.

But the product still exposes these as separate machinery.

The traveller does not have one place that says:

> “I noticed the problem, I chose this recovery, I need your approval for exactly this reason, and after you approve I will continue taking care of the Journey.”

After continuation executes, the product also needs to converge back to:

> “Change applied. I’m watching the trip again.”

That is the R43 product.

# 1. Operator mode

Create a product-level **Journey Operator** state for an ACTIVE Journey.

Do not create another Agent runtime.

Operator mode should bind:
- active standing mission;
- Guardian Autopilot enrollment;
- autonomy envelope;
- current Journey/Twin;
- latest material incident;
- current Agent/recovery run;
- pending approval if any;
- last executed recovery;
- monitoring continuation state.

Preferred user action:

**“Take care of this trip”**

The action may create/update the standing mission and enable Autopilot in one product flow.

It should let the traveller choose a simple authority preference such as:

- **Watch and advise** — PLAN_ONLY
- **Handle routine changes, ask me for important ones** — EXECUTE_WITHIN_BOUNDS with existing policy gates
- optionally use existing traveller AgentPolicy for detailed bounds

Do not expose internal policy enums unless needed in advanced settings.

## New user-visible Operator states

Suggested product states:

- OFF
- WATCHING
- INVESTIGATING
- RECOVERY_READY
- WAITING_FOR_APPROVAL
- APPLYING
- RECOVERED
- NEEDS_ATTENTION
- DEGRADED

The exact names may vary, but one user-facing state must be derivable from durable existing rows.

This state is a product projection, not a new authority source.

# 2. One Operator projection

Add one deterministic server-owned projection that joins:

- Journey + current activity
- AutopilotEnrollment
- standing JourneyMission
- latest GuardianPulse / GuardianRun
- AgentRun
- ReplanProposal
- AgentPendingAction
- ActionApproval
- current active PlanVersion
- latest material Event

Example:

```json
{
  "state": "WAITING_FOR_APPROVAL",
  "headline": "I found a closure and prepared a safer plan.",
  "journey_phase": "IN_TRANSIT",
  "incident": {
    "kind": "CLOSURE",
    "activity": "..."
  },
  "decision": {
    "summary": "Move the garden visit later and continue to the museum first.",
    "proposal_id": "..."
  },
  "approval": {
    "required": true,
    "approval_id": "...",
    "action_label": "Approve change"
  },
  "operator": {
    "watching": true,
    "will_continue_after_approval": true
  }
}
```

No raw Agent traces by default.

Advanced details may expose provenance, model/provider, and tool history.

# 3. Approval must be an Operator interaction

When an Agent-selected recovery hits REQUIRE_CONFIRMATION / REQUIRE_STEP_UP:

- show one plain-language approval card in the Operator surface;
- explain what changes and why;
- show relevant cost/schedule/commitment impact from server-owned proposal facts;
- allow authenticated traveller to approve or reject.

Do not ask the model again after approval.

Reuse the existing ActionApproval + AgentPendingAction + continuation path.

The product promise is:

> **Approve once; CityNexus continues the exact action it already chose.**

## Approval notification

Reuse NotificationEvent.

A pending Operator approval should create one deduped notification.

Example:
> “CityNexus found a recovery for the closure. Review one change.”

Do not spam on every Guardian pulse.

# 4. Continuation convergence

This is a critical R43 implementation requirement.

When `resume_pending_action()` successfully executes the Agent-selected mutation:

- Operator state must become RECOVERED/APPLIED;
- active plan must reflect the executed proposal;
- the relevant Guardian/Agent recovery lineage must be understandable as completed;
- stale approval CTA must disappear;
- the triggering incident should be acknowledged/resolved according to existing domain semantics if the executed action actually addresses it;
- Autopilot must remain enrolled;
- next Operator projection must return to WATCHING after the brief recovered state.

Do not rerun the model merely to say “done.”

If the existing GuardianRun row cannot currently learn that an approval continuation executed, add a narrow server-owned reconciliation link/update. Do not create a second recovery run.

# 5. Operator timeline

Add a compact user-facing timeline, not a developer receipt carousel.

Example:

- 10:12 — “Watching your trip”
- 10:24 — “Detected: 依水園 is closed”
- 10:24 — “Working on a recovery”
- 10:25 — “I recommend visiting X first”
- 10:25 — “Waiting for your approval”
- 10:26 — “Approved”
- 10:26 — “Plan updated”
- 10:26 — “Watching again”

Source the timeline from durable domain rows/audits.

Do not invent progress percentages or fake intermediate model steps.

# 6. External model owns the decision

For the R43 recovery path, the configured external Agent must own:

- interpreting the incident in Journey context;
- choosing whether action is needed;
- selecting/requesting a recovery;
- choosing the proposal/action to execute.

The server remains authoritative for:
- provider/world truth;
- feasibility;
- policy;
- approval;
- mutation;
- idempotency.

Do not replace model judgment with a fixed deterministic recovery recipe merely to make the live closure predictable.

If the external Agent is unavailable during the R43 product experiment, report it honestly.

For this R43 closure, do not claim the deterministic Guardian fallback proves Autonomous Journey Operator model judgment.

# 7. One-click product activation

Prefer one product action that establishes the long-running loop.

Example endpoint/product action:

`POST /api/v1/journeys/{journey_id}/operator/start`

Possible responsibilities:
- authenticate owner/member as appropriate;
- create/update a standing mission from a plain-language objective such as “Take care of this trip and protect my confirmed commitments”;
- bind requested autonomy;
- enable Guardian Autopilot;
- return the Operator projection.

Do not require the user to manually:
1. create mission,
2. start Guardian,
3. find policy,
4. start another worker.

Stopping Operator should disable future autonomous watch/recovery but preserve historical rows.

# 8. World Context experiment

Do not wait for random weather or a real closure.

The charter explicitly permits lab simulation when boundaries are clear.

For the one R43 product experiment, use **one clearly labelled provider/world-context lab disruption** if a naturally occurring real disruption is not available.

Requirements:
- the fact source must be explicitly SIMULATED/LAB_FIXTURE or equivalent;
- never call it LIVE_PROVIDER;
- it must enter through the normal World Context / Guardian sensing path, not by directly inserting a ReplanProposal or AgentRun;
- only one material incident;
- no “lottery” retries.

A product experiment proving the autonomous loop with honest simulated world truth is more valuable than waiting for random provider reality.

# 9. User-visible closed loop

The R43 acceptance criterion is not “rows exist.”

A normal user must be able to observe this sequence in the product:

1. Operator is ON and watching.
2. A disruption appears.
3. Operator says it is investigating.
4. External Agent chooses a recovery.
5. If authority is required, Operator asks once.
6. User approves once.
7. Existing continuation executes the exact pending action.
8. User sees the plan changed.
9. Operator says it is watching again.

If policy allows the chosen action autonomously, a separate deterministic test may cover that branch, but the single product closure should prefer the human-approval branch because it demonstrates the entire autonomy/authority handoff.

# 10. Group journeys

Do not make R43 a full collective-mediation project.

However, do not bypass existing collective authority.

If a recovery affects a collective Journey and existing gates require member mediation, Operator state should surface NEEDS_ATTENTION / WAITING_FOR_MEMBERS instead of pretending one owner approval is enough.

Future Revolution work can make multi-traveller Operator coordination a major product slice.

# 11. Authority boundary

Allowed autonomous activity before approval:
- sensing;
- World Context refresh;
- model reasoning;
- inspection;
- provider-backed fact acquisition allowed by current tools;
- generating recovery proposals;
- presenting a recommendation.

Allowed mutation only when existing Gateway policy says:
- ALLOW_AUTO, or
- required ActionApproval/collective authority is valid and consumed.

Forbidden:
- bypassing ActionApproval;
- changing AgentPolicy silently;
- treating a notification click as approval without auth;
- re-running the model after approval to choose a different action;
- applying a proposal other than the frozen pending action;
- fabricating world truth.

Keep `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`.

# 12. Focused tests

Tests exist to support the product loop. Keep them focused.

At minimum:

1. Operator start creates/reuses standing mission + Autopilot enrollment.
2. Operator OFF -> WATCHING after start.
3. material World Context incident -> INVESTIGATING / recovery lineage.
4. external Agent proposal requiring approval -> WAITING_FOR_APPROVAL.
5. Operator projection points to exact ActionApproval + AgentPendingAction.
6. approval notification dedupes.
7. authenticated approve consumes exact approval.
8. continuation executes exact frozen pending action without a second model call.
9. active plan changes to the Agent-selected plan.
10. stale approval CTA disappears.
11. Operator shows RECOVERED then WATCHING.
12. Autopilot remains enrolled after recovery.
13. one incident does not generate duplicate Agent recovery runs.
14. reject path leaves active plan unchanged and Operator returns to WATCHING/NEEDS_ATTENTION honestly.
15. collective authority is not bypassed.
16. product surface hides raw internal enums/tool traces by default.
17. R42 execution state remains valid after recovery where applicable.
18. TypeScript + focused Operator Playwright.

Do not rerun R34-R40 suites unless a specific regression blocks this loop.

# 13. One bounded R43 product closure

This is a product experiment, not a provider lottery.

Use one fresh Journey.

Set up through real product paths:
- active Journey;
- Operator ON via the new product action;
- standing objective / autonomy preference;
- existing plan and execution context as needed.

Use one clearly labelled lab World Context disruption if no natural live incident is available.

Then perform exactly one Operator incident loop:

1. Guardian senses the incident through the normal pulse path.
2. configured external Hermes/DeepSeek Agent runs.
3. Agent selects a recovery/proposal.
4. policy requires one human approval.
5. UI/API exposes one Operator approval.
6. authenticated traveller approves once.
7. existing continuation executes without a second Agent model run.
8. Operator returns to monitoring.

Valid outcomes:
- `OPERATOR_RECOVERED_AFTER_APPROVAL`
- `OPERATOR_AUTONOMOUSLY_RECOVERED`
- `OPERATOR_WAITING_FOR_COLLECTIVE_AUTHORITY`
- `OPERATOR_EXTERNAL_AGENT_BLOCKED`
- `OPERATOR_NO_FEASIBLE_RECOVERY`

A blocked external model is an honest experimental result.
Do not substitute deterministic fallback and call it success.

## Product proof to record

Keep one machine artifact for reproducibility, but do not turn it into the product.

Record:
- fresh Journey
- Operator start state
- incident source/provenance
- Guardian detection
- one AgentRun/model identity
- model-selected action/proposal
- approval requirement
- one user approval
- pending action identity before/after
- model call count before/after approval
- active plan before/after
- Operator timeline/state after recovery
- Autopilot still active
- authority boundary

Required artifact names:
- `REVOLUTION_R43_AUTONOMOUS_JOURNEY_OPERATOR_RESULT.md`
- `backend/output/r43-autonomous-journey-operator-v1.json`

Do not rerun the closure for a prettier outcome.

# Stop condition

Stop after one visible closed-loop product experiment.

Do not follow R43 with “R43.1 proof hardening” unless a defect genuinely blocks the next new capability.

## Revolution test

At the end, ask a non-developer:

> “What can CityNexus do now that it could not do before?”

The intended answer is:

> **“I can put it in charge of the trip. If something goes wrong, it notices, works out a recovery, asks me only when it needs permission, applies what I approved, and keeps watching.”**
