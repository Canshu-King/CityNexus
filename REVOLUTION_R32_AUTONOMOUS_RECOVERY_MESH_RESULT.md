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
