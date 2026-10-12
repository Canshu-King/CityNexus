# REVOLUTION R33 — Open-World Journey Adaptation

## Status inherited from R32

R32 is CLOSED for its stated target. Do not reopen it.

Accepted inherited facts:
- branch ancestry includes R32 fresh exact-run closure;
- stale R1 Agent output is rejected before Gateway use;
- current R2 Agent can create one authorized mutation under current server-owned authority;
- focused R32 regression was green;
- WB2api/Hermes selection and `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` remain unchanged.

The R32 optional `NOT_PROVEN` dimensions are not blockers for R33. Do not create a verifier-only R32 strike, 2D, copied evidence, or another proof loop.

## Revolution objective

Move from a safe autonomous control plane to a user-visible adaptive travel product.

A live external fact must materially change what a real Agent chooses to do, and that autonomous choice must materially change the Journey/collective outcome while preserving server-owned truth and authority.

R33 is not proven merely because:
- an AgentRun completed;
- a ReplanProposal row exists;
- a verifier is green;
- an old replay produces a different UUID;
- UI text says "Agent".

The changed world fact, changed strategy, changed Journey, Agent provenance, and legal authority must be one causal chain.

## Product gap already implemented on this branch

The R32 backend persisted `ReplanProposal.source_agent_run_id` and `recovery_epoch_id`, but the public `/api/v1/journeys/{journey_id}/replans` projection and Live Recovery UI discarded that provenance.

R33 now exposes both fields as explanatory provenance and renders a traveller-facing Agent-origin message. These identifiers are not authority tokens; final mutation remains governed by the current server-side authority path.

Changed product files:
- `backend/app/schemas.py`
- `backend/app/main.py`
- `frontend/src/features/execution/LiveRecovery.tsx`

Codex must verify these changes locally before the live strike and repair only real defects found.

## Minimum fresh live closure — R33-1

Perform exactly one fresh open-world closure after focused local verification.

### Starting Journey

Use a new or clean live Journey whose initial active plan has at least one meaningful discretionary choice. Before the world change, record the initial active-plan strategy in traveller terms, for example:
- outdoor stop vs indoor stop;
- walking-heavy route vs transit-heavy route;
- earlier vs later discretionary activity;
- one open attraction/venue vs another grounded alternative.

Do not pre-script the final replacement.

### Fresh external fact

Acquire one new external provider-backed fact after the initial plan exists.

Preferred facts, in order:
1. live weather observation affecting the planned time/place;
2. live place/service availability or closure fact;
3. live mobility condition with provider-backed measured/qualified evidence.

The fact must be captured through the product's existing provider/ingestion boundary and persisted with honest provenance.

Not acceptable as the proving fact:
- `SIMULATED` public event input;
- hand-edited DB row;
- copied prior output;
- hard-coded fixture selected because its expected answer is known;
- a prompt statement that merely tells Hermes the desired replacement.

If the configured environment cannot obtain an honest external fact, report BLOCKED with the exact provider/boundary reason. Do not downgrade provenance.

### Real Agent strategy change

Run the existing external WB2api/Hermes path against the current Journey after the fresh fact exists.

The Agent must inspect current product truth and autonomously choose a response. The prompt may state the traveller's goals/constraints and the new fact, but must not prescribe:
- the exact replacement place;
- the exact proposal id;
- the exact tool sequence;
- the desired mutation result.

To count as R33, the Agent output must be strategy-materially different from the pre-change Journey. A UUID-only or wording-only difference is insufficient.

Examples that count:
- replace the newly unsuitable outdoor stop with a grounded indoor alternative;
- move a discretionary stop to another time and preserve a protected booking;
- switch the relevant mobility mode/route when current evidence makes the old choice materially worse or infeasible.

### Server-owned truth and authority

The Agent may propose; it may not fabricate truth or authority.

Required:
- proposal remains bound to the exact AgentRun and current RecoveryEpoch;
- candidate/place/mobility/weather facts used for a hard decision come from existing qualified product evidence;
- current collective/single-member authority path decides whether mutation is legal;
- stale epoch/run/receipt cannot authorize;
- at most one Journey mutation for this closure;
- do not enable estimate authority;
- do not alter WB2api/Hermes selection merely to make the strike pass.

### User-visible closure

After the authorized mutation, the product surface must make the causal outcome understandable without exposing internal authority jargon.

Minimum UI evidence:
- what changed in the world;
- what changed in the Journey (removed/added/moved or equivalent visible strategy delta);
- Agent-origin provenance is visible on the replan card via `live-agent-origin`;
- the active Journey after mutation reflects the new strategy.

The UI must not claim a physical trip happened if only software/provider execution occurred.

## Required causal receipt for R33-1

Write one compact result document after the strike, only if it actually ran.

It must name:
- git head used;
- Journey id;
- initial active plan id and short human-readable strategy summary;
- fresh provider observation/event id, provider key, provenance, capture time;
- exact AgentRun id and RecoveryEpoch id;
- proposal id and proposed plan id;
- concise semantic delta between old and new strategy;
- authority mode/receipt id if applicable;
- final active plan id;
- mutation count;
- whether `source_agent_run_id` on the public replan projection equals the exact live AgentRun;
- whether Live Recovery rendered `live-agent-origin`;
- limitations (for example replay-backed Hermes or no physical travel).

No machine verdict framework is required for R33-1 unless an existing test already provides one. The primary proof is causal product behavior, not a new verifier.

## Focused verification before live strike

Use the smallest useful checks. At minimum:
- backend focused tests covering replan projection/schema and Agent runtime/recovery behavior touched by this change;
- frontend typecheck or the narrowest relevant test for `LiveRecovery`;
- existing R32/R30 tests only where needed to ensure this provenance exposure did not weaken authority.

Do not rerun the entire historical evidence suite unless a real regression requires it.

## Success

R33-1 is PROVEN only if all are true:
1. a fresh external fact is persisted honestly after the starting plan exists;
2. a real external AgentRun reacts without a preselected answer;
3. its strategy is materially different from the pre-fact Journey;
4. that proposal is exactly bound to the live AgentRun/current epoch;
5. legal current authority permits exactly one mutation;
6. the active Journey actually changes;
7. the user-facing recovery surface exposes the changed plan and Agent origin;
8. no server-owned truth/authority boundary is weakened.

If any one is missing, report the exact missing link as PARTIAL or BLOCKED. Do not manufacture closure.

## Codex handoff

Work only on:
`gpt/revolution-r33-open-world-journey-adaptation`

Start by fetching the branch and inspecting the three already changed files. Treat them as a proposed implementation, not as pre-proven code.

Then:
1. add/repair narrow tests for the public provenance projection and UI rendering;
2. run focused verification;
3. if green, execute R33-1 once using the configured live provider boundaries;
4. commit real code fixes if needed;
5. write `REVOLUTION_R33_OPEN_WORLD_JOURNEY_ADAPTATION_RESULT.md` with the causal receipt;
6. push the branch.

Do not reopen R32 and do not create R33-2 merely because R33-1 succeeded.
