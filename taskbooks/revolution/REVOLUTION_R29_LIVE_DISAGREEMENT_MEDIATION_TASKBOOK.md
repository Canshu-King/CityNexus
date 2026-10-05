# Revolution R29 — Live Disagreement Mediation

## Revolution thesis

R28 closed the identity/continuation seam: CityNexus can wait for multiple signed Journey principals, preserve their decision as server truth, let the real external Agent reach the approval boundary, and resume the same pending action after authenticated approval.

But one product dead end remains:

> if relevant members choose different grounded proposals, the system stops at `UNRESOLVED_DISAGREEMENT`.

That is not a group-travel agent. It is a ballot collector.

R29 teaches CityNexus to **mediate real disagreement without majority voting, authority laundering, preference rewriting, or endless re-asking of the same question**.

## Binding branch and GPT relay

Branch:

`gpt/revolution-r29-disagreement-mediation`

GPT has already implemented the first product slice:

- `d339ae4bf1fc0fe1e2fe1cfe305f750b79286c14` — disagreement creates a mediator child mission instead of terminating;
- `2374d7dcd429d3ecea5d1c760650e5d86318633e` — external Agent is explicitly constrained to mediate, never majority-vote or pick a winner, and cannot finish with prose alone;
- `b058415ca969777954adcaecd04ae5340aa55af2` — mediator authority boundary tests;
- `c3c1e8aa11efb42ef281f13f8fbaa48d810d4086` — traveler UI exposes live mediation and automatic continuation;
- `271d015e91bed03d8672b1cd071f23321013876a` — mediator child inherits the parent mission's already-bounded authority envelope instead of collapsing to compiler-default zero ceilings.

R28 remains closed on its own branch. Do not reopen R28 unless an R29 test finds a genuine shared regression.

## Product behavior already intended

When all required responses arrive and the selected proposal IDs differ:

1. parent collective mission becomes `ANSWERED`;
2. clarification becomes `MEDIATION_REQUIRED`;
3. server creates a child mission with:
   - `resolved_intent.collective_mediation.kind = DISAGREEMENT_MEDIATION`;
   - the decision epoch;
   - required member IDs;
   - each member's proposal choice;
   - the previous candidate proposal IDs;
   - mediation round number;
4. no proposal receives authority;
5. UI tells members the Agent is mediating;
6. normal child-mission resume invokes the configured Agent;
7. Agent must use tools, not prose, to advance.

## The hard R29 rule

A mediation round is successful only if it changes the decision surface.

Forbidden:

- asking the same two proposals again with new prose;
- majority voting;
- OWNER wins because OWNER is privileged;
- averaging preferences into a fake group preference;
- silently changing JourneyMember preferences;
- accepting either disputed proposal before a later collective round resolves it;
- inventing a "compromise" without grounded world/mobility/feasibility evidence.

Required before a fresh collective round:

> At least one candidate option must be materially new compared with the disputed round, and the server must be able to explain why it improves the worst-member outcome or removes an unacceptable-member condition.

If no such candidate can be grounded inside the mission envelope, the Agent must terminate the mediation attempt as machine-visible `UNRESOLVED` with the exact blocker. That is better than looping.

## Codex Phase 1 — local gate on GPT implementation

Start here only:

```bash
git fetch origin
git checkout gpt/revolution-r29-disagreement-mediation
git reset --hard origin/gpt/revolution-r29-disagreement-mediation
git rev-parse HEAD
git status --short

cd backend
python -m compileall -q app
python -m pytest -q tests/test_r29_disagreement_mediation.py
```

Then run the existing R28 principal/continuation focused suites because R29 sits directly on those seams:

```bash
python -m pytest -q \
  tests/test_r28_authenticated_member_principal.py \
  tests/test_r28_durable_approval_continuation.py
```

Frontend:

```bash
cd ../frontend
npm run typecheck
npm run build
```

Fix real defects directly on this branch. Do not spend a pass reviewing unrelated history.

## Codex Phase 2 — add the missing disagreement integration test

Add a focused backend test that proves the HTTP route, not only helper functions.

Minimum scenario:

- fresh active shared Journey;
- two in-force signed members;
- two server-derived `GROUNDED_FEASIBLE` collective proposals;
- OWNER chooses proposal A;
- ADMIN chooses proposal B.

Required assertions after the second response:

- response status = `MEDIATION_REQUIRED`;
- `child_mission != null`;
- parent mission = `ANSWERED`;
- no ReplanProposal became `ACCEPTED`;
- active PlanVersion unchanged;
- child has `collective_mediation.kind == DISAGREEMENT_MEDIATION`;
- child contains both member choices;
- child contains no `selected_proposal_id`;
- child authority ceilings/protected/mutable/action-class envelope equal the parent mission and are not widened;
- audit `agent.collective_decision.mediation_started` exists;
- baseline TravelerTwin/JourneyMember preferences unchanged.

Negative authority assertion:

- trying to route an old disputed proposal directly into `accept_replan` through the mediator mission must not gain authority merely because the mediation child exists.

## Codex Phase 3 — prevent questionnaire loops

This is the main implementation work still open.

Before `request_collective_decision` may create round N+1 from a mediation child, add a server-owned mediation-progress gate.

Recommended durable facts:

- source clarification/decision epoch;
- previous proposal IDs and compact option shapes;
- previous per-member fits/fairness;
- new proposal IDs and shapes;
- worst-member score before/after where available;
- unacceptable-member set before/after;
- reason why the new surface is materially different.

A fresh round is allowed only if one of these is machine true:

1. a new grounded candidate shape is present that was absent in the previous round; and
2. it improves the worst-member/fairness boundary or introduces a genuinely different compromise dimension;

or

3. prior world facts changed materially, making an old shape meaningfully different now.

If the option surface is effectively identical, return a typed refusal such as:

`MEDIATION_NO_PROGRESS`

Do not reopen `WAITING_FOR_MEMBERS`.

## Codex Phase 4 — mediator completion semantics

For a mediator child, valid terminal paths are only:

### A. Fresh round

`request_collective_decision -> WAITING_FOR_MEMBERS`

with the progress gate above proven.

### B. Honest unresolved

`conclude_recovery(outcome=UNRESOLVED)`

with a bounded blocker such as:

- no new grounded candidate;
- every compromise violates one member's unacceptable boundary;
- C4/budget/mobility envelope leaves no feasible compromise;
- world facts insufficient and acquisition budget exhausted.

The Agent must not emit a successful terminal prose-only answer.

## Codex Phase 5 — UI contract

Extend the R28 Playwright surface rather than redesigning the app.

Add R29 coverage proving:

1. after the second conflicting response, the UI says the travelers disagree and CityNexus is mediating;
2. it does not show either prior option as "winner";
3. mediator child can auto-resume;
4. if mediation reaches a fresh member round, UI shows the new N/M decision surface;
5. the new option set visibly differs from the prior one;
6. if mediation is `UNRESOLVED`, UI says why instead of pretending a choice was made.

Keep 360/390/412 px usable.

## Codex Phase 6 — one real external-Agent strike

Only after focused gates are green.

Use a fresh disposable DB and the normal working WB2api/Hermes-compatible chain.

Set up two authenticated members with deliberately conflicting journey-scoped preferences and a protected C4 commitment.

Run:

1. real Agent discovers material trade-off;
2. round 1 returns to members;
3. OWNER and ADMIN deliberately choose different options;
4. server creates mediator child;
5. real external Agent resumes mediator child;
6. Agent searches/replans through normal tools;
7. either:
   - produces at least one materially new grounded compromise and opens round 2; or
   - honestly terminates `UNRESOLVED` with machine-grounded blocker.

For the preferred PROVEN path, choose a scenario where a real compromise exists.

Round 2:

- both authenticated members choose the new compromise;
- server creates the normal resolved child;
- external Agent reaches `accept_replan`;
- approval boundary suspends the same AgentRun;
- signed authorized approval auto-resumes;
- proposal becomes active exactly once.

Do not hand the Agent proposal IDs, member answers, or a tool sequence.

## R29 machine verdict

Add `backend/scripts/r29_machine_verdict.py`.

It must derive from durable DB state and fail unless all are true:

- two distinct authenticated principals disagreed in round 1;
- no round-1 disputed proposal was accepted;
- mediator child exists on the causal lineage;
- real configured external Agent ran the mediator child;
- fresh round has material option-surface progress;
- no majority/role override evidence;
- member preferences unchanged by mediation;
- round 2 responses are authenticated;
- selected compromise is the exact proposal later accepted;
- approval continuation remains same-run/exactly-once using the R28 invariant;
- C4 remains preserved;
- execution truth remains honestly labeled.

Output:

`R29_MACHINE_VERDICT.json`

No hand editing.

## Deliverable

Commit:

- `REVOLUTION_R29_LIVE_DISAGREEMENT_MEDIATION_RESULT.md`
- generated `R29_MACHINE_VERDICT.json`
- focused backend/frontend tests;
- any required product code;
- bounded replay instructions.

Do not commit credentials, bearer tokens, local secret config, or disposable DBs.

## Stop condition

R29 is closed only when CityNexus can show:

> two authenticated travelers genuinely disagree; the Agent does not choose a winner; it creates a materially better grounded decision surface; the humans then converge; and the already-proven R28 approval continuation completes the chosen compromise.

If no grounded compromise exists, a truthful machine-visible `UNRESOLVED` is a valid product outcome but not the preferred R29 PROVEN demo path.

Do not open R29.1, Checkpoint D, or another evidence treadmill.

The next Revolution is **better group intelligence**, not more receipts.
