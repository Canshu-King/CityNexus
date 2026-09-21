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

## Freeze sentence

**Unknown destination text may identify a request to resolve a destination; it does not
identify a destination.**
