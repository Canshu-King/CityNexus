# Revolution R32 autonomous recovery mesh result

## Machine result

The required single concurrent live strike ran against remote hardening head
`0885b1052ee4ca7ea87dd5db65dd9eda2af7991c` with a fresh Journey and the
configured WB2api OpenAI-compatible Hermes endpoint.

**Overall verdict: `NOT_PROVEN`**

Machine dimensions and evidence are in
`backend/output/R32_MACHINE_VERDICT.json`; the complete durable checkpoint is
`backend/output/r32-live-strike-final.json`.

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
