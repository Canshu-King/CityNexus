# Revolution R87 — First Honest Live City Discovery (not another fixture)

## R86 acceptance and exact baton
At reviewed remote HEAD `7f2adf04a5a4ed56cc2ce49850eeccfb7fe6bcef`, R86 implementation `e30f08db8e32a0cc98d3dd25c7892d2fab5f8abf` provides a test-proven signed zero-catalogue DRAFT Journey -> select source-linked OSM candidate -> explicit UNKNOWN cost acknowledgement -> native PlanVersion select/start. Keep **PROVEN only for the isolated signed controlled path**. Codex reports 16 adjacent backend tests and 2 Chromium (including seed), plus typecheck/build/compile. Actual Overpass was BLOCKED: `real_city_enabled=False`, replay mode. Do not rerun R58-R86 campaigns.

## Two precise technical risks to inspect narrowly
1. `backend/app/services.py` uses integer `cost_minor=0` in a legacy Activity compatibility field for UNKNOWN admission cost, with `cost_status=UNKNOWN`, `price_known=false`, `cost_included_in_total=false`, Plan `PARTIAL_UNKNOWN` and booking refusal. Audit **all user-visible consumers** of activity cost, totals, budgets, recommendations, exports and offline data: no display or arithmetic path may misinterpret the compatibility zero as FREE or a full budget estimate. Repair only real leaks. Retain native booking refusal and explicit acknowledgement.
2. `bootstrap_discovery.py` now claims durable `IdempotencyKey` scoped by journey/member/traveler before a provider call, improving over city-wide rate limiting. Inspect concurrent race, retry after timeout and provider endpoint fallback: a single app request must not silently become multiple public Overpass HTTP attempts. If provider supports fallback endpoints, either explicitly enforce a true one-attempt limit for this path or report actual attempt count transparently. Do not claim atomic correctness based solely on SQLite test.

## R87 actual user leap
A newly created real-city Journey with zero seeded public Places should let the traveler explicitly select a public search center (or secure-context foreground GPS), give provider-consent, and receive **one real source-linked named OSM candidate from a bounded live Overpass call** when network/config allow. From selection proceed to R86's native start, retaining opening and cost evidence constraints. If OpenStreetMap tags do not ground opening, do NOT assert the Journey startable; show the exact reason and actionable choice (another grounded candidate or source verification). An OSM entity is not inherently open, accessible, safe or free.

## Execution conditions and proof
- Only attempt a real Overpass call if explicitly enabled, network works, a deliberate public center is validated WGS84, and consent is supplied. Maximum ONE real external discovery trial for this R87 closure, not repeat-until-green. If blocked, record BLOCKED and deliver source/UX readiness, not LIVE_PROVIDER_SUCCESS.
- Use a freshly product-created signed A/B Journey in a city catalog verified zero beforehand. A discovers; B cannot read unchosen candidates, private query/center, receipt, or member-specific progress. No auto plan mutation by query. Selecting one Place should yield exactly one materialization.
- No forged geolocation, artificial OSM IDs or substituted TEST_PROVIDER. Record sanitized request/response timestamps/status, OSM IDs, original source URLs, access-deny filtering, counts, PlanVersions, Agent/Guardian/provider calls and remaining unverified matters. Maps external release remains separately consented and destination-only.
- Run one focused backend slice, one browser scenario and typecheck/build/compile/diff. No historical suite reruns.
- Push implementation, truthful `REVOLUTION_R87_FIRST_LIVE_CITY_DISCOVERY_RESULT.md` and exact SHA to `gpt/revolution-r33-open-world-journey-adaptation`.

**Revolution is a visitor finding a real place and starting a usable trip; passing fixtures are a means, not the finish line.**
