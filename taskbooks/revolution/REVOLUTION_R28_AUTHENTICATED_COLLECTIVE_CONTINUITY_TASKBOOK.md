# Revolution R28 — Authenticated Collective Continuity

## Why this exists

R27 made a real leap: a configured external Agent independently inspected a shared Journey, surfaced a true member trade-off, invoked `request_collective_decision`, waited for both relevant members, and reached the governed `accept_replan` boundary. Real provider facts, server-side fairness, member-specific preferences, a protected C4 commitment, and a real Gateway approval receipt are all evidenced.

But R27 must not be mythologized. Two closure claims are overstated:

1. The real GLM AgentRun did **not** itself consume the approved receipt and activate the proposal. AgentRun `590de0b7-ad8c-4467-ba99-345078cb44d5` ended with `Agent stopped a repeated tool request before another domain action.` The later successful consumption was a separate `citynexus-local-agent` gateway call (`r27-agent-approved-retry-0003`).
2. The so-called physical execution was an HTTP execution-state-machine exercise. The Journey was scheduled for 2026-10-08, while `depart/arrive/begin/complete` was recorded around 2026-10-05 JST. This proves runtime state transitions, not real-world physical presence.

R28 exists to remove those seams instead of adding another report layer.

### Important correction about the earlier external API strike

Do **not** treat the first failed WB2api / external-model attempt as an unresolved CityNexus product defect. The operator immediately retried the same API path after the failure, and the later strike succeeded on the real configured runtime. The first failure is consistent with transient external contention / concurrency / timeout while the API was already in use; it remains useful historical evidence of runtime variability, but it is **not** a reason for R28 to redesign the model provider, replace WB2api, widen fallbacks, or spend a round on API diagnosis.

Use the successful retry as the binding R27 capability evidence. Only touch provider/runtime reliability if a fresh R28 acceptance run reproduces a deterministic failure under controlled conditions.

## Revolution principle

Do not build an ORD/evidence treadmill. Do not spend the round re-proving R20–R27. Do not add another deterministic fallback that merely makes the demo look closed.

The product leap is:

> A shared Journey can pause for real humans, authenticate exactly which member answered, resume the originating Agent-controlled action causally after approval, and distinguish simulated execution from real-world execution truth.

The system should become more alive, not better at narrating itself.

## R28 primary outcome

Deliver one fresh end-to-end shared Journey showing all of the following on a single causal lineage:

- two independently authenticated Journey members;
- conflicting journey-scoped preferences;
- a real configured external Agent discovers the conflict without being handed proposal/member answers;
- server derives the collective decision and waits for the correct members;
- each decision response is bound to the authenticated caller principal and cannot impersonate the other member;
- the originating Agent mission enters a durable suspended state when `REQUIRE_CONFIRMATION` is returned;
- after a real authenticated user approval, the pending Agent action resumes automatically through the same durable continuation lineage — no ad-hoc `citynexus-local-agent` replay script and no manually assembled second tool call;
- the accepted proposal becomes active only after the authenticated approval is consumed;
- execution truth is explicitly labeled so an API simulation can never be reported as physical presence.

## P0 — Fix truth before adding features

### P0.1 Receipt/report consistency must be machine-derived

Create a closure verifier that reads the runtime DB and fails the build/package if any claimed fact disagrees with durable state.

At minimum verify:

- `agent_runs.status/outcome` vs the machine receipt wording;
- exact tool steps for every claimed AgentRun;
- approval `created_at/approved_at/consumed_at` ordering;
- actor identity that consumed the approval;
- proposal `PRESENTED -> ACCEPTED` transition and exact request that caused it;
- Journey active plan transition;
- planned activity timestamps vs actual execution timestamps;
- `transport_caller_principal_authentication` status.

Forbidden: hand-editing a receipt field such as `REQUIRE_CONFIRMATION_THEN_ACCEPTED` when the referenced AgentRun actually ended in `STOP_REPETITION`.

Recommended output: one generated `R28_MACHINE_VERDICT.json` with `PROVEN`, `NOT_PROVEN`, and `CONTRADICTED` fields.

### P0.2 Correct execution vocabulary

Introduce a durable execution-truth distinction. Minimum acceptable semantics:

- `SIMULATED_STATE_TRANSITION`
- `OPERATOR_CONFIRMED_EXECUTION`
- `DEVICE/LOCATION_VERIFIED_EXECUTION` only if real evidence exists

Do not call rapid API transitions against a future itinerary `physical execution`.

Any Journey/report/UI surface must preserve this distinction.

## P1 — Authenticated member principal boundary

R27 already proved server-side member state; now prove caller identity.

### Required behavior

For every collective response route and approval route:

- resolve an authenticated traveler/principal from the normal request authentication mechanism;
- map that principal to an in-force `JourneyMember` server-side;
- do not accept caller-supplied `member_id` as authority;
- reject a valid Journey member attempting to answer for a different member;
- reject a non-member;
- reject withdrawn/expired members;
- preserve OWNER/ADMIN/COLLABORATOR capability policy.

### Negative controls

Must include all:

1. OWNER token/session tries to submit ADMIN's response -> 403.
2. ADMIN token/session tries to approve an OWNER-only action -> 403 where policy requires OWNER.
3. random authenticated traveler -> 403.
4. unauthenticated caller -> 401.
5. stale/withdrawn member principal -> 403.
6. replay of an already-consumed approval -> 409/idempotent non-mutation.

No fake header-only identity if the product already has a real auth seam. If auth is genuinely absent, implement the smallest production-shaped principal abstraction first and label it honestly; do not claim internet-grade authentication until cryptographic/session verification actually exists.

## P2 — Durable human-in-the-loop Agent continuation

This is the heart of R28.

### Current defect to eliminate

R27 sequence:

- real GLM AgentRun asks `accept_replan`;
- Gateway returns `REQUIRE_CONFIRMATION`;
- real AgentRun later ends in repetition stop;
- user approves after the run is already over;
- a separate local-agent retry consumes approval and mutates state.

That is a stitched closure, not a continuous Agent lifecycle.

### Required state model

Add a first-class suspended continuation, for example:

- mission status: `WAITING_FOR_APPROVAL`;
- originating `agent_run_id` / continuation lineage id;
- pending tool name;
- canonical server-owned arguments/fingerprint;
- approval id;
- expiration;
- exact resume policy.

When `REQUIRE_CONFIRMATION` occurs:

1. persist the pending action atomically;
2. stop model spending immediately;
3. do **not** mark the mission as completed/no-action/repetition failure;
4. expose the approval to the correct authenticated human;
5. on approval, atomically resume the pending action using server-owned arguments;
6. consume the approval exactly once;
7. continue the same mission lineage and produce a final terminal outcome.

The resume should not require the model to rediscover/restate the exact same action unless product semantics truly require new reasoning. If the Agent already selected the proposal and the only missing fact was human approval, deterministic continuation is preferable and more trustworthy.

### Causal proof

The final evidence must allow one query to traverse:

`AgentRun -> pending action -> ActionApproval -> authenticated approver -> approval consumption -> proposal acceptance -> active PlanVersion`

No manually named `r27-agent-approved-retry-*` equivalent is allowed in the closure trace.

## P3 — Make the collective experience user-visible

Do not spend R28 only in backend tables.

Provide a minimal real product surface where two members can understand:

- why CityNexus is asking them;
- the two/three grounded choices;
- what each choice optimizes or sacrifices;
- whose response is still pending;
- whether the Agent is waiting on facts, members, or approval;
- what happened after agreement.

Avoid exposing raw internal matrices as UI. Translate server truth into concise human language.

A successful R28 demo should feel like a shared Journey coordinating people, not a database test harness.

## P4 — Execution truth, not fake physicality

The next demo may use simulated state transitions, but then label them as simulation.

If you want to claim **real-world execution**, require evidence tied to real time and real presence, such as a device/location or explicit operator confirmation captured at the moment of execution. Do not fabricate GPS or accelerate clock time.

For this round, an honest `SIMULATED_STATE_TRANSITION` closure is acceptable if P1–P3 are genuinely closed. Do not block the Revolution waiting for a person to physically travel to Nara.

## Product-level acceptance criteria

R28 is ACCEPTED only if all are true:

1. Fresh shared Journey, not the R27 SQLite snapshot.
2. Real external Agent runtime, not deterministic prose substitution.
3. At least two independently authenticated in-force members.
4. Distinct member preferences are read through normal product APIs.
5. Agent discovers/requests a true collective decision itself.
6. Server derives options and required members.
7. Principal-bound member responses pass; impersonation controls fail.
8. Agent mission durably suspends at approval instead of ending and being manually replayed.
9. Authenticated approval resumes the pending action automatically.
10. The exact selected proposal is accepted; non-selected proposal remains server-rejected.
11. C4/protected commitments remain protected.
12. Receipt generator agrees with DB on every claimed Agent outcome.
13. Execution is labeled truthfully as simulated or verified; no false “physical” wording.
14. Focused regression suite passes.
15. No authority/mainline merge unless separately instructed.

## Efficiency rules

- Spend no more than a small initial slice of the round on broad review. Start from R27 code SHA `2b1190ec56ae753093777a8891eaefb913316c8c` / delivery SHA `ab49ca066a0fead7949f9d4a99ab310c91b3361d`.
- Reuse the working collective/fairness/world-fact machinery. Do not rewrite R27.
- Prefer one production-shaped implementation over ten evidence scripts.
- The earlier first-call API failure was followed by a successful retry on the same real path; do not classify it as an open blocker or launch provider refactoring unless R28 reproduces it deterministically.
- Do not rerun external providers repeatedly unless required by a failing acceptance criterion.
- Do not widen the scope into another city/source-research expedition unless the fresh R28 Journey genuinely lacks grounded candidates.
- Keep `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`.
- Do not weaken Gateway, member fairness, C4, or live-provider truth boundaries to make the demo pass.

## Required delivery

Return one package containing:

- `REVOLUTION_R28_AUTHENTICATED_COLLECTIVE_CONTINUITY_RESULT.md`
- generated `R28_MACHINE_VERDICT.json`
- focused test output
- substantive code diff from R27 code SHA
- bounded replay instructions
- disposable fresh runtime DB with no credentials
- one concise UI capture/receipt if the member decision surface was implemented

The report must explicitly separate:

- **Agent reasoning proven**
- **authenticated human decision proven**
- **automatic continuation proven**
- **Gateway mutation proven**
- **execution simulation proven**
- **real-world physical execution proven/not proven**

## Final instruction to Codex

Do not optimize for the sentence “R28 closed.” Optimize for removing the seam that made R27 need a stitched story.

R27 taught CityNexus to mediate a group. R28 must teach it to **wait for real people, know who answered, and continue its own work afterward without a human operator secretly finishing the Agent's job**.
