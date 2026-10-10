# Revolution R64 — Member-Owned Side Quest Execution

## Why this strike exists

R63 made a planned temporary split a first-class, member-scoped product concept. That was important, but the separated traveller still mostly has a label plus a return/rendezvous projection.

R64 must turn that temporary split into something the traveller can actually *do*.

A member who intentionally leaves the group should be able to start a private, member-owned side quest, execute it, and then return toward the shared rendezvous — while the shared Journey remains the single authoritative group plan.

This is a user-facing capability strike, not a verifier/evidence strike.

## Product promise

During an active shared Journey, an authenticated in-force member with an active `PLANNED_SEPARATION` may create and execute one personal side quest.

The side quest:

- belongs only to that member;
- may point at a concrete known Place, but is **not** inserted into the shared active PlanVersion;
- has its own lightweight execution state;
- can be started, arrived, completed, or cancelled by that member only;
- keeps the shared rendezvous visible throughout;
- hands back into the existing R63 return-to-rendezvous projection after completion/cancellation;
- exposes only privacy-safe summary information to other group members.

The group must never acquire a second active PlanVersion or a second shared execution cursor because one member temporarily goes elsewhere.

## User experience

### Separated traveller

While R63 planned separation is active, show a clear private side-quest card in Journey Live.

Minimum useful flow:

1. Traveller chooses/declares a side destination.
2. Server resolves it to an existing exact Place when possible.
3. Traveller confirms: “Go here before I rejoin at <shared rendezvous>.”
4. Side quest becomes `READY`.
5. Traveller can `START` it.
6. Traveller can report authenticated `ARRIVE`.
7. Traveller can `COMPLETE` or `CANCEL`.
8. After completion/cancellation, the product immediately foregrounds the return-to-rendezvous state from R63.

The side-quest card should always show:

- private destination title/place to its owner;
- current side-quest state;
- shared rendezvous place/time;
- return status from R63 when available;
- a plain statement that the shared Journey has not been changed.

### Other members

Other members should see only a privacy-safe summary, for example:

- “Alice is on a planned personal stop.”
- shared rendezvous and return-risk state;
- whether Alice is still away / returning / side quest finished.

Do **not** reveal the side destination name, exact coordinates, personal note, or route to other members by default.

If the existing product already has an explicit group-sharing permission primitive that is demonstrably applicable, it may be reused. Do not invent a new permission framework for R64.

## Authority and identity

All writes are member-bound.

The server must derive the acting traveller/member from the authenticated principal. It must not trust request-body traveller/member ids.

Only the owner of the side quest may:

- create/replace it;
- start it;
- mark arrival;
- complete it;
- cancel it.

An admin/collaborator may observe only the privacy-safe projection unless existing authority explicitly grants more.

A removed/expired member cannot create or advance a side quest.

## Canonical relationship to R63

R64 depends on a currently active, active-plan-bound R63 `PLANNED_SEPARATION`.

If the R63 planned separation expires, is cancelled, is superseded, its rendezvous becomes terminal, or its bound PlanVersion is no longer active:

- the personal side quest must cease to be executable;
- preserve it as durable history;
- do not silently retarget it to a new shared plan;
- do not claim the member physically rejoined.

If a new planned separation is later created, it gets a new side quest or an explicit user action to re-establish one.

## Data model guidance

Prefer a small durable member-owned execution object over encoding a complex state machine only inside UI state.

A new focused model/table is acceptable if it materially simplifies correctness, e.g. `MemberSideQuest`.

Minimum durable fields should cover:

- id
- journey_id
- member_id
- traveler_id
- planned_separation_intent_id
- active_plan_version_id
- rendezvous_activity_id
- side_place_id when exact place is resolved
- side_title / user description
- destination_authority
- state
- created_at / started_at / arrived_at / completed_at / cancelled_at / updated_at

Suggested states:

- `READY`
- `EN_ROUTE`
- `ARRIVED`
- `COMPLETED`
- `CANCELLED`
- `INVALIDATED`

Do not overload the shared Activity state machine or create fake shared Activities just to reuse endpoints.

Exactly one nonterminal side quest per member/planned-separation is enough for R64.

## Destination resolution

The product must distinguish:

1. **EXACT_KNOWN_PLACE** — server can bind to an existing Place.
2. **DESCRIPTIVE_ONLY** — user named somewhere, but it is not a trustworthy canonical Place.

Only `EXACT_KNOWN_PLACE` should become a navigable canonical destination.

For `DESCRIPTIVE_ONLY`:

- preserve the user’s text;
- do not fabricate coordinates;
- do not fabricate a provider route;
- UI may ask the member to choose an exact known place.

Do not make live external place search mandatory for this strike.

## Execution truth

Side-quest execution events are authenticated product execution truth, not proof of physical presence.

If existing Journey execution endpoints have a clean reusable receipt mechanism, reuse the semantics carefully. Otherwise add narrow member-side-quest endpoints.

Minimum commands:

- create/replace
- start
- arrive
- complete
- cancel

Idempotent repeats must not create duplicate transitions/audit rows beyond the project’s normal idempotency semantics.

Reject impossible transitions, e.g.:

- READY -> COMPLETE
- COMPLETED -> ARRIVE
- another member advancing someone else’s quest

Do not set any `physical_presence_verified`-style claim solely from these commands.

## Return handoff

The side quest does not own a second recovery system.

After `COMPLETE` or `CANCEL`:

- R63 planned separation remains active unless the user explicitly ends it or the rendezvous scope expires;
- the UI switches emphasis from the personal destination to “return to shared rendezvous”;
- existing R63 route/authority logic remains the only path for return ETA and return-risk escalation;
- only trusted member location + exact live provider route may trigger the existing Guardian/recovery boundary, exactly as R63 requires.

A completed side quest with no route evidence should truthfully show `RETURN_UNKNOWN`, not invent an ETA.

## Shared-plan invariants

R64 must prove by construction and focused tests:

- active PlanVersion id remains unchanged for normal side-quest operations;
- PlanVersion count does not increase;
- no shared Activity is inserted for the private stop;
- no ReplanProposal is created simply because a side quest exists;
- no collective approval is required merely to create/execute the private side quest;
- if return risk later requires shared-plan mutation, use the existing collective recovery path.

## Privacy projection

Owner projection may include:

- destination title/place;
- side-quest state/timestamps;
- personal route context if available;
- rendezvous;
- return state.

Non-owner projection should include only:

- member display name;
- `planned_personal_stop: true`;
- coarse state such as `AWAY`, `RETURNING`, `FINISHED`;
- shared rendezvous;
- return-risk state when it affects the shared commitment.

Do not expose exact side destination or coordinates in group projection by default.

Add a regression test that explicitly searches the non-owner JSON/UI for the private place string and confirms it is absent.

## UI requirements

Extend the existing Journey Live surface rather than making a separate demo page.

Owner:

- side-quest card
- create/choose destination
- Start / I arrived / Done / Cancel controls as appropriate
- shared rendezvous always visible
- return state visible after finish/cancel

Other member:

- privacy-safe status only

Important: R64 Playwright should exercise the real product mutation API for the side-quest lifecycle. Mocking unrelated read surfaces is acceptable if needed, but do not mock the R64 write lifecycle itself.

## Required focused tests

Backend tests should cover at least:

1. authenticated member creates own side quest bound to active R63 separation;
2. body spoofing cannot create for another member;
3. second member may own their own independent side quest;
4. non-owner projection does not leak private destination;
5. exact known Place binds; descriptive-only does not fabricate coordinates;
6. READY -> EN_ROUTE -> ARRIVED -> COMPLETED works;
7. invalid transition rejects;
8. duplicate command is idempotent or safely rejected according to existing convention;
9. completion does not end R63 planned separation or claim reunion;
10. R63 cancellation/expiry/active-plan change invalidates execution without retargeting;
11. active PlanVersion and PlanVersion count remain unchanged;
12. no proposal/approval/recovery mutation on ordinary side-quest execution;
13. completed quest + no route evidence => truthful `RETURN_UNKNOWN`;
14. trusted live return risk still hands into the existing R63/R57/R60 recovery path, not a new one.

Frontend / Playwright:

- two authenticated browser contexts;
- owner runs the real R64 create/start/arrive/complete lifecycle;
- collaborator sees safe away/returning status but never the private place string;
- owner sees rendezvous and eventual return emphasis;
- no second shared plan appears;
- no fake physical-reunion success text appears.

## Bounded experiment

Use a fresh isolated SQLite DB and normal product APIs.

A good bounded result is:

- two-member active Journey;
- one active PlanVersion;
- member A creates an active R63 planned separation;
- member A chooses an existing exact Place as a private side quest;
- member A starts, arrives, completes;
- member B can observe only privacy-safe status;
- shared PlanVersion remains unchanged;
- after completion the owner sees return-to-rendezvous state;
- if no live route provider is used, `RETURN_UNKNOWN` is an acceptable and preferred truthful result.

No external Agent/provider call is required for R64 closure.

If a live provider happens to be used, report it precisely, but do not retry merely to manufacture a “better” result.

## Do not do

- Do not rerun R58–R63 historical strike campaigns.
- Do not build another verifier.
- Do not add a second shared PlanVersion.
- Do not add a parallel shared Journey.
- Do not model the private stop as a fake shared Activity.
- Do not expose the private destination to the group by default.
- Do not make live provider success a pass/fail requirement.
- Do not invent ETA/location/physical presence.
- Do not start a fresh Agent run solely for evidence.
- Do not spend the strike polishing result-doc provenance while the user-facing lifecycle is incomplete.

## Definition of done

R64 is done when a real authenticated member can use the normal product UI/API to execute a private temporary side quest during a planned group split and then transition back toward the shared rendezvous, with:

- one authoritative shared PlanVersion;
- member-bound execution;
- privacy-safe group visibility;
- truthful evidence boundaries;
- existing R63 return-risk/recovery handoff reused;
- focused tests green.

The result document should be short and factual. The product capability is the deliverable.
