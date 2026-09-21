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
