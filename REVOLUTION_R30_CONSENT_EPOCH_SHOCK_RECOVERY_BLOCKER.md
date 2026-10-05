# R30 consent epoch shock recovery — causal blocker

## Strike

- Branch: `gpt/revolution-r30-consent-epoch-shock-recovery`
- HEAD: `c4638ce1dcfff0ed5a1fe5e188965dc3089674ba`
- Journey: `f148d18f-b3d6-445e-b48a-8e0d97a79d09`
- Database: `backend/r28-live-b83fee73b0aebf92.sqlite3`
- Command:

  ```powershell
  $env:CITYNEXUS_WB2API_CONFIG='C:\Users\仓鼠王\WorkBuddy\2026-09-15-15-47-27\wb2api\config.json'
  $env:CITYNEXUS_LAB_ESTIMATE_AUTHORITY='false'
  .\.venv\Scripts\python.exe run_r30_live.py --full-r30
  ```

## Persisted causal evidence

- Round-1 external AgentRun: `5d9a723a-2480-4311-a870-7a3b8247a617`.
- Mediator external AgentRun: `59773e05-1738-4f9d-aa70-ad337f914eb9`.
- Renewed E1: `44f1ffbb272f75b98168e09929e7d4a3421f9cbc97ec573cacec0c178fe8c673`.
- Renewed W1: `3383cc1ed60593ef6174f51b73efd131287b61aaec372506cbddaeed9933355c`.
- Server-owned targeted closure Event: `39dd7236-5eb9-4596-9e68-45b8c9205cec`.
- Closure scope Place: `real-place-8c09b32224152e3e1ae12843`.
- Stale-authority denial audit: `da395ab5-411d-44c2-aa2e-51848ba8b3cb`.
- Material W changed to `f1c9b145f65e842333cf1af3d51c79d26d719a4e6ee91d2a7ee612c199edff2e` while E stayed equal.
- Post-shock external recovery AgentRun: `b61e24e7-2b5b-4b1e-80e1-a6acf1210ed3`.

The recovery Agent found a jointly acceptable compound opportunity and went through the normal durable approval path. No post-shock collective round was persisted, so no E2/W2 authority record exists.

## Machine verdict

`output/revolution-r30-live-20261006/R30_MACHINE_VERDICT.json`:

```text
overall: CONTRADICTED
PROVEN: 8
NOT_PROVEN: 2
CONTRADICTED: 1
```

First causal closure failure:

- `final_exactly_once_continuation`: `CONTRADICTED`.
- The final run's inherited R28 verifier reports `authenticated_collective_responses: CONTRADICTED` because the final recovery mission has no collective parent mission, and `transport_caller_principal_authentication` is consequently contradicted.
- The accepted F4 proposal also records `impact_target_server_validated=false` and `IMPACT_TARGET_NOT_SERVER_VALIDATED`; its incident evidence is typed as `OPPORTUNITY_WINDOW` while the persisted trigger is the provider `CLOSURE` Event.
- `fresh_selective_human_authority` and `e2_w2_durable_when_required` remain `NOT_PROVEN` because the no-tradeoff branch did not create a post-shock resolved collective round.

This is preserved as the real product/lineage blocker. No further harness or mission entrance changes were made after the single first-round prompt narrowing, and no human trade-off was manufactured to obtain a prettier verdict.

## Narrow validation

```text
python -m compileall -q app run_r30_live.py scripts/r30_machine_verdict.py
python -m pytest -q tests/test_r29_disagreement_mediation.py tests/test_r28_authenticated_member_principal.py tests/test_r28_durable_approval_continuation.py
41 passed, 4 warnings
```

Truth boundary: the shock transport is a server-owned deterministic REPLAY fixture; external Journey Agents use configured external runtimes; physical travel is NOT PROVEN.
