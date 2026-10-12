The traveller can now redirect the running Journey in natural language — “I’m tired, make the rest of today easier”, “less walking tonight”, “the kids want ramen” — and CityNexus turns that into a scoped, temporary Journey intent that the existing Operator can plan, coordinate, approve, execute, and automatically expire without corrupting long-term preferences.

# R51 Live Journey Intent Steering

## Delivered

- Added durable `JourneyIntent` records with authenticated traveler/member attribution, server-resolved activity targets, Journey-timezone scope boundaries, supersession, and lifecycle expiry.
- Routed the existing Agent command endpoint through the real semantic interpretation path once, then persisted bounded temporary intent separately from `Preference` and TravelerTwin evidence.
- Added a child `PLAN_ONLY` mission under the active Operator mission. It protects the current activity and C3/C4 commitments and leaves mutation, shared-trip coordination, and booking authority behind the existing R43/R45/R47 gates.
- Threaded active intent into Agent inspection, planning preference context, Journey Ahead, overnight briefing, and the Operator projection.
- Added an inline Operator input with temporary-scope/status feedback and an authenticated API request.
- `CITYNEXUS_LAB_ESTIMATE_AUTHORITY=false` for the one fresh multi-activity experiment.

## One fresh experiment

- Journey: `22222222-2222-4222-8222-222222222222` (`Asia/Shanghai`, six activities); Operator was enabled.
- The current activity remained `IN_PROGRESS` before and after submission.
- Submitted exactly once: `I'm tired. Make the rest of today easier and keep walking low.`
- Result: `INTENT_STEERING_NEEDS_CLARIFICATION`. The request was stored with authenticated traveler attribution and a REST_OF_TODAY scope ending at local midnight. No replan or preference/Twin write occurred.
- The environment had no configured semantic-model credentials (`CITYNEXUS_AI_API_KEY`/`DEEPSEEK_API_KEY` absent and AI disabled), so the semantic compiler used its deterministic fallback rather than an external model. Its interpretation did not ground a walking constraint, so CityNexus asked whether to slow the pace, reduce walking, or reduce stops. The exact wording was not retried or changed.

Machine-readable experiment receipt: [backend/output/r51-live-journey-intent-steering-v1.json](backend/output/r51-live-journey-intent-steering-v1.json).

## Verification

- Backend focused suite: 45 passed (`test_journey_intent.py`, `test_r51_live_journey_intent.py`, Agent mission runtime, and principal boundary).
- Frontend TypeScript: `npm run typecheck:all` passed.
- Focused Playwright: `r51-live-journey-intent.spec.ts` passed.
- `python -m compileall app` and `git diff --check` passed.
- No R33–R50 historical campaign was run.

当前:R51 / live intent steering delivered; experiment clarified without changing the active activity / next: configure the semantic provider to evaluate a future intent with model grounding
