# REVOLUTION R45 — Collective Journey Operator

## Product-direction gate

This task is governed by `REVOLUTION_LAB_PRODUCT_DIRECTION_CHARTER.md`.

The required product answer is:

> **CityNexus newly learns to manage a shared trip disruption with multiple travellers: identify who is affected, gather each relevant person's choice, mediate disagreement when needed, wait for real collective authority, apply the agreed recovery, and keep operating the Journey.**

If implementation turns into replaying old R27/R29 proof or building another developer-only collective dashboard, stop and correct course.

## Starting truth

R44 is complete at `f53a860c9d451e4d0f67851077bfedfd54ebf6e5`.

R44 proved:
- Operator brain outage is fail-closed;
- blocked recovery preserves the same Event, GuardianRun, RecoveryEpoch, standing mission and Autopilot enrollment;
- bounded resume and safe zero-tool handoff work;
- no deterministic fallback is used.

Do not rerun R33-R44 historical closures.

## Existing capabilities to connect — do not reimplement

The repository already has:
- JourneyMember + role/capability model;
- authenticated member principals;
- collective trade-off clarification;
- per-member responses;
- WAITING_FOR_MEMBERS;
- unanimous collective resolution;
- mediation mission on disagreement;
- CollectiveAuthorityReceipt;
- collective mutation preflight;
- R43 Journey Operator;
- R44 resilient Operator brain;
- approval continuation;
- Guardian / World Context / RecoveryEpoch.

R45 is valuable only if these become one user-visible multi-traveller Operator experience.

## 1. Operator becomes member-aware

Extend the Journey Operator projection with a `collective` section when the current recovery affects multiple in-force members.

Suggested states:

- `SINGLE_TRAVELLER`
- `WAITING_FOR_MEMBERS`
- `MEDIATING`
- `COLLECTIVE_READY`
- `COLLECTIVE_AUTHORIZED`
- `COLLECTIVE_STALE`
- `COLLECTIVE_NEEDS_ATTENTION`

Example:

```json
{
  "collective": {
    "state": "WAITING_FOR_MEMBERS",
    "required_count": 3,
    "response_count": 1,
    "viewer_has_responded": false,
    "members": [
      {"display_name": "Alice", "responded": true},
      {"display_name": "Bob", "responded": false}
    ],
    "options": [...]
  }
}
```

Do not expose raw clarification JSON by default.

## 2. One shared Operator loop

For a collective Journey disruption:

1. Guardian detects one material incident.
2. external Agent reasons in Journey context.
3. Agent requests recovery.
4. server determines a collective trade-off exists.
5. Operator state becomes `WAITING_FOR_MEMBERS`.
6. each relevant authenticated member sees the same recovery context but their own response state.
7. member responses go through the existing collective clarification endpoint.
8. if members converge, server issues/uses the existing collective authority path.
9. if they disagree, Operator becomes `MEDIATING` and the existing mediation mission runs through the external Agent.
10. once authority exists, execution continues through existing Gateway/continuation.
11. Operator returns to WATCHING for everyone.

Do not create a parallel "group operator" runtime.

## 3. Member-specific UX

Each in-force member should see:
- what changed in the trip;
- why CityNexus is asking them;
- the candidate recovery choices;
- who has responded;
- whether they personally still need to respond;
- what happens next.

A member must never answer for another member.

If traveler auth is configured, the server resolves the authenticated member and ignores caller attempts to impersonate a different member.

Ordinary copy:

> “A closure affects the group. CityNexus needs 3 travellers to choose before it can change the shared plan.”

After response:

> “Your choice is recorded. Waiting for 1 traveller.”

## 4. Mediation as a product experience

Disagreement is not a failure.

When different members select different grounded proposals:
- Operator state = `MEDIATING`;
- external Agent receives the existing member-scoped preferences and candidate evidence;
- model must seek a grounded compromise rather than majority-vote a winner;
- if a new collective decision is required, Operator presents a fresh round.

User copy:

> “You don’t all want the same recovery. I’m looking for a compromise that protects everyone’s important constraints.”

Do not expose "R29 mediator" language.

## 5. Collective authority is the mutation boundary

Do not let:
- owner approval;
- majority response;
- one member's preference;
- Operator autonomy mode

bypass existing `CollectiveAuthorityReceipt` / collective preflight.

For a shared recovery, mutation is allowed only when existing server collective authority rules say it is allowed.

If authority becomes stale because world facts or candidate surface changed:
- Operator shows `COLLECTIVE_STALE`;
- do not apply the old plan;
- if appropriate, external Agent can open a new bounded collective decision under the new recovery reality.

## 6. R44 brain resilience applies to collective work

If the external Agent fails during collective mediation:
- preserve the collective mission/clarification/recovery lineage;
- R44 brain state explains the outage;
- do not lose member responses;
- resume safely when the brain is available again.

Do not reset the collective round just because the model runtime failed.

## 7. Operator timeline

The normal Operator timeline should support collective moments:

- “Closure detected”
- “CityNexus found 2 recovery options”
- “Waiting for 3 travellers”
- “Alice responded”
- “Bob responded”
- “Group choices conflict”
- “Looking for a compromise”
- “New compromise ready”
- “All required travellers agreed”
- “Shared plan updated”
- “Watching again”

Source these from durable mission/member/authority/audit rows.

## 8. Notifications

Reuse NotificationEvent.

Per relevant member, create at most one deduped notification per collective decision epoch:

> “The shared trip needs your choice.”

Do not notify uninvolved members.

Do not send a new notification on every Guardian pulse.

If a new collective decision epoch opens because the old one became stale, a new notification is legitimate.

## 9. Operator start semantics

"Take care of this trip" on a shared Journey should start one Journey-level Operator, not one independent Operator per traveller.

Every member views the same underlying Journey Operator state with a viewer-specific projection.

Do not create duplicate standing missions because two members open the screen.

## 10. One-click response

Keep the current collective response endpoint as authority backend, but make the Operator UI the normal interaction surface.

Each candidate option should show ordinary consequences:
- schedule impact;
- protected commitments;
- relevant places;
- cost/loss if grounded;
- member-specific fit when available.

No raw proposal IDs in the main UI.

## 11. External model owns mediation judgment

For disagreement, external Hermes/DeepSeek must own compromise reasoning.

The server owns:
- candidate facts;
- member identity;
- authority;
- feasibility;
- mutation.

Do not replace disagreement mediation with:
- majority vote;
- owner override;
- deterministic first-option selection.

If external brain is unavailable:
- preserve state through R44;
- valid result may be `COLLECTIVE_OPERATOR_BRAIN_BLOCKED`.

## 12. Focused tests

Only tests needed for the visible loop:

1. shared Journey Operator start creates one standing mission/enrollment.
2. collective incident -> WAITING_FOR_MEMBERS.
3. viewer projection shows only real in-force required members.
4. authenticated member cannot answer for another member.
5. one response updates response_count without mutating plan.
6. unanimous responses progress toward existing collective authority path.
7. disagreement -> MEDIATING rather than majority winner.
8. mediation external-model outage preserves member responses through R44.
9. collective authority receipt is required before mutation.
10. owner-only approval cannot bypass missing member authority.
11. stale collective epoch refuses mutation.
12. successful collective recovery updates one shared active plan.
13. all viewers converge back to WATCHING.
14. notifications dedupe per member/decision epoch.
15. TypeScript + focused Collective Operator Playwright.

Do not rerun R27/R29 historical proof suites unless a specific defect blocks this product loop.

## 13. One bounded R45 product experiment

Use one fresh shared Journey with at least 2 authenticated/in-force members.

Use one clearly labelled LAB_FIXTURE material disruption through normal Guardian sensing.

Run one collective Operator loop:

1. Operator ON.
2. incident detected.
3. external Agent produces grounded recovery choices.
4. collective decision becomes WAITING_FOR_MEMBERS.
5. member A responds once.
6. member B responds once.

Prefer a deliberate disagreement in the lab product experiment if the existing candidate surface naturally supports two meaningful choices, because that proves the new capability:
- disagreement -> MEDIATING;
- external Agent produces/chooses a grounded compromise or opens a fresh round;
- required members respond;
- collective authority is issued;
- shared plan mutates once;
- Operator returns to WATCHING.

Do not hand-write mediation output.

If external Agent is unavailable, preserve state and report honestly.

Valid outcomes:
- `COLLECTIVE_OPERATOR_RECOVERED`
- `COLLECTIVE_OPERATOR_MEDIATED_AND_RECOVERED`
- `COLLECTIVE_OPERATOR_WAITING_FOR_MEMBERS`
- `COLLECTIVE_OPERATOR_BRAIN_BLOCKED`
- `COLLECTIVE_OPERATOR_NO_COMPROMISE`

Do not rerun for a prettier outcome.

## Stop condition

Stop after one visible multi-traveller Operator experiment.

The end-user capability must be obvious:

> **“When our shared trip hits a problem, CityNexus coordinates the people affected, asks each of us only for the choice it needs, mediates when we disagree, waits for real group authority, updates the trip, and keeps managing it.”**
