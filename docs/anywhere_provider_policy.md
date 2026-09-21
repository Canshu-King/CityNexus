# CityNexus Anywhere Provider Policy v1

Status: arbiter contract note for Anywhere v1 provider behavior, hydration UX, cache reuse, and discovery-area semantics.

This file is self-contained. It does not change CNX-DEMO, the Beijing golden fixture, frozen Simulation truth gates, or the core Anywhere capability contract. It defines how real providers are budgeted and how a HYDRATABLE destination becomes operationally useful without pretending that public provider latency is instantaneous.

## 1. Implementation order is frozen

The implementation order is:

1. **Provider client strategy first**
   - use a bounded, observable provider policy;
   - prefer one primary Overpass endpoint per attempt rather than spending the same category budget serially across three mirrors;
   - treat timeout, 429, 5xx, malformed XML/JSON, and partial/truncated data as explicit provider observations;
   - use the canonical destination extent/bounds when the resolver supplies them;
   - correct category/tag mapping, including a real nightlife branch;
   - never infer success from HTTP 200 plus an empty or malformed payload.

2. **Fresh-cache read gate second**
   - a stored `expires_at` has no product value unless read before network work;
   - if a matching candidate/catalog snapshot is still fresh, reuse it and do not call the remote provider;
   - cache reuse must be keyed by canonical destination identity, provider policy/version, catalog schema/version, and the relevant discovery-area identity;
   - a warm run must be measurably different from a cold run once this gate lands.

3. **Readiness thresholds third**
   - only after provider behavior and fresh-cache reuse are real may `readiness_policy_version` thresholds be frozen;
   - do not score a destination as structurally weak merely because the client discarded 6-7 of 10 categories through its own timeout policy;
   - readiness is based on truthful category coverage and mobility evidence, not raw POI count.

The sequence above is normative. A readiness threshold may exist temporarily for development, but it is not a release-level policy until steps 1 and 2 are proven.

## 2. R8: four-minute cold hydration is allowed, but foreground blocking is not

A HYDRATABLE operation may take several minutes in v1 when public providers are slow or rate-limited. The product must not require the user to remain on one spinner screen for the entire duration.

### Required semantics

- hydration admission target: **<= 1 second** under normal local DB conditions;
- admission returns or reuses a durable `operation_id`;
- long provider work runs asynchronously outside the request lifecycle;
- status is queryable;
- refresh/reopen resumes the same nonterminal operation for the same durable fingerprint;
- the user may navigate away while hydration continues;
- the UI must show truthful phase/elapsed/provider state rather than fake percentage;
- completion must **not automatically mutate, select, or start a Journey**;
- when hydration reaches a plannable result, UI exposes an explicit **"去规划" / Go to planning** action;
- failure leaves the Journey identity intact and exposes a retry/recovery action;
- provider network work must never hold a SQLite write transaction.

There is **no v1 total-latency hard requirement of 60 seconds**. The measured 238-245 second cold path is acceptable only because the operation is resumable and non-blocking. Provider-policy work should still reduce latency aggressively, but must not manufacture facts or silently drop categories merely to hit a cosmetic SLA.

### Review/demo environment

Pre-hydration before a live classroom/review demo is allowed and recommended.

It must satisfy all of the following:

- the hydrated catalog is the same normalized/provenance-bearing product data used by normal planning;
- it is not a hidden replacement fixture;
- the UI/runtime may truthfully show the destination as already READY/warm;
- cold-path evidence must be retained separately in logs/tests so a warm demo is not misrepresented as a 1-second cold hydration;
- CNX-DEMO and Beijing golden behavior remain deterministic and independent of the live-provider profile.

## 3. Provider budget contract shape

Provider timing is policy, not scattered magic constants.

A hydration operation exposes or records an effective `provider_budget` with this shape:

```yaml
provider_budget:
  policy_version: "anywhere-provider-v1"
  total_operation_budget_ms: 300000
  stages:
    RESOLVING_DESTINATION:
      stage_budget_ms: 10000
      request_timeout_ms: 5000
      max_attempts: 2
    DISCOVERING_POIS:
      stage_budget_ms: 240000
      request_timeout_ms: 60000
      max_attempts_per_query: 1
    BUILDING_MOBILITY:
      stage_budget_ms: 30000
      request_timeout_ms: 10000
      max_attempts_per_chunk: 2
  concurrency:
    max_inflight_provider_requests: 1
  retry:
    backoff_ms: [1000, 3000, 8000]
    honor_retry_after: true
  partial_policy:
    preserve_successful_categories: true
    budget_exhaustion_status: PARTIAL
    never_promote_partial_to_complete: true
```

The numeric values above are the **v1 review-profile starting policy**, not universal provider truth. They are versioned and may be tuned only with measured evidence.

### Budget rules

1. A stage budget is an upper bound for that stage, not a promise to consume the full amount.
2. Request timeout must not exceed the remaining stage budget.
3. A timeout/429/5xx consumes budget and produces a provider observation.
4. Do not serially burn the same category budget across three mirrors by default.
5. Mirror failover, if used, must be explicit in provider observations and must share the same stage budget.
6. A partial response that contains validated entities may be preserved as PARTIAL; it must not be discarded merely because another category timed out.
7. Provider failure must not be flattened into `NO_FEASIBLE_PLAN`.
8. Budget exhaustion must never fabricate empty-category certainty.
9. Retry/backoff is bounded. Public endpoints are not to be hammered.
10. Ordinary full regression tests use deterministic fixtures; live-provider timing belongs in opt-in smoke/acceptance evidence.

## 4. Discovery-area contract shape

If destination resolution supplies an administrative extent, hydration must use that extent rather than silently replacing it with a fixed 5 km radius around the centroid.

The normalized `discovery_area` shape is:

```yaml
discovery_area:
  strategy: ADMIN_EXTENT
  source: PHOTON_EXTENT
  source_provider: PHOTON
  coordinate_system: WGS84
  canonical_destination_id: "..."
  bbox:
    west: 98.123
    south: 27.123
    east: 99.123
    north: 28.123
  centroid:
    latitude: 27.7443567
    longitude: 98.6672235
  observed_at: "2026-09-21T00:00:00Z"
  radius_m: null
```

Allowed `strategy` values for v1:

- `ADMIN_EXTENT`
- `RADIUS_FALLBACK`

Allowed `source` values for v1:

- `PHOTON_EXTENT`
- `CANONICAL_DESTINATION_BOUNDS`
- `CENTROID_RADIUS_FALLBACK`

### Area rules

1. `ADMIN_EXTENT` is preferred whenever a trusted resolver returns a usable extent.
2. `RADIUS_FALLBACK` is allowed only when a usable extent is absent.
3. A radius fallback must expose its actual `radius_m`; it must not masquerade as county-wide discovery.
4. The existing 5 km clamp must not override a valid county/district extent.
5. All normalized discovery geometry is WGS-84.
6. Provider-native coordinate systems remain recorded in provenance.
7. The discovery-area identity participates in cache/hydration fingerprinting so a 5 km fallback result cannot be reused later as if it represented the full administrative extent.
8. If a bbox is too large for one safe provider request, it may be tiled/chunked, but each chunk must preserve parent-area identity and deduplicate normalized entities before persistence.

## 5. Category discovery policy

The provider policy must query real tag semantics, not substitute unrelated categories.

At minimum, nightlife must have its own deterministic provider mapping. It must not fall through to a default query containing cafes, restaurants, libraries, arts centres, or theatres unless those tags are explicitly part of the nightlife policy.

Every category observation reports one of:

- `READY`
- `PARTIAL`
- `MISSING`

A category is not `MISSING` merely because the request timed out. Timeout/rate-limit/provider failure is a runtime observation and normally yields `PARTIAL` or unresolved coverage, not proof that the physical category does not exist.

## 6. Fresh-cache read gate

Before any discovery network work, the server checks for a compatible fresh candidate/catalog snapshot.

A cache hit is reusable only when all relevant dimensions match:

```text
canonical_destination_id
+ discovery_area_identity
+ provider_policy_version
+ catalog_schema_version
+ readiness_policy_version
+ source/provider family
```

If `expires_at > now` and the snapshot remains compatible:

- return/reuse it;
- do not call Photon/Overpass solely to recreate the same catalog;
- record the cache source in operation diagnostics.

If expired but still safe for existing truth rules:

- it may support a stale-while-refresh path only if the response labels it as stale;
- background refresh may start;
- stale data must not be upgraded in fact quality.

If incompatible or unusable:

- begin/reuse hydration normally.

A release gate must prove that warm provider-call count is lower than cold provider-call count. A TTL that is only written and never read fails this contract.

## 7. Mobility interaction

Catalog discovery and mobility are related but separate phases.

The Anywhere mobility ruling remains:

- global destination mobility coverage may be PARTIAL;
- a normal selectable plan must have acceptable evidence for **100% of its used legs**;
- missing legs may be shown only as PARTIAL/NON_SELECTABLE truth with explicit gap identities and provenance;
- no haversine-derived travel time, LLM-estimated duration, or mock time may be promoted to live mobility truth.

The v1 planning shortlist remains bounded and mobility matrix requests must respect the measured Valhalla per-request cell limit.

## 8. Completion and Journey behavior

Hydration completion changes destination/catalog capability. It does not silently rewrite the user's Journey.

For an existing DRAFT Journey:

1. hydration reaches a plannable capability;
2. UI shows completion;
3. user chooses **Go to planning**;
4. planning reads the hydrated catalog;
5. the same Journey id remains in use.

Automatic background hydration may update catalog/cache state, but it must not automatically select a plan, start execution, create a booking, or mutate user intent.

## 9. Release evidence required

Before this policy is called implemented, provide evidence for:

- one county using Photon extent rather than the 5 km clamp;
- nightlife query no longer using the unrelated default tag set;
- cold vs warm provider-call count demonstrating TTL read reuse;
- cold operation accepted in <= 1 second and resumed after refresh using the same operation id;
- provider timeout/429 produces PARTIAL/runtime failure, not false structural UNAVAILABLE;
- no provider network call occurs inside a SQLite write transaction;
- user can leave the hydration view and later return to the same operation;
- completion exposes Go to planning and does not auto-mutate Journey;
- review/demo prehydration is labeled as warm/READY rather than misrepresented as cold performance.
