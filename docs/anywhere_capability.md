# CityNexus Anywhere Capability v1

Status: arbiter contract note for Commander/F-lane merge.

## Arbiter rulings R1-R4

### R1 — resolver outage is runtime failure, not structural UNAVAILABLE

Accepted.

`READY | HYDRATABLE | UNAVAILABLE` describes structural destination capability.
If Photon is temporarily unreachable while resolution is required, return
`DESTINATION_RESOLVER_UNAVAILABLE` and make the hydration/request retryable.
Do not permanently downgrade the destination to `UNAVAILABLE` merely because the
resolver is down.

If a canonical destination identity is already cached, the backend may answer from
that identity without probing Photon again.

v1 resolver path is Photon only. Nominatim is not a v1 dependency.

Photon locale rule from measured evidence: do not send `lang=zh`; default Photon
results may preserve Chinese names. UI language changes must not silently replace the
canonical destination identity with a different transliteration.

### R2 — structural capability and runtime provider state are separate truths

Accepted.

`capability`:
- `READY`
- `HYDRATABLE`
- `UNAVAILABLE`

`provider_status` observations:
- `OK`
- `RATE_LIMITED`
- `UNREACHABLE`
- `PARTIAL`

A missing observation means the provider has not been checked; do not fabricate `OK`.

Examples:
- `UNAVAILABLE + no provider outage` means the backend has no traceable supported source.
- `HYDRATABLE + UNREACHABLE` means support exists but the provider cannot be reached now.
- `HYDRATABLE + RATE_LIMITED` is retryable and must not be shown as permanent unsupported.
- `PARTIAL` means a parseable response was incomplete or only partially usable.

### R3 — current-plan marker is additive and derived, never a second persisted truth

Choose option (a), specifically an additive per-plan `is_current` projection.

`journey.active_plan_version_id` remains the single authoritative persisted truth.
`is_current` MUST be computed from that field at response time and MUST NOT be persisted
or independently mutated.

Invariant:

```text
is_current(plan) == (plan.id == journey.active_plan_version_id)
```

If `active_plan_version_id` is null, every returned plan has `is_current=false`.
If non-null and the referenced plan is in the response, exactly one plan is current.

This avoids a response-envelope breaking change while removing consumer ambiguity.
A mutation/focused gate should prove that changing the authoritative active plan changes
the projection and that stale versions never remain marked current.

### R4 — WGS-84 is canonical persistence

Accepted with one clarification.

All normalized persisted CityNexus geometry is WGS-84 and carries
`coordinate_system=WGS84`.

Provider provenance separately records `source_coordinate_system`.

For a future Amap provider, source coordinates may be GCJ-02. Conversion to canonical
WGS-84 must happen in one owned geospatial adapter at provider ingress. If an Amap
basemap or other GCJ-02 rendering surface is later used, WGS-84 -> GCJ-02 conversion
must also go through that same owned conversion boundary.

Frontend feature code and business services must not each perform their own conversions.

Do not freeze any Amap-specific request/response payload in v1. The generic provider and
provenance contract already leaves the hook. Amap remains optional until credentials and
measured behavior exist.

## Capability semantics

`READY` means the server-owned readiness policy passes using traceable normalized data.
`HYDRATABLE` means trusted providers exist but current local data is missing, stale, or
insufficient and can be prepared.
`UNAVAILABLE` means the product has no currently supported traceable source capable of
preparing the destination.

`UNAVAILABLE` is structural. It is not a synonym for timeout, 429, DNS failure, or 5xx.

## Coverage is the readiness input, not raw POI count

Every capability response reports category coverage:

- attractions
- food
- nightlife
- lodging
- mobility
- booking

Each dimension is `READY | PARTIAL | MISSING` and may include a verified candidate count
for diagnostics. Candidate count alone cannot promote the destination to READY.

The exact readiness threshold is a server-owned, versioned policy
(`readiness_policy_version`). The policy must evaluate category coverage, provenance,
and mobility evidence. It must not be an unversioned magic number such as
`places.length > 0`.

Only the backend capability/readiness evaluator may promote `HYDRATABLE -> READY`.
The frontend, an LLM, and provider success alone cannot perform that transition.

Minimum promotion conditions:

1. destination identity is canonical and traceable;
2. persisted place identities are normalized and provenance-bearing;
3. the current readiness policy's required category coverage passes;
4. mobility coverage required by that policy is present at an accepted fact quality;
5. no partial provider response is being treated as complete;
6. persistence completed atomically after provider network work ended.

## Hydration state machine

```text
QUEUED
  -> RUNNING / RESOLVING_DESTINATION
  -> RUNNING / DISCOVERING_POIS
  -> RUNNING / NORMALIZING
  -> RUNNING / BUILDING_MOBILITY
  -> RUNNING / PERSISTING
  -> RUNNING / FINALIZING
  -> COMPLETED

Any nonterminal phase may -> FAILED for retryable runtime failure.
Resolution/discovery may -> UNAVAILABLE for a structural no-source result.
RUNNING -> ABANDON_REQUESTED -> ABANDONED when work cannot stop immediately.
QUEUED -> ABANDONED is allowed.
```

`FAILED` is runtime failure and can be retryable.
`UNAVAILABLE` is structural and must not be used merely for provider outage.

No fake percentage is required. Expose phase, elapsed time, retry advice, and provider
observations.

## Durable idempotency

The durable hydration fingerprint is server-owned and includes at least:

```text
canonical_destination_id
+ catalog_schema_version
+ readiness_policy_version
+ provider_policy_version
```

All callers for one nonterminal fingerprint converge on one operation id.
A process-local mutex is not sufficient as the sole guarantee.

## Database lock boundary

Network calls to Photon, Overpass, routing providers, or future Amap adapters must happen
outside SQLite write transactions.

Required shape:

```text
short read/claim transaction
-> close/release
-> provider network work
-> short persistence transaction
-> close/release
-> next phase
```

The stay-generation long-write-lock failure must not be reproduced in catalog hydration.

## v1 provider facts

Measured local facts provided by Commander are treated as design evidence:

- Photon resolves the selected small-county case and returns `admin_level`, WGS-84 point,
  and an extent/bounding box.
- Photon rejects `lang=zh`; use default language behavior for Chinese identity.
- Nominatim is not reachable from the current machine and is not part of v1.
- Overpass v1 uses POST form data; do not rely on the measured failing GET query shape.
- Primary Overpass availability is fragile enough that 429, timeout, and partial responses
  are first-class expected states.
- Photon and Overpass normalized coordinates are WGS-84.

Live-provider behavior must have bounded timeout, retry/backoff policy, cache, and
provider-status evidence. Ordinary regression tests must use deterministic fixtures rather
than depending on public provider uptime.

## Reason codes

The Anywhere v1 contract freezes these nine stable machine-readable reasons:

1. `NO_TRACEABLE_CATALOG_SOURCE`
2. `DESTINATION_RESOLVER_UNAVAILABLE`
3. `CATALOG_EMPTY`
4. `CATALOG_INSUFFICIENT`
5. `CATALOG_PREPARING`
6. `CATALOG_PROVIDER_UNAVAILABLE`
7. `NO_FEASIBLE_PLAN`
8. `NO_EXISTING_PLAN_TO_REPLAN`
9. `MOBILITY_DATA_UNAVAILABLE`

429/timeout/partial details belong in provider observations; frontend code must not infer
reason codes by matching English provider text.

## Existing Journey recovery

Hydration is destination/catalog work, not Journey recreation.
A Journey created before its destination becomes READY must keep the same Journey id and
become plannable after hydration completes.

The existing Beijing Journey is a required regression case.

## AI boundary

AI may interpret preferences, semantically tag already verified places, rank allow-listed
place ids, and produce natural-language explanations.

AI must not create persistent physical place identity, coordinates, booking truth, route
duration, or provider provenance.

Unknown place ids emitted by an LLM must be rejected rather than persisted.

## Amap scope

Do not freeze an Amap-specific payload in Anywhere v1.

The generic provider/provenance model intentionally supports future Amap integration,
including `source_coordinate_system=GCJ02`. Amap remains an optional adapter/config hook
until a credentialed spike produces measured request/response behavior.


## R10 — One canonical resolver boundary for capability and hydration

Destination identity must not be computed independently by
`GET /destinations/capability` and `POST /catalog-hydrations`.

Both entry points MUST call the same server-owned resolver core, conceptually:

```text
resolve_destination(raw_input)
  -> RESOLVED(canonical identity, provider provenance)
  -> AMBIGUOUS(candidate identities)
  -> NO_MATCH
  -> RUNTIME_FAILURE
```

The shared boundary owns:

- Photon invocation and provider observations;
- canonical destination identity;
- canonical display name;
- WGS-84 centroid/extent normalization;
- resolver provenance;
- ambiguity/no-match/runtime-failure classification;
- cache reuse of an already resolved identity.

### Endpoint parity invariant

For the same raw destination input and the same resolver/provider state:

- capability and catalog-hydration admission MUST produce/reuse the same canonical identity;
- neither path may persist or return `unresolved:<hash>` as canonical identity;
- neither path may require an already registered catalog source before attempting identity resolution;
- a resolver outage is a retryable runtime failure on both paths, not structural UNAVAILABLE;
- a healthy resolver returning zero candidates is a structural no-identity result on both paths;
- an ambiguous resolver result must remain ambiguous rather than one endpoint guessing a winner.

If one endpoint resolves a destination while the other says `NO_REGISTERED_SOURCE` for the same input, the parity gate fails.

### State after successful identity resolution

Resolution success does not by itself mean READY.

- resolved identity + insufficient/missing local planning evidence -> `HYDRATABLE`;
- resolved identity + sufficient compatible local catalog/evidence for a selectable shared-planner candidate -> `READY`;
- resolver healthy + no canonical candidate -> `UNAVAILABLE` with no canonical id;
- resolver unavailable -> runtime failure / retryable, not `UNAVAILABLE`.

Use the existing machine action `PREPARE_DESTINATION` for the HYDRATABLE case rather than inventing a second action enum for "start hydration".

### Required R10 parity gates

At minimum test all of:

1. a known resolvable county through capability;
2. the same county through catalog-hydration admission;
3. both return the same canonical identity and provider provenance;
4. removing resolver invocation from either endpoint makes the test fail;
5. Photon healthy + zero result -> no canonical id, structural no-identity result;
6. Photon timeout/unreachable -> retryable resolver runtime failure, no hash persisted;
7. legacy Journey raw city text remains preserved and is backfilled in place after successful resolution.

The implementation may keep separate HTTP handlers, but identity truth must have exactly one owner.
