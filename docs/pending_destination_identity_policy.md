# CityNexus Pending Destination Identity Policy

Status: arbiter contract note for ORD-0157 / R10 pending-destination semantics.

## Decision

A destination that has not been canonically resolved MUST NOT be represented by stuffing
user text into `canonical_destination_id`.

Therefore values such as:

```text
pending:云和县
pending:zzxqvw不存在县
unresolved:<hash>
```

are not canonical destination identities.

For NO_MATCH, AMBIGUOUS, or RUNTIME_FAILURE:

```text
canonical_destination_id = null
```

Raw destination text is resolver input and user-visible context. It is not identity.

## Storage shape

Introduce a separate pending/raw field. Preferred naming:

```text
pending_destination_label
```

The value must preserve the user's original input exactly for UI/audit purposes. Do not
silently normalize punctuation, spacing, or script and then present the normalized value
as if it were the original text.

If resolver matching needs a normalized query, store/derive that separately, for example:

```text
resolver_query_normalized
```

That normalized query is also not identity.

## Correlation and idempotency

An unresolved hydration operation still needs stable correlation/idempotency semantics.
Use an explicitly non-identity field such as:

```text
destination_pending_key
```

Hard rule:

> destination_pending_key is correlation/idempotency material only, never destination identity.

Do not expose it as a place/destination id, do not allow planner truth to depend on it,
and do not join catalog/place identity through it.

If deterministic retry deduplication requires a fingerprint, namespace it as request
idempotency material (for example pending-request-v1 + caller/request scope + normalized
request semantics + policy versions). A deterministic hash remains a request fingerprint,
not a canonical place id.

Prefer keeping the opaque correlation key and deterministic request fingerprint as two
separate concepts if the current schema allows it.

## State semantics

### RESOLVED

- canonical_destination_id: non-null real canonical identity
- resolver/provider provenance: required
- raw/pending user text may remain for audit/history
- readiness is decided separately by local planning evidence

### AMBIGUOUS

- canonical_destination_id: null
- preserve exact raw text
- preserve candidate identities separately
- require disambiguation; do not guess a winner

### NO_MATCH

- canonical_destination_id: null
- preserve exact raw text
- structural no-identity result
- no synthetic `pending:` identity

### RUNTIME_FAILURE

- canonical_destination_id: null
- preserve exact raw text
- retryable named runtime failure
- no synthetic `pending:` identity

## Migration / legacy pending rows

Existing rows containing `pending:` MUST NOT be deleted merely to make the new schema
look clean.

Migration rules:

1. preserve the existing operation row/id and audit history;
2. set canonical_destination_id to null for rows that are only synthetic pending identities;
3. backfill pending_destination_label from the best available raw-input source;
4. if only the already-normalized legacy `pending:` payload survives, mark that fact as
   legacy/normalized rather than claiming it is the exact original user input;
5. generate/backfill the non-identity pending correlation/idempotency material;
6. keep compatibility reads long enough for old rows to complete or be retried;
7. when a later provider resolution succeeds, populate the real canonical identity in
   place without changing the historical raw input.

Do not delete/recreate the operation merely to obtain a new fingerprint.

## Required ORD-0157 gates

1. unresolved raw input never appears in canonical_destination_id;
2. NO_MATCH -> canonical null;
3. RUNTIME_FAILURE -> canonical null and retryable named failure;
4. AMBIGUOUS -> canonical null and candidates preserved separately;
5. RESOLVED -> real canonical identity + provider provenance;
6. exact raw destination input is preserved separately from normalized resolver query;
7. punctuation-loss regression: `zzxqvw-不存在县` must not be presented as if
   `zzxqvw不存在县` were the original user text;
8. pending correlation/idempotency token cannot be consumed as planner/place identity;
9. repeated unresolved requests obey intended idempotency without inventing destination identity;
10. legacy `pending:` rows migrate/backfill in place and are not deleted;
11. mutation: reintroducing `pending:<raw>` into canonical_destination_id makes the gate red;
12. mutation: using destination_pending_key as canonical identity or catalog join key makes the gate red.

## Provider-to-application split contract (ORD-0188 -> ORD-0167)

The provider lane and the product/application lane are intentionally separate.

### Provider lane B owns evidence acquisition only

B may own the provider adapter implementation and adapter-bound isolated tests under:

    backend/app/integrations/discovery/**

B returns a typed provider-resolution result. At minimum the result must distinguish:

    MATCH
    AMBIGUOUS
    NO_MATCH
    RUNTIME_FAILURE

The provider result may carry, as applicable:

    provider name/version
    normalized provider query
    provider candidate identifier
    provider display label
    WGS84 coordinates
    observed_at
    candidate set for AMBIGUOUS
    retryable flag / typed runtime error
    raw provider evidence/provenance needed for audit

The exact repository type names may differ, but the semantic distinctions above MUST remain
machine-readable.

B MUST NOT decide that a provider candidate is already a CityNexus canonical destination.
B MUST NOT write application persistence, pending/canonical fields, planner joins, catalog side
effects, or application idempotency.

In particular:

- provider timeout / transport/runtime failure MUST NOT become NO_MATCH;
- ambiguous provider evidence MUST NOT be collapsed to MATCH merely to unblock planning;
- a provider label or coordinate pair is evidence, not product identity by itself.

### Application lane C owns product truth

C consumes B's typed result and owns:

- exact raw input vs normalized query separation;
- unresolved canonical_destination_id = null;
- pending operation persistence/history;
- in-place transition from pending request to real canonical identity;
- application retry/idempotency;
- catalog hydration handoff;
- planner/product joins;
- final small-county end-to-end closure.

Only C decides when provider evidence has satisfied the product's canonical-identity contract.

### No cross-boundary "helping"

Waiting for the other lane is NOT permission to cross the write boundary.

If B stops at an interface needed by C:

- B reports the interface/result shape and stops;
- Commander/ledger forwards that interface unchanged;
- C adapts only the application-side consumer.

If C needs a provider-side shape change:

- C files/records the requested contract delta;
- B owns the provider-side modification;
- C MUST NOT "just fix" files under integrations/discovery/** while waiting.

Likewise B MUST NOT reach forward into anywhere_capability/application persistence to make its
adapter appear end-to-end complete.

A split task that requires both sides to change must use an explicit handoff receipt, not overlapping
writes.

Recommended handoff receipt:

    provider_lane_source
    provider_result_type_or_schema
    outcome_enum
    provenance_fields
    runtime_failure_shape
    ambiguity_shape
    example_MATCH
    example_AMBIGUOUS
    example_NO_MATCH
    example_RUNTIME_FAILURE
    consumer_owner
    write_boundary_confirmed

Freeze sentence:

> **B resolves provider evidence; C decides when that evidence becomes product truth. Waiting is a handoff state, not permission to cross the boundary.**

## End-to-end runner is not implementation owner

An end-to-end order may be assigned to a lane as the **runner/evidence collector** even when the
chain crosses components owned by other lanes.

That assignment does NOT expand the runner's write domain.

For the current ORD-0192 shape:

- lane B may execute the full Gongshan/Yunhe chain, observe every stage, preserve evidence, and
  name the exact blocker;
- B may modify only its provider-owned write domain already defined above;
- if the failure is in application identity/persistence, catalog orchestration, planner truth,
  frontend visibility, or another owner's domain, B must stop at the blocker and hand it to the
  owning lane;
- B must not "finish the E2E" by patching downstream application files;
- downstream owners must not reach backward into the provider domain to make the E2E pass.

Required blocker receipt when the runner reaches another owner's defect:

    runner_order
    exact_source
    case_name
    stage
    request/input
    observed_result
    expected_contract
    evidence_files
    owning_lane
    handoff_status = BLOCKED_ON_OWNER | READY_FOR_RETRY

The same runner must rerun the affected stage after the owning lane delivers a fix before the
end-to-end case can be called closed.

Freeze sentence:

> **Owning the E2E run means owning the evidence, not every implementation layer it traverses.**

### Resolver-integration unlock marker

The mechanical "resolver is connected" trigger MUST mean product-level integration, not merely a
provider MATCH inside lane B.

Use the following minimum unlock condition:

    P7_RESOLVER_INTEGRATED = true

only when one previously-unseeded raw destination goes through the normal application path and
proves all of:

1. B's typed provider result is consumed by C;
2. exact raw input and normalized resolver query remain separate;
3. MATCH produces a server-owned real canonical identity;
4. unresolved companion states keep canonical_destination_id = null;
5. the operation is persisted/replayable with intended idempotency;
6. no pending/raw key is used as product identity.

A provider-only MATCH does not unlock P7.

Once this marker is true, Harness/Human-Journey wakeup may proceed mechanically. If the visible
product still cannot complete the journey, that is a product finding, not a reason to delay wakeup.

## Live small-county end-to-end closure for ORD-0167

ORD-0167 is not fully closed by schema/unit tests alone. It must include one real end-to-end case
that begins with a destination absent from the local seeded/catalog identity set and ends at the
shared planning path without inventing identity.

### Happy-path case

Choose one real small county/district that:

- is not already represented by a local seed/canonical destination row at test start;
- is resolvable by the configured live resolver/provider;
- has enough provider-backed discovery data to exercise the normal catalog/planner path.

Record the exact user input text before any normalization.

Required proof sequence:

1. **Pre-state inventory**
   - exact input string;
   - local catalog/identity query showing the destination is not already satisfied by a seed row;
   - relevant provider mode/configuration.

2. **Pending/request state**
   - exact raw input remains in `pending_destination_label`;
   - normalized resolver query is separate;
   - `canonical_destination_id` is null until a real provider-backed identity is resolved;
   - `destination_pending_key` is correlation/idempotency only.

3. **Resolution**
   - real provider attempt is observable;
   - successful resolution writes a real canonical destination identity in place;
   - provider/provenance fields identify the resolver source;
   - no `pending:<raw>`, raw-text hash, or pending key becomes identity.

4. **Discovery/catalog hydration**
   - downstream provider discovery is made using the resolved canonical destination context;
   - normalized catalog rows persist with source/provenance;
   - the operation keeps its historical raw input and operation id.

5. **Shared planner**
   - planner/catalog joins use the real canonical identity/catalog entities;
   - no planner join uses `destination_pending_key`;
   - no seeded/synthetic fallback is allowed to masquerade as live evidence.

6. **Product outcome**
   - when provider evidence is sufficient, the case must reach the same shared planner and produce a
     normal selectable/eligible result;
   - if provider evidence is genuinely insufficient, report that named provider/evidence limitation
     instead of fabricating a selectable result.

7. **Replay/idempotency**
   - repeating the same request follows the intended idempotency behavior;
   - the retry does not create a second fake destination identity or duplicate canonical catalog
     identity.

### Mobility-evidence milestone classification

For the overnight Gongshan/Yunhe closure, a truthful chain may stop before SELECTABLE when the
first real blocker is mobility evidence that is not hard-eligible.

The milestone is considered materially achieved at that boundary only when all upstream proof is
real and the blocker is named from the candidate's **actual used edges**.

Allowed milestone outcome:

    HYDRATABLE
    blocker = MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE

This is acceptable evidence of chain progress. It is NOT a SELECTABLE result.

Hard rules:

1. Do not enable live routing on the user's main preview merely to manufacture SELECTABLE.
2. Do not upgrade EXPLICIT_FROZEN_FIXTURE / SYNTHETIC_DEFAULT / UNKNOWN evidence into hard-eligible
   evidence for convenience.
3. Aggregate repository counts such as "184/240 rows are SYNTHETIC_DEFAULT" are diagnostic context,
   not proof that the current candidate is blocked. The E2E runner must inventory the exact edges
   that the candidate actually uses.
4. If all actual used edges are hard-eligible despite background synthetic rows, the candidate may
   continue toward SELECTABLE.
5. If any required used edge is not hard-eligible, stop honestly at the named mobility blocker.
6. A canary-only live Valhalla run may be performed later as additional evidence, but it is not an
   overnight acceptance prerequisite and must not change preview/live-user configuration.

Required mobility blocker receipt:

    candidate_id
    used_edge_count
    used_edge_ids
    per_edge_source_kind
    per_edge_provider_or_fixture
    per_edge_fact_quality
    per_edge_hard_eligible
    hard_eligible_count
    frozen_fixture_count
    synthetic_default_count
    unknown_count
    first_blocking_edge_or_edges
    final_product_state
    blocker_reason

The following upstream E2E facts remain hard requirements even when the final outcome is the named
mobility gap:

- pre-state proves no pre-recorded/golden destination/catalog satisfaction;
- provider observations and provenance are retained;
- provider extent/bbox is used when available rather than silently replacing it with a fixed 5 km
  circle;
- warm/retry path proves a real read/cache gate and is not merely another cold hydration;
- canonical identity and provider-backed catalog truth reach the shared planner without pending/raw
  identity substitution.

Freeze sentence:

> **Background synthetic evidence predicts risk; only the actual used-edge inventory proves the blocker. Stop truthfully at the first real gap, never fabricate SELECTABLE.**

### Negative companion case

Run one structurally unresolvable input such as the standing nonsense-string regression.

Required result:

- `canonical_destination_id = null`;
- exact raw text preserved;
- state = NO_MATCH (or the repository's exact structural no-match state);
- no catalog/planner identity is synthesized;
- no pending key is used as a Place/destination join key.

### Runtime-failure companion

Inject or reproduce a resolver/provider runtime failure separately from NO_MATCH.

Required result:

- `canonical_destination_id = null`;
- retryable named runtime state;
- exact raw input preserved;
- no false NO_MATCH;
- no synthetic canonical identity.

### Evidence receipt

The end-to-end receipt should include:

    source sha/archive
    exact raw input
    normalized resolver query
    pre-state identity/catalog inventory
    operation id
    canonical id before/after resolution
    resolver/provider provenance
    discovery/catalog provenance
    planner input identity
    final product state
    retry/idempotency result

Do not call the happy path complete merely because the resolver returns a name. The closure target is
identity -> provider-backed catalog -> shared planner/product outcome.

Freeze sentence:

> **Resolve a real place, preserve the user's raw request, and carry only real canonical identity into planning.**

## Freeze sentence

**Unknown destination text may identify a request to resolve a destination; it does not
identify a destination.**
