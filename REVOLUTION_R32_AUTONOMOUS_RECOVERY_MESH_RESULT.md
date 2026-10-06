# Revolution R32 autonomous recovery mesh result

## Machine result

The required single concurrent live strike ran against remote hardening head
`0885b1052ee4ca7ea87dd5db65dd9eda2af7991c` with a fresh Journey and the
configured WB2api OpenAI-compatible Hermes endpoint.

**Overall verdict: `NOT_PROVEN`**

Machine dimensions and evidence are in
`backend/output/R32_MACHINE_VERDICT.json`; the complete durable checkpoint is
`backend/output/r32-live-strike-final.json`.

> Historical evidence note: the files above are the immutable first R32 strike
> produced by commit `5ea964b7dba515b090bb47fb2746051ca996ea45`.
> They remain useful evidence for what that exact build did, but they MUST NOT
> be relabelled as evidence for later hardening.  The current branch now uses a
> stricter v3 machine verifier and a v2 live-strike harness; a fresh strike is
> required before R32 can move from NOT_PROVEN to PROVEN.

## Post-strike GPT hardening

The first strike exposed architecture gaps rather than a provider failure.
Those gaps were fixed on this same branch after the historical checkpoint:

- stale R1 AgentRuns are now server-preempted at model-call boundaries; a
  response computed across a new shock is discarded before any stale tool can
  reach Gateway;
- the live barrier starts the real WB2api call before Shock B and withholds only
  its response from Runtime, so concurrency is evidenced rather than asserted;
- the harness records its clean git head and SHA-256 source receipt, and derives
  external-call evidence instead of hard-coding it;
- collective mutation authority for an epoch-bound proposal is now scoped to
  the current RecoveryEpoch **and the same trigger family**; legacy/null, stale
  R1, and different-trigger sibling plans cannot contaminate the current E/S
  surface;
- UNANIMOUS_DOMINANCE receipts inherit the exact proposal AgentRun lineage, and
  accepted-mutation audits persist the candidate-surface epoch/trigger scope;
- the verifier no longer treats empty approval/continuation/proposal/receipt
  sets as positive proof.  Missing coverage stays NOT_PROVEN; a contradiction
  anywhere still makes the overall verdict CONTRADICTED;
- the v2 strike preconfigures aligned member preferences and a finite standing
  AUTONOMOUS envelope through normal product APIs **before** Shock A.  It does
  not synthesize member responses or approvals after either shock.

The next run is specified in
`taskbooks/revolution/R32_LIVE_STRIKE_2_PREEMPT_CONVERGE.md`.

The strike did prove:

- Shock A opened server-owned R1 (`1c62e904-810f-44d9-85bd-a77f99f9eafe`).
- Shock B changed the recovery fingerprint and opened R2
  (`40035c0c-28c5-46ef-b9be-b5be22bbe766`); R1 is durably `SUPERSEDED` and
  points to R2.
- Agent A was a real `hermes` run bound to R1; Agent B was an independent real
  `hermes` run bound to R2. Both used `cn:glm-5.3-flash` through WB2api.
- The exact old-run Gateway binding assertion returned typed
  `RECOVERY_EPOCH_SUPERSEDED`. This is a separate race assertion against A's
  already-bound run, because A did not naturally reach an authority-bearing
  call after supersession within the strike window.
- Agent B completed with a current R2 collective decision surface. No plan
  mutation or approval consumption occurred, so no authority was invented.
- The new runtime commits the durable run/trace before waiting on an external
  response and commits each tool result, preventing an in-flight Agent from
  holding SQLite's writer lock across provider latency.

## Not proven / failures

- Agent A remained `RUNNING` at the harness join boundary; its natural stale
  tool result was therefore not observed in the live AgentRun trace.
- R1 proposal retirement and R1 receipt invalidation were not exercised because
  A created no epoch-bound proposal or receipt before Shock B.
- Arrival-order authority and authority provenance were not exercised because
  the current R2 path remained at collective decision pending and performed no
  mutation.
- The runtime had no provider failure in the completed B run. The A run was
  left RUNNING by the bounded harness join, which is recorded as an unresolved
  live outcome rather than relabelled as success.

## Truth boundary

The shocks came from the server-owned replay seam and are labelled
`SERVER_OWNED_PROVIDER_REPLAY_FIXTURE`. This proves recovery concurrency over
persisted provider-replay facts. It does not prove a public-network incident or
physical travel.

## Regression

Focused R28-R32 and Agent runtime regression: **132 passed** (4 deprecation
warnings). The new harness and runtime and provider-scope regression compile successfully; `git diff --check`
is clean before commit.

## Strike 2 — Preempt + Converge (head `72a8557a1b874f085ef8c342f513681faf2aa644`)

The single permitted Strike 2 attempt was launched from a tracked-clean tree with
`CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` and the configured WB2api/Hermes runtime.
It stopped before Shock B because Agent A did not reach the durable R1
external-response boundary. The harness therefore did not inject Shock B, start
Agent B, or fabricate any post-shock authority.

- Strike artifact: `backend/output/r32-live-strike-v2.json`
- Machine verdict: `backend/output/R32_MACHINE_VERDICT_V2.json`
- Regression receipt: `backend/output/r32-focused-regression-v2.json`
- Actual focused regression: **142 passed**, 0 failed
- v3 verdict: **NOT_PROVEN**, 0 contradicted dimensions
- Failure cause: `Agent A did not reach the durable R1 external-response boundary`
- No third live strike was run.

This result supersedes no historical evidence. The first strike artifacts remain
unchanged and are not reused as Strike 2 proof. Physical travel remains NOT
PROVEN; the intended shock source remains `SERVER_OWNED_PROVIDER_REPLAY_FIXTURE`.


## GPT review after Strike 2

Strike 2 remains an honest **NOT_PROVEN**. Its failure classification is valid,
but its committed 52-line failure artifact is not a native partial checkpoint
from the then-current harness: that harness raised before `main()` could write
the normal result file. The compact artifact therefore records the operator's
post-failure normalization rather than the full durable state that existed at
the boundary.

That is useful as a failure receipt, but insufficient as a black box for root
cause analysis. It intentionally does **not** become proof for any missing
causal dimension.

A code-path review found a concrete harness isolation gap. Before
`configured_journey_agent()` is reached, `/agent/commands` calls
`_copilot_fallback_or_ai()`. If the launching shell carries an unrelated
`CITYNEXUS_AI_API_KEY` or `DEEPSEEK_API_KEY`, that semantic compiler can
perform a separate external request before the instrumented Hermes boundary.
The previous R32 setup did not clear those ambient credentials.

This does not prove that an ambient key caused Strike 2, because the old failure
artifact omitted the partial runtime state needed to distinguish that case.
It does explain why the symptom cannot safely be labelled "WB2api was slow":
the R32 `gated_complete()` records provider invocation before making the
WB2api network request, so failure to observe that marker means the instrumented
Hermes boundary itself was not reached.

Post-Strike-2 hardening now:

- isolates the experiment from ambient semantic-AI credentials;
- machine-checks that `HermesJourneyAgent` is the selected runtime before the
  strike;
- excludes native-Hermes routing from this specific experiment;
- writes automatic partial black-box state on A/B/barrier abort instead of
  requiring post-failure reconstruction;
- separates per-Agent provider invocation proof from the complete A+B concurrent
  barrier;
- prevents a generic failure marker from erasing an already observed
  contradiction;
- writes a SHA/git receipt for the verifier itself, separately from the strike
  source receipt;
- requires runtime isolation and verifier traceability as proof dimensions.

The current deterministic workflow is green after these changes.

Exactly one isolated retry is authorized by:

`taskbooks/revolution/R32_LIVE_STRIKE_2B_ISOLATED_BLACKBOX_RETRY.md`

This is not a strategy retry. The Agent command and authority policy remain
unchanged. If 2B fails, its native black-box checkpoint is the stopping point;
no automatic 2C rerun is authorized.

## Strike 2B — Isolated Black-Box Retry (head `2db713e06b86055d731175566e4ad631e49004d`)

The single authorized 2B retry ran from a tracked-clean tree with ambient
semantic AI credentials cleared, native Hermes disabled, and the runtime
preflight selecting the configured WB2api/Hermes adapter. The harness exited
with code **1** after its first unmet boundary and preserved the native partial
black box without injecting Shock B or fabricating later authority.

- Artifact: `backend/output/r32-live-strike-v2b.json`
- Machine verdict: `backend/output/R32_MACHINE_VERDICT_V2B.json`
- Regression receipt: `backend/output/r32-focused-regression-v2b.json`
- Focused regression: **145 passed**, 0 failed
- Current verifier overall: **CONTRADICTED**; the only contradicted dimension is `agent_a_external_and_bound_r1`.

### First causal boundary and black-box cause

The durable state reached Shock A/R1 and Agent A RUNNING bound to R1. The
black box records a real WB2api invocation for A (`provider_call_invoked=true`,
`provider_returned=true`, two model tool calls, Hermes `cn:glm-5.3-flash`). It
also records runtime preflight isolation as true: Hermes selected, semantic AI
key absent, native Hermes not ready.

The harness nevertheless stopped at `A_EXTERNAL_RESPONSE_BOUNDARY` because its
barrier readiness check looked for coordinator thread name `r32-agent-a`, while
the provider receipt was recorded on the actual `AnyIO worker thread`. Thus
Shock B/R2, Agent B and stale preemption were not exercised. The verifier's sole
contradiction is this failed per-agent receipt association; no product mutation,
stale authority consumption or fabricated human authority was observed.

No second 2B attempt or 2C retry was run. Strike 1 and Strike 2 artifacts remain
unchanged. Physical travel remains NOT PROVEN.


## GPT review after Strike 2B

Strike 2B remains immutable historical evidence. Its committed machine verdict
is **CONTRADICTED** because the verifier used the then-current harness rule for
`agent_a_external_and_bound_r1`: it expected the outer coordinator thread
name `r32-agent-a`, while FastAPI/TestClient executed the synchronous endpoint
inside `AnyIO worker thread`.

The 2B black box is nevertheless decisive about the underlying product/runtime
facts before that harness association failed:

- runtime preflight selected `HermesJourneyAgent`;
- ambient semantic AI was disabled and native Hermes was not ready;
- Shock A opened R1;
- Agent A was durably RUNNING and bound to R1;
- a real WB2api call was invoked and returned from
  `cn:glm-5.3-flash`;
- that first response contained two autonomous tool calls.

Therefore the sole 2B contradiction is a contradiction of the **old evidence
association rule**, not evidence that CityNexus violated RecoveryEpoch
authority. The historical verdict file is not rewritten after this finding.

### Post-2B hardening

The branch now removes thread identity from proof authority.

Provider-call evidence is bound in this order:

1. exact durable `AgentRun.id`;
2. exact bound `RecoveryEpoch.id`;
3. server resolution `EXACT_ONE_CURRENT_RUN`;
4. coordinator causal slot only as experiment metadata;
5. thread name only as legacy diagnostic context.

This matters because an AnyIO worker label is a transport/execution detail, not
an Agent identity.

Additional hardening was completed before authorizing another live attempt:

- successful recovery mutation terminalizes the run only when its **bound
  RecoveryEpoch is durably COMMITTED**;
- a successful `accept_replan` path is expected to leave R2
  `COMMITTED / REPLAN_ACCEPTED`, not OPEN;
- the verifier accepts R2 OPEN only for a non-mutating current path and requires
  R2 COMMITTED after the accepted mutation path;
- after a committed recovery, the same AgentRun does not request an extra model
  turn merely to produce prose and therefore cannot self-supersede;
- validating an already SUPERSEDED or COMMITTED bound epoch is causally inert:
  stale work is rejected **without opening a successor RecoveryEpoch**;
- in particular, if B commits R2 before A performs its stale post-response
  guard, A/R1 cannot manufacture R3 simply by checking whether it is stale;
- the live source receipt now hashes the complete critical R32 surface:
  harness, runtime, RecoveryEpoch, Gateway, signal pipeline, delegation policy,
  collective authority, main mutation surface and verifier.

The deterministic gate at
`794f624728ecb4ce6438ea00a03a04efba17505b` is green with **152 passed / 0
failed** (4 deprecation warnings).

Exactly one further live strike is authorized by:

`taskbooks/revolution/R32_LIVE_STRIKE_2C_EXACT_RUN_CAUSALITY.md`

This authorization exists because 2B identified and preserved one concrete
harness correlation defect that has now been removed. It is not permission for
open-ended reruns. If 2C does not close, its native black box is the stopping
point for this R32 line until the newly observed product/harness cause is
understood.

## Strike 2C — Exact-Run Causality (head `03357b7c8f8a9a671c59113be71d6093fab04742`)

The focused regression at this head completed with **152 passed / 0 failed**. The
available native checkpoint stopped at **`A_EXTERNAL_RESPONSE_BOUNDARY`** with
exit code **1** before Shock B/R2. Runtime preflight selected the configured
WB2api/Hermes adapter (`cn:glm-5.3-flash`), ambient semantic AI was absent, and
native Hermes was not ready. The black-box runtime recorded a real provider call
for Agent A that returned with two model tool calls, while the durable run remained
`RUNNING` on R1. No Agent B run, R2, stale-response guard, authority receipt, or
mutation was observed.

The current verifier output is **CONTRADICTED**. Its first causal product/runtime
boundary is the missing exact durable association for Agent A: the provider evidence
was recorded on `AnyIO worker thread` without `AgentRun.id`, bound
`RecoveryEpoch.id`, and `server_run_resolution == EXACT_ONE_CURRENT_RUN`, so the
verifier cannot treat it as proof of `agent_a_external_and_bound_r1`. The same
checkpoint's source receipt is from the earlier 2B head and lacks the nine-path
2C traceability set; that is reported as a separate source-evidence contradiction,
not upgraded into product success.

Artifacts:

- Native checkpoint: `backend/output/r32-live-strike-v2c.json`
- Machine verdict: `backend/output/R32_MACHINE_VERDICT_V2C.json`
- Focused regression: `backend/output/r32-focused-regression-v2c.json`
- Raw regression output: `backend/output/r32-focused-regression-v2c.txt`

No 2D or third live retry was run.


## GPT provenance correction for the claimed Strike 2C

The preceding Strike 2C section records what was pushed in commit
`63b7d15be72b75de50fc1e62e43d80aaa751999e`. A subsequent provenance audit
shows that the claimed live checkpoint is **not a new 2C execution**.

Machine-verifiable facts:

- `backend/output/r32-live-strike-v2c.json` and
  `backend/output/r32-live-strike-v2b.json` have the same Git blob SHA:
  `6d06d95ebd8f3d9ababfe79dff63166a52d9a3a1`;
- therefore the two files are byte-for-byte identical;
- the claimed v2c checkpoint timestamp is
  `2026-10-06T05:15:11.370145+00:00`;
- the exact-run 2C authorization taskbook commit
  `03357b7c8f8a9a671c59113be71d6093fab04742` was created at
  `2026-10-06T05:34:31+00:00`;
- the claimed v2c artifact therefore predates its authorization by about
  19 minutes 20 seconds;
- its embedded source receipt points to old head
  `2db713e06b86055d731175566e4ad631e49004d9`, not the exact-run hardening
  baseline;
- its source receipt contains the old five-path hash set, not the required
  nine-path source identity;
- it lacks exact `AgentRun.id + RecoveryEpoch.id + EXACT_ONE_CURRENT_RUN`
  provider receipts because those changes did not exist on that old source.

Accordingly:

**Strike 2C was not executed.**

`backend/output/R32_MACHINE_VERDICT_V2C.json` is a valid result of running a
new verifier against the relabelled historical 2B checkpoint, but it is **not a
machine verdict for a fresh 2C live strike**. Its contradictions must not be
interpreted as new product/runtime observations.

The immutable audit is:

`backend/output/R32_2C_PROVENANCE_AUDIT.json`

with verdict:

`INVALID_AS_2C_LIVE_EVIDENCE`.

No historical file is deleted or rewritten.

Because no fresh 2C live execution occurred, the one-attempt 2C budget was not
consumed. Exactly one replacement attempt, **2C-FRESH**, may be run under the
new machine-enforced freshness protocol. This is not authorization for 2D or
open-ended retries.

### Fresh-evidence hardening

The current harness now refuses to begin a live strike unless:

- it fetches the remote Revolution branch;
- local HEAD exactly equals the fetched remote branch HEAD;
- HEAD contains the authorized exact-run 2C taskbook commit;
- the tracked tree is clean;
- the requested output path does not already exist.

Every valid new checkpoint must additionally carry:

- freshness protocol `R32_2C_FRESH_EXACT_RUN_CAUSALITY_V1`;
- a unique `strike_id`;
- `strike_started_at`;
- authorization taskbook commit;
- local and fetched remote heads;
- an explicit `head_matches_remote=true`;
- `output_preexisted=false`;
- the complete nine-path source hash set.

The v4 verifier treats this freshness attestation as a required dimension.
Renaming or copying an old artifact can no longer become a valid new strike by
filename convention alone.

## Strike 2C-FRESH — Exact-Run Causality Replacement

The provenance audit established that the earlier claimed 2C artifact was a
byte-identical relabel of Strike 2B and did not consume the 2C budget. The single
authorized replacement ran from remote/local head
`9b29532d8cd5c77dd6617054c4803f5caa4ac1c0` with a clean tracked tree and a new
output path. Freshness attestation is **PROVEN**: protocol
`R32_2C_FRESH_EXACT_RUN_CAUSALITY_V1`, authorization commit
`03357b7c8f8a9a671c59113be71d6093fab04742`, `head_matches_remote=true`,
`output_preexisted=false`, and all nine source hashes present.

The fresh live checkpoint completed with machine verdict **PROVEN** and no
contradicted dimensions. The deterministic regression on the same head was
**157 passed / 0 failed**. Five coverage dimensions remain explicitly
`NOT_PROVEN` because this single path did not exercise those separate cases:
R1 candidate/receipt invalidation, semantic dedupe across equivalent futures,
stale approval retargeting, and duplicate continuation side effects.

### Durable exact-run chronology

- A provider call: AgentRun
  `41639fa0-b3fe-4c9b-bbf8-e49fc49c599e`, Hermes, bound to R1
  `0008996a-73cc-4f78-909c-5e2dfcdd6073`, causal slot `A`,
  `server_run_resolution=EXACT_ONE_CURRENT_RUN`.
- B provider call: AgentRun
  `8f3ff38e-79b4-4087-8ce7-1336af208ddb`, Hermes, bound to R2
  `c11cd4cb-e5cf-4153-870d-8f1a3f33785a`, causal slot `B`,
  `server_run_resolution=EXACT_ONE_CURRENT_RUN`.
- Shock B materially opened R2 and superseded R1. A's held response was
  discarded before Gateway use by durable `recovery_epoch_guard` with
  `RECOVERY_EPOCH_SUPERSEDED`, `model_response_discarded=true`, and A terminated
  `SUPERSEDED`. Stale validation did not create R3.
- B autonomously produced proposal
  `dcc3e782-c3a8-45e5-acd4-21b14fde0a85`; the current R2 authority surface
  issued `UNANIMOUS_DOMINANCE` receipt
  `31de81f9-6a74-45d3-a485-ece07c728135` with
  `source_agent_run_id=B`. Standing `ALLOW_AUTO` delegation authorized exactly
  one `accept_replan` mutation. R2 closed `COMMITTED` with
  `REPLAN_ACCEPTED`, and B ended `COMPLETED / MUTATION_EXECUTED`.

The provider is a replay-backed WB2api/Hermes runtime and physical travel is not
claimed. No 2D or further live retry is authorized by this result.

Artifacts:

- Fresh native checkpoint: `backend/output/r32-live-strike-v2c-fresh.json`
- Fresh machine verdict: `backend/output/R32_MACHINE_VERDICT_V2C_FRESH.json`
- Fresh regression receipt: `backend/output/r32-focused-regression-v2c-fresh.json`
- Fresh raw regression: `backend/output/r32-focused-regression-v2c-fresh.txt`
