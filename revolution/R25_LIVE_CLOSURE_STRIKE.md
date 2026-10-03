# Revolution R25 — Live Closure Strike

## Objective

Turn the implemented Strategic Horizon Steward into a machine-proven runtime capability.

The defining proof is:

```text
W1 exists and is genuinely feasible
  -> W2 also exists and is genuinely feasible
  -> scarce shared resource means both cannot be taken
  -> W2 has higher truthful adaptive value
  -> real Agent deliberately leaves W1 empty
  -> no hidden reservation / no plan mutation at W1
  -> execution advances
  -> W2 becomes current
  -> current facts and live mobility are revalidated
  -> normal F4/Gateway path activates W2
  -> added experience executes
  -> protected commitments survive
  -> Journey COMPLETED
```

Do not add a new R26 capability until this machine fact exists.

## Phase 0 — bind source first

In the existing local experiment worktree:

```bash
git rev-parse HEAD
git show --stat --oneline 26b5139b
git show --stat --oneline 2a4b53a3daf958de939abec0beeb5bc453d27d3e
git merge-base --is-ancestor dc93b91db9878690465349c4c2f76888870b6f49 HEAD
git status --porcelain
```

Expected:
- R25 final commit exists locally;
- base is an ancestor;
- no accidental unrelated work.

Then fast-forward push the experimental branch.

Verify remote head after push.

Do not rebase/cherry-pick unless fast-forward unexpectedly fails.

## Phase 1 — machine-grade external timeout

Before the live run, make external model timeout observable.

Requirements:
- AgentRun RUNNING row exists durably before the first external model request;
- a server-owned request timeout applies to Hermes-compatible completion;
- timeout becomes a persisted run state, e.g. `FAILED_EXTERNAL`;
- reason code/message names model timeout rather than generic missing configuration;
- provider/model/elapsed time are retained;
- mission is not misreported as NO_ACTION/DEFER.

Keep this narrow.

## Phase 2 — create a fresh two-window real Journey

Discard the one-window sampled Journey.

Use normal product APIs and real provider-backed Nara catalog rows.

Construct:
- an ACTIVE Journey;
- a current executable activity;
- future protected anchor A;
- later protected anchor B;
- enough slack to derive W1 before A and W2 before B.

No direct DB mutation for the final proof.

Experiment setup may choose known Nara Places, but production code must contain no Nara-specific names.

Before invoking the model, assert machine-side:

```text
len(remaining_opportunity_horizon) >= 2
W1.status == GROUNDED
W2.status == GROUNDED
future_live_traffic == false for future planning evidence
```

If horizon remains 1, fix the Journey structure or the minimal horizon projection bug BEFORE calling the model.

Do not waste provider calls on an impossible fixture.

## Phase 3 — create a real scarce-resource conflict

Choose/ground candidate A for W1 and candidate B for W2 such that:

```text
A individually feasible == true
B individually feasible == true
A_cost <= optional_budget
B_cost <= optional_budget
A_cost + B_cost > optional_budget
```

or an equivalent truthful shared-time/slack resource conflict.

Preferred: budget because it is easy to audit.

Also require:
- TravelerTwin effective soft value(B) > value(A);
- neither candidate is made infeasible to force the answer;
- both have canonical opening/cost;
- planning evidence provenance is explicit;
- current-window execution still requires current live route evidence.

Do not hardcode exact candidate IDs into the mission.

## Phase 4 — run the real Agent at W1

Mission should be strategic but answer-neutral, e.g.:

"Use the remaining trip well. Preserve protected commitments and scarce budget. If acting now would sacrifice a materially better grounded later opportunity, it is acceptable to leave the current window unused. Use only server facts and normal authority boundaries."

Do NOT mention:
- candidate names;
- candidate IDs;
- "choose W2";
- "DEFER";
- the correct tool sequence.

Expected real trace may vary.

Success requires a typed conclusion whose server contract validates strategic defer.

At W1:
- no replan accepted;
- active plan unchanged;
- no future booking/reservation/plan pointer for W2;
- W1 opportunity resolved as deliberately deferred.

## Phase 5 — advance reality

Continue ordinary HTTP execution.

Pass anchor A / intermediate activities until W2 is now the current opportunity.

Refresh Twin.

The later candidate must not inherit authority from earlier future planning evidence.

Recheck:
- opening/cost freshness;
- budget remaining;
- live current->candidate and candidate->next commitment mobility;
- full deterministic feasibility.

## Phase 6 — execute W2

Real Agent inspects current reality.

Generate/select the truthful F4 proposal.

Gateway remains authoritative:
- ALLOW_AUTO or REQUIRE_CONFIRMATION;
- if confirmation is required, use the real server-issued approval receipt.

Then execute the inserted activity via normal state transitions.

Complete the rest of the protected Journey.

Final:
- Journey COMPLETED;
- Twin READY/COMPLETED as appropriate;
- final active PlanVersion contains the executed W2 addition;
- all actually used route edges are hard eligible/current authority;
- W1 consumed zero optional resource.

## Phase 7 — model timeout policy

Attempt primary configured model once with a bounded timeout.

If a machine-recorded timeout occurs:
- retain the failed run receipt;
- switch to another already-configured REAL Hermes-compatible model, preferably `cn:deepseek-v4.1-flash`;
- keep mission text and server facts unchanged;
- rerun.

A successful real fallback model counts.
Deterministic fallback prose does not.

Do not spend hours retrying one dead endpoint.

## Phase 8 — explicit-intent control

After C closure, if runtime is healthy:

Recreate a comparable horizon, but current Journey mission explicitly favors W1 or rejects W2.

Require:

```text
CURRENT_EXPLICIT_MISSION
>
EXPLICIT_PERSISTED_PREFERENCE
>
LEARNED_SOFT
```

The strategy must actually change, not merely show `EXPLICIT_WINS` in JSON.

Target:
- TAKE_NOW at W1 or another action consistent with explicit intent;
- later W2 no longer has the same resource envelope.

This closes D.

## Test budget

Before runtime:
- only tests directly affected by timeout persistence / fixture/horizon changes.

After the machine run:
- one R20-R25 focused lineage run;
- py_compile;
- git diff --check.

Do not broad-suite after every edit.

## Final artifact

Update the EXISTING:

`REVOLUTION_R25_STRATEGIC_HORIZON_STEWARD_RESULT.md`

Do not create R25.1 report.

Append:
- remote-bound final SHA;
- two-window Journey IDs;
- W1/W2 facts;
- resource arithmetic;
- primary/fallback model attempts;
- W1 AgentRun typed defer;
- unchanged plan pointer;
- W2 revalidation;
- Gateway/approval;
- actual execution;
- final Journey/Twin;
- explicit override control if completed.

## Closure sentence

> CityNexus encountered a feasible real opportunity, deliberately left it unused because taking it would consume scarce resources needed for a better later grounded opportunity, then revalidated reality when that later window became current and executed the better experience through normal authority boundaries.
