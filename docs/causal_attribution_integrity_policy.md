# R14 — Causal Attribution Integrity / 因果归因真值

Status: arbiter contract note for CityNexus cross-layer error attribution.

## 1. Purpose

CityNexus MUST NOT present one failure class as another merely because both travel through a
shared fallback path, exception handler, UI banner, or default value.

Freeze sentence:

> **Fault attribution must come from the evidence that distinguishes the fault. A lower or
> adjacent layer may carry the result, but it may not invent a different cause.**

In practical terms: do not borrow a convenient message from another layer.

R14 does not replace R1, R7, R10, R13, or their detailed contracts. It is the common
cross-layer invariant that prevents the same category of truth defect from reappearing in a
different subsystem.

## 2. Four layers covered by R14

### R14-I — Input attribution

Input uncertainty, absence, or parse failure must not be rewritten into a concrete user value.

Examples:

- explicit budget 1600 CNY -> 1600 CNY;
- budget absent -> null / UNKNOWN;
- extraction uncertain -> NEEDS_CONFIRMATION / BLOCKED;
- parse failure -> named parse/input failure;
- none of the above may become numeric 0.

This is the cross-layer form of ORD-0152 / R7 input-truth parity.

### R14-R — Runtime / fallback attribution

A runtime or storage failure must keep its actual runtime class.

Examples:

- SQLite writer contention -> named transient database/runtime failure or retryable service
  state, not a naked generic 500 with no structured reason;
- resolver timeout -> resolver runtime failure, not structural destination UNAVAILABLE;
- a valid operation whose target set is empty -> successful idempotent no-op, not server error.

Fallback behavior may reduce functionality, but it must not rewrite the reason.

### R14-S — Resource / state attribution

A valid response that says a resource or state is missing must not be reclassified as transport
failure.

Examples:

- journey endpoint returns HTTP 404 for a stale stored journey id -> stale/missing journey
  state;
- 404 is positive evidence that the request reached the server and received an application
  response; it cannot be labeled "network unavailable";
- after stale-id detection, the client must clear or quarantine the invalid stored reference
  and offer a real recovery path instead of persisting the false offline state.

This covers ORD-0169.

### R14-P — Presentation attribution

User-visible text, aria-live output, telemetry, and recovery actions MUST be derived from the
same structured classification.

The frontend must not:

- map every fetch failure/status to an "offline" banner;
- infer reason by matching English text;
- show a user-corrective instruction when the product corrupted the input;
- hide major UI surfaces because one unrelated state failed unless that behavior is explicitly
  tied to the classified state.

For a given failure instance, screen copy, accessibility announcement, analytics/telemetry, and
recommended recovery action must agree on the same machine reason.

## 3. Evidence precedence

Classification should use the strongest discriminating evidence available.

Recommended precedence:

1. explicit typed domain/runtime result or structured error code;
2. HTTP status + structured response body from the same request;
3. transport exception / timeout / connection failure for that request;
4. browser/network heuristics only when no stronger request-specific evidence exists.

Important consequences:

- an HTTP 404/409/422/500 response is not "offline"; the server answered;
- `navigator.onLine=true` alone is not proof that every service is reachable, but a same-origin
  HTTP response is enough to disprove "no network response" for that request;
- a successful unrelated endpoint does not override the target endpoint's structured error, but
  it can help demonstrate that a global "network unavailable" banner is over-broad.

## 4. Required classification shape

Where practical, errors/states should have a server- or product-owned structured form such as:

    error_class
    reason_code
    retryable
    source_layer
    correlation_id
    recovery_action
    message_key

Equivalent field names are allowed. The important rule is that classification happens once at
the appropriate evidence boundary and is propagated, not re-invented independently by UI,
telemetry, and fallback code.

## 5. Recovery must match cause

Examples:

- stale journey id -> clear invalid local reference -> journey picker / current valid journey;
- true offline/transport failure -> cached read-only mode / retry when connectivity returns;
- server runtime/transient DB busy -> retry/backoff with named service state;
- structural no-match -> destination not identified / disambiguate or choose another;
- input uncertainty -> ask user to confirm, not "adjust budget";
- empty reset target -> no-op result, not server-error recovery.

A recovery action that only makes sense for a different failure class is itself an R14 failure.

## 6. Required gates

At minimum maintain these regression cases:

1. **Input truth**: explicit 1600 CNY remains 1600 through extraction -> normalization ->
   persistence -> readback -> planner input.
2. **Input unknown**: missing/uncertain budget cannot become 0.
3. **DB contention**: a forced SQLite writer-lock path returns a named structured runtime class;
   UI must not render a generic unexplained failure as if it were user error.
4. **Empty valid operation**: valid scoped reset with zero matching demo rows is 200/204
   idempotent no-op (or equivalent successful empty outcome), never 500.
5. **Stale journey 404**: stale localStorage journey id + target /experience 404 must produce a
   missing/stale-journey classification, clear/quarantine the stale id, expose a recovery path,
   and restore the map/normal shell as appropriate.
6. **True offline**: actual transport failure remains OFFLINE/NETWORK_UNAVAILABLE and is not
   accidentally reclassified as stale journey.
7. **Server 5xx**: application/runtime 5xx remains SERVER/RUNTIME failure and is not called
   OFFLINE merely because fetch did not yield usable domain data.
8. **UI consistency**: visible banner + aria-live + telemetry + recovery action all use the same
   machine reason for each of the above states.

## 7. Mutation-kill requirements

The suite must kill at least these mutations:

- change stale-journey 404 mapping to OFFLINE;
- change true transport failure mapping to JOURNEY_NOT_FOUND;
- change absent/uncertain budget fallback to 0;
- change valid-empty reset outcome to 500;
- collapse named DB/runtime contention to unstructured generic 500;
- let UI choose a message from a broad "catch" branch instead of the structured reason.

A test that only checks copy text without checking the discriminating evidence and machine reason
is insufficient.

## 8. Observability rule

Telemetry must record what the classifier actually decided and the evidence category it used.

Do not emit:

    network_unavailable

for an HTTP 404 merely because the UI entered a fallback screen.

Prefer structured fields such as:

    attribution_reason=JOURNEY_NOT_FOUND
    evidence_kind=HTTP_RESPONSE
    http_status=404
    source_layer=RESOURCE_STATE

This makes false-cause regressions discoverable in production instead of only from screenshots.

## 9. Relationship to existing rules

- R7 owns planner/input parity details; R14 forbids misattributing corrupted input to the user.
- R1/R10 own resolver state distinctions; R14 forbids rewriting runtime failure as structural
  destination truth.
- R13 owns destructive demo isolation; R14 says a valid empty reset target is not a server fault.
- ORD-0112 owns DB-lock implementation details; R14 requires the resulting cause to stay named.
- ORD-0169 owns stale-journey recovery; R14 defines the general attribution invariant.

## 10. Freeze sentence

**Classify from discriminating evidence, propagate the classification, and never borrow a
convenient cause from another layer.**
