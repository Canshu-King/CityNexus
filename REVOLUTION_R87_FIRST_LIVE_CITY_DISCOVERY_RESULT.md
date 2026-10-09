# Revolution R87 — First live city discovery result

## Outcome

**LIVE_PROVIDER_SUCCESS for one bounded OpenStreetMap/Overpass discovery trial; native Journey start remains BLOCKED by honest opening evidence.**

The product now keeps the R86 zero-catalogue path truthful when it receives real OSM data:

1. bootstrap candidates are scoped to the signed Journey member and traveler that requested them;
2. a candidate whose OSM tags do not ground opening hours is visibly marked `OPENING_UNVERIFIED`, cannot be selected for native start, and names the next actions: verify the source or choose another candidate;
3. only a candidate with grounded provider opening evidence can cross the materialization boundary;
4. the plan ranking path treats `PARTIAL_UNKNOWN` totals and UNKNOWN activity prices as absent cost evidence, never as the cheapest zero-cost plan;
5. the Overpass path records one bounded endpoint attempt and preserves the sanitized provider receipt, source OSM IDs and source URLs.

## The one real external trial

The trial was run once from a fresh product-created signed Journey whose city had zero Places beforehand. Live mode was enabled only for this request, a manual public WGS84 center and explicit provider consent were supplied, and the provider call used `max_attempts=1`.

- Captured at: `2026-10-09T18:26:33.641373+00:00` (UTC)
- Journey: `d803a10e-69c8-41b5-b814-cfa1fd8d9351`
- Public center: `39.120, 117.200`, radius `2500m`
- Query: `museum`
- Endpoint: `https://overpass-api.de/api/interpreter`
- Result: HTTP `200`, `2669.1ms`, `16` provider elements, `3` named candidates retained
- Attempts: exactly `1`; no mirror fallback or retry was used

The three source-bound OSM candidates were:

- 津城静园 — `overpass:node/4679569649` — [OSM source](https://www.openstreetmap.org/node/4679569649)
- 张叔诚故居 — `overpass:node/7953235622` — [OSM source](https://www.openstreetmap.org/node/7953235622)
- 中共天津历史纪念馆 — `overpass:node/2263259321` — [OSM source](https://www.openstreetmap.org/node/2263259321)

All three returned `opening_state=UNKNOWN` and `price_state=UNKNOWN`. They remained private `BOOTSTRAP_PRIVATE` candidates; none was materialized, planned, booked, charged, or started. This is the correct live result: an OSM identity is not proof that a place is open, accessible, safe, or free.

## Focused proof

- Backend R87 privacy/opening/attempt slice: `pytest -q backend/tests/test_r87_first_live_city_discovery.py` — **1 passed**
- R86 native zero-catalogue start regression: `pytest -q backend/tests/test_r86_first_startable_real_city_journey.py` — **1 passed**
- Chromium R87 scenario (including the real-seed setup): `npm run test:e2e -- e2e/r87-first-live-city-discovery.spec.ts --project=chromium` — **2 passed**
- Chromium R86 native-start regression: `npm run test:e2e -- e2e/r86-first-startable-real-city-journey.spec.ts --project=chromium` — **2 passed**
- `npm run typecheck` — passed
- `npm run build` — passed (existing chunk-size warning only)
- `python -m compileall -q backend/app backend/tests/test_r87_first_live_city_discovery.py` — passed
- `git diff --check` — passed

## Remaining limits

- This proves one live discovery answer, not a complete live start: all returned candidates lacked grounded opening hours, so the new UI and server gate correctly stop before Place/PlanVersion creation.
- Admission prices remained unknown; the compatibility integer zero is marked UNKNOWN, excluded from totals, and not bookable.
- No physical presence, walking route, real ticket purchase, AgentRun, GuardianRun, Booking, Order, or PaymentTransaction was created by the trial.
- The external source can change after capture; the stored receipt is an evidence record, not a guarantee of current opening or safety.

## Commits and remote

- GPT R87 taskbook base: `2dc932e15` (remote taskbook commit)
- R87 implementation commit: recorded in the follow-up commit after this report is sealed
- The completed result will be pushed to both `codex/revolution-r63-planned-parallel-journey` and `gpt/revolution-r33-open-world-journey-adaptation` so the review window reads the same history.

