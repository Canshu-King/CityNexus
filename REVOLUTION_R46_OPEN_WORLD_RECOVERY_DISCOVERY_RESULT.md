# Revolution R46 — Open-World Recovery Discovery

## Product result

CityNexus now gives the Journey Agent an explicit `discover_recovery_options` action. When the current recovery surface is too narrow, the Agent can describe the kind of alternative that would help. The server derives the Journey and incident anchor, clamps the provider budget, materializes provider-backed `Place` rows through the existing real-city discovery path, and returns only server-owned Place ids.

Discovery is durable inside the same RecoveryEpoch. An equivalent semantic query reuses its prior attempt; a second distinct query consumes the final bounded attempt. Discovery never creates a `ReplanProposal`, never issues authority, and never mutates the active plan. The Agent can pass returned Place ids to the existing `request_replan` path.

The Operator projection now reports discovery progress, bounded attempts, provider provenance, and ordinary traveller copy:

> “The known choices are too narrow, so I’m looking nearby for new possibilities.”

Provider degradation preserves the existing recovery surface and is represented separately from R44 planning-brain failure.

## Fresh product experiment

Machine evidence: [`backend/output/r46-open-world-recovery-discovery-v1.json`](backend/output/r46-open-world-recovery-discovery-v1.json)

The experiment used a fresh demo Journey with the normal plan, World Context `LAB_FIXTURE` closure, Guardian sensing, and one Journey-level Operator. The Agent action was exercised through the real Gateway with `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false`.

- Provider mode: `captured_replay` (`SEALED_REAL_REPLAY`), explicitly not live.
- The Agent supplied a semantic search intent, not coordinates or provider external ids.
- Existing recovery space was expanded to 5 materialized provider-backed Place ids.
- Repeating the same semantic query reused the same durable attempt and consumed no new budget.
- The normal `request_replan` path then ran with the discovered Place ids and produced one server-generated proposal.
- Discovery reported `creates_proposal=false` and `mutates_active_plan=false`; no authority receipt or active-plan mutation was created.

Result: `OPEN_WORLD_RECOVERY_EXPANDED`.

The replay catalog yielded one grounded replan proposal after expansion, so the experiment stopped at the first bounded terminal product outcome rather than manufacturing a second semantic future. A live provider was not claimed.

## Focused validation

- Recovery-surface semantics: 8 passed (`tests/test_recovery_discovery.py`).
- Python compileall: passed.
- Frontend TypeScript check: passed (`npm run typecheck`).
- The focused Playwright/browser launcher remains blocked by the environment’s system Python 3.10 missing `enum.StrEnum`; no browser assertion was claimed.

## Commit

Pending final R46 commit and push on `gpt/revolution-r33-open-world-journey-adaptation`.
