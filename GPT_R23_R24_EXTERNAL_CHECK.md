# GPT external check — R23/R24 continuation -> R25

Inspected:
- uploaded `CityNexus-RevolutionLab-R23-20261003.zip`;
- bundled runtime receipt + focused tests;
- remote R23 machine receipt/report;
- remote R24-memory continuation receipt/report;
- current experiment head `dc93b91db9878690465349c4c2f76888870b6f49`;
- current TravelerTwin learning, candidate evidence, F4 opportunity insertion, Agent inspection and real-city strategy code.

## Verdict

R23 is a real capability leap, but separate the layers precisely.

### Proven strongly
- plain ACTIVITY_COMPLETED / ACTIVITY_SKIPPED no longer automatically become likes/dislikes;
- voluntary choice and explicit feedback have distinct evidence classes;
- LEARNED_SOFT is persisted, inspectable, expirable and clearable;
- canonical Place category/tags are used instead of Place name;
- explicit preferences suppress contradictory learned signals at planning surface;
- TravelerTwin shows EXPLICIT_WINS conflict state;
- deterministic real-city ordering can change while hard feasibility facts remain unchanged;
- F4 supports a bounded multi-candidate input instead of taking only the first hint;
- positive opportunity threshold is now 30 minutes;
- inspect_twin exposes compact TravelerTwin context to the model;
- R23 real Agent path used Hermes / cn:deepseek-v4.1-flash with estimate authority false and live Valhalla;
- an ACTIVE NO_ACTION control exists.

### What is not yet fully proven

The R23 real Agent positive run did not prove a causal model-choice flip between two equally grounded alternatives.

The canonical report says the model selected the only grounded new culture candidate it could prove. That proves:
- the Agent saw learned context;
- the Agent used the real tool surface;
- the final opportunity was canonical/live/governed/executed.

It does NOT by itself prove:
- candidate A and candidate B were both grounded and hard-feasible;
- the Agent chose B over A because TravelerTwin changed.

The deterministic A/B ranking receipt proves causal planner adaptation. The model run proves autonomous execution. The final missing bridge is a real model choice over a genuinely competitive grounded set.

Do not reopen R23 to patch this as R23.1. Close that bridge as the first acceptance slice of R25.

## The uploaded later R23 receipt is useful but not clean causal isolation

The uploaded runtime receipt at `dc93b91d` shows:
- a different traveler/run from the earlier canonical R23 receipt;
- baseline park -> craft;
- learned calligraphy museum -> craft;
- learned plan has only 2 minutes of live mobility burden vs 41 minutes in the stated baseline.

That is a good product outcome, but by itself the final selection cannot be attributed solely to learning because route burden also differs materially.

Keep the earlier same-hard-facts deterministic A/B receipt as the causal ranking proof.

## R24-memory files are continuation hardening, not a new Revolution species

The repository contains `output/revolution-r24-memory-delivery-20261003`.

That work adds:
- evidence decay;
- avoidance signals;
- explicit override reconciliation.

It explicitly records no new AgentRun.

Treat it as R23 hardening / memory semantics, not as the next major capability milestone.

## Current code defect — reflect replay rejuvenates old evidence

In `learn_from_journey()`, when an evidence row already exists the function currently updates:
- `existing.created_at = now`;
- `existing.expires_at = now + 180 days`;

even when the same Journey outcome rows are simply reprocessed.

Therefore repeated `POST /reflect/process` can rejuvenate old evidence indefinitely and defeat decay.

R25 must make evidence ingestion idempotent by source outcome IDs:
- no new outcome evidence => do not refresh age/TTL/strength;
- new independent evidence => update aggregate once;
- keep original provenance.

## Current learning limit — repeated evidence does not materially reinforce ranking

Multiple same-direction rows mostly increase evidence_count while effective strength is chosen from the strongest representative row.

Therefore repeated independent voluntary choices do not yet create a stronger preference in a meaningful bounded way.

Fix narrowly:
- aggregate independent evidence across Journeys with a capped function;
- preserve raw evidence rows;
- use effective strength for ranking;
- contradiction reduces/net-balances effective confidence;
- explicit preference still wins.

Do not build a probabilistic-profile framework.

## Current strategic product limit — opportunity autonomy is locally greedy

R22/R23 decide one current OpportunityWindow at a time.

The current deterministic fit asks:
- does this candidate fit now?
- is it inside current remaining budget?
- what is its local preference fit / mobility / slack?

It does not prove that CityNexus can preserve scarce time/money for a known better opportunity later in the remaining Journey.

That is the next Revolution frontier.

## R25 thesis

R25 should move from:

`good decision in the current window`

to:

`good stewardship of the remaining journey horizon`.

Machine fact target:

> CityNexus can see more than one grounded opportunity in the remaining trip, understand that taking the first may consume scarce budget/time needed for a later higher-value option, deliberately defer a feasible current opportunity, and later execute the better one — while explicit human intent can reverse that strategy.

This is temporal agency, not another scoring patch.
