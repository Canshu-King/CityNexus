# GPT external check — R26 behavioral closure

Reviewed:
- uploaded `REVOLUTION_R26_DECISION_CRITICAL_CLARIFICATION_RESULT.md`;
- remote implementation commit `2aaea4adf57b61f767b79a9560770df4056864b5`;
- report-binding head `3a39abefd9dc86bce71de790bd855f83265e969c`;
- clarification endpoint, child-mission resume, DEFER Gateway validation, execution skip/state-machine code, and R26 focused tests.

## Verdict

R26 contains a genuine new capability, but the published result overstates behavioral closure.

### What is genuinely proven

The implementation proves:
- server-owned decision-sensitivity receipt;
- `CLARIFICATION_REQUIRED` is accepted only when the server derives two feasible competing options;
- model cannot invent authoritative option IDs;
- mission enters `WAITING_FOR_USER`;
- answer is checked against a decision-epoch fingerprint;
- `TAKE_LATER` becomes journey-scoped `CURRENT_EXPLICIT_MISSION`;
- parent mission becomes ANSWERED;
- child mission inherits/widens no authority;
- real Hermes-compatible model resumes;
- child Agent sees the explicit answer and can produce a server-valid `DEFER` conclusion;
- stale/factual-unknown boundaries exist.

This is a real Revolution step: the system can distinguish a human-value question from missing provider facts.

### Behavioral contradiction in the current result

The report states:
- W1 Todaiji Museum = 800 JPY;
- W2 Isuien Garden = 1200 JPY;
- optional budget = 1800 JPY;
- combined cost 2000 > 1800;
- user answered `TAKE_LATER`;
- child mission concluded `NO_ACTION + DEFER`.

But the same report then states that normal execution completed:

`Nara Park -> Todaiji Museum -> Isuien Garden`.

Therefore the final physical execution did not reflect the clarified `TAKE_LATER/DEFER` choice.

Current code explains why:
- `answer_journey_clarification()` persists explicit preference and creates a child mission;
- `conclude_recovery(... horizon_decision="DEFER")` validates a non-mutating conclusion;
- neither path changes Activity execution state;
- the active plan remains unchanged;
- ordinary execution therefore continues through W1 and W2.

So R26 currently proves:
> ask the right question and persist the answer

more strongly than:
> the answer changes what the traveler actually does.

Do not open R27 until this gap is closed.

## Existing product primitive to reuse

CityNexus already has the real product route:

`POST /api/v1/journeys/{journey_id}/activities/{activity_id}/skip`

It already:
- rejects protected C3/C4;
- rejects locked authoritative activities;
- marks Activity SKIPPED;
- records ACTIVITY_SKIPPED;
- advances the cursor;
- keeps active PlanVersion unchanged.

Do not build a new execution engine.

## Important truth-boundary caveat

A naive W1 skip can change the actual adjacency.

Example:
`Park -> Museum -> Garden`
becomes
`Park -> Garden`.

The frozen active-plan mobility evidence may not contain the new direct edge.

Therefore a clarified defer may not simply call `skip_activity` and then depart.

Before committing the skip on an authoritative execution plan:
- derive the actual execution origin;
- capture/revalidate the direct live provider route to the next non-skipped activity;
- persist a bounded execution mobility override/receipt without mutating the frozen PlanVersion evidence;
- block the skip/depart if the new actual edge cannot become hard eligible.

This keeps the R15+ truth boundary intact.

## Best closure fixture

Ask the clarification when W1 is the CURRENT optional Activity, not one activity too early.

Sequence:
1. execute the prefix normally until W1 becomes current but has not departed;
2. run the decision-critical mission comparing current W1 vs later W2;
3. user answers TAKE_LATER;
4. child Agent applies the clarified choice;
5. server skips W1 and advances directly to W2 with a fresh live actual-edge receipt;
6. execute W2;
7. Journey COMPLETED.

This avoids creating a separate future-intent scheduler just to remember a skip.

## R26 success correction

R26 C/D should require a physical divergence between opposite human answers.

TAKE_LATER:
- W1 status = SKIPPED;
- W1 consumed optional cost = 0;
- W2 executes.

TAKE_NOW:
- W1 executes;
- its real consumed resource is reflected;
- later strategy responds to the remaining resource.

The same hard facts should not end with identical execution histories.

## Test gap

The current R26 file has only three focused tests and none prove:
- answer -> execution mutation;
- DEFER cannot close as NO_ACTION while W1 later executes;
- post-skip live route truth;
- opposite answers yield different execution histories.

Add these directly, then run the focused lineage once.
