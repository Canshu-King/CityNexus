# R30 consent epoch shock recovery — live blocker

## Strike

- R30 branch SHA: `7b4b0e0e312b53863a76ccf880706d58b55a8df5`
- Database: `backend/r28-live-5babd9653d003198.sqlite3`
- Journey: `9c0a68a1-7d62-4acf-a46d-dae90747a959`
- Command:

  ```powershell
  $env:CITYNEXUS_WB2API_CONFIG='C:\Users\仓鼠王\WorkBuddy\2026-09-15-15-47-27\wb2api\config.json'
  $env:CITYNEXUS_LAB_ESTIMATE_AUTHORITY='false'
  .\.venv\Scripts\python.exe run_r30_live.py --full-r30
  ```

## Durable causal evidence

- Round-1 external AgentRun: `17d93301-2096-4ebd-bc93-7476e5c22dc1`.
- Mediator external AgentRun: `b5ac5dd9-54f2-4b45-82da-2278e03e1e2a`.
- Targeted provider closure Event: `8096db19-79c0-46b4-8ca7-ce92b531bffd`.
- Closure scope Place: `real-place-8c09b32224152e3e1ae12843`.
- Stale denial audit: `dbaace16-974c-4c9f-90b3-c94163983509`.
- Post-shock external recovery AgentRun: `6c3b3623-91dc-4879-bd2b-cff8cd330748`.
- Final durable approval: `288ae951-edba-4829-a69f-d0eb62e88e7a`.

The strike proved current UNANIMOUS_DOMINANCE recovery authority, so E2/W2 was correctly marked not required. The provider shock remained server-owned replay input and the external Agent path completed one approval continuation.

## Machine verdict

`output/revolution-r30-live-20261006/R30_MACHINE_VERDICT.json` reports:

```text
overall: CONTRADICTED
PROVEN: 10
NOT_PROVEN: 0
CONTRADICTED: 1
```

The only R30 contradiction is `final_exactly_once_continuation`. Its inherited R28 verdict is:

```text
PROVEN: 11
NOT_PROVEN: 1
CONTRADICTED: 2
overall: CONTRADICTED
```

The first causal failure is lineage: the final recovery AgentRun mission has no reachable collective parent mission. Consequently R28 marks `authenticated_collective_responses` as contradicted, `non_selected_proposals_rejected` as not proven, and `transport_caller_principal_authentication` as contradicted. The approval itself is authenticated and consumed; the missing lineage prevents exactly-once continuation from being machine-proven.

No E/W rows, trusted Events, stale consent, approval, or verifier state were edited. No harness or mission was changed to manufacture a trade-off. R30 remains blocked on the real inherited continuation invariant.

Truth boundary: the shock transport is a server-owned deterministic REPLAY fixture; external Journey Agents use configured external runtimes; physical travel is NOT PROVEN.
